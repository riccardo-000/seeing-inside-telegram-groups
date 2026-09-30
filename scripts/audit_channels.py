"""Full read-only audit: does channel X really have a (public, active) group?

No joins, no messages, no clicks. One request every --delay seconds (all
sources share the same throttle); at most --max-resolves username lookups
that are not already in the local session cache. Short FloodWait (<= 60 s):
wait and slow down; longer: stop. Create data/interim/audit/STOP to stop
gracefully. Resumable: channels already in channels_audit.csv are skipped.

Queue (highest priority first):
  1. TGDataset crypto candidates, re-read from data/interim/seeds_tgdataset_crypto_a*.csv
     while the Zenodo streams are still running;
  2. active channels + parents of comment chats from data/interim/pairs/chats.csv;
  3. channels recommended by Telegram as similar to audited active channels.

Per channel: description (links + @mentions), pinned post, last 200 posts
(plain/hidden/button links + @mentions), linked discussion group, every
linked username resolved and classified, every public group checked for
activity (last 100 messages). Verdict per channel with evidence saved in
data/interim/audit/{channels_audit,channel_links,groups}.csv.

Usage:
    python scripts/audit_channels.py --delay 6 --max-resolves 250
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import sys
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from telethon import TelegramClient, errors
from telethon.tl.functions.channels import GetChannelRecommendationsRequest, GetFullChannelRequest
from telethon.tl.types import Channel, InputPeerChannel, InputPeerUser, PeerUser

from find_pairs import GROUP_HINT, link_usernames, mentions
from peek_channel import TME_RE, extract_links
import prefilter_tme
from src.utils.budget import BudgetExceeded, ResolveBudget
from src.utils.config import DATA_INTERIM, load_config, session_path

csv.field_size_limit(sys.maxsize)  # t.me link lists of aggregator channels are huge

OUT = DATA_INTERIM / "audit"
ACTIVE_DAYS = 30
GROUP_MIN_MSGS, GROUP_MIN_USERS = 20, 5          # standalone group, last 7 days
COMMUNITY_MIN_FREE, COMMUNITY_MIN_USERS = 10, 5  # linked group used as a chat, last 7 days
MAX_CANDIDATES = 60                              # usernames checked per channel

AUDIT_COLS = [
    "channel", "channel_id", "source", "status", "verdict", "title", "subscribers", "last_post",
    "posts_30d", "scam", "fake", "verified", "linked_group", "linked_group_public",
    "linked_free_msgs_7d", "linked_free_users_7d", "public_groups_active", "public_groups_inactive",
    "n_candidates", "n_checked", "n_private_invites", "description", "checked_at", "error",
]
LINK_COLS = ["channel", "target", "found_in", "target_type", "target_title", "note"]
GROUP_COLS = [
    "group", "title", "members", "is_linked_to", "msgs_7d", "users_7d", "free_msgs_7d",
    "free_users_7d", "last_msg", "scam", "fake", "active",
]


class Stop(Exception):
    pass


class Api:
    """Single throttle for every request; counts username resolves."""

    def __init__(self, client, delay, max_resolves, hours):
        self.client, self.delay, self.max_resolves = client, delay, max_resolves
        self.deadline = time.time() + hours * 3600
        self.requests = self.resolves = 0
        self.floodwaits = 0
        self.budget = ResolveBudget("audit_channels")
        self.web_delay = 2.0
        self.web_requests = 0
        self.max_new_resolves_per_channel = 8

    async def tick(self):
        if (OUT / "STOP").exists():
            raise Stop("STOP file")
        if time.time() > self.deadline:
            raise Stop("time cap")
        await asyncio.sleep(self.delay)
        self.requests += 1

    async def run(self, make_coro):
        """Run one request with throttling and FloodWait handling."""
        while True:
            await self.tick()
            try:
                return await make_coro()
            except errors.FloodWaitError as e:
                self.floodwaits += 1
                # be conservative with the shared account: stop on any long wait or on the 2nd wait
                if e.seconds > 30 or self.floodwaits >= 2:
                    raise Stop(f"FLOODWAIT {e.seconds}s (#{self.floodwaits})")
                print(f"  short FloodWait {e.seconds}s: waiting and slowing down", flush=True)
                self.delay *= 1.5
                await asyncio.sleep(e.seconds + 5)

    def cached(self, username: str) -> bool:
        try:
            self.client.session.get_input_entity(username)
            return True
        except (ValueError, KeyError, TypeError):
            return False

    async def web(self, username: str) -> dict:
        """Free check on the public t.me web preview (no API call, no resolve)."""
        await asyncio.sleep(self.web_delay)
        self.web_requests += 1
        try:
            return await asyncio.to_thread(prefilter_tme.check, username, 20.0, False)
        except SystemExit as e:  # HTTP 429 from t.me
            raise Stop(str(e))
        except OSError as e:
            return {"status": f"web_error_{type(e).__name__}", "kind": ""}

    async def input_entity(self, username: str):
        """Input peer for a username; a network resolve only if not cached."""
        try:
            return self.client.session.get_input_entity(username)
        except (ValueError, KeyError, TypeError):
            pass
        if self.resolves >= self.max_resolves:
            raise Stop("username resolve cap reached")
        try:
            self.budget.take()  # shared daily budget for the whole account
        except BudgetExceeded as e:
            raise Stop(str(e))
        self.resolves += 1
        try:
            return await self.run(lambda: self.client.get_input_entity(username))
        except (ValueError, errors.UsernameInvalidError, errors.UsernameNotOccupiedError):
            return None


def append(path: Path, cols: list[str], row: dict) -> None:
    new = not path.exists()
    with open(path, "a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        if new:
            w.writeheader()
        w.writerow(row)


def read_col(path: Path, col: str) -> set[str]:
    if not path.exists():
        return set()
    with open(path, newline="", encoding="utf-8") as fh:
        return {r[col].lower() for r in csv.DictReader(fh) if r.get(col)}


class Auditor:
    def __init__(self, api: Api):
        self.api = api
        self.done = read_col(OUT / "channels_audit.csv", "channel")
        self.groups: dict[str, dict] = {}
        if (OUT / "groups.csv").exists():
            with open(OUT / "groups.csv", newline="", encoding="utf-8") as fh:
                self.groups = {r["group"].lower(): r for r in csv.DictReader(fh)}
        self.types: dict[str, tuple[str, str]] = {}  # username -> (type, title)
        self.queued: set[str] = set(self.done)
        self.q_tgd: list[dict] = []
        self.q_known: list[dict] = []
        self.q_rec: list[dict] = []
        self.q_linked: list[dict] = []
        self.q_priority: list[dict] = []
        self.tgd_rows_seen: dict[str, int] = {}
        self.verdicts = Counter()
        self.aggregators_first = False

    # ---------- queue ----------
    def add(self, queue: list, username: str, source: str, **extra) -> None:
        if username and username.lower() not in self.queued:
            self.queued.add(username.lower())
            queue.append({"username": username, "source": source, **extra})

    def web_says_skip(self, username: str) -> bool:
        """True if scripts/prefilter_tme.py already saw this channel dead or inactive (no API needed)."""
        if not hasattr(self, "_prefilter"):
            self._prefilter = {}
            for f in DATA_INTERIM.glob("tme_prefilter*.csv"):
                with open(f, newline="", encoding="utf-8") as fh:
                    for r in csv.DictReader(fh):
                        self._prefilter[r["username"].lower()] = r
        r = self._prefilter.get(username.lower())
        if r is None:
            return False
        return not (r["status"] == "alive" and r["kind"] in ("channel", "channel_no_preview")
                    and (r["kind"] == "channel_no_preview" or int(r.get("posts_30d") or 0) > 0))

    def refresh_tgdataset(self) -> None:
        # best candidates first (scripts/rank_tgdataset.py), then anything newer from Zenodo
        queue = DATA_INTERIM / "tgdataset_queue.csv"
        if queue.exists() and "queue" not in self.tgd_rows_seen:
            with open(queue, newline="", encoding="utf-8") as fh:
                for r in csv.DictReader(fh):
                    if not self.web_says_skip(r["username"]):
                        self.add(self.q_tgd, r["username"], "tgdataset", channel_id=r["channel_id"])
            self.tgd_rows_seen["queue"] = 1
        for f in sorted(DATA_INTERIM.glob("seeds_tgdataset_crypto_*.csv")):
            if f.name.endswith("_alive.csv"):
                continue
            text = f.read_text(encoding="utf-8")
            if not text.endswith("\n"):  # file still being written: skip the partial last line
                text = text[: text.rfind("\n") + 1]
            rows = list(csv.DictReader(text.splitlines()))
            for r in rows[self.tgd_rows_seen.get(f.name, 0):]:
                if self.web_says_skip(r.get("username", "")):
                    continue
                self.add(self.q_tgd, r.get("username", ""), "tgdataset", channel_id=r.get("channel_id", ""))
            self.tgd_rows_seen[f.name] = len(rows)

    def load_master(self) -> None:
        """Priority queue from data/interim/master.csv (scripts/build_master.py):
        1. project channels linked to an active community but never audited;
        2. groups/channels named by the manual review and not yet verified;
        3. aggregators marked MANY in the manual review.
        """
        path = DATA_INTERIM / "master.csv"
        if not path.exists():
            return
        with open(path, newline="", encoding="utf-8-sig") as fh:
            rows = list(csv.DictReader(fh))
        for r in rows:
            if r["channel"] and r["channel_status"] == "not_checked":
                self.add(self.q_priority, r["channel"].lstrip("@"), "master:project_channel")
        for r in rows:
            g = r["group"]
            if g.startswith("@") and r["group_type"] == "unverified":
                self.add(self.q_priority, g.lstrip("@"), f"master:manual_check_of_{r['channel']}")
        for r in rows:
            if r["channel"] and (r.get("manual_group") or "").strip().upper() == "MANY":
                self.add(self.q_priority, r["channel"].lstrip("@"), "master:aggregator")

    def load_known(self) -> None:
        path = DATA_INTERIM / "pairs" / "chats.csv"
        if not path.exists():
            return
        with open(path, newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        channels = [r for r in rows if r["kind"] == "channel" and r["note"] != "inactive channel" and r.get("last_date")]
        # channels with many links first (aggregators like @Airdrop)
        channels.sort(key=lambda r: -int((r["note"].split(" ")[0] or "0") if r["note"].split(" ")[0].isdigit() else 0))
        for r in channels:
            self.add(self.q_known, r["username"], "search")
        for r in rows:  # comment chats: audit their parent channel
            if r["kind"] == "group" and "discussion" in r.get("note", ""):
                self.q_known.append({"username": r["username"], "source": "parent_of_comment_chat", "is_group": True})

    def next_item(self):
        self.refresh_tgdataset()
        for q in ((self.q_priority, self.q_known, self.q_linked, self.q_tgd, self.q_rec) if self.aggregators_first
                  else (self.q_priority, self.q_tgd, self.q_known, self.q_linked, self.q_rec)):
            if q:
                return q.pop(0)
        return None

    # ---------- groups ----------
    async def activity(self, entity) -> dict:
        msgs = await self.api.run(lambda: self.api.client.get_messages(entity, limit=100))
        since = datetime.now(timezone.utc) - timedelta(days=7)
        recent = [m for m in msgs if m.date >= since and m.action is None]
        users = {m.from_id.user_id for m in recent if isinstance(m.from_id, PeerUser)}
        free = [m for m in recent if m.reply_to is None and isinstance(m.from_id, PeerUser)]
        links = set()
        for m in msgs:  # only t.me links (not @mentions: those are mostly people)
            for ls in extract_links(m).values():
                links.update(link_usernames(ls))
        return {
            "_links": sorted(links),
            "msgs_7d": len(recent), "users_7d": len(users), "free_msgs_7d": len(free),
            "free_users_7d": len({m.from_id.user_id for m in free}),
            "last_msg": msgs[0].date.date().isoformat() if msgs else "",
        }

    async def check_group(self, ent: Channel, linked_to: str = "") -> dict:
        key = (ent.username or f"id{ent.id}").lower()
        if key in self.groups:
            return self.groups[key]
        full = await self.api.run(lambda: self.api.client(GetFullChannelRequest(ent)))
        parent = ""
        if full.full_chat.linked_chat_id:
            p = next((c for c in full.chats if c.id == full.full_chat.linked_chat_id), None)
            parent = getattr(p, "username", None) or str(full.full_chat.linked_chat_id)
        row = {"group": ent.username or f"id{ent.id}", "title": ent.title,
               "members": full.full_chat.participants_count, "is_linked_to": linked_to or parent,
               "scam": ent.scam, "fake": ent.fake}
        try:
            row |= await self.activity(ent)
        except errors.RPCError as e:
            row |= {"last_msg": f"not readable: {type(e).__name__}"}
        if row["is_linked_to"]:
            row["active"] = (row.get("free_msgs_7d", 0) >= COMMUNITY_MIN_FREE
                             and row.get("free_users_7d", 0) >= COMMUNITY_MIN_USERS)
        else:
            row["active"] = (row.get("msgs_7d", 0) >= GROUP_MIN_MSGS
                             and row.get("users_7d", 0) >= GROUP_MIN_USERS)
        self.groups[key] = row
        append(OUT / "groups.csv", GROUP_COLS, row)
        if row.get("active"):
            for u in row.get("_links", []):
                self.add(self.q_linked, u, f"posted_in_group:@{row['group']}")
        return row

    # ---------- channels ----------
    async def parent_of(self, group_username: str):
        inp = await self.api.input_entity(group_username)
        if not isinstance(inp, InputPeerChannel):
            return None
        full = await self.api.run(lambda: self.api.client(GetFullChannelRequest(inp)))
        p = next((c for c in full.chats if c.id == full.full_chat.linked_chat_id), None)
        return getattr(p, "username", None)

    async def audit(self, item: dict) -> None:
        if item.get("is_group"):
            parent = await self.parent_of(item["username"])
            if parent and parent.lower() not in self.done:
                self.queued.add(parent.lower())
                await self.audit({"username": parent, "source": f"parent_of_comment_chat:@{item['username']}"})
            return

        name = item["username"]
        row = {"channel": name, "source": item["source"], "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        if not self.api.cached(name):
            w = await self.api.web(name)  # free: spend a resolve only on chats that are alive
            if w.get("status") in ("not_found", "empty_page"):
                return self.save(row | {"status": "not_found_web", "verdict": "dead"})
            if w.get("kind") == "user_or_bot":
                return self.save(row | {"status": "user_or_bot_web", "verdict": "dead"})
            if w.get("kind") == "channel" and w.get("last_post") and not int(w.get("posts_30d") or 0):
                return self.save(row | {"status": "alive_web", "verdict": "inactive", "title": w.get("title"),
                                        "subscribers": w.get("subscribers"), "last_post": w["last_post"][:10],
                                        "posts_30d": 0, "description": w.get("description")})
        inp = await self.api.input_entity(name)
        if inp is None:
            return self.save(row | {"status": "not_found", "verdict": "dead"})
        if isinstance(inp, InputPeerUser):
            return self.save(row | {"status": "user_or_bot", "verdict": "dead"})

        full = await self.api.run(lambda: self.api.client(GetFullChannelRequest(inp)))
        ch = next((c for c in full.chats if c.id == full.full_chat.id), None)
        if ch is not None and ch.megagroup:
            g = await self.check_group(ch)
            print(f"[{self.api.requests} req, {self.api.resolves} resolves] group @{name} ({row['source'][:30]}): "
                  f"{'ACTIVE' if g.get('active') else 'inactive'}", flush=True)
            parent = next((c for c in full.chats if c.id == full.full_chat.linked_chat_id), None)
            if parent is not None and getattr(parent, "username", None):
                self.add(self.q_linked, parent.username, f"parent_of_group:@{name}")
            return
        if ch is None or not ch.broadcast:
            return self.save(row | {"status": "not_a_channel", "verdict": "not_a_channel"})
        about = full.full_chat.about or ""
        row |= {"channel_id": ch.id, "title": ch.title, "subscribers": full.full_chat.participants_count,
                "scam": ch.scam, "fake": ch.fake, "verified": ch.verified,
                "description": about.replace("\n", " ")[:1000]}
        if item.get("channel_id") and str(item["channel_id"]) != str(ch.id):
            row["error"] = "username now belongs to a different channel"

        posts = await self.api.run(lambda: self.api.client.get_messages(ch, limit=100))
        if len(posts) == 100:
            posts += await self.api.run(lambda: self.api.client.get_messages(ch, limit=100, max_id=posts[-1].id))
        now = datetime.now(timezone.utc)
        row["last_post"] = posts[0].date.date().isoformat() if posts else ""
        row["posts_30d"] = sum(1 for m in posts if m.date >= now - timedelta(days=ACTIVE_DAYS))
        if not row["posts_30d"]:
            return self.save(row | {"status": "alive", "verdict": "inactive"})
        row["status"] = "alive"

        # pinned post, if older than the posts we read
        pinned = full.full_chat.pinned_msg_id
        if pinned and all(m.id != pinned for m in posts):
            p = await self.api.run(lambda: self.api.client.get_messages(ch, ids=pinned))
            if p:
                posts.append(p)

        # linked discussion group
        linked_active = False
        if full.full_chat.linked_chat_id:
            lg = next((c for c in full.chats if c.id == full.full_chat.linked_chat_id), None)
            if lg is not None:
                g = await self.check_group(lg, linked_to=name)
                linked_active = bool(g.get("active")) and bool(lg.username)
                row |= {"linked_group": lg.username or f"id{lg.id}", "linked_group_public": bool(lg.username),
                        "linked_free_msgs_7d": g.get("free_msgs_7d"), "linked_free_users_7d": g.get("free_users_7d")}
                append(OUT / "channel_links.csv", LINK_COLS, {
                    "channel": name, "target": row["linked_group"], "found_in": "linked_chat",
                    "target_type": "group", "target_title": lg.title,
                    "note": "community (free chat)" if linked_active else "comments only"})

        # every username the channel points to
        found: dict[str, str] = {}
        invites = set()
        def collect(links, where):
            for l in links:
                if l.split("/")[0].startswith("+") or l.startswith("joinchat"):
                    invites.add(l)
            for u in link_usernames(links):
                found.setdefault(u, where)
        collect(TME_RE.findall(about), "description")
        for u in mentions(about):
            found.setdefault(u, "description")
        for m in posts:
            for kind, links in extract_links(m).items():
                collect(links, "post" if kind == "plain" else f"post_{kind}")
            for u in mentions(m.message or ""):
                found.setdefault(u, "post_mention")
        dedup: dict[str, tuple[str, str]] = {}  # same username written with different case
        for u, w in found.items():
            dedup.setdefault(u.lower(), (u, w))
        found = {u: w for k, (u, w) in dedup.items() if k != name.lower()}
        freq = Counter()
        for m in posts:
            freq.update(u.lower() for u in mentions(m.message or ""))
        cands = sorted(found.items(), key=lambda kv: (kv[1] != "description", not GROUP_HINT.search(kv[0]), -freq[kv[0].lower()]))
        row |= {"n_candidates": len(cands), "n_private_invites": len(invites)}

        active_groups, inactive_groups, checked, new_resolves = [], [], 0, 0
        for u, where in cands[:MAX_CANDIDATES]:
            key = u.lower()
            if key not in self.types and not self.api.cached(u):
                w = await self.api.web(u)  # free classification first
                if w.get("status") in ("not_found", "empty_page"):
                    self.types[key] = ("not_found", "")
                elif w.get("kind") == "user_or_bot":
                    self.types[key] = ("user_or_bot", "")
                elif w.get("kind") in ("channel", "channel_no_preview"):
                    self.types[key] = ("channel", w.get("title") or "")  # audited later from the queue
                elif new_resolves >= self.api.max_new_resolves_per_channel:
                    self.types.setdefault(key, None)
                    checked += 1
                    append(OUT / "channel_links.csv", LINK_COLS, {
                        "channel": name, "target": u, "found_in": where, "target_type": w.get("kind") or "unknown",
                        "target_title": w.get("title") or "", "note": "not resolved (per-channel cap)"})
                    self.types.pop(key, None)
                    continue
                else:
                    new_resolves += 1
            if key not in self.types:
                inp_u = await self.api.input_entity(u)
                if inp_u is None:
                    self.types[key] = ("not_found", "")
                elif isinstance(inp_u, InputPeerUser):
                    self.types[key] = ("user_or_bot", "")
                elif isinstance(inp_u, InputPeerChannel):
                    ent = await self.api.run(lambda: self.api.client.get_entity(inp_u))
                    self.types[key] = ("group" if ent.megagroup else "channel", ent.title)
                    if ent.megagroup:
                        await self.check_group(ent)
                else:
                    self.types[key] = ("other", "")
            checked += 1
            ttype, title = self.types[key]
            note = ""
            if ttype == "group":
                g = self.groups.get(key, {})
                note = "active" if str(g.get("active")) == "True" else "inactive"
                (active_groups if note == "active" else inactive_groups).append(u)
            append(OUT / "channel_links.csv", LINK_COLS, {
                "channel": name, "target": u, "found_in": where, "target_type": ttype,
                "target_title": title, "note": note})
            if ttype == "channel":
                self.add(self.q_linked, u, f"linked_from:@{name}")
        for l in sorted(invites):
            append(OUT / "channel_links.csv", LINK_COLS, {
                "channel": name, "target": l, "found_in": "invite", "target_type": "private_invite",
                "target_title": "", "note": "not opened"})

        if linked_active:
            active_groups.insert(0, row["linked_group"])
        row |= {"n_checked": checked, "public_groups_active": " ".join(active_groups),
                "public_groups_inactive": " ".join(inactive_groups)}
        if active_groups:
            verdict = "public_group_active"
        elif inactive_groups:
            verdict = "public_group_inactive"
        elif invites:
            verdict = "private_links_only"
        elif full.full_chat.linked_chat_id:
            verdict = "comments_only"
        else:
            verdict = "no_group"
        if verdict != "public_group_active" and checked < len(cands):
            verdict += "_unverified_rest"
        self.save(row | {"verdict": verdict})

        # similar channels suggested by Telegram
        try:
            rec = await self.api.run(lambda: self.api.client(GetChannelRecommendationsRequest(channel=ch)))
            for c in rec.chats:
                if isinstance(c, Channel) and c.broadcast and c.username:
                    self.add(self.q_rec, c.username, f"recommended_by:@{name}")
        except errors.RPCError:
            pass

    def save(self, row: dict) -> None:
        append(OUT / "channels_audit.csv", AUDIT_COLS, row)
        self.done.add(row["channel"].lower())
        self.verdicts[row.get("verdict", "?")] += 1
        extra = f" -> {row.get('public_groups_active')}" if row.get("verdict") == "public_group_active" else ""
        print(f"[{self.api.requests} req, {self.api.resolves} resolves] @{row['channel']} ({row['source'][:25]}): "
              f"{row.get('verdict')}{extra}", flush=True)


async def main_async(args) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "STOP").unlink(missing_ok=True)
    config = load_config()
    client = TelegramClient(str(session_path(config).with_suffix("")), config.api_id, config.api_hash)
    await client.connect()
    if not await client.is_user_authorized():
        raise SystemExit("Not logged in: run scripts/login.py first.")
    api = Api(client, args.delay, args.max_resolves, args.hours)
    aud = Auditor(api)
    aud.aggregators_first = args.aggregators_first
    api.max_new_resolves_per_channel = args.max_resolves_per_channel
    aud.load_master()
    aud.load_known()
    print(f"priority queue from master.csv: {len(aud.q_priority)}", flush=True)
    t0 = time.time()
    reason = ""
    try:
        idle = errors_in_row = 0
        while True:
            item = aud.next_item()
            if item is None:
                idle += 1
                if idle > 60:  # nothing new for ~10 min
                    reason = "queue empty"
                    break
                await asyncio.sleep(10)
                continue
            idle = 0
            try:
                await aud.audit(item)
            except Stop:
                raise
            except (errors.RPCError, ConnectionError, asyncio.TimeoutError) as e:
                errors_in_row += 1
                if errors_in_row >= 3:
                    reason = f"3 errors in a row ({type(e).__name__}): check the connection"
                    break
                aud.save({"channel": item["username"], "source": item["source"], "status": "error",
                          "verdict": "error", "error": type(e).__name__,
                          "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds")})
            else:
                errors_in_row = 0
            if len(aud.done) % 10 == 0:
                print(f"== {(time.time()-t0)/60:.0f} min | audited {sum(aud.verdicts.values())} | "
                      f"{dict(aud.verdicts)} | queue prio={len(aud.q_priority)} tgd={len(aud.q_tgd)} known={len(aud.q_known)} linked={len(aud.q_linked)} rec={len(aud.q_rec)}", flush=True)
    except Stop as e:
        reason = str(e)
    finally:
        await client.disconnect()
    print(f"\nDONE ({reason}): {api.requests} requests, {api.resolves} resolves, {api.web_requests} web checks, {api.floodwaits} short FloodWaits, "
          f"{(time.time()-t0)/60:.0f} min\nverdicts: {dict(aud.verdicts)}", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--delay", type=float, default=6.0, help="seconds before each request")
    ap.add_argument("--max-resolves", type=int, default=250, help="max uncached username lookups")
    ap.add_argument("--max-resolves-per-channel", type=int, default=8,
                    help="new username resolves spent on one channel's links")
    ap.add_argument("--aggregators-first", action="store_true",
                    help="known channels and their links before TGDataset candidates")
    ap.add_argument("--hours", type=float, default=8.0, help="hard time cap")
    asyncio.run(main_async(ap.parse_args()))


if __name__ == "__main__":
    main()

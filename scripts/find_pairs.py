"""Find public channels that advertise an active standalone public group.

Read-only, no joins: keyword search (contacts.Search), public channel info
and recent posts, public group info and recent history. Never sends, reacts
or clicks. Every API call goes through a throttle (delay + request budget +
time cap); stops everything at the first FloodWait.

A "real group" is a public supergroup (has @username) that is NOT the
comment/discussion group of a channel, with >= MIN_MSGS messages from
>= MIN_USERS distinct users in the last 7 days.

Outputs (data/interim/pairs/): chats.csv (every evaluated chat), pairs.csv
(channel -> real group). Prints only counts and public chat usernames.

Usage:
    python scripts/find_pairs.py --budget 400 --minutes 60
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from telethon import TelegramClient, errors
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.functions.contacts import SearchRequest
from telethon.tl.types import Channel, PeerUser

from peek_channel import TME_RE, extract_links
from src.utils.config import DATA_INTERIM, load_config, session_path

KEYWORDS = [
    "crypto signals", "crypto pump", "airdrop", "bitcoin trading", "altcoin gems",
    "binance futures", "crypto giveaway", "forex signals", "memecoin", "100x gems",
    "crypto chat", "crypto community", "trading group", "solana gems", "crypto investment",
]
MIN_MSGS, MIN_USERS = 20, 5
CHANNEL_ACTIVE_DAYS = 30
MAX_LINKS_PER_CHANNEL = 4
GROUP_HINT = re.compile(r"chat|group|talk|community|discuss|lounge|club", re.I)
CHAT_COLS = [
    "username", "title", "kind", "participants", "scam", "fake", "verified",
    "linked_chat_id", "last_date", "msgs_7d", "users_7d", "real_group", "found_via", "note",
]
PAIR_COLS = [
    "channel", "channel_title", "channel_subs", "channel_last_post", "channel_scam",
    "group", "group_title", "group_members", "group_msgs_7d", "group_users_7d",
    "group_scam", "link_source",
]


class Budget(Exception):
    pass


class Throttle:
    """Sleeps before every request, counts them, enforces budget and time cap."""

    def __init__(self, client, delay: float, budget: int, minutes: float):
        self.client, self.delay, self.budget = client, delay, budget
        self.deadline = time.time() + minutes * 60
        self.used = 0

    async def wait(self, delay: float | None = None) -> None:
        if self.used >= self.budget or time.time() > self.deadline:
            raise Budget()
        await asyncio.sleep(self.delay if delay is None else delay)
        self.used += 1

    async def __call__(self, request, delay: float | None = None):
        await self.wait(delay)
        return await self.client(request)


def link_usernames(text_links: list[str]) -> list[str]:
    """Public usernames from t.me link paths (drop invites, post ids, bots)."""
    out = []
    for path in text_links:
        name = path.split("/")[0]
        if name.startswith("+") or name in ("joinchat", "c", "s", "addlist", "share", "proxy", "iv"):
            continue
        if name.endswith("bot") or len(name) < 5:
            continue
        out.append(name)
    return out


MENTION_RE = re.compile(r"(?<![\w/])@([A-Za-z][A-Za-z0-9_]{4,31})(?![\w])")  # usernames are ASCII


def mentions(text: str) -> list[str]:
    """@usernames written in text (groups are often cited this way, not as links)."""
    return [u for u in MENTION_RE.findall(text) if not u.lower().endswith("bot")]


async def recent_activity(t: Throttle, entity, limit: int = 100) -> tuple[int, int, str]:
    await t.wait()
    msgs = [m async for m in t.client.iter_messages(entity, limit=limit)]
    since = datetime.now(timezone.utc) - timedelta(days=7)
    recent = [m for m in msgs if m.date >= since and m.action is None]
    users = {m.from_id.user_id for m in recent if isinstance(m.from_id, PeerUser)}
    last = msgs[0].date.date().isoformat() if msgs else ""
    return len(recent), len(users), last


async def evaluate_group(t: Throttle, ent: Channel, found_via: str, chats: dict) -> dict:
    key = ent.username.lower()
    if key in chats:
        return chats[key]
    full = await t(GetFullChannelRequest(ent))
    row = {
        "username": ent.username, "title": ent.title, "kind": "group",
        "participants": full.full_chat.participants_count, "scam": ent.scam, "fake": ent.fake,
        "verified": ent.verified, "linked_chat_id": full.full_chat.linked_chat_id or "",
        "found_via": found_via, "note": "",
    }
    if full.full_chat.linked_chat_id:
        row |= {"real_group": False, "note": "discussion group of a channel"}
    else:
        try:
            n, u, last = await recent_activity(t, ent)
            row |= {"msgs_7d": n, "users_7d": u, "last_date": last,
                    "real_group": n >= MIN_MSGS and u >= MIN_USERS}
        except errors.RPCError as e:
            row |= {"real_group": False, "note": f"history not readable: {type(e).__name__}"}
    row["_about_links"] = link_usernames(TME_RE.findall(full.full_chat.about or ""))
    chats[key] = row
    return row


async def resolve(t: Throttle, username: str, cache: dict):
    key = username.lower()
    if key not in cache:
        await t.wait()
        try:
            cache[key] = await t.client.get_entity(username)
        except (ValueError, errors.UsernameInvalidError, errors.UsernameNotOccupiedError, errors.ChannelPrivateError):
            cache[key] = None
    return cache[key]


async def process_channel(t: Throttle, ch: Channel, found_via: str, chats: dict, cache: dict, pairs: list) -> None:
    key = ch.username.lower()
    if key in chats:
        return
    full = await t(GetFullChannelRequest(ch))
    row = {
        "username": ch.username, "title": ch.title, "kind": "channel",
        "participants": full.full_chat.participants_count, "scam": ch.scam, "fake": ch.fake,
        "verified": ch.verified, "linked_chat_id": full.full_chat.linked_chat_id or "",
        "found_via": found_via, "note": "",
    }
    chats[key] = row
    await t.wait()
    posts = [m async for m in t.client.iter_messages(ch, limit=50)]
    row["last_date"] = posts[0].date.date().isoformat() if posts else ""
    if not posts or posts[0].date < datetime.now(timezone.utc) - timedelta(days=CHANNEL_ACTIVE_DAYS):
        row["note"] = "inactive channel"
        return

    # Candidate group links: description first, then posts; group-ish names first.
    about = [(u, "about") for u in link_usernames(TME_RE.findall(full.full_chat.about or ""))]
    about += [(u, "about") for u in mentions(full.full_chat.about or "")]
    in_posts = []
    for m in posts:
        for links in extract_links(m).values():
            in_posts += [(u, "post") for u in link_usernames(links)]
        in_posts += [(u, "post") for u in mentions(m.message or "")]
    seen, cands = {key}, []
    for u, src in about + in_posts:
        if u.lower() not in seen:
            seen.add(u.lower())
            cands.append((u, src))
    cands.sort(key=lambda x: (x[1] != "about", not GROUP_HINT.search(x[0])))
    row["note"] = f"{len(cands)} linked usernames"

    for u, src in cands[:MAX_LINKS_PER_CHANNEL]:
        ent = await resolve(t, u, cache)
        if not isinstance(ent, Channel) or not ent.megagroup or not ent.username:
            continue
        g = await evaluate_group(t, ent, f"link from @{ch.username}", chats)
        if g.get("real_group"):
            pairs.append({
                "channel": ch.username, "channel_title": ch.title, "channel_subs": row["participants"],
                "channel_last_post": row["last_date"], "channel_scam": ch.scam,
                "group": g["username"], "group_title": g["title"], "group_members": g["participants"],
                "group_msgs_7d": g["msgs_7d"], "group_users_7d": g["users_7d"], "group_scam": g["scam"],
                "link_source": src,
            })
            print(f"  PAIR @{ch.username} -> @{g['username']} ({g['msgs_7d']} msgs/{g['users_7d']} users in 7d)", flush=True)


def write_outputs(out_dir: Path, chats: dict, pairs: list) -> None:
    with open(out_dir / "chats.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=CHAT_COLS, extrasaction="ignore")
        w.writeheader()
        w.writerows(chats.values())
    with open(out_dir / "pairs.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=PAIR_COLS)
        w.writeheader()
        w.writerows(pairs)


async def main_async(args) -> None:
    base = DATA_INTERIM / "pairs"
    out_dir = base / args.tag if args.tag else base
    out_dir.mkdir(parents=True, exist_ok=True)
    # Chats already evaluated in earlier runs are skipped.
    done = set()
    for f in base.glob("**/chats.csv"):
        if f.parent != out_dir:
            with open(f, newline="", encoding="utf-8") as fh:
                done |= {r["username"].lower() for r in csv.DictReader(fh) if r.get("username")}
    keywords = [k.strip() for k in args.keywords.split(",")] if args.keywords else KEYWORDS
    print(f"{len(done)} chats already evaluated in earlier runs; {len(keywords)} keywords")
    config = load_config()
    client = TelegramClient(str(session_path(config).with_suffix("")), config.api_id, config.api_hash)
    await client.connect()
    if not await client.is_user_authorized():
        raise SystemExit("Not logged in: run scripts/login.py first.")
    t = Throttle(client, args.delay, args.budget, args.minutes)
    chats, cache, pairs, found = {}, {}, [], {}
    stop = ""
    t0 = time.time()
    try:
        # 1) keyword search
        for kw in keywords:
            res = await t(SearchRequest(q=kw, limit=30), delay=args.search_delay)
            new = 0
            for c in res.chats:
                if isinstance(c, Channel) and c.username and c.username.lower() not in found \
                        and c.username.lower() not in done:
                    found[c.username.lower()] = (c, kw)
                    new += 1
            print(f"[{t.used:3d} req] search {kw!r}: +{new} (total {len(found)})", flush=True)

        # 2) groups found directly, then channels (bigger first)
        items = sorted(found.values(), key=lambda x: (not x[0].megagroup, -(x[0].participants_count or 0)))
        for i, (c, kw) in enumerate(items, 1):
            try:
                if c.megagroup:
                    g = await evaluate_group(t, c, f"search:{kw}", chats)
                    # a real group found by search: look for its parent channel in its description
                    if g.get("real_group"):
                        for u in g["_about_links"][:2]:
                            ent = await resolve(t, u, cache)
                            if isinstance(ent, Channel) and ent.broadcast and ent.username:
                                await process_channel(t, ent, f"about of @{c.username}", chats, cache, pairs)
                elif c.broadcast:
                    await process_channel(t, c, f"search:{kw}", chats, cache, pairs)
            except errors.FloodWaitError:
                raise
            except errors.RPCError as e:
                chats.setdefault(c.username.lower(), {"username": c.username, "title": c.title,
                                                      "kind": "?", "note": f"error {type(e).__name__}"})
            if i % 5 == 0:
                write_outputs(out_dir, chats, pairs)
                print(f"[{t.used:3d} req, {(time.time()-t0)/60:4.1f} min] {i}/{len(items)} chats, "
                      f"{sum(1 for r in chats.values() if r.get('real_group'))} real groups, {len(pairs)} pairs", flush=True)
    except errors.FloodWaitError as e:
        stop = f"FLOODWAIT {e.seconds}s — stopped. Log it in memory/collection-log.md."
    except Budget:
        stop = "budget/time cap reached"
    finally:
        write_outputs(out_dir, chats, pairs)
        await client.disconnect()
    real = [r for r in chats.values() if r.get("real_group")]
    print(f"\nDONE ({stop or 'all search results processed'}): {t.used} requests, {(time.time()-t0)/60:.1f} min")
    print(f"chats evaluated: {len(chats)} | real active groups: {len(real)} | channel->group pairs: {len(pairs)}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--budget", type=int, default=400, help="max API requests")
    ap.add_argument("--minutes", type=float, default=60)
    ap.add_argument("--delay", type=float, default=7.0, help="seconds before each request")
    ap.add_argument("--search-delay", type=float, default=30.0)
    ap.add_argument("--keywords", default="", help="comma-separated keywords (default: built-in list)")
    ap.add_argument("--tag", default="", help="output subfolder of data/interim/pairs/")
    asyncio.run(main_async(ap.parse_args()))


if __name__ == "__main__":
    main()

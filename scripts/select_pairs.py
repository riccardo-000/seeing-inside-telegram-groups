"""Pick the channel -> group pairs that pass the selection rules. Offline (no Telegram).

Reads the audit evidence in data/interim/<topic>/audit/ (channels_audit.csv,
channel_links.csv, groups.csv, group_about.csv) plus the seed topics, and gives
every channel with a candidate group one row with an outcome and the reason:

  valida          passes every rule: check a sample by hand
  da_controllare  passes the numbers but one point needs a human (see `motivo`)
  esclusa         fails a rule (see `motivo`)

Rules (memory/decisions.md, 2026-10-17 crypto list, 2026-10-18 conspiracy):
  - the group has a public username (2026-10-18: a linked chat without one cannot
    be opened or checked from outside);
  - the group is the channel's own: its linked discussion chat, or a group named in the channel description that cites the
    channel back in its own description or has a matching name. A group only in
    the description, without either, is `da_controllare`. Groups found only in
    posts are not candidates (ads, shared hubs).
  - group active: >= MIN_MSGS messages from >= MIN_USERS users in the last 7 days,
    bots excluded, and bot messages < MAX_BOT_SHARE of all messages;
  - channel: >= --min-subs subscribers, posts in the last 30 days;
  - one group per channel and one channel per group: a group claimed by several
    channels goes to the channel it is linked to; otherwise `da_controllare`;
  - topic (conspiracy): US/World news or not a TGDataset seed -> `da_controllare`.

Output: data/interim/<topic>/pairs/candidate_pairs.csv, best first (valida, then
da_controllare, then esclusa). Columns final/riccardo/marco/simone/note are for the
manual check, as in the review files.

Usage:
    python scripts/select_pairs.py --topic conspiracy --min-subs 2000
    python scripts/select_pairs.py --topic crypto --min-subs 1000 --out /tmp/check.csv
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.utils.config import add_topic_arg, paths

csv.field_size_limit(sys.maxsize)

MIN_MSGS, MIN_USERS = 10, 5
MAX_BOT_SHARE = 0.5
OWN_LINKS = ("linked_chat", "description")
CHECK_TOPICS = {"US news", "World news"}
NOISE = re.compile(r"(official|channel|chat|group|community|talk|discussion|public|english|news|the)")
COLS = ["esito", "motivo", "final", "channel", "group", "topic", "riccardo", "marco", "simone", "note",
        "how_found", "channel_title", "group_title", "channel_subs", "channel_last_post", "group_members",
        "group_msgs_7d", "group_users_7d", "bot_share", "group_checked_at", "altri_gruppi",
        "link_channel", "link_group"]
ORDER = {"valida": 0, "da_controllare": 1, "esclusa": 2}


def read(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def num(x) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def tokens(name: str) -> set[str]:
    return {t for t in re.split(r"[^a-z0-9]+", NOISE.sub(" ", name.lower())) if len(t) >= 4}


def cites(about: str, channel: str) -> bool:
    a = about.lower()
    return f"@{channel.lower()}" in a or f"t.me/{channel.lower()}" in a


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_topic_arg(ap)
    ap.add_argument("--min-subs", type=int, default=2000, help="minimum channel subscribers")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    p = paths(args.topic)
    out = args.out or p.pairs / "candidate_pairs.csv"

    channels = {r["channel"].lower(): r for r in read(p.audit / "channels_audit.csv")}  # last audit wins
    groups = {r["group"].lower(): r for r in read(p.audit / "groups.csv")}
    about = {r["group"].lower(): r["about"] for r in read(p.audit / "group_about.csv")}
    topics = {}
    for f in p.seeds.glob("seeds_*.csv"):
        for r in read(f):
            topics.setdefault(r["username"].lower(), r.get("topic") or "")

    # candidate edges: linked chat or description link to a group
    edges: dict[tuple[str, str], set[str]] = {}
    for r in read(p.audit / "channel_links.csv"):
        if r["target_type"] == "group" and r["found_in"] in OWN_LINKS:
            edges.setdefault((r["channel"].lower(), r["target"].lower()), set()).add(r["found_in"])
    for g, r in groups.items():  # group audited before its channel: the link is only in groups.csv
        parent = (r.get("is_linked_to") or "").lower()
        if parent in channels:
            edges.setdefault((parent, g), set()).add("linked_chat")
    linked_owner = {g: c for (c, g), how in edges.items() if "linked_chat" in how}
    claimants: dict[str, set[str]] = {}
    for c, g in edges:
        claimants.setdefault(g, set()).add(c)

    rows = []
    for (c, g), how in edges.items():
        ch, gr = channels.get(c, {}), groups.get(g, {})
        name_c, name_g = ch.get("channel") or c, gr.get("group") or g
        msgs, users, bots = num(gr.get("msgs_7d")), num(gr.get("users_7d")), num(gr.get("bot_msgs_7d"))
        bot_share = bots / (msgs + bots) if msgs + bots else 0.0
        topic = topics.get(c)
        no_username = name_g.startswith("id") and name_g[2:].isdigit()
        out_reasons, check_reasons = [], []

        if num(ch.get("subscribers")) < args.min_subs:
            out_reasons.append(f"canale < {args.min_subs} iscritti")
        if not num(ch.get("posts_30d")):
            out_reasons.append("canale senza post negli ultimi 30 giorni")
        if msgs < MIN_MSGS or users < MIN_USERS:
            out_reasons.append(f"gruppo poco attivo ({msgs:.0f} msg, {users:.0f} utenti in 7 g)")
        if no_username:
            out_reasons.append("gruppo senza username pubblico (non verificabile da fuori)")
        if bot_share >= MAX_BOT_SHARE:
            out_reasons.append(f"gruppo con {bot_share:.0%} di messaggi da bot")
        owner = linked_owner.get(g)
        if owner and owner != c:
            out_reasons.append(f"gruppo collegato a @{channels.get(owner, {}).get('channel', owner)}")
        elif not owner and len(claimants[g]) > 1:
            check_reasons.append("gruppo in descrizione di più canali: " +
                                 " ".join("@" + x for x in sorted(claimants[g]) if x != c))
        if "linked_chat" not in how:
            if cites(about.get(g, ""), name_c):
                how = how | {"group_cites_channel"}
            elif tokens(name_c) & tokens(name_g) or tokens(ch.get("title", "")) & tokens(gr.get("title", "")):
                how = how | {"same_name"}
            else:
                check_reasons.append("gruppo solo nella descrizione del canale: verificare che sia suo")
        if ch.get("error"):
            check_reasons.append(ch["error"])
        if args.topic == "conspiracy":
            if topic is None:
                check_reasons.append("non è un seed TGDataset: verificare il tema")
            elif not topic:
                check_reasons.append("tema non etichettato in TGDataset: verificare che sia in ambito")
            elif topic in CHECK_TOPICS:
                check_reasons.append(f"tema {topic}: verificare che sia complottista")

        esito = "esclusa" if out_reasons else "da_controllare" if check_reasons else "valida"
        rows.append({
            "esito": esito, "motivo": "; ".join(out_reasons or check_reasons),
            "channel": "@" + name_c, "group": "@" + name_g, "topic": topic or "",
            "how_found": " ".join(sorted(how)), "channel_title": ch.get("title", ""),
            "group_title": gr.get("title", ""), "channel_subs": ch.get("subscribers", ""),
            "channel_last_post": ch.get("last_post", ""), "group_members": gr.get("members", ""),
            "group_msgs_7d": gr.get("msgs_7d", ""), "group_users_7d": gr.get("users_7d", ""),
            "bot_share": f"{bot_share:.2f}", "group_checked_at": (gr.get("checked_at") or "")[:10],
            "link_channel": f"https://t.me/s/{name_c}",
            "link_group": "" if no_username else f"https://t.me/{name_g}",
            "_linked": "linked_chat" in how, "_users": users,
        })

    # one group per channel: best outcome, then linked chat, then most active users
    rows.sort(key=lambda r: (r["channel"].lower(), ORDER[r["esito"]], not r["_linked"], -r["_users"]))
    best, others = {}, {}
    for r in rows:
        k = r["channel"].lower()
        if k in best:
            if r["esito"] != "esclusa":
                others.setdefault(k, []).append(r["group"])
        else:
            best[k] = r
    # one channel per group among the kept rows
    taken: dict[str, str] = {}
    for r in sorted(best.values(), key=lambda r: (ORDER[r["esito"]], not r["_linked"], -r["_users"])):
        g = r["group"].lower()
        if r["esito"] != "esclusa" and g in taken:
            r["esito"], r["motivo"] = "esclusa", f"gruppo già assegnato a {taken[g]}"
        elif r["esito"] != "esclusa":
            taken[g] = r["channel"]
    final = sorted(best.values(), key=lambda r: (ORDER[r["esito"]], r["motivo"], -num(r["channel_subs"])))
    for r in final:
        r["altri_gruppi"] = " ".join(others.get(r["channel"].lower(), []))

    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS, extrasaction="ignore")
        w.writeheader()
        w.writerows(final)
    counts = {e: sum(r["esito"] == e for r in final) for e in ORDER}
    print(f"{out}: {len(final)} channels with a candidate group -> {counts}")


if __name__ == "__main__":
    main()

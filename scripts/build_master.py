"""Merge every channel/group we know into one file: data/interim/master.csv.

Offline (no Telegram). One row per channel <-> group link; channels with no
group and groups with no known channel get a row with the other side empty.

Inputs (all optional):
    data/interim/pairs/active_channels.csv  manual review (manual_* columns)
    data/interim/pairs/chats.csv            keyword search run (find_pairs.py)
    data/interim/audit/channels_audit.csv   full channel audit (audit_channels.py)
    data/interim/audit/groups.csv           group activity checks
    data/interim/audit/channel_links.csv    channel -> linked usernames

Manual columns already present in master.csv are preserved, so the file can
be rebuilt after new runs without losing hand-written notes.

Usage:
    python scripts/build_master.py
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.utils.config import DATA_INTERIM

OUT = DATA_INTERIM / "master.csv"
MANUAL = ["manual_group", "manual_scam_signals", "checked_by", "notes"]
COLS = [
    "channel", "channel_title", "channel_subs", "channel_last_post", "channel_status",
    "group", "group_title", "group_members", "group_msgs_7d", "group_users_7d",
    "group_free_msgs_7d", "group_type", "group_active", "how_found", "verified_by",
] + MANUAL


def read(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8-sig") as fh:  # -sig: files saved by Excel/Numbers
        return list(csv.DictReader(fh))


def norm(name: str) -> str:
    """'@X', 't.me/X', 'https://t.me/X' -> 'x'; private invites keep their path."""
    name = (name or "").strip()
    name = re.sub(r"^(https?://)?(t\.me|telegram\.me)/", "", name, flags=re.I).lstrip("@")
    return name.split("?")[0].rstrip("/").lower()


def is_private(name: str) -> bool:
    return name.startswith("+") or name.startswith("joinchat")


def main() -> None:
    active = read(DATA_INTERIM / "pairs" / "active_channels.csv")
    chats = read(DATA_INTERIM / "pairs" / "chats.csv")
    audit = read(DATA_INTERIM / "audit" / "channels_audit.csv")
    groups_rows = read(DATA_INTERIM / "audit" / "groups.csv")
    links = read(DATA_INTERIM / "audit" / "channel_links.csv")
    previous = {(r["channel"].lower(), r["group"].lower()): r for r in read(OUT)}

    display: dict[str, str] = {}  # lowercase -> original spelling

    def key(name: str) -> str:
        k = norm(name)
        if k:  # invite hashes are case-sensitive: keep the original spelling for display
            display.setdefault(k, norm_keep_case(name))
        return k

    def norm_keep_case(name: str) -> str:
        n = re.sub(r"^(https?://)?(t\.me|telegram\.me)/", "", (name or "").strip(), flags=re.I).lstrip("@")
        return n.split("?")[0].rstrip("/")

    # ---- channels
    channels: dict[str, dict] = {}
    for r in chats:
        if r["kind"] == "channel":
            status = "inactive" if r["note"] == "inactive channel" else "active"
            channels[key(r["username"])] = {"channel_title": r["title"], "channel_subs": r["participants"],
                                            "channel_last_post": r["last_date"], "channel_status": status}
    for r in audit:  # audit is more thorough: overrides
        if r["verdict"] in ("not_a_channel", "error"):
            continue
        status = {"dead": "dead", "inactive": "inactive"}.get(r["verdict"], "active")
        channels[key(r["channel"])] = {"channel_title": r["title"], "channel_subs": r["subscribers"],
                                       "channel_last_post": r["last_post"], "channel_status": status}
    manual = {key(r["channel"]): {"manual_group": r.get("manual_real_group", ""),
                                  "manual_scam_signals": r.get("manual_scam_signals", ""),
                                  "checked_by": r.get("checked_by", ""), "notes": r.get("notes", "")}
              for r in active}
    for k in manual:
        channels.setdefault(k, {"channel_status": "active"})

    # ---- groups
    groups: dict[str, dict] = {}
    for r in chats:
        if r["kind"] == "group":
            linked = bool(r.get("linked_chat_id"))
            groups[key(r["username"])] = {
                "group_title": r["title"], "group_members": r["participants"],
                "group_msgs_7d": r.get("msgs_7d", ""), "group_users_7d": r.get("users_7d", ""),
                "group_active": r.get("real_group") if not linked else "",
                "_linked_to": "?" if linked else ""}
    for r in groups_rows:
        linked_to = r["is_linked_to"] if not r["is_linked_to"].lstrip("-").isdigit() else "?"
        groups[key(r["group"])] = {
            "group_title": r["title"], "group_members": r["members"], "group_msgs_7d": r["msgs_7d"],
            "group_users_7d": r["users_7d"], "group_free_msgs_7d": r["free_msgs_7d"],
            "group_active": r["active"], "_linked_to": norm(linked_to) if linked_to != "?" else "?"}
        if linked_to and linked_to != "?":
            channels.setdefault(key(linked_to), {"channel_status": "not_checked"})

    # ---- edges channel -> group
    edges: dict[tuple[str, str], dict] = {}

    def edge(ch: str, gr: str, how: str, by: str) -> None:
        e = edges.setdefault((ch, gr), {"how": set(), "by": set()})
        e["how"].add(how)
        e["by"].add(by)

    for g, info in groups.items():
        if info["_linked_to"] and info["_linked_to"] != "?":
            edge(info["_linked_to"], g, "linked_chat", "script")
    for r in links:
        if r["target_type"] in ("group", "private_invite"):
            edge(key(r["channel"]), key(r["target"]), r["found_in"], "script")
    for r in chats:
        via = r.get("found_via", "")
        if r["kind"] == "group" and via.startswith("link from @"):
            edge(key(via[len("link from @"):]), key(r["username"]), "post", "script")
        if r["kind"] == "channel" and via.startswith("about of @"):
            edge(key(r["username"]), key(via[len("about of @"):]), "description", "script")
    for ch, m in manual.items():
        cell = (m["manual_group"] or "").strip()
        # free text like "PREMIUM GROUP" is kept in manual_group but not turned into links
        if " " in cell and "t.me/" not in cell and "@" not in cell:
            continue
        for token in re.split(r"[\s,;]+", cell):
            if not token:
                continue
            if token.upper() == "MANY":
                continue  # kept in manual_group; the script lists them
            g = key(token)
            if g and g != ch:
                edge(ch, g, "manual", "manual")

    # ---- rows
    rows = []
    linked_channels = {c for c, _ in edges}
    linked_groups = {g for _, g in edges}

    def group_type(ch: str, g: str) -> str:
        if is_private(g):
            return "private"
        info = groups.get(g)
        if info is None:
            return "unverified"
        lt = info["_linked_to"]
        if lt == ch:
            return "community" if str(info.get("group_active")) == "True" else "comments_only"
        if lt == "?":
            return "comment_chat_of_a_channel"
        if lt:
            return f"community_of_@{display.get(lt, lt)}"
        return "standalone"

    def make(ch: str, g: str, how="", by="") -> dict:
        row = {"channel": ("@" + display.get(ch, ch)) if ch else "",
               "group": (("@" + display.get(g, g)) if not is_private(g) else "t.me/" + display.get(g, g)) if g else "",
               "how_found": how, "verified_by": by}
        row |= channels.get(ch, {}) if ch else {}
        if g:
            info = groups.get(g, {})
            row |= {k: v for k, v in info.items() if not k.startswith("_")}
            row["group_type"] = group_type(ch, g) if ch else ("standalone" if not info.get("_linked_to") else "comment_chat_of_a_channel")
            if row["group_type"] in ("private", "unverified"):
                row["group_active"] = ""
        row |= manual.get(ch, {})
        prev = previous.get((row["channel"].lower(), row["group"].lower()))
        if prev:  # keep hand-written notes from earlier versions of master.csv
            for c in MANUAL:
                if prev.get(c) and not row.get(c):
                    row[c] = prev[c]
        return row

    for (ch, g), e in edges.items():
        rows.append(make(ch, g, " ".join(sorted(e["how"])), "+".join(sorted(e["by"]))))
    for ch in channels:
        if ch not in linked_channels:
            rows.append(make(ch, ""))
    for g in groups:
        if g not in linked_groups:
            rows.append(make("", g, "search", "script"))

    order = {"active": 0, "not_checked": 1, "inactive": 2, "dead": 3}
    rows.sort(key=lambda r: (not r["channel"], order.get(r.get("channel_status", ""), 4),
                             str(r.get("group_active")) != "True", not r["group"],
                             -int(r.get("channel_subs") or 0)))
    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    pairs = [r for r in rows if r["channel"] and r["group"] and str(r.get("group_active")) == "True"
             and r.get("group_type") in ("community", "standalone")]
    print(f"{len(rows)} rows -> {OUT.relative_to(Path.cwd())}")
    print(f"channels: {len(channels)} | groups: {len(groups)} | channel-group links: {len(edges)}")
    print(f"channel + ACTIVE group (community or standalone): {len(pairs)} rows, "
          f"{len({r['channel'] for r in pairs})} channels")


if __name__ == "__main__":
    main()

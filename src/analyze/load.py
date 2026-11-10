"""Point 1 of the analysis plan: load the message dumps as one clean table.

Reads only the files already on disk (``data/raw/<topic>/messages/``): no Telegram access.
For every pair of the two final lists it joins three sources (messages, pair lists, admin
lists), assigns a role to every message and the observation window of every chat.
Nothing is deleted: every row keeps its flags and each analysis picks what it needs.
The column contract is in ``src/analyze/README.md``.

Usage::

    from src.analyze.load import iter_pairs, load_messages, chat_table

    for pair, df in iter_pairs("crypto"):      # one pair at a time (low memory)
        ...
    df = load_messages("conspiracy", text=False)   # all messages, without text
"""

from __future__ import annotations

import csv
import gzip
import json
from collections.abc import Iterator
from pathlib import Path

import pandas as pd

from src.utils.config import DATA_INTERIM, DATA_RAW, TOPICS

# Observation window (decisions 2026-10-28 and 2026-11-10): dumps start on 2026-07-30 UTC;
# all chats are cut at the same end, the first moment after which no regular dump stopped.
WINDOW_START = pd.Timestamp("2026-07-30T00:00:00Z")
COMMON_END = pd.Timestamp("2026-11-04T00:00:00Z")

# A chat's window is shortened when its dump starts late or stops early, i.e. when the
# silence before its first / after its last message is much longer than its usual gap
# between messages (decision 2026-11-10, "Observation windows from the data").
GAP_FACTOR = 50
MIN_SILENCE = pd.Timedelta(days=2)
MIN_MESSAGES_FOR_RULE = 200  # below this, long silences are normal: window not changed

# Groups that banned the research account: their dump stops at the ban (collection log).
BANNED = {"vigilantfoxchat", "fionarosediamondchatofficial", "thelightpaperdistribution",
          "greatreject_social"}

# Usernames saved under another file name (collection log, 2026-11-05).
FILE_ALIASES = {"demons": "gambledemons", "zeczcash": "3984096229"}

# Roles that make up the three voices of the analysis plan (point 6).
ADMIN_ROLES = ("creator", "admin", "anonymous_admin", "channel_reply")


def _norm(username: str) -> str:
    return str(username).strip().lstrip("@").lower()


def _channel_peer_id(chat_id: int) -> int:
    """``-100xxxxxxxxxx`` (chat id) → ``xxxxxxxxxx`` (id used as sender / forward source)."""
    return abs(int(chat_id)) - 1_000_000_000_000


def _find_file(topic: str, name: str) -> Path | None:
    """Dump file of ``name``; falls back to the other arm's folder (same public chat)."""
    name = FILE_ALIASES.get(name, name)
    for t in (topic, *[x for x in TOPICS if x != topic]):
        folder = DATA_RAW / t / "messages"
        for f in folder.glob("*.jsonl.gz"):
            if f.name[: -len(".jsonl.gz")].lower() == name:
                return f
    return None


def pairs(topic: str | None = None) -> pd.DataFrame:
    """The final pairs with their dump files.

    Conspiracy rows whose ``final`` is not ``valida`` (pairs moved to crypto, decision
    2026-11-10) are left out. ``has_data`` is False when a file is missing (group gone).
    """
    rows = []
    for t in ([topic] if topic else TOPICS):
        path = DATA_INTERIM / t / "pairs" / "final_pairs.csv"
        with open(path, newline="", encoding="utf-8-sig") as fh:
            for r in csv.DictReader(fh):
                if r.get("final", "valida").strip() not in ("", "valida"):
                    continue
                ch, gr = _norm(r["channel"]), _norm(r["group"])
                fc, fg = _find_file(t, ch), _find_file(t, gr)
                rows.append({"topic": t, "pair_id": f"{t}:{ch}", "channel": ch, "group": gr,
                             "channel_file": fc, "group_file": fg,
                             "has_data": fc is not None and fg is not None})
    return pd.DataFrame(rows)


def read_dump(path: Path) -> pd.DataFrame:
    """One dump file as a DataFrame, fields as written by ``src/collect/messages.py``."""
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        df = pd.DataFrame.from_records(json.loads(line) for line in fh)
    df["date"] = pd.to_datetime(df["date"], utc=True)
    return df


def read_admins(dump_path: Path) -> list[dict]:
    path = dump_path.with_name(dump_path.name.replace(".jsonl.gz", ".admins.json"))
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []


def chat_window(dates: pd.Series, chat: str) -> tuple[pd.Timestamp, pd.Timestamp, str]:
    """Observation window of one chat: (start, end, note).

    Default: WINDOW_START → COMMON_END. The start moves to the first message (the end to the
    last) when the silence before it (after it) exceeds both ``GAP_FACTOR`` × the chat's
    average gap and ``MIN_SILENCE``; banned groups end at their last message.
    """
    start, end, notes = WINDOW_START, COMMON_END, []
    d = dates[(dates >= WINDOW_START) & (dates < COMMON_END)]
    if d.empty:
        return start, end, "no messages in window"
    first, last = d.min(), d.max()
    if chat in BANNED:
        end = last
        notes.append("ends early: banned the research account")
    elif len(d) >= MIN_MESSAGES_FOR_RULE:
        gap = (last - first) / (len(d) - 1)
        limit = max(GAP_FACTOR * gap, MIN_SILENCE)
        if COMMON_END - last > limit:
            end = last
            notes.append("ends early: dump stopped before the common end")
    if len(d) >= MIN_MESSAGES_FOR_RULE:
        gap = (last - first) / (len(d) - 1)
        if first - WINDOW_START > max(GAP_FACTOR * gap, MIN_SILENCE):
            start = first
            notes.append("starts late: no history before the first message")
    return start, end, "; ".join(notes)


def _base_columns(df: pd.DataFrame, pair: pd.Series, side: str, chat: str) -> pd.DataFrame:
    text = df["text"].fillna("")
    out = pd.DataFrame({
        "topic": pair["topic"],
        "pair_id": pair["pair_id"],
        "side": side,
        "chat": chat,
        "chat_id": df["chat_id"],
        "msg_id": df["id"],
        "date": df["date"],
        "sender_kind": df["sender_kind"],
        "sender": df["sender"].astype("Int64"),
        "is_bot": df["sender_is_bot"].eq(True),
        "is_service": df["service"].notna(),
        "has_text": text.str.strip() != "",
        "n_chars": text.str.len(),
        "text": text,
        "reply_to": df["reply_to"].astype("Int64"),
        "thread_top": df["thread_top"].astype("Int64"),
        "is_forward": df["fwd_kind"] != "none",
        "fwd_kind": df["fwd_kind"],
        "fwd_from": df["fwd_from"].astype("Int64"),
        "media": df["media"],
        "urls": df["urls"],
        "tme": df["tme"],
        "views": df["views"].astype("Int64"),
        "forwards": df["forwards"].astype("Int64"),
        "n_replies": df["n_replies"].astype("Int64"),
        "post_author": df["post_author"],
    })
    return out


def _group_roles(g: pd.DataFrame, linked_id: int, admins: list[dict]) -> pd.Series:
    """Role of every message in a group (precedence as in README)."""
    creators = {a["user"] for a in admins if a.get("is_creator") and not a.get("is_bot")}
    admin_ids = {a["user"] for a in admins if not a.get("is_bot")}
    role = pd.Series("user", index=g.index, dtype="object")
    user = g["sender_kind"] == "user"
    role[user & g["sender"].isin(admin_ids)] = "admin"
    role[user & g["sender"].isin(creators)] = "creator"
    role[user & g["is_bot"]] = "bot"  # bots stay bots even when admin
    role[g["sender_kind"] == "none"] = "anonymous_admin"
    ch = g["sender_kind"] == "channel"
    role[ch] = "other_channel"
    linked = ch & (g["sender"] == linked_id)
    role[linked & g["reply_to"].isna()] = "channel_copy"
    role[linked & g["reply_to"].notna()] = "channel_reply"
    role[g["is_service"]] = "service"
    return role


def prepare_pair(pair: pd.Series, text: bool = True) -> pd.DataFrame:
    """Clean table of one pair: channel and group messages, one row per message."""
    c_raw, g_raw = read_dump(pair["channel_file"]), read_dump(pair["group_file"])
    linked_id = _channel_peer_id(c_raw["chat_id"].iloc[0])
    c = _base_columns(c_raw, pair, "channel", pair["channel"])
    g = _base_columns(g_raw, pair, "group", pair["group"])

    c["role"] = "channel"
    c.loc[c["is_service"], "role"] = "service"
    c["is_comment"] = False
    g["role"] = _group_roles(g, linked_id, read_admins(pair["group_file"]))
    copies = set(g.loc[g["role"] == "channel_copy", "msg_id"])
    g["is_comment"] = g["reply_to"].isin(copies) | g["thread_top"].isin(copies)

    df = pd.concat([c, g], ignore_index=True)
    df["voice"] = None
    df.loc[df["role"] == "channel", "voice"] = "channel"
    df.loc[df["role"].isin(ADMIN_ROLES), "voice"] = "admin"
    df.loc[df["role"] == "user", "voice"] = "user"

    df["in_window"] = False
    for side, chat in (("channel", pair["channel"]), ("group", pair["group"])):
        m = df["side"] == side
        start, end, _ = chat_window(df.loc[m, "date"], chat)
        df.loc[m, "in_window"] = (df.loc[m, "date"] >= start) & (df.loc[m, "date"] <= end) \
            & (df.loc[m, "date"] < COMMON_END)
    if not text:
        df = df.drop(columns=["text"])
    return df


def iter_pairs(topic: str | None = None, text: bool = True) -> Iterator[tuple[pd.Series, pd.DataFrame]]:
    """Yield ``(pair, messages)`` for every pair with data, one pair at a time."""
    for _, pair in pairs(topic).iterrows():
        if pair["has_data"]:
            yield pair, prepare_pair(pair, text=text)


def load_messages(topic: str | None = None, text: bool = False) -> pd.DataFrame:
    """All messages of ``topic`` (both arms if None). Without text by default (memory)."""
    return pd.concat([df for _, df in iter_pairs(topic, text=text)], ignore_index=True)


def chat_table(topic: str | None = None) -> pd.DataFrame:
    """One row per chat: window, counts per role, flags (basis of Table 1)."""
    rows = []
    for pair, df in iter_pairs(topic, text=False):
        for side, chat, path in (("channel", pair["channel"], pair["channel_file"]),
                                 ("group", pair["group"], pair["group_file"])):
            s = df[df["side"] == side]
            w = s[s["in_window"]]
            start, end, note = chat_window(s["date"], chat)
            row = {
                "topic": pair["topic"], "pair_id": pair["pair_id"], "side": side, "chat": chat,
                "file": f"{path.parent.parent.name}/{path.name}",
                "n_on_disk": len(s), "n_in_window": len(w),
                "first_message": s["date"].min(), "last_message": s["date"].max(),
                "window_start": start, "window_end": end,
                "window_days": round((end - start) / pd.Timedelta(days=1), 2),
                "window_note": note,
                "n_with_text": int(w["has_text"].sum()),
                "n_human": int(w["voice"].notna().sum()),
                "authors_human": int(w.loc[w["voice"].isin(["admin", "user"]), "sender"].nunique()),
            }
            for role in ("channel", "creator", "admin", "anonymous_admin", "channel_reply",
                         "channel_copy", "other_channel", "bot", "user", "service"):
                row[f"n_{role}"] = int((w["role"] == role).sum())
            if side == "group":
                admins = read_admins(path)
                row["admins_listed"] = len(admins)
                row["is_discussion_group"] = row["n_channel_copy"] > 0
                row["n_comment"] = int(w["is_comment"].sum())
            rows.append(row)
    return pd.DataFrame(rows)

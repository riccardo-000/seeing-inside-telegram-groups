"""Point 2 of the analysis plan: structural measures, channel vs group (pandas only).

Uses every message inside each chat's window (no sample). "Human" messages are those with a
``voice`` (channel posts on the channel side; admins and users in the group): bots, copies of
channel posts, other channels and service messages are left out, except where a measure counts
them on purpose (bot share). Definitions of the 9 measures: ``docs/analysis-plan.md`` §2 and
``src/analyze/README.md``.
"""

from __future__ import annotations

import math
import re
from urllib.parse import urlsplit

import pandas as pd

from src.analyze.load import chat_window, iter_pairs

_DOMAIN_RE = re.compile(r"^[a-z0-9-]+(\.[a-z0-9-]+)+$")
_TELEGRAM_HOSTS = {"t.me", "telegram.me", "telegram.dog"}
_SECOND_LEVEL = {"co", "com", "org", "net", "gov", "ac", "edu"}


def base_domain(url: str) -> str | None:
    """Registered domain of a URL, or None for fragments without one.

    Stored URLs can be truncated (Telegram counts offsets in UTF-16, so text after emoji is
    cut wrongly): '.youtube.com/@x' → youtube.com, '/planetactus' → None. The domain is reduced
    to its last two labels (three for e.g. co.uk), so subdomains of a site count as the site.
    """
    u = url.strip().split()[0] if url.strip() else ""
    u = u.lstrip(".")
    if not u:
        return None
    if "://" not in u:
        u = "http://" + u
    try:
        host = (urlsplit(u).hostname or "").lower()
    except ValueError:
        return None
    host = host.removeprefix("www.")
    if not _DOMAIN_RE.match(host) or host.replace(".", "").isdigit():  # no IP addresses
        return None
    labels = host.split(".")
    if len(labels) >= 3 and len(labels[-1]) == 2 and labels[-2] in _SECOND_LEVEL:
        return ".".join(labels[-3:])
    return ".".join(labels[-2:])


def link_targets(urls, tme) -> set[str]:
    """Where a message points: web domains, and Telegram chats as ``t.me/<name>``."""
    out = set()
    for p in tme if isinstance(tme, list) else []:
        out.add("t.me/" + p.split("/")[0])
    for u in urls if isinstance(urls, list) else []:
        d = base_domain(u)
        if d and d not in _TELEGRAM_HOSTS and d != "me":
            out.add(d)
    return out


def _share(mask: pd.Series) -> float:
    return float(mask.mean()) if len(mask) else math.nan


def _side_measures(h: pd.DataFrame, window_days: float) -> dict:
    """Measures computed the same way on both sides (1 and 2)."""
    return {
        "n_human": len(h),
        "msgs_per_day": len(h) / window_days if window_days > 0 else math.nan,
        "share_link": _share(h["urls"].map(lambda x: isinstance(x, list) and len(x) > 0)),
        "share_forward": _share(h["is_forward"]),
        "share_media": _share(h["media"].notna()),
        "share_no_text": _share(~h["has_text"]),
    }


def pair_measures(pair: pd.Series, df: pd.DataFrame) -> tuple[list[dict], dict]:
    """Per-chat rows (channel, group) and one per-pair row for one pair."""
    rows, sides = [], {}
    for side, chat in (("channel", pair["channel"]), ("group", pair["group"])):
        s = df[df["side"] == side]
        start, end, note = chat_window(s["date"], chat)
        days = (end - start) / pd.Timedelta(days=1)
        w = s[s["in_window"]]
        h = w[w["voice"].notna()]
        row = {"topic": pair["topic"], "pair_id": pair["pair_id"], "side": side, "chat": chat,
               "window_days": round(days, 2), "window_note": note, **_side_measures(h, days)}
        sides[side] = (s, w, h)
        rows.append(row)

    # group-only measures (3–8)
    s, w, h = sides["group"]
    g = rows[1]
    counts = h["sender"].dropna().value_counts()
    g["authors_human"] = len(counts)
    k = math.ceil(0.1 * len(counts))
    g["top10_authors_share"] = float(counts.iloc[:k].sum() / counts.sum()) if len(counts) else math.nan
    g["admin_share"] = _share(h["voice"] == "admin")
    chat_msgs = w[~w["role"].isin(["service", "channel_copy"])]  # everything said in the group
    g["bot_share"] = _share(chat_msgs["role"] == "bot")
    g["other_channel_share"] = _share(chat_msgs["role"] == "other_channel")
    copies = w[w["role"] == "channel_copy"]
    discussion = len(copies) > 0
    g["is_discussion_group"] = discussion
    g["comment_share"] = _share(h["is_comment"]) if discussion else math.nan
    commented = set(h["reply_to"].dropna()) | set(h["thread_top"].dropna())
    g["posts_commented_share"] = (float(copies["msg_id"].isin(commented).mean())
                                  if discussion else math.nan)
    # replies to another human (target looked up in the whole group file, also off-window)
    humans = s[s["voice"].isin(["admin", "user"])].set_index("msg_id")["sender"]
    target = h["reply_to"].map(humans) if len(h) else pd.Series(dtype="Int64")
    is_human_target = h["reply_to"].isin(humans.index)
    same_person = (target == h["sender"]).fillna(False).astype(bool)  # NA sender: not the same
    g["reply_to_other_share"] = _share(is_human_target & ~same_person)

    # links (9): group targets never seen in the channel
    _, _, hc = sides["channel"]
    known = {"t.me/" + pair["channel"], "t.me/" + pair["group"]}
    for urls, tme in zip(hc["urls"], hc["tme"]):
        known |= link_targets(urls, tme)
    group_targets = [link_targets(u, t) for u, t in zip(h["urls"], h["tme"])]
    with_links = [t for t in group_targets if t]
    all_targets = set().union(*with_links) if with_links else set()
    g["n_link_msgs"] = len(with_links)
    g["group_only_link_msg_share"] = (sum(bool(t - known) for t in with_links) / len(with_links)
                                      if with_links else math.nan)
    g["group_only_target_share"] = (len(all_targets - known) / len(all_targets)
                                    if all_targets else math.nan)

    c = rows[0]
    p = {"topic": pair["topic"], "pair_id": pair["pair_id"], "channel": pair["channel"],
         "group": pair["group"], "is_discussion_group": discussion,
         "admins_listed": int(df.attrs.get("admins_listed", -1)),
         "short_window": bool(c["window_note"] or g["window_note"])}
    for m in ("msgs_per_day", "share_link", "share_forward", "share_media", "share_no_text"):
        p[f"channel_{m}"], p[f"group_{m}"] = c[m], g[m]
        if m != "msgs_per_day":
            p[f"diff_{m}"] = g[m] - c[m]
    p["ratio_msgs_per_day"] = (g["msgs_per_day"] / c["msgs_per_day"]
                               if c["msgs_per_day"] else math.nan)
    for m in ("authors_human", "top10_authors_share", "admin_share", "bot_share",
              "other_channel_share", "comment_share", "posts_commented_share",
              "reply_to_other_share", "n_link_msgs", "group_only_link_msg_share",
              "group_only_target_share"):
        p[m] = g[m]
    return rows, p


def compute(topic: str | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(per-chat table, per-pair table) for ``topic`` (both arms if None)."""
    from src.analyze.load import read_admins

    chat_rows, pair_rows = [], []
    for pair, df in iter_pairs(topic, text=False):
        df.attrs["admins_listed"] = len(read_admins(pair["group_file"]))
        rows, p = pair_measures(pair, df)
        chat_rows += rows
        pair_rows.append(p)
    return pd.DataFrame(chat_rows), pd.DataFrame(pair_rows)

"""Rank TGDataset crypto candidates offline, so username resolves go to the best ones.

No Telegram. Reads data/interim/crypto/seeds/seeds_tgdataset_crypto_a*.csv (written by
seeds_tgdataset.py; can be rerun while the Zenodo streams are still going),
skips channels already audited, and scores each candidate on what TGDataset
(2021 - Jul 2022) says about it:

- recency of its last post in the dataset (stopped long before July 2022 -> likely dead)
- subscribers in 2022 (log scale)
- t.me links in its 2022 posts that look like a group ("chat", "group", "community"...)
- number of distinct t.me targets (aggregator-like channels)
- Telegram's scam flag in 2022 (kept: interesting, small bonus)

Output: data/interim/crypto/seeds/tgdataset_queue.csv, best first. audit_channels.py reads
TGDataset candidates in this order when the file exists.

Usage:
    python scripts/rank_tgdataset.py
"""

from __future__ import annotations

import csv
import math
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.utils.config import paths

csv.field_size_limit(sys.maxsize)  # t.me link lists of aggregator channels are huge

P = paths("crypto")  # crypto arm only: conspiracy seeds come from seeds_conspiracy.py
OUT = P.seeds / "tgdataset_queue.csv"
DATASET_END = date(2022, 7, 31)
GROUPISH = re.compile(r"chat|group|talk|community|discuss|lounge|club|official_?ru|_en$", re.I)
COLS = ["username", "channel_id", "score", "title", "n_subscribers_2022", "last_message_date",
        "months_before_end", "n_tme_targets", "groupish_links", "scam", "archive"]


def read(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8-sig")
    if not text.endswith("\n"):  # still being written
        text = text[: text.rfind("\n") + 1]
    return list(csv.DictReader(text.splitlines()))


def score(r: dict) -> tuple[float, dict]:
    try:
        last = date.fromisoformat(r["last_message_date"])
        months = (DATASET_END - last).days / 30.4
    except ValueError:
        months = 99.0
    subs = int(float(r.get("n_subscribers_2022") or 0))
    targets = [t.split("/")[0] for t in (r.get("tme_links") or "").split() if t and not t.startswith("+")]
    targets = sorted({t for t in targets if t.lower() != (r.get("username") or "").lower()
                      and t.lower() not in ("joinchat", "c", "s", "addlist", "share", "proxy")
                      and not t.lower().endswith("bot")})
    groupish = [t for t in targets if GROUPISH.search(t)]
    s = 0.0
    s += 3.0 if months <= 1 else 2.0 if months <= 3 else 1.0 if months <= 6 else -2.0  # alive in mid-2022?
    s += min(math.log10(subs + 1), 6) / 2                                               # 0 .. 3
    s += 2.0 if groupish else 0.0
    s += min(len(targets), 20) / 10                                                     # 0 .. 2 (aggregators)
    s += 0.5 if r.get("scam") == "True" else 0.0
    return round(s, 2), {"months_before_end": round(months, 1), "n_tme_targets": len(targets),
                         "groupish_links": " ".join(groupish[:10])}


def main() -> None:
    audited = set()
    audit = P.audit / "channels_audit.csv"
    if audit.exists():
        audited = {r["channel"].lower() for r in read(audit)}
    rows, seen = [], set()
    for f in sorted(P.seeds.glob("seeds_tgdataset_crypto_a*.csv")):
        for r in read(f):
            u = (r.get("username") or "").strip()
            if not u or u.lower() in seen or u.lower() in audited:
                continue
            seen.add(u.lower())
            s, extra = score(r)
            rows.append({"username": u, "channel_id": r["channel_id"], "score": s, "title": r["title"][:80],
                         "n_subscribers_2022": r["n_subscribers_2022"], "last_message_date": r["last_message_date"],
                         "scam": r["scam"], "archive": r["archive"], **extra})
    rows.sort(key=lambda r: -r["score"])
    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)
    alive_2022 = sum(1 for r in rows if r["months_before_end"] <= 3)
    grp = sum(1 for r in rows if r["groupish_links"])
    print(f"{len(rows)} candidates not yet audited -> {OUT}")
    print(f"posting in the last 3 months of TGDataset: {alive_2022} | with group-like links: {grp} | "
          f"both: {sum(1 for r in rows if r['months_before_end'] <= 3 and r['groupish_links'])}")
    print("top 15:")
    for r in rows[:15]:
        print(f"  {r['score']:5.2f}  @{r['username']:<28} subs {r['n_subscribers_2022']:>8}  last {r['last_message_date']}  "
              f"groups: {r['groupish_links'][:50]}")


if __name__ == "__main__":
    main()

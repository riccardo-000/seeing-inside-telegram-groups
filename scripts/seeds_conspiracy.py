"""Build the conspiracy seed candidate list. No Telegram, no Zenodo download.

TGDataset's ``labeled_data/conspiracy_channels.csv`` (Conspiracy Money Machine
paper) is the one labelled list on GitHub that already carries **usernames**,
so unlike the crypto seeds it needs no 9-21 GB archive stream. Cross it with
``ch_to_topic_mapping.csv`` (English topics) and ``sabmyk_network.csv`` to get
a topic label per channel, and order the candidates by how relevant the topic
is to the study (radicalisation / Covid / news before religion / unlabelled).

What this canNOT give (unlike the crypto queue): subscribers, last-post date or
t.me links -- those live only in the Zenodo JSON. Liveness therefore has to be
tested. Do that with ``scripts/prefilter_tme.py`` (public web preview, zero
username resolves) before spending any of the daily resolve budget.

Output: data/interim/conspiracy/seeds_conspiracy_candidates.csv, best-first.

Usage:
    python scripts/seeds_conspiracy.py
"""

from __future__ import annotations

import csv
import io
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.utils.config import DATA_INTERIM

BASE = "https://raw.githubusercontent.com/SystemsLab-Sapienza/TGDataset/main/labeled_data"
FILES = {
    "conspiracy": f"{BASE}/conspiracy_channels.csv",
    "topics": f"{BASE}/ch_to_topic_mapping.csv",
    "sabmyk": f"{BASE}/sabmyk_network.csv",
}
OUT = DATA_INTERIM / "conspiracy" / "seeds_conspiracy_candidates.csv"
COLS = ["username", "channel_id", "topic", "in_sabmyk", "priority", "source"]

# Lower is better. The study is about scams in conspiracy/malicious communities:
# radical and Covid/news channels are the ones the supervisor's brief points at.
TOPIC_PRIORITY = {
    "Extremists and radicals": 1,
    "Covid": 2,
    "US news": 3,
    "World news": 3,
    "Carding": 4,
    "Crypto": 5,          # conspiracy AND crypto: overlap with the crypto arm
    "Religion": 6,
    "": 9,                # not in the English topic mapping
}


def fetch(url: str) -> list[dict]:
    with urllib.request.urlopen(url, timeout=120) as resp:
        return list(csv.DictReader(io.StringIO(resp.read().decode("utf-8-sig"))))


def first_col(row: dict) -> str:
    return next(iter(row.values()), "").strip()


def main() -> None:
    consp = fetch(FILES["conspiracy"])
    topics = {r["ch_ID"].strip(): r["topic"].strip() for r in fetch(FILES["topics"])}
    sabmyk = {first_col(r) for r in fetch(FILES["sabmyk"])}
    print(f"{len(consp)} conspiracy channels, {len(topics)} English topic labels, "
          f"{len(sabmyk)} sabmyk ids")

    rows, seen = [], set()
    for r in consp:
        user, cid = r.get("username", "").strip().lstrip("@"), r.get("ch_id", "").strip()
        if not user or user.lower() in seen:
            continue
        seen.add(user.lower())
        topic = topics.get(cid, "")
        rows.append({
            "username": user,
            "channel_id": cid,
            "topic": topic,
            "in_sabmyk": cid in sabmyk,
            "priority": TOPIC_PRIORITY.get(topic, 7),
            "source": "tgdataset_conspiracy_list",
        })
    # sabmyk members first inside their priority band: a known network, useful as a case study
    rows.sort(key=lambda r: (r["priority"], not r["in_sabmyk"], r["username"].lower()))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)

    by_prio: dict[int, int] = {}
    for r in rows:
        by_prio[r["priority"]] = by_prio.get(r["priority"], 0) + 1
    print(f"wrote {len(rows)} candidates -> {OUT}")
    for p in sorted(by_prio):
        label = next((k for k, v in TOPIC_PRIORITY.items() if v == p), "other")
        print(f"  priority {p} ({label or 'unlabelled'}): {by_prio[p]}")


if __name__ == "__main__":
    main()

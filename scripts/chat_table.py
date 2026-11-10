"""Per-chat table of the analysis (point 1 of docs/analysis-plan.md). No Telegram.

Reads the dumps already on disk through src/analyze/load.py and writes
data/processed/chats.csv: one row per chat of the final pairs, with its observation
window, counts per role and flags. It is the basis of Table 1 (dataset overview) and
of the structural measures (point 2). Takes ~1 minute for both arms.

Usage:
    python scripts/chat_table.py                  # both arms
    python scripts/chat_table.py --topic crypto
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.analyze.load import chat_table, pairs
from src.utils.config import DATA_PROCESSED, TOPICS


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--topic", choices=(*TOPICS, "all"), default="all",
                    help="study arm, or all (default)")
    args = ap.parse_args()
    topic = None if args.topic == "all" else args.topic

    p = pairs(topic)
    missing = p[~p["has_data"]]
    for _, r in missing.iterrows():
        print(f"skipped (file missing): {r['pair_id']} channel={r['channel_file'] is not None} "
              f"group={r['group_file'] is not None}")
    table = chat_table(topic)
    out = DATA_PROCESSED / ("chats.csv" if topic is None else f"chats_{topic}.csv")
    out.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(out, index=False)

    for t, s in table.groupby("topic"):
        print(f"{t}: {s['pair_id'].nunique()} pairs, {s['n_on_disk'].sum():,} messages on disk, "
              f"{s['n_in_window'].sum():,} in window")
    short = table[table["window_note"] != ""]
    print(f"{len(short)} chats with a shortened window:")
    for _, r in short.iterrows():
        print(f"  {r['topic']:10} {r['chat']:32} {r['window_start']:%Y-%m-%d} → "
              f"{r['window_end']:%Y-%m-%d}  {r['window_note']}")
    print(f"-> {out}")


if __name__ == "__main__":
    main()

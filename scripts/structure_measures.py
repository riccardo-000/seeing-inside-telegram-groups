"""Structural measures, channel vs group (point 2 of docs/analysis-plan.md). No Telegram.

Writes data/processed/structure_chats.csv (one row per chat) and
data/processed/structure_pairs.csv (one row per pair: channel and group values, group −
channel differences, group-only measures). Uses every message in each chat's window.

Usage:
    python scripts/structure_measures.py                  # both arms
    python scripts/structure_measures.py --topic crypto
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.analyze.structure import compute
from src.utils.config import DATA_PROCESSED, TOPICS

SUMMARY = ["ratio_msgs_per_day", "diff_share_link", "diff_share_forward", "diff_share_media",
           "top10_authors_share", "admin_share", "bot_share", "comment_share",
           "posts_commented_share", "reply_to_other_share", "group_only_link_msg_share",
           "group_only_target_share"]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--topic", choices=(*TOPICS, "all"), default="all", help="study arm, or all (default)")
    args = ap.parse_args()
    topic = None if args.topic == "all" else args.topic

    chats, pairs = compute(topic)
    suffix = "" if topic is None else f"_{topic}"
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    chats.to_csv(DATA_PROCESSED / f"structure_chats{suffix}.csv", index=False)
    pairs.to_csv(DATA_PROCESSED / f"structure_pairs{suffix}.csv", index=False)

    print("median per pair (all pairs):")
    print(pairs.groupby("topic")[SUMMARY].median().T.round(3).to_string())
    print(f"-> {DATA_PROCESSED / f'structure_chats{suffix}.csv'}")
    print(f"-> {DATA_PROCESSED / f'structure_pairs{suffix}.csv'}")


if __name__ == "__main__":
    main()

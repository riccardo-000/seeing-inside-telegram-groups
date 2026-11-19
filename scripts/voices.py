"""Point 6 of docs/analysis-plan.md: channel vs admins vs users, both arms. No Telegram.

Writes:
  data/processed/voices_chats.csv    one row per pair × voice (channel, admin, user, bot,
                                     other_channel): counts and per-message rates
  data/processed/voices_pairs.csv    one row per pair: voices side by side, eligibility
                                     (admin >= 10 / 30 / 50 messages), differences
  data/processed/voices_summary.csv  per topic / threshold / measure: medians, paired
                                     median difference, bootstrap 95% CI, sign test

Usage:
    python scripts/voices.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.analyze.authors import compute, pair_table, summary
from src.utils.config import DATA_PROCESSED


def main() -> None:
    voices = compute()
    pairs = pair_table(voices)
    summ = summary(pairs)
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    for name, df in (("voices_chats", voices), ("voices_pairs", pairs), ("voices_summary", summ)):
        df.to_csv(DATA_PROCESSED / f"{name}.csv", index=False)
        print(f"-> {DATA_PROCESSED / name}.csv ({len(df)} rows)")


if __name__ == "__main__":
    main()

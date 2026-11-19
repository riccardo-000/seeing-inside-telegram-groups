"""Point 8 of docs/analysis-plan.md: robustness of the paired results of points 2 and 5a.

Reads the per-pair tables already in data/processed/ (run structure_measures.py and
invites_results.py first) and recomputes, per topic, the median group − channel difference
(ratio for messages per day) and how many pairs are positive, under these variants:
  all              every pair with data
  no_short_window  without pairs where either chat has a shortened window
  discussion_only  only linked discussion groups (channel copies present)
  no_largest_group without the pair with the largest group (human messages)
  no_top_invites   without the pair whose group has most invitations (5a is concentrated)

Writes data/processed/robustness.csv.

Usage:
    python scripts/robustness.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from src.utils.config import DATA_PROCESSED

MEASURES = {  # column in the merged table → label
    "ratio_msgs_per_day": "group / channel messages per day (ratio)",
    "diff_share_link": "share with link, group − channel",
    "diff_share_forward": "share forwarded, group − channel",
    "diff_share_media": "share with media, group − channel",
    "diff_invite_share": "invitations (no bots), group − channel",
    "diff_suspicious_share_low": "suspicious invitations low, group − channel",
    "diff_suspicious_share_high": "suspicious invitations high, group − channel",
}


def main() -> None:
    s = pd.read_csv(DATA_PROCESSED / "structure_pairs.csv")
    inv = pd.read_csv(DATA_PROCESSED / "invites_suspicious_pairs.csv")
    ic = pd.read_csv(DATA_PROCESSED / "invites_suspicious_chats.csv")
    chats = pd.read_csv(DATA_PROCESSED / "chats.csv")
    df = s.merge(inv.drop(columns="topic"), on="pair_id", how="left")
    size = chats[chats["side"] == "group"].set_index("pair_id")["n_human"]
    top_inv = ic[ic["side"] == "group"].set_index("pair_id")["n_invites"]
    df["group_human"] = df["pair_id"].map(size)
    df["group_invites"] = df["pair_id"].map(top_inv)

    rows = []
    for topic, t in df.groupby("topic"):
        variants = {
            "all": t,
            "no_short_window": t[~t["short_window"].astype(bool)],
            "discussion_only": t[t["is_discussion_group"].astype(bool)],
            "no_largest_group": t.drop(index=t["group_human"].idxmax()),
            "no_top_invites": t.drop(index=t["group_invites"].idxmax()),
        }
        for name, v in variants.items():
            for col, label in MEASURES.items():
                x = v[col].dropna()
                ref = 1.0 if col.startswith("ratio") else 0.0
                rows.append({"topic": topic, "variant": name, "measure": label, "n_pairs": len(x),
                             "median": x.median(), "n_group_higher": int((x > ref).sum()),
                             "n_group_lower": int((x < ref).sum())})
    out = pd.DataFrame(rows)
    out.to_csv(DATA_PROCESSED / "robustness.csv", index=False)
    show = out.assign(median=out["median"].map(lambda m: f"{m:.4g}"))
    for topic, t in show.groupby("topic"):
        print(f"\n== {topic}")
        print(t.pivot(index="measure", columns="variant", values="median")
              [["all", "no_short_window", "discussion_only", "no_largest_group", "no_top_invites"]].to_string())
    print(f"\n-> {DATA_PROCESSED / 'robustness.csv'}")


if __name__ == "__main__":
    main()

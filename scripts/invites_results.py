"""Final invitation results from the hand labels (point 5a of docs/analysis-plan.md). No Telegram.

Run after the two annotators have filled data/interim/invites/domains_to_label.csv and
validation_a.csv / validation_b.csv (it also runs on partial labels: missing ones are
reported). Rules in src/analyze/invite_labels.py.

Writes:
  data/processed/invites_suspicious_chats.csv  per chat: suspicious invitations, low/high range
  data/processed/invites_suspicious_pairs.csv  per pair: channel vs group
  data/processed/invites_quality.json          annotator agreement, detector precision/recall,
                                               suspicious-flag precision/recall
  data/interim/invites/validation_final.csv    items the two annotators disagree on: a third
                                               person fills is_invitation_final / suspicious_final
                                               (kept across runs), then run this again

Usage:
    python scripts/invites_results.py
    python scripts/invites_results.py --dir <folder with label files> --out <output folder>   # tests
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from src.analyze.invite_labels import (LABEL_DIR, detector_quality, domain_labels, suspicious_quality,
                                       suspicious_tables, validation_reference)
from src.analyze.invites import compute, validation_pool
from src.utils.config import DATA_PROCESSED


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", type=Path, default=LABEL_DIR, help="folder with the label files")
    ap.add_argument("--out", type=Path, default=DATA_PROCESSED, help="output folder")
    args = ap.parse_args()

    dom, dom_stats = domain_labels(args.dir)
    labels = {d: lab for d, lab in zip(dom["domain"], dom["final"]) if lab}
    all_domains = pd.read_csv(args.dir / "domains.csv")
    domain_class = dict(zip(all_domains.loc[all_domains["topic"] == "crypto", "domain"],
                            all_domains.loc[all_domains["topic"] == "crypto", "class"]))

    invites, chats, _ = compute()
    per_chat, per_pair = suspicious_tables(invites, chats, labels)
    args.out.mkdir(parents=True, exist_ok=True)
    per_chat.to_csv(args.out / "invites_suspicious_chats.csv", index=False)
    per_pair.to_csv(args.out / "invites_suspicious_pairs.csv", index=False)

    v, val_stats = validation_reference(args.dir)
    pool = validation_pool()
    v = v.merge(pool[["pair_id", "msg_id", "urls", "has_link"]], on=["pair_id", "msg_id"], how="left")
    quality = {"domains": dom_stats, "validation_agreement": val_stats,
               "detector": detector_quality(v, pool),
               "suspicious_flag": suspicious_quality(v, labels, domain_class),
               "note": "conspiracy has no hand-labelled domains: its 'high' range counts every "
                       "unknown domain as suspicious"}
    (args.out / "invites_quality.json").write_text(json.dumps(quality, indent=2, default=str))

    print(json.dumps(quality, indent=2, default=str))
    tot = per_chat.groupby(["topic", "side"])[["n_messages", "n_invites", "n_suspicious_low",
                                               "n_suspicious_high"]].sum()
    print("\nsuspicious invitations by arm and side:\n", tot.to_string())
    print("\nmedian per pair:\n", per_pair.groupby("topic")[
        ["channel_suspicious_share_low", "group_suspicious_share_low",
         "group_suspicious_share_high"]].median().round(5).T.to_string())
    print(f"\n-> {args.out / 'invites_suspicious_chats.csv'}\n-> {args.out / 'invites_suspicious_pairs.csv'}"
          f"\n-> {args.out / 'invites_quality.json'}\n-> {args.dir / 'validation_final.csv'}")


if __name__ == "__main__":
    main()

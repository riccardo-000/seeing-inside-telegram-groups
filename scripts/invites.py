"""Invitations to register on a platform (point 5a of docs/analysis-plan.md). No Telegram.

Runs the invitation detector of src/analyze/invites.py on every message in each chat's
window, both arms (crypto is the deep dive; conspiracy comes for free, for comparison).

Writes:
  data/processed/invites_chats.csv          one row per chat (counts, shares, who, where to)
  data/processed/invites_pairs.csv          one row per pair (channel vs group)
  data/interim/invites/domains.csv          every target domain: counts and automatic class
  data/interim/invites/domains_to_label.csv the most frequent crypto "unknown" domains, for two
                                            annotators (columns label_a / label_b)
  data/interim/invites/validation_a.csv, validation_b.csv
                                            the same crypto messages for two annotators (text
                                            only, blind); validation_key.csv links them back
Existing label / validation files are never overwritten (use --force to regenerate them).

Usage:
    python scripts/invites.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from src.analyze.invites import compute, domain_table, message_invite
from src.analyze.load import iter_pairs
from src.utils.config import DATA_INTERIM, DATA_PROCESSED

N_LABEL = 100           # crypto unknown domains to label by hand
SEED = 20261110
STRATA = {"detected": 60, "link_not_detected": 60, "random": 30}  # validation sample (crypto)


def validation_sample(invites: pd.DataFrame) -> pd.DataFrame:
    """Crypto messages for the hand check: detected / with a link but not detected / random."""
    pool = []
    for pair, df in iter_pairs("crypto", text=True):
        w = df[df["in_window"] & ~df["role"].isin(["service", "channel_copy"]) & df["has_text"]]
        w = w.sample(n=min(len(w), 400), random_state=SEED)  # cap per pair: no chat dominates
        pool.append(w[["pair_id", "side", "chat", "msg_id", "role", "voice", "urls", "text"]])
    pool = pd.concat(pool, ignore_index=True)
    pool["detected"] = [message_invite(u, t)[0] for u, t in zip(pool["urls"], pool["text"])]
    pool["has_link"] = pool["urls"].map(lambda x: isinstance(x, list) and len(x) > 0)
    pool = pool.drop_duplicates("text")
    parts = [
        pool[pool["detected"]].sample(n=STRATA["detected"], random_state=SEED).assign(stratum="detected"),
        pool[pool["has_link"] & ~pool["detected"]].sample(n=STRATA["link_not_detected"], random_state=SEED)
        .assign(stratum="link_not_detected"),
    ]
    rest = pool.drop(index=pd.concat(parts).index)
    parts.append(rest.sample(n=STRATA["random"], random_state=SEED).assign(stratum="random"))
    s = pd.concat(parts).sample(frac=1, random_state=SEED).reset_index(drop=True)
    s.insert(0, "item", [f"v{i:03d}" for i in range(1, len(s) + 1)])
    return s


def write_once(df: pd.DataFrame, path: Path, force: bool) -> None:
    if path.exists() and not force:
        print(f"kept (already exists, may hold labels): {path}")
        return
    df.to_csv(path, index=False)
    print(f"-> {path}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--force", action="store_true", help="regenerate the label and validation files")
    args = ap.parse_args()

    invites, chats, pairs = compute()
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    chats.to_csv(DATA_PROCESSED / "invites_chats.csv", index=False)
    pairs.to_csv(DATA_PROCESSED / "invites_pairs.csv", index=False)
    out = DATA_INTERIM / "invites"
    out.mkdir(parents=True, exist_ok=True)
    domains = domain_table(invites)
    domains.to_csv(out / "domains.csv", index=False)

    to_label = domains[(domains["topic"] == "crypto") & (domains["class"] == "unknown")].head(N_LABEL)
    to_label = to_label.drop(columns=["class", "n_pairs_official"]).assign(label_a="", label_b="",
                                                                           label_final="", notes="")
    write_once(to_label, out / "domains_to_label.csv", args.force)

    sample = validation_sample(invites)
    blind = sample[["item", "text"]].assign(is_invitation="", suspicious="", notes="")
    write_once(blind, out / "validation_a.csv", args.force)
    write_once(blind, out / "validation_b.csv", args.force)
    key = sample[["item", "stratum", "detected", "pair_id", "side", "chat", "msg_id", "role", "voice"]]
    write_once(key, out / "validation_key.csv", args.force)

    for t, c in chats.groupby("topic"):
        tot = c.groupby("side")[["n_messages", "n_invites", "n_hallmark"]].sum()
        print(f"\n{t}: invitations / messages by side\n{tot.assign(share=tot.n_invites / tot.n_messages).round(4)}")
        who = c[[col for col in c.columns if col.startswith("n_invites_by_")]].sum()
        to = c[[col for col in c.columns if col.startswith("n_invites_to_")]].sum()
        print("posted by:", who.to_dict())
        print("to class:", to.to_dict())
    print("\nmedian per pair:\n", pairs.groupby("topic")[["channel_invite_share", "group_invite_share",
                                                          "diff_invite_share", "group_hallmark_share",
                                                          "group_unknown_share"]].median().round(4).T)


if __name__ == "__main__":
    main()

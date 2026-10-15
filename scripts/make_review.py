"""Write the channel -> group pairs still to be checked by hand. Offline (no Telegram).

Takes every pair with an active group in data/interim/<topic>/master.csv
(community or standalone) that is neither in data/processed/pairs_reviewed.csv
nor in an earlier data/interim/<topic>/review/pairs_to_review_*.csv, and writes
it to a new review file. Earlier review files are never touched, so a teammate
can keep working on them.

The first 10 columns match pairs_reviewed.csv; `pair_type` is only the
script's guess, `flags` says why a row looks doubtful. See
data/interim/<topic>/review/README.md.

Usage:
    python scripts/make_review.py --topic crypto --suffix 2026-10-15
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.utils.config import DATA_PROCESSED, add_topic_arg, paths

COLS = ["final", "channel", "group", "pair_type", "channel_status", "script", "riccardo", "marco", "simone",
        "other_notes", "flags", "channel_subs", "group_members", "how_found", "link_channel", "link_group"]
BIG_GROUP = 50_000  # a standalone group this big is usually another project's, linked in an ad
NOISE = re.compile(r"(official|announcements?|ann|news|channel|chat|group|community|global|english|_en|en$)")


def tokens(name: str) -> set[str]:
    return {t for t in re.split(r"[^a-z0-9]+", NOISE.sub(" ", name.lower())) if len(t) >= 4}


def key(row: dict) -> tuple[str, str]:
    return row["channel"].lower().lstrip("@"), row["group"].lower().lstrip("@")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_topic_arg(ap)
    ap.add_argument("--suffix", required=True, help="output name: pairs_to_review_<suffix>.csv (e.g. the date)")
    args = ap.parse_args()
    p = paths(args.topic)
    rev_dir = p.interim / "review"
    out_path = rev_dir / f"pairs_to_review_{args.suffix}.csv"
    if out_path.exists():
        raise SystemExit(f"{out_path} already exists: pick another --suffix")

    done = set()
    for f in [DATA_PROCESSED / "pairs_reviewed.csv", *sorted(rev_dir.glob("pairs_to_review_*.csv"))]:
        if f.exists():
            with open(f, newline="", encoding="utf-8-sig") as fh:
                done |= {key(r) for r in csv.DictReader(fh)}

    with open(p.master, newline="", encoding="utf-8-sig") as fh:
        rows = [r for r in csv.DictReader(fh) if r["channel"] and r["group"] and r["group_active"] == "True"
                and r["group_type"] in ("community", "standalone")]
    shared = Counter(r["group"].lower() for r in rows)

    out = []
    for r in rows:
        if key(r) in done:
            continue
        ch, gr = r["channel"].lstrip("@"), r["group"].lstrip("@")
        community = r["group_type"] == "community"
        flags = ["chat collegata ufficialmente al canale" if community
                 else "gruppo linkato nei post/descrizione: verificare che sia del canale"]
        if shared[r["group"].lower()] > 1:
            flags.append(f"stesso gruppo linkato da {shared[r['group'].lower()]} canali: capire di chi è")
        if not community and int(r["group_members"] or 0) > BIG_GROUP:
            flags.append("gruppo molto grande di un altro progetto: probabile link pubblicitario")
        if gr.lower().startswith("id") and gr[2:].isdigit():
            flags.append("gruppo senza username pubblico")
        msgs = r["group_free_msgs_7d"] or r["group_msgs_7d"] or "?"
        out.append({c: "" for c in COLS} | {
            "channel": "@" + ch, "group": "@" + gr,
            "pair_type": "own_community" if community
                         else ("same_project_group" if tokens(ch) & tokens(gr) else "other_project"),
            "channel_status": r["channel_status"],
            "script": f"attivo ({r['group_users_7d'] or '?'} utenti, {msgs} msg {'liberi ' if community else ''}/7g)",
            "flags": "; ".join(flags), "channel_subs": r["channel_subs"], "group_members": r["group_members"],
            "how_found": r["how_found"], "link_channel": f"https://t.me/s/{ch}", "link_group": f"https://t.me/{gr}"})
    # community chats first, then by channel, so the work can be split in blocks
    out.sort(key=lambda x: (x["pair_type"] != "own_community", x["channel"].lower()))

    rev_dir.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS)
        w.writeheader()
        w.writerows(out)
    print(f"{args.topic}: {len(out)} rows, {len({x['channel'] for x in out})} channels -> {out_path}")


if __name__ == "__main__":
    main()

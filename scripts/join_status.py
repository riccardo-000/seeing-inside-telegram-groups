"""Join status of every final pair, and what is left to do by hand. No Telegram.

Reads data/interim/<topic>/pairs/final_pairs.csv and the latest row per chat of
data/interim/<topic>/joins/joins.csv (script joins, rechecks and manual joins
imported with ``join_chats.py --import-manual``). Writes
data/interim/<topic>/joins/join_status.csv: one row per pair, in file order,
with the group's latest status and a ``da_fare`` column for whoever joins by
hand. Refresh the join log first (``--recheck`` / ``--import-manual``), then
rerun this.

Usage:
    python scripts/join_status.py --topic crypto
    python scripts/join_status.py --topic conspiracy
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.utils.config import add_topic_arg, paths

# latest join status -> what to do by hand (decision 2026-10-29 on anti-bot buttons)
TODO = {
    "": "da fare: join del gruppo (link_group, 1 ogni 5 min)",
    "joined": "fatto",
    "already_member": "fatto",
    "restricted": "fatto (limitato: ok)",
    "needs_verification": "fatto (mutato: ok, leggiamo e riceviamo DM)",
    "removed": "da rifare a mano: join + bottone anti-bot se c'è",
    "join_request": "non fare: serve approvazione admin",
    "private": "sostituire la coppia (gruppo privato o sparito)",
    "not_found": "sostituire la coppia (gruppo non trovato)",
    "not_a_channel": "sostituire la coppia (non è un gruppo)",
    "failed": "da fare: join fallito, riprovare",
}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_topic_arg(ap)
    args = ap.parse_args()
    p = paths(args.topic)
    with open(p.pairs / "final_pairs.csv", newline="", encoding="utf-8-sig") as fh:
        pairs = list(csv.DictReader(fh))
    latest = {}
    log = p.interim / "joins" / "joins.csv"
    if log.exists():
        with open(log, newline="", encoding="utf-8") as fh:
            for r in sorted(csv.DictReader(fh), key=lambda r: (r["date_utc"], r["time_utc"])):
                latest[r["chat"].lower()] = r
    out = p.interim / "joins" / "join_status.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    fields = ["riga", "channel", "group", "link_group", "stato_join", "motivo", "join_utc",
              "canale_joinato", "da_fare"]
    counts = Counter()
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for i, pr in enumerate(pairs, start=2):  # 2 = first data row in a spreadsheet
            group = pr["group"].strip().lstrip("@")
            channel = pr["channel"].strip().lstrip("@")
            g = latest.get(group.lower(), {})
            status = g.get("status", "")
            todo = TODO.get(status, f"controllare ({status})")
            if status == "removed" and "not accessible" in g.get("reason", ""):
                todo = TODO["private"]  # the group itself is gone, not only our membership
            counts[todo] += 1
            w.writerow({
                "riga": i, "channel": pr["channel"], "group": pr["group"],
                "link_group": pr.get("link_group") or f"https://t.me/{group}",
                "stato_join": status, "motivo": g.get("reason", ""),
                "join_utc": f"{g['date_utc']} {g['time_utc']}" if g else "",
                # a channel joined by mistake: to leave by hand (we join groups only)
                "canale_joinato": "sì (da lasciare)" if channel.lower() in latest else "",
                "da_fare": todo,
            })
    print(f"{args.topic}: {len(pairs)} pairs -> {out}")
    for todo, n in counts.most_common():
        print(f"  {n:3}  {todo}")


if __name__ == "__main__":
    main()

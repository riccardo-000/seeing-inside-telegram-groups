"""Extract seed candidates for one TGDataset topic (default: Crypto).

Offline w.r.t. Telegram: reads the topic labels from GitHub and streams one
TGDataset archive from Zenodo. Nothing is written to disk except the output
CSV; the archive is parsed on the fly with ijson (constant memory).

Per candidate channel we keep only: id, username, title, description,
scam/verified flags, subscribers (as of 2022), number and date of the last
text message, and the t.me links found in message text.

Usage:
    python scripts/seeds_tgdataset.py --archive 4 --limit 25
"""

from __future__ import annotations

import argparse
import csv
import io
import re
import sys
import tarfile
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import ijson

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.utils.config import TOPICS, paths

TOPICS_URL = (
    "https://raw.githubusercontent.com/SystemsLab-Sapienza/TGDataset/main/"
    "labeled_data/ch_to_topic_mapping.csv"
)
ARCHIVE_URL = "https://zenodo.org/api/records/7640712/files/TGDataset_{n}.tar.gz/content"
META_FIELDS = {"username", "title", "description", "scam", "verified", "n_subscribers"}
TME_RE = re.compile(r"(?:https?://)?(?:t\.me|telegram\.me)/(\+?[\w\-]+(?:/[\w\-]+)?)", re.I)
COLUMNS = [
    "channel_id", "username", "title", "description", "scam", "verified",
    "n_subscribers_2022", "n_text_messages", "last_message_date", "n_tme_links",
    "tme_links", "topic", "source", "archive", "archive_member",
]


def load_topic_ids(topic: str) -> set[str]:
    """Return the channel ids labelled with ``topic`` in TGDataset (English only)."""
    with urllib.request.urlopen(TOPICS_URL, timeout=60) as resp:
        rows = csv.DictReader(io.TextIOWrapper(resp, encoding="utf-8"))
        return {r["ch_ID"].strip() for r in rows if r["topic"].strip().lower() == topic.lower()}


def as_bool(value) -> bool | None:
    """TGDataset stores flags as bools or as the strings "True"/"False"."""
    if value is None or value == "None":
        return None
    return value if isinstance(value, bool) else str(value) == "True"


def as_int(value) -> int | None:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def iter_candidates(json_stream, wanted: set[str]):
    """Yield one dict per wanted channel from a TGDataset JSON file.

    Uses low-level ijson events so a single huge channel never has to fit
    in memory; messages of non-wanted channels are skipped without storing.
    """
    current = None  # dict for the wanted channel being read, else None
    for prefix, event, value in ijson.parse(json_stream):
        if prefix == "" and event == "map_key":
            if current is not None:
                yield current
            current = {"channel_id": value, "links": set(), "n_msg": 0, "last": 0.0} if value in wanted else None
            continue
        if current is None:
            continue
        parts = prefix.split(".")
        # <id>.<field>
        if len(parts) == 2 and parts[1] in META_FIELDS and event in ("string", "number", "boolean", "null"):
            current[parts[1]] = value
        # <id>.text_messages.<msg_id>.message / .date
        elif len(parts) == 4 and parts[1] == "text_messages":
            if parts[3] == "message" and event == "string":
                current["n_msg"] += 1
                current["links"].update(m.lower() for m in TME_RE.findall(value))
            elif parts[3] == "date" and event in ("number", "string"):
                ts = as_int(value) or 0
                current["last"] = max(current["last"], ts)
    if current is not None:
        yield current


def to_row(c: dict, topic: str, archive: int, member: str) -> dict:
    links = sorted(c["links"])
    last = datetime.fromtimestamp(c["last"], tz=timezone.utc).date().isoformat() if c["last"] else ""
    return {
        "channel_id": c["channel_id"],
        "username": c.get("username") or "",
        "title": (c.get("title") or "").replace("\n", " "),
        "description": (c.get("description") or "").replace("\n", " ")[:500],
        "scam": as_bool(c.get("scam")),
        "verified": as_bool(c.get("verified")),
        "n_subscribers_2022": as_int(c.get("n_subscribers")),
        "n_text_messages": c["n_msg"],
        "last_message_date": last,
        "n_tme_links": len(links),
        "tme_links": " ".join(links),
        "topic": topic,
        "source": "tgdataset",
        "archive": archive,
        "archive_member": member,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--topic", default="Crypto", help="TGDataset topic label (not the study arm)")
    ap.add_argument("--archive", type=int, default=4, choices=[1, 2, 3, 4])
    ap.add_argument("--limit", type=int, default=0, help="stop after N candidates (0 = whole archive)")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    if not args.out and args.topic.lower() not in TOPICS:
        raise SystemExit(f"--out is required for the TGDataset label {args.topic!r}")
    out = args.out or paths(args.topic.lower()).seeds / f"seeds_tgdataset_{args.topic.lower()}_a{args.archive}.csv"
    wanted = load_topic_ids(args.topic)
    print(f"{len(wanted)} channels labelled {args.topic!r}")

    found = 0
    t0 = time.time()
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS)
        writer.writeheader()
        req = urllib.request.Request(ARCHIVE_URL.format(n=args.archive))
        with urllib.request.urlopen(req, timeout=120) as resp, tarfile.open(fileobj=resp, mode="r|gz") as tar:
            for member in tar:
                if not member.isfile() or not member.name.endswith(".json"):
                    continue
                n_before = found
                for cand in iter_candidates(tar.extractfile(member), wanted):
                    writer.writerow(to_row(cand, args.topic, args.archive, member.name))
                    fh.flush()
                    found += 1
                    if args.limit and found >= args.limit:
                        break
                print(f"[{time.time() - t0:6.0f}s] {member.name}: +{found - n_before} (total {found})", flush=True)
                if args.limit and found >= args.limit:
                    break
    print(f"Done: {found} candidates -> {out.relative_to(Path.cwd()) if out.is_relative_to(Path.cwd()) else out}")


if __name__ == "__main__":
    main()

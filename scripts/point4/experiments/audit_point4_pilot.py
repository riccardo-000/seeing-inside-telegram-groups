"""Build a reproducible, score-blind human audit of Point 4 pilot matches.

Run from the repository root after analyze_point4_pilot.py:
    python audit_point4_pilot.py

This script does NOT run Qwen or recompute embeddings.
It reuses message_results.csv and the project's iter_pairs() to retrieve
matched channel post texts and channel-post dates.
"""

import csv
import hashlib
import random
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, ".")
from src.analyze.load import iter_pairs

INPUT = Path("data/interim/point4/pilot_analysis/message_results.csv")
OUTPUT = INPUT.parent
N_PER_PAIR = 16
SEED = 42

BINS = [
    ("very_low", lambda s: s < 0.40),
    ("low", lambda s: 0.40 <= s < 0.50),
    ("just_below_052", lambda s: 0.50 <= s < 0.52),
    ("just_above_052", lambda s: 0.52 <= s < 0.55),
    ("moderate_high", lambda s: 0.55 <= s < 0.70),
    ("very_high", lambda s: s >= 0.70),
]


def stable_rng(text):
    digest = hashlib.sha256(f"{SEED}:{text}".encode("utf-8")).digest()
    return random.Random(int.from_bytes(digest[:8], "big"))


def parse_date(raw):
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def temporal_direction(channel_date, group_date):
    c, g = parse_date(channel_date), parse_date(group_date)
    if c is None or g is None:
        return "unknown"
    try:
        if c > g:
            return "channel_post_after_group_message"
        if c < g:
            return "channel_post_before_group_message"
        return "same_timestamp"
    except TypeError:
        return "unknown"


def read_messages():
    with INPUT.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise RuntimeError(f"No pilot message rows found in {INPUT}")
    for row in rows:
        row["score"] = float(row["similarity"])
    return rows


def select_per_pair(rows, pair_id):
    """Sample diverse, nonidentical group texts, with repetition captured in key."""
    rng = stable_rng(pair_id)
    frequencies = Counter(row["text"] for row in rows)
    unique = {}
    for row in rows:
        unique.setdefault(row["text"], row)
    candidates = list(unique.values())
    selected = {}

    def add_some(pool, n, label):
        pool = [r for r in pool if r["text"] not in selected]
        for row in rng.sample(pool, min(n, len(pool))):
            selected[row["text"]] = (row, label)

    for label, rule in BINS:
        add_some([r for r in candidates if rule(r["score"])], 2, label)

    # Deliberately include the dominant repeats (e.g. copy-paste promotions).
    frequent = sorted(candidates, key=lambda r: (-frequencies[r["text"]], r["text"]))
    for row in frequent[:2]:
        selected.setdefault(row["text"], (row, "frequent_text"))

    add_some(candidates, N_PER_PAIR - len(selected), "random_fill")
    chosen = list(selected.values())[:N_PER_PAIR]
    rng.shuffle(chosen)
    return [(row, label, frequencies[row["text"]]) for row, label in chosen]


def write_csv(path, rows, fields):
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main():
    messages = read_messages()
    grouped = defaultdict(list)
    for row in messages:
        grouped[row["pair_id"]].append(row)
    target_ids = set(grouped)

    # One pass through source pairs retrieves the real matched channel texts.
    source_channels = {}
    for topic in sorted(set(row["topic"] for row in messages)):
        for pair, df in iter_pairs(topic):
            pair_id = pair["pair_id"]
            if pair_id not in target_ids:
                continue
            subset = df[
                (df["side"] == "channel")
                & (df["in_window"])
                & (~df["is_service"])
                & (df["has_text"])
            ]
            source_channels[pair_id] = {
                str(int(row["msg_id"])): {
                    "text": str(row["text"]),
                    "date": str(row["date"]),
                }
                for _, row in subset.iterrows()
            }

    missing = sorted(target_ids.difference(source_channels))
    if missing:
        raise RuntimeError(f"Missing source channel-group pairs: {missing}")

    # Audit ALL matches' time direction; no embeddings are required.
    temporal_rows = []
    for pair_id, group_rows in grouped.items():
        channels = source_channels[pair_id]
        counts = Counter()
        for row in group_rows:
            match = channels.get(str(int(row["best_channel_msg_id"])))
            if match is None:
                raise RuntimeError(f"Missing channel match {row['best_channel_msg_id']} for {pair_id}")
            direction = temporal_direction(match["date"], row["group_date"])
            counts[direction] += 1
        n = len(group_rows)
        temporal_rows.append({
            "topic": group_rows[0]["topic"],
            "pair_id": pair_id,
            "n_messages": n,
            "best_match_before_group": counts["channel_post_before_group_message"],
            "best_match_after_group": counts["channel_post_after_group_message"],
            "best_match_same_timestamp": counts["same_timestamp"],
            "best_match_unknown_order": counts["unknown"],
            "future_match_fraction": counts["channel_post_after_group_message"] / n,
        })

    selected = []
    for pair_id in sorted(grouped):
        for row, stratum, count in select_per_pair(grouped[pair_id], pair_id):
            match = source_channels[pair_id][str(int(row["best_channel_msg_id"]))]
            selected.append((row, stratum, count, match))

    rng = stable_rng("global_audit_order")
    rng.shuffle(selected)
    blind, key = [], []
    for idx, (row, stratum, count, match) in enumerate(selected, 1):
        item_id = f"AUDIT-{idx:03d}"
        blind.append({
            "ITEM_ID": item_id,
            "GROUP_MESSAGE": row["text"],
            "CHANNEL_POST": match["text"],
            "SEMANTICALLY_RELATED_YES_NO_UNSURE": "",
            "SPAM_OR_PROMOTION_YES_NO_UNSURE": "",
            "NOTES": "",
        })
        key.append({
            "ITEM_ID": item_id,
            "TOPIC": row["topic"],
            "PAIR_ID": row["pair_id"],
            "GROUP_MSG_ID": row["group_msg_id"],
            "GROUP_DATE": row["group_date"],
            "CHANNEL_MSG_ID": row["best_channel_msg_id"],
            "CHANNEL_DATE": match["date"],
            "TEMPORAL_DIRECTION": temporal_direction(match["date"], row["group_date"]),
            "SIMILARITY": row["similarity"],
            "PREDICTED_GROUP_ONLY_T052": row["group_only_t052"],
            "SAMPLE_STRATUM": stratum,
            "NUMBER_OF_REPEATS_IN_PAIR": count,
        })

    OUTPUT.mkdir(parents=True, exist_ok=True)
    write_csv(OUTPUT / "manual_audit_blind.csv", blind, list(blind[0]))
    write_csv(OUTPUT / "manual_audit_key.csv", key, list(key[0]))
    write_csv(OUTPUT / "temporal_check.csv", sorted(temporal_rows, key=lambda r: r["pair_id"]), list(temporal_rows[0]))
    print(f"Wrote {len(blind)} human-audit examples (model scores hidden in blind file).")
    print(f"- {OUTPUT / 'manual_audit_blind.csv'}")
    print(f"- {OUTPUT / 'manual_audit_key.csv'}")
    print(f"- {OUTPUT / 'temporal_check.csv'}")
    print("This step requires no model/GPU and changes no pilot data.")


if __name__ == "__main__":
    main()

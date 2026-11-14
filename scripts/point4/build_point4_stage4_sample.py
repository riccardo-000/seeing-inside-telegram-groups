"""Point 4 Stage 4: pair-stratified PROBABILITY sample of eligible group-only messages.

Sampling unit: one sampled group message, INCLUDING repeated texts.
Population: semantically eligible group messages with max similarity < 0.52,
within the pre-existing up-to-5000 messages per pair (not all Telegram history).
Each of the 195 pairs contributes min(M, N_pair) observations, selected by an
order-independent SHA256 priority over pair_id + group_msg_id + random seed.

Important: labels are intentionally blank; no AI or human validation is simulated.
Output estimated proportions, after any later annotation, are only as reliable
as those labels. This does NOT perform clustering or model inference.
"""
import argparse
import csv
import hashlib
import heapq
import json
import math
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

URL_RE = re.compile(r"(?i)(?:https?://|www\.|(?<!\w)t\.me/|(?<!\w)telegram\.me/)\S+")
MENTION_RE = re.compile(r"(?<!\w)@[\w]+", re.UNICODE)
TOPICS = ("crypto", "conspiracy")


def semantic_eligible(text):
    stripped = MENTION_RE.sub(" ", URL_RE.sub(" ", text))
    return any(unicodedata.category(ch).startswith("L") for ch in stripped)


def priority(seed, pair, msgid):
    digest = hashlib.sha256(f"{seed}|{pair}|{msgid}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def read_population(path, per_pair, seed):
    heaps = defaultdict(list)
    eligible_go_counts = Counter()
    seen_ids = set()
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        required = {"topic", "pair_id", "group_msg_id", "text", "similarity", "group_only_t052"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError(f"Missing columns: {required - set(reader.fieldnames or [])}")
        for row in reader:
            pair = row["pair_id"]
            topic = row["topic"]
            if topic not in TOPICS or not pair.startswith(topic + ":"):
                raise ValueError(f"Bad pair/category: {topic}, {pair}")
            score = float(row["similarity"])
            if not math.isfinite(score):
                raise ValueError(f"Nonfinite score {pair}:{row['group_msg_id']}")
            flag = row["group_only_t052"].strip().lower() == "true"
            if flag != (score < .52):
                raise ValueError(f"Inconsistent group-only label in {pair}:{row['group_msg_id']}")
            if not flag or not semantic_eligible(row["text"]):
                continue
            key = (pair, row["group_msg_id"])
            if key in seen_ids:
                raise ValueError(f"Duplicate group message ID within pair: {key}")
            seen_ids.add(key)
            eligible_go_counts[pair] += 1
            p = priority(seed, *key)
            heap = heaps[pair]
            item = (-p, key[1], {k: row.get(k, "") for k in ("topic", "pair_id", "group_msg_id", "text", "similarity", "group_date", "role", "n_chars")})
            if len(heap) < per_pair:
                heapq.heappush(heap, item)
            elif p < -heap[0][0]:
                heapq.heapreplace(heap, item)
    return heaps, eligible_go_counts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--analysis-dir", type=Path, default=Path("data/interim/point4/full_analysis"))
    parser.add_argument("--message-file", type=Path, default=None)
    parser.add_argument("--pair-summary-file", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--per-pair", type=int, default=6)
    parser.add_argument("--seed", type=int, default=42026)
    args = parser.parse_args()
    if args.per_pair < 1:
        raise ValueError("per-pair must be positive")
    messages = args.message_file or args.analysis_dir / "message_results.csv"
    summary = args.pair_summary_file or args.analysis_dir / "methodology_v1" / "pair_policy_summary.csv"
    output = args.output_dir or args.analysis_dir / "stage4_probability_sample"
    if not messages.is_file() or not summary.is_file():
        raise FileNotFoundError("Missing message_results.csv or methodology_v1/pair_policy_summary.csv")
    with summary.open("r", encoding="utf-8-sig", newline="") as f:
        pair_counts = {r["pair_id"]: int(r["filtered_count_t052"]) for r in csv.DictReader(f)}
    heaps, eligible_go_counts = read_population(messages, args.per_pair, args.seed)
    if eligible_go_counts != Counter(pair_counts):
        unequal = [(pair, eligible_go_counts[pair], count) for pair, count in pair_counts.items() if eligible_go_counts[pair] != count]
        raise RuntimeError(f"Mismatch with point4_methodology.py denominator: {unequal[:8]}")
    if len(heaps) != 195:
        raise RuntimeError(f"Expected 195 positive pairs, found {len(heaps)}")
    rows = []
    for pair in sorted(heaps):
        for _, _, row in sorted(heaps[pair], key=lambda x: (x[0], x[1])):
            rows.append(row)
    output.mkdir(parents=True, exist_ok=True)
    blind_path = output / "stage4_annotation_blind.csv"
    key_path = output / "stage4_sampling_key.csv"
    counts_out = Counter()
    with blind_path.open("w", encoding="utf-8-sig", newline="") as fo, key_path.open("w", encoding="utf-8-sig", newline="") as fk:
        blind_writer = csv.DictWriter(fo, ["ITEM_ID", "GROUP_MESSAGE", "FUNCTION_LABEL", "THEME_LABEL", "INTERPRETABLE", "PROMOTIONAL", "NOTES"])
        key_writer = csv.DictWriter(fk, ["ITEM_ID", "topic", "pair_id", "group_msg_id", "group_date", "similarity", "n_chars", "n_population_in_pair", "n_selected_in_pair", "inclusion_probability", "analysis_weight"])
        blind_writer.writeheader(); key_writer.writeheader()
        # Shuffle for blinded coding independently of category / pair order.
        rows.sort(key=lambda r: priority(args.seed+1, r["pair_id"], r["group_msg_id"]))
        for i, row in enumerate(rows, 1):
            item_id = f"S4-{i:04d}"
            pair = row["pair_id"]
            N = eligible_go_counts[pair]
            m = min(args.per_pair, N)
            counts_out[row["topic"]] += 1
            blind_writer.writerow({"ITEM_ID": item_id, "GROUP_MESSAGE": row["text"], "FUNCTION_LABEL": "", "THEME_LABEL": "", "INTERPRETABLE": "", "PROMOTIONAL": "", "NOTES": ""})
            key_writer.writerow({"ITEM_ID": item_id, "topic": row["topic"], "pair_id": pair, "group_msg_id": row["group_msg_id"], "group_date": row["group_date"], "similarity": row["similarity"], "n_chars": row["n_chars"], "n_population_in_pair": N, "n_selected_in_pair": m, "inclusion_probability": m/N, "analysis_weight": N/m})
    manifest = {
        "step": "Point 4 Stage 4 probability-sample preparation",
        "purpose": "Stratified systematic qualitative comparison of group-only contents; NOT a completed thematic classification",
        "population": "Within each of the original 195 pairs: messages from existing up-to-5000 group sampling, >=5 chars, with semantic lexical content under point4-v1 policy, cosine max<0.52",
        "sample_design": "Equal number of selected group messages per pair, without replacement; deterministic SHA256 pseudo-random priority independent of CSV order",
        "per_pair_target": args.per_pair,
        "seed": args.seed,
        "eligible_population_messages": dict(Counter({t: sum(n for p,n in eligible_go_counts.items() if p.startswith(t+":")) for t in TOPICS})),
        "pairs": {t: sum(p.startswith(t+":") for p in eligible_go_counts) for t in TOPICS},
        "sampled_messages": dict(counts_out),
        "estimated_primary_statistic": "Per-topic mean over pairs of each pair's sampled thematic message proportion (equal pair weight); frequencies retained within pair; do not pool records without considering the design",
        "limitations": ["Only group-only semantically eligible messages; does not describe all group messages or full histories.", "Single AI-assisted annotation does not establish human validity or inter-annotator reliability.", "The group-only threshold is sensitive to channel-post corpus size.", "Six messages per pair cannot estimate rare within-pair categories precisely."],
        "output_files": [blind_path.name, key_path.name]
    }
    (output / "stage4_sampling_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Validated 195 pairs and {sum(eligible_go_counts.values()):,} eligible group-only messages.")
    print(f"Wrote {len(rows):,} messages (crypto {counts_out['crypto']}, conspiracy {counts_out['conspiracy']}) to {output}")
    print("Blind file contains no source/category/model prediction; key is separate.")


if __name__ == "__main__":
    main()

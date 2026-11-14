"""Point 4 post-processing policy (v1.0, 2026-11-12).

No embeddings are recomputed. Run after analyze_point4.py or on existing
pilot outputs:
    python point4_methodology.py --analysis-dir data/interim/point4/full_analysis
    python point4_methodology.py --analysis-dir data/interim/point4/pilot_analysis

Outputs are written only into <analysis-dir>/methodology_v1/.
Input message/summary CSVs remain untouched.
"""
import argparse
import csv
import json
import math
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

THRESHOLDS = {"t050": 0.50, "t052": 0.52, "t055": 0.55}
MAIN = "t052"
POLICY = "point4-v1.0"
URL_RE = re.compile(r"(?i)(?:https?://|www\.|(?<!\w)t\.me/|(?<!\w)telegram\.me/)\S+")
MENTION_RE = re.compile(r"(?<!\w)@[\w]+", re.UNICODE)
WHITESPACE_RE = re.compile(r"\s+")


def normalized_text(text):
    """Conservative normalization, only for duplicate-weight sensitivity."""
    return WHITESPACE_RE.sub(" ", unicodedata.normalize("NFKC", str(text)).casefold()).strip()


def semantic_status(text):
    """Only exclude text with no written words after stripping URLs and mentions.

    Keeps conversational greetings, hashtags, captions and all Unicode languages.
    Numeric-only messages are 'nonlexical_only' (numbers alone lack context).
    Does NOT attempt to identify spam, bots, toxicity or factual accuracy.
    """
    raw = str(text)
    stripped = MENTION_RE.sub(" ", URL_RE.sub(" ", raw))
    has_letter = any(unicodedata.category(ch).startswith("L") for ch in stripped)
    if has_letter:
        return "eligible"
    if URL_RE.search(raw):
        return "url_only"
    if MENTION_RE.search(raw):
        return "mention_or_nonlexical_only"
    return "nonlexical_only"


def safe_float(v):
    try:
        x = float(v)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def csv_rows(path):
    with Path(path).open("r", encoding="utf-8-sig", newline="") as f:
        yield from csv.DictReader(f)


def write_csv(path, rows, fields):
    with Path(path).open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def process_pair(pair_id, rows, pair_meta, index_writer):
    """Rows are ordered exactly as their matching embedding file expects."""
    seen = set()
    buckets = defaultdict(list)
    status_count = Counter()
    eligible = []
    all_group_only_index = 0
    example_repeats = Counter()

    # Pass 1: frequency of every normalized eligible text, independent of model label.
    for row in rows:
        status = semantic_status(row.get("text", ""))
        status_count[status] += 1
        if status == "eligible":
            key = normalized_text(row["text"])
            example_repeats[key] += 1

    # Pass 2: construct per-pair summaries and an embedding index for unique
    # group-only messages. 'embedding_row' is the index inside the original
    # <pair>.npy that includes ALL t052 group-only rows, including excluded rows.
    for row in rows:
        status = semantic_status(row.get("text", ""))
        score = safe_float(row.get("similarity"))
        if score is None:
            raise ValueError(f"{pair_id}: non-finite similarity for group message {row.get('group_msg_id')}")
        flags = {label: score < threshold for label, threshold in THRESHOLDS.items()}
        if flags[MAIN]:
            if status == "eligible":
                key = normalized_text(row["text"])
                if key not in seen:
                    seen.add(key)
                    index_writer.writerow({
                        "topic": pair_meta["topic"], "pair_id": pair_id,
                        "group_msg_id": row.get("group_msg_id"),
                        "embedding_row": all_group_only_index,
                        "text_frequency_in_sample": example_repeats[key],
                        "similarity": score,
                    })
            all_group_only_index += 1
        if status == "eligible":
            eligible.append((normalized_text(row["text"]), flags, score))
            buckets[normalized_text(row["text"])].append(flags)

    n_all = len(rows)
    n_valid = len(eligible)
    if n_all != int(pair_meta["n_meaningful"]):
        raise ValueError(f"{pair_id}: {n_all} rows but pair summary says {pair_meta['n_meaningful']}")
    data = {
        "topic": pair_meta["topic"], "pair_id": pair_id,
        "n_channel_posts": int(float(pair_meta.get("n_channel_posts") or 0)),
        "n_channel_unique_texts": int(float(pair_meta.get("n_channel_unique_texts") or 0)),
        "n_group_sample": int(float(pair_meta["n_group_sample"])),
        "n_short": int(float(pair_meta["n_short_chit_chat"])),
        "n_embedded_original": n_all,
        "n_url_only": status_count["url_only"],
        "n_mention_only": status_count["mention_or_nonlexical_only"],
        "n_nonlexical_only": status_count["nonlexical_only"],
        "n_semantically_eligible": n_valid,
        "n_unique_eligible_texts": len(buckets),
        "max_text_frequency": max((len(b) for b in buckets.values()), default=0),
        "excluded_share_of_embedded": (n_all - n_valid) / n_all if n_all else None,
    }
    for label in THRESHOLDS:
        total = sum(flags[label] for _, flags, _ in eligible)
        unique_fraction = [sum(flags[label] for flags in b) / len(b) for b in buckets.values()]
        data[f"original_rate_{label}"] = (sum(float(row["similarity"]) < THRESHOLDS[label] for row in rows) / n_all) if n_all else None
        data[f"filtered_count_{label}"] = total
        data[f"filtered_rate_{label}"] = (total / n_valid) if n_valid else None
        data[f"unique_rate_{label}"] = (sum(unique_fraction) / len(unique_fraction)) if unique_fraction else None
        capped_n = sum(min(len(b), 5) for b in buckets.values())
        capped_total = sum(frac * min(len(b), 5) for frac, b in zip(unique_fraction, buckets.values()))
        data[f"cap5_rate_{label}"] = capped_total / capped_n if capped_n else None
    return data


def summarize_pair_means(pair_data):
    output = []
    for topic in ("crypto", "conspiracy"):
        subset = [p for p in pair_data if p["topic"] == topic]
        for cutoff in (0, 10, 50):
            included = [p for p in subset if p["n_channel_unique_texts"] >= cutoff and p["n_semantically_eligible"] > 0]
            for label, value in THRESHOLDS.items():
                for basis, col in (("filtered_messages", "filtered_rate"), ("unique_texts", "unique_rate"), ("frequency_cap5", "cap5_rate"), ("original_embedded", "original_rate")):
                    vals = [p[f"{col}_{label}"] for p in included if p[f"{col}_{label}"] is not None]
                    output.append({"topic":topic, "min_unique_channel_posts":cutoff, "threshold": value,
                                   "basis":basis, "n_pairs":len(vals),
                                   "mean_pair_rate":sum(vals)/len(vals) if vals else None,
                                   "median_pair_rate":sorted(vals)[len(vals)//2] if len(vals)%2 else (sorted(vals)[len(vals)//2-1]+sorted(vals)[len(vals)//2])/2 if vals else None})
    return output


def run(analysis_dir):
    analysis_dir = Path(analysis_dir)
    if not analysis_dir.is_dir():
        raise FileNotFoundError(f"Analysis directory not found: {analysis_dir}")
    pair_meta_path = analysis_dir / "pair_results.csv"
    all_message_path = analysis_dir / "message_results.csv"
    pair_dir = analysis_dir / "pairs"
    if not pair_meta_path.exists() or not all_message_path.exists():
        raise FileNotFoundError("Both pair_results.csv and message_results.csv must exist. Run analysis/aggregation first.")
    pair_meta = {r["pair_id"]:r for r in csv_rows(pair_meta_path)}
    output_dir = analysis_dir / "methodology_v1"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Process original per-pair CSVs when present, otherwise group the aggregated
    # message CSV. The latter is already pair-contiguous in the project's outputs.
    msgfiles = sorted(pair_dir.glob("*_messages.csv")) if pair_dir.exists() else []
    pair_inputs = []
    if msgfiles:
        for msgfile in msgfiles:
            # Recover exact pair ID from summary metadata rather than deriving
            # an identifier from the filename (safe_pair_name is not reversible).
            key = msgfile.name.removesuffix("_messages.csv")
            matched = [pid for pid in pair_meta if pid.replace(":", "__").replace("/", "_").replace("\\", "_") == key]
            if len(matched) != 1:
                raise ValueError(f"Cannot map {msgfile} to exactly one pair ({matched})")
            pair_inputs.append((matched[0], list(csv_rows(msgfile))))
    else:
        buckets = defaultdict(list)
        for row in csv_rows(all_message_path):
            buckets[row["pair_id"]].append(row)
        pair_inputs = sorted(buckets.items())

    results = []
    index_path = output_dir / "unique_group_only_embedding_index.csv"
    with index_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["topic", "pair_id", "group_msg_id", "embedding_row", "text_frequency_in_sample", "similarity"])
        writer.writeheader()
        processed = set()
        for pair_id, messages in pair_inputs:
            if pair_id not in pair_meta:
                raise ValueError(f"Pair has messages but no summary: {pair_id}")
            results.append(process_pair(pair_id, messages, pair_meta[pair_id], writer))
            processed.add(pair_id)
        # Handle pairs with no meaningful messages (empty per-pair message files)
        for pair_id, metadata in pair_meta.items():
            if pair_id not in processed:
                results.append(process_pair(pair_id, [], metadata, writer))

    results.sort(key=lambda x:(x["topic"], x["pair_id"]))
    pair_cols = ["topic", "pair_id", "n_channel_posts", "n_channel_unique_texts", "n_group_sample", "n_short", "n_embedded_original", "n_url_only", "n_mention_only", "n_nonlexical_only", "n_semantically_eligible", "n_unique_eligible_texts", "max_text_frequency", "excluded_share_of_embedded"]
    for label in THRESHOLDS:
        pair_cols += [f"original_rate_{label}", f"filtered_count_{label}", f"filtered_rate_{label}", f"unique_rate_{label}", f"cap5_rate_{label}"]
    write_csv(output_dir / "pair_policy_summary.csv", results, pair_cols)
    summary = summarize_pair_means(results)
    write_csv(output_dir / "topic_policy_summary.csv", summary, ["topic", "min_unique_channel_posts", "threshold", "basis", "n_pairs", "mean_pair_rate", "median_pair_rate"])
    desc = {
        "policy": POLICY, "main_threshold": 0.52, "sensitivity_thresholds": [0.50,0.55],
        "primary_metric": "Unweighted mean of per-pair fraction of semantically eligible group messages with max cosine similarity below threshold 0.52.",
        "eligibility": "After URLs and @mentions are removed, at least one Unicode letter must remain. Group-only URL/emoji/mention/numeric messages excluded from denominator but counted separately. Short messages <5 chars already excluded upstream.",
        "duplicate_policy": "Primary counts all eligible sampled messages, including repeated texts. Sensitivity weights each normalized distinct text once, and separately caps each normalized text frequency at 5 per pair.",
        "normalization": "Unicode NFKC + casefold + whitespace collapse (only for duplicate sensitivity).",
        "channel_corpus": "Unchanged from original calibrated pipeline. 10/50 distinct channel-post minima are descriptive sensitivity strata, not primary eligibility criteria.",
        "temporality": "All posts in recorded window; semantic overlap, NOT evidence of temporal influence or causal origin.",
        "clustering": "Use unique_group_only_embedding_index.csv to select unique eligible group-only rows from each original per-pair .npy. Indices are 0-based in that .npy; may include noneligible rows that are skipped by the index.",
        "caveat": "Semantic non-alignment with the channel is not synonymous with an independent community discussion. This script does not detect spam or filter external references beyond text eligibility.",
        "files": ["pair_policy_summary.csv", "topic_policy_summary.csv", "unique_group_only_embedding_index.csv"]
    }
    (output_dir / "policy.json").write_text(json.dumps(desc, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Processed {len(results)} pairs. Results in: {output_dir}")
    for row in summary:
        if row["min_unique_channel_posts"] == 0 and row["threshold"] == 0.52:
            print(f"{row['topic']:>11s} {row['basis']:>20s}: {row['mean_pair_rate']:.2%} (n={row['n_pairs']})")
    return results, summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Apply documented Point-4 methodology to existing embedding results")
    parser.add_argument("--analysis-dir", default="data/interim/point4/full_analysis")
    args = parser.parse_args()
    run(args.analysis_dir)

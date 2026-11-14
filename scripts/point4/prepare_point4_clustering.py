"""Prepare the Point 4 clustering dataset without recomputing embeddings.

Inputs:
  <analysis-dir>/methodology_v1/unique_group_only_embedding_index.csv
  <analysis-dir>/message_results.csv
  <analysis-dir>/group_only_embeddings/<safe_pair_id>.npy

Checks every index entry against the per-pair order in the original message CSV,
checks source NPY shapes, and writes two memory-mapped NPY arrays plus aligned
metadata, one for each topic. Only one pair's embeddings enter RAM at a time.

Usage:
  python prepare_point4_clustering.py --check-only
  python prepare_point4_clustering.py
"""

import argparse
import csv
import json
import math
import os
import re
import time
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

TOPICS = ("crypto", "conspiracy")
MAIN_THRESHOLD = 0.52
EMBEDDING_DIM = 1024
URL_RE = re.compile(r"(?i)(?:https?://|www\.|(?<!\w)t\.me/|(?<!\w)telegram\.me/)\S+")
MENTION_RE = re.compile(r"(?<!\w)@[\w]+", re.UNICODE)
WHITESPACE_RE = re.compile(r"\s+")
METADATA_COLS = ["embedding_index", "topic", "pair_id", "group_msg_id", "group_date", "role", "n_chars", "similarity", "text_frequency_in_sample", "group_only_frequency_in_sample", "original_embedding_row", "text"]


def semantic_eligible(text):
    stripped = MENTION_RE.sub(" ", URL_RE.sub(" ", text))
    return any(unicodedata.category(char).startswith("L") for char in stripped)


def normalized_text(text):
    return WHITESPACE_RE.sub(" ", unicodedata.normalize("NFKC", text).casefold()).strip()


def safe_pair_name(pair_id):
    return pair_id.replace(":", "__").replace("/", "_").replace("\\", "_")


def read_index(path):
    by_pair = defaultdict(list)
    by_msg = defaultdict(dict)
    counts = Counter()
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        expected_cols = {"topic", "pair_id", "group_msg_id", "embedding_row", "text_frequency_in_sample", "similarity"}
        if not expected_cols.issubset(reader.fieldnames or []):
            raise ValueError("Index CSV is missing required columns")
        for n, row in enumerate(reader, start=1):
            topic, pair, msgid = row["topic"], row["pair_id"], row["group_msg_id"]
            if topic not in TOPICS or not pair.startswith(topic + ":"):
                raise ValueError(f"Index row {n}: invalid topic/pair")
            rowno, frequency, similarity = int(row["embedding_row"]), int(row["text_frequency_in_sample"]), float(row["similarity"])
            if rowno < 0 or frequency < 1 or not math.isfinite(similarity) or similarity >= MAIN_THRESHOLD:
                raise ValueError(f"Index row {n}: invalid embedding row, frequency or similarity")
            if msgid in by_msg[pair]:
                raise ValueError(f"Index row {n}: repeated message ID within {pair}")
            item = {"topic": topic, "pair_id": pair, "group_msg_id": msgid, "embedding_row": rowno, "frequency": frequency, "similarity": similarity}
            if by_pair[pair] and rowno <= by_pair[pair][-1]["embedding_row"]:
                raise ValueError(f"Index row {n}: non-increasing embedding positions in {pair}")
            by_pair[pair].append(item)
            by_msg[pair][msgid] = item
            counts[topic] += 1
    if not by_pair:
        raise ValueError("Empty index")
    return by_pair, by_msg, counts


def match_original_messages(path, by_pair, by_msg):
    group_only_positions = Counter()
    found = Counter()
    messages_seen = 0
    go_frequency = defaultdict(Counter)
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        required = {"topic", "pair_id", "group_msg_id", "group_date", "role", "n_chars", "text", "similarity", "group_only_t052"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError("Message CSV is missing required columns")
        for row in reader:
            pair, msgid = row["pair_id"], row["group_msg_id"]
            messages_seen += 1
            score = float(row["similarity"])
            if not math.isfinite(score):
                raise ValueError(f"Non-finite similarity for {pair}/{msgid}")
            go = row["group_only_t052"].strip().lower() == "true"
            if go != (score < MAIN_THRESHOLD):
                raise ValueError(f"group_only_t052 disagrees with score for {pair}/{msgid}")
            entry = by_msg.get(pair, {}).get(msgid)
            if entry is not None:
                if not go:
                    raise ValueError(f"Indexed message is not group-only: {pair}/{msgid}")
                if entry["embedding_row"] != group_only_positions[pair]:
                    raise ValueError(f"Wrong NPY position for {pair}/{msgid}: index={entry['embedding_row']}, expected={group_only_positions[pair]}")
                if row["topic"] != entry["topic"] or abs(score - entry["similarity"]) > 1e-5:
                    raise ValueError(f"Index/message mismatch for {pair}/{msgid}")
                if not semantic_eligible(row["text"]):
                    raise ValueError(f"Indexed message is not semantically eligible: {pair}/{msgid}")
                entry["group_date"] = row["group_date"]
                entry["role"] = row["role"]
                entry["n_chars"] = int(row["n_chars"])
                entry["text"] = row["text"]
                found[pair] += 1
            if go:
                group_only_positions[pair] += 1
                if semantic_eligible(row["text"]):
                    go_frequency[pair][normalized_text(row["text"])] += 1
    missing = [(p, len(items) - found[p]) for p, items in by_pair.items() if found[p] != len(items)]
    if missing:
        raise ValueError(f"Indexed messages missing from original CSV: {missing[:8]}")
    for pair, items in by_pair.items():
        for item in items:
            item["group_only_frequency"] = go_frequency[pair][normalized_text(item["text"])]
            if item["group_only_frequency"] <= 0:
                raise ValueError(f"No group-only duplicates found for indexed message {pair}/{item['group_msg_id']}")
        if sum(item["group_only_frequency"] for item in items) != sum(go_frequency[pair].values()):
            raise ValueError(f"Distinct-text frequency reconciliation failed for {pair}")
    return group_only_positions, messages_seen


def validate_embedding_files(embedding_dir, by_pair, group_only_positions):
    expected_size = 0
    for pair, items in sorted(by_pair.items()):
        path = embedding_dir / (safe_pair_name(pair) + ".npy")
        if not path.exists():
            raise FileNotFoundError(f"Missing source embeddings: {path}")
        arr = np.load(path, mmap_mode="r", allow_pickle=False)
        expected_rows = group_only_positions[pair]
        if arr.ndim != 2 or arr.shape != (expected_rows, EMBEDDING_DIM):
            raise ValueError(f"{path}: expected shape {(expected_rows, EMBEDDING_DIM)}, got {arr.shape}")
        if not np.issubdtype(arr.dtype, np.floating):
            raise ValueError(f"{path}: expected floating-point embeddings, got {arr.dtype}")
        if items[-1]["embedding_row"] >= expected_rows:
            raise ValueError(f"{path}: selected index out of bounds")
        expected_size += len(items) * EMBEDDING_DIM * 4
        del arr
    return expected_size


def build_outputs(output_dir, embedding_dir, by_pair, counts):
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = {"methodology": "point4-v1.0", "threshold": MAIN_THRESHOLD, "embedding_dimension": EMBEDDING_DIM,
                "dtype": "float32", "unit": "unique eligible group-only text within each channel-group pair",
                "pairwise_deduplication": "Unicode NFKC + casefold + whitespace collapse, as in methodology_v1",
                "order": "Sorted pair_id, then increasing original embedding_row; metadata row i matches .npy row i",
                "notes": "Texts shared across distinct pairs are intentionally kept separate. This is semantic non-alignment, not evidence of causal discussion origin.",
                "frequency_definitions": {"text_frequency_in_sample": "Frequency of the normalized text among ALL semantically eligible sampled messages (including aligned ones)", "group_only_frequency_in_sample": "Frequency of the normalized text among semantically eligible messages with similarity < 0.52"},
                "topics": {}}
    ranges = []
    for topic in TOPICS:
        pair_ids = sorted(pair for pair in by_pair if by_pair[pair][0]["topic"] == topic)
        count = counts[topic]
        matrix_temp = output_dir / f"{topic}_embeddings.partial.npy"
        metadata_temp = output_dir / f"{topic}_metadata.partial.csv"
        matrix_final = output_dir / f"{topic}_embeddings.npy"
        metadata_final = output_dir / f"{topic}_metadata.csv"
        arr_out = np.lib.format.open_memmap(matrix_temp, mode="w+", dtype=np.float32, shape=(count, EMBEDDING_DIM))
        current = 0
        print(f"\nBuilding {topic}: {count:,} selected vectors ({count*EMBEDDING_DIM*4/2**20:.1f} MiB)", flush=True)
        with metadata_temp.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=METADATA_COLS)
            writer.writeheader()
            for n, pair in enumerate(pair_ids, start=1):
                items = by_pair[pair]
                file_path = embedding_dir / (safe_pair_name(pair) + ".npy")
                original = np.load(file_path, mmap_mode="r", allow_pickle=False)
                indices = np.fromiter((item["embedding_row"] for item in items), count=len(items), dtype=np.int64)
                selected = np.asarray(original[indices], dtype=np.float32)
                if not np.isfinite(selected).all():
                    raise ValueError(f"{file_path}: embeddings contain NaN or infinity")
                end = current + len(items)
                arr_out[current:end] = selected
                for offset, item in enumerate(items):
                    writer.writerow({"embedding_index": current + offset, "topic": topic, "pair_id": pair, "group_msg_id": item["group_msg_id"],
                                     "group_date": item["group_date"], "role": item["role"], "n_chars": item["n_chars"],
                                     "similarity": item["similarity"], "text_frequency_in_sample": item["frequency"], "group_only_frequency_in_sample": item["group_only_frequency"],
                                     "original_embedding_row": item["embedding_row"], "text": item["text"]})
                ranges.append({"topic": topic, "pair_id": pair, "start_index_inclusive": current, "end_index_exclusive": end, "n_unique_texts": len(items)})
                current = end
                del original, selected
                if n % 20 == 0 or n == len(pair_ids):
                    print(f"  {n}/{len(pair_ids)} pairs | {current:,}/{count:,} vectors", flush=True)
        if current != count:
            raise RuntimeError(f"{topic}: wrote {current} vectors, expected {count}")
        arr_out.flush()
        del arr_out
        os.replace(matrix_temp, matrix_final)
        os.replace(metadata_temp, metadata_final)
        manifest["topics"][topic] = {"pairs": len(pair_ids), "unique_texts": count, "embeddings_file": matrix_final.name,
                                     "metadata_file": metadata_final.name, "shape": [count, EMBEDDING_DIM],
                                     "embedding_size_mib": round(count*EMBEDDING_DIM*4/2**20, 2)}
    with (output_dir / "pair_index_ranges.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["topic", "pair_id", "start_index_inclusive", "end_index_exclusive", "n_unique_texts"])
        writer.writeheader()
        writer.writerows(ranges)
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest


def main():
    parser = argparse.ArgumentParser(description="Validate and build scalable, aligned Point-4 clustering inputs")
    parser.add_argument("--analysis-dir", type=Path, default=Path("data/interim/point4/full_analysis"))
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--check-only", action="store_true", help="Validate links and NPY shapes without creating the large output arrays")
    args = parser.parse_args()
    analysis_dir = args.analysis_dir
    index_path = analysis_dir / "methodology_v1" / "unique_group_only_embedding_index.csv"
    message_path = analysis_dir / "message_results.csv"
    embedding_dir = analysis_dir / "group_only_embeddings"
    for p in (index_path, message_path, embedding_dir):
        if not p.exists():
            raise FileNotFoundError(f"Required input not found: {p}")
    started = time.perf_counter()
    print("Point 4 clustering dataset preparation", flush=True)
    by_pair, by_msg, counts = read_index(index_path)
    print(f"Index: {sum(counts.values()):,} entries across {len(by_pair)} pairs | crypto={counts['crypto']:,}, conspiracy={counts['conspiracy']:,}", flush=True)
    group_only_positions, messages_seen = match_original_messages(message_path, by_pair, by_msg)
    expected_size = validate_embedding_files(embedding_dir, by_pair, group_only_positions)
    print(f"Validated {messages_seen:,} message rows and {len(by_pair)} source NPY files; expected combined embedding size: {expected_size/2**30:.2f} GiB", flush=True)
    if args.check_only:
        print("Validation passed. No files created.", flush=True)
        return
    output_dir = args.output_dir or (analysis_dir / "clustering_input")
    manifest = build_outputs(output_dir, embedding_dir, by_pair, counts)
    for topic in TOPICS:
        arr_file = output_dir / manifest["topics"][topic]["embeddings_file"]
        meta_file = output_dir / manifest["topics"][topic]["metadata_file"]
        arr = np.load(arr_file, mmap_mode="r")
        if list(arr.shape) != manifest["topics"][topic]["shape"] or not meta_file.exists():
            raise RuntimeError(f"Verification of output files failed for {topic}")
        del arr
    print(f"\nDONE in {(time.perf_counter()-started)/60:.1f} min. Outputs: {output_dir}", flush=True)
    print("Files: crypto_embeddings.npy, conspiracy_embeddings.npy, crypto_metadata.csv, conspiracy_metadata.csv, pair_index_ranges.csv, manifest.json", flush=True)


if __name__ == "__main__":
    main()

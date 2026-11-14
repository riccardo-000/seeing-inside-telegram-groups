"""Point 4 - exploratory semantic clustering (CPU, no model inference).

Input: clustering_input/{crypto,conspiracy}_{embeddings.npy,metadata.csv}
First run: python cluster_point4_stage2.py --mode pilot
After validation: python cluster_point4_stage2.py --mode full

Approach: pair-stratified training sample, TruncatedSVD, L2 normalization,
MiniBatchKMeans, representative-message audit export. Pilot results are
DIAGNOSTIC, not final topic prevalence estimates.
"""

import argparse
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import MiniBatchKMeans
from sklearn.decomposition import TruncatedSVD
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import normalize
from threadpoolctl import threadpool_limits

TOPICS = ("crypto", "conspiracy")
SEED = 42
EXAMPLE_PER_CLUSTER = 6


def sample_across_pairs(pair_ids, target, rng):
    """Give every channel/group pair a chance to contribute to the fit."""
    n = len(pair_ids)
    if target >= n:
        return np.arange(n, dtype=np.int64)
    series = pd.Series(np.arange(n, dtype=np.int64), index=pair_ids)
    pair_groups = [(str(p), a.to_numpy(dtype=np.int64)) for p, a in series.groupby(level=0, sort=True)]
    selected = []
    quota = max(1, target // len(pair_groups))
    for _, indices in pair_groups:
        count = min(quota, len(indices))
        selected.extend(rng.choice(indices, size=count, replace=False).tolist())
    selected = np.asarray(selected, dtype=np.int64)
    if len(selected) < target:
        mask = np.ones(n, dtype=bool)
        mask[selected] = False
        remaining = np.flatnonzero(mask)
        extra = rng.choice(remaining, size=min(target-len(selected), len(remaining)), replace=False)
        selected = np.concatenate((selected, extra))
    return np.sort(selected)


def validated_inputs(input_dir, topic):
    embeddings_path = input_dir / f"{topic}_embeddings.npy"
    metadata_path = input_dir / f"{topic}_metadata.csv"
    if not embeddings_path.exists() or not metadata_path.exists():
        raise FileNotFoundError(f"Missing input files for {topic} under {input_dir}")
    embeddings = np.load(embeddings_path, mmap_mode="r", allow_pickle=False)
    metadata = pd.read_csv(metadata_path, encoding="utf-8-sig", dtype={"topic": str, "pair_id": str, "group_msg_id": str, "text": str})
    required = {"embedding_index", "topic", "pair_id", "group_msg_id", "text", "similarity", "group_only_frequency_in_sample"}
    if not required.issubset(metadata.columns):
        raise ValueError(f"Missing metadata fields for {topic}: {sorted(required - set(metadata.columns))}")
    if embeddings.ndim != 2 or embeddings.shape[0] != len(metadata):
        raise ValueError(f"Metadata/embeddings shape mismatch for {topic}")
    if not np.array_equal(metadata["embedding_index"].to_numpy(), np.arange(len(metadata))):
        raise ValueError(f"Embedding indices out of alignment for {topic}")
    if not metadata["topic"].eq(topic).all():
        raise ValueError(f"Incorrect topic in {topic}_metadata.csv")
    if metadata["group_only_frequency_in_sample"].isna().any() or (metadata["group_only_frequency_in_sample"] < 1).any():
        raise ValueError(f"Invalid frequency weights in {topic}")
    if not np.isfinite(np.asarray(embeddings[:min(128, len(embeddings))])).all():
        raise ValueError(f"Non-finite embedding values for {topic}")
    return embeddings, metadata


def project_batch(embeddings, indices, svd):
    batch = np.asarray(embeddings[indices], dtype=np.float32)
    projected = svd.transform(batch).astype(np.float32, copy=False)
    return normalize(projected, norm="l2", copy=False).astype(np.float32, copy=False)


def run_topic(input_dir, output_dir, topic, mode, n_clusters, fit_size, n_components, batch_size, threads):
    started = time.perf_counter()
    source, meta = validated_inputs(input_dir, topic)
    n, dim = source.shape
    rng = np.random.default_rng(SEED if topic == "crypto" else SEED + 1)
    indices = sample_across_pairs(meta["pair_id"].to_numpy(), min(fit_size, n), rng)
    sample = np.asarray(source[indices], dtype=np.float32)
    components = min(n_components, dim - 1, len(sample) - 1)
    clusters = min(n_clusters, len(sample) - 1)
    if components < 2 or clusters < 2:
        raise ValueError("Not enough data for clustering")
    print(f"\n[{topic}] {n:,} source vectors; fitting on {len(indices):,} pair-stratified examples; k={clusters}, dimensions={components}", flush=True)

    with threadpool_limits(limits=threads):
        svd = TruncatedSVD(n_components=components, n_iter=3, random_state=SEED)
        reduced_sample = normalize(svd.fit_transform(sample).astype(np.float32), norm="l2", copy=False)
        model = MiniBatchKMeans(n_clusters=clusters, batch_size=min(2048, max(128, len(sample))), n_init=3, max_iter=100, random_state=SEED, reassignment_ratio=0.0)
        model.fit(reduced_sample)
        print(f"[{topic}] SVD and MiniBatchKMeans fit complete ({(time.perf_counter()-started)/60:.1f} min)", flush=True)

        if mode == "pilot":
            selected = indices
            reduced = reduced_sample
        else:
            selected = np.arange(n, dtype=np.int64)
            reduced_path = output_dir / f"{topic}_reduced.npy"
            reduced = np.lib.format.open_memmap(reduced_path, mode="w+", dtype=np.float32, shape=(n, components))
            for start in range(0, n, batch_size):
                end = min(start+batch_size, n)
                reduced[start:end] = project_batch(source, slice(start, end), svd)
                if end == n or end % (batch_size*10) == 0:
                    print(f"[{topic}] projected {end:,}/{n:,}", flush=True)
            reduced.flush()

        labels = np.empty(len(selected), dtype=np.int32)
        strengths = np.empty(len(selected), dtype=np.float32)
        centers = normalize(model.cluster_centers_.astype(np.float32, copy=True), norm="l2", copy=False)
        for start in range(0, len(selected), batch_size):
            end = min(start+batch_size, len(selected))
            block = np.asarray(reduced[start:end], dtype=np.float32)
            block_labels = model.predict(block)
            labels[start:end] = block_labels
            strengths[start:end] = np.sum(block * centers[block_labels], axis=1)

        silhouette = None
        if len(selected) >= max(200, clusters*3) and len(np.unique(labels)) > 1:
            eval_rows = rng.choice(len(selected), size=min(1200, len(selected)), replace=False)
            if len(np.unique(labels[eval_rows])) > 1:
                silhouette = float(silhouette_score(np.asarray(reduced[eval_rows]), labels[eval_rows], metric="cosine"))

    result = meta.iloc[selected].copy().reset_index(drop=True)
    result["cluster_id"] = labels
    result["center_cosine"] = strengths
    result.insert(0, "source_embedding_index", selected)
    cluster_rows = []
    example_rows = []
    unique_by_pair = result.groupby("pair_id")["group_only_frequency_in_sample"].sum()

    for cluster in range(clusters):
        subset = result.loc[result["cluster_id"] == cluster]
        if subset.empty:
            continue
        total_frequency = int(subset["group_only_frequency_in_sample"].sum())
        top_pairs = subset["pair_id"].value_counts()
        cluster_rows.append({
            "topic": topic, "cluster_id": cluster, "n_unique_texts": len(subset),
            "n_pairs": subset["pair_id"].nunique(),
            "n_group_only_messages": total_frequency,
            "mean_center_cosine": float(subset["center_cosine"].mean()),
            "median_center_cosine": float(subset["center_cosine"].median()),
            "top_pair_id": str(top_pairs.index[0]),
            "top_pair_share_unique_texts": float(top_pairs.iloc[0] / len(subset)),
            "mean_pair_prevalence": float((subset.groupby("pair_id")["group_only_frequency_in_sample"].sum() / unique_by_pair).reindex(unique_by_pair.index, fill_value=0).mean())
            if mode == "full" else np.nan,
        })
        top = subset.nlargest(EXAMPLE_PER_CLUSTER, "center_cosine")
        rest = subset.drop(index=top.index)
        other = rest.sample(n=min(EXAMPLE_PER_CLUSTER, len(rest)), random_state=SEED+cluster) if not rest.empty else rest
        for kind, chosen in (("central", top), ("random", other)):
            for _, row in chosen.iterrows():
                example_rows.append({"topic": topic, "cluster_id": cluster, "example_type": kind,
                                     "pair_id": row["pair_id"], "group_msg_id": row["group_msg_id"],
                                     "center_cosine": row["center_cosine"], "group_only_frequency_in_sample": row["group_only_frequency_in_sample"],
                                     "text": row["text"]})

    result[["source_embedding_index", "topic", "pair_id", "group_msg_id", "cluster_id", "center_cosine", "group_only_frequency_in_sample"]].to_csv(output_dir / f"{topic}_assignments.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(cluster_rows).sort_values("n_unique_texts", ascending=False).to_csv(output_dir / f"{topic}_cluster_summary.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(example_rows).to_csv(output_dir / f"{topic}_cluster_examples.csv", index=False, encoding="utf-8-sig")
    result_info = {"topic": topic, "mode": mode, "input_vectors": int(n), "assigned_vectors": int(len(result)),
                   "fit_sample": int(len(sample)), "components": int(components), "clusters_requested": int(clusters),
                   "clusters_nonempty": int(len(cluster_rows)), "svd_explained_variance_ratio_sum": float(svd.explained_variance_ratio_.sum()),
                   "sample_cosine_silhouette": silhouette, "elapsed_seconds": round(time.perf_counter()-started, 2),
                   "warning": "Exploratory forced-assignment clustering; cluster labels and thematic validity require qualitative review. Pilot counts are not population estimates."}
    print(f"[{topic}] Saved {len(result):,} assignments, {len(cluster_rows)} cluster summaries, {len(example_rows)} review examples. Silhouette={silhouette}", flush=True)
    return result_info


def main():
    parser = argparse.ArgumentParser(description="Point 4 exploratory clustering; use --mode pilot first.")
    parser.add_argument("--input-dir", type=Path, default=Path("data/interim/point4/full_analysis/clustering_input"))
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--mode", choices=("pilot", "full"), default="pilot")
    parser.add_argument("--clusters", type=int, default=None)
    parser.add_argument("--fit-sample", type=int, default=None)
    parser.add_argument("--components", type=int, default=64)
    parser.add_argument("--batch-size", type=int, default=8192)
    parser.add_argument("--threads", type=int, default=4)
    args = parser.parse_args()
    if args.components < 2 or args.batch_size < 128 or args.threads < 1:
        parser.error("Invalid components, batch size or thread count")
    clusters = args.clusters or (45 if args.mode == "pilot" else 100)
    fit_sample = args.fit_sample or (10000 if args.mode == "pilot" else 30000)
    if clusters < 2 or fit_sample < clusters:
        parser.error("clusters must be >=2 and fit-sample >= clusters")
    out = args.output_dir or args.input_dir.parent / ("clustering_pilot" if args.mode == "pilot" else "clustering_full")
    out.mkdir(parents=True, exist_ok=True)
    print(f"Point 4 semantic clustering | mode={args.mode} | k={clusters} | fit sample={fit_sample} | threads={args.threads}", flush=True)
    run_summary = {"mode": args.mode, "seed": SEED, "projection": "TruncatedSVD followed by L2 normalization", "clustering": "MiniBatchKMeans", "topics": {}}
    for topic in TOPICS:
        run_summary["topics"][topic] = run_topic(args.input_dir, out, topic, args.mode, clusters, fit_sample, args.components, args.batch_size, args.threads)
        (out / "run_summary.json").write_text(json.dumps(run_summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nDONE. Files in {out}. Review *cluster_examples.csv before making any topic claims.", flush=True)


if __name__ == "__main__":
    main()

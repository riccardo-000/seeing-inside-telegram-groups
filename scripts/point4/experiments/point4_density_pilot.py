"""Point 4 - alternative density-based *pilot* for semantic topic discovery.

Reuses the exact same pair-stratified 10k-per-topic sample as
cluster_point4_stage2.py, but permits noise/unassigned messages.
No Qwen/model inference. Outputs are exploratory, NOT validated themes.

Default requires: python -m pip install umap-learn
Uses sklearn HDBSCAN (scikit-learn >= 1.3) or the external hdbscan package.
For a dependency-free projection fallback, run with --projection svd.
"""
import argparse
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import normalize
from threadpoolctl import threadpool_limits

from cluster_point4_stage2 import validated_inputs, sample_across_pairs

TOPICS = ("crypto", "conspiracy")
SEED = 42


def get_hdbscan(min_size, min_samples, threads):
    try:
        from sklearn.cluster import HDBSCAN
        return HDBSCAN(min_cluster_size=min_size, min_samples=min_samples, metric="euclidean", cluster_selection_method="eom", n_jobs=threads)
    except ImportError:
        try:
            import hdbscan
        except ImportError as exc:
            raise RuntimeError("Install scikit-learn>=1.3 or hdbscan to run density clustering") from exc
        return hdbscan.HDBSCAN(min_cluster_size=min_size, min_samples=min_samples, metric="euclidean", cluster_selection_method="eom", core_dist_n_jobs=threads)


def projection(sample, args):
    if args.projection == "umap":
        try:
            import umap
        except ImportError as exc:
            raise RuntimeError("UMAP missing. Install with: python -m pip install umap-learn") from exc
        projector = umap.UMAP(n_neighbors=args.neighbors, n_components=args.components, min_dist=0.05,
                              metric="cosine", random_state=SEED, low_memory=True)
        lowdim = projector.fit_transform(sample)
        info = {"projection": "UMAP", "dimensions": args.components, "neighbors": args.neighbors, "min_dist": 0.05}
    else:
        comps = min(args.components, sample.shape[1] - 1, len(sample) - 1)
        projector = TruncatedSVD(n_components=comps, n_iter=4, random_state=SEED)
        lowdim = projector.fit_transform(sample)
        info = {"projection": "TruncatedSVD", "dimensions": comps, "explained_variance": float(projector.explained_variance_ratio_.sum())}
    reduced = np.asarray(lowdim, dtype=np.float32)
    if args.projection == "svd":
        # For the linear SVD baseline, Euclidean distance on normalized vectors
        # is monotonic with cosine distance. Do not normalize UMAP output:
        # its Euclidean neighborhood geometry would be distorted.
        reduced = normalize(reduced, norm="l2", copy=False)
    return reduced, info


def main_topic(topic, args, output_dir):
    start_time = time.perf_counter()
    source, metadata = validated_inputs(args.input_dir, topic)
    rng = np.random.default_rng(SEED if topic == "crypto" else SEED + 1)
    selected = sample_across_pairs(metadata["pair_id"].to_numpy(), min(args.sample_size, len(metadata)), rng)
    sample = np.asarray(source[selected], dtype=np.float32)
    sample = normalize(sample, norm="l2", copy=False)
    print(f"[{topic}] reading {len(selected):,} unique texts across {metadata.iloc[selected]['pair_id'].nunique()} pairs", flush=True)
    with threadpool_limits(limits=args.threads):
        print(f"[{topic}] projecting with {args.projection}...", flush=True)
        reduced, projection_info = projection(sample, args)
        print(f"[{topic}] fitting HDBSCAN (min_cluster_size={args.min_cluster_size}, min_samples={args.min_samples})...", flush=True)
        model = get_hdbscan(args.min_cluster_size, args.min_samples, args.threads)
        labels = model.fit_predict(reduced).astype(np.int32)
    probabilities = np.asarray(model.probabilities_, dtype=np.float32)
    cluster_ids = sorted(x for x in np.unique(labels).tolist() if x >= 0)
    noise = labels == -1
    result = metadata.iloc[selected].copy().reset_index(drop=True)
    result.insert(0, "source_embedding_index", selected)
    result["cluster_id"] = labels
    result["membership_probability"] = probabilities
    cols = ["source_embedding_index", "topic", "pair_id", "group_msg_id", "cluster_id", "membership_probability", "group_only_frequency_in_sample"]
    result[cols].to_csv(output_dir / f"{topic}_assignments.csv", index=False, encoding="utf-8-sig")

    summaries, examples = [], []
    for cluster_id in cluster_ids:
        local = np.flatnonzero(labels == cluster_id)
        v = sample[local]
        center = normalize(v.mean(axis=0, keepdims=True), norm="l2")[0]
        scores = v @ center
        top_indices = local[np.argsort(-scores)[:args.examples_per_cluster]]
        rest = np.setdiff1d(local, top_indices, assume_unique=True)
        rand_indices = rng.choice(rest, size=min(len(rest), args.examples_per_cluster), replace=False) if len(rest) else np.array([], dtype=int)
        subset = result.iloc[local]
        share = float(subset["pair_id"].value_counts().iloc[0] / len(subset))
        summaries.append({
            "topic": topic, "cluster_id": cluster_id, "n_unique_texts": len(local),
            "n_pairs": subset["pair_id"].nunique(), "largest_pair_share": share,
            "sample_message_weight_sum": int(subset["group_only_frequency_in_sample"].sum()),
            "mean_original_centroid_cosine": float(scores.mean()),
            "median_membership_probability": float(np.median(probabilities[local]))
        })
        for kind, idx in (("central", top_indices), ("random", rand_indices)):
            for j in idx:
                row = result.iloc[int(j)]
                examples.append({"topic": topic, "cluster_id": cluster_id, "example_type": kind,
                                 "pair_id": row["pair_id"], "group_msg_id": row["group_msg_id"],
                                 "original_centroid_cosine": float(sample[j] @ center),
                                 "membership_probability": float(probabilities[j]), "text": row["text"]})

    if noise.any():
        noise_idx = rng.choice(np.flatnonzero(noise), size=min(30, int(noise.sum())), replace=False)
        for j in noise_idx:
            row = result.iloc[int(j)]
            examples.append({"topic": topic, "cluster_id": -1, "example_type": "noise_random",
                             "pair_id": row["pair_id"], "group_msg_id": row["group_msg_id"],
                             "original_centroid_cosine": np.nan, "membership_probability": float(probabilities[j]),
                             "text": row["text"]})

    summary_columns = ["topic", "cluster_id", "n_unique_texts", "n_pairs", "largest_pair_share", "sample_message_weight_sum", "mean_original_centroid_cosine", "median_membership_probability"]
    pd.DataFrame(summaries, columns=summary_columns).to_csv(output_dir / f"{topic}_cluster_summary.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(examples).to_csv(output_dir / f"{topic}_cluster_examples.csv", index=False, encoding="utf-8-sig")
    total = len(selected)
    information = {"topic": topic, "input_vectors": len(metadata), "sampled_vectors": total, "n_clusters": len(cluster_ids),
                   "noise_count": int(noise.sum()), "noise_fraction": float(noise.mean()),
                   "assigned_fraction": float((~noise).mean()),
                   "largest_cluster_fraction_of_assigned": float(max(np.bincount(labels[~noise])) / (~noise).sum()) if cluster_ids else None,
                   "median_cluster_size": float(np.median([int((labels == c).sum()) for c in cluster_ids])) if cluster_ids else None,
                   "projection_info": projection_info, "elapsed_seconds": round(time.perf_counter() - start_time, 2),
                   "caution": "Exploratory clusters. A label is NOT proof of a coherent topic; noise is not proof of irrelevant content."}
    print(f"[{topic}] {len(cluster_ids)} clusters; {int(noise.sum()):,}/{total:,} unassigned ({noise.mean():.1%}); elapsed {information['elapsed_seconds']:.1f}s", flush=True)
    return information


def main():
    parser = argparse.ArgumentParser(description="Point4 alternative density clustering PILOT; does not modify previous results.")
    parser.add_argument("--input-dir", type=Path, default=Path("data/interim/point4/full_analysis/clustering_input"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/interim/point4/full_analysis/clustering_density_pilot"))
    parser.add_argument("--sample-size", type=int, default=10000)
    parser.add_argument("--projection", choices=("umap", "svd"), default="umap")
    parser.add_argument("--components", type=int, default=15)
    parser.add_argument("--neighbors", type=int, default=30)
    parser.add_argument("--min-cluster-size", type=int, default=50)
    parser.add_argument("--min-samples", type=int, default=10)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--examples-per-cluster", type=int, default=5)
    args = parser.parse_args()
    if min(args.sample_size, args.components, args.neighbors, args.min_cluster_size, args.min_samples, args.threads, args.examples_per_cluster) < 1:
        parser.error("All numeric settings must be >=1")
    if args.sample_size <= max(args.components, args.min_cluster_size, args.neighbors):
        parser.error("sample-size must be greater than components, neighbors and min-cluster-size")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    report = {"experiment": "Density-based clustering pilot, same pair-stratified sample as stage2 KMeans", "seed": SEED,
              "method": "UMAP (Euclidean coordinates) / normalized SVD + HDBSCAN", "settings": {k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()}, "topics": {}}
    for topic in TOPICS:
        report["topics"][topic] = main_topic(topic, args, args.output_dir)
        (args.output_dir / "run_summary.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print("DONE - compare coverage AND example coherence before selecting final method", flush=True)


if __name__ == "__main__":
    main()

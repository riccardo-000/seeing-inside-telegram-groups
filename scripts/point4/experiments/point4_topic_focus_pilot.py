"""Point 4: exploratory topic-oriented clustering pilot (not population estimates).

Train only on the informative-length stratum of already-filtered group-only texts.
Preserve ALL source records and embeddings for the downstream functional-content analysis.
No Qwen or GPU inference. Requires cluster_point4_stage2.py in repository root.

Usage:
    python point4_topic_focus_pilot.py
"""
import argparse
import json
import re
import time
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import MiniBatchKMeans
from sklearn.decomposition import TruncatedSVD
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import normalize
from threadpoolctl import threadpool_limits

from cluster_point4_stage2 import sample_across_pairs, validated_inputs

SEED = 42
TOPICS = ("crypto", "conspiracy")


def canonical_text(value):
    """Conservative NFKC / invisible-format normalization only for FIT sampling."""
    text = unicodedata.normalize("NFKC", str(value))
    text = "".join(char for char in text if unicodedata.category(char) != "Cf")
    text = re.sub(r"\s+", " ", text).strip().casefold()
    return text


def run_topic(topic, args):
    start_time = time.perf_counter()
    embeddings, metadata = validated_inputs(args.input_dir, topic)
    n = len(metadata)
    text_lengths = metadata["text"].astype(str).str.len()
    eligible_mask = text_lengths >= args.min_chars
    eligible = metadata.loc[eligible_mask].copy()
    eligible.insert(0, "source_embedding_index", np.flatnonzero(eligible_mask.to_numpy()))
    eligible["canonical"] = eligible["text"].map(canonical_text)
    pre_dedup_n = len(eligible)
    # Do not allow slight visual/Unicode variants in the SAME pair to dominate fitting.
    eligible = eligible.drop_duplicates(subset=["pair_id", "canonical"], keep="first").reset_index(drop=True)
    post_dedup_n = len(eligible)
    if len(eligible) < max(args.clusters * 4, args.components + 2):
        raise RuntimeError(f"{topic}: too few eligible texts ({len(eligible)})")
    rng = np.random.default_rng(SEED if topic == "crypto" else SEED + 1)
    local_indices = sample_across_pairs(eligible["pair_id"].to_numpy(), min(args.fit_sample, len(eligible)), rng)
    selected = eligible.iloc[local_indices].copy().reset_index(drop=True)
    source_indices = selected["source_embedding_index"].to_numpy(dtype=np.int64)
    X = np.asarray(embeddings[source_indices], dtype=np.float32)
    normalize(X, copy=False)
    print(f"[{topic}] {n:,} total unique texts; >= {args.min_chars} chars {pre_dedup_n:,}; after fit-only canonical dedup {post_dedup_n:,}; fitting {len(selected):,} from {selected['pair_id'].nunique()} pairs", flush=True)
    with threadpool_limits(limits=args.threads):
        comps = min(args.components, X.shape[1] - 1, len(X)-1)
        svd = TruncatedSVD(n_components=comps, n_iter=3, random_state=SEED)
        Z = normalize(svd.fit_transform(X).astype(np.float32), copy=False)
        km = MiniBatchKMeans(n_clusters=args.clusters, n_init=3, batch_size=min(2048, len(X)), max_iter=100, random_state=SEED, reassignment_ratio=0.0)
        labels = km.fit_predict(Z)
        centers = normalize(km.cluster_centers_.astype(np.float32), copy=False)
        similarities = np.sum(Z * centers[labels], axis=1)
        eval_rows = rng.choice(len(X), size=min(1200,len(X)), replace=False)
        sil = float(silhouette_score(Z[eval_rows], labels[eval_rows], metric="cosine")) if len(np.unique(labels[eval_rows]))>1 else None
    selected["cluster_id"] = labels.astype(int)
    selected["center_cosine"] = similarities
    output_dir = args.output_dir
    selected[["source_embedding_index","topic","pair_id","group_msg_id","cluster_id","center_cosine","group_only_frequency_in_sample"]].to_csv(output_dir / f"{topic}_assignments.csv",index=False,encoding="utf-8-sig")
    summaries, examples = [], []
    for cluster_id, sub in selected.groupby("cluster_id", sort=True):
        central = sub.nlargest(args.examples_per_cluster,"center_cosine")
        remaining = sub.drop(index=central.index)
        random_rows = remaining.sample(n=min(args.examples_per_cluster,len(remaining)),random_state=SEED+int(cluster_id))
        largest = sub["pair_id"].value_counts().iloc[0]
        summaries.append({"topic":topic, "cluster_id":int(cluster_id), "n_sampled_texts":len(sub),
                          "n_pairs":sub["pair_id"].nunique(),"largest_pair_share":largest/len(sub),
                          "mean_center_cosine":float(sub["center_cosine"].mean()),
                          "sampled_frequency_sum":int(sub["group_only_frequency_in_sample"].sum())})
        for kind,chosen in (("central",central),("random",random_rows)):
            for _,r in chosen.iterrows():
                examples.append({"topic":topic,"cluster_id":int(cluster_id),"example_type":kind,"pair_id":r["pair_id"],
                                "group_msg_id":r["group_msg_id"],"center_cosine":r["center_cosine"],"text":r["text"]})
    pd.DataFrame(summaries).to_csv(output_dir / f"{topic}_cluster_summary.csv",index=False,encoding="utf-8-sig")
    pd.DataFrame(examples).to_csv(output_dir / f"{topic}_cluster_examples.csv",index=False,encoding="utf-8-sig")
    report = {"topic":topic,"all_unique_texts":int(n),"length_eligible":int(pre_dedup_n),"after_canonical_fit_dedup":int(post_dedup_n),
              "fit_sample":len(selected),"represented_pairs":int(selected["pair_id"].nunique()),"clusters":len(summaries),
              "svd_variance_sum":float(svd.explained_variance_ratio_.sum()),"sample_silhouette":sil,
              "seconds":round(time.perf_counter()-start_time,2),
              "warning":"DIAGNOSTIC ONLY: length >= cutoff is not proof of topical content, clusters are not validated topics, and sampling frequencies are not population prevalence."}
    print(f"[{topic}] {len(summaries)} clusters; silhouette={sil:.3f} if available; {report['seconds']:.1f} s",flush=True)
    return report


def main():
    parser=argparse.ArgumentParser(description="Exploratory clustering of the length-qualified group-only stratum")
    parser.add_argument("--input-dir",type=Path,default=Path("data/interim/point4/full_analysis/clustering_input"))
    parser.add_argument("--output-dir",type=Path,default=Path("data/interim/point4/full_analysis/clustering_topic_focus_pilot"))
    parser.add_argument("--min-chars",type=int,default=40)
    parser.add_argument("--fit-sample",type=int,default=10000)
    parser.add_argument("--clusters",type=int,default=30)
    parser.add_argument("--components",type=int,default=64)
    parser.add_argument("--examples-per-cluster",type=int,default=8)
    parser.add_argument("--threads",type=int,default=4)
    args=parser.parse_args()
    if min(args.min_chars,args.fit_sample,args.clusters,args.components,args.examples_per_cluster,args.threads)<1 or args.fit_sample<=max(args.clusters,args.components):
        parser.error("Invalid numeric settings")
    args.output_dir.mkdir(parents=True,exist_ok=True)
    result={"method":"Length-qualified, per-pair NFKC-deduplicated fit sample + SVD + MiniBatchKMeans", "seed":SEED,
            "configuration":{k:str(v) if isinstance(v,Path) else v for k,v in vars(args).items()},"topics":{}}
    for topic in TOPICS:
        result["topics"][topic]=run_topic(topic,args)
        (args.output_dir / "run_summary.json").write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding="utf-8")
    print("DONE. Review random AND central examples. Do not treat all sampled clusters as validated topics.",flush=True)

if __name__=="__main__":
    main()

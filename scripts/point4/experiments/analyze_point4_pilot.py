import sys
import time
import hashlib
import json
from pathlib import Path

sys.path.insert(0, ".")

import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F

from transformers import AutoTokenizer
from optimum.intel import OVModelForFeatureExtraction

from src.analyze.load import iter_pairs


# ============================================================
# POINT 4 — PILOT (3 CRYPTO + 3 CONSPIRACY)
# ============================================================

MODEL_ID = "OpenVINO/Qwen3-Embedding-0.6B-int8-ov"

DEVICE = "GPU"

MAX_LENGTH = 512
BATCH_SIZE = 8

MAX_GROUP_MESSAGES_PER_PAIR = 5000
MIN_CHARS = 5
PILOT_PAIRS_PER_TOPIC = 3

RANDOM_SEED = 42

# Calibrated threshold + sensitivity thresholds.
THRESHOLDS = {
    "t050": 0.50,
    "t052": 0.52,
    "t055": 0.55,
}

MAIN_THRESHOLD = 0.52

TOPICS = ["crypto", "conspiracy"]

TASK = (
    "Given a Telegram group message, retrieve channel posts "
    "that discuss the same topic, event, entity, claim, or activity"
)

QUERY_PROMPT = f"Instruct: {TASK}\nQuery:"


# ============================================================
# OUTPUTS / CHECKPOINTS
# ============================================================

OUTPUT_DIR = Path("data/interim/point4/pilot_analysis")
PAIR_DIR = OUTPUT_DIR / "pairs"
EMBED_DIR = OUTPUT_DIR / "group_only_embeddings"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
PAIR_DIR.mkdir(parents=True, exist_ok=True)
EMBED_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# HELPERS
# ============================================================

def stable_seed(text):
    digest = hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()

    return int(digest[:8], 16)


def safe_pair_name(pair_id):
    return (
        pair_id
        .replace(":", "__")
        .replace("/", "_")
        .replace("\\", "_")
    )


def channel_candidates(df):
    return df[
        (df["side"] == "channel") &
        (df["in_window"]) &
        (~df["is_service"]) &
        (df["has_text"])
    ].copy()


def group_candidates(df):
    """
    Free-group human messages for Point 4.

    Short messages are intentionally NOT removed here.
    They are sampled with the same population as Point 3 and
    later reported separately as chit-chat.

    Content analysis excludes:
      - service messages
      - channel-post comments
      - bots
      - empty text
      - channel copies / other-channel voices

    The existing 'voice' field is used so that the role logic
    stays consistent with the Point 3 / calibration pipeline.
    """
    return df[
        (df["side"] == "group") &
        (df["in_window"]) &
        (~df["is_service"]) &
        (~df["is_comment"]) &
        (~df["is_bot"]) &
        (df["has_text"]) &
        (df["voice"].isin(["admin", "user"]))
    ].copy()


def sample_group_messages(groups, pair_id):
    """
    Same Point-3 sampling rule:
      up to 5,000 messages per pair, deterministic fixed seed;
      all messages if fewer than 5,000.
    """
    n = min(
        MAX_GROUP_MESSAGES_PER_PAIR,
        len(groups)
    )

    if len(groups) <= MAX_GROUP_MESSAGES_PER_PAIR:
        sampled = groups.copy()
    else:
        sampled = groups.sample(
            n=n,
            random_state=stable_seed(
                f"{RANDOM_SEED}:group:{pair_id}"
            ),
        ).copy()

    return sampled.reset_index(drop=True)


def get_query_instruction(text):
    return f"{QUERY_PROMPT}{text}"


def last_token_pool(last_hidden_states, attention_mask):
    left_padding = (
        attention_mask[:, -1].sum()
        == attention_mask.shape[0]
    )

    if left_padding:
        return last_hidden_states[:, -1]

    sequence_lengths = (
        attention_mask.sum(dim=1) - 1
    )

    batch_size = last_hidden_states.shape[0]

    return last_hidden_states[
        torch.arange(
            batch_size,
            device=last_hidden_states.device
        ),
        sequence_lengths,
    ]


def encode(texts, tokenizer, model, is_query):
    if not texts:
        return np.empty(
            (0, 1024),
            dtype=np.float32
        )

    if is_query:
        texts = [
            get_query_instruction(x)
            for x in texts
        ]

    all_embeddings = []

    for start in range(0, len(texts), BATCH_SIZE):

        batch_texts = texts[
            start:start + BATCH_SIZE
        ]

        inputs = tokenizer(
            batch_texts,
            padding=True,
            truncation=True,
            max_length=MAX_LENGTH,
            return_tensors="pt",
        )

        with torch.no_grad():
            outputs = model(**inputs)

            embeddings = last_token_pool(
                outputs.last_hidden_state,
                inputs["attention_mask"],
            )

            embeddings = F.normalize(
                embeddings,
                p=2,
                dim=1,
            )

        all_embeddings.append(
            embeddings.detach().cpu().numpy().astype(
                np.float32,
                copy=False,
            )
        )

    return np.concatenate(
        all_embeddings,
        axis=0,
    )


def compute_best_matches(
    group_embeddings,
    channel_embeddings,
    group_batch_size=16,
):
    """
    For every group embedding, find the most similar channel
    embedding without materializing the full group x channel
    matrix.
    """
    n_groups = len(group_embeddings)

    best_scores = np.full(
        n_groups,
        -np.inf,
        dtype=np.float32,
    )

    best_indices = np.full(
        n_groups,
        -1,
        dtype=np.int64,
    )

    channel_tensor = torch.from_numpy(
        channel_embeddings
    )

    for start in range(
        0,
        n_groups,
        group_batch_size,
    ):
        end = min(
            start + group_batch_size,
            n_groups,
        )

        group_tensor = torch.from_numpy(
            group_embeddings[start:end]
        )

        similarities = (
            group_tensor @ channel_tensor.T
        )

        values, indices = torch.max(
            similarities,
            dim=1,
        )

        best_scores[start:end] = (
            values.numpy()
        )

        best_indices[start:end] = (
            indices.numpy()
        )

    return best_scores, best_indices


def append_csv(df, path):
    write_header = not path.exists()

    df.to_csv(
        path,
        mode="a",
        header=write_header,
        index=False,
        encoding="utf-8-sig",
    )


def pair_done_path(pair_id):
    return PAIR_DIR / (
        safe_pair_name(pair_id) + ".done"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("POINT 4 — PILOT (3 CRYPTO + 3 CONSPIRACY)")
    print("=" * 70)

    print("\nConfiguration:")
    print(f"  Device: {DEVICE}")
    print(f"  Model: {MODEL_ID}")
    print(f"  Batch size: {BATCH_SIZE}")
    print(
        "  Max group messages/pair: "
        f"{MAX_GROUP_MESSAGES_PER_PAIR}"
    )
    print(f"  Min chars for embedding: {MIN_CHARS}")
    print(f"  Main threshold: {MAIN_THRESHOLD}")
    print(
        "  Sensitivity thresholds: "
        f"{list(THRESHOLDS.values())}"
    )
    print(f"  Random seed: {RANDOM_SEED}")
    print(f"  Pilot pairs per topic: {PILOT_PAIRS_PER_TOPIC}")

    # --------------------------------------------------------
    # Load all pairs and determine sample
    # --------------------------------------------------------

    pair_data = []

    print("\nScanning pairs and building Point-3-compatible sample...")

    for topic in TOPICS:

        print(f"\n--- {topic.upper()} ---")

        for pair, df in iter_pairs(topic):

            pair_id = pair["pair_id"]

            groups = group_candidates(df)

            if groups.empty:
                continue

            sampled = sample_group_messages(
                groups,
                pair_id,
            )

            channels = channel_candidates(df)

            if channels.empty:
                print(
                    f"SKIP {pair_id}: no channel posts"
                )
                continue

            pair_data.append(
                {
                    "topic": topic,
                    "pair": pair,
                    "pair_id": pair_id,
                    "channels": channels,
                    "groups": sampled,
                }
            )

            print(
                f"{pair_id}: "
                f"{len(channels)} channel posts, "
                f"{len(sampled)} sampled group messages"
            )

    # Pick small / median / large workloads in each topic for a
    # more informative runtime pilot than the first three pairs.
    # Sampling WITHIN each selected pair remains unchanged.
    all_pair_data = pair_data
    pair_data = []

    print("\nSelecting three workload-diverse pairs per topic...")
    for topic in TOPICS:
        candidates = [
            item for item in all_pair_data
            if item["topic"] == topic
            and (item["groups"]["n_chars"] >= MIN_CHARS).any()
        ]

        if len(candidates) < PILOT_PAIRS_PER_TOPIC:
            raise RuntimeError(
                f"{topic}: only {len(candidates)} eligible pairs; "
                f"need {PILOT_PAIRS_PER_TOPIC} for pilot."
            )

        def workload(item):
            # Unique texts approximate the number of actual model calls.
            long_groups = item["groups"].loc[
                item["groups"]["n_chars"] >= MIN_CHARS, "text"
            ]
            return int(item["channels"]["text"].nunique() + long_groups.nunique())

        candidates.sort(key=lambda item: (workload(item), item["pair_id"]))
        positions = [0, len(candidates) // 2, len(candidates) - 1]
        chosen = [candidates[i] for i in positions]
        pair_data.extend(chosen)

        for rank, item in zip(["small", "median", "large"], chosen):
            print(
                f"  {topic} / {rank}: {item['pair_id']} "
                f"(estimated unique texts: {workload(item)})"
            )

    print("\n" + "=" * 70)
    print("SAMPLE SUMMARY")
    print("=" * 70)

    total_channels = sum(
        len(x["channels"])
        for x in pair_data
    )

    total_groups = sum(
        len(x["groups"])
        for x in pair_data
    )

    total_short = sum(
        (
            x["groups"]["n_chars"] < MIN_CHARS
        ).sum()
        for x in pair_data
    )

    total_long = total_groups - total_short

    print(f"Pairs: {len(pair_data)}")
    print(f"Channel posts: {total_channels}")
    print(f"Sampled group messages: {total_groups}")
    print(f"Short/chit-chat messages: {total_short}")
    print(f"Meaningful messages (>= {MIN_CHARS} chars): {total_long}")

    # Save the sampling metadata before the expensive model run.
    sampling_rows = []

    for item in pair_data:

        groups = item["groups"]

        sampling_rows.append(
            {
                "topic": item["topic"],
                "pair_id": item["pair_id"],
                "n_channel_posts": len(
                    item["channels"]
                ),
                "n_group_sample": len(groups),
                "n_short_chit_chat": int(
                    (
                        groups["n_chars"]
                        < MIN_CHARS
                    ).sum()
                ),
                "n_meaningful": int(
                    (
                        groups["n_chars"]
                        >= MIN_CHARS
                    ).sum()
                ),
            }
        )

    pd.DataFrame(
        sampling_rows
    ).to_csv(
        OUTPUT_DIR / "sampling_summary.csv",
        index=False,
        encoding="utf-8-sig",
    )

    # --------------------------------------------------------
    # Load model
    # --------------------------------------------------------

    print("\nLoading tokenizer...")

    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_ID,
        padding_side="left",
    )

    print("\nLoading INT8 OpenVINO model...")

    load_start = time.perf_counter()

    model = OVModelForFeatureExtraction.from_pretrained(
        MODEL_ID,
        export=False,
    )

    model.to(DEVICE)

    load_time = (
        time.perf_counter()
        - load_start
    )

    print(
        f"Model load time: "
        f"{load_time:.2f} s"
    )
    print(
        "Model device:",
        model.device,
    )

    # --------------------------------------------------------
    # Aggregate outputs are rebuilt from per-pair checkpoints
    # at the end. This makes the whole run safely resumable.
    # --------------------------------------------------------

    message_output = (
        OUTPUT_DIR / "message_results.csv"
    )

    pair_output = (
        OUTPUT_DIR / "pair_results.csv"
    )

    if message_output.exists():
        message_output.unlink()

    if pair_output.exists():
        pair_output.unlink()

    total_start = time.perf_counter()

    # --------------------------------------------------------
    # Process each pair independently
    # --------------------------------------------------------

    processed = 0

    for item in pair_data:

        pair_id = item["pair_id"]
        topic = item["topic"]

        done_path = pair_done_path(
            pair_id
        )

        if done_path.exists():
            print(
                f"\n[{processed + 1}/"
                f"{len(pair_data)}] "
                f"{pair_id}: checkpoint exists, "
                f"skipping."
            )
            processed += 1
            continue

        print("\n" + "-" * 70)
        print(
            f"[{processed + 1}/{len(pair_data)}] "
            f"{pair_id}"
        )
        print("-" * 70)

        channels = item["channels"]
        groups = item["groups"]

        meaningful = groups[
            groups["n_chars"] >= MIN_CHARS
        ].copy()

        if meaningful.empty:
            pair_row = {
                "topic": topic,
                "pair_id": pair_id,
                "n_group_sample": len(groups),
                "n_short_chit_chat": len(groups),
                "n_meaningful": 0,
                "n_group_only_t050": 0,
                "n_group_only_t052": 0,
                "n_group_only_t055": 0,
                "rate_t050": np.nan,
                "rate_t052": np.nan,
                "rate_t055": np.nan,
                "median_similarity": np.nan,
            }

            pair_message_output = (
                PAIR_DIR
                / (
                    safe_pair_name(pair_id)
                    + "_messages.csv"
                )
            )

            pd.DataFrame(
                columns=[
                    "topic",
                    "pair_id",
                    "group_msg_id",
                    "group_date",
                    "role",
                    "n_chars",
                    "text",
                    "similarity",
                    "best_channel_msg_id",
                    "group_only_t050",
                    "group_only_t052",
                    "group_only_t055",
                ]
            ).to_csv(
                pair_message_output,
                index=False,
                encoding="utf-8-sig",
            )

            pair_summary_output = (
                PAIR_DIR
                / (
                    safe_pair_name(pair_id)
                    + "_summary.json"
                )
            )

            pair_summary_output.write_text(
                json.dumps(
                    pair_row,
                    indent=2,
                    default=float,
                ),
                encoding="utf-8",
            )

            done_path.write_text(
                "done\n",
                encoding="utf-8",
            )

            processed += 1
            continue

        # ----------------------------------------------------
        # Exact duplicate channel texts can be embedded once.
        # This does NOT change max similarity because duplicate
        # documents have identical embeddings.
        # ----------------------------------------------------

        channel_unique = (
            channels[
                ["msg_id", "date", "text"]
            ]
            .drop_duplicates(
                subset=["text"],
                keep="first",
            )
            .reset_index(drop=True)
        )

        channel_texts = (
            channel_unique["text"]
            .astype(str)
            .tolist()
        )

        # Same optimisation for group embeddings: duplicate
        # group texts keep separate rows/counts, but the embedding
        # itself only needs to be computed once.
        group_unique = (
            meaningful[
                ["text"]
            ]
            .drop_duplicates(
                subset=["text"],
                keep="first",
            )
            .reset_index(drop=True)
        )

        group_texts = (
            group_unique["text"]
            .astype(str)
            .tolist()
        )

        print(
            f"Channel posts: {len(channels)} "
            f"({len(channel_unique)} unique texts)"
        )

        print(
            f"Meaningful group messages: "
            f"{len(meaningful)} "
            f"({len(group_unique)} unique texts)"
        )

        # ----------------------------------------------------
        # Embeddings
        # ----------------------------------------------------

        start = time.perf_counter()

        channel_embeddings = encode(
            channel_texts,
            tokenizer,
            model,
            is_query=False,
        )

        channel_time = (
            time.perf_counter()
            - start
        )

        start = time.perf_counter()

        group_unique_embeddings = encode(
            group_texts,
            tokenizer,
            model,
            is_query=True,
        )

        group_time = (
            time.perf_counter()
            - start
        )

        # ----------------------------------------------------
        # Similarity
        # ----------------------------------------------------

        start = time.perf_counter()

        best_scores, best_indices = (
            compute_best_matches(
                group_unique_embeddings,
                channel_embeddings,
            )
        )

        similarity_time = (
            time.perf_counter()
            - start
        )

        group_unique["similarity"] = (
            best_scores
        )

        group_unique["best_channel_index"] = (
            best_indices
        )

        group_unique["best_channel_msg_id"] = [
            int(
                channel_unique.iloc[int(i)]["msg_id"]
            )
            for i in best_indices
        ]

        # Map the unique-text results back to every sampled
        # group message, preserving duplicate messages.
        score_map = dict(
            zip(
                group_unique["text"],
                group_unique["similarity"],
            )
        )

        index_map = dict(
            zip(
                group_unique["text"],
                group_unique[
                    "best_channel_msg_id"
                ],
            )
        )

        meaningful["similarity"] = (
            meaningful["text"].map(score_map)
        )

        meaningful[
            "best_channel_msg_id"
        ] = (
            meaningful["text"].map(index_map)
        )

        # ----------------------------------------------------
        # Labels for all three thresholds
        # ----------------------------------------------------

        for label, threshold in THRESHOLDS.items():

            meaningful[
                f"group_only_{label}"
            ] = (
                meaningful["similarity"]
                < threshold
            )

        # ----------------------------------------------------
        # Save group-only embeddings for the main threshold.
        # One row per sampled message, including duplicates.
        # This is what the later clustering stage needs.
        # ----------------------------------------------------

        main_mask = (
            meaningful[
                "group_only_t052"
            ].to_numpy()
        )

        if main_mask.any():

            unique_group_only = (
                group_unique[
                    group_unique[
                        "similarity"
                    ] < MAIN_THRESHOLD
                ]
            )

            unique_embeddings = (
                group_unique_embeddings[
                    unique_group_only.index.to_numpy()
                ]
            )

            # Map the unique embeddings back to every
            # group-only message, including duplicates.
            unique_embedding_map = {
                text: emb
                for text, emb in zip(
                    unique_group_only["text"],
                    unique_embeddings,
                )
            }

            message_embeddings = np.stack(
                [
                    unique_embedding_map[text]
                    for text in meaningful.loc[
                        main_mask,
                        "text"
                    ]
                ]
            ).astype(
                np.float32,
                copy=False,
            )

            np.save(
                EMBED_DIR / (
                    safe_pair_name(pair_id)
                    + ".npy"
                ),
                message_embeddings,
            )

        # ----------------------------------------------------
        # Message-level output
        #
        # IMPORTANT: save one file per pair. The final aggregate
        # is rebuilt from these files, so an interrupted run never
        # forces us to recompute completed pairs.
        # ----------------------------------------------------

        meaningful_output = meaningful[
            [
                "topic",
                "pair_id",
                "msg_id",
                "date",
                "role",
                "n_chars",
                "text",
                "similarity",
                "best_channel_msg_id",
                "group_only_t050",
                "group_only_t052",
                "group_only_t055",
            ]
        ].copy()

        meaningful_output.rename(
            columns={
                "msg_id": "group_msg_id",
                "date": "group_date",
            },
            inplace=True,
        )

        pair_message_output = (
            PAIR_DIR
            / (
                safe_pair_name(pair_id)
                + "_messages.csv"
            )
        )

        meaningful_output.to_csv(
            pair_message_output,
            index=False,
            encoding="utf-8-sig",
        )

        # ----------------------------------------------------
        # Pair summary
        # ----------------------------------------------------

        n_meaningful = len(meaningful)

        pair_row = {
            "topic": topic,
            "pair_id": pair_id,
            "n_channel_posts": len(channels),
            "n_channel_unique_texts": len(
                channel_unique
            ),
            "n_group_sample": len(groups),
            "n_short_chit_chat": int(
                (
                    groups["n_chars"]
                    < MIN_CHARS
                ).sum()
            ),
            "n_meaningful": n_meaningful,
            "n_group_only_t050": int(
                meaningful[
                    "group_only_t050"
                ].sum()
            ),
            "n_group_only_t052": int(
                meaningful[
                    "group_only_t052"
                ].sum()
            ),
            "n_group_only_t055": int(
                meaningful[
                    "group_only_t055"
                ].sum()
            ),
            "rate_t050": float(
                meaningful[
                    "group_only_t050"
                ].mean()
            ),
            "rate_t052": float(
                meaningful[
                    "group_only_t052"
                ].mean()
            ),
            "rate_t055": float(
                meaningful[
                    "group_only_t055"
                ].mean()
            ),
            "chit_chat_rate_all_sample": float(
                (
                    groups["n_chars"]
                    < MIN_CHARS
                ).mean()
            ),
            "median_similarity": float(
                meaningful[
                    "similarity"
                ].median()
            ),
            "p25_similarity": float(
                meaningful[
                    "similarity"
                ].quantile(0.25)
            ),
            "p75_similarity": float(
                meaningful[
                    "similarity"
                ].quantile(0.75)
            ),
            "channel_embedding_time_s": channel_time,
            "group_embedding_time_s": group_time,
            "similarity_time_s": similarity_time,
        }

        # ----------------------------------------------------
        # Save per-pair checkpoint metadata
        # ----------------------------------------------------

        # Final aggregation reads these per-pair JSON summaries.
        # The original script only created them for empty pairs,
        # causing the aggregate step to fail for normal pairs.
        pair_summary_output = (
            PAIR_DIR / (safe_pair_name(pair_id) + "_summary.json")
        )
        pair_summary_output.write_text(
            json.dumps(pair_row, indent=2),
            encoding="utf-8",
        )

        checkpoint = {
            "topic": topic,
            "pair_id": pair_id,
            "n_channel_posts": len(channels),
            "n_channel_unique_texts": len(
                channel_unique
            ),
            "n_group_sample": len(groups),
            "n_meaningful": n_meaningful,
            "n_group_only_t052": int(
                meaningful[
                    "group_only_t052"
                ].sum()
            ),
            "thresholds": THRESHOLDS,
            "channel_embedding_time_s": channel_time,
            "group_embedding_time_s": group_time,
            "similarity_time_s": similarity_time,
        }

        done_path.write_text(
            json.dumps(
                checkpoint,
                indent=2,
            ),
            encoding="utf-8",
        )

        elapsed = (
            time.perf_counter()
            - total_start
        )

        processed += 1

        print(
            f"Similarity done in "
            f"{similarity_time:.2f} s"
        )

        print(
            f"Group-only @0.52: "
            f"{pair_row['n_group_only_t052']}/"
            f"{n_meaningful} "
            f"({pair_row['rate_t052']:.2%})"
        )

        print(
            f"Pair time: "
            f"{channel_time + group_time + similarity_time:.1f} s"
        )

        print(
            f"Elapsed total: "
            f"{elapsed / 3600:.2f} h"
        )

    # --------------------------------------------------------
    # Final aggregation
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("AGGREGATING POINT 4 RESULTS")
    print("=" * 70)

    summary_files = sorted(
        PAIR_DIR.glob("*_summary.json")
    )

    pair_rows = []

    for summary_file in summary_files:
        pair_rows.append(
            json.loads(
                summary_file.read_text(
                    encoding="utf-8"
                )
            )
        )

    pair_results = pd.DataFrame(
        pair_rows
    )

    pair_results = pair_results.sort_values(
        ["topic", "pair_id"]
    ).reset_index(drop=True)

    pair_results.to_csv(
        pair_output,
        index=False,
        encoding="utf-8-sig",
    )

    # Rebuild the complete message file from pair-level files.
    # This avoids holding all text in memory at once.
    if message_output.exists():
        message_output.unlink()

    message_files = sorted(
        PAIR_DIR.glob("*_messages.csv")
    )

    for message_file in message_files:
        chunk = pd.read_csv(
            message_file
        )
        if chunk.empty:
            continue
        append_csv(
            chunk,
            message_output,
        )

    # Pair-weighted summary: every pair has equal weight.
    summary_rows = []

    for topic in TOPICS:

        subset = pair_results[
            pair_results["topic"] == topic
        ]

        if subset.empty:
            continue

        for label, threshold in THRESHOLDS.items():

            values = subset[
                f"rate_{label}"
            ].dropna()

            summary_rows.append(
                {
                    "topic": topic,
                    "threshold": threshold,
                    "n_pairs": len(values),
                    "mean_pair_rate": values.mean(),
                    "median_pair_rate": values.median(),
                    "std_pair_rate": values.std(
                        ddof=1
                    ),
                    "q25_pair_rate": values.quantile(
                        0.25
                    ),
                    "q75_pair_rate": values.quantile(
                        0.75
                    ),
                }
            )

    summary = pd.DataFrame(
        summary_rows
    )

    summary.to_csv(
        OUTPUT_DIR / "topic_summary.csv",
        index=False,
        encoding="utf-8-sig",
    )

    # Pooled counts are descriptive only. The pair-weighted
    # summary above remains the primary comparison unit.
    pooled_rows = []

    for topic in TOPICS:

        subset = pair_results[
            pair_results["topic"] == topic
        ]

        if subset.empty:
            continue

        pooled_rows.append(
            {
                "topic": topic,
                "sampled_group_messages": int(
                    subset[
                        "n_group_sample"
                    ].sum()
                ),
                "short_chit_chat": int(
                    subset[
                        "n_short_chit_chat"
                    ].sum()
                ),
                "meaningful_messages": int(
                    subset[
                        "n_meaningful"
                    ].sum()
                ),
                "group_only_t050": int(
                    subset[
                        "n_group_only_t050"
                    ].sum()
                ),
                "group_only_t052": int(
                    subset[
                        "n_group_only_t052"
                    ].sum()
                ),
                "group_only_t055": int(
                    subset[
                        "n_group_only_t055"
                    ].sum()
                ),
            }
        )

    pd.DataFrame(
        pooled_rows
    ).to_csv(
        OUTPUT_DIR / "pooled_summary.csv",
        index=False,
        encoding="utf-8-sig",
    )

    print("\n" + "=" * 70)
    print("POINT 4 ANALYSIS COMPLETE")
    print("=" * 70)

    print(
        f"Pairs processed/available: "
        f"{len(pair_results)}"
    )
    for topic in TOPICS:
        subset = pair_results[pair_results["topic"] == topic]
        measured_seconds = subset[
            ["channel_embedding_time_s", "group_embedding_time_s", "similarity_time_s"]
        ].sum().sum()
        print(f"  {topic} measured model+similarity time: {measured_seconds / 60:.1f} min")

    print(
        "\nPair-weighted summary:"
    )

    print(
        summary.to_string(
            index=False
        )
    )

    print(
        "\nOutputs:"
    )
    print(
        f"  {OUTPUT_DIR / 'message_results.csv'}"
    )
    print(
        f"  {OUTPUT_DIR / 'pair_results.csv'}"
    )
    print(
        f"  {OUTPUT_DIR / 'topic_summary.csv'}"
    )
    print(
        f"  {OUTPUT_DIR / 'pooled_summary.csv'}"
    )
    print(
        f"  {EMBED_DIR}"
    )



if __name__ == "__main__":
    main()

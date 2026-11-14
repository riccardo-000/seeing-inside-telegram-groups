# Point 4 — Supplementary methods and sensitivity analyses

## Data lineage and units

- **Pair-level population:** 195 linked channel–discussion-group pairs, 98 crypto and 97 conspiracy. All comparisons of mean rates are **pair-equal** unless noted.
- **Channel text corpus:** 134,984 observed posts (134,984 is a count of posts, not distinct texts). The median number of *distinct* channel posts per pair is 83 crypto and 237 conspiracy.
- **Group sample:** 513,973 group message instances from the original maximum-5,000-per-pair sampling protocol, with upstream service/bot exclusion. 40,411 messages shorter than five characters were not embedded; 473,562 were embedded.
- **Semantically eligible:** remove URL-only, mention-only and other non-lexical messages from the primary analysis, preserving messages with actual text even if they contain links. 24,541 URL-only + 1,883 mention-only + 1,554 other non-lexical = 27,978 excluded; 473,562 − 27,978 = **445,584** eligible.
- **Operational non-aligned:** 334,080 messages below the calibrated threshold 0.52 (169,406 crypto and 164,674 conspiracy).
- **Clustering population:** 284,068 distinct (per-pair) group-only texts, not the same unit as the message-frequency denominator. Exploratory clustering proceeded separately by category. A >=40-character fit-only filter and small pilot samples were used for interpretability diagnostics, not for full-dataset prevalence.
- **Exploratory content sample:** six group-only message instances selected without replacement from each pair (1,170 total), not deduplicated texts. The sampling frame is the **already sampled** group message corpus.

## Embeddings and matching

The retrieval implementation used normalized embeddings produced by `OpenVINO/Qwen3-Embedding-0.6B-int8-ov`, maximum token length 512, batch size 8, with an instruction prefix on group-query embeddings (`Instruct: Given a Telegram group message, retrieve channel posts that discuss the same topic, event, entity, claim, or activity`) and document embeddings for channel posts. For each eligible group message, the maximum cosine similarity across the available linked channel posts was recorded. The threshold of 0.52 was chosen from an independent 100-example calibration exercise, with 0.50 and 0.55 used only for sensitivity. Neither cross-encoder verification nor time-constrained retrieval is part of the current pipeline.

## Sensitivity results (unweighted means of per-pair rates)

| Similarity cutoff | Crypto | Conspiracy | Difference (conspiracy minus crypto) |
|---|---:|---:|---:|
| 0.50 | 69.42% | 69.94% | +0.52 pp |
| **0.52 primary** | **74.68%** | **76.11%** | **+1.43 pp** |
| 0.55 | 80.56% | 83.37% | +2.81 pp |

| Counting policy at cutoff 0.52 | Crypto | Conspiracy |
|---|---:|---:|
| Original embedded (before text eligibility filter) | 74.46% | 75.09% |
| **Semantically eligible messages (primary)** | **74.68%** | **76.11%** |
| Unique normalized texts within each pair | 74.84% | 75.73% |
| Text frequency capped at five per pair | 75.11% | 75.89% |

Within-pair duplication can change individual pair rates substantially even when the pair-equal category means remain similar.

## Channel-size strata

| Distinct channel posts | Crypto: pairs, mean | Conspiracy: pairs, mean |
|---|---:|---:|
| 1–9 | 10, 89.33% | 6, 99.63% |
| 10–49 | 27, 78.31% | 12, 94.03% |
| 50–199 | 33, 76.29% | 26, 88.11% |
| 200–999 | 22, 65.81% | 38, 72.68% |
| 1,000 or more | 6, 57.60% | 15, 40.23% |

Across categories, greater channel-post count correlates with lower non-alignment; Spearman's rho is −0.420 (crypto; bootstrap CI −0.585 to −0.231) and −0.827 (conspiracy; CI −0.892 to −0.727). A supplementary additive OLS fit found an association of −5.22 percentage points per doubling of channel size (HC3 95% CI −6.16 to −4.28); however, topic-by-size interaction was evident (exploratory p=0.000625), so no single adjusted topic coefficient is suitable as a primary conclusion. These are observational associations with structural sensitivity built into maximum-over-candidates matching.

## Exploratory coding and sampling

The separate Stage 4 content sample contains 588 crypto and 582 conspiracy messages, six drawn per pair. Function and primary subject were assigned separately; interpretability and promotional intent were supplementary flags. Text was assessed without opening linked URLs, and insufficiently clear messages could receive `Unclear`. The pipeline was a documented, rule-guided **single coding pass** with targeted case checks; it did not produce a human ground truth or an inter-annotator agreement statistic. It has not undergone independent accuracy validation. The label estimates and 95% bootstrap intervals reflect message/pair sampling only, conditional on the assigned labels.

**Length check:** 66.3% of sampled crypto messages and 29.4% of conspiracy messages were shorter than 40 characters. For <40-character messages, the *message-level* shares assigned to greeting/social were 30.3% crypto (n=390) and 11.7% conspiracy (n=171); information/news were 0.3% and 0.6%. For messages >=40 characters, greeting/social were 2.5% crypto (n=198) and 1.2% conspiracy (n=411), while information/news were 7.1% and 31.4%, respectively. These length-stratified summaries use a **different estimand** (message-level, not equal pair weights) and do not remove all language and sampling confounds.

**Quality diagnostics:** 582/1,170 codes (49.7%) have low coding confidence; 220/1,170 (18.8%) were flagged as uncertain in interpretability. Such uncertainty is not represented by the bootstrap intervals. Near-zero assignments to a topic in this small sample are not evidence of genuine absence: percentile resampling of an observed zero cell cannot recover unseen labels.

## Clustering pilot status

MiniBatchKMeans and UMAP+HDBSCAN pilots were performed as exploratory discovery/diagnostic techniques, but the 60 later 30-cluster-per-topic KMeans groups did not yield 60 validated topics. On a four-example-per-cluster pilot review, only 14 of 60 cluster candidates had a dominant subject in at least three examples; 43 were mixed/weakly supported and three predominantly non-thematic/uncertain. Consequently, no cluster-size-based topic prevalence is reported.

## Interpretation constraints

- A maximum cosine similarity below 0.52 is a property of the defined model, sampled channel corpus and threshold; it does **not** prove that a message originated independently or that the topic is novel.
- The matching channel corpus may include posts later than the group message. Temporal precedence cannot be inferred.
- The 195 pairs are observed samples, not a random sample of all Telegram communities; the group-message quota introduces additional sampling bounds.
- The labels are exploratory because their independent precision/recall and inter-annotator reliability are unknown. These limitations matter especially for theme percentages and between-category contrasts.

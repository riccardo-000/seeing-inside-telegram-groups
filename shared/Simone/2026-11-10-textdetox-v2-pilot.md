# TextDetox v2 — Local toxicity classification pilot (conspiracy arm)

**Author:** Simone  
**Date:** 2026-11-10  
**Status:** Exploratory pilot — not a validated result for the paper

## 1. Objective

Evaluate whether a pre-trained multilingual text classifier can be run locally on the collected conspiracy-related Telegram messages, measure inference speed, and prepare a small sample for human inspection.

This pilot relates to **Section 3 (Tone)** and **Section 5b (Conspiracy — tone)** of `docs/analysis-plan.md`. It does **not** implement the full study design or replace the agreed analysis plan.

## 2. Model and approach

- **Model:** `textdetox/xlmr-large-toxicity-classifier-v2` (Hugging Face; XLM-R-based multilingual toxicity classifier).
- **Task:** Binary toxicity classification, with output labels 0 (non-toxic/neutral) and 1 (toxic).
- **Score:** Model softmax score for the toxic class, from 0 to 1.
- **Provisional decision threshold:** 0.50. **Not calibrated or validated on our Telegram data.**
- **Approach:** Direct inference using the **already trained model**. **No fine-tuning or training** has been carried out.
- **Execution:** Local CPU inference, without submitting Telegram messages to a hosted LLM/API. Model files were downloaded from Hugging Face on first use and cached locally.

**Important distinction:** Toxicity is not equivalent to sentiment, dangerousness, illegal content, or a proposed 0–5 aggression scale. This model does not directly produce any of those classifications.

## 3. Local environment

| Item | Configuration |
| --- | --- |
| Computer | AMD Ryzen AI 7 350, Radeon 860M integrated graphics, 32 GB RAM |
| Operating system / terminal | Windows, Command Prompt |
| Python | 3.11.9 |
| Environment | Local `.venv/` inside the project (Git-ignored) |
| Main software | CPU PyTorch, Transformers, SentencePiece, Safetensors, tqdm |
| Acceleration | CPU only in this pilot; GPU/NPU not benchmarked |
| Model download | Approx. 2.24 GB model weights, held in the local Hugging Face cache (not committed) |

The pilot scripts were kept locally, outside the shared analysis pipeline:
- `telegram_textdetox_test.py`: reads existing compressed message dumps, samples messages, performs inference, and writes scores and run metadata.
- `textdetox_review_local.py`: matches saved scores back to source records, so original text can be inspected **locally** by a human reviewer.

These scripts are **not claimed to be committed or integrated** into `src/analyze/` as of this report.

## 4. Input, sampling, and outputs

**Input directory:** `data/raw/conspiracy/messages/`  
**Input format:** gzip-compressed JSON Lines (`*.jsonl.gz`), as produced by the project's collection scripts.

The benchmark script:
- Excludes service messages, known bot messages, and records without non-empty text.
- Uses a deterministic, seed-based reservoir sample across eligible records in the conspiracy directory (**not yet a per-pair/per-chat sample**).
- Uses CPU inference with **batch size 8**, **maximum 256 tokens per message**, **8 CPU threads**, and **seed 42** (script defaults).
- Outputs message references, metadata flags, a toxicity score, and a provisional binary classification.
- Does not include raw message text in the initial scoring CSV.

Local outputs, deliberately placed **outside the repository**:
- `../telegram-local-results/test_100.csv`: scores and message references.
- `../telegram-local-results/test_100.meta.json`: run settings and timing.
- `../telegram-local-results/review_100.csv`: subsequent **local-only** review table containing original messages, scores, and fields for human labels and notes.

A separate AI-assisted Italian translation/interpretation workbook was created for exploratory qualitative inspection. These interpretations are **not independent human ground truth** and must not be treated as formal validation.

## 5. First benchmark results

| Metric | Observed value |
| --- | ---: |
| Scored messages | 100 |
| Measured inference time | 37.2 seconds |
| Throughput | 2.69 messages/second |
| Predicted toxic at threshold 0.50 | 19/100 |
| Predicted non-toxic at threshold 0.50 | 81/100 |

The score counts were checked against the locally generated 100-message review file. The sample and threshold do **not** support a population-level estimate of toxicity in conspiracy communities.

At the observed throughput, classifying **1.5 million** messages would take approximately **155 hours of inference** (about 6.5 days), excluding setup, preprocessing, and further analysis. This is **only an extrapolation from a small 100-message CPU run**, not a reliable estimate of full-dataset runtime.

## 6. Limitations and methodological requirements

**Not paper-ready.** Before reporting scientific results, the pipeline needs to:

1. Apply channel–group pairing, align observation windows, and remove channel posts automatically copied into linked discussion groups.
2. Distinguish **channel posts, group admins, and regular users** using agreed role-labeling rules.
3. Follow the plan's **up-to-5,000 human text messages per chat** sampling scheme (or document and approve a change). This pilot sampled across all eligible messages.
4. Detect message languages, check model coverage, and report excluded or unsupported languages.
5. Use **independent manual annotation** by at least two annotators; calculate agreement, precision, recall, and F1; inspect false positives and false negatives.
6. Validate or calibrate the threshold instead of assuming 0.50 is optimal.
7. Distinguish lexical toxicity from sentiment, incitement, fraud promotion, and other content dimensions.
8. Assess the effects of truncation at 256 tokens and explore performance improvements using alternative batch sizes or inference runtimes.

Preliminary AI-assisted inspection revealed potentially ambiguous classifications, but does not establish a formal error rate.

## 7. Privacy and repository handling

- **Do not commit** raw-message review CSVs, translation workbooks, screenshots with identifying text, Telegram credentials, `.env` or `.session` files, or downloaded model weights/caches.
- Keep any review table containing actual message text local and access-controlled, subject to the team's data-handling arrangements.
- At the time of this pilot, GitHub reported **public** repository visibility, despite the project guidelines describing a **private** repository. The team should reconcile visibility and review previously committed sensitive data and Git history.
- This report contains **technical details and aggregates only**: no user messages or identifiers.

## 8. Proposed next steps (not yet performed)

1. Run a longer 1,000–10,000-message benchmark; compare batch sizes and CPU/ONNX inference options.
2. Agree on final model, sampling, validation, and methodology with the team; record decisions in `memory/decisions.md`.
3. Create a privacy-conscious, multilingual human annotation sample and codebook.
4. Integrate validated scoring into the channel–group/admin–user comparisons.
5. Report effect sizes, uncertainty, preprocessing choices, and model limitations in the paper.

**Summary:** TextDetox v2 ran successfully on 100 conspiracy-related Telegram messages on a local Windows CPU. This establishes technical feasibility, **not** a validated estimate of toxicity or aggression in the full dataset.

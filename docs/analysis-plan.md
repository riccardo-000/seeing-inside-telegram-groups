# Analysis plan — DRAFT v1

**Status (2026-11-10):** points 1–9 agreed by Riccardo (with Claude Code), point 10 still to
decide. **To be reviewed by Marco and Simone**; anything they want to change is discussed
together, then logged in `memory/decisions.md`. No analysis code has been written yet.

## 0. Starting point

- **Research questions** (README): (1) tone and content, channel vs linked group;
  (2) admins vs regular users; (3) unsolicited DMs; (4) crypto vs conspiracy.
- **Data** (collection closed 2026-11-10): **crypto 98 pairs** (~2.3 M messages),
  **conspiracy 97 pairs** (~1.5 M), **195 distinct pairs**. Window from 2026-07-30; five very
  large groups end earlier (decision 2026-11-10); Rekt Plebs group only 2026-10-27 → 11-04.
  DMs: crypto 22, conspiracy 15.
- **Overall design:** a **common core** measured the same way on both arms (points 1–4, 6–8),
  plus **one deep dive per arm** (point 5): crypto → invitations to register on platforms;
  conspiracy → tone.
- **Paper:** LNCS, max 16 pages excl. references, due **3 January 2027**.

## 1. Unit of analysis and cleaning

- **Unit = the pair.** Every measure is computed per chat, then as **group − channel** per
  pair: each channel is the control for its own group.
- **Windows differ per chat:** use rates (per day, per message), never raw counts. Truncated
  chats stay in; sensitivity check without them (point 8).
- **Excluded from text measures:** service messages (join/leave/pin), messages without text.
- **Channel posts copied into the group** (Telegram copies every channel post into its linked
  discussion group: `sender_kind = channel` and forwarded from the channel itself) are removed
  from the group side, otherwise the group "contains" the channel.
- **Bot messages are kept and reported as a result** (decision 2026-11-10): share of bot
  messages per chat; excluded only from tone and content measures (human authors).
- **Pairs in both arms** (COTI, Rekt Plebs, QSI) count only in crypto (decision 2026-11-10).

## 2. Structural measures (pandas only)

| # | Measure | Where | Answers |
|---|---|---|---|
| 1 | Messages per day | channel, group | How much more active the group is |
| 2 | Share of messages with links / forwarded / with media / without text | channel, group | What the content of each layer is made of |
| 3 | Distinct human authors; share of messages by the top 10% authors | group | Many voices or few |
| 4 | Share of messages by admins | group | How "controlled" the group still is |
| 5 | Share of bot messages | group | Bot result (point 1) |
| 6 | Share of messages that are comments on a channel post vs free chat | group | How much the group depends on the channel |
| 7 | Share of channel posts with at least one comment | pair | How much discussion the channel generates |
| 8 | Share of messages replying to another user | group | Whether users talk to each other |
| 9 | Share of group links to domains / `t.me` chats never seen in the channel | pair | What enters through the group that the channel does not show |

Left out: time synchrony between posts and group activity; Gini-style concentration indices.
Output: one table per chat and one per pair (also Table 1 of the paper, dataset overview).
Limitation: anonymous admins (writing as the group) are counted as admins but not as persons.

## 3. Tone (automatic, pre-trained models run locally)

| Dimension | What is counted |
|---|---|
| Sentiment | Share of negative / neutral / positive messages |
| Toxicity | Share of messages with insults, hate, threats |
| Style | Length, share of questions, emoji, capitals, exclamation marks (no model) |

- **Models:** pre-trained multilingual models, **run locally** (no message leaves the
  computer). Candidates and install in point 9. No LLM API.
- **Sample:** up to 5,000 human messages with text per chat, random with a fixed seed; all
  messages if fewer (channels enter whole).
- **Per pair:** share in the group − share in the channel.
- **Genre effect:** channel posts are long and curated, group messages short; part of any tone
  difference is form. Compare shares, not means, and report style next to tone.
- **Languages:** every message gets a language label; tone is reported only for the languages
  each model covers, and the paper states the share of messages left out per arm. Covered
  languages are fixed after seeing the real language distribution.
- **Validation by hand:** ~200 messages per dimension, two annotators, blind to the model
  output; report agreement between annotators and with the model.

## 4. Content: what the group talks about that the channel does not

Each message → multilingual embedding (local model), compared with the channel posts.

| # | Measure | How |
|---|---|---|
| 1 | Off-topic comments | Comments know their post (`thread_top`): similarity comment ↔ that post |
| 2 | **Group-only content** (main number) | For each free group message, the most similar channel post; below a threshold → "group-only" |
| 3 | What group-only content is made of | Automatic clustering of group-only messages, then **we read ~20 examples per cluster and name it** |

- **Threshold:** fixed by hand on ~100 message–post pairs ("same topic? yes/no"); results also
  reported with two nearby thresholds.
- **Very short messages** ("gm", one emoji): no meaningful embedding → counted apart as
  "chit-chat" (below a minimum length).
- Same sample as point 3. Each group message is compared with all channel posts in the pair's
  window.
- Tools: `sentence-transformers` model + `scikit-learn` clustering (no BERTopic).
- Group-only messages are also where point 5 looks first.

## 5. Per-arm deep dives (replaces the full scam taxonomy)

The full scam taxonomy with a 1,200-message labelled sample (`docs/scam-definitions.md`, never
committed) was dropped as too much manual work. Instead:

### 5a. Crypto — invitations to register on a platform

- **Automatic detection:** messages with registration / referral links (`ref=`,
  `invite_code=`, `/register`, `/signup`, Telegram bots with `?start=`) or sign-up / deposit /
  claim wording.
- **Labelled by hand per domain, not per message:** the ~100 most frequent domains are
  classified as *official site of the project*, *known exchange*, or *unknown / suspicious
  platform*. One label covers thousands of messages.
- **Suspicious invite** = invite to an unknown platform, or any invite with a fraud hallmark
  (fixed or guaranteed returns, deposit → daily payout). Exact rule to be finalized.
- **Validation:** ~150 messages checked by hand → error rate of the detector.
- Expected result: rate of suspicious invites channel vs group, and who posts them (point 6).
- **Passive only:** we measure the invitations, we never register or click.

### 5b. Conspiracy — tone

- Toxicity and sentiment from point 3, in depth: channel vs group, three voices (point 6).
- ~200 messages validated by hand (point 3).
- **Open:** whether to add an "incitement" category (calls to act against someone), with a
  narrow definition. Delicate to label; to decide separately.

## 6. Admins vs users: three voices

| Voice | Who | Where |
|---|---|---|
| Channel | Official voice (admins, posting as the channel) | channel |
| Admins in the group | Creator and admins writing as persons | group |
| Users | All other humans | group |

- **Roles:** creator/admin (in `.admins.json`); anonymous admin (message sent as the group —
  how it appears in the dumps to verify); linked channel (copied posts, already removed);
  other channel (a user writing "as a channel", often promotion, counted apart); **bot, also
  when admin** (moderation bots stay bots); user.
- **Measures (all reused):** share of messages per voice (2), toxicity and sentiment per voice
  (3), similarity to the channel per voice (4), invitations per voice and domain type (5a).
- **Threshold:** a group enters the admin vs user comparison only if admins wrote ≥ 30 messages
  in the window; report how many groups pass; check with 10 and 50.
- **Paired comparison:** per group, rate among admins − rate among users.
- **Limitations:** admin list is a snapshot at dump time; anonymous admins are not
  distinguishable; messages deleted by admins (often scams) are missing → shares among users
  are lower bounds.
- No extra manual work.

## 7. DMs (descriptive, case study)

- **Unit = sender** (all DMs of one account read together).

| Measure | How | Automatic? |
|---|---|---|
| Senders, bots vs humans | `sender_is_bot` | yes |
| Type of DM | `bot_service`, `opener`, `impersonation`, `investment`, `unclear`… | by hand (~25 senders, **all three label all**) |
| Probable source group | Minutes between our join and the first DM | yes (join logs) |
| Who the sender is | Sender id vs admin lists and authors in all dumps: admin somewhere, active author, or lurker | yes |
| Telegram flags | `scam`, `fake`, `premium` | yes |
| Exposure rate | Human DMs per joined group and per day of membership | yes |

- **DM checks continue every 2–3 days until 2026-12-01**, then closed (passive: reads the
  inbox, never replies, does not mark as read). Window stated in the paper.
- **Limitations:** one account per arm; different windows (crypto from 2026-10-19, conspiracy
  from 2026-10-28); DMs deleted before a check are lost; an `opener` stays ambiguous because we
  never reply → called "unsolicited contact", not scam.

## 8. Centerpiece figure, tables, statistics

- **Centerpiece figure:** grid of panels, rows = main measures, columns = crypto / conspiracy;
  in each panel one thin line per pair joining **channel → admins in group → users**, thick line
  = median. Main measures: toxicity share (3), group-only content share (4), suspicious invite
  share (5a, crypto), bot share (1–2).
- **Table 1:** dataset per arm (pairs, messages, authors, windows, truncated chats).
- **Table 2:** measures × voices × arm, median with confidence interval.

| Question | Test | Unit |
|---|---|---|
| Group different from channel? | Paired Wilcoxon | pair |
| Admins different from users? | Paired Wilcoxon | group (≥ 30 admin messages) |
| Crypto different from conspiracy? | Mann–Whitney on per-pair differences | pair |

- **Every pair weighs the same** (per-pair rates, then compare pairs).
- **Effect size first:** median difference with bootstrap CI (resampling pairs); p-values
  reported but not the result.
- **Holm correction** for multiple comparisons.
- **List of tests frozen before looking at results**, logged in `memory/decisions.md`.
- **Robustness:** rerun without the 5 truncated groups and Rekt Plebs; admin threshold 10 and 50;
  the two nearby group-only thresholds.

## 9. Dependencies and models

Today the venv has only pandas and numpy. Nothing is installed until coding starts.

| Library | Use | Point |
|---|---|---|
| `scipy` | statistical tests | 8 |
| `matplotlib` | figures | 8 |
| `scikit-learn` | clustering | 4 |
| `openpyxl` | labelling files with dropdown | 3, 4, 5, 7 |
| `lingua-language-detector` | language of each message (good on short text, no compiling) | 3 |
| `torch`, `transformers`, `sentence-transformers` | run pre-trained models locally | 3, 4 |

Candidate models (Hugging Face, from memory: **to verify online before download**, names and
sizes reported before downloading):

| Use | Candidate | Languages (to verify) |
|---|---|---|
| Sentiment | `cardiffnlp/twitter-xlm-roberta-base-sentiment` | 8 incl. EN, IT, DE, ES; no RU, HE, ZH |
| Toxicity | `textdetox/xlmr-large-toxicity-classifier` | EN, RU, UK, DE, ES, ZH, AR and others |
| Toxicity (alt.) | `unitary/multilingual-toxic-xlm-roberta` | EN, RU, IT, FR, ES, PT, TR |
| Embeddings | `paraphrase-multilingual-MiniLM-L12-v2` | 50+ |

- Size: ~1–2 GB of libraries in the venv, ~2–3 GB of models in `~/.cache/huggingface` (outside
  the repo).
- **Versions pinned** in `requirements.txt` after install, same environment on all machines.
- **Heavy computations run once** on one machine; only compressed results (scores per message,
  tables per chat) are committed, < 100 MB per file. **Embeddings are not committed** (> 1 GB);
  only derived measures are.
- Only models are downloaded; no message leaves the computer.

## 10. Who does what, and order in the week

**To decide** (team).

## 11. Manual work (summary)

| Task | Point | Size |
|---|---|---|
| Classify domains | 5a (crypto) | ~100 domains |
| Validate the invite detector | 5a (crypto) | ~150 messages |
| Validate tone (sentiment, toxicity) | 3, 5b | ~200 messages |
| Group-only threshold | 4 | ~100 message–post pairs |
| Name the content clusters | 4 | ~20 examples per cluster, together |
| Label DM senders | 7 | ~25 senders, all three |

Each task: two annotators on (part of) it, blind (text only, no chat / author / role), no
discussion while labelling, for an agreement figure. Files: one `.xlsx` per annotator with a
dropdown and the definitions on the first sheet; local spreadsheet app, **not Google Sheets**
(messages would go to Google's servers). Rough estimate: **2–3 hours per person**.

## 12. Open questions

- Review of this plan by Marco and Simone.
- Point 10: who does what, order and timeline.
- 5a: exact rule for "suspicious invite"; referral links to known exchanges and exchange
  "listing agent" messages: suspicious or not.
- 5b: "incitement" category yes/no and its definition.
- Conspiracy donations / product sales: count apart (`monetization` flag) or ignore.
- Languages each of us can label by hand.
- DeepStateUA pair (borderline; its channel was joined by mistake).
- Mail to the supervisor: hand-pressed captchas, join requests sent, the per-arm deep dives,
  DM checks until 2026-12-01.
- Privacy / pseudonymization (deferred): to apply before any release or quote; what we can
  release (supervisor: "release data and notebooks").
- Paper structure: `docs/paper-outline.md` vs the sections already on Overleaf — which one wins.

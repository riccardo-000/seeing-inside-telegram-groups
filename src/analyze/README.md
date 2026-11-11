# src/analyze — analysis code

One folder for all the analysis of `docs/analysis-plan.md`. Everything reads the dumps already
in `data/raw/` (no Telegram) through **`load.py`**, so all points work on the same data.

| File | Plan point | Status |
|---|---|---|
| `load.py` | 1 — data preparation (this README) | done |
| `structure.py` | 2 — structural measures (section below) | done |
| `tone.py` | 3 — tone | stub |
| `content.py` | 4 — group-only content | to write |
| `invites.py` | 5a — invitations to register (section below) | detector done; hand labels to do |
| `authors.py` | 6 — three voices (roles already come from `load.py`) | stub |
| `dms.py` | 7 — DMs | to write |
| `stats.py` | 8 — tests and figures | to write |

Outputs go to `data/processed/` (< 100 MB per file). Prepared messages are **not** saved again
in the repo (they would duplicate the dumps): `load.py` rebuilds them in about a minute.

## How to use it

Run from the repo root with the project venv (only pandas needed):

```python
import sys; sys.path.insert(0, ".")
from src.analyze.load import iter_pairs, load_messages, pairs, chat_table

for pair, df in iter_pairs("crypto"):          # one pair at a time (low memory)
    group = df[(df.side == "group") & df.in_window]
    ...

df = load_messages("conspiracy", text=False)  # all messages, without text (~1.5 M rows)
```

Per-chat table (Table 1 of the paper, basis of point 2):

```bash
python scripts/chat_table.py          # → data/processed/chats.csv (~45 s)
```

## Pairs

`pairs()` reads the two final lists: **crypto 98 pairs with data** (100 listed, 2 groups gone),
**conspiracy 97** (rows with `final` ≠ `valida` are the 3 pairs moved to crypto).
`pair_id` = `<topic>:<channel username>`, e.g. `crypto:officialkybernetwork`.
File quirks handled: `@demons` → `gambledemons`, `@zeczcash` → `3984096229`; a file missing in
the arm's folder is read from the other one (`@rektplebssubmission`, only in conspiracy).

## Columns (one row per message)

| Column | Meaning |
|---|---|
| `topic` | `crypto` / `conspiracy` |
| `pair_id` | pair the message belongs to |
| `side` | `channel` / `group` |
| `chat` | username of the chat (lower case, as in the pair list) |
| `chat_id`, `msg_id` | Telegram ids; (`chat_id`, `msg_id`) is unique |
| `date` | UTC timestamp |
| `sender_kind`, `sender` | as on disk: `user` / `channel` / `none`, and the raw id (not pseudonymized yet) |
| `role` | see below |
| `voice` | `channel` / `admin` / `user`, or empty (bots, copies, other channels, service) — the three voices of point 6 |
| `is_bot` | sender is a bot (Telegram flag) |
| `is_service` | join / leave / pin and similar service messages |
| `has_text`, `n_chars`, `text` | text (empty string if none); `text` is dropped with `text=False` |
| `reply_to`, `thread_top` | id of the message replied to / top of the thread |
| `is_comment` | group message replying to (or in the thread of) a copy of a channel post |
| `is_forward`, `fwd_kind`, `fwd_from` | forwarded message and its source |
| `media`, `urls`, `tme` | media type, URLs, `t.me` paths found in the text |
| `views`, `forwards`, `n_replies` | counters as on disk |
| `post_author` | admin signature / custom title, if any |
| `in_window` | inside the chat's observation window (see below) — **filter on this** |

### Roles

Channel side: every post is `channel` (also when it carries an author signature), service
messages are `service`.

Group side, first rule that matches:

| Role | Rule |
|---|---|
| `service` | service message |
| `channel_copy` | sent by the paired channel, not a reply: Telegram's copy of a channel post in its discussion group. **Excluded** from group measures |
| `channel_reply` | sent as the paired channel, as a reply: an admin answering as the channel → admin voice |
| `other_channel` | sent as another channel (promotion, or copies of another channel's posts) |
| `anonymous_admin` | no sender on disk (`sender_kind = none`): anonymous admin, often with a title in `post_author` |
| `bot` | bot account, **also when it is an admin** (decision on bots, 2026-11-10) |
| `creator` / `admin` | in the group's `.admins.json` |
| `user` | everyone else |

`voice`: `channel` → channel; `creator`, `admin`, `anonymous_admin`, `channel_reply` → admin;
`user` → user. Five conspiracy groups have **no visible admin list**
(`irishpatriotschat`, `crismartinj`, `ericsflatchat`, `chemtrailspartages`,
`covidrechercheverite_chat`): their admins are counted as users, so leave them out of the
admins-vs-users comparison.

### Observation windows

Default window: **2026-07-30 00:00 UTC → 2026-11-04 00:00 UTC** for every chat (common end).
It is shortened when the data show the dump did not cover it: the silence before the first
(after the last) message is longer than both 50 × the chat's average gap between messages and
2 days (only for chats with ≥ 200 messages); banned groups end at their last message.
21 chats are shortened (`window_note` in `chats.csv`). Rates per day must use `window_days`.

## chats.csv (one row per chat)

`topic, pair_id, side, chat, file, n_on_disk, n_in_window, first_message, last_message,
window_start, window_end, window_days, window_note, n_with_text, n_human, authors_human`,
one `n_<role>` column per role, and for groups `admins_listed, is_discussion_group,
n_comment`. All counts are inside the window. `is_discussion_group` = the group contains
copies of the paired channel's posts (it is its linked discussion group): 87 of 98 crypto
groups, 92 of 97 conspiracy groups; the others were paired by name or description.

## Structural measures (point 2, `structure.py`)

```bash
python scripts/structure_measures.py   # → data/processed/structure_chats.csv, structure_pairs.csv (~50 s)
```

All messages in each chat's window (no sample). **Human** messages = rows with a `voice`
(channel posts; admins and users in the group).

| Column | Definition |
|---|---|
| `msgs_per_day` | human messages / `window_days` (both sides); `ratio_msgs_per_day` = group / channel |
| `share_link`, `share_forward`, `share_media`, `share_no_text` | share of human messages with a URL / forwarded / with media / without text (both sides); `diff_*` = group − channel |
| `authors_human` | distinct human senders in the group (anonymous admins have no id: not counted) |
| `top10_authors_share` | share of human messages written by the most active 10% of authors (rounded up) |
| `admin_share` | share of human group messages with voice admin |
| `bot_share`, `other_channel_share` | share of all group messages (except service and channel copies) sent by bots / as another channel |
| `comment_share` | share of human group messages that are comments on a channel post (discussion groups only, else empty) |
| `posts_commented_share` | share of channel copies in the group with ≥ 1 human comment (discussion groups only) |
| `reply_to_other_share` | share of human group messages replying to a message of another human (admin or user) |
| `n_link_msgs` | human group messages with at least one link target |
| `group_only_link_msg_share` | share of those pointing to ≥ 1 target never linked by the channel |
| `group_only_target_share` | share of distinct group link targets never linked by the channel |

Link targets: web links → registered domain (last two labels, three for `co.uk`-like
suffixes; `www.` dropped; truncated fragments without a domain discarded, IP addresses
discarded); Telegram links → `t.me/<chat>` (first path segment, from the `tme` field). The
pair's own channel and group count as known to the channel. 16 groups are not discussion
groups (no channel copies): their comment measures are empty.

Truncated domains (the dump sometimes cuts the first letters of a link: `igilantfox.com`
for `vigilantfox.com`) are mapped back to the full domain seen in the same pair
(`fragment_map`): first label 1–3 characters shorter, at least 4 characters long.

## Invitations to register (point 5a, `invites.py`)

```bash
python scripts/invites.py   # ~95 s, both arms
```

**Invitation** = message (any poster except service and channel copies) with
(a) a registration / referral link — referral parameter (`ref=`, `invite_code=`, `aff=`, …) or
sign-up path (`/register`, `/signup`, `/invite/`, `/ref/`, `/join/`, …) on a platform domain, or a
Telegram bot link with `?start=`; or (b) registration wording ("sign up", "referral",
"deposit", RU/ES/IT/ID/AR equivalents) **and** a link to a platform domain. Social, video,
news, explorer and reference sites (`NOT_PLATFORM`) are never platforms.

**Domain class** (automatic, with its source): `telegram_bot`; `official` (also linked by the
pair's channel); `exchange` and `trading_tool` (hand-written lists in `invites.py`, **to be
reviewed by the team**); `shortener` (destination unknown); `unknown` (labelled by hand).
**Fraud hallmark** = wording with fixed / guaranteed returns, "deposit X … daily",
"minimum deposit", "passive income", …

Outputs: `data/processed/invites_chats.csv` (per chat: messages, invitations, hallmarks, who
posted them, to which class), `data/processed/invites_pairs.csv` (per pair, channel vs group),
`data/interim/invites/domains.csv` (every target domain with counts and class).

### Hand work (two annotators, each alone, without talking about it)

1. **`data/interim/invites/domains_to_label.csv`** — the 100 most frequent crypto `unknown`
   domains (85% of unknown invitations). Fill `label_a` (first annotator) or `label_b` (second)
   with `suspicious`, `legit` or `unclear`. **Do not open the sites** (project rule: no
   clicking links; scam sites can be harmful): judge from the name and a web search of the
   domain (news, scam-report sites). Then together fill `label_final` where you disagree.
2. **`data/interim/invites/validation_a.csv`** (first annotator) and **`validation_b.csv`**
   (second): the same 150 crypto messages, text only. Columns `is_invitation` (`yes`/`no`:
   does it invite to register / sign up / deposit on a platform?) and `suspicious`
   (`yes`/`no`/`unclear`). Do not open `validation_key.csv` (it says which messages the
   detector flagged) until both files are done.

Re-running `scripts/invites.py` never overwrites these files (only with `--force`).

### After the hand work: final results (`invite_labels.py`)

```bash
python scripts/invites_results.py   # ~2 min; also runs on partial labels
```

- **Domain label** = `label_final` if filled, else the common label of `label_a` and `label_b`;
  otherwise unresolved. Agreement (Cohen's kappa) is reported.
- **Suspicious invitation** = fraud hallmark, or a target domain labelled `suspicious`.
  **Unresolved** = otherwise pointing to an `unknown` domain without a final label (or
  `unclear`). Results are a range: `low` (unresolved = not suspicious) and `high`
  (unresolved = suspicious). Conspiracy has no hand labels, so its `high` counts every unknown
  domain.
- **Validation**: the reference answer is the common answer of A and B; where they disagree the
  script writes `data/interim/invites/validation_final.csv` — a third person fills
  `is_invitation_final` / `suspicious_final` (kept across runs), then rerun. Detector precision
  and recall are weighted by the size of each part of the sampling pool (detected / link not
  detected / no link).

Outputs: `data/processed/invites_suspicious_chats.csv`, `invites_suspicious_pairs.csv`,
`invites_quality.json` (agreement, precision, recall).

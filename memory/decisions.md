# Decision log

Append-only. Format in `memory/README.md`. Newest at the bottom.

## 2026-09-22 — Project scope
- **Author:** Riccardo (+ Claude Code)
- **Decision:** Seed ~100 crypto + ~100 conspiracy/malicious channels from TGDataset; join
  channels and their linked groups (public only); passive observation; download chats;
  analyze tone and authors (admin vs user); count scam DMs and whether senders are admins;
  compare channel vs group with focus on scam/carding communities.
- **Why:** Agreed with the supervisor.
- **Impact:** README, `src/collect/*`, `src/analyze/*`, paper methodology.

## 2026-09-22 — Stack and repo setup
- **Author:** Riccardo (+ Claude Code)
- **Decision:** Python ≥ 3.11 + Telethon, pandas, python-dotenv, tqdm (pinned in
  `requirements.txt`). Private GitHub repo. Secrets only in local `.env`; `*.session`,
  `data/raw/`, `data/interim/` gitignored.
- **Why:** Telethon is the standard MTProto client for research collection; pandas 3.x
  requires Python 3.11. Session files are account credentials.
- **Impact:** `.gitignore`, `requirements.txt`, `src/utils/config.py`.

## 2026-09-22 — Pseudonymization approach (proposed)
- **Author:** Riccardo (+ Claude Code)
- **Decision:** Replace user ids with HMAC-SHA256(id, `PSEUDONYM_SALT`) before analysis;
  drop usernames/display names/phones. Salt shared out-of-band, never committed.
- **Why:** Keeps ids linkable across chats (needed for admin-vs-DM-sender analysis)
  without storing direct identifiers; a plain hash of a Telegram id is trivially reversible.
- **Impact:** `src/analyze/authors.py::pseudonymize`, Ethics section. To confirm with team.

## 2026-09-22 — Dedicated Telegram research account
- **Author:** Riccardo (+ Claude Code)
- **Decision:** Use a dedicated Telegram account (not a personal number) for joining and DM logging.
- **Why:** Isolates the team's personal accounts; ban/restriction risk is accepted and
  noted as a limitation.
- **Impact:** `.env` (local), paper Limitations.

## 2026-09-22 — No formal ethics/DPO review requested
- **Author:** Riccardo (+ Claude Code)
- **Decision:** No separate ethics board / DPO consultation before collection; proceed under
  the scope agreed with the supervisor and the safeguards in README "Ethics & scope".
- **Why:** Team decision.
- **Impact:** Paper Ethics section must justify the safeguards explicitly.

## 2026-09-22 — Seed and group sources beyond TGDataset
- **Author:** Riccardo (+ Claude Code)
- **Decision:** TGDataset is the starting point (topic labels), but groups and channels are
  not limited to it: (1) groups advertised via t.me / public invite links in channels'
  *recent* posts, (2) TeraGram (ICWSM '26, 2015–2025, includes discussion groups — check
  access), (3) Telegram public search by keyword. Each seed records its `source`.
- **Why:** TGDataset stops in July 2022 and many channels will be dead; supervisor's brief
  also points to invite links in channel posts.
- **Impact:** `src/collect/channels.py`, README scope, Methodology 4.1. **Related work:**
  TeraGram already covers discussion groups → our novelty must be sharpened (admin vs user
  scam roles, received DMs, live observation of malicious groups). To mention to supervisor.

## 2026-09-22 — Pseudonymization at ingestion (supersedes "Pseudonymization approach (proposed)")
- **Author:** Riccardo (+ Claude Code)
- **Decision:** Pseudonymize user ids (HMAC with shared salt) and redact personal data from
  text **before writing to disk**, not at analysis time. Details and open questions in
  `memory/data-protection.md`.
- **Why:** Supervisor's brief: "Store no personal data" / "redact at ingestion".
- **Impact:** new `src/utils/privacy.py`; `collect/messages.py`, `collect/dms.py`,
  `analyze/authors.py` now work on pseudonyms only.

## 2026-09-22 — Simple git workflow
- **Author:** Riccardo (+ Claude Code)
- **Decision:** Everyone works directly on `main` (pull → commit → push). No feature
  branches or PR reviews required.
- **Why:** Repo is mainly shared memory, docs and some code; PR process is overkill for 3 people.
- **Impact:** `CONTRIBUTING.md`, `CLAUDE.md` rule 7.

## 2026-09-22 — Raw data shared via repo; privacy deferred
- **Author:** Riccardo (+ Claude Code)
- **Decision:** `data/raw/` and `data/interim/` are committed to the private repo so all
  three members can see what is found. Pseudonymization/redaction is deferred to the
  paper-writing phase (supersedes "Pseudonymization at ingestion"). `.session`/`.env` stay
  out of git.
- **Why:** Team needs a simple way to share findings; privacy to be handled before publishing.
- **Impact:** `.gitignore`, `CLAUDE.md` rules 2/5/8, README Ethics, `memory/data-protection.md`.
  Notes: files must be < 100 MB (GitHub limit); anything committed stays in git history,
  so removing it later requires rewriting history. Supervisor's brief says "store no
  personal data" — to reconcile in the Ethics section / with the supervisor.

## 2026-09-22 — One shared Telegram research account on three machines
- **Author:** Riccardo (+ Claude Code)
- **Decision:** A single research account; all three members log in from their own machine
  (own `.env` with the same values, own `.session`) and run scripts. Coordination through
  `memory/collection-log.md`: joins one person at a time, disjoint chat assignment for
  dumps, a single DM logger instance, shared FloodWait log.
- **Why:** Everyone will run collection scripts; only one number available.
- **Impact:** `CLAUDE.md` rule 8, `CONTRIBUTING.md`, collectors must be resumable and
  deduplicate by (chat_id, message_id). Rate limits and the 500-chat cap are shared.

## 2026-09-29 — Config loading and per-machine login
- **Author:** Riccardo (+ Claude Code)
- **Decision:** `src/utils/config.py` reads `.env` (api id/hash + phone required); each member
  runs `scripts/login.py` once on their own machine to create a local `research.session`.
  Session files are never copied between machines.
- **Why:** `.session` is a full account credential; one login per machine keeps it local.
  Logins on different machines should be spaced out (new-device logins on a fresh account
  can trigger Telegram's anti-abuse checks).
- **Impact:** `src/utils/config.py`, `scripts/login.py`, `.venv` (Python 3.12, local).

## 2026-09-29 — No task split: equal contribution
- **Author:** Riccardo (+ Claude Code)
- **Decision:** No fixed roles; all three members work on every part (seeds, collection,
  analysis, writing). The paper states equal contribution.
- **Why:** Team decision.
- **Impact:** `CONTRIBUTING.md` "Who does what"; paper contribution statement. Course requires
  the paper to "state clearly who did what" → keep the git log / decisions.md author field
  accurate so concrete contributions can be listed if asked. Chat assignment for message
  dumps (collection-log.md) still applies: it is coordination, not a role split.

## 2026-09-29 — Username-resolve budget for the shared account
- **Author:** Riccardo (+ Claude Code)
- **Decision:** At most ~100 username resolves per day for the whole account (all people, all
  scripts), logged in `collection-log.md`. Scripts reuse the local session cache so already
  known chats cost nothing; 1 request every 6 s; stop at the first long FloodWait.
- **Why:** On 2026-09-29 ~250–300 resolves in one day on a new account triggered a 19 h
  FloodWait (68,674 s). Other read-only calls (history, channel info) were not the problem.
- **Impact:** `scripts/audit_channels.py --max-resolves`, collection-log, paper Limitations
  (collection speed).

## 2026-09-29 — What counts as "channel with a group"; single master file
- **Author:** Riccardo (+ Claude Code)
- **Decision:** A channel "has a group" if it points (description, posts, hidden links,
  buttons, @mentions) to a public supergroup that is active, or if its linked discussion group
  has a public username and is used as a chat. Thresholds (last 7 days): standalone group
  ≥ 20 messages from ≥ 5 users; linked "community" ≥ 10 free messages (not replies to posts)
  from ≥ 5 users. Private invite links are recorded but never opened. All channels/groups go
  into one file, `data/interim/master.csv`, rebuilt by `scripts/build_master.py` (manual columns
  are preserved); manual checks are done there.
- **Why:** Keyword search showed ~2% of active crypto channels link a standalone public group,
  but airdrop aggregators (@AirdropDetective, @Airdrop) link many project channels whose
  linked chat is an active community → project channel + community is the pair we study.
  Manual review of 42 channels (team, 2026-09-29) agreed with the script on aggregators and
  on "signals" channels having no public group.
- **Impact:** seed selection (Methodology), `audit_channels.py`, `build_master.py`,
  `master.csv`. Thresholds to be defended in the paper.

## 2026-10-07 — Second Telegram account for the conspiracy arm; data split by topic
- **Author:** Riccardo (+ Claude Code)
- **Decision:** A second dedicated research account collects the conspiracy arm; the first
  account keeps the crypto arm. One `.env` holds both (`TELEGRAM_*_CRYPTO`,
  `TELEGRAM_*_CONSPIRACY`; unsuffixed variables still read as crypto). Every script takes a
  required `--topic crypto|conspiracy` that selects both the account and the data folders
  (`src/utils/config.py: paths()`): `data/interim/<topic>/{seeds,prefilter,pairs,audit,peek}/`,
  `data/interim/<topic>/master.csv`, `data/raw/<topic>/messages/`, `data/raw/dms/<topic>/`.
  The daily resolve budget (100/day) is now per account:
  `data/interim/accounts/resolve_ledger_<account>.csv` (old ledger = crypto). Existing files
  were moved with `git mv` (all audit/pairs/master rows were crypto). For conspiracy,
  `audit_channels.py` queues only seed channels the web prefilter saw alive and posting.
  `dm_logger.py` runs once per account and matches senders against the dumps of both topics.
- **Why:** The resolve limit and FloodWaits are per account, so one shared account made the
  two arms compete for 100 resolves/day; two accounts double throughput and let the arms run
  in parallel without mixing files. Explicit `--topic` avoids writing one arm's data into the
  other's folders.
- **Impact:** all `scripts/`, `src/utils/config.py`, `src/utils/budget.py`, `.env.example`,
  CLAUDE.md rule 8, collection-log (account per entry). Paper Methodology: two research
  accounts; DM counts reported per account (a newer account may receive fewer/more DMs);
  supersedes the single-account part of "One shared Telegram research account on three
  machines" (2026-09-22).

## 2026-10-07 — Order of the conspiracy audit queue
- **Author:** Riccardo (+ Claude Code)
- **Decision:** `audit_channels.py --topic conspiracy` audits only seeds the web prefilter saw
  alive and posting, ordered by: topic priority from `seeds_conspiracy.py` (Extremists,
  Covid, US/World news, Carding, Crypto, Religion, unlabelled); then channels whose
  description has group-like t.me links (chat/group/community...); then any t.me link; then
  posts in the last 30 days. First runs on the new account are capped low (≤30 resolves/run,
  ≤4 new resolves per channel, 8 s/request).
- **Why:** Resolves are the scarce resource (100/day/account). Channels that advertise a
  group in their description are the most likely to give a channel–group pair; a new account
  is more likely to be limited, so it starts slow.
- **Impact:** `scripts/audit_channels.py`, seed selection for the conspiracy arm (Methodology).

## 2026-10-08 — Conspiracy queue: channels with a visible preview first
- **Author:** Riccardo (+ Claude Code)
- **Decision:** In the conspiracy audit queue, channels whose t.me web preview shows recent
  posts come before every channel without a preview (`channel_no_preview`), across topics;
  the order from "Order of the conspiracy audit queue" (2026-10-07) applies inside each block.
  Second day of the conspiracy account: full 100-resolve daily budget.
- **Why:** On 2026-10-07, 15 of the 19 no-preview channels audited were inactive and used half
  of the resolves; the prefilter cannot tell their activity, so they are the least promising.
- **Impact:** `scripts/audit_channels.py` (conspiracy seed order), Methodology (seed selection).

## 2026-10-17 — Final list of 100 crypto channel–group pairs
- **Author:** Riccardo + Marco (+ Claude Code)
- **Decision:** The crypto arm studies the 100 pairs in `data/interim/crypto/pairs/final_pairs.csv`
  (100 channels, 100 distinct public groups, one group per channel). Built from Marco's manual
  list (`shared/Marco/definitive_100_pairs.csv`, itself based on
  `review/coppie_valide_2026-10-17.csv`): removed `@airdropo→@airdropninjagroup` (bot-run group,
  excluded in review), `@gambledemons` and `@binibitnews` (same group as `@demons` /
  `@binibit_top`), `@weexnews→@weex_official` (other app's group); for 4 channels with two groups
  kept the main one (`altri_gruppi`). Added 8 channels: 5 own linked chats from `master.csv` that
  pass the rules (ChainGPT, ASI Alliance, Lithosphere, BC.GAME, CoinTrendz) and 3 found via the
  public t.me pages, group page citing the channel (Watcher Guru, The VSЁ, Zcash). Working
  criteria: group is the channel's own (linked chat, Telegram community, or matching name / link
  back), shared by ≤ 2 channels, ≥ 10 msgs from ≥ 5 users in 7 days, < 50% bot messages,
  channel ≥ 1000 subscribers and posting in the last weeks, public username.
- **Open:** activity of `@watcherguruchat` and `@thevsechat` not measured via API (web only);
  `@crypgptcommunity` was "dubbia" (low activity); 3 crypto-casino pairs (ATOM, 2× BC.GAME):
  team to confirm they are in scope; 32 pairs passed the rules but were never checked by hand.
- **Why:** Marco's manual list kept groups that exist but have no messages and some ad links
  to other projects; the stricter rules, checked against the 73 hand-reviewed pairs, agree with
  the review ~85% of the time and reject all 16 "other project" pairs.
- **Impact:** seed selection (Methodology), message dumps (input list), paper table of pairs.

## 2026-10-18 — Selection rules for the conspiracy pairs; faster pair search
- **Author:** Riccardo (+ Claude Code)
- **Decision:** A conspiracy channel–group pair is chosen by `scripts/select_pairs.py`
  (output `data/interim/conspiracy/pairs/candidate_pairs.csv`, outcome `valida` /
  `da_controllare` / `esclusa` with the reason). Rules: the group is the channel's own (its
  linked discussion chat, or a group in the channel description that cites the channel back or
  has a matching name; description-only otherwise → check by hand; groups seen only in posts
  are not candidates); **the group has a public username** (a linked chat without one cannot
  be opened or checked from outside → excluded); ≥ 10 messages from ≥ 5 users in 7 days, bots
  excluded, < 50% bot messages; channel **≥ 2000 subscribers** and posts in the last 30 days;
  one group per channel and one channel per group; topic US/World news or channel not a
  TGDataset seed → check by hand. Final list = `valida` (sample-checked by hand) + the
  `da_controllare` rows accepted by hand.
  Pair search: `audit_channels.py --topic conspiracy --seeds-only --min-subs 2000 --links
  description --daily-limit 150`: only TGDataset seeds (no linked/recommended channels), small
  channels skipped from the web preview without a resolve, groups only from linked chat +
  description; the queue picks up new web-prefilter rows while it runs (prefilter of the
  ~7,300 unlabelled seeds restarted 2026-10-18). Daily resolve budget of the conspiracy
  account raised **from 100 to 150**.
- **Why:** The 105 hand-review rows mixed shared hub groups and ads found in posts; stricter
  rules applied by a script give a list that only needs a sample check. 2000 subscribers keeps
  the larger, more visible channels; groups without a public username cannot be verified.
  Covid/Extremists seeds were exhausted, so the unlabelled seeds are profiled for free on the
  web first. 150 resolves/day: 0 FloodWait in 9 runs at 100/day; the 19 h FloodWait of
  2026-09-29 came at ~250/day. Stop at the first long FloodWait.
- **Impact:** seed selection (Methodology), `scripts/select_pairs.py`, `scripts/audit_channels.py`
  (`--seeds-only`, `--min-subs`, `--daily-limit`, `group_about.csv`). The same script on crypto
  (≥ 1000 subs) finds 80 of the 100 final crypto pairs as `valida` (the other 20 came from manual
  and web search); the crypto list is unchanged.

## 2026-10-18 — Join the groups first; captcha groups are not verified; DMs checked daily
- **Author:** Riccardo (+ Claude Code)
- **Decision:** (1) Each account joins the **100 groups** of its final pairs first
  (`scripts/join_chats.py --kind groups`); channels are not joined for now (their history and
  comments are read without joining) and may be joined later (`--kind channels`) if joins are
  left over. (2) Joins are slow: ≤ 20 per run, 90–120 s apart, stop at the first FloodWait of
  any length; one person per account at a time. (3) The account never presses buttons or answers
  captchas: groups where a bot gates, restricts or removes new members are only detected (read-only,
  60 s after the join) and logged as `needs_verification` / `removed`; groups needing admin
  approval are skipped without sending a join request. Whether a human may press a plain
  "I'm not a robot" button by hand is **open**: decide as a team (and ask the supervisor) once we
  know how many groups are affected. (4) Nobody can keep `dm_logger.py` running, so DMs are
  collected by `dm_logger.py --once` about once a day (one instance per account at a time); the
  DM observation window of an account starts on the day its groups are joined.
- **Why:** For DM exposure groups matter most: their member list is visible to members, while a
  channel's subscribers are visible only to its admins (limited list). Joining only groups halves
  the joins (Telegram does not publish join limits; on our accounts we have no data yet, so 20/run
  is a cautious guess). Automating a captcha means bypassing an anti-bot check and breaks the
  passive-only rule (CLAUDE.md rule 3). Daily checks: DMs stay in the inbox with their arrival
  date, so counts and timing are kept.
- **Impact:** `scripts/join_chats.py` (log in `data/interim/<topic>/joins/joins.csv`),
  `scripts/dm_logger.py --once`. Paper: Methodology 4.2–4.3 (joins, DM window); Limitations:
  DMs from admins who pick targets from the channel subscriber list are not observed; DMs deleted
  by the sender before the daily check are lost and ex-scam accounts deleted in the meantime lose
  sender role → DM counts are lower bounds; groups behind a captcha are missing. Deviation from the
  scope "join the channels and their groups": tell the supervisor.

## 2026-10-18 — A group must be used as a chat, not only for post comments
- **Author:** Riccardo (+ Claude Code)
- **Decision:** On top of the 2026-10-18 rules, `select_pairs.py` requires the group to be
  used as a chat: ≥ 10 messages that are **not replies** (free messages) from ≥ 5 users in
  the last 7 days. A linked discussion group whose activity is only comments under the
  channel posts is excluded ("solo commenti ai post").
- **Why:** A comment section is part of the channel, not a separate community; the study
  compares channels with groups where users talk to each other. The first 150/day audit
  found mostly US-news channels whose linked chats are comment sections.
- **Impact:** conspiracy `candidate_pairs.csv`: 22 valida + 33 da_controllare (was 35 + 62).
  **Crypto:** the same rule would exclude 12 of the 80 final crypto pairs that the script
  can evaluate (crypto list not changed yet: team to decide, for consistency between arms).

## 2026-10-20 — Conspiracy topic: only Covid/Extremists auto-valid; keyword-ranked queue
- **Author:** Riccardo (+ Claude Code)
- **Decision:** In `select_pairs.py`, TGDataset topics Crypto and Religion join US/World news
  as `da_controllare`: only Covid and Extremists seeds can be `valida` without a manual
  topic check. A new keyword list (`src/utils/conspiracy_terms.py`: QAnon, awakening, deep
  state/NWO, "truth"/disclosure, Covid/vaccines/5G, UFO/esoteric, sovereign/freedom, plus
  DE/IT/ES/FR/RU terms) is applied to channel/group titles and descriptions: column
  `parole_chiave` in `candidate_pairs.csv` (rows with hits listed first), and the conspiracy
  audit queue now puts channels with hits first (before topic priority).
- **Why:** The 2026-10-19 audit turned up "valid" pairs under Crypto/Religion that are not
  conspiracy (crypto trading, Christian apologetics, meme channels). TGDataset's conspiracy
  file mixes topics, so the label alone is not enough. Keywords are a ranking aid and a
  hint for the reviewer, not a label: many clear Covid channels have no keyword (empty
  descriptions), and words like "truth" or "patriot" also hit ordinary channels.
- **Impact:** seed selection and topic check (Methodology); `candidate_pairs.csv` now 20 valida
  + 52 da_controllare.

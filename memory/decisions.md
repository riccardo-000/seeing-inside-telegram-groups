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

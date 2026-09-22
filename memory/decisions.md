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

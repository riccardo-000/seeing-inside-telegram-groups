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

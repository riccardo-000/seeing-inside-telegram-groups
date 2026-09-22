# CLAUDE.md — project context for AI sessions

Shared by all three team members. Read this and `memory/` at the start of every session.

## Project

"Seeing inside Telegram groups" — Research Topics in Cybersecurity (DTU), Project 3.
Measurement study of scams in Telegram: ~100 crypto + ~100 conspiracy/malicious channels
from TGDataset, plus their public linked groups. We compare channels vs groups, admins vs
regular users, and log unsolicited scam DMs received by a passive research account.
Deliverable: a paper (outline in `docs/paper-outline.md`). Full scope in `README.md`.

Stack: Python ≥ 3.11, Telethon, pandas, python-dotenv, tqdm.

## Hard rules

1. **Never commit secrets.** No `*.session`, `*.session-journal`, `.env`, API ids/hashes,
   phone numbers, or salts in any tracked file, commit message, or log output.
   Config is read only through `src/utils/config.py`.
2. **Never commit raw or intermediate data.** `data/raw/` and `data/interim/` stay local.
   Only pseudonymized, aggregated outputs may go in `data/processed/`, after review.
3. **Passive observation only.** Code must never send messages, reply, react, click links,
   or answer DMs. Only public chats may be joined. If a task seems to require interaction,
   stop and ask.
4. **Log every project decision** in `memory/decisions.md` (date, author, decision, why).
   This includes methodology choices (seed selection, labels, thresholds) — they end up in
   the paper.
5. Before committing, run `git status` and check that nothing under `data/raw/`,
   `data/interim/`, or any `.session`/`.env` file is staged.
6. Do not install dependencies without asking the human.
7. Everyone works directly on `main`: `git pull` before starting, commit + push at the end
   of the session (see `CONTRIBUTING.md`). No PR process.
8. **Personal data is pseudonymized at ingestion** via `src/utils/privacy.py` — collectors
   must never write raw user ids, usernames, names or phones to disk
   (see `memory/data-protection.md`).

## Layout

```
.
├── CLAUDE.md            # this file
├── README.md            # scope, setup, ethics
├── CONTRIBUTING.md      # git workflow, commits, who does what
├── requirements.txt
├── .env.example         # template; real .env is gitignored
├── src/
│   ├── collect/         # channels.py, messages.py, dms.py (Telethon, read-only)
│   ├── analyze/         # authors.py, tone.py (pandas)
│   └── utils/           # config.py (.env loading), privacy.py (pseudonymization)
├── data/
│   ├── raw/             # gitignored
│   ├── interim/         # gitignored
│   └── processed/       # pseudonymized aggregates only
├── docs/                # paper-outline.md, meeting-notes.md
└── memory/              # shared AI/team memory: decisions.md, data-protection.md, ...
```

## Shared memory

`memory/` is the team's shared, versioned memory for AI sessions (see `memory/README.md`).
Personal/local assistant memory does not reach teammates — anything the others need to
know goes in `memory/`.

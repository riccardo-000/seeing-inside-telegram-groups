# Contributing

Three people, all using AI assistants. These rules keep the repo consistent and safe.

## Branches

- `main` is always working and reviewed. No direct pushes.
- One branch per feature: `feat/<topic>`, `fix/<topic>`, `docs/<topic>`, `analysis/<topic>`
  (e.g. `feat/join-channels`, `analysis/tone-baseline`).
- Open a PR into `main`; at least **one other member** reviews before merging.
- Keep branches short-lived; rebase on `main` before opening the PR.

## Commits

[Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <short summary>

feat(collect): add resumable message dump
fix(dms): handle FloodWaitError
docs(paper): draft methodology section
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `analysis`.
Scopes: `collect`, `analyze`, `utils`, `paper`, `memory`, `repo`.

AI-assisted commits are fine; the human committing is responsible for the content.
Keep any co-author trailer the assistant adds.

## Before every commit / PR

- [ ] `git status` shows no `*.session`, `.env`, `data/raw/`, `data/interim/` files.
- [ ] No API ids, hashes, phone numbers, usernames or user ids in code, notebooks or outputs.
- [ ] Notebooks cleared of outputs that contain raw messages.
- [ ] New decisions logged in `memory/decisions.md`.

## Who does what

| Area | Owner | Backup |
|---|---|---|
| Collection: seed list, joins, message dump (`src/collect/channels.py`, `messages.py`) | _TBD_ | _TBD_ |
| DM logging + admin/user roles (`src/collect/dms.py`, `src/analyze/authors.py`) | _TBD_ | _TBD_ |
| Tone & scam classification, channel vs group (`src/analyze/tone.py`) | _TBD_ | _TBD_ |
| Paper writing / related work (`docs/paper-outline.md`) | shared | — |

Fill in names at the first meeting and log it in `memory/decisions.md`.

## Working with AI assistants

- Start each session by having the assistant read `CLAUDE.md` and `memory/`.
- Decisions made during a session → `memory/decisions.md` before ending it.
- Don't let the assistant run collection against Telegram without you watching it
  the first time; check rate limits and that it never sends anything.
- Only one member runs the research Telegram account at a time (session files are
  per-machine and must not be shared through git).

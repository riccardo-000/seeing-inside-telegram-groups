# Contributing

Three people, all using AI assistants. Keep it simple: everyone works on `main`.

## Workflow

```bash
git pull                 # always, before starting
# ... work ...
git status               # check nothing sensitive is listed (see below)
git add <files>
git commit -m "docs(memory): add seed selection criteria"
git push                 # if rejected: git pull, then push again
```

- Commit small and often, push at the end of each session so the others see
  `memory/` updates.
- If you are about to do something big or experimental, a branch is fine, but not required.
- Conflicts in `memory/decisions.md`: keep both entries, in date order.

## Commit messages

Short, with a type prefix (Conventional Commits, loosely):
`feat`, `fix`, `docs`, `analysis`, `chore` — e.g. `feat(collect): resumable message dump`,
`docs(memory): log seed selection`.

## Never commit

- `*.session`, `.env` — Telegram credentials / API keys / salt.
- `data/raw/`, `data/interim/` — collected data (gitignored, but double-check `git status`).
- Notebook outputs showing messages.

## Who does what

To be decided by the team; log it in `memory/decisions.md`. The paper must state who did what.

## Working with AI assistants

- Start each session: have the assistant read `CLAUDE.md` and `memory/`.
- End each session: decisions → `memory/decisions.md`, then commit + push.
- Watch the first real collection run against Telegram yourself (rate limits, nothing sent).
- Only one member runs the research Telegram account at a time; session files are per-machine.

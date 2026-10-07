# Contributing

Three people, all using AI assistants. Keep it simple: everyone works on `main`.

## Workflow

```bash
git pull                 # always, before starting
# ... work ...
git status               # check no .session / .env is listed
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
- Notebook outputs showing messages.

## Who does what

No fixed roles: everyone works on everything, equal contribution (decisions.md, 2026-09-29).
The course requires the paper to state who did what, so keep commit authors and the
`Author` field in `memory/decisions.md` accurate.

## Working with AI assistants

- Start each session: have the assistant read `CLAUDE.md` and `memory/`.
- End each session: decisions → `memory/decisions.md`, then commit + push.
- Watch the first real collection run against Telegram yourself (rate limits, nothing sent).
- The two research Telegram accounts (crypto, conspiracy) are shared: everyone logs in on
  their own machine (own `.env` with the same values, own `.session` per account). Coordinate via `memory/collection-log.md`.
  `.env` values are passed in person / password manager, never via git or group chats.

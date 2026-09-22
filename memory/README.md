# memory/ — shared memory for the team's AI sessions

Each of us uses an AI assistant, and each assistant's local memory is private to one
machine. This folder is the **shared, versioned** memory: whatever a session learns or
decides that the others need goes here, and is committed like code.

## Convention

- **Read first.** At the start of a session, the assistant reads `CLAUDE.md` and every file in `memory/`.
- **`decisions.md`** — append-only log of project decisions. One entry per decision:

  ```
  ## YYYY-MM-DD — <short title>
  - **Author:** <name> (+ AI assistant if used)
  - **Decision:** what was decided
  - **Why:** reasoning / alternatives considered
  - **Impact:** files, methodology or paper sections affected
  ```

  Never rewrite old entries; if a decision is reversed, add a new entry that references it.
- **Other files** (optional), one topic per file, kebab-case: e.g. `seed-selection.md`,
  `telethon-gotchas.md`, `label-definitions.md`. Start each with a one-line summary.
- **What does NOT go here:** secrets, credentials, raw messages, usernames or user ids,
  anything from `data/raw/`. Also not things already obvious from the code or git history.
- Commit memory updates with `docs(memory): ...`, in the same PR as the related change.
- If two people edit the same file, resolve conflicts by keeping both entries in date order.

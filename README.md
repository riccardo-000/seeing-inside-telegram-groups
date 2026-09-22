# Seeing inside Telegram groups

Group project (3 people) for **Research Topics in Cybersecurity** (DTU) — Project 3.
Goal: a measurement study of scam activity in Telegram channels and their linked
discussion groups, to be written up as a paper.

## Research questions

1. How do tone and content differ between a **channel** (admin-controlled broadcast)
   and its **linked discussion group** (open to members)?
2. Who posts scam content: **admins** or **regular users**?
3. How many unsolicited **scam DMs** does a passive member receive, and do they come
   from admins of the monitored chats or from regular members?
4. How do **crypto** communities compare with **conspiracy/malicious** ones, with a
   focus on suspicious communities (scam / carding)?

## Scope (agreed with the supervisor)

- Seed: ~100 **crypto** channels and ~100 **conspiracy/malicious** channels, starting from
  [TGDataset](https://github.com/SystemsLab-Sapienza/TGDataset) (collected up to July 2022)
  and complemented with newer sources: still-active channels' recent posts, TeraGram
  (ICWSM '26, up to 2025), and Telegram public search.
- Join the channels and their groups — both linked discussion groups and public groups
  advertised via links in channel posts — **public groups only**, passive observation.
- Automatically download the chat history.
- Analyze message tone and authors: distinguish admins from users attempting scams.
- Count scam DMs received by the research account and check whether senders are
  admins or regular users.
- Compare channel vs group, focusing on suspicious communities (scam/carding).

## Repository layout

```
src/
  collect/   channels.py (seed + join), messages.py (dump), dms.py (DM logging)
  analyze/   authors.py (admin vs user roles), tone.py (tone + scam labels)
  utils/     config.py (.env loading), privacy.py (pseudonymization at ingestion)
data/
  raw/       raw dumps — gitignored, never committed
  interim/   intermediate files — gitignored
  processed/ pseudonymized, aggregated outputs only
docs/        paper-outline.md, meeting-notes.md
memory/      shared context/decision log for the team's AI sessions
```

## Setup

Requires **Python ≥ 3.11** (pandas 3.x).

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in your own values
```

Get `TELEGRAM_API_ID` / `TELEGRAM_API_HASH` from <https://my.telegram.org> → *API development tools*.
Use a **dedicated research account**, not a personal one. The Telethon `*.session` file
created on first login is a credential for that account: it is gitignored and must never
be shared or committed.

> Status: `src/` contains skeletons only (signatures + docstrings). Collection logic is
> not implemented yet.

## Ethics & scope

- **Passive observation only.** The research account joins chats and reads history.
  It never posts, replies, reacts, votes, or clicks links, and never answers DMs.
- **Public chats only.** We only join channels and groups that are publicly reachable
  (public `@username`, public linked discussion group, or public invite link). No invite-only or private
  groups, no deception to gain access.
- **No interaction with users.** Nobody is contacted; incoming DMs are logged, not answered.
  Links and attachments in scam messages are not opened.
- **Pseudonymized at ingestion.** User IDs are replaced by keyed hashes (HMAC with a secret salt
  kept outside the repo) before anything is written to disk; message text is redacted of
  phones, emails and user mentions; usernames, display names and phone numbers are
  dropped. Raw data stays on the collectors' machines (`data/raw/`, gitignored) and is not
  shared publicly. The paper reports only aggregate results; quoted messages are
  paraphrased or redacted so they cannot be searched back to an individual.
- **Minimization.** We collect message text and metadata needed for the research
  questions; no media is downloaded.
- **Rate limiting.** Collection respects Telegram flood limits and the Telegram ToS.
- **Retention.** Raw data is deleted at the end of the project unless otherwise agreed
  with the supervisor.

See also `docs/paper-outline.md` (Ethics section) and `memory/decisions.md`.

## Team

See `CONTRIBUTING.md`.

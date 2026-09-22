# Collection log — who is running what on the shared Telegram account

One research account, used by all three from their own machines. Before starting any
script that talks to Telegram: `git pull`, read the last entries, add yours, commit + push.
When done: fill in the end time and outcome, commit + push.

## Rules

- **Joins:** one person at a time, never in parallel. Slow (≥ 30 s between joins), and stop
  on `FloodWaitError`: note the wait time here.
- **Message dumps:** each person dumps only the chats assigned to them (see below). One file
  per chat in `data/raw/`, so git never conflicts.
- **DM logger:** only one instance running at a time (DMs arrive per account, not per machine).
- **FloodWait / warnings / restrictions:** log them here immediately and tell the others.
  If the account gets restricted, everyone stops.
- Max **500 channels + supergroups** per account: track the running total below.

## Chat assignment

_To be filled once the seed list exists (split into three disjoint sets)._

| Member | Chats (file / range) |
|---|---|
| | |

Joined so far: **0 / 500**

## Log

Newest at the bottom.

| Start | End | Who | Job | Chats | Outcome / FloodWait |
|---|---|---|---|---|---|
| | | | | | |

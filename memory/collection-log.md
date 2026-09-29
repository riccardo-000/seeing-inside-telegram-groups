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
| 2026-09-29 | 2026-09-29 | Riccardo | First Telethon login (`scripts/login.py`), creates local `.session` | — | OK, authorized. No FloodWait. |
| 2026-09-29 | 2026-09-29 | Riccardo | Liveness check test (`scripts/check_alive.py`), resolve + channel info only, no joins, 10 s delay | 5 crypto seeds (TGDataset) | OK: 4 alive, 1 not found. No FloodWait. |
| 2026-09-29 | 2026-09-29 | Riccardo | Liveness check (`scripts/check_alive.py`), no joins, 10 s delay | 2 more crypto seeds (TGDataset) | OK: 0 alive, 2 not found. No FloodWait. Zenodo downloads stopped at 7 candidates. |
| 2026-09-29 | 2026-09-29 | Riccardo | Read-only peek (`scripts/peek_channel.py`): last 200 posts + comments of top 10 threads, no joins | 2 crypto channels (TGDataset test) | OK: ~16 requests, no FloodWait. Comments of linked group readable without joining. |
| 2026-09-29 | 2026-09-29 | Riccardo | Read-only: history of MoneroEconomicForum linked group (last 100 msgs) + 6 joiner profiles, no joins | 1 group | OK, readable without joining. No FloodWait. |
| 2026-09-29 | 2026-09-29 | Riccardo | Read-only: sponsored messages (ads) shown in MoneroEconomicForum (GetSponsoredMessages; no view/click reports) | 1 channel | OK, 1 ad returned. No FloodWait. |
| 2026-09-29 | | Riccardo | Read-only search for channel + standalone group pairs (`scripts/find_pairs.py`): keyword search, channel info/posts, group history; no joins; 7 s/request, 30 s/search, cap 400 requests / 60 min | crypto keyword search | |

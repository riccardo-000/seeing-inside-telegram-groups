# Collection log — who is running what on the shared Telegram accounts

Two research accounts since 2026-10-07: **crypto** (the original one) and **conspiracy**,
used by all three from their own machines. Scripts pick one with `--topic`; write the
account in the *Chats* column of every entry. Limits below apply **per account**. Before starting any
script that talks to Telegram: `git pull`, read the last entries, add yours, commit + push.
When done: fill in the end time and outcome, commit + push.

## Rules

- **Joins:** one person at a time, never in parallel. Slow (≥ 30 s between joins), and stop
  on `FloodWaitError`: note the wait time here.
- **Message dumps:** each person dumps only the chats assigned to them (see below). One file
  per chat in `data/raw/`, so git never conflicts.
- **DM logger:** only one instance per account at a time (DMs arrive per account, not per machine).
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
| 2026-09-29 12:33 | 2026-09-29 13:22 | Riccardo | Read-only search for channel + standalone group pairs (`scripts/find_pairs.py`): keyword search, channel info/posts, group history; no joins; 7 s/request, 30 s/search, cap 400 requests / 60 min | crypto keyword search | ~326 requests, no FloodWait. Stopped at 115/124 chats by a network ConnectionError (timeouts), not by Telegram. |
| 2026-09-29 | 2026-09-29 | Riccardo | Read-only: description of @Airdrop + resolve its t.me links/mentions, no joins | 1 channel | OK, 4 requests, no FloodWait. |
| 2026-09-29 15:05 | 2026-09-29 15:55 | Riccardo | Full channel audit (`scripts/audit_channels.py`): resolve, description, 200 posts, linked group, all linked usernames, group activity, similar-channel recommendations; no joins; 6 s/request, max 250 username resolves/day; fed by TGDataset crypto candidates streamed from Zenodo (no Telegram) + 42 active channels + parents of comment chats | crypto | **FLOODWAIT 68,674 s (~19 h) at 15:55 → no Telegram scripts until 2026-09-30 ~11:00.** Hit after ~127 username resolves in the audit (+ ~100–150 earlier today in find_pairs/tests): likely the daily ResolveUsername limit. Zenodo streams (no Telegram) keep running. |

| 2026-09-30 18:30 | 2026-09-30 18:40 | Riccardo | No Telegram: built the conspiracy seed candidate list from TGDataset's GitHub `conspiracy_channels.csv` (`scripts/seeds_conspiracy.py`) -> 11,570 usernames, 4,763 with an English topic label | — | OK, 0 resolves. No Zenodo download needed for the conspiracy arm. |
| 2026-09-30 | — | — | Added `scripts/prefilter_tme.py`: liveness/activity check over the public t.me web preview (HTTPS, no MTProto, no resolves). | — | Parser verified 19:35 on 5 known chats (matches API results); title/subscribers parsing fixed for /s/ pages. |

**2026-09-30 ~11:00 — the 68,674 s FloodWait of 2026-09-29 15:55 has expired by the clock (not yet re-tested with a call). Today's resolve budget: 100 for the whole account (`data/interim/resolve_ledger.csv` is still empty). Joined: 0/500 — no joins have been made yet.**
| 2026-09-30 19:40 | 2026-09-30 19:48 | Riccardo | Web prefilter (`prefilter_tme.py`, t.me/s pages, no API, no account) of all TGDataset crypto candidates, 2 s/request | 487 crypto not yet audited | OK, no HTTP 429 (one network error, resumed): 123 active channels, 41 no preview, 194 inactive, 125 dead, 4 other. 0 resolves. |
| 2026-09-30 19:52 | 2026-09-30 21:18 | Riccardo | API audit (`audit_channels.py`): master.csv priority (34 project channels, 9 manual groups, 3 aggregators) then 164 TGDataset channels alive per web prefilter; web check before every resolve; no joins; 6 s/request; ≤100 resolves (ledger), ≤8 new resolves per channel; stop on any FloodWait > 30 s or on the 2nd | crypto | OK, stopped by hand. 597 requests, **92 resolves** (ledger), 437 free web checks, **0 FloodWait**. 69 channels audited: 29 with an active public group, 20 inactive, 9 no group, 3 dead, 8 other. Priority queue done; 145 TGDataset channels still queued. |
| 2026-10-05 18:48 | 2026-10-05 19:56 | Riccardo | API audit (`audit_channels.py`), same rules as 2026-09-30: master.csv priority, then TGDataset (web-alive), then known channels; web check before every resolve; no joins; 6 s/request; ≤100 resolves (ledger), ≤8 new per channel; stop on FloodWait > 30 s or 2nd | crypto| OK: stopped at the daily budget. 100 resolves (ledger), ~1,000 API requests over two runs (one restart after a non-ASCII username bug, fixed), 0 FloodWait. |
| 2026-10-06 10:51 | 2026-10-06 11:25 | Riccardo | API audit (`audit_channels.py`), same rules as 2026-10-05: master.csv priority, then TGDataset (web-alive), then known channels; web check before every resolve; no joins; 6 s/request; ≤100 resolves (ledger), ≤8 new per channel; stop on FloodWait > 30 s or 2nd | crypto| Stopped by hand so the team can browse manually in the app (same account, same limits). 30 resolves (ledger), 0 FloodWait; 28 channels audited, 12 with an active public group. **Manual browsing in the app also resolves usernames on this account: keep it light; prefer https://t.me/s/<name> in a logged-out browser.** |
| 2026-10-06 11:02 | 2026-10-06 12:36 | Riccardo | No Telegram API: web prefilter (`prefilter_tme.py`, t.me/s pages, no account) of conspiracy candidates, priority order (labelled first), 2 s/request. Output now in `data/interim/conspiracy/` | 4,881 labelled conspiracy candidates | Stopped by hand at 1,783/4,881 (Extremists, Covid, part of US news); resumable. 386 active (posts in 30 d), 631 inactive, 231 no preview, 498 dead/empty. No HTTP 429, 0 resolves. |
| 2026-10-06 15:15 | 2026-10-06 16:23 | Riccardo | No Telegram API: web prefilter resumed (same command, run2), remaining labelled conspiracy candidates, 2 s/request | 3,098 labelled conspiracy candidates | Stopped by hand at 3,482/4,881 total (1,699 this run). Cumulative: 806 active (posts in 30 d), 1,259 inactive, 414 no preview, 939 dead/empty. No HTTP 429, 0 resolves. |
| 2026-10-07 09:15 | 2026-10-07 09:47 | Riccardo | API audit (`audit_channels.py`) to find more crypto pairs, same rules as 2026-10-06 (priority from master.csv, then TGDataset web-alive, then known); **bot messages now excluded from group activity**; no joins; 6 s/request; ≤100 resolves (ledger), ≤8 new per channel; stop on FloodWait > 30 s or 2nd | crypto| Paused by hand (Riccardo editing files). 52 resolves (ledger), 0 FloodWait, 1 transient Telegram RpcCallFail (server side). 48 left today. |
| 2026-10-07 09:18 | 2026-10-07 ~09:50 | Riccardo | No Telegram API: web prefilter run3 (same command), all remaining conspiracy candidates: rest of labelled, then unlabelled; 2 s/request | 8,088 conspiracy candidates | Stopped by hand for the per-topic folder refactor at ~774/8,088 (4,256/11,570 total in `data/interim/conspiracy/prefilter/tme_prefilter.csv`). 0 resolves. Resume with `prefilter_tme.py --topic conspiracy`. |
| 2026-10-07 09:58 | 2026-10-07 09:58 | Riccardo | First Telethon login of the new **conspiracy** account (`login.py --topic conspiracy`), creates local `research_conspiracy.session` | conspiracy account | OK, authorized. No FloodWait. New account: start slow (few resolves/joins per day). |
| 2026-10-07 10:03 | 2026-10-07 10:32 | Riccardo | API audit (`audit_channels.py --topic crypto`), resumed after the folder refactor; same rules as 09:15 (master.csv priority, then TGDataset web-alive, then known; bot messages excluded); no joins; 6 s/request; ≤100 resolves/day (ledger: 52 used today), ≤8 new per channel; stop on FloodWait > 30 s or 2nd | crypto account | Crashed once on a legacy basic group (InputPeerChat; fixed e0dec3c, restarted). Daily budget used up: 100/100 resolves today, 0 FloodWait. ~19 channels audited this run; new active pairs incl. MEXC_ENchannel, solidusaitech, changelly, wazirx. |
| 2026-10-07 10:03 | — | Riccardo | **First API audit on the conspiracy account** (`audit_channels.py --topic conspiracy`): 1,495 prefilter-alive conspiracy seeds, most promising first (topic priority, group-like t.me links in description, posts in 30 d); no joins; **new account, slow start:** 8 s/request, ≤30 resolves this run, ≤4 new per channel; stop on FloodWait > 30 s or 2nd | conspiracy account | running |

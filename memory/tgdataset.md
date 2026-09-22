# TGDataset — how it is built and what we can use (inspected 2026-09-22)

Sources: GitHub `SystemsLab-Sapienza/TGDataset` (README, labeled_data, sample),
Zenodo record 7640712 (CC-BY 4.0, published 2023-02-14). Paper: `docs/prof-material/2025-lamorgia-tgdataset.pdf`.

## What's on GitHub (small, free to use now)

| File | Rows | Columns | Notes |
|---|---|---|---|
| `labeled_data/ch_to_topic_mapping.csv` | 19,768 | `ch_ID, topic` | **English channels only.** IDs only, no username. |
| `labeled_data/channel_to_language_mapping.csv` | 120,979 | `ch_id \t language` (TAB-separated) | ru 42,983 · (none) 23,305 · en 19,768 · fa 16,779 · de 4,950 |
| `labeled_data/conspiracy_channels.csv` | 11,618 | `ch_id, username` | All languages, **has usernames**. From the Conspiracy Money Machine paper. |
| `labeled_data/sabmyk_network.csv` | 236 | `ch_ID, username` | One conspiracy network. |
| `tgdataset_sample/tgdataset_preview.json` | 10 channels | full format | Good for writing/testing the parser offline. |

Topic counts (English): Religion 4,725 · US news 2,948 · Videogame modding 1,957 · Covid 1,716 ·
**Carding 1,489** · Entertainment 1,440 · World news 995 · **Extremists and radicals 989** ·
Indian edu 939 · Software 871 · Porn 830 · **Crypto 563** · Social 306.
Conspiracy list ∩ English topics = 4,902 (mostly US news, Covid, Religion; 107 labelled Crypto).

## Full dataset on Zenodo

- 4 archives: `TGDataset_1.tar.gz` 19.7 GB, `_2` 20.4 GB, `_3` 21.1 GB, `_4` 9.5 GB
  (~71 GB compressed, **~460 GB uncompressed**), 121 JSON files of ≤1,000 channels.
- Split **alphabetically by username** (not by topic) → the channels we want are spread over
  all four archives.
- JSON: `{channel_id: {creation_date, username, title, description, scam, verified,
  n_subscribers, text_messages: {msg_id: {message, date, author, is_forwarded,
  forwarded_from_id, forwarded_message_date}}, generic_media: {...}}}`.
  All values are strings (e.g. `"False"`, `"1450995556.0"`); `author` is `"None"` for channel posts.

## Gotchas for us

1. **Channels only**: no groups, no member messages, no comments (paper §8). Groups must be
   discovered via linked discussion groups (API) or links in posts.
2. **Only plain-text links survive.** Message entities are not stored, so links hidden behind
   text (hyperlinks/buttons) are lost → extracting `t.me/...` from TGDataset text
   underestimates advertised groups. Recent posts fetched via API do include entities.
3. **Topic CSV has IDs but no usernames.** Telethon cannot open a channel from a bare ID
   (needs an access hash) → we need usernames, which are only in the big JSON files
   (or in `conspiracy_channels.csv`).
4. Data stops **July 2022**: many channels will be deleted/renamed/banned.
5. Topic labels exist only for English channels.

## Proposed plan (not decided)

- Conspiracy seeds: `conspiracy_channels.csv` (has usernames) → no download needed.
- Crypto / Carding / Extremists seeds: need usernames → stream the Zenodo archives once and
  extract **only** `id, username, title, description, scam, verified, n_subscribers` plus the
  `t.me` links found in text, without unpacking 460 GB to disk (stream the tar, parse JSON
  per file). Result: a small CSV kept in `data/interim/`.
- Pilot: start with `TGDataset_4` (9.5 GB) to test the pipeline.
- Then check which seeds are still alive via API (slowly, see collection-log) and fetch
  **recent** messages live instead of relying on 2022 messages.

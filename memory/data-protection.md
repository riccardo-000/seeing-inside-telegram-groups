# Data protection: how personal data is obfuscated

Status: **design agreed in principle (2026-09-22), details open** — see "Open questions".
Code: `src/utils/privacy.py` (skeleton). Supervisor's brief: "Store no personal data";
"redact personal data at ingestion, report only in aggregate".

## Principle: pseudonymize at ingestion

Collectors pass every Telethon object through `privacy.sanitize_*` **before** writing to
`data/raw/`. No raw user id, username, name or phone number ever touches disk, so even
`data/raw/` holds no direct identifiers.

## What happens to each field

| Data | Treatment | Why |
|---|---|---|
| User id (message sender, admin, DM sender, forward-from-user) | `HMAC-SHA256(PSEUDONYM_SALT, id)` → first 16 hex chars, prefix `u_` | Deterministic → same person has the same pseudonym across chats, so admin ↔ DM-sender matching still works. A plain hash is brute-forceable (ids are small ints). |
| Username, first/last name, bio, photo, phone | **Dropped** | Not needed for any research question. |
| User flags (`bot`, `scam`, `fake`, `premium`) | Kept | Useful signals, not identifying. |
| Message text | Kept, **redacted**: phones → `<PHONE>`, emails → `<EMAIL>`, user @mentions and `t.me/<user>` → `<USER>` | Tone/scam analysis needs the text; contact details of third parties do not. |
| URLs / domains, crypto wallet addresses, invite links to public chats | Kept | They are the scam indicators themselves. |
| Channel / group ids, usernames, titles | Kept | Public entities, not persons (needed for channel-vs-group comparison). |
| Media | Not downloaded; only media type | Minimization; avoids illegal/copyrighted content (as TGDataset). |

## The salt (`PSEUDONYM_SALT`)

- Long random string, in each collector's local `.env`; never committed.
- **One shared salt** for the whole team (shared out-of-band, e.g. in person), otherwise
  pseudonyms from different machines don't match.
- **Destroyed at the end of the project** → pseudonyms can no longer be linked to ids.
- Generate with: `python3 -c "import secrets; print(secrets.token_hex(32))"`

## In the paper

- Report only aggregates. Quoted messages are paraphrased/translated so they can't be
  searched back to a person; never print pseudonyms.
- The released dataset (if any) contains aggregates or re-keyed pseudonyms only.

## Residual risks (→ Limitations / Ethics)

- Names or personal details written in free text (e.g. "ask John Smith") are not caught
  by regexes; optional NER pass could reduce this.
- Pseudonymized data is still personal data under GDPR while the salt exists.
- Wallet addresses can sometimes be linked to people via blockchain analytics; we keep
  them only as scam indicators and do not attempt attribution.

## Open questions (team to decide → decisions.md)

- [ ] Regexes for phones/emails: which formats/languages to cover?
- [ ] Distinguishing user @mentions from channel/group @mentions (resolve via API vs. keep a list of known chats).
- [ ] NER on free text: yes/no?
- [ ] Keep full URLs or only domains?
- [ ] Who holds the salt, and when exactly is it destroyed?

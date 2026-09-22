# Paper outline — Seeing inside Telegram groups

Working title: *Seeing inside Telegram groups: admins, users and scams in crypto and
conspiracy communities*

## Abstract

_(~150–200 words, write last.)_ Problem: scams on Telegram spread both through channels
and their open discussion groups. Approach: passive measurement of ~200 channels from
TGDataset and their public linked groups, plus a log of unsolicited DMs. Key findings: _TBD_.

## 1. Introduction

- Telegram as a hub for crypto and conspiracy communities; channel/group structure.
- Gap: prior work mostly studies channels; little on linked groups and on who scams (admins vs members).
- Research questions (see README) and contributions.

## 2. Background

- Telegram channels, supergroups, linked discussion groups, admin roles, anonymous admins.
- Scam taxonomy: investment/pump-and-dump, impersonation, phishing/drainers, carding.

## 3. Related work

- TGDataset (La Morgia et al.) and prior large-scale Telegram measurements.
- Crypto scams / pump-and-dump on Telegram.
- Conspiracy and extremist communities on Telegram.
- Carding and underground markets on messaging platforms.
- DM spam / social engineering studies.

## 4. Methodology

- 4.1 Seed selection from TGDataset (criteria, categories, sizes).
- 4.2 Data collection: joining, linked-group resolution, message dump, time window, rate limits.
- 4.3 DM logging with a passive account.
- 4.4 Role identification: admin vs regular user.
- 4.5 Tone analysis and scam classification (labels, baseline, validation on a manually labelled sample).
- 4.6 Pseudonymization and data handling.

## 5. Results

- 5.1 Dataset overview (chats reachable, joined, messages, active users).
- 5.2 Channel vs group comparison.
- 5.3 Admins vs users in scam content.
- 5.4 Unsolicited DMs: volume, types, sender roles.
- 5.5 Crypto vs conspiracy; focus on scam/carding communities.

## 6. Discussion

## 7. Ethics

Passive observation, public chats only, no interaction, pseudonymization, minimization,
retention, no media download. Discuss expectations of privacy in public groups and the
research account's status as a member. (Mirror README "Ethics & scope".)

## 8. Limitations

- Seed bias from TGDataset (age of the dataset, deleted channels).
- Admin lists not always visible; anonymous admins.
- DM volume depends on a single account's visibility.
- Classifier precision/recall; language coverage.
- Observation window length.

## 9. Conclusion

## References

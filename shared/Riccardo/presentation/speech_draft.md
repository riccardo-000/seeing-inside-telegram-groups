# Speech draft — "Seeing Inside Telegram Groups" (10 min, 12 slides)

Revised after Marco's review against the prof's brief (1 project, 2 type of paper, 3 status, 4 plan, 5 who does what). Same text as the speaker notes. Speakers: Riccardo 1–4 and 12, Marco 5–8, Simone 9–11. If short on time, cut slide 8 first; never cut slide 12 (it covers points 4 and 5 of the brief).

**Slide 1 — Seeing Inside Telegram Groups** · RICCARDO (0:00-0:15)

Hi everyone, we are Marco, Simone and Riccardo. Today we'll present our research project, the main findings obtained so far, and our plan for completing the final paper.

**Slide 2 — Channels broadcast; linked groups talk back** · RICCARDO (0:15-1:05)

Telegram channels are mainly used for broadcasting: only the admins post. Their linked discussion groups let regular users, administrators and bots interact. Previous research has already studied Telegram channels, public groups, scams and harmful content; for example TGDataset collects the channels, and Slobozhan and Alvisi compare or link channels and groups. Our specific goal is to compare each channel systematically with its own discussion group, across several dimensions: what becomes visible when we look at the discussion layer and not only at the official channel? We do it in two communities, crypto and conspiracy. Our final deliverable will be a technical paper based on this empirical measurement study.

**Slide 3 — Data: 195 channel–group pairs, observed passively** · RICCARDO (1:05-1:55)

We collected data from 195 channel-group pairs: 98 crypto and 97 conspiracy, starting from TGDataset. The dataset contains about 3.8 million messages over fourteen weeks, from late July to early November 2026. Collection was passive: we monitored public communities without posting messages or interacting with users. A key part of our approach is to distinguish the channel's official posts, administrators writing inside the group, regular users, and bots.

**Slide 4 — Groups carry the volume: 10–50× more messages** · RICCARDO (1:55-3:00)

The first result concerns activity. In the typical pair, groups are much more active than their channels: about fifty times more messages per day in crypto and ten times more in conspiracy. The format also differs: channel posts carry links and media much more often, while group messages are mostly conversational text. These differences hold across our robustness checks, for example without truncated observation windows or without the largest group. Now Marco will present what we found about the content of these discussions.

**Slide 5 — ~75% of group messages are semantically non-aligned** · MARCO (3:00-4:10)

To check whether groups simply repeat what their channels publish, we used Qwen3, a multilingual embedding model. For each eligible group message we computed its maximum cosine similarity to the observed posts of its own channel. Using a threshold of 0.52, calibrated on a separate set of one hundred examples, messages below the threshold are semantically non-aligned. The result is about 75% in crypto and 76% in conspiracy, with no significant difference between the pair-level means. So a large share of group discussion is not closely represented in the channel's posts. However, this does not prove that these topics originated in the groups.

**Slide 6 — What the non-aligned messages do** · MARCO (4:10-4:55)

What are these non-aligned messages doing? We coded a separate sample of 1,170 messages, six per channel-group pair. Crypto groups show more greetings and social interaction, while conspiracy groups share much more news: about 22% of the coded conspiracy messages, against 3% in crypto. These findings are exploratory: a single coding pass without independent validation, so they are not definitive prevalence estimates.

**Slide 7 — Crypto: channels invite more, flagged invites cluster** · MARCO (4:55-5:40)

For the crypto deep dive we focused on invitations to register on platforms: referral links, sign-up links and related wording. In the typical pair the channel has a much higher invitation rate: about 3.7% of posts, against 0.04% of non-bot group messages. In absolute numbers groups still contain more invitations, because they have far more messages. The most striking result is concentration: of about 7,700 group invitations flagged as suspicious under our definition, more than 7,400, that is 96%, come from a single referral group. Flagged does not mean confirmed scam. We also report over 10,500 bot invitations separately.

**Slide 8 — Who posts links: channels, then admins, then users** · MARCO (5:40-6:00, cut first if short on time)

Separating the three voices gives more context. In crypto almost 80% of channel posts contain a link, against about 9% of admin messages in the group and less than 1% of regular users' messages, as median rates across eligible pairs. This counts any link, not only invitations. Now Simone will discuss toxicity in conspiracy communities.

**Slide 9 — Conspiracy: groups are 4 times as toxic as their channels** · SIMONE (6:00-7:10)

For conspiracy communities we analysed about one million messages with Toxicity-Lens, a multilingual classifier for several forms of harmful language. At our main threshold, about 2% of channel posts and 8.6% of group messages are classified as toxic. Across the 96 completed pairs, the group is more toxic in 82 cases, with a median paired increase of about 2.7 percentage points. By voice, channels have the lowest classified toxicity, then group administrators, then regular users. These are model-based findings: independent human validation remains a limitation.

**Slide 10 — Toxic messages are more likely to receive toxic replies** · SIMONE (7:10-8:10)

We also looked at how toxicity relates to conversations. Using Telegram's reply references we analysed about 384,000 parent-reply pairs. A reply to a message classified as toxic was itself toxic about 21% of the time, against about 8% after a non-toxic message. This positive association appears in all 51 groups that meet our minimum sample size. It does not establish causation: recurring users, discussion topics and moderation can also contribute.

**Slide 11 — What groups add** · SIMONE (8:10-8:45)

Overall, our findings show three differences between channels and their groups. First, groups contain much more activity and a large share of semantically non-aligned discussion. Second, promotion differs between channels, administrators and users, and suspicious invitation signals are concentrated in a few crypto groups. Third, conspiracy groups show higher classified toxicity, and toxic replies are associated with toxic parent messages. Riccardo will close with our status and plan.

**Slide 12 — Project status and roadmap to 3 January** · RICCARDO (8:45-10:00)

These are our main findings so far, but the project is not finished. We have completed the data collection and the main structural, semantic, promotional and toxicity analyses. What remains: we keep monitoring unsolicited private messages until the first of December, then we analyse those contacts, write the related work, limitations and ethics, and integrate everything into our final technical paper, due on the third of January. We contributed equally: Marco focused on the pair review and the semantic content analysis, Simone on toxicity, topics and conversations, and I on data collection, structural measures, invitations and coordination. The DM analysis and the final writing and review we do together. Our goal is to show not only what Telegram channels publish, but what researchers miss when they do not look at the associated discussion groups. Thank you, we welcome your questions and feedback.

---

## Possible questions (short answers)

- **Why pairs?** Each channel is the control for its own group: same community, same period.
- **What is new compared to prior work?** Channels and groups have been studied, also together (e.g. Slobozhan 2023, Alvisi 2026); we keep each channel and its own group as two levels of one community and compare them on several dimensions.
- **Is the toxicity model reliable?** Not validated by hand: a limitation we state; results are stable across thresholds 0.3 / 0.5 / 0.7.
- **Are the flagged invitations scams?** No: they match our operational definition (unknown platform or fixed-return wording); 96% sit in one referral group.
- **Did you interact with anyone?** No. Public chats only, no messages, no clicks on links.
- **DMs?** 23 on the crypto account and 17 on the conspiracy one so far, mostly bots plus a few openers; analysis after 1 December.

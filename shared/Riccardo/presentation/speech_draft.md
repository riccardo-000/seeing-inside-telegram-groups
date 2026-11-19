# Speech draft — "Seeing Inside Telegram Groups" (10 min)

Bozza in inglese, ~1,250 parole ≈ 10 min a ritmo normale. Gli stessi testi sono nelle note del
relatore di ogni slide. Speaker indicati come proposta (blocchi da ~3 min): cambiateli liberamente.
Se il tempo stringe: saltate la slide 8 (voices) e accorciate la 6.

---

## Block 1 — Setup (Riccardo, ~3 min)

**Slide 1 — Title (0:00–0:20)**
Hi everyone, we are Marco, Simone and Riccardo. Our project looks inside Telegram groups:
the discussion groups that are linked to public channels.

**Slide 2 — Channels broadcast; linked groups talk back (0:20–1:10)**
Telegram channels are one-way: only the admins post. Most measurement studies, including
TGDataset, which we started from, look only at channels. But many channels have a linked
discussion group, where anyone can write: admins, regular users, bots.
So our question is simple: what happens in the group that you cannot see from the channel?
We always compare a channel with its own group, so each channel acts as the control for its
group. And we did it in two communities, each with its own deep dive: in crypto we look at
invitations to register on platforms, a common scam vector; in conspiracy we look at toxicity.

**Slide 3 — Data (1:10–2:00)**
We selected about one hundred crypto and one hundred conspiracy channels that have a public
linked group: 195 pairs, 3.8 million messages, over fourteen weeks, from the end of July to
the beginning of November. Collection was strictly passive: we joined only public chats and
never sent a single message. Every message gets a role: the channel itself, admins writing in
the group, regular users, and bots, which we always keep apart.

**Slide 4 — Groups carry the volume (2:00–3:00)**
First, the structure. In the typical pair the group is far more active than its channel:
about ten times more messages per day in conspiracy, and about fifty times in crypto.
And it is a different kind of content: channel posts are polished, almost always with media,
and often with a link. Group messages are mostly short plain text.
These directions hold in every robustness check we ran: without truncated chats, without the
largest group, and with only true discussion groups. Now Marco on what the groups talk about.

## Block 2 — Content and crypto (Marco, ~3 min)

**Slide 5 — Three in four group messages match no channel post (3:00–4:15)**
To see whether groups just echo their channel, I embedded every group message with a
multilingual embedding model, Qwen3, and looked for the most similar post of its channel.
If the similarity is below a threshold that we calibrated by hand, 0.52, the message is not
aligned with anything the channel published.
About three in four group messages are not aligned: 75% in crypto and 76% in conspiracy, and
the difference between the two communities is not significant.
One caveat: this measures distance from the channel's posts, not that the topic was born in
the group.

**Slide 6 — What the unmatched messages do (4:15–5:00)**
What are these messages then? On a sample of six messages per pair we coded what they do.
Crypto groups are social: greetings, questions, asking for help. Conspiracy groups share news
and argue: news sharing is 22% of these messages, against 3% in crypto. Promotion is a small
share in both. These numbers are exploratory: a single coding pass, no second annotator.

**Slide 7 — Crypto: channels invite, suspicious invites cluster (5:00–5:50)**
For crypto, the deep dive is invitations to register on a platform: referral links, sign-up
links, deposit wording. The surprise is that it is the channel that invites: about 4% of its
posts, while group members almost never do. Suspicious invitations, to unknown platforms or
promising fixed returns, are rare and very concentrated: of 7,700 in groups, 7,400 are in one
single referral group. Token-alert bots post another 10,000 invitations, which we report
separately.

**Slide 8 — Who speaks (optional, 5:50–6:10)**
Splitting each pair into its three voices confirms it: the channel is where the links are,
almost 80% of crypto channel posts, while admins in the group post far fewer and crypto users
almost none. Now Simone on conspiracy.

## Block 3 — Conspiracy and wrap-up (Simone, ~3.5 min)

**Slide 9 — Conspiracy: groups are 4× as toxic (6:10–7:30)**
For conspiracy we classified about one million messages with Toxicity-Lens, a multilingual
model that scores seven categories, from insults to threats. In channels 2% of messages are
toxic; in groups 8.6%, about four times more. Pair by pair, the group is more toxic than its
channel in 82 of 96 pairs, with a median gap of 2.7 percentage points; insults and profanity
drive most of it. By voice: the channel is the cleanest, admins in the group are in between,
and regular users are the most toxic. The result holds if we change the threshold or drop the
largest group.

**Slide 10 — Toxicity attracts toxic replies (7:30–8:30)**
Groups are conversations, so we rebuilt who replies to whom from Telegram's reply links:
about 384 thousand reply pairs. A reply to a toxic message is toxic 21% of the time, against
8% for a reply to a non-toxic one, and the direction is the same in all 51 groups with enough
replies. This is an association, not causation: the topic, recurring users and moderation can
all play a role.

**Slide 11 — What groups add (8:30–10:00)**
To sum up, looking inside the groups adds three things.
Volume and new topics: groups are ten to fifty times more active, and mostly talk about things
the channel never posted.
Promotion stays upstream: in crypto, invitations to register come from the channel, and
suspicious ones cluster in a handful of groups.
And the tone gets rougher: conspiracy groups are four times as toxic as their channels, users
more than admins, and toxic messages attract toxic replies.
Our limits: the classifiers are not validated by hand, and community topics were labelled with
an LLM. Next, we analyse the unsolicited DMs our passive accounts received, and write the
paper. Thank you — happy to take questions.

---

## Possible questions (short answers)

- **Why pairs?** Each channel is the control for its own group: same community, same period.
- **Is the toxicity model reliable?** Not validated by hand yet: we report it as a limitation;
  results are stable across thresholds 0.3 / 0.5 / 0.7.
- **Did you interact with anyone?** No. Public chats only, no messages, no clicks on links.
- **Why is the channel the main inviter in crypto?** Channels of projects and exchanges push
  their own referral and sign-up links; in groups, users rarely do it except in referral groups.
- **DMs?** 23 on the crypto account and 17 on the conspiracy one so far, mostly bots plus a few
  "hello" and coin-pitch openers; analysis after 1 December.

# Paper Writing Plan — Seeing Inside Telegram Groups

## 1. Why we should start writing now

This is the right moment to start writing the paper, even though the dataset is still being constructed.

The professor's guidelines explicitly suggest that writing should accompany the research process rather than come only at the end. The paper should be built around a clear central idea, explicit contributions, and evidence supporting those contributions.

The main principle is:

> **Problem → Idea → Evidence → Comparison with previous work**

We should therefore avoid waiting until all experiments are finished before starting to structure the paper.

---

## 2. Current state of the project

At the moment, the real workflow is:

```text
TGDataset
    ↓
Selection of candidate crypto channels
    ↓
Telegram API verification
    ↓
Channels still active and accessible
    ↓
Manual inspection of each active channel
    ↓
Search for Telegram group links inside the channel
    ↓
Manual validation of the group
    ↓
Store the channel–group relation in:
data/interim/pairs/active_channels.csv
```

Riccardo is currently working on the automatic part:

- reading channels from TGDataset;
- querying the Telegram API;
- verifying whether those channels still exist and are active.

Marco and Simone are currently working on the manual validation step:

- inspecting active channels;
- looking for links to Telegram groups;
- validating the discovered groups;
- recording the results in `data/interim/pairs/active_channels.csv`.

For now, the pilot domain is **Crypto**.

---

## 3. First methodological point to clarify

We need to define precisely what we mean by an **associated group**.

At the moment, we are not necessarily studying only Telegram's officially linked discussion groups.

We are manually looking for **public Telegram groups explicitly linked or promoted inside a channel**.

This distinction matters.

A possible working definition is:

> A group is considered associated with a channel when the channel explicitly exposes a Telegram link pointing to that group and the group is publicly accessible at collection time.

This definition is only preliminary, but something of this kind must be fixed before the dataset grows significantly.

---

## 4. What the paper should actually be about

The paper should **not** mainly describe the collector.

The collector is the mechanism that allows us to generate the evidence needed for the scientific contribution.

The central narrative should instead be:

```text
Telegram channels mainly expose administrator-generated broadcast content
                        ↓
Suspicious communities may also direct users toward public groups
                        ↓
Those groups expose interactions among ordinary users
                        ↓
Channel-only observation may therefore hide part of the community
                        ↓
We build paired channel–group observations
                        ↓
We quantify what additional information becomes observable in the group layer
```

So the paper should not become:

> "We built a Telegram scraper."

Nor:

> "We collected some Telegram groups."

The scientific idea should be closer to:

> **We investigate what additional information about suspicious communities becomes observable when moving from their broadcast channel layer to their associated public group layer.**

---

## 5. Proposed paper structure

A good initial structure would be:

| Section | Purpose |
|---|---|
| **Abstract** | Written last. Problem → relevance → approach → main result |
| **1. Introduction** | Telegram context, channel/group distinction, research gap, RQ, contributions |
| **2. Problem** | Explain why channel-only analysis may miss the social layer |
| **3. Approach** | Explain the paired channel–group idea |
| **4. Data Collection and Methodology** | TGDataset seeds, verification, group discovery, filtering |
| **5. Analysis / Experiments** | Metrics and methods for comparing channels and groups |
| **6. Results** | Quantitative answers to the research questions |
| **7. Related Work** | TGDataset, Telegram groups, suspicious communities, cybercrime/conspiracy literature |
| **8. Ethics and Limitations** | Public data, users, pseudonymisation, selection bias, dataset limitations |
| **9. Conclusion and Future Work** | Problem, findings, contributions, limitations, possible extensions |

The paper should not necessarily be written in this order.

The first parts we can already work on are:

- Problem
- Approach
- Data Collection
- Methodology
- preliminary Introduction structure

The Abstract should be written only near the end.

---

## 6. What we can already write now

Even before completing the collection, several parts are already sufficiently defined.

### 6.1 Background

We can already explain the structural distinction:

- **Channels:** one-to-many communication, mainly admin-generated content.
- **Groups:** many-to-many communication, users can interact with one another.

This distinction is fundamental because our project focuses exactly on the information that becomes visible when moving from the broadcast layer to the social layer.

### 6.2 The problem

TGDataset focuses on Telegram channels.

Our work starts from those channels, but asks a different question:

> What is missing when researchers observe only the channel?

The hypothesis is that groups may reveal:

- users;
- discussions;
- requests;
- complaints;
- offers;
- coordination;
- user-to-user interaction;
- responses to admin posts;
- topics not present in the broadcast content;
- differences between admin discourse and community discourse.

### 6.3 Data acquisition methodology

We can already describe:

- TGDataset as seed source;
- selection of candidate crypto channels;
- verification of current channel availability via Telegram API;
- manual inspection;
- group-link discovery;
- manual validation;
- storage of the discovered channel–group relation.

### 6.4 Limitations

Some limitations are already known:

- TGDataset represents an older snapshot of Telegram;
- many channels may have disappeared or become inactive;
- our discovery method depends on explicit links;
- manual inspection may introduce human errors;
- not every suspicious channel necessarily exposes a public group;
- public groups may disappear or change over time.

These limitations should be tracked now, not invented at the end.

---

## 7. Separate dataset construction from scientific analysis

This distinction is fundamental.

Suppose we eventually obtain:

```text
300 candidate crypto channels
180 still active
70 exposing a Telegram group
55 valid public groups
```

These numbers are useful, but they are mainly **dataset-construction results**.

They are not yet the scientific answer.

The real research starts once we have pairs such as:

```text
channel_i ↔ group_i
```

Then we ask:

> What can we learn from `group_i` that would not be observable from `channel_i` alone?

This is the central analytical step.

---

## 8. Design the experiments before seeing the final results

The experiments should directly support claims that may later appear in the Introduction.

A useful internal structure is:

| Potential claim | Required evidence |
|---|---|
| Groups expose more participants | Number and activity of observable users |
| Groups expose different content | Topic/content divergence |
| Groups expose interaction behaviour | Replies, discussions, conversation structure |
| Groups contain information absent from channels | Content novelty |
| Admin discourse differs from user discourse | Semantic/topic comparison |
| Groups react to channel posts | Thread/comment analysis |
| Groups reveal temporal dynamics | Response time, conversation duration, activity bursts |

We should **not automatically use all of these metrics**.

The goal should be to choose a small number of strong measurements that directly answer the research question.

---

## 9. Treat `active_channels.csv` as part of dataset provenance

The file:

```text
data/interim/pairs/active_channels.csv
```

should not be treated only as an operational spreadsheet.

It is part of the dataset provenance.

Ideally, for each candidate we should be able to reconstruct:

```text
channel
    ↓
how it was discovered
    ↓
when it was checked
    ↓
active / inactive
    ↓
whether a group was found
    ↓
where the link was found
    ↓
group identifier
    ↓
public / private
    ↓
when the group was validated
```

This would allow the methodology section to make precise statements such as:

> We manually validated every automatically discovered candidate and retained only currently accessible public channel–group associations.

That is much stronger and more reproducible than saying:

> We manually looked for groups.

---

## 10. Turn manual validation into a protocol

Marco and Simone's current manual workflow should become a reproducible protocol.

Before scaling the collection, we should define:

- what counts as a valid Telegram group link;
- where links are searched:
  - channel description;
  - pinned messages;
  - ordinary posts;
  - forwarded messages;
  - other locations;
- whether multiple groups per channel are allowed;
- how duplicates are handled;
- how inactive groups are handled;
- how private groups are handled;
- how expired invite links are handled;
- how redirected usernames are handled;
- how bots are treated;
- how links to other channels are distinguished from group links.

This internal protocol can later become part of the Methodology section.

---

## 11. Crypto should initially be treated as a pilot domain

For now:

```text
Crypto
    ↓
Build paired corpus
    ↓
Test methodology
    ↓
Run preliminary experiments
```

This is preferable to immediately expanding to multiple categories.

The Crypto pilot should reveal whether:

- enough channel–group pairs exist;
- the data is accessible;
- the chosen metrics are meaningful;
- the collection procedure works;
- the comparison actually produces interesting results.

Only after this pilot should we decide whether to extend the study to **Conspiracy**.

If a second domain is added later, it can help determine whether the observed behaviour is:

- specific to Crypto;
- or more general across suspicious Telegram communities.

---

## 12. Suggested division of work

### Riccardo

Main focus:

- automatic candidate extraction from TGDataset;
- Telegram API validation;
- channel activity/existence checks;
- documentation of the automatic pipeline.

### Marco and Simone

Main focus:

- manual inspection of active channels;
- discovery of group links;
- validation of candidate groups;
- documentation of the manual validation protocol.

### Marco

Additional scientific coordination:

- research questions;
- paper outline;
- literature review;
- evidence matrix;
- methodology design;
- connection between claims and experiments;
- overall scope control.

The division should remain flexible. Everyone should understand the full project and eventually review the entire paper.

---

## 13. Recommended workflow from now on

The next steps should be:

1. **Freeze a preliminary main research question.**
2. **Define precisely what an associated group is.**
3. **Review the structure of `active_channels.csv`.**
4. **Formalize the manual group-discovery protocol.**
5. **Create the complete paper skeleton.**
6. **Start writing Problem, Approach, and Data Collection.**
7. **Build a Related Work matrix.**
8. **Define the measurements used to quantify group-level information gain.**
9. **Run a pilot analysis on Crypto.**
10. **Evaluate whether Conspiracy should be added as a second domain.**
11. **Refine the RQ based on the pilot results.**
12. **Only then move toward the final experiments and results section.**

---

## 14. Core scientific direction

A good current formulation of the project is:

> **We investigate the information gap between Telegram broadcast channels and associated public groups, measuring what additional content, interactions, and community behaviours become observable when moving from the broadcast layer to the social layer of suspicious communities.**

The collector, the dataset construction, and the manual validation pipeline exist to support this research question.

The paper should therefore always remain focused on:

```text
research question
        +
paired channel–group dataset
        +
reproducible methodology
        +
quantitative evidence
        =
scientific contribution
```

---

## 15. Immediate next step

The next concrete task should be:

> **Define the preliminary research question, formalize the meaning of "associated group", and inspect `data/interim/pairs/active_channels.csv` to verify whether the current dataset records enough information to support a reproducible methodology.**

This should be completed before substantially scaling the collection.

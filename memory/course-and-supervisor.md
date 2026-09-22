# Course constraints and supervisor guidance

Summary of `docs/prof-material/` (read 2026-09-22). Check the originals before quoting.

## Course 02234 (Nicola Dragoni, DTU) — hard constraints

- **Deadline:** submit the paper on DTU Learn before **midnight CET, 3 January 2027**.
- **Type:** technical paper (problem → our contribution → evidence → related work).
- **Template:** Springer **LNCS** (Overleaf template available). **Max 16 pages excluding
  references.** "USE THE TEMPLATE."
- **Individual evaluation:** the paper must **state clearly who did what**.
- **Student workshop:** present type of project, problem, status, plan, and who does what.
  Not graded on its own, but skipping it fails a learning objective.
- Group must be registered on DTU Learn. Emails need `[02234]` in the subject.
- Top reports may be invited for publication under the lecturer's supervision.
- DTU rules on cheating / AI chatbots apply (see L1 slides 26–27).

## Project 3 brief (Alberto Maria Mongardini, among@dtu.dk — lecture slide 114)

- Gap: TGDataset covers channels, where only admins speak; groups are where members talk.
- **Start from TGDataset:** its channels advertise thousands of **public group invite links**
  (focus on malicious ones) — i.e. groups are found both as linked discussion groups
  and via invite links posted in channel messages.
- Collect passively with accounts that join public groups reachable by a public link:
  **never posting, never replying, never asking.**
- Question: what does a group reveal that its channel does not? How do users interact in
  groups about carding, calls to violence, etc.?
- **"Store no personal data."** "A probe that asks a question or accepts an offer has become
  a participant" → out of scope for a term project.
- Related Project 1 wording (doxxing): "Redact personal data at ingestion, report only in
  aggregate, never contact a target or an operator."

## Supervisor's recipe (slides 116–117)

1. Get the whole population, not a sample.
2. **Define the abuse before you look for it** — definitions first, code second.
3. Screen cheaply, then confirm expensively.
4. **Validate by hand and publish the error rate** (multiple annotators, false positives;
   conservative thresholds → findings are lower bounds, say so).
5. Convert counts into harm; release data and notebooks.

Turning it into a paper:
- Start from released data (Zenodo/GitHub).
- **Name the centerpiece figure/table in week one.**
- One question, answered properly.
- Choose thresholds and defend them.
- **Write the ethics section deliberately:** what data, what we did not collect, rate limits,
  dual-use risk, why disclosure still wins.
- Release artifacts.

## Useful facts from the TGDataset paper

- 120,979 channels, 498M messages, collected Jan 2021 – **Jul 2022** (expect many dead channels).
- 121 JSON files (~71 GB compressed, 4 parts) on Zenodo; sample + scripts on
  GitHub `SystemsLab-Sapienza/TGDataset`; released CSVs: language labels, topic mapping,
  conspiracy channel list, Sabmyk list.
- Telethon, 5 s between calls; no media downloaded.
- Channel fields include Telegram's `scam` and `verified` flags (183 scam channels).
- §8 Limitations: no user comments/replies collected → exactly the gap our project fills.
- §7 Ethics relies on GDPR Art. 85 + minimization **limited to admin posts**; our work
  processes member messages, so we cannot just copy that argument.
- Related work to follow up: Pushshift Telegram (Baumgartner '20, includes groups),
  pump-and-dump (La Morgia '20/'21, Xu & Livshits USENIX Sec '19), Conspiracy Money Machine
  (Imperati et al. USENIX Sec '25), fake/clone channels (La Morgia et al. ICWS '23, TWEB '24),
  carding forums (Kigerl '20).

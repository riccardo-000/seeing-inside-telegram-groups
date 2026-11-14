# Semantic non-alignment and thematic characterization of Telegram discussion groups

*Manuscript-ready Point 4 section — quantitative analysis and exploratory content characterization*

## Methods

### Channel–group matching and semantic non-alignment

We examined 195 linked Telegram channel–discussion-group pairs, comprising 98 cryptocurrency-related (*crypto*) and 97 conspiracy-related (*conspiracy*) pairs. For each pair, the existing collection pipeline sampled up to 5,000 group messages after applying its service-message, automated-message, and other eligibility rules. The observed channel corpus was used as the reference set. Across pairs, the data comprised 134,984 channel posts and 513,973 sampled group messages. Of the latter, 40,411 contained fewer than five characters and were not embedded. We embedded the remaining 473,562 messages using `OpenVINO/Qwen3-Embedding-0.6B-int8-ov`, with a retrieval-oriented instruction for group-message queries, document-style channel-post embeddings, and L2-normalized vectors.

Let \(G_i\) be the eligible group messages and \(C_i\) the observed channel posts for pair \(i\). For each group message \(g\), we calculated its highest cosine similarity to any available post from the linked channel:

\[
 s(g,C_i) = \max_{c\in C_i} \cos\!\left(E_q(g),E_d(c)\right).
\]

We defined **semantic non-alignment** (hereafter *group-only* in the operational sense) as \(s(g,C_i)<0.52\). This threshold was fixed prior to the full analysis following a separate, balanced 100-item calibration exercise; 0.50 and 0.55 were retained as sensitivity thresholds. After embedding, messages with no Unicode letter remaining upon removal of URLs and mentions (including URL-only and other non-lexical content) were excluded from the primary denominator. This yielded 445,584 semantically eligible messages: 226,100 crypto and 219,484 conspiracy. The primary estimator was the unweighted mean of the within-pair non-alignment proportions, giving all channel–group pairs equal influence. We additionally examined frequency-weighting alternatives and restrictions by channel-corpus size. Uncertainty was evaluated at the pair level, rather than treating messages from the same discussion group as independent observations.

### Exploratory characterization of non-aligned content

For the thematic component, we first explored deduplicated non-aligned texts (284,068 unique texts *within pairs*) using embedding-based clustering. The clustering pilots served to identify candidate subjects and communicative functions, not to estimate their frequencies: unsupervised cluster labels were not assumed to correspond one-to-one to coherent topics. We then developed a two-axis coding scheme distinguishing **communicative function** (e.g., greeting, question, discussion, information sharing, promotion) from **primary subject** (e.g., finance, health, politics, religion, technology), with separate indicators for interpretability and promotion.

To characterize the actual non-aligned message traffic, rather than the distinct-text clustering corpus, we drew six messages without replacement from each of the 195 pairs, producing 1,170 messages (588 crypto; 582 conspiracy). Repeated texts were retained because the target was message traffic. Messages were assigned labels using a reproducible, text-only, rule-guided coding procedure with targeted case review and an explicit `Unclear` category. The primary descriptive summaries average within-pair proportions; 95% intervals use 5,000 pair/within-pair bootstrap draws. **This thematic coding is exploratory and lacks independent reference-label validation.** Its intervals quantify sampling variation *conditional on the assigned labels*, not the error of the coding procedure.

## Results

### High semantic non-alignment in both categories

Of the 445,584 semantically eligible group messages, 334,080 fell below the predefined similarity threshold. The equal-pair-weighted mean non-alignment rate was **74.68%** among the 98 crypto pairs (95% pair-bootstrap CI 71.68–77.57%) and **76.11%** among the 97 conspiracy pairs (71.48–80.50%). The estimated difference was **+1.43 percentage points** (conspiracy minus crypto; bootstrap 95% CI −3.95 to +6.74 points; Welch test \(p=0.606\)). We therefore do not find convincing evidence of a difference between the **mean pair-level rates**; this must not be read as evidence of equivalence. The corresponding message-pooled proportions were 74.93% and 75.03%, but these give greater influence to high-traffic pairs and are not the primary estimand (Table 1; Figure 1).

**Table 1.** Semantic non-alignment at threshold 0.52, with channel–group pairs as the primary analytical units.

| Measure | Crypto | Conspiracy |
|---|---:|---:|
| Channel–group pairs | 98 | 97 |
| Semantically eligible group messages | 226,100 | 219,484 |
| Operationally group-only messages | 169,406 | 164,674 |
| Mean pair-level non-alignment rate | **74.68%** | **76.11%** |
| 95% bootstrap CI for mean | 71.68–77.57% | 71.48–80.50% |
| Median pair-level rate | 77.16% | 84.28% |
| Between-pair SD | 14.84 pp | 22.91 pp |
| Pooled message-level rate | 74.93% | 75.03% |

![Figure 1. Distribution of the observed per-pair semantic non-alignment rates. Each point represents one channel–group pair; diamonds indicate the pair-equal category means.](figures/figure_1_pairwise_rates.png)

There was appreciable heterogeneity between channel–group pairs, particularly within the conspiracy category (standard deviation 22.91 versus 14.84 percentage points; exploratory Brown–Forsythe \(p=0.0058\)). Median rates were 84.28% and 77.16%, respectively. Such distributional contrasts are secondary findings and were not multiplicity-adjusted; they should not be substituted for the preregistered-style primary comparison of mean rates.

### The size of the channel reference corpus matters

The reference channels differed in size: the median number of distinct channel posts was 83 for crypto and 237 for conspiracy. Larger reference corpora were associated with lower measured non-alignment (Spearman \(\rho=-0.420\) for crypto and \(\rho=-0.827\) for conspiracy; both \(p<0.001\); Figure 2). This relationship has a **mechanical component**: when the score is a maximum over candidate posts, adding a candidate cannot reduce the maximum for a fixed query. Corpus size, content and observation period therefore complicate category comparisons. Exploratory channel-size strata showed distinct patterns, including reversals at the highest sizes; there is no defensible single, context-free size-adjusted category effect.

![Figure 2. Association between distinct channel-post count and the measured fraction of semantically non-aligned group messages. The maximum-over-candidates similarity measure is sensitive to reference-corpus size.](figures/figure_2_channel_corpus_size.png)

The result was also sensitive to the operational similarity threshold. At thresholds of 0.50, 0.52 and 0.55, the equal-pair mean non-alignment rates were 69.42%, 74.68% and 80.56% in crypto, and 69.94%, 76.11% and 83.37% in conspiracy (Figure 3). The difference in means remained comparatively small across these thresholds. Counting each distinct normalized text once per pair, or capping its frequency at five, changed the overall pair means little, although individual communities sometimes changed substantially.

![Figure 3. Sensitivity of pair-equal mean semantic non-alignment rates to the similarity threshold. The primary threshold was 0.52.](figures/figure_3_threshold_sensitivity.png)

### Distinct communicative functions are visible among non-aligned messages

The exploratory coding of 1,170 group-only messages suggested a contrast in communicative function (Table 2; Figure 4). The label *Greeting/social interaction* accounted for 20.9% of crypto messages versus 4.3% of conspiracy messages (difference −16.6 pp, 95% bootstrap interval −22.4 to −11.0 pp). *Information/news sharing* accounted for 2.6% versus 22.3%, respectively (difference +19.8 pp, 95% interval +14.1 to +26.0 pp). The *Substantive discussion/opinion* label occurred in 25.9% and 32.0%; its difference was less clearly distinguished from zero (95% interval −1.6 to +14.0 pp). These intervals are conditional on assigned codes and do not constitute evidence of labeling accuracy.

**Table 2.** Exploratory communicative-function labels within the stratified sample of group-only messages (six messages per pair; pair-equal percentages). Differences are conspiracy minus crypto.

| Assigned communicative function | Crypto | Conspiracy | Difference (pp), 95% interval |
|---|---:|---:|---:|
| Greeting/social interaction | 20.9% | 4.3% | −16.6 [−22.4, −11.0] |
| Question or help request | 15.0% | 14.8% | −0.2 [−5.8, +5.8] |
| Substantive discussion/opinion | 25.9% | 32.0% | +6.1 [−1.6, +14.0] |
| Information/news sharing | 2.6% | 22.3% | +19.8 [+14.1, +26.0] |
| Promotion/solicitation | 5.3% | 9.1% | +3.8 [−1.3, +9.3] |
| Moderation/security | 1.7% | 0.7% | −1.0 [−2.9, +0.7] |
| Other/unclear | 28.7% | 16.8% | −11.9 [−19.6, −4.4] |

![Figure 4. Pair-equal proportions of assigned communicative-function labels among sampled non-aligned messages. These are exploratory, unvalidated category assignments.](figures/figure_4_communicative_functions.png)

In subject coding, `No clear theme` was assigned to 60.2% of crypto and 34.9% of conspiracy messages, while `Unclear` accounted for 16.8% and 12.9%. Among messages with identifiable subject cues, the conspiracy sample included politics/government, health/medicine, religion/spirituality and war/geopolitics; the crypto sample included trading and financial markets, rewards, account operations and technical support. These subject labels are suitable for **illustrating the breadth of conversation types**, not as independently verified estimates of thematic prevalence. In particular, a legible greeting with no explicit subject should not be conflated with a message whose meaning is uncertain.

Message length is an important competing explanation for the functional contrasts: in the stratified sample, median message length was 26 characters in crypto compared with 92.5 in conspiracy; 66.3% versus 29.4% were shorter than 40 characters. Among messages at least 40 characters long, information/news sharing was assigned to 7.1% of crypto messages and 31.4% of conspiracy messages (message-level, unadjusted within-stratum descriptives). The difference therefore does not disappear in this length stratum, but stratification alone cannot eliminate language, context or coding differences.

## Discussion and threats to validity

The main finding is that a substantial majority of assessable text traffic in these linked discussion groups lacks a sufficiently close semantic counterpart in the **observed** associated channel corpus, under the chosen retrieval model and threshold. This indicates topical divergence as operationalized by the matching procedure, not independently originated conversations. Some non-aligned messages are social interactions, questions, support requests or promotions rather than wholly novel topics, and messages assigned the same topic may still differ substantially in intent and context.

Four limitations are central. **First**, the matching reference includes available channel posts without enforcing that each post precede the group message; temporal precedence and causal origin cannot be inferred. **Second**, maximum-cosine retrieval scores depend on reference-corpus size and on model/threshold performance; the two categories have unequal channel sizes. **Third**, the group-message collections are capped observational samples, with service and non-lexical exclusions and possible duplication/spam effects. **Fourth**, thematic labels were produced in a single reproducible coding pass without independent ground-truth evaluation; short texts, multilingual content and context-poor replies increase uncertainty. Bootstrap intervals describe sampling variability, not classification error or the representativeness of Telegram overall.

Consequently, the strongest contribution is the quantitative characterization of **semantic non-alignment with observed channel posts** across 195 linked communities, supported by threshold and duplicate-policy sensitivity checks. The thematic analysis offers preliminary descriptive context for the messages that are not matched, but does not establish robust theme-prevalence rankings or a causal mechanism for the emergence of independent discussions.

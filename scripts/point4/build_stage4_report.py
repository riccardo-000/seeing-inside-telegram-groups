from pathlib import Path
import pandas as pd, numpy as np
import matplotlib.pyplot as plt
from scipy.stats import spearmanr
import json

ROOT=Path('/mnt/data/point4_stage4_complete')
DATA=ROOT/'stage4_labeled.csv'
KEY=Path('/mnt/data/point4_stage4_ready/sample/stage4_sampling_key.csv')
EST=ROOT/'results/stage4_exploratory_estimates.csv'
D=pd.read_csv(DATA,encoding='utf-8-sig',keep_default_na=False)
K=pd.read_csv(KEY,encoding='utf-8-sig')
S=pd.read_csv(EST)
M=D.merge(K,on='ITEM_ID',validate='one_to_one')
M['length_chars']=M.GROUP_MESSAGE.astype(str).str.len()
M['length_ge40']=M.length_chars>=40
M['topic_resolved']=~M.THEME_LABEL.isin(['No clear theme','Unclear'])
M['repeated_within_sample']=M.duplicated(['pair_id','GROUP_MESSAGE'],keep=False)
assert len(M)==1170 and M.pair_id.nunique()==195
assert (M.groupby('pair_id').size()==6).all()
assert int(M.groupby('pair_id').n_population_in_pair.first().sum())==334080
# minimal reproducible diagnostics about length, ambiguity and sample composition
qc=[]
for t,v in M.groupby('topic'):
    qc.append({'topic':t,'n_pairs':v.pair_id.nunique(),'n_messages':len(v),'median_length':v.length_chars.median(),
      'share_under40':float((v.length_chars<40).mean()),'share_no_clear_theme':float((v.THEME_LABEL=='No clear theme').mean()),
      'share_unclear_theme':float((v.THEME_LABEL=='Unclear').mean()),
      'share_interpretable_yes':float((v.INTERPRETABLE=='YES').mean()),
      'share_reviewed':float((v.CODING_CONFIDENCE=='reviewed').mean()),
      'share_low_coding_confidence':float((v.CODING_CONFIDENCE=='low').mean()),
      'share_sample_repeated_within_pair':float(v.repeated_within_sample.mean())})
qc_df=pd.DataFrame(qc)
qc_df.to_csv(ROOT/'results/stage4_quality_diagnostics.csv',encoding='utf-8-sig',index=False)
# conditional breakdown by length, not a replacement for full-sample estimate
ls=[]
for (t,long),v in M.groupby(['topic','length_ge40']):
 for field in ['FUNCTION_LABEL','THEME_LABEL','PROMOTIONAL']:
  for lab,count in v[field].value_counts().items():
   ls.append({'topic':t,'length_ge40':long,'field':field,'category':lab,'n':count,'denominator':len(v),'share':count/len(v)})
pd.DataFrame(ls).to_csv(ROOT/'results/stage4_length_strata.csv',encoding='utf-8-sig',index=False)
# robustness: variation of per-pair category proportions with length; exploratory descriptive only
pair=M.groupby(['topic','pair_id']).agg(mean_len=('length_chars','mean'),short_share=('length_ge40',lambda x:float((~x).mean())),no_clear_rate=('THEME_LABEL',lambda x:float((x=='No clear theme').mean())),social_rate=('FUNCTION_LABEL',lambda x:float((x=='Greeting/social interaction').mean()))).reset_index()
pair.to_csv(ROOT/'results/stage4_pair_length_diagnostics.csv',encoding='utf-8-sig',index=False)
figdir=ROOT/'figures';figdir.mkdir(exist_ok=True)
# Utility for showing raw proportions with category names abbreviated for length
def comp(field,labels,filename,title):
 x=S[(S.field==field)&(S.topic.isin(['crypto','conspiracy']))].pivot(index='category',columns='topic',values='pair_equal_rate').reindex(labels).fillna(0)
 ax=x[['crypto','conspiracy']].plot(kind='barh',figsize=(10, max(4,0.37*len(labels)+1)),width=.68)
 ax.set_title(title);ax.set_xlabel('Pair-equal share of assigned labels (%)')
 ax.set_xlim(0,max(0.05,x.to_numpy().max()*1.20))
 import matplotlib.ticker as mtick
 ax.xaxis.set_major_formatter(mtick.PercentFormatter(xmax=1.0,decimals=0))
 ax.invert_yaxis();ax.legend(title='Category');plt.tight_layout();plt.savefig(figdir/filename,dpi=180);plt.close()
fun_order=['Greeting/social interaction','Question or help request','Substantive discussion/opinion','Information/news sharing','Promotion/solicitation','Moderation/security','Other/unclear']
comp('function',fun_order,'01_function_comparison.png','Communicative functions in sampled group-only messages')
theme_order=['No clear theme','Unclear','Politics/government','Health/medicine','Religion/spirituality','Work/commerce/services','Crypto/markets','History/conspiracy claims','War/geopolitics','Platform/community operations','Technology/software/privacy','Scams/security','Media/arts/gaming','Platform/rewards']
comp('theme',theme_order,'02_theme_comparison.png','Primary themes (exploratory text coding)')
# CI difference for selected categories
x=S[(S.topic=='difference_conspiracy_minus_crypto') & (((S.field=='function')&S.category.isin(fun_order))|((S.field=='theme')&S.category.isin(['No clear theme','Unclear','Politics/government','Health/medicine','War/geopolitics','Crypto/markets'])))]
x=x.sort_values('pair_equal_rate')
fig,ax=plt.subplots(figsize=(10,7.5)); ys=np.arange(len(x)); means=x.pair_equal_rate.to_numpy()*100
lower=(x.pair_equal_rate-x.bootstrap_low_95).to_numpy()*100;upper=(x.bootstrap_high_95-x.pair_equal_rate).to_numpy()*100
ax.errorbar(means,ys,xerr=[lower,upper],fmt='o',capsize=3)
ax.axvline(0,ls='--',lw=1,color='gray');ax.set_yticks(ys);ax.set_yticklabels([f"{f}: {lab}" for f,lab in zip(x.field,x.category)]);ax.set_xlabel('Conspiracy − Crypto (percentage points), 95% pair bootstrap CI');ax.set_title('Exploratory differences in assigned labels');plt.tight_layout();fig.savefig(figdir/'03_difference_intervals.png',dpi=180);plt.close(fig)
# make small aggregate flat table
small=S[(S.topic.isin(['crypto','conspiracy'])) & (S.field.isin(['function','theme']))].copy()
small['percentage']=100*small['pair_equal_rate'];small['lo_pct']=100*small['bootstrap_low_95'];small['hi_pct']=100*small['bootstrap_high_95']
small[['field','category','topic','n_pairs','percentage','lo_pct','hi_pct']].to_csv(ROOT/'results/stage4_publication_table.csv',index=False,encoding='utf-8-sig')
# report summaries
report=[]
report.append('# Point 4 — Stage 4: Exploratory characterization of group-only messages\n')
report.append('## Scope and coding provenance\n')
report.append('This analysis describes 1,170 sampled Telegram group messages, six randomly selected from each of 195 channel–group pairs (98 crypto, 97 conspiracy), drawn from 334,080 semantically eligible **group-only message instances** in the previously sampled observation window. The primary estimand is the mean within-pair proportion, with each pair weighted equally. Text duplicates remain in the message-level target.\n')
report.append('Messages were coded with a **text-only, rule-guided single-pass exploratory procedure and targeted review** under taxonomy v3. There is **no independent human validation**, adjudicated inter-annotator agreement, or measured classification accuracy. Confidence intervals below quantify sampling uncertainty **conditional on assigned labels**, not annotation error. Unclear subjects remain explicitly unclassified. These are preliminary descriptive estimates, not validated population prevalence.\n')
report.append('## Communicative-function composition\n')
fun=S[(S.field=='function')&S.topic.isin(['crypto','conspiracy'])].pivot(index='category',columns='topic',values='pair_equal_rate').reindex(fun_order)
report.append('| Function | Crypto (%) | Conspiracy (%) | Difference, Conspiracy−Crypto (pp) | 95% bootstrap interval (pp) |\n|---|---:|---:|---:|---:|')
for lab in fun_order:
 d=S[(S.field=='function')&(S.category==lab)&(S.topic=='difference_conspiracy_minus_crypto')].iloc[0]
 report.append(f'| {lab} | {fun.loc[lab,"crypto"]*100:.1f} | {fun.loc[lab,"conspiracy"]*100:.1f} | {d.pair_equal_rate*100:+.1f} | [{d.bootstrap_low_95*100:+.1f}, {d.bootstrap_high_95*100:+.1f}] |')
report.append('\nIn this exploratory coding, non-specific greetings/reactions are more frequent in crypto, while information/news sharing is more frequent in conspiracy. Interpretation is sensitive to how short messages and heterogeneous languages are categorized.\n')
report.append('## Main identified subject themes\n')
report.append('| Subject | Crypto (%) | Conspiracy (%) |\n|---|---:|---:|')
theme=S[(S.field=='theme')&S.topic.isin(['crypto','conspiracy'])].pivot(index='category',columns='topic',values='pair_equal_rate').reindex(theme_order)
for lab in theme_order:
 report.append(f'| {lab} | {theme.loc[lab,"crypto"]*100:.1f} | {theme.loc[lab,"conspiracy"]*100:.1f} |')
report.append('\nThe largest themes by share are *No clear theme* and *Unclear*, which are not equivalent: a legible short reply may have no developed subject, whereas an opaque or linguistically unassessable message is uncertain. No inference about the absence of substantive discussion can be drawn from these labels alone.\n')
report.append('## Quality and sensitivity diagnostics\n')
report.append('| Group | Median characters | Under 40 chars | No clear theme | Unclear theme | Low-confidence codes |\n|---|---:|---:|---:|---:|---:|')
for _,q in qc_df.iterrows():
 report.append(f'| {q.topic.title()} | {q.median_length:.0f} | {q.share_under40*100:.1f}% | {q.share_no_clear_theme*100:.1f}% | {q.share_unclear_theme*100:.1f}% | {q.share_low_coding_confidence*100:.1f}% |')
report.append('\nAny apparent category difference may be confounded by text length, language distribution, platform-specific jargon, and the conservative abstention rules. Examine `stage4_length_strata.csv` before placing confidence in any category-specific estimate.\n')
report.append('## Conclusions defensible at this stage\n')
report.append('1. The completed quantitative group-only analysis remains the main validated numerical finding: 74.68% crypto vs 76.11% conspiracy pair-mean rates after message filtering, with strong channel corpus size effects.\n')
report.append('2. This Stage 4 coding provides a **descriptive map of types of content**, not a verified semantic classifier. Its most useful pattern is the contrast between everyday interaction and news/opinion-style messages, subject to language and length differences.\n')
report.append('3. A smaller set of explicitly identifiable topic examples is present (health, politics, geopolitics, spiritual claims, markets, platform support), but their recorded fractions should not be treated as independently validated prevalence.\n')
report.append('4. Before the paper claims prevalence of specific themes, obtain an independently judged reference sample or narrow claims to the documented qualitative examples. An agreement statistic cannot be supplied without multiple independent judgments.\n')
report.append('## Reproducibility\n')
report.append('- `stage4_labeled.csv`: every message and its four required taxonomy labels, plus audit notes and confidence tier.\n- `stage4_exploratory_estimates.csv`: estimates and 95% pair/within-pair bootstrap intervals (5,000 repetitions; script seed 20261113).\n- `stage4_pair_label_rates.csv`: 195 pair-level category rates.\n- `stage4_length_strata.csv`: descriptive length sensitivity.\n- `stage4_quality_diagnostics.csv`: data-quality and coding diagnostics.\n- `stage4_sampling_key.csv`: unchanged sampling key (kept separate until coding).\n- `figures/`: charts for reporting.\n')
(ROOT/'REPORT_STAGE4.md').write_text('\n'.join(report)+'\n',encoding='utf-8')
print(qc_df.to_string(index=False));print('report, figures, diagnostics created')

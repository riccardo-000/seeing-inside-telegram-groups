"""Reproducible descriptive/statistical analysis of Point 4 pair-level outputs.

Run from a directory with the five CSVs:
    python point4_statistical_analysis.py --data-dir . --out-dir point4_results

Or provide any other directory with pair_policy_summary.csv, pair_results.csv,
pooled_summary.csv, topic_summary.csv, topic_policy_summary.csv.
No embedding/model work. All inferential tests treat channel–group pairs as units.
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.formula.api as smf
from statsmodels.nonparametric.smoothers_lowess import lowess
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

SEED = 2026
N_BOOT = 30000


def bootstrap_vector(x, seed=SEED, n_boot=N_BOOT):
    gen = np.random.default_rng(seed)
    return gen.choice(x, size=(n_boot, len(x)), replace=True)


def ci(x, level=.95):
    a = (1-level) / 2
    return [float(np.quantile(x, a)), float(np.quantile(x, 1-a))]


def percentage(v):
    return f'{100*v:.2f}%'


def check_data(p, q, ts, pooled):
    assert len(p) == 195 and len(q) == 195, 'Unexpected pair count'
    assert p.pair_id.is_unique and q.pair_id.is_unique, 'Duplicate pair identifiers'
    assert set(p.pair_id) == set(q.pair_id), 'Pair IDs mismatch'
    assert p.notna().all().all() and q.notna().all().all(), 'Missing values in pair summaries'
    assert ((p.n_embedded_original + p.n_short) == p.n_group_sample).all()
    assert ((p.n_semantically_eligible + p.n_url_only + p.n_mention_only + p.n_nonlexical_only) == p.n_embedded_original).all()
    assert (p.n_semantically_eligible > 0).all()
    assert (p.n_channel_unique_texts > 0).all()
    assert np.allclose(p.filtered_count_t052/p.n_semantically_eligible, p.filtered_rate_t052)
    j = p.merge(q[['pair_id','n_group_sample','n_meaningful','rate_t052']], on='pair_id', validate='one_to_one', suffixes=('','_q'))
    assert (j.n_group_sample == j.n_group_sample_q).all()
    assert (j.n_embedded_original == j.n_meaningful).all()
    assert np.allclose(j.original_rate_t052, j.rate_t052)
    for topic in ('crypto','conspiracy'):
        s = p[p.topic==topic]
        row = pooled[pooled.topic==topic].iloc[0]
        assert s.n_group_sample.sum() == row.sampled_group_messages
        assert s.n_short.sum() == row.short_chit_chat
        assert s.n_embedded_original.sum() == row.meaningful_messages
        for lab, threshold in (('t050', .50), ('t052', .52), ('t055', .55)):
            raw_mean = float(s[f'original_rate_{lab}'].mean())
            referenced_mean = float(ts[(ts.topic == topic) & np.isclose(ts.threshold, threshold)].mean_pair_rate.iloc[0])
            assert np.isclose(raw_mean, referenced_mean)
            raw_count = int((s[f'original_rate_{lab}'] * s.n_embedded_original).sum().round())
            assert raw_count == int(row[f'group_only_{lab}'])
    return True


def plot_all(p, mean_ci, figs):
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'savefig.dpi':300})
    groups = ['crypto','conspiracy']
    data = [100*p[p.topic==topic].filtered_rate_t052.to_numpy() for topic in groups]
    colors = [plt.rcParams['axes.prop_cycle'].by_key()['color'][i] for i in range(2)]

    fig,ax=plt.subplots(figsize=(7.8,5.3), layout='constrained')
    bp=ax.boxplot(data, positions=[1,2], widths=.43, patch_artist=True, showfliers=False, medianprops={'color':'black','linewidth':1.5})
    for patch,col in zip(bp['boxes'],colors):
        patch.set_facecolor(col);patch.set_alpha(.18);patch.set_edgecolor(col)
    rng=np.random.default_rng(SEED)
    for i, vals in enumerate(data):
        x=i+1+rng.uniform(-.22,.22,size=len(vals))
        ax.scatter(x,vals,s=13,alpha=.37,color=colors[i],edgecolor='none')
        ax.scatter(i+1,vals.mean(),marker='D',color=colors[i],s=56,zorder=4,label='Mean' if i==0 else None)
    ax.set_xticks([1,2],['Crypto (n=98)','Conspiracy (n=97)'])
    ax.set_ylim(0,104);ax.set_ylabel('Semantically non-aligned group messages (%)')
    ax.set_title('Point 4 | Per-community group-only share (threshold 0.52)')
    ax.grid(axis='y',alpha=.15)
    fig.savefig(figs/'01_distribution.png',bbox_inches='tight')
    fig.savefig(figs/'01_distribution.svg',bbox_inches='tight')
    plt.close(fig)

    fig,ax=plt.subplots(figsize=(8.8,5.9),layout='constrained')
    for topic,color in zip(groups,colors):
        g=p[p.topic==topic]
        x=np.log10(g.n_channel_unique_texts)
        y=g.filtered_rate_t052*100
        ax.scatter(g.n_channel_unique_texts,y,s=24,alpha=.59,label=f'{topic.title()} pairs',color=color)
        smoothed=lowess(y,x,frac=.5,it=1,return_sorted=True)
        ax.plot(10**smoothed[:,0],smoothed[:,1],lw=2,color=color,label=f'{topic.title()} LOWESS (descriptive)')
    ax.set_xscale('log');ax.set_ylim(0,104);ax.set_xlim(.8,30000)
    ax.set_xlabel('Number of distinct channel posts (log scale)')
    ax.set_ylabel('Semantically non-aligned group messages (%)')
    ax.set_title('Point 4 | Dependence on available channel-post count')
    ax.legend(loc='lower left',fontsize=8,frameon=False);ax.grid(alpha=.15,which='both')
    fig.savefig(figs/'02_channel_size.png',bbox_inches='tight')
    fig.savefig(figs/'02_channel_size.svg',bbox_inches='tight')
    plt.close(fig)

    fig,ax=plt.subplots(figsize=(7.6,5.1),layout='constrained')
    x=np.array([.5,.52,.55]); labels=['t050','t052','t055']
    for topic,color in zip(groups,colors):
        g=p[p.topic==topic]
        means=np.array([g[f'filtered_rate_{lab}'].mean() for lab in labels])
        cis=[]
        for i,lab in enumerate(labels):
            b=bootstrap_vector(g[f'filtered_rate_{lab}'].to_numpy(),SEED + 11*i)
            cis.append(ci(b.mean(axis=1)))
        lo=np.array([z[0] for z in cis]);hi=np.array([z[1] for z in cis])
        ax.errorbar(x,means*100,yerr=[(means-lo)*100,(hi-means)*100],marker='o',capsize=3,lw=2,color=color,label=f'{topic.title()}')
    ax.set_xticks(x,['0.50','0.52','0.55']);ax.set_ylim(57,92)
    ax.set_ylabel('Mean per-pair group-only share (%)')
    ax.set_xlabel('Cosine similarity threshold')
    ax.set_title('Point 4 | Sensitivity to threshold (95% bootstrap CIs)')
    ax.legend(frameon=False);ax.grid(axis='y',alpha=.15)
    fig.savefig(figs/'03_threshold_sensitivity.png',bbox_inches='tight')
    fig.savefig(figs/'03_threshold_sensitivity.svg',bbox_inches='tight')
    plt.close(fig)

    edges=[-np.inf,9,49,199,999,np.inf]
    labels=['1–9','10–49','50–199','200–999','1000+']
    d=p.copy();d['channel_bin']=pd.cut(d.n_channel_unique_texts,bins=edges,labels=labels)
    fig,ax=plt.subplots(figsize=(9.2,5.2),layout='constrained')
    xx=np.arange(len(labels)); width=.36
    for i,(topic,color) in enumerate(zip(groups,colors)):
        g=d[d.topic==topic].groupby('channel_bin',observed=True).filtered_rate_t052.agg(['mean','count']).reindex(labels)
        vals=100*g['mean'].to_numpy()
        bars=ax.bar(xx+(i-.5)*width,vals,width,color=color,alpha=.73,label=topic.title())
        for j,b in enumerate(bars):
            ax.annotate(f'n={int(g.iloc[j]["count"])}',(b.get_x()+b.get_width()/2,b.get_height()),xytext=(0,3),textcoords='offset points',ha='center',va='bottom',fontsize=8)
    ax.set_xticks(xx,labels);ax.set_ylim(0,116)
    ax.set_xlabel('Number of distinct channel posts')
    ax.set_ylabel('Mean per-pair group-only share (%)')
    ax.set_title('Point 4 | Comparisons within channel-size strata (descriptive)')
    ax.legend(frameon=False);ax.grid(axis='y',alpha=.12)
    fig.savefig(figs/'04_stratified_channel_size.png',bbox_inches='tight')
    fig.savefig(figs/'04_stratified_channel_size.svg',bbox_inches='tight')
    plt.close(fig)


def analyze(data_dir, out_dir):
    paths={
      'policy':data_dir/'pair_policy_summary.csv',
      'original':data_dir/'pair_results.csv',
      'topic_policy':data_dir/'topic_policy_summary.csv',
      'topic':data_dir/'topic_summary.csv',
      'pooled':data_dir/'pooled_summary.csv',
    }
    for name,path in paths.items():
        if not path.exists():raise FileNotFoundError(f'Missing {name}: {path}')
    p=pd.read_csv(paths['policy']);q=pd.read_csv(paths['original']); t=pd.read_csv(paths['topic_policy']); ts=pd.read_csv(paths['topic']);pool=pd.read_csv(paths['pooled'])
    check_data(p,q,ts,pool)
    figs=out_dir/'figures';figs.mkdir(parents=True,exist_ok=True)
    groups={topic:p[p.topic==topic].copy() for topic in ('crypto','conspiracy')}
    a=groups['crypto'].filtered_rate_t052.to_numpy(); b=groups['conspiracy'].filtered_rate_t052.to_numpy()
    ab=bootstrap_vector(a,SEED);bb=bootstrap_vector(b,SEED+1)
    bootstrap_means={'crypto':ci(ab.mean(axis=1)),'conspiracy':ci(bb.mean(axis=1))}
    diff=b.mean()-a.mean();diffci=ci(bb.mean(axis=1)-ab.mean(axis=1))
    median_diff=np.median(b)-np.median(a)
    medianci=ci(np.median(bb,axis=1)-np.median(ab,axis=1))
    welch=stats.ttest_ind(b,a,equal_var=False)
    brown=stats.levene(a,b,center='median')
    ks=stats.ks_2samp(a,b)
    mwu=stats.mannwhitneyu(b,a,alternative='two-sided')
    p['is_consp']=(p.topic=='conspiracy').astype(int)
    p['log2_channels']=np.log2(p.n_channel_unique_texts)
    p['log2_group']=np.log2(p.n_semantically_eligible)
    add=smf.ols('filtered_rate_t052 ~ is_consp + log2_channels + log2_group',data=p).fit(cov_type='HC3')
    inter=smf.ols('filtered_rate_t052 ~ is_consp * log2_channels + log2_group',data=p).fit(cov_type='HC3')
    result={
       'n_pairs':len(p),'n_crypto':len(a),'n_conspiracy':len(b),
       'sampled_messages':int(p.n_group_sample.sum()),
       'eligible_messages':int(p.n_semantically_eligible.sum()),
       'short_messages':int(p.n_short.sum()),
       'url_only':int(p.n_url_only.sum()),
       'mention_only':int(p.n_mention_only.sum()),
       'nonlexical_only':int(p.n_nonlexical_only.sum()),
       'ci_method':'Within-topic nonparametric percentile bootstrap, 30000 draws; pair is resampling unit',
       'means':{k:{'rate':float(v.filtered_rate_t052.mean()),'ci95':bootstrap_means[k],'median':float(v.filtered_rate_t052.median()),'sd':float(v.filtered_rate_t052.std(ddof=1)),
                       'n_channel_posts_median':float(v.n_channel_unique_texts.median()),'pooled_rate':float(v.filtered_count_t052.sum()/v.n_semantically_eligible.sum())} for k,v in groups.items()},
       'difference_conspiracy_minus_crypto':float(diff), 'difference_ci95':diffci,
       'median_difference':float(median_diff),'median_difference_ci95':medianci,
       'welch_p':float(welch.pvalue),'welch_t':float(welch.statistic),
       'mann_whitney_p_exploratory':float(mwu.pvalue),
       'ks_p_exploratory':float(ks.pvalue),
       'brown_forsythe_p_exploratory':float(brown.pvalue),
       'channel_count_p_mann_whitney':float(stats.mannwhitneyu(groups['crypto'].n_channel_unique_texts,groups['conspiracy'].n_channel_unique_texts).pvalue),
       'spearman':{},
       'additive_regression':{'R2':float(add.rsquared),'topic_coef':float(add.params['is_consp']),'topic_CI':add.conf_int().loc['is_consp'].tolist(),'topic_p':float(add.pvalues['is_consp']),
                              'log2_channel_coef':float(add.params['log2_channels']),'log2_channel_CI':add.conf_int().loc['log2_channels'].tolist(),
                              'log2_channel_p':float(add.pvalues['log2_channels'])},
       'interaction_regression':{'R2':float(inter.rsquared),'interaction_coef':float(inter.params['is_consp:log2_channels']),'interaction_p':float(inter.pvalues['is_consp:log2_channels']),
                                  'interaction_CI':inter.conf_int().loc['is_consp:log2_channels'].tolist()},
       'computational_model_time_hours':float(q[['channel_embedding_time_s','group_embedding_time_s','similarity_time_s']].sum().sum()/3600)
    }
    for topic,g in groups.items():
        r=stats.spearmanr(g.n_channel_unique_texts,g.filtered_rate_t052)
        # Recompute rho in pair bootstrap (same sampled indices for x, y)
        rng=np.random.default_rng(SEED + (3 if topic=='crypto' else 4))
        idx=rng.integers(0,len(g),size=(8000,len(g)))
        xs=g.n_channel_unique_texts.to_numpy();ys=g.filtered_rate_t052.to_numpy()
        rhos=np.array([stats.spearmanr(xs[i],ys[i]).statistic for i in idx])
        result['spearman'][topic]={'rho':float(r.statistic),'p':float(r.pvalue),'ci95':ci(rhos)}

    table=[]
    for topic,g in groups.items():
        for label,th in [('t050',.5),('t052',.52),('t055',.55)]:
            table.append({'topic':topic,'basis':'filtered_messages','threshold':th,'n_pairs':len(g),'mean_pct':100*g[f'filtered_rate_{label}'].mean(),'median_pct':100*g[f'filtered_rate_{label}'].median()})
        for basis,col in [('original_embedded','original_rate_t052'),('unique_texts','unique_rate_t052'),('frequency_cap5','cap5_rate_t052')]:
            table.append({'topic':topic,'basis':basis,'threshold':.52,'n_pairs':len(g),'mean_pct':100*g[col].mean(),'median_pct':100*g[col].median()})
    pd.DataFrame(table).to_csv(out_dir/'result_summary.csv',index=False)
    s=p.copy();s['delta_unique_minus_filtered_pp']=100*(s.unique_rate_t052-s.filtered_rate_t052)
    s['delta_filter_minus_original_pp']=100*(s.filtered_rate_t052-s.original_rate_t052)
    s.sort_values('pair_id').to_csv(out_dir/'pair_diagnostics.csv',index=False)
    strata=[]
    for lower,upper,name in [(1,9,'1-9'),(10,49,'10-49'),(50,199,'50-199'),(200,999,'200-999'),(1000,np.inf,'1000+')]:
        for topic,g in groups.items():
            h=g[(g.n_channel_unique_texts>=lower)&(g.n_channel_unique_texts<=upper)]
            strata.append({'stratum':name,'topic':topic,'n_pairs':len(h),'mean_pct':100*h.filtered_rate_t052.mean(),'median_pct':100*h.filtered_rate_t052.median()})
    pd.DataFrame(strata).to_csv(out_dir/'channel_size_strata.csv',index=False)
    plot_all(p,bootstrap_means,figs)
    with open(out_dir/'statistics.json','w',encoding='utf8') as fh: json.dump(result,fh,indent=2,ensure_ascii=False)
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--data-dir',type=Path,default=Path('.'))
    parser.add_argument('--out-dir',type=Path,default=Path('point4_final_analysis'))
    args=parser.parse_args()
    r=analyze(args.data_dir,args.out_dir)
    print(json.dumps(r,ensure_ascii=False,indent=2))

if __name__=='__main__':main()

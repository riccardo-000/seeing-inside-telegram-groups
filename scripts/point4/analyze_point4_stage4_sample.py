"""Analyze an independently sampled and FULLY CODED Point-4 Stage-4 blind CSV.

Does not infer labels, open URLs, fit embeddings or assume human raters exist.
Produces descriptive, pair-weighted exploratory estimates. Bootstrap uncertainty
reflects pair and within-pair resampling ONLY, not annotation error.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

import numpy as np
import pandas as pd

FUNCTIONS = [
    'Substantive discussion/opinion', 'Question or help request',
    'Information/news sharing', 'Greeting/social interaction',
    'Promotion/solicitation', 'Moderation/security', 'Other/unclear',
]
THEMES = [
    'Crypto/markets', 'Technical/blockchain/wallet', 'Platform/rewards',
    'Scams/security', 'Politics/government', 'War/geopolitics',
    'Health/medicine', 'Religion/spirituality', 'Migration/identity',
    'History/conspiracy claims', 'Platform/community operations',
    'Technology/software/privacy', 'Work/commerce/services',
    'Media/arts/gaming', 'Daily life/personal', 'Science/environment',
    'History/culture (non-conspiratorial)', 'Other specific topic',
    'No clear theme', 'Unclear',
]
FLAGS = {'INTERPRETABLE':['YES','NO','UNSURE'], 'PROMOTIONAL':['YES','NO','UNSURE']}
TOPICS=('crypto','conspiracy')


def read_inputs(annotations, key):
    a=pd.read_csv(annotations, dtype=str, keep_default_na=False, encoding='utf-8-sig')
    k=pd.read_csv(key, dtype=str, keep_default_na=False, encoding='utf-8-sig')
    needed={'ITEM_ID','GROUP_MESSAGE','FUNCTION_LABEL','THEME_LABEL','INTERPRETABLE','PROMOTIONAL'}
    key_needed={'ITEM_ID','topic','pair_id','group_msg_id','n_population_in_pair','n_selected_in_pair','inclusion_probability','analysis_weight'}
    if not needed.issubset(a.columns) or not key_needed.issubset(k.columns):
        raise ValueError('Missing required fields in annotations/key')
    if a.ITEM_ID.duplicated().any() or k.ITEM_ID.duplicated().any():
        raise ValueError('Duplicate ITEM_ID')
    if set(a.ITEM_ID)!=set(k.ITEM_ID):
        raise ValueError('Annotation and sampling key differ in ITEM_ID')
    for col, allowed in [('FUNCTION_LABEL',FUNCTIONS), ('THEME_LABEL',THEMES), *FLAGS.items()]:
        invalid=a.loc[~a[col].isin(allowed),['ITEM_ID',col]]
        if not invalid.empty:
            raise ValueError(f'{col} missing/invalid in {len(invalid)} rows. First: {invalid.head(7).to_dict("records")}')
    v=a.merge(k,on='ITEM_ID',validate='one_to_one')
    if not bool(v.topic.isin(TOPICS).all()) or len(v)!=len(k):
        raise ValueError('Invalid topic values or sample size')
    for _,g in v.groupby('pair_id'):
        claimed=int(g.n_selected_in_pair.iloc[0])
        pool=int(g.n_population_in_pair.iloc[0])
        if len(g)!=claimed or claimed>pool:
            raise ValueError(f'Sampling count mismatch for {g.pair_id.iloc[0]}')
        if not np.isclose(float(g.inclusion_probability.iloc[0]),claimed/pool):
            raise ValueError(f'Sampling probability mismatch in {g.pair_id.iloc[0]}')
    return v


def get_bootstrap_draws(v, topic, B, rng):
    sub=v[v.topic==topic].sort_values(['pair_id','group_msg_id'])
    groups=[part for _,part in sub.groupby('pair_id')]
    sizes={len(g) for g in groups}
    if len(sizes)!=1:
        raise ValueError('This analysis requires constant per-pair sample size; rerun sampling with equal m or adapt bootstrap.')
    n=len(groups)
    m=next(iter(sizes))
    pair_choice=rng.integers(0,n,size=(B,n),dtype=np.int32)
    msg_choice=rng.integers(0,m,size=(B,n,m),dtype=np.int16)
    return groups,pair_choice,msg_choice


def boot_metric(groups, pair_choice, msg_choice, col, labels):
    matrix=np.array([[row for row in group[col]] for group in groups],dtype=object)
    sel=matrix[pair_choice[:,:,None],msg_choice]
    out={}
    for label in labels:
        estimate=float(np.mean(matrix==label))
        samples=np.mean(sel==label,axis=(1,2))
        lo,hi=np.quantile(samples,[0.025,0.975])
        out[label]=(estimate,float(lo),float(hi),samples)
    return out


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--annotations',type=Path,required=True)
    p.add_argument('--key',type=Path,required=True)
    p.add_argument('--out-dir',type=Path,default=None)
    p.add_argument('--bootstrap-reps',type=int,default=3000)
    p.add_argument('--seed',type=int,default=20261113)
    args=p.parse_args()
    if args.bootstrap_reps<500:raise ValueError('--bootstrap-reps must be >=500')
    df=read_inputs(args.annotations,args.key)
    out=args.out_dir or (args.key.parent/'analysis')
    out.mkdir(parents=True,exist_ok=True)
    bootstrap={}
    rng=np.random.default_rng(args.seed)
    for t in TOPICS:
        bootstrap[t]=get_bootstrap_draws(df,t,args.bootstrap_reps,rng)
    specs=[('FUNCTION_LABEL',FUNCTIONS,'function'),('THEME_LABEL',THEMES,'theme'),('INTERPRETABLE',FLAGS['INTERPRETABLE'],'interpretable'),('PROMOTIONAL',FLAGS['PROMOTIONAL'],'promotional')]
    all_summary=[]
    for col, labels, name in specs:
        topic_outputs={}
        for t in TOPICS:
            topic_outputs[t]=boot_metric(*bootstrap[t],col,labels)
            for label in labels:
                est,lo,hi,_=topic_outputs[t][label]
                all_summary.append({'field':name,'category':label,'topic':t,'n_pairs':len(bootstrap[t][0]),'n_annotated_messages':sum(len(g) for g in bootstrap[t][0]),'pair_equal_rate':est,'bootstrap_low_95':lo,'bootstrap_high_95':hi})
        for label in labels:
            crypto=topic_outputs['crypto'][label]
            consp=topic_outputs['conspiracy'][label]
            diff=consp[3]-crypto[3]
            lo,hi=np.quantile(diff,[.025,.975])
            all_summary.append({'field':name,'category':label,'topic':'difference_conspiracy_minus_crypto','n_pairs':len(bootstrap['crypto'][0])+len(bootstrap['conspiracy'][0]),'n_annotated_messages':len(df),'pair_equal_rate':consp[0]-crypto[0],'bootstrap_low_95':float(lo),'bootstrap_high_95':float(hi)})
    pd.DataFrame(all_summary).to_csv(out/'stage4_exploratory_estimates.csv',index=False,encoding='utf-8-sig')
    pair_rows=[]
    for (topic,pair), g in df.groupby(['topic','pair_id']):
        base={'topic':topic,'pair_id':pair,'n_labeled':len(g),'n_population_group_only':int(g.n_population_in_pair.iloc[0])}
        for col,labels,name in specs:
            for label in labels:
                base[f'{name}::{label}']=float((g[col]==label).mean())
        pair_rows.append(base)
    pd.DataFrame(pair_rows).to_csv(out/'stage4_pair_label_rates.csv',index=False,encoding='utf-8-sig')
    info={'n_messages':len(df),'n_pairs':df.pair_id.nunique(),'n_crypto':int((df.topic=='crypto').sum()),'n_conspiracy':int((df.topic=='conspiracy').sum()),'bootstrap_reps':args.bootstrap_reps,'provenance':'Annotation provenance must be reported separately; this script is not a validator of coding truth.',
          'interpretation':'Pair-equal proportions of *assigned* labels among group-only eligible messages in the original per-pair sample. Bootstrap combines pair and within-pair resampling, excludes labeling error. Do not claim human validation or inter-rater reliability.'}
    (out/'stage4_analysis_manifest.json').write_text(json.dumps(info,indent=2),encoding='utf-8')
    print(f'DONE: {len(df):,} coded messages; {df.pair_id.nunique()} pairs; output in {out}')
    for col,labels,name in specs[:2]:
        summary=pd.DataFrame(all_summary)
        focus=summary[(summary.field==name)&(summary.topic.isin(TOPICS))].sort_values('pair_equal_rate',ascending=False)
        print(f'\nMost frequent {name} labels (exploratory conditional on coding):')
        print(focus.head(6)[['topic','category','pair_equal_rate']].to_string(index=False))

if __name__=='__main__':main()

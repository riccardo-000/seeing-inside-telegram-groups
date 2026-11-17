#!/usr/bin/env python3
"""Read-only reply-graph pilot for the existing conspiracy Toxicity-Lens full corpus."""
import argparse
import contextlib
import json
import os
import sqlite3
import sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pandas as pd

THRESHOLDS = (.3, .5, .7)
METHODS = ('prefix', 'chunks')


def read_scores(db, entry, frame, full, checkpoint):
    pid = entry['pair_id']; digest, total, scored = checkpoint
    if total != entry['group_total'] or scored != total or len(frame) != total:
        raise RuntimeError(f'{pid}: complete group count mismatch')
    if full.sample_digest(frame) != digest:
        raise RuntimeError(f'{pid}: row digest mismatch; no score join performed')
    s = pd.read_sql_query('SELECT "row",voice,role,n_chars,prefix_toxicity,chunks_toxicity FROM scores WHERE pair_id=? AND side=? ORDER BY "row"', db, params=(pid,'group'))
    if len(s) != total or not np.array_equal(s['row'].to_numpy(), np.arange(total)):
        raise RuntimeError(f'{pid}: score rows not contiguous')
    for col in ('voice','role','n_chars'):
        if not np.array_equal(s[col].to_numpy(), frame[col].to_numpy()):
            raise RuntimeError(f'{pid}: checkpoint {col} mismatch')
    for m in METHODS:
        values = s[m+'_toxicity'].to_numpy(float)
        if not np.isfinite(values).all() or ((values<0)|(values>1)).any():
            raise RuntimeError(f'{pid}: invalid toxicity scores')
    return s


def audit_and_analyze(pair_num, frame, raw, scores):
    """One group, exact row alignment already checked. No IDs/text in outputs."""
    if frame.chat_id.nunique()>1 or raw.chat_id.nunique()>1 or raw['id'].duplicated().any():
        raise RuntimeError(f'P{pair_num:03d}: multiple chats or duplicate raw IDs')
    if len(frame) and (len(raw)==0 or frame.chat_id.iloc[0]!=raw.chat_id.iloc[0]):
        raise RuntimeError(f'P{pair_num:03d}: raw/eligible chat mismatch')
    f=frame.reset_index(drop=True)
    lookup={int(mid): i for i,mid in enumerate(f.msg_id)}
    raw_ids=set(map(int,raw['id']))
    reply=f.reply_to.notna().to_numpy()
    children=np.flatnonzero(reply)
    parents=np.array([lookup.get(int(f.reply_to.iloc[i]),-1) for i in children],dtype=np.int64)
    raw_present=np.array([int(f.reply_to.iloc[i]) in raw_ids for i in children],dtype=bool)
    matched=parents>=0
    child=children[matched]; parent=parents[matched]
    # Same chat ID, parent ID smaller and parent timestamp not later than child.
    ids=f.msg_id.to_numpy(dtype=np.int64); dates=f.date.astype('int64').to_numpy()
    time_ok=(ids[parent]<ids[child]) & (dates[parent]<=dates[child])
    child=child[time_ok]; parent=parent[time_ok]
    kind=f.sender_kind.fillna('none').to_numpy(); sender=f.sender.to_numpy(dtype=object)
    known=np.array([kind[c]==kind[p] and kind[c] in ('user','channel') and pd.notna(sender[c]) and pd.notna(sender[p]) and sender[c]==sender[p] for c,p in zip(child,parent)],dtype=bool)
    # Longest observed eligible chain ending at each message; lower bound, not full thread depth.
    parent_by_child={int(c):int(p) for c,p in zip(child,parent)}
    depth=np.zeros(len(f),dtype=np.int64)
    for c in np.argsort(ids):
        if c in parent_by_child: depth[c]=depth[parent_by_child[c]]+1
    audit=dict(pair=pair_num,eligible_group=len(f),raw_group=len(raw),raw_reply_messages=int(raw.reply_to.notna().sum()),eligible_reply_messages=len(children),parent_in_raw=int(raw_present.sum()),parent_not_in_raw=int((~raw_present).sum()),parent_in_raw_but_not_eligible=int((raw_present & ~matched).sum()),parent_eligible=int(matched.sum()),invalid_order=int((~time_ok).sum()),usable_edges=len(child),known_same_sender_edges=int(known.sum()),usable_without_known_self=int((~known).sum()),observed_chain_ge_3_messages=int((depth>=2).sum()),max_observed_depth=int(depth.max()) if len(depth) else 0,flagged_channel_comments=int(f.is_comment.sum()))
    transitions=[]; roles=[]; comments=[]
    voices=f.voice.to_numpy()
    for method in METHODS:
        vals=scores[method+'_toxicity'].to_numpy(float)
        for th in THRESHOLDS:
            toxic=vals>=th
            for subset,mask in [('all_edges',np.ones(len(child),dtype=bool)),('exclude_known_self',~known)]:
                c,p=child[mask],parent[mask]
                a,b=toxic[p],toxic[c]
                n11=int((a&b).sum()); n10=int((a&~b).sum()); n01=int((~a&b).sum()); n00=int((~a&~b).sum())
                n1=n11+n10; n0=n01+n00
                p1=100*n11/n1 if n1 else np.nan; p0=100*n01/n0 if n0 else np.nan
                transitions.append(dict(pair=pair_num,method=method,threshold=th,subset=subset,edges=len(c),parent_toxic_reply_toxic=n11,parent_toxic_reply_not=n10,parent_not_reply_toxic=n01,parent_not_reply_not=n00,n_toxic_parents=n1,n_nontoxic_parents=n0,pct_reply_toxic_given_toxic=p1,pct_reply_toxic_given_nontoxic=p0,difference_pp=p1-p0))
                if subset=='exclude_known_self':
                    for pv in ('admin','user'):
                        for cv in ('admin','user'):
                            k=(voices[p]==pv)&(voices[c]==cv)
                            n=int(k.sum()); pos=int((k&b).sum())
                            roles.append(dict(pair=pair_num,method=method,threshold=th,parent_voice=pv,reply_voice=cv,n=n,positive=pos,prevalence_pct=100*pos/n if n else np.nan))
            for label,mask in [('flagged_channel_comment',f.is_comment.to_numpy(bool)),('not_flagged',~f.is_comment.to_numpy(bool))]:
                n=int(mask.sum()); pos=int((mask&toxic).sum())
                comments.append(dict(pair=pair_num,method=method,threshold=th,context=label,n=n,positive=pos,prevalence_pct=100*pos/n if n else np.nan))
    return audit,transitions,roles,comments


def summary(transitions):
    rows=[]
    for (m,t,s),x in transitions.groupby(['method','threshold','subset']):
        for min_n in (1,20,50):
            q=x[(x.n_toxic_parents>=min_n)&(x.n_nontoxic_parents>=min_n)]
            n1=int(q.n_toxic_parents.sum()); n0=int(q.n_nontoxic_parents.sum()); d=q.difference_pp
            rows.append(dict(method=m,threshold=t,subset=s,min_edges_each_parent_class=min_n,n_groups=len(q),n_edges=int(q.edges.sum()),median_difference_pp=d.median(),groups_positive=int((d>0).sum()),groups_negative=int((d<0).sum()),groups_tied=int((d==0).sum()),pooled_pct_given_toxic=100*q.parent_toxic_reply_toxic.sum()/n1 if n1 else np.nan,pooled_pct_given_nontoxic=100*q.parent_not_reply_toxic.sum()/n0 if n0 else np.nan))
    return pd.DataFrame(rows)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo',type=Path,default=Path.cwd())
    p.add_argument('--toxicity-dir',type=Path,required=True)
    p.add_argument('--output-dir',type=Path,required=True)
    p.add_argument('--limit-pairs',type=int,default=5,help='First N complete pairs at start; 0 = all complete pairs')
    a=p.parse_args(); repo=a.repo.resolve(); source=a.toxicity_dir.resolve(); out=a.output_dir.resolve()
    if a.limit_pairs<0 or out==repo or repo in out.parents or out==source or source in out.parents or out in source.parents or out.exists():
        p.error('Use a new output directory outside the repository and separate from the toxicity directory; limit >=0.')
    import lens_pairs_full as full
    plan=json.loads((source/'plan.json').read_text(encoding='utf-8-sig')); cfg=plan['config']; entries=plan['pairs']
    if cfg['topic']!='conspiracy' or cfg['window']!='overlap' or cfg['long_mode']!='both' or cfg['cap'] is not None:
        raise RuntimeError('Unexpected toxicity plan configuration')
    if full.hash_file(Path(full.__file__))!=cfg['script_sha256']:
        raise RuntimeError('Original toxicity script hash differs from plan')
    sys.path.insert(0,str(repo)); from src.analyze import load as loader
    pairs=loader.pairs('conspiracy')
    if len(pairs)!=97 or len(entries)!=97 or not pairs.has_data.all() or pairs.pair_id.tolist()!=[e['pair_id'] for e in entries]:
        raise RuntimeError('Pair list differs from plan')
    if [e['pair'] for e in entries]!=list(range(1,98)):
        raise RuntimeError('Unexpected pair numbering')
    norm=lambda d:{k.replace('\\','/'):v for k,v in d.items()}
    print('Verifying original source hashes...',flush=True)
    if norm(full.snapshot(repo,pairs))!=norm(plan['sources']):
        raise RuntimeError('Input source hashes differ from original plan')
    dbpath=source/'scores.sqlite3'
    audits=[]; transitions=[]; roles=[]; comments=[]
    with contextlib.closing(sqlite3.connect(dbpath.as_uri()+'?mode=ro',uri=True,timeout=10)) as db:
        db.execute('PRAGMA query_only=ON')
        # One short statement: only groups from pairs complete at start. No long read transaction.
        checkpoint={(pid,side):(digest,n,k) for pid,side,digest,n,k in db.execute('SELECT pair_id,side,digest,total,scored FROM progress')}
        complete=[e for e in entries if all((e['pair_id'],s) in checkpoint and checkpoint[e['pair_id'],s][1:]==(e[s+'_total'],e[s+'_total']) for s in ('channel','group'))]
        selected=complete[:a.limit_pairs] if a.limit_pairs else complete
        if not selected: raise RuntimeError('No complete pairs available')
        by_id={r.pair_id:r for _,r in pairs.iterrows()}
        for j,e in enumerate(selected,1):
            pid=e['pair_id']; pair=by_id[pid]
            print(f'[{j}/{len(selected)}] P{e["pair"]:03d}',flush=True)
            frames,_=full.prepare(loader,pair,SimpleNamespace(window=cfg['window']))
            f=frames['group']; del frames
            sc=read_scores(db,e,f,full,checkpoint[pid,'group'])
            raw=loader.read_dump(pair['group_file'])[['chat_id','id','reply_to']]
            audit, tr, ro, co=audit_and_analyze(e['pair'],f,raw,sc)
            audits.append(audit); transitions.extend(tr); roles.extend(ro); comments.extend(co)
            print(f'  {audit["usable_edges"]:,} matched reply edges',flush=True)
    out.mkdir(parents=True,exist_ok=False)
    t=pd.DataFrame(transitions)
    for name,df in [('conversation_audit',pd.DataFrame(audits)),('reply_transitions',t),('reply_roles',pd.DataFrame(roles)),('comment_context',pd.DataFrame(comments)),('conversation_summary',summary(t))]:
        full.atomic_csv(df,out/(name+'.csv'))
    meta=dict(created_utc=full.now(),script_sha256=full.hash_file(Path(__file__)),plan_sha256=full.hash_file(source/'plan.json'),model=json.loads((source/'model.json').read_text(encoding='utf-8-sig')),completed_pairs_at_start=len(complete),selected_pairs=[e['pair'] for e in selected],scope='complete pairs at start; group direct replies only',primary='chunks, threshold 0.5, exclude known self-replies; exploratory per-group risk difference',cautions=['Reply IDs resolved within same chat; original dump does not retain explicit cross-chat reply target.','Not flagged as comment does not imply free chat.','Parent not eligible includes copies, no-text, bots, service, outside overlap etc.','Observed depth is lower bound, not full conversational depth.','Repeated replies/users not independent; pooled estimates descriptive, not causal.','No human or language validation yet.'])
    full.atomic_json(meta,out/'conversation_meta.json')
    au=pd.DataFrame(audits); n=int(au.usable_edges.sum()); r=int(au.eligible_reply_messages.sum())
    report=f'# Conversation analysis — exploratory snapshot\n\nPairs: {len(selected)}/{len(entries)} ({len(complete)} complete at start)\n\nEligible group messages: {au.eligible_group.sum():,}\n\nEligible direct replies: {r:,}\n\nUsable scored reply edges: {n:,} ({100*n/r if r else 0:.2f}% of eligible replies)\n\nKnown same-sender edges: {au.known_same_sender_edges.sum():,}\n\nMessages ending observed chains of at least three messages: {au.observed_chain_ge_3_messages.sum():,}\n\nPrimary: chunks, threshold 0.5, exclude known self-replies. See conversation_summary.csv; minimum 20 edges in each parent class is an exploratory support filter.\n\nNo causal claims. No message text, sender IDs or message IDs exported.\n'
    (out/'conversation_report.md').write_text(report,encoding='utf-8')
    print(report,flush=True)

if __name__=='__main__': main()

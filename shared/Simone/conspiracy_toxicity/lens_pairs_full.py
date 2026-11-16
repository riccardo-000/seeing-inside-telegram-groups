#!/usr/bin/env python3
"""Local paired toxicity pilot using the project's own analysis loader."""
import argparse, hashlib, json, os, sys, time, sqlite3, subprocess
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

MODEL = 'abacusai/Toxicity-Lens'
MODEL_FILE = 'onnx/model_int8_block32.onnx'
LABELS = ['toxicity','severe_toxicity','identity_attack','insult','profanity','threat','sexually_explicit']
LIMIT = 256
STRIDE = 32


def atomic_csv(df, path):
    tmp = path.with_suffix('.tmp')
    df.to_csv(tmp, index=False, encoding='utf-8-sig')
    os.replace(tmp, path)


def atomic_json(obj,path):
    tmp=path.with_suffix('.tmp'); tmp.write_text(json.dumps(obj,indent=2),encoding='utf-8'); os.replace(tmp,path)


def hash_file(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()


def stable_seed(seed, pair, side):
    return int.from_bytes(hashlib.sha256(f'{seed}:{pair}:{side}'.encode()).digest()[:4], 'big')


class Lens:
    def __init__(self, revision, threads, batch):
        import onnxruntime as ort
        from huggingface_hub import hf_hub_download
        from transformers import AutoTokenizer
        cfg=Path(hf_hub_download(MODEL,'config.json',revision=revision))
        # Pin all other downloads to the actual resolved snapshot, even if requested main.
        self.revision=cfg.parent.name
        p=hf_hub_download(MODEL,MODEL_FILE,revision=self.revision)
        self.tok=AutoTokenizer.from_pretrained(MODEL, revision=self.revision,use_fast=True)
        if not self.tok.is_fast: raise RuntimeError('Fast tokenizer required for overflow windows')
        mapping=json.loads(cfg.read_text(encoding='utf-8'))['id2label']
        order=[mapping[str(i)].lower() for i in range(len(mapping))]
        if len(order)!=7 or set(order)!=set(LABELS): raise RuntimeError(f'Unexpected labels: {order}')
        self.order=[order.index(k) for k in LABELS]
        opts=ort.SessionOptions(); opts.intra_op_num_threads=threads; opts.inter_op_num_threads=1
        opts.graph_optimization_level=ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        self.sess=ort.InferenceSession(p,sess_options=opts,providers=['CPUExecutionProvider'])
        self.inputs={v.name for v in self.sess.get_inputs()}; self.batch=batch
        self.model_sha=hash_file(p)

    def predict(self, enc):
        feed={}
        for name in self.inputs:
            if name in enc: feed[name]=np.asarray(enc[name],dtype=np.int64)
            elif name=='token_type_ids': feed[name]=np.zeros_like(enc['input_ids'],dtype=np.int64)
            else: raise RuntimeError(f'Unknown ONNX input {name}')
        logits=np.asarray(self.sess.run(None,feed)[0],dtype=np.float64)
        if logits.shape!=(len(enc['input_ids']),7) or not np.isfinite(logits).all(): raise RuntimeError('Invalid logits')
        return np.exp(-np.logaddexp(0,-logits[:,self.order]))

    def score(self,texts, chunks):
        texts=[str(t).strip() for t in texts]
        lengths=np.array([len(x) for x in self.tok(texts,truncation=False,verbose=False)['input_ids']])
        enc=self.tok(texts,truncation=True,max_length=LIMIT,padding=True,return_tensors='np')
        prefix=self.predict(enc); maximum=prefix.copy(); windows=np.ones(len(texts),dtype=int)
        if chunks:
            for i in np.flatnonzero(lengths>LIMIT):
                enc=self.tok(texts[i],truncation=True,max_length=LIMIT,stride=STRIDE,
                             return_overflowing_tokens=True,padding=True,return_tensors='np')
                n=len(enc['input_ids']); windows[i]=n
                # Include the original prefix score; only infer subsequent windows.
                for j in range(1,n,self.batch):
                    scores=self.predict({k:v[j:j+self.batch] for k,v in enc.items() if k in self.inputs or k=='input_ids'})
                    maximum[i]=np.maximum(maximum[i],scores.max(axis=0))
        return prefix, maximum, lengths, windows


def prepare(loader,pair,args):
    df=loader.prepare_pair(pair,text=True)
    # Use the repository role contract, plus explicit bot flag and duplicate check.
    if df.duplicated(['side','chat_id','msg_id']).any():
        raise RuntimeError(f'Duplicate message keys in {pair.pair_id}; inspect raw dumps before continuing.')
    windows={}
    for side in ('channel','group'):
        x=df[df.side==side]
        a,b,note=loader.chat_window(x.date,pair[side]); windows[side]=(a,b,note)
    if args.window=='overlap':
        start=max(w[0] for w in windows.values()); end=min(w[1] for w in windows.values())
        if start>=end: raise RuntimeError(f'No overlapping window for {pair.pair_id}')
        df=df[df.in_window & df.date.ge(start) & df.date.le(end)].copy()
        effective={side:(start,end) for side in windows}
    else:
        df=df[df.in_window].copy(); effective={s:(v[0],v[1]) for s,v in windows.items()}
    outputs={}; meta=[]
    for side in ('channel','group'):
        x=df[df.side==side]
        eligible=x[x.has_text & ~x.is_bot & ~x.is_service & x.voice.isin(['channel','admin','user'])].copy()
        eligible=eligible.sort_values(['chat_id','msg_id'])
        sample=eligible  # full eligible population, no sampling
        sample=sample.reset_index(drop=True)
        a,b=effective[side]
        meta.append(dict(pair_id=pair.pair_id,side=side,chat=pair[side],window_start=str(a),window_end=str(b),
            original_window_note=windows[side][2],window_days=(b-a).total_seconds()/86400,n_in_window=len(x),
            n_eligible=len(eligible),n_sample=len(sample),n_bots=int(x.is_bot.sum()),
            n_copies=int(x.role.eq('channel_copy').sum()),n_other_channel=int(x.role.eq('other_channel').sum()),
            n_service=int(x.is_service.sum()),n_no_text=int((~x.has_text).sum()),
            n_eligible_admin=int(eligible.voice.eq('admin').sum()),n_eligible_user=int(eligible.voice.eq('user').sum())))
        outputs[side]=sample
    return outputs,meta


def summaries(all_scores, meta, args):
    chatrows=[]; voicerows=[]; pairrows=[]; final=[]
    methods=['prefix','chunks'] if args.long_mode=='both' else ['prefix']
    def stats(scores,keys):
        rows=[]
        for method in methods:
            for lab in LABELS:
                vals=scores[method+'_'+lab].astype(float); n=len(vals)
                for threshold in (.3,.5,.7):
                    pos=int(vals.ge(threshold).sum())
                    rows.append(dict(**keys,method=method,category=lab,threshold=threshold,n=n,positive=pos,
                        prevalence_pct=100*pos/n if n else np.nan,mean_score=vals.mean(),
                        median_chars=scores.n_chars.median(),median_tokens=scores.n_tokens.median(),
                        truncated_pct=100*scores.was_truncated.mean() if n else np.nan))
        return rows
    for pid,side,sc in all_scores:
        chatrows.extend(stats(sc,dict(pair_id=pid,side=side)))
        for voice in (['channel'] if side=='channel' else ['admin','user']):
            voicerows.extend(stats(sc[sc.voice==voice],dict(pair_id=pid,side=side,voice=voice)))
    c=pd.DataFrame(chatrows); v=pd.DataFrame(voicerows)
    for (pid,method,lab,th),g in c.groupby(['pair_id','method','category','threshold'],sort=False):
        a=g[g.side=='channel'].iloc[0]; b=g[g.side=='group'].iloc[0]
        pairrows.append(dict(pair_id=pid,method=method,category=lab,threshold=th,n_channel=a.n,n_group=b.n,
            positive_channel=a.positive,positive_group=b.positive,channel_pct=a.prevalence_pct,group_pct=b.prevalence_pct,
            delta_pp=b.prevalence_pct-a.prevalence_pct,channel_truncated_pct=a.truncated_pct,group_truncated_pct=b.truncated_pct))
    p=pd.DataFrame(pairrows)
    for (method,lab,th),g in p.groupby(['method','category','threshold'],sort=False):
        x=g.dropna(subset=['delta_pp']); d=x.delta_pp
        final.append(dict(method=method,category=lab,threshold=th,n_pairs=len(x),
            median_channel_pct=x.channel_pct.median(),median_group_pct=x.group_pct.median(),median_paired_delta_pp=d.median(),
            mean_paired_delta_pp=d.mean(),groups_higher=int(d.gt(0).sum()),channels_higher=int(d.lt(0).sum()),ties=int(d.eq(0).sum())))
    return c,v,p,pd.DataFrame(final),pd.DataFrame(meta)



COLS=['row','voice','role','n_chars','n_tokens','was_truncated','n_windows']+['prefix_'+k for k in LABELS]+['chunks_'+k for k in LABELS]


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def open_db(out):
    db=sqlite3.connect(out/'scores.sqlite3',timeout=3)
    db.execute('PRAGMA journal_mode=WAL')
    db.execute('PRAGMA synchronous=FULL')
    db.execute('CREATE TABLE IF NOT EXISTS progress (pair_id TEXT, side TEXT, digest TEXT, total INTEGER, scored INTEGER, PRIMARY KEY(pair_id,side))')
    fields=', '.join('"'+k+'" '+('TEXT' if k in ('voice','role') else 'INTEGER' if k in COLS[:7] else 'REAL')+' NOT NULL' for k in COLS)
    db.execute(f'CREATE TABLE IF NOT EXISTS scores (pair_id TEXT, side TEXT, {fields}, PRIMARY KEY(pair_id,side,"row"))')
    db.commit()
    return db


def snapshot(repo,pairs):
    paths={repo/'src/analyze/load.py',repo/'src/utils/config.py', repo/'data/interim'/pairs.iloc[0].topic/'pairs/final_pairs.csv'}
    for _,pair in pairs.iterrows():
        for side in ('channel','group'):
            path=Path(pair[side+'_file']); paths.add(path)
            admins=path.with_name(path.name.replace('.jsonl.gz','.admins.json'))
            if admins.exists(): paths.add(admins)
    return {str(p.relative_to(repo)):hash_file(p) for p in sorted(paths)}


def sample_digest(sample):
    h=hashlib.sha256()
    for r in sample.itertuples():
        h.update(json.dumps([str(r.chat_id),str(r.msg_id),str(r.voice),str(r.role),str(r.text)],ensure_ascii=False).encode()); h.update(b'\n')
    return h.hexdigest()


def status(out,db,plan,reason):
    progress={(r[0],r[1]):(r[2],r[3]) for r in db.execute('SELECT pair_id,side,total,scored FROM progress')}
    rows=[]; completed=0; done=0; total=0
    for pair in plan['pairs']:
        item={'pair':pair['pair'],'pair_id':pair['pair_id'],'channel':pair['channel'],'group':pair['group']}
        full=True; started=False
        for side in ('channel','group'):
            n=pair[side+'_total']; key=(pair['pair_id'],side); state=progress.get(key)
            if state and state[0]!=n: raise RuntimeError('Checkpoint count mismatch')
            k=state[1] if state else 0
            item[side+'_scored']=k; item[side+'_total']=n
            item[side+'_status']='done' if state is not None and k==n else 'partial' if k else 'pending'
            full &= item[side+'_status']=='done'; started |= state is not None
            done+=k; total+=n
        item['status']='complete' if full else 'in progress' if started else 'pending'
        completed+=int(full); rows.append(item)
    atomic_csv(pd.DataFrame(rows),out/'progress.csv')
    model_path=out/'model.json'; model=json.loads(model_path.read_text()) if model_path.exists() else {}
    lines=['# Conspiracy toxicity — full-corpus progress', '', f'Updated (UTC): {now()}',f'State: {reason}',f'Model: {MODEL} / {MODEL_FILE}',f'Model revision: {model.get("revision","not loaded")}',f'Source Git commit at plan creation: {plan["git_commit"]}',f'Configuration: no cap; {plan["config"]["window"]} window; {plan["config"]["long_mode"]} long-text mode; {plan["config"]["threads"]} threads; batch {plan["config"]["batch_size"]}.',f'Completed pairs: {completed}/{len(rows)}',f'Committed scores: {done}/{total} ({100*done/total if total else 0:.2f}%)','', 'Provisional: no human validation or language filtering; full-corpus sampling change requires team approval. No text or sender IDs in this log.','', '| Pair | Channel | Channel scored/eligible | Group | Group scored/eligible | Status |','|---|---|---:|---|---:|---|']
    for r in rows:
        # Numeric pair only is safe to share after repository privacy is verified; names included for team workflow.
        lines.append(f'| {r["pair"]:03d} | {r["channel"]} | {r["channel_scored"]}/{r["channel_total"]} | {r["group"]} | {r["group_scored"]}/{r["group_total"]} | {r["status"]} |')
    history_path=out/'sessions.json'
    if history_path.exists():
        history=json.loads(history_path.read_text(encoding='utf-8'))
        if history:
            last=history[-1]
            lines.extend(['','## Latest completed session',f'End (UTC): {last["ended_utc"]}',f'Reason: {last["reason"]}',f'New scores: {last["new_scores"]}',f'Elapsed hours: {last["wall_seconds"]/3600:.3f}'])
    path=out/'progress.md'; tmp=path.with_suffix('.tmp'); tmp.write_text('\n'.join(lines)+'\n',encoding='utf-8'); os.replace(tmp,path)
    return done,total,completed


def advance_side(db,out,plan,pid,side,sample,lens,args,deadline):
    digest=sample_digest(sample); n=len(sample)
    old=db.execute('SELECT digest,total,scored FROM progress WHERE pair_id=? AND side=?',(pid,side)).fetchone()
    if old:
        if old[:2]!=(digest,n): raise RuntimeError(f'Input changed: {pid} {side}')
        start=old[2]
    else:
        start=0
        with db: db.execute('INSERT INTO progress VALUES (?,?,?,?,?)',(pid,side,digest,n,0))
    if start==n: return True
    print(f'  {side}: resume {start}/{n}',flush=True)
    t=time.monotonic(); pending=[]; saved=start
    placeholders=','.join('?' for _ in range(len(COLS)+2))
    def flush():
        nonlocal saved
        if pending:
            with db:
                db.executemany(f'INSERT INTO scores VALUES ({placeholders})',pending)
                saved+=len(pending)
                db.execute('UPDATE progress SET scored=? WHERE pair_id=? AND side=?',(saved,pid,side))
            pending.clear()
            print(f'    {saved}/{n} | {(saved-start)/max(.001,time.monotonic()-t):.2f} msg/s',flush=True)
    try:
        for j in range(start,n,args.batch_size):
            if time.monotonic()>=deadline: flush(); return False
            batch=sample.iloc[j:j+args.batch_size]; p,m,l,w=lens.score(batch.text.tolist(),args.long_mode=='both')
            for i,r in enumerate(batch.itertuples()):
                pending.append((pid,side,j+i,str(r.voice),str(r.role),int(r.n_chars),int(l[i]),int(l[i]>LIMIT),int(w[i]),*[float(x) for x in p[i]],*[float(x) for x in m[i]]))
            if len(pending)>=128: flush()
        flush(); return True
    except KeyboardInterrupt:
        # Any already committed batch is durable; discard uncommitted partial batch.
        raise


def export(out,db,plan,args):
    done,total,n_pairs=status(out,db,plan,'snapshot')
    complete={(r[0],r[1]) for r in db.execute('SELECT pair_id,side FROM progress WHERE scored=total')}
    crows=[]; vrows=[]; prows=[]
    for p in plan['pairs']:
        pid=p['pair_id']
        if not all((pid,s) in complete for s in ('channel','group')): continue
        scores=[]
        for side in ('channel','group'):
            frame=pd.read_sql_query('SELECT * FROM scores WHERE pair_id=? AND side=? ORDER BY "row"',db,params=(pid,side)).drop(columns=['pair_id','side'])
            if len(frame)!=p[side+'_total']: raise RuntimeError('Score count mismatch')
            scores.append((pid,side,frame))
        c,v,pdf,_,_=summaries(scores,[],args); crows.append(c); vrows.append(v); prows.append(pdf)
    if prows:
        c=pd.concat(crows,ignore_index=True); v=pd.concat(vrows,ignore_index=True); p=pd.concat(prows,ignore_index=True); final=[]
        for (method,lab,th),g in p.groupby(['method','category','threshold'],sort=False):
            x=g.dropna(subset=['delta_pp']); d=x.delta_pp
            final.append(dict(method=method,category=lab,threshold=th,n_pairs=len(x),median_channel_pct=x.channel_pct.median(),median_group_pct=x.group_pct.median(),median_paired_delta_pp=d.median(),mean_paired_delta_pp=d.mean(),groups_higher=int(d.gt(0).sum()),channels_higher=int(d.lt(0).sum()),ties=int(d.eq(0).sum())))
        for name,frame in [('chat_statistics',c),('voice_statistics',v),('pair_statistics',p),('conspiracy_summary',pd.DataFrame(final))]: atomic_csv(frame,out/(name+'.csv'))
    return done,total,n_pairs


def main():
    parser=argparse.ArgumentParser(description='Full, resumable conspiracy toxicity analysis (no sampling cap)')
    parser.add_argument('--repo',type=Path,default=Path.cwd()); parser.add_argument('--topic',choices=['conspiracy'],default='conspiracy')
    parser.add_argument('--output-dir',type=Path,required=True); parser.add_argument('--hours',type=float,default=12)
    parser.add_argument('--window',choices=['repo','overlap'],default='overlap'); parser.add_argument('--long-mode',choices=['prefix','both'],default='both')
    parser.add_argument('--threads',type=int,default=4); parser.add_argument('--batch-size',type=int,default=8); parser.add_argument('--revision',default='main')
    parser.add_argument('--plan-only',action='store_true'); parser.add_argument('--status',action='store_true')
    a=parser.parse_args(); repo=a.repo.resolve(); out=a.output_dir.resolve()
    if out==repo or repo in out.parents: parser.error('Output must stay outside the repository')
    if min(a.hours,a.threads,a.batch_size)<=0: parser.error('Numeric settings must be positive')
    start=time.monotonic(); deadline=start+a.hours*3600
    out.mkdir(parents=True,exist_ok=True); plan_path=out/'plan.json'
    if a.status:
        if not plan_path.exists(): parser.error('No plan exists yet')
        plan=json.loads(plan_path.read_text(encoding='utf-8')); a.long_mode=plan['config']['long_mode']
        if not (out/'scores.sqlite3').exists(): parser.error('No checkpoint database')
        with open_db(out) as db:
            d,t,n=export(out,db,plan,a); status(out,db,plan,'manual status snapshot')
        print(f'{d}/{t} scored; {n}/{len(plan["pairs"])} complete. See progress.md'); return
    if not (repo/'src/analyze/load.py').exists(): parser.error('Run from repository root or use --repo')
    sys.path.insert(0,str(repo)); from src.analyze import load as loader
    pairs=loader.pairs(a.topic)
    if len(pairs)!=97 or not pairs.has_data.all() or pairs.pair_id.duplicated().any(): raise SystemExit('Expected 97 distinct valid pairs with both dumps; investigate any change.')
    config=dict(topic=a.topic,window=a.window,long_mode=a.long_mode,threads=a.threads,batch_size=a.batch_size,requested_revision=a.revision,max_tokens=LIMIT,stride=STRIDE,cap=None,script_sha256=hash_file(Path(__file__)))
    print('Checking exact input files...',flush=True); sources=snapshot(repo,pairs)
    if plan_path.exists():
        plan=json.loads(plan_path.read_text(encoding='utf-8'))
        if plan['config']!=config or plan['sources']!=sources or [x['pair_id'] for x in plan['pairs']]!=pairs.pair_id.tolist(): raise SystemExit('Inputs/configuration changed. Restore original files/settings or use a new output directory; no mixed results.')
    else:
        if (out/'scores.sqlite3').exists() or (out/'model.json').exists(): raise SystemExit('Unexpected existing checkpoints without plan; use a new directory')
        meta=[]; entries=[]
        try: commit=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
        except (OSError,subprocess.CalledProcessError): commit='unknown'
        for i,(_,pair) in enumerate(pairs.iterrows(),1):
            samples,md=prepare(loader,pair,a); meta.extend(md)
            entry=dict(pair=i,pair_id=pair.pair_id,channel=pair.channel,group=pair.group,channel_total=len(samples['channel']),group_total=len(samples['group'])); entries.append(entry)
            print(f'Plan {i}/97: {pair.channel} {entry["channel_total"]} | {pair.group} {entry["group_total"]}',flush=True)
        plan=dict(config=config,sources=sources,pairs=entries,git_commit=commit,created_utc=now()); atomic_csv(pd.DataFrame(meta),out/'sampling.csv'); atomic_json(plan,plan_path)
    db=open_db(out); before,total,completed=status(out,db,plan,'ready')
    print(f'Plan: {total} eligible messages; {before} already scored; {completed}/97 pairs complete.',flush=True)
    if a.plan_only: db.close(); return
    model_path=out/'model.json'; previous=json.loads(model_path.read_text()) if model_path.exists() else None
    reason='session ended'; lens=None
    try:
        if completed==97: reason='all pairs complete'
        else:
            lens=Lens(previous['revision'] if previous else a.revision,a.threads,a.batch_size)
            model=dict(revision=lens.revision,model_sha256=lens.model_sha,model=MODEL,model_file=MODEL_FILE)
            if previous and previous!=model: raise RuntimeError('Model change detected; cannot resume')
            atomic_json(model,model_path)
            for i,(_,pair) in enumerate(pairs.iterrows(),1):
                if time.monotonic()>=deadline: reason='session time budget reached'; break
                complete=db.execute('SELECT COUNT(*) FROM progress WHERE pair_id=? AND total=scored',(pair.pair_id,)).fetchone()[0]
                if complete==2: continue
                print(f'Pair {i}/97: {pair.channel} -> {pair.group}',flush=True)
                samples,_=prepare(loader,pair,a)
                entry=plan['pairs'][i-1]
                if any(len(samples[s])!=entry[s+'_total'] for s in ('channel','group')): raise RuntimeError('Plan counts changed')
                if not all(advance_side(db,out,plan,pair.pair_id,side,samples[side],lens,a,deadline) for side in ('channel','group')):
                    reason='session time budget reached'; break
                status(out,db,plan,'running; last pair completed')
            else: reason='all pairs complete'
    except KeyboardInterrupt: reason='interrupted by user; committed scores retained'
    except Exception:
        reason='error; committed scores retained'; raise
    finally:
        try:
            d,t,n=export(out,db,plan,a)
            meta_path=out/'sessions.json'; history=json.loads(meta_path.read_text()) if meta_path.exists() else []
            history.append(dict(ended_utc=now(),reason=reason,wall_seconds=time.monotonic()-start,new_scores=d-before,total_scored=d,eligible=t,completed_pairs=n)); atomic_json(history,meta_path); status(out,db,plan,reason)
            print(f'{reason}: {d}/{t} messages, {n}/97 pairs; {d-before} new. See progress.md.',flush=True)
        finally: db.close()

if __name__=='__main__': main()

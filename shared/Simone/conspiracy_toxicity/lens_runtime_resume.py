#!/usr/bin/env python3
"""Resume the original toxicity pipeline, optionally using eight ONNX threads.
Run with the original script beside this file. No checkpoint/config edits.
Never run alongside another toxicity writer. Benchmark uses committed rows only.
"""
import argparse
import gc
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
import time
import numpy as np


def load_original(path):
    spec = importlib.util.spec_from_file_location('lens_original_runtime', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def compare(a, b):
    return dict(max_abs=float(np.max(np.abs(a-b))),
                disagreements={str(t):int(np.count_nonzero((a>=t)!=(b>=t)))
                               for t in (.3,.5,.7)})


def acceptable(c):
    return c['max_abs'] <= 1e-4 and not any(c['disagreements'].values())


def timed_scores(lens, texts, batch, chunks):
    # Warm-up separately; identical batch size and texts for both tests.
    lens.score(texts[:batch], chunks)
    start=time.perf_counter(); rows=[]
    for i in range(0,len(texts),batch):
        p,m,_,_=lens.score(texts[i:i+batch],chunks)
        rows.append(np.concatenate([p,m],axis=1))
    return np.concatenate(rows), time.perf_counter()-start


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--hours',type=float,default=24)
    parser.add_argument('--test-threads',type=int,default=8)
    parser.add_argument('--benchmark-messages',type=int,default=64)
    args=parser.parse_args(); out=args.output_dir.resolve(); repo=Path.cwd().resolve()
    if args.hours<=0 or args.test_threads<=0 or args.benchmark_messages<=0:
        parser.error('Positive settings required')
    original=Path(__file__).resolve().with_name('lens_pairs_full.py')
    plan=json.loads((out/'plan.json').read_text(encoding='utf-8'))
    cfg=plan['config']; mod=load_original(original)
    if mod.hash_file(original)!=cfg['script_sha256']:
        raise SystemExit('Original script hash mismatch; no changes made.')
    if cfg['long_mode']!='both' or cfg['threads']!=4 or cfg['batch_size']!=8:
        raise SystemExit('This launcher is intended for the original 4-thread, batch 8, both-mode experiment.')
    expected=json.loads((out/'model.json').read_text(encoding='utf-8'))
    OriginalLens=mod.Lens; event=None
    log=out/'runtime_benchmarks.json'
    sessionfile=out/'sessions.json'
    prior_sessions=len(json.loads(sessionfile.read_text(encoding='utf-8'))) if sessionfile.exists() else 0

    def log_event():
        history=json.loads(log.read_text(encoding='utf-8')) if log.exists() else []
        if history and history[-1].get('started_utc')==event['started_utc'] and history[-1].get('launcher_sha256')==event['launcher_sha256']:
            history[-1]=event
        else: history.append(event)
        mod.atomic_json(history,log)

    def select_lens(revision, threads, batch):
        nonlocal event
        from src.analyze import load as loader
        pairs=loader.pairs(cfg['topic'])
        # Read only. The original pipeline already verified source hashes.
        with sqlite3.connect((out/'scores.sqlite3').as_uri()+'?mode=ro',uri=True) as db:
            states={(r[0],r[1]):r[2:] for r in db.execute('SELECT pair_id,side,digest,total,scored FROM progress')}
            choice=None
            for entry in plan['pairs']:
                pid=entry['pair_id']
                for side in ('channel','group'):
                    state=states.get((pid,side))
                    if state and state[2]<state[1] and state[2]>=args.benchmark_messages:
                        choice=(pid,side,state); break
                if choice: break
            if not choice:
                print('No sufficiently large partial side for checkpoint benchmark; retaining original threads.',flush=True)
                return OriginalLens(revision,threads,batch)
            pid,side,(digest,total,scored)=choice
            pair=pairs.loc[pairs.pair_id.eq(pid)].iloc[0]
            samples,_=mod.prepare(loader,pair,argparse.Namespace(window=cfg['window']))
            sample=samples[side]
            if len(sample)!=total or mod.sample_digest(sample)!=digest:
                raise RuntimeError('Sample fingerprint mismatch; refusing to resume.')
            # Use recent committed rows. Align with original batch boundaries.
            count=max(batch,(args.benchmark_messages//batch)*batch)
            end=(scored//batch)*batch; start=end-count
            if start<0: raise RuntimeError('Not enough aligned committed rows.')
            cols=','.join('"'+s+'"' for s in mod.COLS[7:])
            rows=db.execute(f'SELECT "row",{cols} FROM scores WHERE pair_id=? AND side=? AND "row">=? AND "row"<? ORDER BY "row"',(pid,side,start,end)).fetchall()
            if [x[0] for x in rows]!=list(range(start,end)): raise RuntimeError('Missing benchmark rows.')
            stored=np.asarray([x[1:] for x in rows],dtype=float)
            texts=sample.iloc[start:end].text.tolist()
        # Compare against both the historical checkpoint and the original runtime.
        event=dict(started_utc=mod.now(),launcher_sha256=mod.hash_file(Path(__file__)),original_script_sha256=cfg['script_sha256'],pair_id=pid,side=side,benchmark_messages=len(texts),plan_threads=threads,test_threads=args.test_threads,batch_size=batch,first_unscored_row=scored,model_sha256=expected['model_sha256'],outcome='benchmark started')
        log_event()
        def check_model(lens):
            if lens.model_sha!=expected['model_sha256'] or lens.revision!=expected['revision']:
                raise RuntimeError('Model fingerprint mismatch.')
        print(f'Benchmark {len(texts)} committed messages: {threads} vs {args.test_threads} threads; no scores will be overwritten.',flush=True)
        base=OriginalLens(revision,threads,batch); check_model(base)
        s4,t4=timed_scores(base,texts,batch,True)
        event.update(baseline_msg_s=len(texts)/t4,baseline_vs_checkpoint=compare(s4,stored))
        print(f'Baseline: {len(texts)/t4:.2f} msg/s',flush=True)
        # Free the first ONNX session before opening another.
        del base; gc.collect()
        try:
            candidate=OriginalLens(revision,args.test_threads,batch); check_model(candidate)
            s8,t8=timed_scores(candidate,texts,batch,True)
            event.update(candidate_msg_s=len(texts)/t8,candidate_vs_checkpoint=compare(s8,stored),candidate_vs_baseline=compare(s8,s4),speedup=t4/t8)
            print(f'Candidate: {len(texts)/t8:.2f} msg/s; speedup {t4/t8:.2f}x',flush=True)
            if all(acceptable(event[k]) for k in ('baseline_vs_checkpoint','candidate_vs_checkpoint','candidate_vs_baseline')) and t4/t8>=1.10:
                event.update(effective_threads=args.test_threads,outcome='candidate accepted (local sample only)'); log_event()
                print(f'Resuming with {args.test_threads} threads. No stored scores changed.',flush=True)
                return candidate
            del candidate; gc.collect()
        except Exception as exc:
            event['candidate_error']=type(exc).__name__+': '+str(exc)
        event.update(effective_threads=threads,outcome='original runtime retained'); log_event()
        print('Candidate did not pass all checks or was not at least 10% faster; retaining original threads.',flush=True)
        base=OriginalLens(revision,threads,batch); check_model(base); return base

    mod.Lens=select_lens
    # Preserve the exact original CLI configuration, hashes, progress and row checks.
    sys.argv=[str(original),'--repo',str(repo),'--topic',cfg['topic'],'--output-dir',str(out),'--hours',str(args.hours),'--window',cfg['window'],'--long-mode',cfg['long_mode'],'--threads',str(cfg['threads']),'--batch-size',str(cfg['batch_size']),'--revision',cfg['requested_revision']]
    try:
        mod.main()
    finally:
        if event is not None and 'effective_threads' in event and sessionfile.exists():
            history=json.loads(sessionfile.read_text(encoding='utf-8'))
            if len(history)==prior_sessions+1:
                history[-1]['effective_threads']=event['effective_threads']
                history[-1]['runtime_benchmark']=log.name
                mod.atomic_json(history,sessionfile)
                event['session_ended_utc']=history[-1]['ended_utc']; log_event()
                # Original status displays the plan settings, so explicitly append runtime provenance.
                progress=out/'progress.md'
                if progress.exists():
                    p=progress.read_text(encoding='utf-8')
                    tmp=progress.with_suffix('.tmp'); tmp.write_text(p+f'\nRuntime override for latest session: {event["effective_threads"]} ONNX threads (plan: {cfg["threads"]}); see {log.name} and sessions.json.\n',encoding='utf-8'); tmp.replace(progress)


if __name__=='__main__': main()

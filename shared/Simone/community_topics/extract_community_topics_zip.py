#!/usr/bin/env python3
"""Export blinded, time-stratified community topic samples in 1–3 ZIP archives."""
import argparse
import csv
import hashlib
import json
import random
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path
from types import SimpleNamespace

PATTERNS = [
    ('[URL]', re.compile(r'(?i)\b(?:https?://|www\.|t\.me/|telegram\.me/|telegram\.dog/|tg://)\S+')),
    ('[EMAIL]', re.compile(r'(?i)\b[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}\b')),
    ('[HANDLE]', re.compile(r'(?<!\w)@[\w]{2,}')),
    ('[IP]', re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')),
    ('[PHONE]', re.compile(r'(?<!\w)\+?\d(?:[ ()\-]*\d){7,}(?!\w)')),
]


def redact(text, limit):
    text = str(text).strip()
    for replacement, pattern in PATTERNS:
        text = pattern.sub(replacement, text)
    if len(text) <= limit:
        return text, False
    sep = '\n[TEXT SHORTENED]\n'
    remaining = limit - len(sep)
    head = remaining * 2 // 3
    return text[:head] + sep + text[-(remaining-head):], True


def select_rows(df, cap, seed):
    """One random row per equal-size chronological rank stratum; no toxicity selection."""
    df = df.sort_values(['date', 'chat_id', 'msg_id'], kind='stable')
    n = len(df)
    k = min(n, cap)
    if k == 0:
        return df.iloc[:0]
    if k == n:
        return df
    rng = random.Random(seed)
    indices = [rng.randrange(i*n//k, (i+1)*n//k) for i in range(k)]
    return df.iloc[indices]


def stable_seed(seed, pid, side):
    return int.from_bytes(hashlib.sha256(f'{seed}:{pid}:{side}'.encode()).digest()[:8], 'big')


def write_json(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def package_batches(staging, upload, archives, total_pairs, total_sample, seed, max_chars):
    """Package only the anonymized JSON batches; never include local mapping or raw files."""
    batches = sorted(staging.glob('topic_batch_*.json'))
    if not batches:
        raise RuntimeError('No batches to package.')
    if archives > len(batches):
        raise ValueError('More requested archives than batches; use fewer archives or a larger pilot.')
    outputs = []
    for i in range(archives):
        start = i * len(batches) // archives
        end = (i + 1) * len(batches) // archives
        members = batches[start:end]
        name = 'community_topics.zip' if archives == 1 else f'community_topics_{i+1:02d}_of_{archives:02d}.zip'
        path = upload / name
        manifest = {'format_version': 1, 'archive_index': i+1, 'archive_count': archives,
                    'total_pairs_all_archives': total_pairs, 'sampled_messages_all_archives': total_sample,
                    'seed': seed, 'max_chars': max_chars,
                    'method': 'chronological rank-stratified random sample; no toxicity selection; original language retained',
                    'batches': [f.name for f in members],
                    'privacy': 'Regex masking only; review samples for residual personal information before upload.'}
        with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
            for f in members:
                z.write(f, arcname=f.name)
            z.writestr('archive_manifest.json', json.dumps(manifest, ensure_ascii=False, indent=2)+'\n')
        with zipfile.ZipFile(path) as z:
            if z.testzip() is not None or set(z.namelist()) != {f.name for f in members} | {'archive_manifest.json'}:
                raise RuntimeError(f'ZIP integrity check failed: {name}')
        outputs.append(path)
    return outputs


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo', type=Path, default=Path.cwd())
    p.add_argument('--plan', type=Path, required=True, help='Existing full-corpus plan.json')
    p.add_argument('--output-dir', type=Path, required=True)
    p.add_argument('--channel-sample', type=int, default=100)
    p.add_argument('--group-sample', type=int, default=200)
    p.add_argument('--pairs-per-file', type=int, default=5)
    p.add_argument('--archives', type=int, choices=(1,2,3), default=1, help='Number of upload ZIP files (default 1)')
    p.add_argument('--max-chars', type=int, default=1200)
    p.add_argument('--seed', type=int, default=42)
    p.add_argument('--limit-pairs', type=int, default=None, help='Optional first N pairs for a pilot')
    a = p.parse_args()
    if min(a.channel_sample,a.group_sample,a.pairs_per_file) < 1 or a.max_chars < 100 or (a.limit_pairs is not None and a.limit_pairs < 1):
        p.error('Positive sample sizes, batch size and pilot size required; max-chars >=100')
    repo, out = a.repo.resolve(), a.output_dir.resolve()
    if out.exists():
        p.error('Output directory already exists. Choose a fresh directory to avoid mixing exports.')
    if out == repo or repo in out.parents:
        p.error('Output must be outside the Git repository (contains sampled text).')
    if not (repo/'src/analyze/load.py').is_file():
        p.error('Run from the Git repository root or use --repo.')
    try:
        import lens_pairs_full as full
    except ImportError as e:
        raise SystemExit('Place this script beside the original lens_pairs_full.py and use the existing .venv. '+str(e))
    plan = json.loads(a.plan.read_text(encoding='utf-8-sig'))
    cfg = plan['config']
    if cfg['topic'] != 'conspiracy' or cfg['window'] != 'overlap' or cfg['cap'] is not None:
        raise SystemExit('Expected the existing conspiracy overlap/no-cap plan.')
    if full.hash_file(Path(full.__file__)) != cfg['script_sha256']:
        raise SystemExit('Original analysis script hash differs from plan. Restore the exact script.')
    sys.path.insert(0, str(repo))
    from src.analyze import load as loader
    pairs = loader.pairs('conspiracy')
    entries = plan['pairs']
    if len(pairs) != 97 or len(entries) != 97 or not pairs.has_data.all() or pairs.pair_id.duplicated().any() or pairs.pair_id.tolist() != [x['pair_id'] for x in entries]:
        raise SystemExit('Pair list or dump availability differs from the original plan.')
    if any(x['pair'] != i for i,x in enumerate(entries,1)):
        raise SystemExit('Unexpected plan numbering.')
    print('Checking original source hashes...', flush=True)
    norm = lambda d: {k.replace('\\','/'):v for k,v in d.items()}
    if norm(full.snapshot(repo,pairs)) != norm(plan['sources']):
        raise SystemExit('Raw inputs or loader changed since the toxicity plan. Do not mix datasets.')
    args = SimpleNamespace(window=cfg['window'])
    with (repo/'data/interim/conspiracy/pairs/final_pairs.csv').open(encoding='utf-8-sig',newline='') as f:
        originals = {r['channel'].strip().lstrip('@').lower():r.get('topic','') for r in csv.DictReader(f) if r.get('final','valida').strip() in ('','valida')}
    out.parent.mkdir(parents=True,exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix='.topic_export_',dir=out.parent))
    upload = tmp/'upload'; upload.mkdir()
    staging = tmp/'review_samples'; staging.mkdir()
    private = tmp/'local_only'; private.mkdir()
    batch, mapping, counts = [], [], []
    total_pairs = min(len(pairs), a.limit_pairs or len(pairs))
    total_sample = 0
    try:
        for i,(_,pair) in enumerate(pairs.iloc[:total_pairs].iterrows(),1):
            data,_ = full.prepare(loader,pair,args)
            entry = entries[i-1]
            label = f'P{i:03d}'
            record = {'pair':label, 'sides':{}}
            mapping.append({'pair':label,'pair_id':pair.pair_id,'channel':pair.channel,'group':pair.group,'original_topic':originals.get(pair.channel,'')})
            for side,cap in [('channel',a.channel_sample),('group',a.group_sample)]:
                df=data[side]
                if len(df) != entry[side+'_total']:
                    raise RuntimeError(f'{label}/{side}: eligible count changed.')
                selected=select_rows(df,cap,stable_seed(a.seed,pair.pair_id,side))
                texts=[]; shortened=0
                for t in selected.text:
                    text, truncated=redact(t,a.max_chars)
                    texts.append(text); shortened+=int(truncated)
                n=len(texts); total_sample+=n
                record['sides'][side]={'eligible':len(df),'sampled':n,'shortened':shortened,'messages':texts}
                counts.append({'pair':label,'side':side,'eligible':len(df),'sampled':n,'shortened':shortened})
            batch.append(record)
            print(f'{i}/{total_pairs}: {label} | channel {len(record["sides"]["channel"]["messages"])} | group {len(record["sides"]["group"]["messages"])}',flush=True)
            if len(batch)==a.pairs_per_file or i==total_pairs:
                num=(i-1)//a.pairs_per_file+1
                write_json(staging/f'topic_batch_{num:02d}.json',{'method':'chronological rank-stratified random sample; no toxicity selection; regex redaction; original language retained','seed':a.seed,'max_chars':a.max_chars,'pairs':batch})
                batch=[]
        for filename, rows in [('pair_mapping.csv',mapping),('sample_counts.csv',counts)]:
            with (private/filename).open('w',encoding='utf-8-sig',newline='') as f:
                w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
        write_json(private/'manifest.json',{'topic':'conspiracy','source_plan_sha256':full.hash_file(a.plan),'source_git_commit':plan['git_commit'],'seed':a.seed,'channel_cap':a.channel_sample,'group_cap':a.group_sample,'pairs_per_file':a.pairs_per_file,'archives':a.archives,'max_chars':a.max_chars,'pairs':total_pairs,'sampled_messages':total_sample,'sampling':'one random message per equal-sized chronological rank stratum; sample all if below cap','privacy':'No sender/chat/message IDs or toxicity scores in upload batches. Regex masking is not complete anonymization. Review sampled text before sharing.'})
        files = package_batches(staging, upload, a.archives, total_pairs, total_sample, a.seed, a.max_chars)
        # Keep extracted samples for local privacy review; upload only the ZIP(s).
        sizes = [(f.name, f.stat().st_size) for f in files]
        tmp.rename(out)
    except BaseException:
        shutil.rmtree(tmp,ignore_errors=True)
        raise
    print(f'Done: {total_pairs} pairs, {total_sample} messages, {len(sizes)} ZIP file(s).', flush=True)
    for name, size in sizes:
        print(f'  {out / "upload" / name}  ({size / 1024**2:.2f} MiB)', flush=True)
    print('Review the sampled text in review_samples before sharing. If you edit a sample, rebuild its ZIP locally before upload. Never upload local_only or raw dumps.', flush=True)


if __name__=='__main__':
    main()

"""Documented refinement of 66 'Other specific topic' diagnostic labels.

This is a SINGLE AI-ASSISTED exploratory recoding of the existing 240-item
cluster-balanced sample, not an independent human annotation or validation.
It changes only the THEME_LABEL_V3 for 'Other specific topic'; all original
fields and labels are retained for traceability.
"""
import csv
from collections import Counter
from pathlib import Path
import argparse

# Explicit item-ID coding; based on original visible message and existing NOTES.
THEME_BY_ITEM = {
    # Platform support, access, account status, admin or group operations
    "Platform/community operations": "0001 0016 0018 0066 0099 0113 0117 0120 0127 0152 0157 0188 0202 0223 0240",
    # Applications, AI, software, computing and privacy
    "Technology/software/privacy": "0032 0049 0050 0058 0070 0090 0091 0115 0140 0144 0156 0178 0181 0196",
    # Recruiting, commercial service marketing, partnerships, labor and trade
    "Work/commerce/services": "0020 0024 0046 0089 0094 0101 0164 0180 0185 0191 0236",
    # Media, music, video, books, recreational games and arts
    "Media/arts/gaming": "0003 0047 0063 0095 0098 0129 0151 0173 0211 0217 0232",
    "Daily life/personal": "0067 0071 0118 0134 0138 0206",
    "Science/environment": "0014 0017 0201 0210",
    "History/culture (non-conspiratorial)": "0132 0155 0203",
    # Uncertain subject despite named words
    "Unclear": "0109",
    # Specific weapon mechanics not matched to a major category
    "Other specific topic": "0135",
}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--labels', type=Path, default=Path('point4_stage3_exploratory_labels.csv'))
    p.add_argument('--key', type=Path, default=Path('point4_annotation_key.csv'))
    p.add_argument('--output-dir', type=Path, default=Path('point4_stage4_ready'))
    a=p.parse_args()
    mapping={}
    for theme, items in THEME_BY_ITEM.items():
        for n in items.split():
            key=f'P4-{n}'
            if key in mapping:raise RuntimeError(f'Duplicate manual mapping {key}')
            mapping[key]=theme
    with a.labels.open(encoding='utf-8-sig',newline='') as f:
        labels=list(csv.DictReader(f))
    with a.key.open(encoding='utf-8-sig',newline='') as f:
        meta={r['ITEM_ID']:r for r in csv.DictReader(f)}
    original_other={r['ITEM_ID'] for r in labels if r['THEME_LABEL']=='Other specific topic'}
    if mapping.keys()!=original_other:
        raise RuntimeError(f'Manual mapping mismatch. Missing {sorted(original_other - mapping.keys())}, unexpected {sorted(mapping.keys()-original_other)}')
    a.output_dir.mkdir(parents=True,exist_ok=True)
    out=a.output_dir/'stage3_revised_240_labels.csv'
    fields=['ITEM_ID','topic','cluster_id','pair_id','group_msg_id','FUNCTION_LABEL','THEME_LABEL_ORIGINAL','THEME_LABEL_V3','INTERPRETABLE','PROMOTIONAL','NOTES','REVISION_ORIGIN']
    count=Counter()
    with out.open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields)
        writer.writeheader()
        for r in labels:
            data=meta[r['ITEM_ID']]
            theme=mapping.get(r['ITEM_ID'],r['THEME_LABEL'])
            if r['THEME_LABEL']=='Other specific topic' and r['ITEM_ID'] not in mapping:raise AssertionError('mapping')
            writer.writerow({'ITEM_ID':r['ITEM_ID'],'topic':data['topic'],'cluster_id':data['cluster_id'],'pair_id':data['pair_id'],'group_msg_id':data['group_msg_id'],'FUNCTION_LABEL':r['FUNCTION_LABEL'],'THEME_LABEL_ORIGINAL':r['THEME_LABEL'],'THEME_LABEL_V3':theme,'INTERPRETABLE':r['INTERPRETABLE'],'PROMOTIONAL':r['PROMOTIONAL'],'NOTES':r.get('NOTES',''),'REVISION_ORIGIN':'reclassified from Other specific topic' if r['ITEM_ID'] in mapping else 'unchanged'})
            count[(data['topic'],theme)]+=1
    if len(labels)!=240:raise RuntimeError('Expected original 240 labels')
    summary=a.output_dir/'stage3_revised_diagnostic_counts.csv'
    with summary.open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.writer(f);writer.writerow(['topic','theme_label_v3','count_in_nonprobability_diagnostic_sample'])
        for (topic,theme), n in sorted(count.items()):writer.writerow([topic,theme,n])
    print('Revised', len(original_other), 'Other specific topic labels within 240; wrote',out)
    print('Still Other specific topic:',sum(n for (t,theme),n in count.items() if theme=='Other specific topic'))

if __name__=='__main__': main()

#!/usr/bin/env python3
"""H3 2026-11-12: saved project evidence and read-only findings -> MD/JSON handoff.
Assignment all-project-prefix-and-cross-review. No execution beyond local reads.
"""
import argparse, hashlib, json
from pathlib import Path
W=Path(__file__).resolve().parents[2]; E=W.parent; S=E/'scratch-h3-packet-builder-20261112'
H=E/'codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/codex-h3-all-project-prefix-and-cross-review-20261112'
p=argparse.ArgumentParser(); p.add_argument('--cohort',action='append',required=True); p.add_argument('--review',type=Path); a=p.parse_args()
def pin(path): return {'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bytes':path.stat().st_size}
rows={}; history=[]
for name in a.cohort:
    root=S/'tests'/name
    for path in sorted(root.rglob('project-evidence.json')):
        row=json.loads(path.read_bytes()); row['evidence']=pin(path); rows[row['project']]=row; history.append(row)
review=json.loads(a.review.read_bytes()) if a.review else {'status':'Part B not yet started','findings':[]}
value={'scope':'OFFLINE PREFIX AND READ-ONLY REVIEW; NO AUTHORIZATION','projects':list(rows.values()),'history':history,'review':review}
lines=['# Helper 3 all-project prefix and cross-review — 2026-11-12','']
passed=[p for p,r in rows.items() if r['builder']['returncode']==2]
refused={p:r['builder']['status'].get('message') for p,r in rows.items() if r['builder']['returncode']!=2}
lines+=['Prefix accepted: '+(', '.join(passed) or 'none yet')+'. Refusals: '+(json.dumps(refused) if refused else 'none')+'. Accepted prefixes stop before owner-approved runtime and D117 authorization; no registration or launch authority is issued.','']
lines+=['| Project | Bundle bytes | Lines | Source documents | Chunks | Largest chunk bytes / lines | Max chunk lines | Oversize | Bytes / CHORUS | Chunks / CHORUS |','|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
base=rows.get('CHORUS')
for project,row in rows.items():
    br=row['bundle']['bytes']/base['bundle']['bytes'] if base else None; cr=row['chunk_count']/base['chunk_count'] if base else None
    row['ratios_to_chorus']={'bundle_bytes':br,'chunk_count':cr}
    lines.append(f"| {project} | {row['bundle']['bytes']} | {row['bundle_lines']} | {row['source_documents']} | {row['chunk_count']} | {row['largest_chunk_bytes']} / {row['largest_byte_chunk_lines']} | {row['maximum_chunk_lines']} | {len(row['oversize_chunks'])} | {br if br is not None else 'pending'} | {cr if cr is not None else 'pending'} |")
counts={grade:sum(f['grade']==grade for f in review['findings']) for grade in ('P1','P2','P3')}
lines+=['','Review findings: '+', '.join(f'{n} {g}' for g,n in counts.items())+'. '+review['status']+'.','']
for finding in review['findings']:
    lines += [f"- {finding['id']} {finding['grade']}: {finding['title']}"]
lines+=['','## Project readbacks','']
for project,row in rows.items():
    lines+=[f'### {project}', '',f"Evidence: `{row['evidence']['path']}` SHA-256 `{row['evidence']['sha256']}`.",f"Profile `{row['profile']}`; source_dir `{row['source_dir']}`; {row['manifest_sources']} manifest source entries.",'Scope: '+json.dumps(row['scope'],sort_keys=True)+'.','Omission context: '+json.dumps(row['omission_context'],sort_keys=True)+'.','']
    for check in row['checks']:
        lines += ['Command: `'+ ' '.join(check['command'])+'`; exit '+str(check['returncode'])+'.','```text',check['stdout']+check['stderr'],'```','']
if a.review:
    lines += ['## Adversarial review','']
    for finding in review['findings']:
        lines += [f"### {finding['id']} {finding['grade']}: {finding['title']}",'',finding['location'],finding['scenario'],'Smallest fix: '+finding['fix'],'Evidence: '+finding.get('evidence','static source trace'), '']
    lines += [review.get('details_markdown','')]
else: lines += ['First-project interim handoff; remaining projects and Part B pending.']
text='\n'.join(lines)+'\n'; raw=json.dumps(value,indent=2)+'\n'
assert chr(64) not in text and chr(64) not in raw
H.with_suffix('.md').write_text(text); H.with_suffix('.json').write_text(raw)
for path in [H.with_suffix('.md'),H.with_suffix('.json')]: print(json.dumps(pin(path)))

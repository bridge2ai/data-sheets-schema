#!/usr/bin/env python3
"""Issue 6094: inspect only four completed saved runs for timing fields.
Inputs preserved artifacts; stdout bounded structure, no execution or probes.
2026-11-13. Filesystem enumeration includes hidden and ignored entries.
"""
from pathlib import Path
import json
R=Path(__file__).resolve().parents[2];E=R.parent
RUNS=[E/'scratch-h2-helper-cache-20261112/tests'/name for name in ('public-correction-cache','public-omissions-cache')]
RUNS += [E/'scratch-native-main-integration-20261112/tests'/name for name in ('h1-ci-8760-public-canary-20261113','h1-ci-current-pending-public-20261113')]
def brief(value):
 if isinstance(value,dict):return {k:(v if isinstance(v,(int,float,bool,type(None))) else str(v)[:180]) for k,v in value.items()}
 return str(value)[:500]
for root in RUNS:
 print('\nRUN',root)
 print('root files',[p.name for p in root.iterdir() if p.is_file()])
 for actual in sorted((root/'cases').rglob('actual-result.json')):
  case=actual.parent;print('CASE',case)
  print('attempt files',[str(p.relative_to(case/'native-attempt')) for p in (case/'native-attempt').rglob('*') if p.is_file() and p.parent.name!='helper-cache'])
  for name in ('native-attempt/started.json','native-attempt/runtime-observation.json','native-attempt/transcript.jsonl','native-attempt/control.jsonl','fresh-attempt/stages/journal.json'):
   p=case/name
   if not p.exists():print('MISSING',name);continue
   print('FILE',name,'bytes',p.stat().st_size)
   if p.suffix=='.jsonl':
    lines=p.read_text().splitlines();print('lines',len(lines))
    for line in lines[:2]+lines[-2:]:print(brief(json.loads(line)))
   else:
    value=json.loads(p.read_bytes());print(brief(value))
    if name.endswith('journal.json'):
     for row in value['records'][:1]:print('STAGE RECORD',brief(json.loads(Path(row['path']).read_bytes())))
 print('host matches',[str(p.relative_to(root)) for p in root.rglob('*host*.json') if 'site-packages' not in p.parts])

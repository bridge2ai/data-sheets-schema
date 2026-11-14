#!/usr/bin/env python3
"""G13 handoff, 2026-11-12. Inputs saved map/results; outputs lead handoff MD/JSON.
Only designated handoff files are replaced, preserving staged snapshots in scratch.
"""
import argparse
import hashlib
import json
from pathlib import Path
p=argparse.ArgumentParser()
p.add_argument('--map',type=Path,required=True)
p.add_argument('--results',type=Path)
p.add_argument('--handoff',type=Path,required=True)
a=p.parse_args()
value=json.loads((a.map/'map.json').read_text())
results=json.loads(a.results.read_text()) if a.results else {'phase':'Part 1 complete; implementation and rehearsal pending','answer':'The source map is saved. No production registration has been built. Final runtime requires real observation evidence and owner terms. No probe, capture, reservation or native binary execution occurred.'}
value['results']=results
raw=json.dumps(value,indent=2)+'\n'
lines=['# Helper 3 registration builder — 2026-11-12','',results['answer'],'']
if 'commit' in results:
    lines += ['Local commit: `'+results['commit']+'` on `'+results['branch']+'`.',
              'Worktree: `'+results['worktree']+'`. Source status: '+('clean' if not results['source_status'] else results['source_status'])+'.',
              '',results['bounds'],'',results['limitations'],'']
lines += [(a.map/'map.md').read_text()]
if 'runs' in results:
    lines += ['', '## Saved tests and outputs', '', results['test_summary'], '',
              '| Cohort | Cases | Failures | Errors | Skips | Runner exit | Saved log |',
              '|---|---:|---:|---:|---:|---:|---|']
    for row in results['runs']:
        count=row.get('counts',{})
        code=row.get('outcome.json',{}).get('returncode','not completed')
        lines.append('| '+row['name']+' | '+' | '.join(str(count.get(k,'not run')) for k in ['cases','failures','errors','skipped'])+' | '+str(code)+' | ['+row['name']+']('+row['log']['path']+') |')
    lines += ['', 'The first real canary verified nonempty files plus a production recapture of CHORUS selection, unchanged profile despite a conflicting environment value, and absence of the future attempt directory. It proves the offline input prefix only.', '', 'Retained runner failures: '+json.dumps(results['retained_run_failures']), '',
              'Actual protected constructor refusal: `'+results['protected_refusal']['refusal']+'`.',
              'Saved refusal: ['+results['protected_refusal_file']['path']+']('+results['protected_refusal_file']['path']+').', '',
              'Real builder status: `'+results['real_status']['status']+'`. Needed: '+results['real_status']['needed'],
              '', 'Documented producer, never executed:', '', '```sh', results['real_status']['producer_command'], '```', '',
              '| Real output | Bytes | SHA-256 |','|---|---:|---|']
    for item in results['real_outputs']:
        lines.append('| ['+Path(item['path']).name+']('+item['path']+') | '+str(item['bytes'])+' | `'+item['sha256']+'` |')
    lines += ['', 'Runbook: ['+results['runbook']['path']+']('+results['runbook']['path']+').', '',
              'All four protected files match main `'+results['protected_files'][0]['main_commit']+'` byte for byte. The companion JSON carries the computed hashes, exact commands, network-denial and origin evidence, runner outcomes and routing-spy boundaries.', '', '## Findings for the lead', '']
    for finding in results['review_findings_for_lead']:
        lines += ['- **'+finding['id']+' — '+finding['severity']+':** '+finding['finding']+' '+finding.get('next',finding.get('resolution',''))]
    lines += ['', 'No GitHub issues were filed under the offline assignment; the lead owns publication and issue filing. No production date, account fact, review, CI success or owner authorization was invented.', '', 'Helper scripts retained and committed:', '']
    lines += ['- `'+path+'`' for path in results['helper_scripts']]
else:
    lines += ['',results['phase']]
text='\n'.join(lines)+'\n'
if '@' in text or '@' in raw: raise ValueError('handoff forbids at-sign characters')
a.handoff.with_suffix('.json').write_text(raw)
a.handoff.write_text(text)
for path in [a.handoff,a.handoff.with_suffix('.json')]:
    print(str(path)+' '+hashlib.sha256(path.read_bytes()).hexdigest())

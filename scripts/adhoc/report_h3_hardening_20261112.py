#!/usr/bin/env python3
"""2026-11-12 #5989/#5990/#5991: local commits and JUnit -> lead handoff.
No external writes, source mutations or launch. First and final reports retained.
"""
import argparse,hashlib,json,subprocess,xml.etree.ElementTree as ET
from pathlib import Path
W=Path(__file__).resolve().parents[2]; E=W.parent; S=E/'scratch-h3-launch-hardening-20261112'
H=E/'codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/codex-h3-launch-sequence-hardening-20261112'
p=argparse.ArgumentParser(); p.add_argument('--final',action='store_true'); a=p.parse_args()
def git(*args):return subprocess.check_output(['/usr/bin/git','-C',str(W),*args]).decode().strip()
def pin(p):return {'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}
commits=[{'commit':c,'subject':git('show','-s','--format=%s',c),'files':git('diff-tree','--no-commit-id','--name-only','-r',c).splitlines()} for c in git('rev-list','--reverse','0fc003a86081891abbe8e130ac760c01da06423e..HEAD').splitlines()]
cohorts=[]
for root in sorted((S/'tests').iterdir()):
    if not (root/'pytest.xml').exists() or not (root/'outcome.json').exists():continue
    xml=ET.parse(root/'pytest.xml'); outcome=json.loads((root/'outcome.json').read_bytes())
    cohorts.append({'name':root.name,'cases':len(xml.findall('.//testcase')),'failures':len(xml.findall('.//failure')),'errors':len(xml.findall('.//error')),'returncode':outcome['returncode'],'cleanup_verified':outcome['cleanup_verified'],'junit':pin(root/'pytest.xml'),'log':pin(root/'pytest.log'),'outcome':pin(root/'outcome.json')})
value={'phase':'final' if a.final else 'first repair committed; remaining repairs pending','commits':commits,'cohorts':cohorts,'registered_document_versions_changed':False,'scope':'Offline synthetic engineering tests only; no native executable, real capture or attempt reservation; no push or GitHub write.'}
lines=['# Helper 3 launch-sequence hardening — 2026-11-12','',value['phase']+'. No registered-document kind/version changed.','']
for c in commits:lines += ['- `'+c['commit']+'`: '+c['subject']+'. Files: '+', '.join('`'+f+'`' for f in c['files'])+'.']
lines+=['','| Cohort | Cases | Failures | Errors | Exit | Cleanup |','|---|---:|---:|---:|---:|---|']
for c in cohorts: lines += [f"| {c['name']} | {c['cases']} | {c['failures']} | {c['errors']} | {c['returncode']} | {c['cleanup_verified']} |"]
if a.final:
    extra=json.loads((S/'final-details.json').read_bytes()); value.update(extra); lines+=['',extra['details_markdown']]
else:
    lines+=['','Direction claims are registration-scoped and independent of packet path. The recorded direction UTC instant is the identity within that registration; equivalent fractional spellings share a claim. A refreshed host confirmation cannot renew it. Owner starts retain distinct records and remain repeatable. Synthetic claims used by tests are not capture/word/attempt reservations. The load-once entry and child input binding are pending; no trust claim is made for them yet.']
raw=json.dumps(value,indent=2)+'\n'; text='\n'.join(lines)+'\n'; assert chr(64) not in raw+text
H.with_suffix('.json').write_text(raw); H.with_suffix('.md').write_text(text)
for path in [H.with_suffix('.md'),H.with_suffix('.json')]:print(json.dumps(pin(path)))

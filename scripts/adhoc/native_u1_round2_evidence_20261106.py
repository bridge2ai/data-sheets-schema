"""#4354 U1 2026-11-06: verify final packet/evidence identities without edits.
Inputs: scratch validation logs, M7/U1 trees and four proposals. Outputs: evidence
JSON in the unprotected packet directory. Does not modify protected artifacts.
"""
import collections
import json
import re
from native_u1_round2_20261106 import ROOT, SCRATCH, COMPOSED, BASE, HEAD, OUT, SHARED, SIDECAR, CHECKER, PINS, sha, run

def identity(path):
    raw=path.read_bytes()
    return dict(path=str(path),bytes=len(raw),sha256=sha(raw))

protected=[]
for name in (SHARED,SIDECAR,CHECKER,PINS):
    raw=(ROOT/name).read_bytes()
    assert raw==run(['git','show',BASE+':'+name])
    protected.append(identity(ROOT/name))
packets=[]
for name in ('shared_generation','api_runner_companion','canonical_hashes','run_spec_boundary_contracts'):
    meta=json.loads((OUT/(name+'.json')).read_text())
    assert sha((ROOT/meta['target']).read_bytes())==meta['preimage_sha256']
    assert sha((COMPOSED/meta['target']).read_bytes())==meta['postimage_sha256']
    assert sha((OUT/(name+'.patch')).read_bytes())==meta['patch_sha256']
    packets.append(meta)
run(['git','apply','--check',*[str(OUT/(n+'.patch')) for n in ('shared_generation','api_runner_companion','canonical_hashes','run_spec_boundary_contracts')]])
sidecar=json.loads((COMPOSED/SIDECAR).read_text()); before=json.loads((ROOT/SIDECAR).read_text())
for a,b in zip(before['contracts'],sidecar['contracts']):
    assert {k:v for k,v in a.items() if not k.startswith('function_')}=={k:v for k,v in b.items() if not k.startswith('function_')}
assert sidecar['producer_sha256']==sha((ROOT/'scripts/adhoc/native_u1_round2_20261106.py').read_bytes())
assert (ROOT/CHECKER).read_bytes()==(COMPOSED/CHECKER).read_bytes()
for path in ('tests/test_native_shared_render.py','tests/test_native_u1_selector_refusals.py'):
    assert (ROOT/path).read_bytes()==(COMPOSED/path).read_bytes()
comparison=None
scan=SCRATCH/'r2-scanner.json'
if scan.exists():
    prior=json.loads((SCRATCH/'scanner-before.json').read_text())
    current=json.loads(scan.read_text())
    def key(row):
        return json.dumps({k:v for k,v in row.items() if k!='line'},sort_keys=True)
    old=collections.Counter(map(key,prior['violations'])); new=collections.Counter(map(key,current['violations']))
    comparison=dict(before_count=sum(old.values()),after_count=sum(new.values()),new_findings=list((new-old).elements()),removed_findings=list((old-new).elements()))
    (SCRATCH/'r2-scanner-comparison.json').write_text(json.dumps(comparison,indent=2)+'\n')
logs=[]
for path in sorted(SCRATCH.glob('r2-*.log')):
    lines=path.read_text(errors='replace').splitlines()
    item=identity(path); item['tail']=lines[-6:]
    events=[m.groups() for line in lines if line.startswith('[gw')
            for m in [re.search(r'\b(PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS)\b (tests/.*)',line)] if m]
    if events:
        item['terminal_test_event_counts']=dict(collections.Counter(event[0] for event in events))
        item['failed_or_error_events']=[event for event in events if event[0] in ('FAILED','ERROR')]
    logs.append(item)
changed=run(['git','diff','--name-only'],COMPOSED).decode().splitlines()
assert set(changed)-{'fairscape_models'} == {p['target'] for p in packets} | {
    'tests/test_native_shared_render.py','tests/test_native_u1_selector_refusals.py'}, changed
result=dict(u1_source_commit=HEAD,base=BASE,composed=str(COMPOSED),protected_unchanged=protected,packets=packets,logs=logs,scanner_comparison=comparison,
    composed_tracked_diff=changed,
    test_overlays=[identity(ROOT/p) for p in ('tests/test_native_shared_render.py','tests/test_native_u1_selector_refusals.py')],
    artifacts=[identity(p) for p in sorted(SCRATCH.glob('r2-*.json'))])
(OUT/'round2_evidence.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'protected_unchanged':len(protected),'packets':len(packets),'logs':len(logs),'scanner':comparison},indent=2))

# Purpose: summarize retained U2 round-3 evidence (#5508), 2026-11-06.
# Inputs: scratch XML/JSON and local Git. Output: r3-summary.json, no source edits.
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET
R=Path(__file__).resolve().parents[2];S=R.parent/'scratch-native-u2'
def git(*args): return subprocess.check_output(['git',*args],cwd=R)
out={'head':git('rev-parse','HEAD').decode().strip(),'runs':{},'mutations':{}}
for path in S.glob('r3-*.execution.json'):
    value=json.loads(path.read_bytes());xml=path.with_name(path.name.replace('.execution.json','.xml'))
    if xml.exists():
        cases=ET.parse(xml).getroot().findall('.//testcase')
        value['counts']=dict(Counter('failed' if c.find('failure') is not None else 'error' if c.find('error') is not None else 'skipped' if c.find('skipped') is not None else 'passed' for c in cases))
        value['failures']=[c.attrib for c in cases if c.find('failure') is not None or c.find('error') is not None]
    out['runs'][path.stem]=value
for path in (S/'r3-mutations3').glob('M*.json'):
    value=json.loads(path.read_bytes());xml=path.with_suffix('.xml')
    if xml.exists():
        cases=ET.parse(xml).getroot().findall('.//testcase')
        value['failed']=[{'test':c.attrib,'reason':(c.find('failure') if c.find('failure') is not None else c.find('error')).attrib.get('message','')} for c in cases if c.find('failure') is not None or c.find('error') is not None]
    out['mutations'][path.stem]=value
manifest=json.loads((R/'src/data_sheets_schema/native_controller_sources_v1.json').read_bytes())
paths={pin['path'] for pin in manifest['modules'].values()}|{'src/data_sheets_schema/native_controller_sources_v1.json','src/data_sheets_schema/native_attribution_controller.py','src/data_sheets_schema/native_supervisor_authority.py','src/data_sheets_schema/native_attribution_registration.py','notes/claudecode_direct/prepare_direct.py','notes/claudecode_direct/run_direct_canary.py'}
for path in paths:
    assert (R/path).read_bytes()==git('show','e8c9dbe3c:'+path),path
out['frozen_v1_unchanged']=sorted(paths)
changed=git('diff','--name-only','e8c9dbe3c','HEAD').decode().splitlines()
assert not any(p.startswith('data/') or p.endswith(('shared_generation.py','canonical_hashes.yaml')) for p in changed)
out['changed_paths']=changed
if (S/'r3-scan.json').exists():
    before=json.loads((S/'baseline-scan.json').read_bytes()); after=json.loads((S/'r3-scan.json').read_bytes())
    out['scanner']={'baseline_summary':before.get('summary'),'round3_summary':after.get('summary'),'violations_equal':before['violations']==after['violations']}
    initial=json.loads((S/'scan.json').read_bytes())
    out['scanner']['tracked_without_reason']={name:len(value['tracked_without_reason']) for name,value in [('M7',before),('round1',initial),('round3',after)]}
    assert out['scanner']['tracked_without_reason']=={'M7':110,'round1':113,'round3':110}
    print(json.dumps(out['scanner'],indent=2))
    assert out['scanner']['violations_equal']
(S/'r3-summary.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({'head':out['head'],'runs':{k:v.get('counts',v['exit_code']) for k,v in out['runs'].items()},'mutations':{k:v['returncode'] for k,v in out['mutations'].items()}},indent=2))

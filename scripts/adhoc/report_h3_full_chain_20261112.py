#!/usr/bin/env python3
"""H3 full-chain handoff, 2026-11-12: saved scratch evidence -> lead MD/JSON.
No provider, native execution or external write. Replaces only designated handoff.
"""
import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
E=Path('/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions')
S=E/'scratch-h3-packet-builder-20261112'
H=E/'codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/codex-h3-full-chain-rehearsal-20261112'
p=argparse.ArgumentParser(); p.add_argument('--final',type=Path); a=p.parse_args()
def pin(path):
    raw=path.read_bytes(); return {'path':str(path),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
run=S/'tests/full-chain-canary-01'
progress=next((run/'cases').rglob('chain-progress.json'))
value={'phase':'first full-chain canary complete; Parts B/C/D and remaining admission tests pending',
 'answer':'The scratch composition builds and validates synthetic runtime, preparation, shared composition, bound permission evidence, execution registration and current review bundle through production functions. The first full-chain canary passes. No capture, reservation or native process ran; three-command admission and remaining documents are still pending.',
 'timestamp_procedure':'Proposed: read valid_from from the already supplied runtime, never choose a date. Create the registration-addition commit with that exact explicit author date. Re-read the commit and call the production equality validator, refusing any mismatch; scratch success/refusal proof is pending.',
 'owner_inputs':'Owner identity, actual authorization time and D117 word, durable binary location, version/auth facts, explicit environment, provisional limits, deadlines and evidence directory remain unsupplied; no owner act is inferred.',
 'composition':json.loads((S/'composition-a/composition.json').read_bytes()),
 'canary':{'progress':json.loads(progress.read_bytes()),'progress_pin':pin(progress),'log':pin(run/'pytest.log'),'junit':pin(run/'pytest.xml')},
 'counts':{'canary_cases':len(ET.parse(run/'pytest.xml').getroot().findall('.//testcase')),'canary_failures':len(ET.parse(run/'pytest.xml').getroot().findall('.//failure'))}}
if a.final: value.update(json.loads(a.final.read_bytes()))
text='# Helper 3 full-chain rehearsal — 2026-11-12\n\n'+value['answer']+'\n\n'+value['timestamp_procedure']+'\n\n'+value['owner_inputs']+'\n\n'
text+='Phase: '+value['phase']+'\n\n'
if 'details_markdown' in value: text+=value['details_markdown']+'\n'
else: text+='Saved evidence: `'+str(progress)+'` and `'+str(run/'pytest.log')+'`.\n'
raw=json.dumps(value,indent=2)+'\n'
assert '@' not in raw and '@' not in text
H.with_suffix('.json').write_text(raw); H.with_suffix('.md').write_text(text)
for path in [H.with_suffix('.md'),H.with_suffix('.json')]: print(str(path)+' '+hashlib.sha256(path.read_bytes()).hexdigest())

#!/usr/bin/env python3
"""G13 evidence collector, 2026-11-12. Read saved logs/JUnit/artifacts/local Git;
write one new scratch JSON for the handoff generator. No network or native run.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser()
p.add_argument('--scratch',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
a=p.parse_args()

def digest(path):
    raw=path.read_bytes()
    return {'path':str(path),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}

def git(*args):
    return subprocess.check_output(['/usr/bin/git','-C',str(ROOT),*args],text=True).strip()

runs=[]
for name in ['canary-01','canary-02','synthetic-canary-01','focused-01','focused-02','final-01','expectation-regression-01']:
    directory=a.scratch/'tests'/name
    row={'name':name,'directory':str(directory),'log':digest(directory/'pytest.log')}
    if (directory/'pytest.xml').exists():
        xml=ET.parse(directory/'pytest.xml').getroot()
        cases=xml.findall('.//testcase')
        row['counts']={'cases':len(cases),'failures':len(xml.findall('.//failure')),
                       'errors':len(xml.findall('.//error')),'skipped':len(xml.findall('.//skipped'))}
        row['junit']=digest(directory/'pytest.xml')
    for file in ('outcome.json','worker-outcome.json','network.json','origins-after.json'):
        if (directory/file).exists(): row[file]=json.loads((directory/file).read_bytes())
    runs.append(row)
real=next((a.scratch/'tests/final-01/cases').glob('test_real_chorus_prefix*/packet'))
refusal=next((a.scratch/'tests/final-01/cases').rglob('protected-refusal.json'))
routing=sorted((a.scratch/'tests/final-01/cases').rglob('routing-evidence.json'))
protected=['src/data_sheets_schema/shared_generation.py','src/data_sheets_schema/api_runner.py',
           'src/download/prompts/canonical_hashes.yaml','tests/utils/run_spec_boundary_contracts.json']
main='7ad8c9e7295f1575ae9108ea62c12c83b1dd4db1'
protected_evidence=[]
for relative in protected:
    raw=(ROOT/relative).read_bytes()
    old=subprocess.check_output(['/usr/bin/git','-C',str(ROOT),'show',main+':'+relative])
    protected_evidence.append({**digest(ROOT/relative),'equals_main':raw==old,'main_commit':main})
value={
 'answer':'Real CHORUS input preparation succeeds: production validators accept receipt policy, selection, complete schema/prompt/profile pins and byte inventory. The builder exits 2 at the first dependency stop: owner-approved provisional runtime/D117 authorization and real saved observations for final runtime. No production registration was issued. Synthetic saved runtime and review joins pass; the unchanged protected RunSpec constructor refuses native_shared_generation_version, so full-chain preparation/composition/permission/registration cannot be rehearsed on this base. Three CLI routing spies stop before effect implementations and all reservations; they do not bypass the refusal or prove admission.',
 'worktree':str(ROOT),'branch':git('branch','--show-current'),'commit':git('rev-parse','HEAD'),
 'source_status':git('status','--short'),
 'real_status':json.loads((real/'status.json').read_bytes()),
 'real_outputs':[digest(path) for path in sorted(real.iterdir()) if path.is_file()],
 'real_command':json.loads((real.parent/'builder-command.json').read_bytes()),
 'real_stdout':digest(real.parent/'builder.stdout'),
 'protected_refusal':json.loads(refusal.read_bytes()),'protected_refusal_file':digest(refusal),
 'routing_evidence':[{'file':digest(path),'result':json.loads(path.read_bytes())} for path in routing],
 'test_summary':'Final unchanged-source cohort: 15 passed, runner exit 0. Subsequent exact-byte/verified-consumer regression: 1 passed, runner exit 0. These are focused tests, not full CI or full-chain admission.',
 'runs':runs,'protected_files':protected_evidence,
 'map':{'json':digest(ROOT/'notes/native_canary_packet_map_DRAFT_20261112/map.json'),
        'table':digest(ROOT/'notes/native_canary_packet_map_DRAFT_20261112/map.md')},
 'runbook':digest(ROOT/'notes/native_canary_runbook_DRAFT_20261112.md'),
 'review_findings_for_lead':[
   {'id':'H3-P1','severity':'blocking','finding':'Protected RunSpec lacks native_shared_generation_version; synthetic prepare fails before instruction/composition. No workaround applied.','next':'Rerun full real/synthetic construction after the authorized merged integration.'},
   {'id':'H3-P2','severity':'blocking','finding':'This base uses review bundle v2/terms v1 and 90-second margin, while N1 v12 proposes 300 seconds and helper2 is changing bundle/terms.','next':'Lead reconciles ratification and merged code; switch isolated review adapter and rerun.'},
   {'id':'H3-P3','severity':'decision before registration','finding':'Runtime valid_from must exactly equal the later registration-addition commit author timestamp. Ordinary later Git commit timing does not provide that equality.','next':'Lead and owner review an explicit authoring-timestamp procedure before production; no date selected or production commit made here.'},
   {'id':'H3-P4','severity':'fixed in new code','finding':'Read-only review caught CRLF normalization of system text and ordinary-consumer use with source-loaded controls in the future expectation wrapper.','resolution':'Use raw UTF-8 bytes and the same loaded_permission_inputs/verified consumer scope as production registration; targeted regression passes.'},
   {'id':'H3-P5','severity':'validation limit','finding':'Post-observation saved-step wrappers beyond review/expectation argument delegation remain unvalidated end to end because of P1; they are DRAFT commands, not launch-ready certification.','next':'Rehearse all remaining documents and actual production admission boundaries on approved merged source before D117/live capture.'}],
 'retained_run_failures':{'canary-01':'Outer sandbox prevented nested sandbox and process monitoring; no test assertion ran. Retried with approved escalation while child kept OS network/native-execution denial.',
                         'focused-02':'15 assertions passed but runner exit 1: map files were added under notes during tests. Retained; final-01 reran without concurrent writes and passed.'},
 'bounds':'New files only on assigned branch. No push, GitHub write, provider/model/native-binary invocation, probe, capture, reservation, private composition arming or protected-file edits. Tests run ordinary Python and local Git for explicitly synthetic evidence only.',
 'helper_scripts':[str(path) for path in sorted((ROOT/'scripts/adhoc').glob('*native_packet*20261112.py'))],
 'limitations':'Synthetic reviews, CI, word, runtime and routing bytes are labelled in bytes. CI is explicitly NOT-EVIDENCE and not_run. Routing stubs registration verification, metadata validation and production-account gate; real account-choice, saved-runtime and review joins execute where applicable. No real permission traces, capture, guard claim or admission were manufactured. Actual source merges, CI completion, owner acts, independent review, runtime observations and launch remain outside this offline assignment.'}
with a.output.open('x') as stream: json.dump(value,stream,indent=2); stream.write('\n')
print(json.dumps(digest(a.output)))

#!/usr/bin/env python3
"""Issue 6094: report available clocks and missing endpoints from saved runs.
Inputs four completed cohorts and retained sleep excerpt; outputs MD/JSON.
No tests, native program, host probe, model or network execution. 2026-11-13.
"""
from pathlib import Path
from datetime import datetime
import hashlib,json,xml.etree.ElementTree as ET
R=Path(__file__).resolve().parents[2];E=R.parent
H=R/'notes/development_efficiency_20261111/handoffs/codex-h2-6094-timing-20261113'
RUNS=[E/'scratch-h2-helper-cache-20261112/tests'/name for name in ('public-correction-cache','public-omissions-cache')]
RUNS += [E/'scratch-native-main-integration-20261112/tests'/name for name in ('h1-ci-8760-public-canary-20261113','h1-ci-current-pending-public-20261113')]
def pin(p):return {'path':str(p),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def stamp(s):return datetime.fromisoformat(s.replace('Z','+00:00')).timestamp()
def blocks(value):
 if isinstance(value,dict):
  if value.get('type') in ('tool_use','tool_result'):yield value
  for child in value.values():yield from blocks(child)
 elif isinstance(value,list):
  for child in value:yield from blocks(child)
rows=[]
for root in RUNS:
 actuals=list((root/'cases').rglob('actual-result.json'));assert len(actuals)==1
 case=actuals[0].parent;attempt=case/'native-attempt'
 files=[root/p for p in ('pytest.xml','outcome.json','plan.json')]
 files += [attempt/p for p in ('control.jsonl','transcript.jsonl','started.json','runtime-observation.json','subscription-dispatched.json')]
 files += [case/'fresh-attempt/stages/journal.json',actuals[0]]
 for p in files:assert p.is_file(), 'required retained artifact missing: '+str(p)
 control=[json.loads(line) for line in (attempt/'control.jsonl').read_text().splitlines()]
 frames=[json.loads(line) for line in (attempt/'transcript.jsonl').read_text().splitlines()]
 decisions={r['request']['request']['input']['tool_use_id']:r for r in control if r['kind']=='decision'}
 tools={};results={}
 for frame in frames:
  for block in blocks(frame):
   if block['type']=='tool_use':tools[block['id']]=block
   elif block['type']=='tool_result':results[block['tool_use_id']]=block
 calls=[]
 for key,tool in tools.items():
  decision=decisions.get(key)
  kind=decision.get('basis','') if decision else 'no saved decision'
  if ': ' in kind:kind=kind.rsplit(': ',1)[1]
  result=results.get(key)
  calls.append({'tool_id':key,'tool':tool['name'],'command_kind':kind,
   'decision_at':None if decision is None else decision['at'],
   'start':None,'end':None,'wall_seconds':None,
   'result_recorded':result is not None,'result_error':None if result is None else result.get('is_error'),
   'reason':'No helper invocation/completion clock or turn boundary timestamps were recorded.'})
 known=[row for row in calls if row['decision_at']]
 intervals=[{'after_tool':a['tool_id'],'before_tool':b['tool_id'],
             'after_kind':a['command_kind'],'before_kind':b['command_kind'],
             'seconds':stamp(b['decision_at'])-stamp(a['decision_at'])}
            for a,b in zip(known,known[1:])]
 journal=json.loads((case/'fresh-attempt/stages/journal.json').read_bytes());stages=[]
 for item in journal['records']:
  p=Path(item['path']);assert hashlib.sha256(p.read_bytes()).hexdigest()==item['sha256']
  record=json.loads(p.read_bytes());payload=record['payload']
  stages.append({'sequence':record['sequence'],'record_type':record['record_type'],
   'cursor':payload.get('cursor'),'start':None,'end':None,'wall_seconds':None,'artifact':pin(p)})
 junit=list(ET.parse(root/'pytest.xml').iter('testcase'));assert len(junit)==1
 result=json.loads(actuals[0].read_bytes());started=json.loads((attempt/'started.json').read_bytes())
 plan=json.loads((root/'plan.json').read_bytes());outcome=json.loads((root/'outcome.json').read_bytes())
 dispatched=json.loads((attempt/'subscription-dispatched.json').read_bytes())
 hosts=[str(p) for p in root.rglob('*host*.json') if 'site-packages' not in p.parts]
 row={'run':root.name,'case':str(case),'source_commit':plan['source_commit'],
  'pytest_seconds':float(junit[0].attrib['time']),'runner_seconds':outcome['seconds'],
  'started_at':started['started_at'],'first_control_at':control[0]['at'],
  'guard_dispatched_at':dispatched.get('dispatched_at'),'finished_at':result.get('finished_at'),
  'first_stop':result.get('first_stop'), 'launch_verification_seconds':None,
  'calls':calls,'stages':stages,'interdecision_intervals':intervals,
  'largest_interdecision_intervals':sorted(intervals,key=lambda x:x['seconds'],reverse=True)[:3],
  'unsettled_tools':[c['tool_id'] for c in calls if not c['result_recorded']],
  'required_helpers_not_observed':[name for name in ('full_schema','full_terms','core_schema','pair','recorder') if not any(c['command_kind']==name for c in calls)],
  'host_observation_files':hosts,'power_source':'unknown: no run-specific observation',
  'heavy_test_overlap':'not established by retained handoff timestamps; activity timestamps are not measurements of concurrent heavy tests',
  'missing_artifacts':['execute_child entry clock','child-dispatch/process-start clock paired to that entry','per-helper start/end and turn-gap clocks','run-specific power/sleep observation'],
  'disposition':'Stopped exact timing reconstruction for this run because required timing artifacts were never retained. No mtime inference or re-execution.',
  'artifacts':[pin(p) for p in files]}
 rows.append(row)
sleep=E/'scratch-h2-cache-gaps-20261113/audit/sleep-events-20261112.txt'
sleep_lines=[line for line in sleep.read_text().splitlines() if '2026-11-12 14:10:39' in line or '2026-11-12 14:21:58' in line]
assert len(sleep_lines)==2
value={'runs':rows,'retained_sleep_excerpt':{'file':pin(sleep),'matching_lines':sleep_lines,'run':'public-omissions-cache','overlap_seconds':679,'basis':'Saved local Sleep/Wake event pair, battery 51 percent; no extrapolation to other runs.'},
 'conclusions':{'dominant_steps':'Cannot isolate helper or verification costs from missing endpoints. Interdecision intervals combine classification, callbacks, helper work, model processing and any host suspension.',
 'code_attribution':'No measured step slowdown can be assigned to a commit from these artifacts. The inherited timer origin precedes launch verification, as the lead independently established; issue 6170 supplies the ruling to repair that.',
 'quiet_host_900_seconds':'Not established: no complete run, isolated helper duration series or remaining-tail timings. Total pytest time is not attempt duration.',
 'recommendation':'Quiet-host run arranged by the lead, after issue 6170 fixes dispatch origin and suspend-inclusive timing. Retain entry/dispatch, helper start/end, turn boundaries and host observations. Do not change the synthetic deadline from this evidence.'},
 'scope':'Read-only saved artifacts only. Missing required endpoints stop reconstruction on each run. Filesystem census includes hidden and ignored entries. No current host probe, native call, public path rerun, source branch edit, publication or GitHub write.'}
with H.with_suffix('.json').open('x') as stream:stream.write(json.dumps(value,indent=2,sort_keys=True).replace(chr(64),'\\u0040')+'\n')
lines=['# Issue 6094: retained timing is insufficient for a per-step budget','',
 'The four saved runs cannot support the requested exact timing breakdown: none retained execute_child entry and child-dispatch endpoints, helper completion clocks, turn boundaries, or run-specific host observations. Exact reconstruction is stopped for each run, as assigned. The tables below retain available control timestamps and leave the missing durations unknown. A control decision is not a helper start; the next decision is not its completion.','',
 'Recommendation: a lead-arranged quiet-host run after the separately assigned issue 6170 repair, with the missing timing fields recorded. These artifacts do not establish that 900 seconds suffices on a quiet host and do not justify a deadline increase. No public path was rerun.','',
 'The saved sleep excerpt establishes a 679-second battery/clamshell sleep during the omissions run, from 22:10:39 to 22:21:58 UTC on November 12. Power at the other runs and overlapping heavy-helper tests are not established. Handoff creation times and test totals do not identify CPU contention.','',
 '| Run | Pytest total (s) | Runner total (s) | Launch verification | Missing endpoints |','| --- | ---: | ---: | --- | --- |']
for row in rows:lines.append(f"| {row['run']} | {row['pytest_seconds']:.2f} | {row['runner_seconds']:.2f} | unknown | entry, dispatch, helper end, turn boundaries, host observation |")
for row in rows:
 lines += ['', '## '+row['run'],'', 'Attempt start evidence: `'+row['started_at']+'`; first control event: `'+row['first_control_at']+'`. These are different lifecycle boundaries and do not measure launch verification.', '',
  '| Tool ID | Kind | Control decision (UTC) | Start | End | Wall seconds | Result recorded |','| --- | --- | --- | --- | --- | --- | --- |']
 for call in row['calls']:lines.append('| '+call['tool_id']+' | '+call['tool']+': '+call['command_kind']+' | '+str(call['decision_at'])+' | unknown | unknown | unknown | '+str(call['result_recorded'])+' |')
 lines += ['', 'Required helper kinds not observed: '+', '.join(row['required_helpers_not_observed'])+'. Recorder completion is not demonstrated. Unsettled at the retained transcript tail: '+', '.join(row['unsettled_tools'])+'. This identifies a pending request/result, not proof a subprocess was running at the exact deadline.', '',
  '| Stage sequence | Record | Cursor | Start/end/wall |','| --- | --- | --- | --- |']
 for stage in row['stages']:lines.append('| '+str(stage['sequence'])+' | '+stage['record_type']+' | '+str(stage['cursor'])+' | unrecorded |')
 lines += ['', 'Largest observed interdecision intervals (combined work, not helper durations or model-turn gaps):']
 for gap in row['largest_interdecision_intervals']:lines.append(f"- {gap['after_tool']} ({gap['after_kind']}) to {gap['before_tool']} ({gap['before_kind']}): {gap['seconds']:.6f} s.")
lines += ['', '## Limits and next measurement','', *value['conclusions'].values(), '',
 'The runtime observations explicitly say SYNTHETIC SOFTWARE TEST ONLY instead of recording observation time. Stage journals identify ordering and content, not stage wall clocks. Helper results are retained in transcripts but lack completion timestamps. File mtimes were not substituted for missing clocks. The own-run passive timing plugin covers subscription guard calls only, not execute_child entry or helper lifetimes.', '',
 'The comparison uses the two helper-1 handoffs named by the assignment and their exact completed cohorts; cancelled/active shard cases were not inspected. Additional work on the four timing reconstructions stops here until new, lead-authorized evidence exists.', '',
 'JSON SHA-256: `'+pin(H.with_suffix('.json'))['sha256']+'`.', 'Producer: `'+str(Path(__file__))+'`.']
text='\n'.join(lines)+'\n';assert chr(64) not in text
with H.with_suffix('.md').open('x') as stream:stream.write(text)
for p in (H.with_suffix('.md'),H.with_suffix('.json')):print(json.dumps(pin(p)))

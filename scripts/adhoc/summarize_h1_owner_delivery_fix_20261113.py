#!/usr/bin/env python3
"""Summarize source-pinned issue6192 before/after evidence, 2026-11-13.
Inputs: fixed six offline G07 cohorts, immutable local test/source Git objects.
Outputs: exclusive H Markdown/JSON and exact source/assertion/protected digests.
No tests, application imports, network, publication or source mutations.
"""
import argparse
import ast
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

R=Path(__file__).resolve().parents[2];E=R.parent
W=E/'codex-native-h1-ci-followups-20261113';B=E/'scratch-native-h1-ci-followups-20261113'
H=R/'notes/development_efficiency_20261111/handoffs'
BASE='b70c8a56c47ff4add3d905313adabdce02ee7d5a'
HEAD='31329ff2351462e0432c9bb3a45e5df74996fb45'
TEST='tests/test_native_shared_owner_delivery.py'
PROTECTED=['src/data_sheets_schema/shared_generation.py','src/data_sheets_schema/api_runner.py',
 'src/download/prompts/canonical_hashes.yaml','tests/utils/run_spec_boundary_contracts.json']
COHORTS=[('6192-baseline-canary',BASE,0),
 ('6192-before-contamination','7d6c8b49218f3390db6c29e2dda4effd2b114e88',1),
 ('6192-after-canary','49b54b0b53da1e1dbc24ee0abb458bf65bdf01b6',1),
 ('6192-after-canary2','dad4db6418f642916428d59d52d14f2410b5dc43',1),
 ('6192-after-canary3',HEAD,0),('6192-owner-and-guard-suite',HEAD,0)]
REFS={}

def need(v,why):
    if not v: raise ValueError(why)

def sha(raw): return hashlib.sha256(raw).hexdigest()

def pin(path,expected=None):
    need(path.resolve(strict=True)==path and path.is_file(),'Physical input required')
    raw=path.read_bytes();digest=sha(raw)
    need(expected is None or digest==expected,'Digest changed '+str(path))
    ref={'path':str(path),'sha256':digest,'bytes':len(raw)};REFS[str(path)]=ref
    return raw,ref

def document(path):
    raw,ref=pin(path);return json.loads(raw),ref

def git(*args):
    result=subprocess.run(['/usr/bin/git','--no-replace-objects','-C',str(W),'-c','core.hooksPath=/dev/null',
       '-c','protocol.allow=never',*args],env={'PATH':'/usr/bin:/bin','HOME':'/var/empty','GIT_NO_LAZY_FETCH':'1',
       'GIT_CONFIG_GLOBAL':'/dev/null','GIT_CONFIG_SYSTEM':'/dev/null','GIT_OPTIONAL_LOCKS':'0'},capture_output=True,timeout=60)
    need(result.returncode==0,'Read-only Git failed');return result.stdout

def body(raw,name):
    rows=[n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef) and n.name==name]
    need(len(rows)==1,'Unique scenario required');nodes=rows[0].body
    if isinstance(nodes[0],ast.Expr) and isinstance(nodes[0].value,ast.Constant) and isinstance(nodes[0].value.value,str):nodes=nodes[1:]
    return ast.dump(ast.Module(body=nodes,type_ignores=[]),include_attributes=False).encode()

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--write',action='store_true');args=ap.parse_args()
    original=git('show',BASE+':'+TEST);current=git('show',HEAD+':'+TEST)
    before=body(original,'test_replay_owner_reuses_catalog_and_unknown_initialization_is_fresh')
    after=body(current,'_assert_replay_owner_reuses_catalog_and_unknown_initialization_is_fresh')
    need(before==after,'Original scenario assertion body changed')
    need(not git('diff','--name-only',BASE,HEAD,'--','src/').strip(),'Production source changed')
    protected={}
    for path in PROTECTED:
        old,new=git('show',BASE+':'+path),git('show',HEAD+':'+path)
        need(old==new,'Protected bytes changed');protected[path]=sha(new)
    rows=[]
    for name,commit,code in COHORTS:
        out=B/'tests'/name
        plan,pref=document(out/'plan.json');outcome,oref=document(out/'outcome.json')
        worker,wref=document(out/'worker-outcome.json');network,nref=document(out/'network.json')
        command,cref=document(out/'pytest-command.json');bootstrap,bref=document(out/'bootstrap.json')
        need(plan['source_commit']==commit and plan['source_root']==str(W) and plan['workers']==2,'Source/worker mismatch')
        need(plan['deadline_seconds'] in (600,900) and outcome['returncode']==code==outcome['worker_returncode']==worker['returncode']
             and outcome['cleanup_verified'] is True and outcome['interrupted'] is None
             and not outcome['forced_cleanup'] and not outcome['observed_surviving_pids']
             and not outcome['observation_errors'] and worker['source_origin_checks_passed'] is True,'Unqualified terminal')
        need(network['network_bind_denied'] is True,'Network guard not witnessed')
        jr,jref=pin(out/'pytest.xml');cases=[]
        for i,case in enumerate(ET.fromstring(jr).iter('testcase')):
            events=[child for child in case if child.tag in ('failure','error','skipped')]
            state='error' if any(x.tag=='error' for x in events) else 'failure' if any(x.tag=='failure' for x in events) else 'skipped' if events else 'passed'
            cases.append({'ordinal':i,'classname':case.get('classname'),'name':case.get('name'),'state':state,
                          'seconds':case.get('time'),'details':[{'kind':x.tag,'text':x.text,'message':x.get('message')} for x in events]})
        counts=dict(Counter(x['state'] for x in cases));need(bool(cases),'Empty evidence')
        if code==0:need(set(counts)=={'passed'},'Passing cohort contains negative/skipped cases')
        if name!='6192-owner-and-guard-suite':need(len(cases)==1,'Canary was not one unit')
        if name=='6192-before-contamination':need('None is None and None is not None' in jr.decode(),'Before assertion changed')
        witnesses=[]
        if name in ('6192-after-canary3','6192-owner-and-guard-suite'):
            # Ignore-independent lookup only inside this owned test output.
            for path in sorted((out/'cases').rglob('owner-delivery.json')):
                witness,ref=document(path)
                need(witness=={'source_root':str(W),'reuse_initially_eligible':True,
                     'original_owner_assertions_completed':True,'unknown_initialization_refused':True},'Child witness differs')
                witnesses.append(ref)
            need(len(witnesses)==(1 if name.endswith('canary3') else 2),'Required child witness missing')
        rows.append({'label':name,'source_commit':commit,'qualified_terminal':True,'counts':counts,'cases':cases,
                     'seconds':outcome['seconds'],'junit':jref,'plan':pref,'outcome':oref,'worker':wref,
                     'network':nref,'command':cref,'bootstrap':bref,'child_witnesses':witnesses})
    data={'created_utc':datetime.now(timezone.utc).isoformat(),'producer':pin(Path(__file__).resolve())[1],
      'issue':6192,'source_commit':HEAD,'source_tree':git('rev-parse',HEAD+'^{tree}').decode().strip(),
      'base_commit':BASE,'branch':'codex/native-h1-ci-followups-20261113','production_changes':False,
      'protected_sha256':protected,'original_assertion_body_preserved':True,'assertion_body_sha256':sha(after),
      'answer':'Test isolation repaired and verified under controlled guarded-dependency contamination. Exact historical CI predecessor remains unidentified.',
      'cause':'The test required a non-None optional-reuse token in a shared pytest interpreter. A changed JSONEncoder.default makes the unchanged dependency guard refuse reuse and reproduces the exact None assertion. This is a causal reproduction of the isolation flaw, not proof that this specific binding caused the saved CI run.',
      'fix':'Run the unchanged warm/fresh/refusal scenario in a fresh Python process with exact checkout origins and mandatory assertions. Parent changed binding stays installed and reuse still refuses. No production guard reset or widening.',
      'review_findings':[{'id':'H1-6192-R1','finding':'Inherited PYTHONOPTIMIZE could strip child assertions','status':'addressed','remedy':'Explicit PYTHONOPTIMIZE=0, non-assert optimized-mode refusal, and parent optimize=1 regression'}],
      'implementation_canary_failures':'Two retained after-fix canaries failed only in the new source-origin witness; exact module/package paths were corrected before broader validation.',
      'ci_run':'43394245660','ci_head':'fc00ce6544b002dc0e726cb196cb5939c8283092','ci_shard':10,
      'ci_worker_order_reproduced':False,'limitations':['No saved raw shard log or worker-order ledger found in the scoped ignore-independent evidence search.',
        'Local two-worker Python3.13/macOS suite is not the CI four-worker Python3.12/Linux shard.',
        'The three-file regression suite is not a complete CI shard replay; no full-suite or native acceptance.'],
      'cohorts':rows,'evidence':list(REFS.values()),'published':False}
    md=['# Issue 6192 owner-delivery isolation','',data['answer'],'',data['cause'],'',data['fix'],'',
      'Head `'+HEAD+'`; base `'+BASE+'`. Original scenario body is AST-identical, digest `'+data['assertion_body_sha256']+'`. Protected files and all production source are unchanged.','',
      '| Cohort | Source | Outcomes | Seconds |','|---|---|---|---:|']
    for row in rows:md.append('| '+row['label']+' | '+row['source_commit']+' | '+json.dumps(row['counts'],sort_keys=True)+' | '+str(row['seconds'])+' |')
    md+=['',data['implementation_canary_failures'],'','Review also closed the inherited optimization defect; the contamination regression sets parent optimization to1 while the child explicitly uses0 and refuses optimized execution.','',*('- '+x for x in data['limitations']),'']
    paths=[H/'codex-h1-6192-owner-delivery-20261113.json',H/'codex-h1-6192-owner-delivery-20261113.md']
    summary={'source':HEAD,'outcomes':{x['label']:x['counts'] for x in rows},'assertion_body_preserved':True,'production_unchanged':True,'status':'preview'}
    if args.write:
        need(not any(p.exists() for p in paths),'Preserve prior report')
        raws=[(json.dumps(data,indent=2,sort_keys=True).replace(chr(64),'\\u0040')+'\n').encode(),('\n'.join(md).replace(chr(64),'[at]')).encode()]
        summary['artifacts']=[]
        for path,raw in zip(paths,raws):
            with path.open('xb') as f:f.write(raw)
            summary['artifacts'].append(pin(path,sha(raw))[1])
        summary['status']='report_written'
    print(json.dumps(summary,indent=2,sort_keys=True))

if __name__=='__main__':main()

#!/usr/bin/env python3
"""Run bounded offline RC-1 reviewer checks and retain evidence, 2026-11-19.
Inputs: assigned worktree, primary interpreter and explicit test targets.
Outputs: console/XML/JSON evidence outside source; pin-tool receipts. No live calls.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[2]
P=Path('/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema')
S=ROOT.parent/'scratch-codex196-agy-reviewer-20261119'
PYTHON=P/'.venv/bin/python'
PIN=P/'scripts/adhoc/compute_pin_chain_20261115.py'

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--label',required=True)
    parser.add_argument('--mode',choices=['tests','pin-check','pin-propose','pin-apply'],default='tests')
    parser.add_argument('--expected-exit',type=int,default=0)
    parser.add_argument('--targets-json',type=Path)
    parser.add_argument('targets',nargs='*')
    args=parser.parse_args()
    assert args.label and all(ch.isalnum() or ch=='-' for ch in args.label)
    lane=S/args.label
    lane.mkdir(parents=True,exist_ok=False)
    env=dict(os.environ,PYTHONPATH=str(ROOT/'src'),PYTHONDONTWRITEBYTECODE='1',PYTHONPYCACHEPREFIX=str(S/'pycache'))
    for key in list(env):
        if key.endswith('API_KEY') or key.startswith(('ANTHROPIC_','CBORG_','OPENAI_')):
            env.pop(key)
    if args.mode=='tests':
        targets=args.targets or json.loads(args.targets_json.read_text())
        if isinstance(targets,dict):
            targets=targets['required_test_roster']
        assert targets and all(isinstance(item,str) for item in targets)
        command=[str(PYTHON),'-B','-m','pytest','-q','-p','no:cacheprovider','--tb=short',
                 '--basetemp',str(lane/'basetemp'),'--junitxml',str(lane/'results.xml'),*targets]
    else:
        command=[str(PYTHON),'-B',str(PIN),'--root',str(ROOT),'--'+args.mode.removeprefix('pin-'),'--compact']
        if args.mode=='pin-apply': command.append('--i-am-lead')
    start=time.monotonic()
    timed_out=False
    with (lane/'console.log').open('xb') as log:
        process=subprocess.Popen(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        try: result=process.wait(timeout=1800)
        except subprocess.TimeoutExpired:
            timed_out=True
            os.killpg(process.pid,signal.SIGTERM)
            try: result=process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid,signal.SIGKILL)
                result=process.wait()
    record=dict(label=args.label,mode=args.mode,command=command,returncode=result,
                expected_exit=args.expected_exit,timed_out=timed_out,seconds=time.monotonic()-start,
                head=subprocess.check_output(['/usr/bin/git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                review_source_sha256=hashlib.sha256((ROOT/'src/data_sheets_schema/native_launch_review.py').read_bytes()).hexdigest())
    if args.mode=='tests' and (lane/'results.xml').is_file():
        suites=list(ET.parse(lane/'results.xml').getroot().iter('testsuite'))
        record['counts']={key:sum(int(s.get(key,'0')) for s in suites) for key in ('tests','failures','errors','skipped')}
    raw=(json.dumps(record,indent=2,sort_keys=True)+'\n').encode()
    (lane/'result.json').write_bytes(raw)
    assert (lane/'console.log').stat().st_size and (lane/'result.json').read_bytes()==raw
    print(json.dumps(record,sort_keys=True))
    return 0 if result==args.expected_exit and not timed_out else 1

if __name__=='__main__': raise SystemExit(main())

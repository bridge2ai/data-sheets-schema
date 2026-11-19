#!/usr/bin/env python3
"""Inspect/remove only completed RC-1 pytest basetemps, 2026-11-19.
Inputs: fixed task lane paths and retained result receipts. Outputs: cleanup logs.
The owner assignment authorizes each lane basetemp removal; evidence stays outside.
"""
import argparse
import json
from pathlib import Path
import subprocess

S=Path('/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-codex196-agy-reviewer-20261119')
SKILL=Path('/Users/marcin/.codex/skills/safe-delete/scripts')
TARGETS={
    'baseline-canary': S/'baseline-canary/basetemp',
    'baseline-agy-red': S/'baseline-agy-red/basetemp',
    'fixed-canary': S/'fixed-canary/basetemp',
    'focused-cohort': S/'focused-cohort/basetemp',
}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('label',choices=TARGETS)
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    target=TARGETS[args.label]
    lane=target.parent
    result=json.loads((lane/'result.json').read_text())
    assert result['mode']=='tests' and result['timed_out'] is False
    assert (lane/'results.xml').is_file() and (lane/'console.log').stat().st_size
    assert target.is_dir() and not target.is_symlink() and target.resolve()==target
    siblings=sorted(path.name for path in lane.iterdir() if path!=target)
    log=lane/('cleanup-applied.log' if args.apply else 'cleanup-preflight.log')
    guard=[str(SKILL/'guarded_rm.sh'),'--expect-parent',str(lane),'--log',str(S/'deletions.tsv'),
           '--note','RC-1 completed pytest fixtures only; console/XML/JSON evidence retained']
    commands=([guard+[str(target)]] if args.apply else
              [[str(SKILL/'preflight.sh'),'--search-root',str(S),str(target)],guard+['--dry-run',str(target)]])
    with log.open('xb') as out:
        for command in commands:
            completed=subprocess.run(command,stdout=out,stderr=subprocess.STDOUT,timeout=120)
            assert completed.returncode==0,command
    if args.apply:
        assert not target.exists() and not target.is_symlink()
        assert siblings==sorted(path.name for path in lane.iterdir() if path.name!='cleanup-applied.log')
    print(json.dumps(dict(label=args.label,applied=args.apply,target=str(target),target_exists=target.exists(),log=str(log))))

if __name__=='__main__': main()

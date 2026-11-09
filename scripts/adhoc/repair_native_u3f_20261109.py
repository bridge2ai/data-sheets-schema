"""U3-F offline evidence, 2026-11-09; inputs source roots and saved U3-E evidence.

Outputs only scratch-native-u1u3/u3f; supports the U3-F local repair handoff.
No provider/native launch. Each scanner runs under the inherited OS deny policy.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-native-u1u3'
OUT = SCRATCH / 'u3f'
LOCK = ROOT.parent / 'plans/native_quiet_window.lock'

def quiet():
    if os.path.lexists(LOCK):
        raise RuntimeError('quiet-window lock exists')

def scan(label, source):
    quiet()
    OUT.mkdir(exist_ok=True)
    prior = SCRATCH / 'canary-retry'
    env = json.loads((prior / 'plan.json').read_text())['environment']
    env['PYTHONPATH'] = str(source / 'src') + ':' + str(source)
    command = ['/usr/bin/sandbox-exec', '-f', str(prior / 'network-denied.sb'),
        str(prior / 'venv/bin/python'), '-P', '-B',
        str(ROOT / '.claude/skills/d4d-generation-specificity-audit/scan.py'),
        '--root', str(source), '--report', str(OUT / (label + '.md')),
        '--json', str(OUT / (label + '.json')), '--full-json']
    start = time.monotonic()
    with (OUT / (label + '.log')).open('xb') as stream:
        result = subprocess.run(command, cwd=source, env=env, stdout=stream,
            stderr=subprocess.STDOUT, timeout=3300)
    record = dict(command=command, returncode=result.returncode, seconds=time.monotonic()-start)
    (OUT / (label + '-run.json')).write_text(json.dumps(record, indent=2)+'\n')
    print(json.dumps(record), flush=True)

def ledger():
    OUT.mkdir(exist_ok=True)
    rows = json.loads((SCRATCH / 'exact-node-ledger.json').read_bytes())
    text = (SCRATCH / 'exact-nonpasses.md').read_text()
    counts = {}
    for row in rows:
        key = row['run'] + ':' + row['status']
        counts[key] = counts.get(key, 0) + 1
    result = dict(observations=len(rows), nonpass_report_bytes=len(text.encode()), counts=counts,
        relevant=[row for row in rows if row['run'] in ('packet-suite', 'packet-specificity-hooks', 'census-serial-recheck') and row['status'] != 'passed'])
    (OUT / 'prior-ledger-review.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    if sys.argv[1] == 'ledger':
        ledger()
    elif sys.argv[1] == 'scan':
        scan(sys.argv[2], Path(sys.argv[3]).resolve())

#!/usr/bin/env python3
"""#5212 round 6, 2026-11-02: replay saved CI failure node lists offline.

Inputs: pinned archive, scratch basetemp, saved failures TSV, optional exclusion.
Outputs: exact command/selection JSON plus the offline runner's log/phase ledger.
No source overlays, remote commands, provider credentials or network access.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

p = argparse.ArgumentParser()
p.add_argument('--tree', type=Path, required=True)
p.add_argument('--basetemp', type=Path, required=True)
selection = p.add_mutually_exclusive_group(required=True)
selection.add_argument('--failures-tsv', type=Path)
selection.add_argument('--failures-json', type=Path, help='Replay failed nodes from an offline phase ledger')
p.add_argument('--exclude', action='append', default=[])
p.add_argument('--extra', action='append', default=[])
a = p.parse_args()
assert 'scratch-5212fix' in a.basetemp.parts
source = a.failures_tsv or a.failures_json
raw = source.read_bytes()
notes = False
if a.failures_tsv:
    nodes = [line.split('\tFAILED ', 1)[1].split(' - ', 1)[0]
             for line in raw.decode().splitlines()]
else:
    ledger = json.loads(raw)
    nodes = sorted({row['nodeid'] for row in ledger['reports'] if row['outcome'] == 'failed'})
    assert nodes, 'no failed nodes to replay'
    notes = ledger['environment'].get('notes_lane', False)
assert len(nodes) == len(set(nodes))
assert set(a.exclude) <= set(nodes)
nodes = [node for node in nodes if node not in a.exclude]
command = [sys.executable, '-S', '-P', '-B',
           str(Path(__file__).with_name('run_d68_round4_20261101.py')),
           '--tree', str(a.tree), '--basetemp', str(a.basetemp),
           *(['--notes'] if notes else []), *nodes, *a.extra, '-v',
           *([] if notes else ['-n', '4', '--dist', 'load', '--maxschedchunk=1']), '--durations=25']
record = {'command': command, 'nodes': nodes, 'extra': a.extra, 'excluded': a.exclude,
          'selection_source': str(source), 'source_sha256': hashlib.sha256(raw).hexdigest()}
target = a.basetemp.with_suffix('.selection.json')
target.write_text(json.dumps(record, indent=2))
start = time.monotonic()
with a.basetemp.with_suffix('.log').open('w') as stream:
    result = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT)
record.update(exit_code=result.returncode, wall_seconds=time.monotonic() - start)
target.write_text(json.dumps(record, indent=2))
print(json.dumps({'nodes': len(nodes), 'exit_code': result.returncode,
                  'wall_seconds': record['wall_seconds']}))
raise SystemExit(result.returncode)

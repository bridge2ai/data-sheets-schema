"""Continue only unfinished U3-B round-2 regression nodes, 2026-11-07.

Inputs: group, evidence directory, finished prior run labels, new run label.
Outputs: exact disjoint node-selection ledger and ordinary bounded pytest logs.
Serves P2-2 broad coverage when the P2-3 ordered attempt reaches its deadline;
this continuation never claims to preserve the interrupted process's state.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser()
parser.add_argument('group', choices=['api', 'shared'])
parser.add_argument('directory', type=Path)
parser.add_argument('name')
parser.add_argument('--prior', action='append', required=True)
parser.add_argument('--plan', action='store_true')
args = parser.parse_args()
directory = args.directory.resolve()
assert directory.is_relative_to(ROOT.parent / 'scratch-native-u3b')
if (ROOT.parent / 'plans/native_quiet_window.lock').exists():
    raise SystemExit('Quiet window active; defer continuation')
files = (directory / (args.group + '-wall-final-roster.txt')).read_text().splitlines()
collection = (directory / 'collect-final.log').read_text()
assert 'U3B_EXIT=' in collection
nodes = re.findall(r'^(tests/[^\n]+::[^\n]+)$', collection, re.M)
selected = [node for filename in files for node in nodes if node.split('::', 1)[0] == filename]
assert selected and len(selected) == len(set(selected))
completed = set()
for name in args.prior:
    log = (directory / (name + '.log')).read_text()
    assert 'U3B_EXIT=' in log, 'prior run is still active'
    header = json.loads(log.splitlines()[0])
    assert Path(header['cwd']) == ROOT
    for filename, digest in header['source_sha256'].items():
        assert hashlib.sha256((ROOT / filename).read_bytes()).hexdigest() == digest, filename
    rows = [json.loads(line) for line in (directory / (name + '.events.jsonl')).read_text().splitlines()]
    assert not any(row['outcome'] == 'failed' for row in rows), 'classify failures before continuing'
    done = {row['nodeid'] for row in rows if row['phase'] == 'call' and row['outcome'] == 'passed'}
    assert done <= set(selected)
    assert not completed & done, 'prior coverage overlaps'
    completed.update(done)
pending = [node for node in selected if node not in completed]
ledger = {'group': args.group, 'prior_runs': args.prior, 'selected_count': len(selected),
          'completed_count': len(completed), 'pending_count': len(pending),
          'completed': sorted(completed), 'pending': pending,
          'scope': 'disjoint broad-suite continuation; not full-order state evidence'}
if args.plan:
    print(json.dumps(ledger, indent=2))
    raise SystemExit(0)
output = directory / (args.name + '-selection.json')
if output.exists():
    raise SystemExit('Refusing to overwrite selection evidence')
output.write_text(json.dumps(ledger, indent=2) + '\n')
if not pending:
    print('All selected nodes already passed')
    raise SystemExit(0)
raise SystemExit(subprocess.call([
    sys.executable, str(ROOT / 'scripts/adhoc/validate_native_u3b.py'), args.name,
    '--workers', '2', '--output-dir', str(directory), *pending,
    '-q', '--tb=short', '--junitxml=' + str(directory / (args.name + '.xml'))], cwd=ROOT))

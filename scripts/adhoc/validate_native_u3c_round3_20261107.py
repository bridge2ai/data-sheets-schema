"""U3-C Round 3 roster/evidence driver, 2026-11-07.

Inputs: merged checkout and previous C roster. Outputs: explicit plans and
bounded sequential suite evidence in the single assigned scratch directory.
API file partitions provide broad coverage, not B's separate full-order gate.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT.parent / 'scratch-native-u3c-r3'
parser = argparse.ArgumentParser()
parser.add_argument('--plan', action='store_true')
parser.add_argument('groups', nargs='*')
args = parser.parse_args()
old = ROOT.parent / 'native-u3c-r2-final-combined-20261107/pytest-command.json'
combined = [n for n in json.loads(old.read_text())['args'] if n.startswith('tests/')]
def files(*patterns):
    return sorted({p.relative_to(ROOT).as_posix() for pattern in patterns
                   for p in (ROOT / 'tests').glob(pattern)})
api = files('test_api_*.py', 'test_source_heading*.py', 'test_renderer_contract_captures.py')
api.append('tests/test_download/test_api_runner.py')
groups = {
    'ca': combined,
    'b-focused': files('test_native_u3b_reuse.py', 'test_native_schema_metadata_reuse.py',
                       'test_schema_event_replay.py', 'test_schema_snapshot*.py',
                       'test_schema_cache*.py', 'test_cache_dependencies*.py',
                       'test_native_shared_selection.py'),
    'b-shared': files('test_shared_generation*.py', 'test_typed_audit*.py', 'test_audit_omission*.py'),
    'b-bc1': files('test_bc1*.py', 'test_wave7*bc1*.py'),
    **{f'b-api-{i+1}': api[i::4] for i in range(4)},
    'collect': ['tests'],
}
selected = args.groups or list(groups)
assert set(selected) <= set(groups)
plan = {name: groups[name] for name in selected}
if args.plan:
    print(json.dumps(plan, indent=2))
    raise SystemExit(0)
for name in selected:
    while (ROOT.parent / 'plans/native_quiet_window.lock').exists():
        print('Quiet lock held; waiting 60 seconds', flush=True)
        time.sleep(60)
    command = [sys.executable, '-S', '-P', '-B',
               str(ROOT / 'scripts/adhoc/run_native_u3c_round3_20261107.py'),
               '--out', str(OUT / name), '--workers', '0' if name == 'collect' else '2']
    if name == 'collect':
        command.append('--collect-only')
    command += groups[name]
    print('Starting ' + name, flush=True)
    result = subprocess.run(command, cwd=ROOT)
    print(f'Finished {name}: {result.returncode}', flush=True)
    outcome = OUT / name / 'outcome.json'
    assert outcome.stat().st_size
    observed = json.loads(outcome.read_text())
    if not observed['cleanup_verified']:
        raise SystemExit('Cleanup/deadline gate failed; inspect before continuing')

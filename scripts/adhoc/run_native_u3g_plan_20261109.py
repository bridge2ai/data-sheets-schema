"""Run selected U3-G planned cohorts sequentially, 2026-11-09 (#5653).

Inputs: a committed planner's JSON and explicit group names. Outputs: fresh
supervised evidence directories; inspect persisted canary bytes before batches.
No provider/native/network path; each child uses the checked-in denied runner.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
EXECUTIONS = next(p for p in ROOT.parents if p.name == 'd4d-executions')
OUT = EXECUTIONS / 'scratch-native-u1u3/u3g'


def canary(folder):
    outcome = json.loads((folder / 'outcome.json').read_bytes())
    assert outcome['returncode'] == 0 and outcome['cleanup_verified']
    assert outcome['worker']['source_origin_checks_passed']
    assert outcome['seconds'] < 3300
    assert (folder / 'pytest.xml').stat().st_size
    paths = [p for p in folder.glob('cases/popen-*/test_validate_probe_uses_saved*/verified-output.json')
             if p.resolve(strict=True) == p]
    assert len(paths) == 1
    document = json.loads(paths[0].read_bytes())
    assert document['result']['checked'] is document['result']['passed'] is True
    assert len(document['result']['traces']) == 7
    assert document['effort'] == 'high' and document['selected_receipt_instrument'] == 4
    for name in ('expectation.json', 'probe.json', 'account-choice.json'):
        assert paths[0].with_name(name).stat().st_size
    instructions = [p for p in folder.glob('cases/popen-*/u4-genuine-saved-probe*/instruction.md')
                    if p.resolve(strict=True) == p]
    assert len(instructions) == 1 and instructions[0].stat().st_size
    return {'verified_output_sha256': hashlib.sha256(paths[0].read_bytes()).hexdigest(),
            'instruction_sha256': hashlib.sha256(instructions[0].read_bytes()).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan', type=Path)
    parser.add_argument('groups', nargs='+')
    args = parser.parse_args()
    plan = json.loads(args.plan.read_bytes())
    assert plan['kind'] == 'native_u3g_offline_cohort_plan'
    source = Path(plan['source_root'])
    assert source.resolve(strict=True) == source and source.is_relative_to(EXECUTIONS)
    runner = source / 'scripts/adhoc/run_native_u3g_20261109.py'
    assert hashlib.sha256(runner.read_bytes()).hexdigest() == plan['runner']['sha256']
    groups = {row['name']: row for row in plan['cohorts']}
    assert len(set(args.groups)) == len(args.groups) and set(args.groups) <= set(groups)
    env = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'LANG': 'en_US.UTF-8',
           'GIT_NO_LAZY_FETCH': '1', 'GIT_CONFIG_GLOBAL': '/dev/null',
           'GIT_CONFIG_SYSTEM': '/dev/null', 'PYTHONDONTWRITEBYTECODE': '1'}
    for name in args.groups:
        if os.path.lexists(EXECUTIONS / 'plans/native_quiet_window.lock'):
            raise SystemExit('quiet window active; next cohort not started')
        row = groups[name]
        destination = Path(row['out'])
        assert destination.resolve() == destination and destination.is_relative_to(OUT)
        assert not destination.exists(), 'never overwrite run evidence'
        if name != 'canary':
            print(json.dumps({'canary': canary(Path(groups['canary']['out']))}), flush=True)
        if name == 'parity':
            folder = Path(groups['parity-canary']['out'])
            outcome = json.loads((folder / 'outcome.json').read_bytes())
            assert outcome['returncode'] == 0 and outcome['cleanup_verified']
            actual = list((folder / 'parity').glob('*.txt'))
            assert len(actual) == 1
            saved = EXECUTIONS / 'scratch-native-u1u3/parity2-canary-baseline/parity' / actual[0].name
            assert actual[0].read_bytes() == saved.read_bytes()
        assert row['argv'][1:4] == ['-S', '-P', '-B']
        assert row['argv'][4] == str(runner) and row['cwd'] == str(source)
        print(json.dumps({'start': name, 'out': str(destination)}), flush=True)
        # The child supervisor owns its process tree and independent 3250 s
        # watchdog. An outer subprocess.run timeout would kill that supervisor
        # alone and abandon its separately grouped sandbox descendants.
        result = subprocess.run(row['argv'], cwd=source, env={**env, **row['environment']},
                                check=False)
        if result.returncode not in (0, 1):
            raise SystemExit(result.returncode)
        outcome = json.loads((destination / 'outcome.json').read_bytes())
        assert outcome['cleanup_verified'] and outcome['seconds'] < 3300
        if name == 'canary':
            print(json.dumps({'canary': canary(destination)}), flush=True)
        print(json.dumps({'finished': name, 'returncode': result.returncode}), flush=True)


if __name__ == '__main__':
    main()

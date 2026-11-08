#!/usr/bin/env python3
"""Exact D9 offline validation cohorts and artifact summaries, 2026-11-07.

Inputs: committed checkout, inherited D8/C6 rosters. Outputs: exclusive plan
and supervised test cohorts in scratch-native-u3d. No network/native dispatch.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-native-u3d'


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts/adhoc' / (name + '.py'))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def groups():
    old = module('native_u3d_round6_evidence_20261107')
    d = {f'tests/test_{name}.py' for name in old.D_MODULES}
    d.update(str(path.relative_to(ROOT)) for path in (ROOT / 'tests').glob('test_native_u3d*.py'))
    c = {str(path.relative_to(ROOT)) for path in (ROOT / 'tests').glob('test_native_shared*.py')}
    c.add('tests/test_native_u3c_test_driver.py')
    all_dc = d | c
    permission = {'tests/test_native_shared_permissions.py'}
    registration = {'tests/test_native_shared_registration.py'}
    lifecycle = {name for name in all_dc if any(term in name for term in (
        '_execution.', '_execution_variant.', '_execution_failure.', '_live_capture.',
        '_results.', '_saved_pool_bound.', '_provenance.'))}
    remainder = sorted(all_dc - permission - registration - lifecycle)
    # File-level partitions preserve fixture isolation, and no node is omitted.
    result = {'permission': sorted(permission), 'registration': sorted(registration),
        'lifecycle': sorted(lifecycle), 'dc-1': remainder[::2], 'dc-2': remainder[1::2]}
    base = module('plan_native_u3c_round4_20261107').plan(Path(sys.executable))['groups']
    for name in ('a-core', 'b-focused'):
        result[name] = base[name]['nodes']
    result['b-schema'] = ['tests/' + name for name in (
        'test_historical_digest_cache.py', 'test_imported_schema_snapshot.py',
        'test_schema_digest_cache.py', 'test_schema_view.py')]
    result['census'] = ['tests/test_native_shared_consumer_census.py',
        'tests/test_native_u3d_round9_boundaries.py', 'tests/test_native_u3c_round4_helpers.py']
    result['collection'] = ['tests']
    if set().union(*(set(result[key]) for key in ('permission', 'registration', 'lifecycle', 'dc-1', 'dc-2'))) != all_dc:
        raise RuntimeError('D/C cohort partition dropped a file')
    if any(not (ROOT / node.split('::')[0]).is_file() for name, nodes in result.items()
           if name != 'collection' for node in nodes):
        raise RuntimeError('missing selected test file')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('plan', 'run'))
    parser.add_argument('--group')
    parser.add_argument('--label')
    args = parser.parse_args()
    roster = groups()
    if args.action == 'plan':
        target = SCRATCH / 'round9-plan.json'
        with target.open('x') as handle:
            json.dump(roster, handle, indent=2, sort_keys=True)
            handle.write('\n')
        print(target)
        return 0
    if args.group not in roster:
        parser.error('select one explicit group')
    if json.loads((SCRATCH / 'round9-plan.json').read_text()) != roster:
        raise RuntimeError('saved roster differs from current source')
    label = args.label or args.group
    if not label or any(not (letter.isalnum() or letter == '-') for letter in label):
        raise ValueError('unsafe evidence label')
    argv = [sys.executable, '-S', '-P', '-B',
        str(ROOT / 'scripts/adhoc/run_native_u3d_round9_20261107.py'),
        '--out', str(SCRATCH / ('round9-' + label)), '--workers',
        '0' if args.group in ('census', 'collection') else '2']
    if args.group == 'collection':
        argv.append('--collect-only')
    return subprocess.call(argv + roster[args.group], cwd=ROOT)


if __name__ == '__main__':
    raise SystemExit(main())

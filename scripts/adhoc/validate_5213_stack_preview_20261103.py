#!/usr/bin/env python3
"""#5213 round 5, 2026-11-03: frozen offline acceptance plan and evidence join.

Inputs: pinned archive, round-4 plans, BC1 round-2 scope. Outputs: fresh external
plan, named runs and summary. Existing BC1 runner owns each 3600-second deadline.
This helper never edits source, applies overlays, publishes, or starts a batch.
"""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
DRIVER = ROOT / 'scripts/adhoc/bc1_g2_validate_20261103.py'
SANDBOX = ROOT / 'scripts/adhoc/d76_loopback_only_20261031.sb'
SG2 = 'test_sg2_root_launch_completes_and_records_registered_paths'
CANARY = ('tests/test_wave7_5213_d76_round4_boundaries.py::'
          'test_unchanged_native_spec_retains_valid_registration_and_exclusive_write[write_registration]')
PINS = {
    'final-9a76e-d76-without-sg2/plan.json': 'f3fcfeedf08d23b1f91bd850fff36fc84e23043df8040f4801e97f54215abc67',
    'final-9a76e-sg2-none/plan.json': 'c839a6e24ee334068a6a80d9f49912eaf8c7888e398c373385010d1f89e06df0',
    'final-9a76e-sg2-explicit/plan.json': 'f3eb244210ceaf2651ea8b62e98e3f343ab5226e49b477f0319ecd3d76b353eb',
    'final-9a76e-sg2-conventional/plan.json': 'd3db11efa5feb04b7fb05f5c74ef6c442cdeeac5d5724a68fb8176fab85c7a3d',
}
SCOPE_SHA = '3583bc40dbf800bf419899e2ae8dcb6ad4020e1ae46d624f34cd2406c2f29112'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


def git(tree, *args):
    return subprocess.check_output(['git', '--no-replace-objects', '-c', 'protocol.allow=never',
                                    '-C', str(tree), *args],
                                   env=dict(os.environ, GIT_NO_LAZY_FETCH='1')).decode().strip()


def init(options):
    tree = options.tree.resolve(strict=True)
    evidence = options.evidence.resolve()
    assert not evidence.is_relative_to(tree) and not evidence.exists()
    assert sha(options.scope) == SCOPE_SHA
    scope = read(options.scope)
    assert len(scope['files']) == 91 and len(scope['groups']) == 13
    assert Counter(sum(scope['groups'], [])) == Counter(scope['files'])
    original = []
    for name, digest in PINS.items():
        path = options.round4 / name
        assert sha(path) == digest
        original.extend(read(path)['targets'])
    assert len(original) == len(set(original)) == 349
    d76_files = sorted({node.split('::')[0] for node in original})
    runs = {
        'canary': {'targets': [CANARY], 'workers': 2},
        'full-collection': {'targets': ['tests'], 'workers': 0, 'collect_only': True},
        'd76-without-sg2': {'targets': d76_files, 'workers': 2, 'exclude': SG2},
    }
    for mode in ('none', 'explicit', 'conventional'):
        nodes = [node for node in original if SG2 in node and node.endswith('[' + mode + ']')]
        assert len(nodes) == 1
        runs['sg2-' + mode] = {'targets': nodes, 'workers': 0}
    for index, group in enumerate(scope['groups']):
        runs[f'bc1-{index:02d}'] = {
            'targets': [path for path in group if path != 'tests/test_ci_sharding.py'],
            'workers': 2,
        }
    runs['bc1-ci-sharding'] = {'targets': ['tests/test_ci_sharding.py'], 'workers': 0}
    runs['skill-guards'] = {'targets': ['tests/test_neutral_generation_schema.py',
                                      'tests/test_external_dataset_onboarding.py'], 'workers': 2}
    proof = read(tree / '.g2-archive.json')
    assert git(tree, 'rev-parse', 'HEAD') == proof['commit']
    assert not git(tree, 'diff', 'HEAD', '--')
    plan = {'tree': str(tree), 'head': proof['commit'], 'runs': runs,
            'original_d76_nodes': sorted(original), 'bc1_scope_sha256': sha(options.scope),
            'round4_plan_sha256': PINS, 'producer_sha256': sha(Path(__file__)),
            'driver_sha256': sha(DRIVER), 'sandbox_sha256': sha(SANDBOX),
            'launcher_sha256': sha(ROOT / 'scripts/adhoc/g2_bc1_offline_20261101.py'),
            'protected_sha256': {path: sha(tree / path) for path in
                ('src/data_sheets_schema/shared_generation.py', 'src/download/prompts/canonical_hashes.yaml')},
            'coverage': {path: [name for name, run in runs.items() if path in run['targets']]
                         for path in scope['files'] if any(term in path for term in
                             ('specificity', 'test_profiles.py', 'test_generality_tuned.py'))},
            'limits': 'Overlapping canary/cohorts are observations, not unique-suite totals; offline macOS only.'}
    evidence.mkdir(parents=True)
    save(evidence / 'plan.json', plan)
    print(json.dumps({'plan': str(evidence / 'plan.json'), 'sha256': sha(evidence / 'plan.json'),
                      'runs': list(runs), 'original_d76_count': len(original)}, indent=2))


def load_plan(evidence):
    plan = read(evidence / 'plan.json')
    tree = Path(plan['tree'])
    assert sha(Path(__file__)) == plan['producer_sha256']
    assert sha(DRIVER) == plan['driver_sha256'] and sha(SANDBOX) == plan['sandbox_sha256']
    assert sha(ROOT / 'scripts/adhoc/g2_bc1_offline_20261101.py') == plan['launcher_sha256']
    assert git(tree, 'rev-parse', 'HEAD') == plan['head']
    assert not git(tree, 'diff', 'HEAD', '--')
    assert all(sha(tree / path) == digest for path, digest in plan['protected_sha256'].items())
    return plan, tree


def canary_proof(evidence):
    result = read(evidence / 'canary/result.json')
    assert result['returncode'] == 0 and sum(int(s['tests']) for s in result['suites']) == 1
    artifacts = list((evidence / 'canary/tmp').rglob('new-registration.json'))
    assert len(artifacts) == 1 and artifacts[0].stat().st_size > 0
    record = read(artifacts[0])
    assert record['project'] == 'EXAMPLE' and record['method'] == 'claudecode_direct'
    return {'path': str(artifacts[0]), 'bytes': artifacts[0].stat().st_size, 'sha256': sha(artifacts[0])}


def run(options):
    plan, tree = load_plan(options.evidence)
    row = plan['runs'][options.name]
    if options.name != 'canary':
        canary_proof(options.evidence)
    arguments = list(row['targets']) + ['-q']
    if row.get('collect_only'):
        arguments += ['--collect-only']
    if row.get('exclude'):
        arguments += ['-k', 'not ' + row['exclude']]
    if row['workers']:
        arguments += ['-n', str(row['workers']), '--dist=load', '--maxschedchunk=1']
    command = ['/usr/bin/sandbox-exec', '-f', str(SANDBOX), '-D',
               'LOCAL_ROOT=' + str(options.evidence), sys.executable, '-S', '-B', str(DRIVER),
               'test', str(tree), '--output', str(options.evidence / options.name), *arguments]
    env = dict(os.environ, PYTHONPATH=str(tree / 'src'))
    code = subprocess.call(command, cwd=ROOT, env=env)
    load_plan(options.evidence)
    if options.name == 'canary' and code == 0:
        print(json.dumps({'canary_artifact': canary_proof(options.evidence)}, indent=2))
    return code


def summary(options):
    plan, tree = load_plan(options.evidence)
    collection = read(options.evidence / 'full-collection/collected.json')
    full_result = read(options.evidence / 'full-collection/result.json')
    assert full_result['returncode'] == 0 and full_result['identity']['commit'] == plan['head']
    d76_current = {node for node in collection if node.split('::')[0] in
                   plan['runs']['d76-without-sg2']['targets']}
    assert not set(plan['original_d76_nodes']) - d76_current
    rows = []
    for name, run_spec in plan['runs'].items():
        directory = options.evidence / name
        result = read(directory / 'result.json')
        assert result['identity']['commit'] == plan['head']
        artifacts = {path.name: sha(path) for path in directory.iterdir()
                     if path.is_file() and path.name in
                     {'started.json', 'result.json', 'pytest.log', 'junit.xml',
                      'collected.json', 'events.jsonl', 'failures.jsonl'}}
        if run_spec.get('collect_only'):
            rows.append({'name': name, 'collected': len(collection), 'executed': 0,
                         'returncode': result['returncode'], 'sha256': artifacts})
            continue
        expected = Counter(node for node in collection if any(
            node == target or node.split('::')[0] == target for target in run_spec['targets'])
            and run_spec.get('exclude', '\x00') not in node)
        events = [json.loads(line) for line in (directory / 'events.jsonl').read_text().splitlines()]
        phases = {phase: Counter(e['nodeid'] for e in events if e['when'] == phase)
                  for phase in ('setup', 'call', 'teardown')}
        assert phases['setup'] == phases['teardown'] == expected, name + ': setup/teardown mismatch'
        setup_refusals = Counter(e['nodeid'] for e in events
                                if e['when'] == 'setup' and e['outcome'] != 'passed')
        assert phases['call'] + setup_refusals == expected, name + ': call mismatch'
        xml = ET.parse(directory / 'junit.xml')
        cases = list(xml.iter('testcase'))
        assert len(cases) == sum(expected.values()), name + ': XML count mismatch'
        statuses = Counter()
        xfails = []
        for case in cases:
            if case.find('failure') is not None:
                statuses['failed'] += 1
            elif case.find('error') is not None:
                statuses['error'] += 1
            elif case.find('skipped') is not None:
                skipped = case.find('skipped')
                if skipped.attrib.get('type') == 'pytest.xfail':
                    statuses['xfailed'] += 1
                    xfails.append(case.attrib)
                else:
                    statuses['skipped'] += 1
            else:
                statuses['passed'] += 1
        rows.append({'name': name, 'expected': sum(expected.values()), 'executed': len(cases),
                     'counts': dict(statuses), 'xfails': xfails, 'seconds': result['seconds'],
                     'returncode': result['returncode'], 'sha256': artifacts})
    output = options.evidence / 'summary.json'
    save(output, {'head': plan['head'], 'plan_sha256': sha(options.evidence / 'plan.json'),
                  'canary_artifact': canary_proof(options.evidence), 'runs': rows,
                  'original_d76_count': 349, 'd76_added_nodes': sorted(d76_current - set(plan['original_d76_nodes'])),
                  'full_collection_occurrences': len(collection), 'full_collection_unique': len(set(collection)),
                  'limits': plan['limits']})
    print(json.dumps({'output': str(output), 'sha256': sha(output), 'runs': len(rows)}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('init', 'run', 'summary'))
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--tree', type=Path)
    parser.add_argument('--round4', type=Path)
    parser.add_argument('--scope', type=Path)
    parser.add_argument('--name')
    args = parser.parse_args()
    assert args.evidence.is_absolute() and '..' not in args.evidence.parts
    if args.action == 'init':
        init(args)
    elif args.action == 'run':
        raise SystemExit(run(args))
    else:
        summary(args)

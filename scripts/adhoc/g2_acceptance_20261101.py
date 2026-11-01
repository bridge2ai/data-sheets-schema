#!/usr/bin/env python3
# Purpose: reproducible, serial G2 acceptance and exact-base failure replays.
# Inputs: pinned archive, pytest arguments / saved failed-node ledgers.
# Outputs: immutable per-unit logs, nodes, events, JUnit and result JSON;
# shard assignment and a node-by-node failure ledger. G2 tasks 7-8, 2026-11-01.
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET


def save(path, value):
    raw = json.dumps(value, sort_keys=True, indent=2).encode() + b'\n'
    path.write_bytes(raw)
    assert path.read_bytes() == raw


def run(tree, output, arguments):
    output.mkdir(parents=True, exist_ok=False)
    identity = json.loads((tree / '.g2-archive.json').read_bytes())
    launcher = Path(__file__).with_name('g2_bc1_offline_20261101.py')
    args = []
    for arg in arguments:
        if arg.startswith('@@'):
            args.extend(json.loads(Path(arg[2:]).read_bytes()))
        else:
            args.append(arg)
    if not args:
        raise ValueError('explicit pytest arguments required')
    command = [sys.executable, '-S', '-B', str(launcher), 'pytest', *args,
        '-p', 'no:cacheprovider', '--basetemp=' + str(output / 'tmp'),
        '--junitxml=' + str(output / 'junit.xml')]
    env = dict(os.environ, G1_CHECKOUT_ROOT=str(tree), G1_TEST_FAILURES_PATH=str(output / 'failures.jsonl'),
        G2_COLLECTED_PATH=str(output / 'collected.json'), G2_TEST_EVENTS_PATH=str(output / 'events.jsonl'),
        PYTHONPYCACHEPREFIX=str(output / 'pycache'), TMPDIR=str(output),
        GIT_ALLOW_PROTOCOL='file', GIT_NO_LAZY_FETCH='1')
    start = time.monotonic()
    save(output / 'started.json', {'identity': identity, 'command': command, 'tree': str(tree),
        'python': sys.version, 'launcher_sha256': hashlib.sha256(launcher.read_bytes()).hexdigest(),
        'poetry_lock_sha256': hashlib.sha256((tree / 'poetry.lock').read_bytes()).hexdigest()})
    with (output / 'pytest.log').open('w') as log:
        child = subprocess.Popen(command, cwd=tree, env=env, stdout=log, stderr=subprocess.STDOUT)
        while True:
            try:
                returncode = child.wait(timeout=45)
                break
            except subprocess.TimeoutExpired:
                print(output.name, 'elapsed', round(time.monotonic() - start), flush=True)
                progress(output / 'events.jsonl')
    suites = []
    if (output / 'junit.xml').is_file():
        suites = [suite.attrib for suite in ET.parse(output / 'junit.xml').iter('testsuite')]
    save(output / 'result.json', {'identity': identity, 'returncode': returncode,
        'seconds': time.monotonic() - start, 'suites': suites})
    print(json.dumps(json.loads((output / 'result.json').read_bytes())), flush=True)
    return returncode


def scope(tree, path):
    files = set()
    for pattern in ('*bc1*.py', '*general*.py', '*specificity*.py'):
        files.update(str(p.relative_to(tree)) for p in (tree / 'tests').rglob(pattern))
    files.update(('tests/test_build_api_registrations.py', 'tests/test_registration_input_sizing.py',
                  'tests/test_neutral_generation_schema.py'))
    save(path, sorted(files))
    print('\n'.join(sorted(files)))


def shard(tree, collected, output):
    sys.path.insert(0, str(tree))
    from utils.pytest_shard import balanced_files, partition_lanes, read_weights
    nodes = json.loads(collected.read_bytes())
    ordinary = partition_lanes(nodes)['ordinary']
    assignments = balanced_files((node.split('::')[0] for node in ordinary), 6,
                                  read_weights(tree / 'utils/ci_test_durations.json'))
    owner = assignments['tests/test_build_api_registrations.py']
    selected = [node for node in ordinary if assignments[node.split('::')[0]] == owner]
    save(output, {'shard': f'{owner}/6', 'node_count': len(selected),
        'collected_count': len(nodes), 'assignments': assignments, 'selected_nodes': selected})
    print(f'{owner}/6: {len(selected)} nodes; full collection {len(nodes)}')


def failures(paths, output):
    nodes = set()
    for path in paths:
        if path.is_file():
            for line in path.read_text().splitlines():
                nodes.add(json.loads(line)['nodeid'])
    save(output, sorted(nodes))
    print(len(nodes), 'unique failed nodes')


def progress(path):
    events = [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []
    counts = Counter(row['outcome'] for row in events if row['when'] == 'call')
    errors = [row for row in events if row['when'] != 'call' and row['outcome'] == 'failed']
    print(dict(counts), 'setup/teardown errors', len(errors), 'last:', events[-1] if events else None, flush=True)


def details(paths):
    for path in paths:
        if path.is_file():
            for line in path.read_text().splitlines():
                row = json.loads(line)
                print(path.parent.name, row['nodeid'], row['when'])
                print(row['longrepr'][-2200:])


def failure_summary(paths):
    for path in paths:
        if not path.is_file():
            continue
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        groups = Counter()
        for row in rows:
            errors = [line.strip() for line in row['longrepr'].splitlines() if line.startswith('E ')]
            groups[(row['when'], errors[-1] if errors else row['longrepr'].splitlines()[-1])] += 1
        print(path.parent.name, len(rows), 'failed reports')
        for signature, count in groups.items():
            print(count, *signature)


def ledger(root, output):
    """Join immutable unit evidence without converting failures into passes."""
    repo = Path(__file__).resolve().parents[2]
    final_head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo).decode().strip()
    units, failed_nodes = {}, {}
    for result_path in sorted(root.glob('*/result.json')):
        unit = result_path.parent
        result = json.loads(result_path.read_bytes())
        started = json.loads((unit / 'started.json').read_bytes())
        assert result['identity'] == started['identity']
        nodes = json.loads((unit / 'collected.json').read_bytes())
        assert len(nodes) == len(set(nodes))
        events_path = unit / 'events.jsonl'
        events = ([json.loads(line) for line in events_path.read_text().splitlines()]
                  if events_path.exists() else [])
        assert all(row['nodeid'] in nodes for row in events)
        failures_path = unit / 'failures.jsonl'
        failures = ([json.loads(line) for line in failures_path.read_text().splitlines()]
                    if failures_path.exists() else [])
        assert len(failures) == sum(row['outcome'] == 'failed' for row in events)
        for row in failures:
            errors = [line.strip() for line in row['longrepr'].splitlines() if line.startswith('E ')]
            failed_nodes.setdefault(row['nodeid'], []).append({'unit': unit.name,
                'when': row['when'], 'signature': errors[-1] if errors else row['longrepr'].splitlines()[-1],
                'trace_sha256': hashlib.sha256(row['longrepr'].encode()).hexdigest()})
        xml = unit / 'junit.xml'
        skipped = [{'class': node.get('classname'), 'name': node.get('name'),
                    'reason': node.find('skipped').get('message')}
                   for node in ET.parse(xml).iter('testcase')
                   if node.find('skipped') is not None] if xml.exists() else []
        changes = subprocess.check_output(['git', 'diff', '--name-only',
            result['identity']['commit'], final_head], cwd=repo).decode().splitlines()
        hashes = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                  for path in sorted(unit.iterdir()) if path.is_file()
                  and path.suffix in ('.json', '.jsonl', '.xml', '.log')}
        units[unit.name] = {'result': result, 'collected_count': len(nodes),
            'call_outcomes': dict(Counter(row['outcome'] for row in events if row['when'] == 'call')),
            'failed_reports': len(failures), 'skips': skipped, 'files_sha256': hashes,
            'junit_present': xml.exists(),
            'nodes_without_teardown': sorted(set(nodes) - {
                row['nodeid'] for row in events if row['when'] == 'teardown'}),
            'changes_from_tested_commit_to_final': changes}
    assignment = json.loads((root / 'shard-assignment.json').read_bytes())
    actual = json.loads((root / 'ordinary-shard-final/collected.json').read_bytes())
    assert set(actual) == set(assignment['selected_nodes'])
    assert any(node.startswith('tests/test_build_api_registrations.py::') for node in actual)
    assert units['ordinary-shard-final']['junit_present']
    assert not units['ordinary-shard-final']['nodes_without_teardown']
    outcomes = {}
    for name in units:
        path = root / name / 'events.jsonl'
        events = [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []
        for row in events:
            if row['nodeid'] in failed_nodes:
                outcomes.setdefault(row['nodeid'], {}).setdefault(name, {})[row['when']] = row['outcome']
    document = {'final_head': final_head, 'units': units, 'failed_nodes': failed_nodes,
        'failed_node_outcomes_by_unit': outcomes, 'shard': assignment['shard'],
        'shard_matches_ci_assignment': True, 'shard_contains_builder': True}
    save(output, document)
    print('Final head:', final_head, 'unique nodes with any failure:', len(failed_nodes))
    for name, unit in units.items():
        print(name, unit['collected_count'], unit['call_outcomes'],
              'failed reports', unit['failed_reports'], 'skips', len(unit['skips']))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['run', 'scope', 'shard', 'failures', 'progress', 'details', 'failure-summary', 'ledger'])
    parser.add_argument('--tree', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--collection', type=Path)
    parser.add_argument('arguments', nargs='*')
    args, rest = parser.parse_known_args()
    if args.action == 'run':
        raise SystemExit(run(args.tree.resolve(), args.output.resolve(), args.arguments + rest))
    elif args.action == 'scope':
        scope(args.tree.resolve(), args.output)
    elif args.action == 'shard':
        shard(args.tree.resolve(), args.collection, args.output)
    elif args.action == 'failures':
        failures([Path(p) for p in args.arguments + rest], args.output)
    elif args.action == 'details':
        details([Path(p) for p in args.arguments + rest])
    elif args.action == 'failure-summary':
        failure_summary([Path(p) for p in args.arguments + rest])
    elif args.action == 'ledger':
        ledger(args.tree.resolve(), args.output)
    else:
        progress(Path(args.arguments[0]))

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


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['run', 'scope', 'shard', 'failures', 'progress', 'details'])
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
    else:
        progress(Path(args.arguments[0]))

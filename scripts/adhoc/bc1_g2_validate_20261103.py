#!/usr/bin/env python3
# Purpose: pinned-archive offline acceptance with a hard 3600-second deadline.
# Inputs: local Git ref or archive plus pytest nodes; outputs: immutable logs,
# JUnit, collection/events/failures and identities in scratch. Tasks 4-8, 2026-11-03.
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
from g2_bc1_evidence_20261101 import archive, save


def metadata(tree):
    tree = tree.resolve()
    assert tree.is_relative_to(ROOT.parent / 'scratch-bc1g2')
    assert not (tree / '.git').exists()
    commit = json.loads((tree / '.g2-archive.json').read_bytes())['commit']
    common = subprocess.check_output(['git', 'rev-parse', '--git-common-dir'], cwd=ROOT).decode().strip()
    objects = (ROOT / common / 'objects').resolve()
    subprocess.run(['git', 'init', '--quiet', str(tree)], check=True)
    (tree / '.git/objects/info/alternates').write_text(str(objects) + '\n')
    subprocess.run(['git', '-C', str(tree), 'update-ref', '--no-deref', 'HEAD', commit], check=True)
    subprocess.run(['git', '-C', str(tree), 'read-tree', commit], check=True)
    assert subprocess.run(['git', '-C', str(tree), 'symbolic-ref', '-q', 'HEAD'], capture_output=True).returncode == 1
    save(tree / '.integration-metadata.json', {'commit': commit, 'objects': str(objects), 'detached': True})


def scope(output):
    selected = set()
    for pattern in ('*bc1*.py', 'test_g2*.py', '*general*.py', '*specificity*.py', '*typed_audit_runtime*.py'):
        selected.update(str(path.relative_to(ROOT)) for path in (ROOT / 'tests').rglob(pattern))
    touched = subprocess.check_output(['git', 'diff', '--name-only', 'ddfd45c3b', '3f673180d', '--', 'tests'], cwd=ROOT)
    selected.update(path for path in touched.decode().splitlines() if path.endswith('.py'))
    # Path.rglob includes ignored files: the guard-file census is exhaustive.
    guards = {str(path.relative_to(ROOT)) for path in (ROOT / 'tests').rglob('*.py')
              if any(term in path.read_text() for term in
                     ('latch_journal', 'refuse_legacy_execution', 'require_selected_resume_owner'))}
    selected.update(path for path in guards if Path(path).name.startswith('test_'))
    selected.update('tests/' + name + '.py' for name in
        ('test_prompt_registry', 'test_schema_sync', 'test_ci_sharding', 'test_registration_input_sizing'))
    weights = json.loads((ROOT / 'utils/ci_test_durations.json').read_bytes())['file_seconds']
    # Serial groups, two workers within each. Bound estimated file sums so
    # each invocation fits the independent hard one-hour deadline.
    groups, batch, total = [], [], 0
    for path in sorted(selected, key=lambda p: (-weights.get(p, 30), p)):
        cost = weights.get(path, 30)
        if batch and total + cost > 900:
            groups.append(batch)
            batch, total = [], 0
        batch.append(path)
        total += cost
    if batch:
        groups.append(batch)
    save(output, {'files': sorted(selected), 'guard_files': sorted(guards), 'groups': groups})
    print(len(selected), 'files;', len(groups), 'groups')


def run(tree, output, arguments):
    tree, output = tree.resolve(), output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    launcher = ROOT / 'scripts/adhoc/g2_bc1_offline_20261101.py'
    command = [sys.executable, '-S', '-B', str(launcher), 'pytest', *arguments,
        '-p', 'no:cacheprovider', '--basetemp=' + str(output / 'tmp'),
        '--junitxml=' + str(output / 'junit.xml')]
    env = dict(os.environ, G1_CHECKOUT_ROOT=str(tree), G1_TEST_FAILURES_PATH=str(output / 'failures.jsonl'),
        G2_COLLECTED_PATH=str(output / 'collected.json'), G2_TEST_EVENTS_PATH=str(output / 'events.jsonl'),
        PYTHONDONTWRITEBYTECODE='1', PYTHONPYCACHEPREFIX=str(output / 'pycache'), TMPDIR=str(output),
        GIT_ALLOW_PROTOCOL='file', GIT_NO_LAZY_FETCH='1', PYTEST_XDIST_AUTO_NUM_WORKERS='2')
    env.pop('D4D_MANIFEST', None)
    identity = json.loads((tree / '.g2-archive.json').read_bytes())
    hashes = {name: hashlib.sha256((tree / name).read_bytes()).hexdigest() for name in
        ('src/data_sheets_schema/shared_generation.py', 'notes/bc1_shared_generation_patch_2026-10-27.json')}
    save(output / 'started.json', {'identity': identity, 'command': command, 'protected_hashes': hashes,
                                  'deadline_seconds': 3600})
    start = time.monotonic()
    with (output / 'pytest.log').open('w') as log:
        child = subprocess.Popen(command, cwd=tree, env=env, stdout=log, stderr=subprocess.STDOUT,
                                 start_new_session=True)
        while True:
            try:
                code = child.wait(timeout=min(45, max(.01, 3600 - (time.monotonic() - start))))
                break
            except subprocess.TimeoutExpired:
                elapsed = time.monotonic() - start
                print(output.name, 'elapsed', round(elapsed), flush=True)
                if elapsed >= 3600:
                    os.killpg(child.pid, signal.SIGTERM)
                    try:
                        child.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        os.killpg(child.pid, signal.SIGKILL)
                        child.wait()
                    code = 124
                    break
    suites = [s.attrib for s in ET.parse(output / 'junit.xml').iter('testsuite')] if (output / 'junit.xml').exists() else []
    result = {'identity': identity, 'returncode': code, 'seconds': time.monotonic() - start, 'suites': suites}
    save(output / 'result.json', result)
    print(json.dumps(result), flush=True)
    return code


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('archive', 'test', 'metadata', 'scope'))
    parser.add_argument('tree', type=Path)
    parser.add_argument('--ref')
    parser.add_argument('--output', type=Path)
    args, rest = parser.parse_known_args()
    if args.action == 'archive':
        archive(args.ref, args.tree.resolve())
    elif args.action == 'metadata':
        metadata(args.tree)
    elif args.action == 'scope':
        scope(args.output)
    else:
        raise SystemExit(run(args.tree, args.output, rest))

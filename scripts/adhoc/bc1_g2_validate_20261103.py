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
        GIT_ALLOW_PROTOCOL='file', GIT_NO_LAZY_FETCH='1')
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
    parser.add_argument('action', choices=('archive', 'test'))
    parser.add_argument('tree', type=Path)
    parser.add_argument('--ref')
    parser.add_argument('--output', type=Path)
    args, rest = parser.parse_known_args()
    if args.action == 'archive':
        archive(args.ref, args.tree.resolve())
    else:
        raise SystemExit(run(args.tree, args.output, rest))

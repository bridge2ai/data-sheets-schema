"""Resume the quiet-window-interrupted PR5531 shard, 2026-11-08.

Inputs: original shard log and current CI collection/weights. Outputs: selected
and remaining node manifest plus JUnit under scratch-pr5531-fix. Invoke through
pr5531_fix_a_run.py for the quiet-window guard and 3600-second deadline.
"""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = Path(os.environ.get('D4D_PR5531_FIX_SCRATCH', ROOT.parent / 'scratch-pr5531-fix'))
LOCK = ROOT.parent / 'plans/native_quiet_window.lock'


class Collection:
    def pytest_collection_finish(self, session):
        self.nodes = [item.nodeid for item in session.items]


def _node_key(node):
    path, *parts = node.split('::')
    return ('.'.join([path[:-3].replace('/', '.'), *parts[:-1]]), parts[-1])


def _completed_nodes(collection_nodes, scratch=SCRATCH):
    xml_path = Path(scratch) / 'fix-d-shard1.xml'
    if xml_path.exists():
        try:
            xml_completed = {
                (case.attrib['classname'], case.attrib['name'])
                for case in ET.parse(xml_path).iter('testcase')
                if 'classname' in case.attrib and not list(case)
            }
            if xml_completed:
                return {node for node in collection_nodes if _node_key(node) in xml_completed}
        except ET.ParseError:
            pass
    log = (Path(scratch) / 'fix-d-shard1.log').read_text()
    return set(re.findall(r'^\[gw\d+\].*? PASSED (.+?)\s*$', log, re.MULTILINE))


def main():
    assert not LOCK.exists()
    collection = Collection()
    result = pytest.main(['tests', '--collect-only', '-q', '-p', 'no:cacheprovider',
                          '-p', 'utils.pytest_shard', '--ci-shard=1/8',
                          '--ci-shard-timings=utils/ci_test_durations.json',
                          '--ci-lane=ordinary'], plugins=[collection])
    if result:
        return int(result)
    completed = _completed_nodes(collection.nodes, SCRATCH)
    assert completed <= set(collection.nodes)
    remaining = [node for node in collection.nodes if node not in completed]
    # Complete the broad coverage before the expensive admission suite; this
    # changes scheduling only, with exactly the same remaining node set.
    remaining.sort(key=lambda node: node.startswith('tests/test_report_admission.py::'))
    (SCRATCH / 'fix-d-shard-remaining.json').write_text(json.dumps({
        'selected': collection.nodes, 'completed': sorted(completed),
        'remaining': remaining}, indent=2) + '\n')
    if not remaining:
        return 0
    command = [sys.executable, '-m', 'pytest', *remaining, '-v', '-n', '2',
               '--dist', 'load', '--maxschedchunk=1', '-p', 'no:cacheprovider',
               f'--basetemp={SCRATCH}/fix-d-shard-remaining',
               f'--junitxml={SCRATCH}/fix-d-shard-remaining.xml']
    print(f'Resuming {len(remaining)} of {len(collection.nodes)} selected cases', flush=True)
    assert not LOCK.exists()
    env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'}
    return subprocess.call(command, env=env)


if __name__ == '__main__':
    sys.exit(main())

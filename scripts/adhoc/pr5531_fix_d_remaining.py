"""Finish interrupted PR5531 fix-D checks, 2026-11-08.

Inputs: focused JUnit and the same test files. Outputs: remaining-node manifest
and JUnit under scratch-pr5531-fix. Run via pr5531_fix_a_run.py for the deadline.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = Path(os.environ.get('D4D_PR5531_FIX_SCRATCH', ROOT.parent / 'scratch-pr5531-fix'))
LOCK = ROOT.parent / 'plans/native_quiet_window.lock'
FILES = ['tests/test_source_heading_completed.py', 'tests/test_pr5531_regressions.py',
         'tests/test_download/test_api_runner.py', 'tests/test_removals.py',
         'tests/test_nested_string_lists.py', 'tests/test_identifier_form.py',
         'tests/test_enum_alias_normalisation.py', 'tests/test_british_normaliser.py',
         'tests/test_mailto_ids.py', 'tests/test_rocrate/test_normalize.py']


class Collection:
    def pytest_collection_finish(self, session):
        self.nodes = [item.nodeid for item in session.items]


def main():
    assert not LOCK.exists()
    collection = Collection()
    result = pytest.main([*FILES, '--collect-only', '-q', '-p', 'no:cacheprovider'],
                         plugins=[collection])
    if result:
        return int(result)
    completed = {(case.attrib['classname'], case.attrib['name'])
                 for case in ET.parse(SCRATCH / 'fix-d-focused.xml').iter('testcase')
                 if 'classname' in case.attrib and not list(case)}
    remaining = []
    matched = set()
    for node in collection.nodes:
        path, *parts = node.split('::')
        key = ('.'.join([path[:-3].replace('/', '.'), *parts[:-1]]), parts[-1])
        if key in completed:
            matched.add(key)
        else:
            remaining.append(node)
    assert matched == completed, (len(matched), len(completed))
    manifest = {'collected': len(collection.nodes), 'completed': len(completed),
                'remaining': remaining}
    (SCRATCH / 'fix-d-remaining.json').write_text(json.dumps(manifest, indent=2) + '\n')
    command = [sys.executable, '-m', 'pytest', *remaining, '-v', '-n', '2',
               '--dist', 'worksteal', '-p', 'no:cacheprovider',
               f'--basetemp={SCRATCH}/fix-d-remaining',
               f'--junitxml={SCRATCH}/fix-d-remaining.xml']
    print(repr(command), flush=True)
    assert not LOCK.exists()
    env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'}
    return subprocess.call(command, env=env)


if __name__ == '__main__':
    sys.exit(main())

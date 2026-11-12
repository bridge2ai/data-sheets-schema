"""Reconstruct PR5531 shard files from saved CI XML, 2026-11-08.

Inputs: earlier review's offline CI artifacts, tracked tests, current weights.
Output: scratch-pr5531-fix/fix-d-ci-files.json; no network or test execution.
"""
from collections import defaultdict
import json
import os
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

from utils.pytest_shard import balanced_files

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = Path(os.environ.get('D4D_PR5531_FIX_SCRATCH', ROOT.parent / 'scratch-pr5531-fix'))
ARTIFACTS = Path(os.environ.get('D4D_PR5531_CI_ARTIFACTS', ROOT.parent / 'scratch-pr5531-rereview/ci-artifacts'))
tracked = subprocess.check_output(['git', 'ls-files', 'tests'], text=True).splitlines()
modules = {p[:-3].replace('/', '.'): p for p in tracked if p.endswith('.py')}
cases = defaultdict(set)
unresolved = []
for path in sorted(ARTIFACTS.glob('*/pytest.xml')):
    for case in ET.parse(path).iter('testcase'):
        cls = case.get('classname', '')
        matches = [m for m in modules if cls == m or cls.startswith(m + '.')]
        if not matches:
            unresolved.append([str(path), cls, case.get('name')])
            continue
        module = max(matches, key=len)
        cases[modules[module]].add((cls, case.get('name')))
weights = json.loads((ROOT / 'utils/ci_test_durations.json').read_text())['file_seconds']
assigned = balanced_files(cases, 8, weights)
files = sorted(p for p in assigned if assigned[p] == 1)
result = {'artifacts': str(ARTIFACTS), 'observed_files': len(cases),
          'unresolved': unresolved, 'shard1_files': files,
          'shard1_previous_case_count': sum(len(cases[p]) for p in files),
          'all_observed_files': sorted(cases)}
(SCRATCH / 'fix-d-ci-files.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({k: v for k, v in result.items() if not k.endswith('files')}, indent=2))

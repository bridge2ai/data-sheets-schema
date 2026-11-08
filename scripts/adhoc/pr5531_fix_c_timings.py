"""PR5531 P1-C timing refresh, 2026-11-08.

Inputs: successful fix-C final-cohort JUnit; repository timing helper.
Outputs: measured target-file weights with local provenance, scratch shard
simulation. Retains all other weights; no fabricated CI run or scaling.
"""
import hashlib
import json
from pathlib import Path
import platform
import subprocess

from utils.update_ci_shard_timings import build
from utils import pytest_shard as ps

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-pr5531-fix'
path = ROOT / 'utils/ci_test_durations.json'
baseline = subprocess.check_output(['git', 'show', '75463cb38:utils/ci_test_durations.json'], text=True)
data = json.loads(baseline)
folder = SCRATCH / 'fix-c-final'
# Helper requires run metadata; only use its measured weights/artifact
# hashes. Do not publish its placeholder run_id/URL as CI evidence.
result = build(folder, ROOT, 0, 'local-uncommitted-fix-c')
updates = {target: result['file_seconds'][target] for target in
           ('tests/test_pr5531_regressions.py', 'tests/test_bc1_pipeline.py')}
artifacts = [{'path': str(folder / 'pytest.xml'),
              'sha256': hashlib.sha256((folder / 'pytest.xml').read_bytes()).hexdigest()}]
before = {name: data['file_seconds'].get(name) for name in updates}
data['file_seconds'].update(updates)
data['file_seconds'] = dict(sorted(data['file_seconds'].items()))
data['source']['pr5531_fix_c_local_20261108'] = {
    'base_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
    'kind': 'local working-tree measurement; not a CI run',
    'python': platform.python_version(), 'platform': platform.platform(), 'workers': 2,
    'method': 'utils.update_ci_shard_timings.build; sum JUnit case seconds, unscaled',
    'artifacts': artifacts, 'previous_file_seconds': before, 'file_seconds': updates}
# Preserve the historical union block's nonstandard indentation verbatim.
# Reformatting it would bury two weight changes in thousands of changed lines.
marker = '  "union_provenance": '
rendered = (json.dumps(data, indent=2) + '\n').split(marker)[0] + marker + baseline.split(marker)[1]
assert json.loads(rendered) == data
path.write_text(rendered)
files = subprocess.check_output(['git', 'ls-files', 'tests'], text=True).splitlines()
files = sorted(f for f in files if Path(f).name.startswith('test_') and f.endswith('.py'))
assign = ps.balanced_files(files, 8, data['file_seconds'])
est = ps._estimates(files, data['file_seconds'])
report = {'approximation': 'git-tracked test files, not actual CI collection; sums of case seconds, not wall-clock predictions',
          'updates': updates, 'shard_case_seconds': {i: sum(est[f] for f in files if assign[f] == i) for i in range(1, 9)},
          'target_shards': {f: assign[f] for f in updates}}
(SCRATCH / 'fix-c-shards.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))

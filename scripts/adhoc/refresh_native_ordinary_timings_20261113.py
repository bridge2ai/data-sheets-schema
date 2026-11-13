"""Refresh successful ordinary-shard timings for PR 5968, 2026-11-13.

Inputs: retained run 43430675981 XML, lead's run metadata, current weights.
Outputs: scratch candidate and provenance summary; --apply writes weights.
Uses the unchanged updater; refuses failed, overlapping or dedicated inputs.

The candidate is not integrated: the existing round-7 provenance test requires
the active weights to equal the prior refresh exactly. The lead must resolve
that snapshot contract before applying this candidate; the failed check and
restored baseline results are retained in the task scratch directory.
"""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from utils.update_ci_shard_timings import build
from utils.pytest_shard import DEDICATED_CASE_LANES

parser = argparse.ArgumentParser()
parser.add_argument('scratch', type=Path)
parser.add_argument('--apply', action='store_true')
args = parser.parse_args()
artifacts = ROOT.parent / 'scratch-ci-artifacts-43430675981'
metadata_path = ROOT.parent / 'codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/lead-ci-run-43430675981-failures-20261113.json'
metadata_raw = metadata_path.read_bytes()
metadata = json.loads(metadata_raw)
assert metadata['run_id'] == '43430675981'
commit = subprocess.check_output(['git', 'rev-parse', '4b1463bc7^{commit}'], cwd=ROOT, text=True).strip()
assert metadata['head'] == commit
selected = (1, 2, 3, 5, 7, 8, 9, 11, 12)
assert sorted(int(job['name'].rsplit(' ', 1)[1]) for job in metadata['jobs']
              if job['name'].startswith('Python 3.12 / shard ') and job['conclusion'] == 'success') == list(selected)
staging = args.scratch / 'successful-ordinary-inputs'
staging.mkdir(exist_ok=True)
dedicated = set(DEDICATED_CASE_LANES.values())
for number in selected:
    relative = Path(f'tests-py3.12-shard{number}/pytest.xml')
    original = artifacts / relative
    assert original.is_file() and original.stat().st_size
    target = staging / relative
    target.parent.mkdir(exist_ok=True)
    if not target.exists():
        target.symlink_to(original)
    assert target.resolve() == original.resolve()
    for case in ET.parse(original).iter('testcase'):
        node = case.attrib['classname'].replace('.', '/') + '.py::' + case.attrib['name']
        assert node not in dedicated, ('dedicated time in ordinary input', node)
# Do not catch or work around updater refusal.
measured = build(staging, ROOT, int(metadata['run_id']), commit)
path = ROOT / 'utils/ci_test_durations.json'
old_raw = path.read_bytes()
old = json.loads(old_raw)
new = deepcopy(old)
key = 'successful_ordinary_refresh_43430675981_20261113'
assert key not in new['source'], 'already applied'
new['source'][key] = dict(
    kind='Partial successful ordinary-shard JUnit refresh; overall run failed',
    measurement=measured['source'],
    selected_shards=list(selected),
    excluded_shards={'4': 'No artifact; assignment excludes it', '6': 'Failed', '10': 'Failed'},
    input_directory=str(artifacts),
    run_metadata=dict(path=str(metadata_path), sha256=hashlib.sha256(metadata_raw).hexdigest()),
    previous_snapshot_sha256=hashlib.sha256(old_raw).hexdigest(),
    previous_measured_values={name: old['file_seconds'].get(name) for name in measured['file_seconds']},
    method=measured['method'],
    limits='Only successful ordinary XML included. Unmeasured values and prior provenance retained. No wall-time or successful-run claim.')
new['file_seconds'].update(measured['file_seconds'])
assert all(new[k] == v for k, v in old.items() if k not in ('source', 'file_seconds'))
assert all(new['source'][k] == v for k, v in old['source'].items())
assert all(new['file_seconds'][k] == v for k, v in old['file_seconds'].items() if k not in measured['file_seconds'])
for node in dedicated:
    assert node.split('::')[0] != 'tests/test_native_shared_execution_failure.py' or node.split('::')[0] not in measured['file_seconds']
summary = dict(run=metadata['run_id'], commit=commit, artifacts=len(measured['source']['artifacts']),
               test_cases=measured['source']['test_cases'], measured_files=len(measured['file_seconds']),
               added_files=len(set(measured['file_seconds']) - set(old['file_seconds'])),
               retained_unmeasured_files=len(set(old['file_seconds']) - set(measured['file_seconds'])),
               total_files=len(new['file_seconds']),
               changed_files=sum(old['file_seconds'].get(k) != v for k, v in measured['file_seconds'].items()),
               prior_provenance_preserved=True, dedicated_cases_in_inputs=0)
candidate = args.scratch / 'timings-candidate.json'
candidate.write_text(json.dumps(new, indent=2) + '\n')
summary['candidate_sha256'] = hashlib.sha256(candidate.read_bytes()).hexdigest()
(args.scratch / 'timings-summary.json').write_text(json.dumps(summary, indent=2) + '\n')
if args.apply:
    path.write_bytes(candidate.read_bytes())
    assert path.read_bytes() == candidate.read_bytes()
print(json.dumps(summary, indent=2))

"""Prepare one offline C integration snapshot for R9-3, 2026-11-08.

Inputs: locally available final C commit, A6 worktree files. Outputs: fresh
scratch snapshot and provenance JSON; no network or native program execution.
C files are copied byte-for-byte; only A registration and test tooling differ.
"""
import importlib.util
import argparse
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('mutation', ROOT / 'scripts/adhoc/mutate_native_u3a_round2_20261107.py')
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
helper.SCRATCH = ROOT.parent / 'scratch-native-u3a-r6'
BASE = 'd205ceddee386acd4749b779cc18b3e78d094b93'
target = helper.SCRATCH / 'c-source'
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--refresh-probe', action='store_true')
args = parser.parse_args()
helper.quiet()
if not args.refresh_probe:
    helper.new_copy(BASE, target)
else:
    assert not helper.git(target, 'status', '--porcelain')
files = {
    'src/data_sheets_schema/native_execution_registration_v2.py': 'src/data_sheets_schema/native_execution_registration_v2.py',
    'scripts/adhoc/run_native_u3a_tests_20261107.py': 'scripts/adhoc/run_native_u3a_tests_20261107.py',
    'scripts/adhoc/probe_native_u3a_round6_c_integration_20261108.py': 'tests/test_native_u3a_round6_c_integration.py',
}
for source, destination in files.items():
    shutil.copyfile(ROOT / source, target / destination)
helper.git(target, 'add', '--', *files.values())
helper.git(target, 'commit', '-qm', 'test: final C with exact A6 preparation fix')
helper.save(helper.SCRATCH / ('c-snapshot-r2.json' if args.refresh_probe else 'c-snapshot.json'), {
    'base': BASE, 'commit': helper.git(target, 'rev-parse', 'HEAD').decode().strip(),
    'a_commit': helper.git(ROOT, 'rev-parse', 'HEAD').decode().strip(),
    'files': {destination: helper.sha((target / destination).read_bytes()) for destination in files.values()},
    'diff': helper.git(target, 'diff', '--stat', BASE, 'HEAD').decode(),
})

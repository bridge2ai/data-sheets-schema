"""Verify assigned artifacts, protected-file diff and authored character rule.

Inputs: handoff path. Outputs: printed hashes and validation facts for handoff.
Variant advance assignment, 2026-11-15.
"""
import hashlib
from pathlib import Path
import subprocess
import sys

protected = ['src/data_sheets_schema/shared_generation.py', 'src/data_sheets_schema/api_runner.py',
             'src/download/prompts/canonical_hashes.yaml', 'tests/utils/run_spec_boundary_contracts.json',
             '.claude/skills/d4d-generation-specificity-audit']
assert not subprocess.check_output(['git', 'diff', '9b6288df6', '--', *protected])
subprocess.run(['git', 'diff', '--check'], check=True)
diff = subprocess.check_output(['git', 'diff', '9b6288df6', '--unified=0'], text=True)
assert not any(chr(64) in line for line in diff.splitlines() if line.startswith('+') and not line.startswith('+++'))
for path in Path('scripts/adhoc').glob('*variant*20261115.py'):
    assert chr(64) not in path.read_text(), path
for name in ('scripts/adhoc/collect_native_failure_evidence.py', 'tests/test_native_failure_artifacts.py'):
    assert chr(64) not in Path(name).read_text(), name
path = Path(sys.argv[1])
raw = path.read_bytes()
assert raw and bytes([64]) not in raw
scratch = Path.cwd().parent / 'scratch-variant-advance-20261115'
for name in ('profile-run', 'variant-profile-run', 'variant-profile-v2-run', 'variant-profile-v3-run',
             'variant-unprofiled-run', 'fixture-advance-run', 'targeted', 'advance-tests',
             'collection', 'collector-cli-run'):
    for member in ('command.json', 'output.log', 'result.json'):
        assert (scratch / name / member).is_file(), (name, member)
for name in ('profile/metrics.json', 'variant-profile-v3/consumed-integration.pickle',
             'variant-profile-v3/fixture-data.pickle', 'variant-profile-v3/metrics.json',
             'variant-profile-v3/integration-6.prof', 'variant-profile-v3/integration-6.txt',
             'variant-profile-v3/profile-costs.json', 'variant-profile-v3/unprofiled.json',
             'fixture-advance/advance.prof', 'fixture-advance/advance.txt', 'fixture-advance/metrics.json',
             'targeted.xml', 'advance-tests.xml', 'test-results/native-failure/manifest.json',
             'base-commit.txt', 'ci-commit.txt'):
    assert (scratch / name).is_file() and (scratch / name).stat().st_size, name
for name in ('tests/native_shared_omission_fixture.py', 'tests/test_native_shared_stages.py',
             'tests/test_native_u3d_guard_contract.py', 'tests/test_native_shared_publication.py',
             'tests/test_native_shared_saved_advance.py', 'src/data_sheets_schema/native_shared_stage/__main__.py'):
    assert Path(name).is_file(), name
print('Protected files and scanner unchanged; diff whitespace and authored character checks passed.')
print('Named source, profile, fixture and command-evidence paths exist; substantive artifacts are nonempty.')
print(str(path))
print(hashlib.sha256(raw).hexdigest())

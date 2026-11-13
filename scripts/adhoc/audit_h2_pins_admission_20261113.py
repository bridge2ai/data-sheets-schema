#!/usr/bin/env python3
"""Read-only final source checks, 2026-11-13.
Inputs helper-2 branches and candidate git objects. Outputs protected-file,
source-anchor negative-test, runner privacy, syntax and timing-location evidence.
The documentation generator's negative test must not write any document/output.
"""
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

R = Path(__file__).resolve().parents[2]; E = R.parent
HP = E / 'codex-native-host-power-20261113'
C = E / 'codex-native-production-run-limits-20261112'
W = E / 'codex-native-helper-cache-home-20261112'
B = Path.home() / 'agent-work/data-sheets-schema/helper2-pins-admission-20261113'
BASE = 'f7f8e8bff6ea14006957d8631f66346d91bcddcd'
sha = lambda raw: hashlib.sha256(raw).hexdigest()
def git(root, *args):
    return subprocess.check_output(['git', *args], cwd=root)
protected = ['src/data_sheets_schema/' + name for name in
    ('shared_generation.py', 'api_runner.py', 'native_subscription_guard.py')]
protected += ['src/download/prompts/canonical_hashes.yaml', 'tests/utils/run_spec_boundary_contracts.json']
checks = []
for root in (HP, C, W):
    for name in protected:
        expected = sha(git(root, 'show', BASE + ':' + name))
        actual = sha((root / name).read_bytes())
        assert actual == expected
        checks.append(dict(branch=root.name, path=name, sha256=actual, equals_candidate=True))
doc = C / 'docs/native-run-limits.md'; before = sha(doc.read_bytes())
command = [sys.executable, '-B', str(C / 'scripts/adhoc/audit_run_limits_20261113.py'),
    '--output', str(B / 'missing-anchor-must-not-exist')]
result = subprocess.run(command, cwd=C, text=True, capture_output=True)
assert result.returncode != 0 and 'required combined timer anchor' in result.stderr
assert before == sha(doc.read_bytes()) and not (B / 'missing-anchor-must-not-exist').exists()
(B / 'docs-anchor-refusal.log').write_text(result.stderr)
runner_names = ('run_helper_cache_tests_20261112.py', 'run_native_h2_tests_20261112.py',
    'run_native_h2_sequence_tests_20261112.py')
privacy = []
for name in runner_names:
    path = HP / 'scripts/adhoc' / name; text = path.read_text()
    assert not re.search(r'/Users/|/home/[^/\s]+|node/v\d', text)
    assert 'shutil.which(name)' in text and "Path.home().glob('.nvm/versions/node/*/bin/' + name)" in text
    privacy.append(dict(path=str(path.relative_to(HP)), sha256=sha(path.read_bytes()), personal_literal=False))
changed = git(HP, 'diff', '--name-only', 'a2db8ab6b', 'HEAD').decode().splitlines()
for name in changed:
    if name.endswith('.py'): ast.parse((HP / name).read_bytes(), filename=name)
locations = []
for name in ('native_pre_dispatch_timing.py', 'native_shared_registration_orchestration.py',
    'native_subscription_capture.py', 'native_execution_orchestration.py', 'native_admission_timer.py'):
    path = HP / 'src/data_sheets_schema' / name
    for number, line in enumerate(path.read_text().splitlines(), 1):
        if any(anchor in line for anchor in ('pre_timing.', 'def _current_authority',
            'def _authority_from_value', 'def current_guard_preparation', 'def step(',
            'ADMISSION_SECONDS =', 'setitimer(', 'class AdmissionExpired')):
            locations.append(dict(path=str(path.relative_to(HP)), line=number, text=line.strip()))
record = dict(heads={root.name: git(root, 'rev-parse', 'HEAD').decode().strip() for root in (HP,C,W)},
    protected=checks, mandatory_anchor_refusal=dict(returncode=result.returncode, document_unchanged=True,
        log_sha256=sha((B / 'docs-anchor-refusal.log').read_bytes())), privacy=privacy,
    privacy_search_includes_hidden_ignored=True, syntax_checked=[name for name in changed if name.endswith('.py')],
    locations=locations)
path = B / 'source-audit.json'; path.write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps(dict(path=str(path), sha256=sha(path.read_bytes()), heads=record['heads'])))

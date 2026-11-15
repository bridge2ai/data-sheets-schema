"""Record ancestor correction validation for the public-stale assignment, 2026-11-15.

Inputs: saved JUnit and collection logs. Output: new section in lead handoff.
"""
import hashlib
from pathlib import Path
import xml.etree.ElementTree as ET

root = Path(__file__).resolve().parents[2]
base = root.parent
scratch = base / 'scratch-public-stale-20261115'
handoff = base / 'codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/codex-public-stale-20261115.md'
pin = hashlib.sha256((root / 'src/data_sheets_schema/native_environment_manifest.py').read_bytes()).hexdigest()
results = []
for name in ('ancestor-units', 'ancestor-registration'):
    path = scratch / (name + '.xml')
    cases = list(ET.parse(path).getroot().iter('testcase'))
    failures = sum(case.find('failure') is not None or case.find('error') is not None for case in cases)
    results.append(f'{name}: {len(cases)} cases, {failures} failures or errors')
collection = (scratch / 'ancestor-collection.log').read_text()
summary = next(line for line in reversed(collection.splitlines()) if 'collected' in line)
body = f'''# Ancestor identity correction implemented; lead commit required before measurement

The correction is implemented. Git add refused creation of the worktree index.lock with Operation not permitted, so no commit was made. Following the correction's explicit fallback, no new make_case measurement or public-case run was attempted. The lead must commit the corrected source before those measurements; capture-to-dispatch and complete after times remain unmeasured.

The resolver now records and rechecks device, inode and file type for ancestor objects, plus the readlink target for symlinks. Payload file identity and the import-root directory identity are unchanged. Freshness, windows, deadlines, fixture timestamp order and scanner pins are unchanged.

Validation in the existing isolated venv:

'''
body += ''.join('- ' + result + '\n' for result in results)
body += f'''- Collection: {summary}
- git diff --check passed.

The three collection errors are the expected missing FAIRSCAPE-model imports in test_canonical_routes.py, test_forward_typed_projections.py and test_nested_dataset_readback.py.

The earlier ancestor-focused run also included test_native_execution_registration_v2.py and was interrupted during its costly real installed-environment preparation after the unit suites had progressed successfully. That interrupted run emitted a pytest teardown KeyError and is not a passing registration result. Its log and JUnit remain saved. The clean ancestor-units rerun excludes that real registration module. Complete real registration validation remains pending the lead commit, alongside the public canary and timing measurements.

The census suite includes new successful cases for creating and removing an unrelated sibling directory during a census. Existing ancestor replacement, symlink retargeting, payload, metadata, RECORD, implementation, unowned-file, memo and publication-race tests were retained. A separate read-only diff review confirmed that only the resolver uses the new identity helper; no additional finding was identified.

New native_environment_manifest.py SHA-256 pin proposal: `{pin}`. Apply only after lead review; scan.py was not edited.

Files for the lead to commit:

- src/data_sheets_schema/native_environment_manifest.py
- tests/test_native_environment_census.py (already untracked at turn start; includes the prior adversarial suite and two new tests)
- scripts/adhoc/write_ancestor_correction_handoff_20261115.py

Pre-existing untracked helpers were preserved: scripts/adhoc/test_census_candidate_20261115.py and scripts/adhoc/write_census_handoff_20261115.py. No push or GitHub write occurred.

Evidence root: {scratch}

Saved evidence: ancestor-units.log and ancestor-units.xml; ancestor-focused.log and ancestor-focused.xml; ancestor-registration.log and ancestor-registration.xml; ancestor-collection.log. Clean unit validation used tests/test_native_environment_census.py, tests/test_native_environment_manifest.py, tests/test_native_environment_modes.py, tests/test_native_subscription_guard.py and tests/test_native_subscription_guard_v2.py. The registration shape run used tests/test_native_environment_registration.py. Collection used pytest --collect-only -q tests. All ran with PYTHONPATH pointing to this worktree's src and the isolated-venv/bin/python3.13 interpreter under the evidence root.

Next, after the lead commit: run the complete phase measurement and one externally bounded public correction case using the retained profiler and public measurement helpers, and measure the actual capture-to-dispatch interval. The existing public helper records launch entry, so that timestamp alone must not be reported as dispatch.
'''
assert chr(64) not in body
handoff.write_text(body + '\n<!-- prior handoff -->\n' + handoff.read_text())
assert handoff.stat().st_size
print(handoff)
print(hashlib.sha256(handoff.read_bytes()).hexdigest())

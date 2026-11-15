"""Verify issue 6246 template provenance and findings, 2026-11-15.
Inputs: Git base, working scanner, saved scan reports. Output: evidence JSON.
"""
import ast
import hashlib
import json
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[2]
scratch = root.parent / 'scratch-scanner-v3-template-20261115'
relative = '.claude/skills/d4d-generation-specificity-audit/scan.py'
base = ast.parse(subprocess.check_output(['git', 'show', 'f10e8ae20:' + relative], cwd=root))
current = ast.parse((root / relative).read_bytes())
def assignments(tree):
    return [ast.dump(node) for node in tree.body if isinstance(node, (ast.Assign, ast.AnnAssign))]
assert assignments(base) == assignments(current)
old_function = next(n for n in base.body if isinstance(n, ast.FunctionDef) and n.name == '_derive_native_v2_render')
old_template = next(n.value.args[0] for n in ast.walk(old_function) if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'expected_module' for t in n.targets))
helper = next(n for n in current.body if isinstance(n, ast.FunctionDef) and n.name == '_native_producer_module_matches')
v2 = next(n.value for n in helper.body if isinstance(n, ast.Assign) and n.targets[0].id == 'v2_template')
assert ast.literal_eval(old_template) == ast.literal_eval(v2)
source_diff = subprocess.check_output(['git', 'diff', 'f10e8ae20', '--', 'src', 'tests/utils/run_spec_boundary_contracts.json'], cwd=root).decode()
assert not source_diff
changed = subprocess.check_output(['git', 'diff', '--name-only'], cwd=root).decode().splitlines()
untracked = subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard'], cwd=root).decode().splitlines()
for name in changed + untracked:
    if name != relative:
        assert chr(64) not in (root / name).read_text(), name
# Existing scanner has notification syntax; ensure additions introduce none.
patch = subprocess.check_output(['git', 'diff', '--unified=0', '--', relative], cwd=root).decode()
assert not any(chr(64) in line for line in patch.splitlines() if line.startswith('+') and not line.startswith('+++'))
result = dict(scanner_sha256=hashlib.sha256((root / relative).read_bytes()).hexdigest(),
              module_assignments_unchanged=True, historical_template_unchanged=True,
              protected_source_unchanged=True, changed_files=changed, untracked_files=untracked)
report_path = scratch / 'scan-report.json'
if report_path.exists():
    report = json.loads(report_path.read_text())
    baseline_path = root.parent / 'scratch-scanner-6245-20261115/baseline-frozen.json'
    baseline = json.loads(baseline_path.read_text())
    result['report_keys'] = list(report)
    result['violations'] = report['violations']
    result['violation_count'] = len(report['violations'])
    result['baseline_violation_count'] = len(baseline['violations'])
    result['violations_equal'] = report['violations'] == baseline['violations']
(scratch / 'evidence.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
if report_path.exists():
    differences = {}
    for key in ('gc_project_hits', 'test_dependencies', 'counts_by_file', 'totals', 'exceptions', 'surfaces'):
        if report[key] != baseline[key]:
            before, after = baseline[key], report[key]
            if isinstance(before, list) and isinstance(after, list):
                differences[key] = dict(removed=[v for v in before if v not in after], added=[v for v in after if v not in before])
            elif isinstance(before, dict) and isinstance(after, dict):
                differences[key] = {name: dict(before=before.get(name), after=after.get(name))
                                    for name in sorted(before.keys() | after.keys())
                                    if before.get(name) != after.get(name)}
            else:
                differences[key] = dict(before=before, after=after)
    (scratch / 'finding-differences.json').write_text(json.dumps(differences, indent=2) + '\n')
    print('Finding difference categories:', list(differences))
    summary = {}
    for path, pair in differences.get('surfaces', {}).items():
        before, after = pair['before'], pair['after']
        summary[path] = {'added': after} if before is None else {
            key: dict(before=before.get(key), after=after.get(key))
            for key in sorted(before.keys() | after.keys()) if before.get(key) != after.get(key)}
    (scratch / 'surface-differences.json').write_text(json.dumps(summary, indent=2) + '\n')
    compact = {}
    for path, fields in summary.items():
        compact[path] = {}
        for key, values in fields.items():
            if key == 'text_spans':
                compact[path][key] = dict(removed=[v for v in values['before'] if v not in values['after']], added=[v for v in values['after'] if v not in values['before']])
            else:
                compact[path][key] = values
    (scratch / 'surface-differences-compact.json').write_text(json.dumps(compact, indent=2) + '\n')
fixture = json.loads((root / 'tests/fixtures/native_u3l_review_cases.json').read_text())
anchor_failures = []
for case in fixture['cases']:
    sources = {}
    for relative, before, after in case['edits']:
        source = sources.get(relative)
        if source is None and before is not None:
            source = (root / relative).read_text()
        if before is not None:
            count = source.count(before)
            if count != 1:
                anchor_failures.append(dict(case=case['name'], path=relative, anchor_count=count))
                break
            source = source.replace(before, after, 1)
        else:
            source = after
        sources[relative] = source
(scratch / 'fixture-anchor-diagnosis.json').write_text(json.dumps(anchor_failures, indent=2) + '\n')
print('Fixture anchor failures:', json.dumps(anchor_failures))
import xml.etree.ElementTree as ET
if (scratch / 'required.xml').exists() and (scratch / 'remaining.xml').exists():
    cases = {}
    for label in ('required', 'remaining'):
        for case in ET.parse(scratch / (label + '.xml')).iter('testcase'):
            if 'classname' not in case.attrib:
                print('Run-level JUnit diagnostic:', ET.tostring(case, encoding='unicode'))
                continue
            key = case.attrib['classname'] + '::' + case.attrib['name']
            failure = case.find('failure')
            cases[key] = dict(passed=failure is None and case.find('error') is None,
                              failure=None if failure is None else failure.attrib.get('message'),
                              detail=None if failure is None else failure.text)
    modules = {}
    for key, value in cases.items():
        module = key.split('::')[0]
        counts = modules.setdefault(module, dict(passed=0, failed=0))
        counts['passed' if value['passed'] else 'failed'] += 1
    test_summary = dict(unique_cases=len(cases), modules=modules,
                        failures={key: value for key, value in cases.items() if not value['passed']})
    (scratch / 'test-summary.json').write_text(json.dumps(test_summary, indent=2) + '\n')
    print('Unique test modules:', json.dumps(modules))
    print('Failure messages:', json.dumps({key: value['failure'] for key, value in cases.items() if not value['passed']}))
    passed = sum(value['passed'] for value in cases.values())
    failed = len(cases) - passed
    print('Unique total:', len(cases), 'passed:', passed, 'failed:', failed)
    canary_artifact = scratch / 'canary/popen-gw0/test_6246_v3_real_source_and_c0/src/data_sheets_schema/native_execution_registration_v2.py'
    assert canary_artifact.is_file() and canary_artifact.stat().st_size > 0
    handoff = root.parent / 'codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/codex-scanner-v3-template-20261115.md'
    body = f'''# Exact v3 producer template handoff

The fix adds a separately selected exact v3 producer skeleton derived from f10e8ae20 and retains the historical v2 template unchanged. Across all assigned test cases, {passed} passed and {failed} failed, out of {len(cases)} unique cases. All failures are retained-fixture cases: nine use the unchanged committed scanner and two have obsolete v2 mutation anchors. The working-tree scan exits 1 with nine violations, exactly equal to the saved f5c7c312f baseline. Scanner SHA-256: `{result['scanner_sha256']}`.

## Fix and proof

The scanner selects the closed skeleton using the already-proved CLI version. It does not infer the accepted template from the producer being checked. Both templates retain imports, initializers, signatures, defaults, decorators and class bodies; the existing detailed producer-body proofs remain in place. The new test proves real v3 route derivation, positive matching of each historical/current producer, and both crossed-version refusals. The existing issue 6246 regression exercises all five mutation refusals against the current v3 source and passes.

The v2 template literal is byte-identical to the former template. All module-level scanner assignments are AST-identical, including pin dictionaries. No pin entry, production source, protected file, or historical fixture was changed. Read-only diff review found no additional defect in the bounded scanner edit; diff whitespace checking passed.

## Tests and execution

The canary passed using the same external watchdog, interpreter, scratch location and one-worker mode as the suite. Its copied producer artifact was verified present and nonempty. It proved offline source copying and positive/crossed-template behavior, not provider or launch behavior.

Unique results by requested file:

- `tests/test_native_scanner_proof_gaps.py`: 10 passed.
- `tests/test_native_u1_scanner_contracts.py`: 84 passed.
- `tests/test_native_u3l_scanner.py`: 50 passed.
- `tests/test_native_u3l_review_fixtures.py`: 2 passed, 11 failed.
- `tests/test_native_u5_scanner.py`: 67 passed.
- `tests/test_native_h1_scanner_authority.py`: 7 passed.
- `tests/test_native_u4b_a5_scanner.py`: 23 passed.
- `tests/test_generation_specificity_skill.py`: 381 passed.

The initial all-file invocation recorded 160 passes and 11 failures. After all retained fixtures finished, it had started repeating modules already completed in the separate invocation. I sent SIGINT to that pytest controller to stop duplicate coverage; it wrote its JUnit report and exited 2. That exit denotes the deliberate interruption, not a scanner configuration result. The separate final-four-module invocation completed with 478 passes, one warning and exit 0. JUnit identities were deduplicated to obtain the unique totals above. No test case is omitted from the combined results. Neither watchdog timed out.

All test and scan processes used the primary checkout's virtual-environment Python, this worktree's src directory in PYTHONPATH, and scratch basetemps. Each pytest invocation used one worker; at most two ran concurrently. External process-group watchdogs bounded execution without inherited alarms. No provider, native binary, network action, push, pull request or GitHub write was performed.

## Retained-fixture failures and next steps

The tests export committed HEAD, still f10e8ae20 because the authorized commit attempt was refused at index.lock. They therefore do not exercise the edited scanner. Nine failures encounter its known v2-only module-template refusal: F0, F2a, F3a, F3a2, F3b, F3c, F3d, B2 and B3. F1 and B1 pass their intended refusal checks.

F2b and F2c fail before invoking the scanner: their frozen mutation anchor calls the former controls-based envelope, which the v3 source replaces with the wire envelope. The saved anchor diagnosis confirms zero occurrences in current source. These historical fixtures were not rewritten or weakened. The lead should commit the scanner fix, rerun retained fixtures, and separately decide how to version or adapt those v2 fixtures for v3. A green complete acceptance suite and D128 approval are not claimed.

## Scan comparison

`scan-report.json` contains complete violation objects and the standard summary. Its nine violations are exactly equal to `scratch-scanner-6245-20261115/baseline-frozen.json`. Project-token findings, test dependencies, per-file counts, totals and exceptions are also exactly equal. No reported finding changed. This was the standard summary scan, not a new full-hit D128 comparison.

The surface metadata differs only in these places: native_environment_manifest is added as a run-shaping import-closure surface; native_command_policy's reference to run_native_canary moves from line 823 to 848; run_native_canary's text spans move correspondingly; typed_audit's source spans relocate after changes already in the assigned base. These are metadata/source changes, not new findings. Exact objects are saved in `surface-differences-compact.json`.

## Files and evidence

Worktree: `{root}`.
Branch: `codex/scanner-v3-template-20261115`.
Base and unchanged HEAD: `f10e8ae20d5450d1933e624c6cb88bdd98900c9b`.
Scratch: `{scratch}`.

The commit attempt failed with Operation not permitted creating the worktree index.lock. Per assignment, these files remain uncommitted for the lead:

'''
    body += ''.join('- `' + name + '`.\n' for name in changed + untracked)
    body += '''
The template builder records the exact reviewed Git source. The runner records exact commands, exit status and watchdog outcome. The evidence helper verifies template preservation, unchanged constants and source, scan comparison, fixture anchors and deduplicated JUnit results.

Saved evidence in scratch: `canary.log`, `canary.json`, `required.log`, `required.xml`, `required.json`, `remaining.log`, `remaining.xml`, `remaining.json`, `scan.log`, `scan.json`, `scan-report.json`, `scan.md`, `evidence.json`, `evidence-final.log`, `test-summary.json`, `fixture-anchor-diagnosis.json`, and `surface-differences-compact.json`. The run-level empty JUnit testcase created during interruption is explicitly recorded and excluded from test identity counts. An initial evidence aggregation attempt stopped on that synthetic record; the final helper handles it without changing any test result.
'''
    for name in changed + untracked:
        assert (root / name).is_file()
    for name in ('canary.log', 'canary.json', 'required.log', 'required.xml', 'required.json', 'remaining.log', 'remaining.xml', 'remaining.json', 'scan.log', 'scan.json', 'scan-report.json', 'scan.md', 'evidence.json', 'test-summary.json', 'fixture-anchor-diagnosis.json', 'surface-differences-compact.json'):
        assert (scratch / name).is_file()
    assert chr(64) not in body
    handoff.write_text(body)
    print('Handoff:', handoff)
    print('Handoff SHA-256:', hashlib.sha256(handoff.read_bytes()).hexdigest())

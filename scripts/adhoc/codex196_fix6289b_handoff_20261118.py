"""Save the issue 6289 CI diagnosis and decision handoff; 2026-11-18.

Inputs: assigned checkout, preserved CI logs/JUnit, timing audit, local JUnit.
Outputs: source evidence, verification receipt, and the requested handoff.
Serves PR 5968. Does not modify code, pins, measured timings, or Git history.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(root, *args):
    return subprocess.check_output(['git', *args], cwd=root, text=True).strip()


def cases(path):
    return [{'classname': row.get('classname'), 'name': row.get('name'),
             'seconds': row.get('time'),
             'outcome': 'failed' if row.find('failure') is not None else
                        'error' if row.find('error') is not None else
                        'skipped' if row.find('skipped') is not None else 'passed'}
            for row in ET.parse(path).iter('testcase')]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--scratch', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    root, scratch = args.root, args.scratch
    audit = json.loads((scratch / 'timing-history-audit.json').read_text())
    baseline = cases(scratch / 'f1-baseline-junit.xml')
    isolation = cases(scratch / 'f2-environment-junit.xml')
    ci = cases(scratch / 'ci-shard11.xml')
    denied = [row for row in ci if row['classname'].startswith('tests.test_native_shared_denials')]
    head = git(root, 'rev-parse', 'HEAD')
    assert head == audit['head']
    assert git(root, 'status', '--porcelain') == ''
    assert len(baseline) == 1 and baseline[0]['outcome'] == 'failed'
    assert len(isolation) == 2 and all(row['outcome'] == 'passed' for row in isolation)
    denial_paths = sorted(root.glob('tests/test_native_shared_denials*.py'))
    missing = [p.relative_to(root).as_posix() for p in denial_paths
               if '_native_helper_import_environment' not in p.read_text()]
    prior = git(root, 'show', 'a6d773e6a^:tests/test_native_shared_denials.py')
    prior_missing = '_native_helper_import_environment' not in prior
    ranges = {
        'tests/test_native_shared_execution.py': [(28, 46), (285, 299)],
        'tests/test_native_shared_execution_variant.py': [(10, 15)],
        'tests/test_native_execution_registration_v2.py': [(24, 36), (59, 66)],
        'tests/utils/native_helper_environment.py': [(9, 35)],
        'tests/test_cborg_completed_reporting.py': [(14, 19)],
        'tests/test_check_large_files.py': [(13, 18)],
        'src/data_sheets_schema/native_shared_results_orchestration.py': [(335, 385), (405, 410)],
        'src/data_sheets_schema/native_execution_orchestration.py': [(631, 644), (740, 755), (770, 772)],
        'src/data_sheets_schema/native_environment_manifest.py': [(720, 729), (792, 799), (844, 859)],
        'src/data_sheets_schema/native_shared_capture_orchestration.py': [(173, 185), (464, 475)],
        'src/data_sheets_schema/native_shared_registration_orchestration.py': [(187, 193)],
        'src/data_sheets_schema/cli/receipts.py': [(142, 151)],
        'src/data_sheets_schema/native_shared_render.py': [(263, 272)],
        'src/data_sheets_schema/native_shared_permission_protocol.py': [(13, 20)],
        'src/data_sheets_schema/native_runtime_profiles.py': [(20, 24)],
        'src/data_sheets_schema/native_admission_timer.py': [(13, 16), (27, 38)],
        'tests/utils/native_synthetic_evidence.py': [(37, 48)],
        'tests/fixtures/native_shared_execution/fake_cli.py': [(176, 182), (218, 228), (250, 263), (309, 332)],
        'notes/matched_cborg_2026-09-13/native_controls/run_native_canary.py': [(604, 625), (651, 677)],
        'notes/matched_cborg_2026-09-13/native_controls/native_control.py': [(433, 469), (497, 505), (535, 545)],
    }
    evidence = {}
    for relative, spans in ranges.items():
        raw = subprocess.check_output(['git', 'show', f'HEAD:{relative}'], cwd=root)
        lines = raw.decode().splitlines()
        evidence[relative] = {
            'blob_sha256': hashlib.sha256(raw).hexdigest(),
            'excerpts': [{'line': number, 'text': lines[number - 1].replace(chr(64), '(at)')}
                         for start, stop in spans for number in range(start, min(stop, len(lines)) + 1)]}
    source_path = scratch / 'f2-source-evidence.json'
    source_path.write_text(json.dumps({'head': head, 'denial_files_missing_fixture': missing,
        'omission_present_before_split': prior_missing, 'sources': evidence}, indent=2) + '\n')
    receipt_path = scratch / 'diagnosis-receipt.json'
    saved = ['ci-shard5.log', 'ci-shard11.log', 'ci-shard11.xml',
             'f1-baseline.log', 'f1-baseline-summary.json', 'f1-baseline-junit.xml',
             'f2-environment.log', 'f2-environment-summary.json', 'f2-environment-junit.xml',
             'timing-history-audit.json', 'proposed-measured-base.json',
             'proposed-scheduling-overrides.json', 'f2-source-evidence.json']
    receipt = {'head': head, 'branch': git(root, 'branch', '--show-current'),
               'source_status': 'clean', 'sparse_paths': git(root, 'sparse-checkout', 'list').splitlines(),
               'f1_baseline': baseline, 'f2_isolation_regressions': isolation,
               'ci_denial_results': denied, 'denial_files_missing_fixture': missing,
               'omission_present_before_split': prior_missing,
               'artifacts': {name: sha(scratch / name) for name in saved},
               'handoff_writer_sha256': sha(Path(__file__)),
               'timing_diagnosis_script_sha256': sha(Path(__file__).with_name(
                    'codex196_fix6289b_timing_diagnosis_20261118.py'))}
    receipt_path.write_text(json.dumps(receipt, indent=2) + '\n')
    r = args.report.parents[3]
    helper1 = r / 'scripts/adhoc/codex196_fix6289b_timing_diagnosis_20261118.py'
    helper2 = Path(__file__).resolve()
    assert helper1.is_file()
    read_case = next(row for row in denied if row['classname'].endswith('_read'))
    bash_case = next(row for row in denied if row['name'].endswith('[Bash-unclassifiable]'))
    report = f'''# CI failures at 7b9497fc1: decision handoff

F1 is reproduced and not fixed: keeping the accepted scheduling estimates while leaving the historical test unchanged requires an explicit override design. The assignment requires the lead's decision before implementation. I recommend the separate, base-bound override file below; no approval has arrived and no implementation commit is claimed. F2 has a concrete, preexisting helper-environment fixture omission, but the truncated CI result does not prove the originating failure. A test-only correction and a diagnostic assertion are proposed below.

The assigned worktree is `{root}`, branch `{receipt['branch']}`, clean at `{head}`. It was created detached at the assigned target, then given its own branch before any potential edit. No source, tests, timings, pins, existing commits, remote branches, or protected worktrees were changed. Disk exhaustion initially prevented helper sessions; the checkout therefore uses sparse roots `.github`, `src`, `tests`, and `utils`, plus root files. The complete tests tree and historical timing fixtures are present. No lifecycle rerun was attempted.

## F1: reproducible invariant failure and proposed fix

The unchanged test failed locally at `tests/test_ci_timing_update.py:347`, the same assertion as CI. Its historical artifact reconstruction succeeded up to that assertion. Saved result: `{scratch / 'f1-baseline-junit.xml'}`; runner receipt: `{scratch / 'f1-baseline-summary.json'}`. This is a reproduction, not a passing check.

The audit identifies {audit['override_count']} effective scheduling changes: {audit['changed_keys']} existing values and {audit['new_keys']} new keys. The historical refresh remains tied to immutable successful JUnit artifacts. The current updater rejects failed artifacts and derives weights exclusively from recorded case durations. It cannot derive the unmeasured denial/rehearsal estimates or substitute new measurements into that fixed historical oracle. Adding another source field also breaks the later whole-document historical snapshot assertion, even if the active weights alone are restored.

Computed identities:

- Current timing file: `{audit['current_timing_sha256']}`.
- Proposed byte-exact measured base: `{audit['restored_timing_sha256']}`.
- Required historical snapshot: `{audit['historical_snapshot_expected_sha256']}`.
- Current reconstructed historical snapshot: `{audit['historical_snapshot_actual_sha256']}`.

The concrete proposal is saved as `{scratch / 'proposed-measured-base.json'}` and `{scratch / 'proposed-scheduling-overrides.json'}`. The audit proves that overlaying the proposed overrides on the measured base exactly preserves every active scheduling weight. Removing the newly added provenance from the historical document also restores the required historical snapshot hash.

Recommended implementation, pending the lead's decision:

1. Restore `utils/ci_test_durations.json` byte-for-byte to the proposed measured base. Leave `tests/test_ci_timing_update.py` unchanged.
2. Add a separate scheduling-estimate document containing the existing estimates and provenance, a schema version, and the measured base SHA-256. The concrete draft above already contains these bytes.
3. Add an explicit `--ci-shard-overrides` option to the sharder and activate it in the ordinary CI command alongside `--ci-shard-timings`. Require the timing option and matching base digest; reject duplicate keys and nonpositive, nonfinite, boolean, or malformed durations. Dedicated lanes must reject this option, as they reject the existing scheduling options.
4. Add focused tests for unchanged historical reconstruction, opt-in activation, stale-base and malformed-input refusal, exact effective-weight preservation, and unchanged coverage under the ordinary sharder. Existing initial-load tests remain applicable. Keep measurement refresh and scheduling estimates explicitly distinct in documentation.

This is an approval request required by the assignment sentence, "If the invariant genuinely cannot hold for an override, propose the minimal, explicit, test-covered override mechanism and explain why, before you implement it." It is not a request to weaken the historical test. An asynchronous design question was submitted; silence is not approval.

F1 summary: reproduced; exact weight-preserving proposal prepared; no fix commit pending the required design decision.

## F2: source diagnosis and bounded verification

The preserved CI JUnit records Read-not_prescribed as {read_case['outcome']} in {read_case['seconds']} seconds and Bash-unclassifiable as {bash_case['outcome']} in {bash_case['seconds']} seconds. The reconciliation path is consistent with `capture_problems` from `native_shared_results_orchestration.py:363`: incomplete capture tries to retain full/core/report and appends the exception for the missing report. The launcher copies this list into the final result at `native_execution_orchestration.py:770`. The log also shows `additional_report: None`. This is downstream incomplete-output evidence; it does not identify the first failing gate.

A concrete fixture omission exists in all {len(missing)} denial modules, including the original unsplit module before the sharding commit. They import `make_case` and `launch_case` but omit `_native_helper_import_environment`. The public variant explicitly imports that autouse fixture. The omission is therefore preexisting, not caused by moving the Read test into a separate file.

Why it can fail on the complete CI collection but pass in a focused local invocation:

- Other modules insert extra import roots during collection, including `tests/test_cborg_completed_reporting.py:16` and `tests/test_check_large_files.py:15`.
- `make_case` writes the environment manifest in the parent pytest interpreter at `tests/test_native_shared_execution.py:40`. The existing `isolated_modules` fixture clears module aliases but preserves the starting import path. Parent preparation and validation can therefore agree on the polluted environment.
- The real helper interpreter does not inherit pytest's import-path additions. The existing `tests/utils/native_helper_environment.py` fixture obtains that helper path before preparation and restores the original path afterward.
- The manifest binds excluded roots and unowned files, and the light census compares their full canonical identity at `native_environment_manifest.py:844`. A different helper import environment is correctly refused.
- The directly traced helper path is receipts CLI to `selected_receipt_paths` to `_base(..., _manifest_mode='light')` to execution registration verification. The CLI can report `native receipt paths refused: environment manifest is stale for the current interpreter environment` before the reconciliation report is written.
- Bash-unclassifiable deliberately terminates before the helper cycle; its successful refusal is compatible with the Read completion case failing later.

Confidence is high that the fixture omission is real and a test-only correction is appropriate. Confidence is limited that this caused the reported CI failure: the original first stop and gate details are truncated. This is a collection-environment hypothesis, not proof of an operating-system defect or a contention timeout.

The source defines separate bounds: admission is 1500 seconds; the synthetic child attempt is 9600 seconds from dispatch; each real Bash helper is capped at 1000 seconds; initialization is 60 seconds; classification is 4 seconds; the observer is 240 seconds; the callback response is 250 seconds from intake. The peer's advance loop is limited to 40 iterations per invocation and is invoked twice. The overall pytest duration includes preparation, execution, capture, and publication and cannot identify which bound fired. Source excerpts and their computed blob hashes are retained in `{source_path}`; no bound was changed.

Recommended test-only correction: import the existing fixture into the denial modules, using the public variant's established pattern:

```python
from tests.test_native_shared_execution import _native_helper_import_environment  # noqa: F401
```

For the next CI attempt, preserve the runtime assertion and replace only its opaque dictionary message with a focused JSON message:

```python
import json

assert result['runtime_gates_passed'], json.dumps({{
    'first_stop': result.get('first_stop'),
    'child_exit_code': result.get('child_exit_code'),
    'capture_problems': result.get('capture_problems'),
    'failing_gates': {{name: row for name, row in result.get('gates', {{}}).items()
                      if row.get('checked') is not True or row.get('passed') is not True}},
}}, indent=2)
```

These are proposals, not applied changes or proven CI fixes. The existing helper-environment regressions both pass in the assigned checkout; they verify normalization despite collection pollution and restoration after refusal. They do not exercise the complete denial lifecycle. Saved JUnit: `{scratch / 'f2-environment-junit.xml'}`; runner receipt: `{scratch / 'f2-environment-summary.json'}`. No production defect is established; no source change or pin rotation is proposed on the current evidence.

F2 summary: missing-report retention traced; preexisting fixture omission identified; isolation checks pass; first CI stop still needs untruncated diagnostics.

## Commands and retained evidence

The focused tests used the existing SIGALRM-free runner, serially, with the primary interpreter and external scratch directories. The primary editable installation points to the primary checkout; the runner explicitly set the assigned checkout's source path. These checks import only the timing utilities and test helper environment; no native manifest acceptance result is claimed.

```text
{root.parents[1] / 'data-sheets-schema/.venv/bin/python'} {root.parents[1] / 'data-sheets-schema/scripts/adhoc/run_lane_20261115.py'} --lane unit --root {root} --python {root.parents[1] / 'data-sheets-schema/.venv/bin/python'} --scratch-dir {scratch / 'f1-baseline'} --timeout-seconds 180 --json-summary {scratch / 'f1-baseline-summary.json'} -- tests/test_ci_timing_update.py::test_successful_ordinary_refresh_reconstructs_measurements_and_preserves_history -q -p no:cacheprovider --junitxml={scratch / 'f1-baseline-junit.xml'}
{root.parents[1] / 'data-sheets-schema/.venv/bin/python'} {root.parents[1] / 'data-sheets-schema/scripts/adhoc/run_lane_20261115.py'} --lane unit --root {root} --python {root.parents[1] / 'data-sheets-schema/.venv/bin/python'} --scratch-dir {scratch / 'f2-environment'} --timeout-seconds 180 --json-summary {scratch / 'f2-environment-summary.json'} -- tests/test_native_helper_environment.py -q -p no:cacheprovider --junitxml={scratch / 'f2-environment-junit.xml'}
```

The CI logs and JUnit were copied from the assignment's temporary downloads to the durable scratch directory before analysis. Evidence inventory and all artifact SHA-256 values: `{receipt_path}`. Original source/test identity remains `{head}`. Both local runner receipts report clean source paths. No paid/provider/native-binary calls, long lifecycle tests, GitHub writes, push, merge, amendment, or history rewrite occurred.

Helper provenance, left uncommitted because this turn ends at the required design decision:

- `{helper1}`.
- `{helper2}`.

Reproduce the timing audit and this handoff with:

```text
{root.parents[1] / 'data-sheets-schema/.venv/bin/python'} {helper1} --root {root} --output {scratch}
{root.parents[1] / 'data-sheets-schema/.venv/bin/python'} {helper2} --root {root} --scratch {scratch} --report {args.report}
```
'''
    assert chr(64) not in report
    args.report.write_text(report)
    assert args.report.stat().st_size > 0
    for path in (root, scratch, helper1, helper2, source_path, receipt_path,
                 root.parents[1] / 'data-sheets-schema/.venv/bin/python',
                 root.parents[1] / 'data-sheets-schema/scripts/adhoc/run_lane_20261115.py'):
        assert path.exists(), path
    print('F1: reproduced; weight-preserving override proposal needs the lead decision; no fix commit.')
    print('F2: helper fixture omission found; two isolation checks pass; CI first stop remains unconfirmed.')
    print(str(args.report) + '\nSHA-256 ' + sha(args.report))
    print(str(receipt_path) + '\nSHA-256 ' + sha(receipt_path))


if __name__ == '__main__':
    main()

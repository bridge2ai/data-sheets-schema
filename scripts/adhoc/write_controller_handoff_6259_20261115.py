"""Issues 6259/6258, 2026-11-15: write evidence-backed lead handoff.

Inputs: saved test summary, pin proposals, Git state; output: assigned handoff.
No source, pin, scanner, Git or external-service mutation.
"""
import json
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[2]
scratch = root.parent / 'scratch-codex-controller-6259-20261115'
destination = root.parent / 'codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/codex-controller-6259-6258-20261115.md'
summary = json.loads((scratch / 'test-summary.json').read_text())
pins = json.loads((scratch / 'full-pin-proposals.json').read_text())
required = ['native.xml', 'audit-parallel.xml', 'deadline.xml', 'denials.xml', 'final-targeted.xml', 'clean-import-canary.xml']
assert all(name in summary for name in required)
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
status = subprocess.check_output(['git', 'status', '--short'], cwd=root, text=True)
text = f'''The cleanup metadata fix is committed at `{commit}`. The denial fixture fix is present but uncommitted because later index-lock writes were refused. The unchanged cleanup regression and shutdown-order tests pass on the final code. Integration still requires the lead's pin rotations. All five denial cases getting past make_case remains unverified: the assigned shared interpreter fails earlier local environment checks.

Implementation and review

The original exception now carries sanitized native_cleanup_errors entries. Normal cleanup, responsive-control cleanup, and timing cleanup retain only exception class names. The audit copies these records onto native_stop without replacing the primary exception or changing the first stop. Existing note wording and the cleanup order are preserved. The required regression test was not edited. The denial test imports and requests isolated_modules; production import-origin checks are unchanged.

Read-only review checked original-exception identity, metadata copying, secret-bearing exception text, cleanup ordering, timing notes, and the complete pin chain. The timing-note assertion exposed during development was corrected before the committed source version; the focused final-code rerun passes. The initial broad native run loaded the earlier note wording, so its timing-note failures must be read together with that focused rerun.

Tests and limitations

Evidence directory: `{scratch}`.

The test runner extracts the exact audit/finalization and native file selections from the CI workflow, substitutes the assigned primary-checkout interpreter, sets the worktree source and CI support PYTHONPATH entries, disables bytecode/cache writes, and puts logs, XML and basetemp under scratch. Local Python is 3.13; CI specifies 3.12. No inherited alarm was used. Each suite has an external process-group timeout. Initial serial audit was deliberately stopped and its log/result retained; the same selection was rerun with three workers while native remained serial.

The first focused canary hit the sandbox loopback bind restriction. The authorized unrestricted offline rerun passed, proving the unchanged real-child regression can retain the primary failure and structured sanitized cleanup record. No native binary or provider call was made.

'''
for name in required:
    row = summary[name]
    counts = row['counts']
    passed = counts['tests'] - counts['failures'] - counts['errors'] - counts['skipped']
    text += f"- `{name}`: {passed} passed, {counts['failures']} failed, {counts['errors']} errors, {counts['skipped']} skipped.\n"
    for message, count in row['messages'].items():
        brief = ' '.join(message.split())[:500].replace(chr(64), '[at]')
        text += f'  Failure category, {count} cases: {brief}\n'
text += '''
The audit setup errors all arise in the checkpoint fixture's SUPPORTED_SOURCES hash assertion. The pin-proposal script verifies that audit_controls/native.py is the only current source absent from that allowlist; these are expected pin refusals. The deadline controller-byte refusals are also expected until pin rotation. The namespace refusals are local environment failures, not controller-pin failures. The ordinary denial run failed all live cases in the fixture builder's environment census before reaching the original import-origin boundary. A single clean-import canary, using the existing repository runner approach of loading physical dependencies without editable-install hooks, passed its import-origin witness but failed the environment JSON structural bound. It was not fanned out. Neither result proves the five cases pass make_case; rerun them in the lead's valid test environment after rotation. No environment guard was weakened.

Exact commands and failure traces are retained in suite result JSON, logs, XML and test-summary.json. Reproduce the CI-selected runs with the assigned interpreter and `scripts/adhoc/test_controller_cleanup_6259_20261115.py audit 3`, `native`, `deadline`, or `denials`. The clean-import probe is separately labelled diagnostic evidence, not a passing denial test.

The final targeted pytest selection was `notes/matched_cborg_2026-09-13/native_controls/test_native_launch.py::test_timing_failure_cannot_prevent_shutdown notes/matched_cborg_2026-09-13/audit_controls/test_native.py::test_real_child_controller_cleanup_cannot_replace_recorded_failure`, with `-q -p no:cacheprovider`, the CI support PYTHONPATH, and scratch final-targeted basetemp/XML/log paths. The diagnostic canary used the assigned interpreter with `-S scripts/adhoc/probe_clean_imports_6258_20261115.py tests/test_native_shared_denials.py -x -vv -p no:cacheprovider`, worktree src on PYTHONPATH, and scratch clean-import-canary basetemp/XML/log paths.

Pin proposals only

The following are exact literal-byte proposals for this commit. The full JSON also records proposed whole-file hashes and the unchanged classifier proof. If the lead uses a different source commit or changes comments while rotating, regenerate downstream hashes. No pin or scanner file was edited.

'''
for proposal in pins['proposals']:
    assert (root / proposal['file']).is_file()
    text += f"- `{proposal['file']}`; `{proposal['field']}`: `{proposal['old']}` -> `{proposal['new']}`.\n"
text += f'''
CONTROL_SHA and the native_control compatibility hashes stay unchanged: native_control.py was not touched; its computed SHA-256 is `{pins['unchanged_CONTROL_SHA']}`. Keep the historical scanner base v2 table. Integrated v2 changes flow into v3, with the additional explicit v3 wire rotation above. The audit allowlist proposal appends the new hash and retains historical hashes. Its classifier is byte-identical, with computed SHA-256 `{pins['audit_classifier_unchanged_sha256']}`.

Reproduction: `scripts/adhoc/propose_controller_pins_20261115.py {commit}` writes pin-proposals.json; `scripts/adhoc/propose_audit_cleanup_pins_6259_20261115.py` reads that JSON and writes full-pin-proposals.json. Hash searches included hidden and ignored files using rg with no-ignore. Search evidence is in controller-pin-search.txt, manifest-pin-search.txt, and audit-pin-search.txt. Historical publication provenance was not proposed for rewriting.

Delivery state

Worktree: `{root}`. Branch: `codex/controller-6259-20261115`.

The two assigned issues were read through read-only GitHub commands after the initial sandbox network refusal. No GitHub write, push, pull request, merge, branch switch, or native launch was performed. The lead owns publication. The primary checkout was not changed. Protected-file and required-regression-test diffs are empty; diff-check.txt is empty on success.

Current worktree status:

```text
{status}```

Uncommitted files are intentionally left in place for the lead after index-lock refusal. Helper scripts are on the assigned worktree under scripts/adhoc, not temporary storage. The final test summary can be regenerated with scripts/adhoc/summarize_controller_tests_6259_20261115.py.
'''
assert chr(64) not in text
destination.write_text(text)
assert destination.is_file() and destination.stat().st_size > 0
assert destination.read_text() == text
print(destination)

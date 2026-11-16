"""Report D156 receipt census correction, 2026-11-16, PR 5968.

Inputs: scratch diagnosis, lane outputs, public timing JSONL, pin proposals.
Outputs: evidence ledger and new top section in the assigned lead handoff.
All counts and timings derive from retained artifacts; no network operations.
"""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-d156-fix-20261116'
HANDOFF = ROOT.parent / 'codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/codex-d156-fix-20261116.md'


def read_rows(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def main():
    diagnosis = json.loads((SCRATCH / 'receipt-census-diagnosis-final.json').read_text())
    lanes = {}
    for name in ('receipt-path-canary', 'receipt-path-tests', 'receipt-public-correction'):
        folder = SCRATCH / name
        summary = json.loads((folder / 'lane_summary.json').read_text())
        cases = [case for path in (folder / 'results').glob('*.xml')
                 for case in ET.parse(path).getroot().iter('testcase')]
        failures = [node.get('message') for case in cases for node in case
                    if node.tag in ('failure', 'error')]
        skipped = sum(case.find('skipped') is not None for case in cases)
        lanes[name] = {'summary': summary, 'passed': len(cases) - len(failures) - skipped,
                       'failed': len(failures), 'skipped': skipped, 'failures': failures}
    public = SCRATCH / 'receipt-public-correction'
    timings = read_rows(SCRATCH / 'receipt-public-timings.jsonl')
    from d156_callback_timing_20261116 import callback_timings
    timing_join = callback_timings(public, timings)
    callbacks = timing_join["callbacks"]
    observers = timing_join["final_callbacks"]
    peak = timing_join.get("peak_final_stage_observer_seconds")
    results = sorted(public.rglob('actual-result.json'))
    result = json.loads(results[0].read_text()) if results else {}
    guard = result.get('subscription_guard', {})
    elapsed = None
    if guard.get('captured_at') and guard.get('dispatched_at'):
        elapsed = (datetime.fromisoformat(guard['dispatched_at'].replace('Z', '+00:00'))
                   - datetime.fromisoformat(guard['captured_at'].replace('Z', '+00:00'))).total_seconds()
    helpers, errors = [], []
    for path in sorted(public.rglob('stderr.txt')):
        for line in path.read_text(errors='replace').splitlines():
            if line.startswith('Error:'):
                errors.append({'path': str(path), 'error': line})
            try:
                value = json.loads(line)
            except ValueError:
                continue
            if isinstance(value, dict) and 'helper_timing' in value:
                helpers.append({'path': str(path), **value['helper_timing']})
    advances = [row for row in helpers if ' advance ' in row.get('command', '')]
    late = advances[-1] if advances else None
    pins = json.loads((SCRATCH / 'receipt-pin-proposals.json').read_text())
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    ledger = {'head': head, 'diagnosis': diagnosis['summary'], 'lanes': lanes,
              "first_stop": result.get("first_stop"), "capture_problems": result.get("capture_problems", []),
              'capture_to_dispatch_seconds': elapsed, 'peak_final_callback_observe_event_seconds': peak,
              'late_advance': late, 'callbacks': callbacks, 'final_observers': observers, 'timing_join': timing_join,
              'helper_timings': helpers, 'errors': errors, 'result_paths': list(map(str, results)), 'pins': pins}
    ledger_path = SCRATCH / 'receipt-fix-evidence.json'
    ledger_path.write_text(json.dumps(ledger, indent=2, sort_keys=True) + '\n')
    passed = lanes['receipt-public-correction']['passed'] == 1 and not lanes['receipt-public-correction']['failed']
    threshold = ('At or under 60 seconds: issues 4400 and 4550 remain deferred.' if peak is not None and peak <= 60
                 else 'Over 75 seconds: issues 4400 and 4550 are triggered.' if peak is not None and peak > 75
                 else 'No owner threshold established; missing measurements are unknown.')
    lines = [
        '# D156 receipt census: CI test-harness import-path mismatch', '',
        'Cause class (b), because CI uses the same full-tree pytest collection: collection polluted the preparing process import paths while receipt helpers start in a clean interpreter. This is a test-harness defect; no production census defect was found. The fix isolates the public test import paths to those of a fresh helper before creating either manifest and retains that environment throughout execution. No check is relaxed and no existing manifest is treated as fresh.', '',
        "Public correction: " + ("PASS." if passed else "FAIL. First stop: " + str(result.get("first_stop") or lanes["receipt-public-correction"]["failures"][:1])) + " Retained helper errors: " + json.dumps(errors[:2]),
        "Capture problems: " + json.dumps(result.get("capture_problems", [])) + ".",
        'Capture-to-dispatch seconds: ' + str(elapsed) + '.',
        'Peak completed final-callback _observe_event seconds: ' + str(peak) + '.',
        "This conservative peak includes every live observer after the late advance callback, including its result and the final-stage requests. PreToolUse request-only peak: " + str(timing_join.get("peak_final_callback_seconds")) + "; shared-test-39 request: " + str(timing_join.get("shared_test_39_seconds")) + " seconds.",
        'Late advance: ' + json.dumps(late, sort_keys=True) + '.', threshold, '',
        '## Diagnosis', '',
        'The unchanged interpreter reproduced the original stale-manifest refusal in the standalone diagnostic harness. Distribution rows, including their recorded file inventories, and interpreter identity match exactly. Site-packages unowned files are unchanged. The differences are missing collection-only import roots: ' + json.dumps(diagnosis['summary']['unowned_removed_by_root'], sort_keys=True) + '. The helper adds zero unowned files. The excluded FAIRSCAPE root is also absent. These are import-scope differences, not an observed cloned-venv RECORD change or bytecode addition.', '',
        'This comparison reconstructs the helper import environment against the retained preparation manifest; the original failing helper did not save its live census. Diagnostic tracing exists only in scripts/adhoc/diagnose_d156_receipt_census_20261116.py, not production. Its JSON is ' + str(SCRATCH / 'receipt-census-diagnosis-final.json') + '.', '',
        "Downstream blocker: the case reaches saved evidence capture and then refuses with AttributeError: denial_problems. Static inspection identifies native_attribution_results.py:826 calling controls[run_native_canary].denial_problems, while native_execution_capabilities.py:23-24 omits denial_problems from its exact member projection; the historical function exists at run_native_canary.py:269. An ignored-and-hidden-inclusive search of the capability file confirms the missing member. This continuation changes neither that projection nor the saved validator. The lead should review the required pure-helper projection and add a focused saved-replay regression; this separate finding is retained for the lead issue ledger. The public case is not a completion or launch-readiness pass.", "",
        "The lane load gate admitted the run without waiting. Host load varied afterward; this is a single-run timing result, not a controlled before-and-after benchmark. A one-second read-only process sample was taken during preparation, before capture. No sampling was performed during the measured live callbacks.", "",
        '## Fix and verification', '',
        'tests/utils/native_helper_environment.py queries a fresh interpreter with the helper PYTHONPATH policy, enters those paths before fixture preparation, and restores the exact original path object on success or refusal. The autouse fixture in tests/test_native_shared_execution.py covers the complete public lifetime. The regression deliberately installs a foreign unowned import root and FAIRSCAPE collection root, checks helper path equality, and checks restoration. It also proves that later path changes remain visible rather than being continuously filtered.', '',
        'The canary proved fresh-child path discovery and restoration through the lane launcher, with a persisted nonempty XML result. It did not establish final-callback performance; the public case supplies that evidence.', '',
    ]
    for name, lane in lanes.items():
        lines.append('- ' + name + ': ' + str(lane['passed']) + ' passed, ' + str(lane['failed'])
                     + ' failed; gate wait ' + str(lane['summary']['gate_wait_seconds']) + ' seconds. Evidence: ' + str(SCRATCH / name / 'lane_summary.json'))
    lines += ['', 'Source/test commit: ebe3597758281fa9c6011743efb964603b20427a. Report-time head: ' + head + '.',
        'The earlier worker, sequence and native_controls results remain retained below; production is unchanged by this continuation. The new public case used the required native-public lane and case, isolated interpreter and 1800-second gate wait; its observer plugin is scripts.adhoc.capture_order_timing_20261116.', '',
        'Read-only review found no additional defect in the test import-path isolation change. The diagnosed CI harness failure is retained here for the lead issue ledger; assignment bounds prohibit GitHub writes. No push, provider call, native binary call or pin edit occurred. Initial index-lock creation was refused; the permitted retry after ten seconds succeeded with sandbox escalation.', '',
        'Pin proposals: ' + json.dumps(pins['proposed_edits']) + '; protected files check: ' + str(pins['protected_files_ok']) + '. Existing scanner asset refresh notices remain in ' + str(SCRATCH / 'receipt-pin-proposals.json') + '.',
        "Final-stage timings are joined by ordered live observer spans to transcript lines and checked against available host intake and authorization timestamps. The conservative peak includes all observer frames after the last stage-advance callback; request-only figures select control_request frames. The ledger retains each tool identity and command. Saved-replay at_callback spans are not used as live observer boundaries.",
        "Timing-report review found the earlier at_callback containment heuristic could not identify live final callbacks. This continuation replaces that heuristic with the checked transcript join; earlier runs stopped before that boundary, so their unknown final timings remain unknown. This finding is retained for the lead issue ledger.",
        'Evidence ledger: ' + str(ledger_path) + '. Artifact discovery uses Path.rglob and includes ignored and hidden files. Reporting script: ' + str(Path(__file__).resolve()) + '.', '']
    section = '\n'.join(lines)
    if chr(64) in section:
        raise ValueError('forbidden character in handoff')
    HANDOFF.write_text(section + '\n---\n\n' + HANDOFF.read_text())
    print(str(HANDOFF))
    print(hashlib.sha256(HANDOFF.read_bytes()).hexdigest())
    print(json.dumps({key: ledger[key] for key in ('capture_to_dispatch_seconds', 'peak_final_callback_observe_event_seconds', 'late_advance')}))


if __name__ == '__main__':
    main()

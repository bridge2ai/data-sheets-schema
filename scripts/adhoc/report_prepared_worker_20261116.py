"""Build the D156 helper handoff from saved lane evidence, 2026-11-16.

Inputs: scratch lane summaries, JUnit files, timing JSONL and pin proposals.
Outputs: review ledger and a new top handoff section for the Claude lead.
No external writes; prior handoff sections are retained.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
E = ROOT.parent
SCRATCH = E / 'scratch-capture-order-20261116'
HANDOFF = E / 'codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/codex-capture-order-20261116.md'
TITLE = '# D156 prepared worker implemented; integrated validation remains blocked by frozen pins'


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()


def counts(path):
    rows = list(ET.parse(path).getroot().iter('testcase'))
    failed = [row for row in rows if row.find('failure') is not None]
    errors = [row for row in rows if row.find('error') is not None]
    skipped = [row for row in rows if row.find('skipped') is not None]
    return {'tests': len(rows), 'passed': len(rows) - len(failed) - len(errors) - len(skipped),
        'failed': len(failed), 'errors': len(errors), 'skipped': len(skipped),
        'findings': [row.get('classname', '') + '::' + row.get('name', '')
                     for row in [*failed, *errors]]}


def main():
    head = git('rev-parse', 'HEAD')
    code_head = git('log', '-1', '--format=%H', '--', 'src', 'tests')
    ledger = {'head': head, 'implementation_head': code_head, 'lanes': {}, 'artifacts': {}}
    results = []
    for name, relative in (
        ('worker-sequence', 'worker-sequence/results/unit.xml'),
        ('broad-partial', 'broad/results/unit.xml'),
        ('components', 'components/results/unit.xml'),
        ('timing-canary', 'timing-canary/results/unit.xml'),
        ('controls-canary', 'controls-canary/results/native.xml'),
        ('controls-budget', 'controls/results/budget.xml'),
        ('controls-sandbox-partial', 'controls/results/native.xml'),
        ('loopback-canary', 'loopback-canary/results/native.xml'),
        ('controls-loopback-budget', 'controls-loopback/results/budget.xml'),
        ('controls-loopback-native', 'controls-loopback/results/native.xml'),
        ('controls-three-worker-canary', 'controls-three-canary/results/native.xml'),
        ('controls-three-worker-budget', 'controls-three/results/budget.xml'),
        ('controls-three-worker-native', 'controls-three/results/native.xml'),
        ('public-collection', 'public-correction/results/pytest.xml'),
        ('public-case', 'public-correction-case/results/pytest.xml'),
        ('worker-before-Darwin-fix', 'final-worker/results/unit.xml'),
        ('Darwin-diagnosis', 'worker-reap-canary/results/unit.xml'),
        ('reaping-fixed-canary', 'reaping-fixed-canary/results/unit.xml'),
        ('prepared-final', 'prepared-final/results/unit.xml')):
        path = SCRATCH / relative
        if not path.is_file():
            results.append('- ' + name + ': no completed JUnit report; no pass claimed.')
            continue
        row = counts(path)
        ledger['lanes'][name] = row
        results.append('- ' + name + ': ' + ', '.join(str(row[key]) + ' ' + key
            for key in ('passed', 'failed', 'errors', 'skipped')) + '. Evidence: ' + str(path))
    summaries = {}
    for path in sorted(SCRATCH.glob('*summary.json')):
        summaries[path.name] = json.loads(path.read_text())
    ledger['lane_summaries'] = summaries
    waits = [name + ': ' + str(doc['gate_wait_seconds']) + ' seconds'
             for name, doc in summaries.items() if 'gate_wait_seconds' in doc]
    public_root = SCRATCH / 'public-correction-case'
    for name in ('capture.json', 'subscription-dispatched.json', 'actual-result.json'):
        ledger['artifacts'][name] = [str(path) for path in public_root.rglob(name)]
    timings = SCRATCH / 'public-case-timings.jsonl'
    spans = [json.loads(line) for line in timings.read_text().splitlines()] if timings.exists() else []
    last = {name: next((row for row in reversed(spans) if row.get('function') == name), None)
            for name in ('_observe_event', 'at_callback')}
    ledger['last_callback_spans'] = last
    pin_path = SCRATCH / 'prepared-worker-pins.json'
    pins = json.loads(pin_path.read_text())
    ledger['pins'] = pins
    ledger['review_findings'] = {
        'frozen_controller_pin_integration': 'blocked: lead owns pin edits',
        'empty_package_initializer': 'fixed with exact source verifier',
        'delegation_drift': 'fixed with post-preparation recheck',
        'heavy_post_capture_reconstruction': 'replaced with fresh identity checks',
        'reaped_worker_group_signal': 'fixed with retained PID and probe-only Darwin fallback',
        'same_size_dependency_edit': 'fixed with required full baseline comparison'}
    ledger_path = SCRATCH / 'prepared-worker-review.json'
    ledger_path.write_text(json.dumps(ledger, indent=2, sort_keys=True) + '\n')
    body = f'''{TITLE}

The D156 prepared worker, production sequence and deferred synthetic fixture are implemented and committed locally. Integrated launch correctness and capture-to-dispatch improvement remain unverified because the frozen controller closure rejects the inherited run_native_canary changes. The lead must review and integrate the pin proposals before those paths can run. This is not launch-readiness evidence. The earlier protocol audit and D156 ruling remain below.

Final branch head: {head}. Last source/test commit: {code_head}.

## Implemented boundaries

The sequence starts launch in prepare mode, waits for its exact prepared record, runs capture and guard as separate processes, then publishes a one-use proceed record. IPC is under the sequence packet, outside every registered reservation. Preparation verifies registration, classifier admission and source/environment authority, prewarms the controller and opens its non-reserving callback scope. Registration bytes, source and environment digests, attempt path, nonce and worker PID bind readiness. The prepared wait retains the registered 1200-second bound.

Proceed freshly checks exact bytes, Git HEAD, package roster and pins, committed source blobs, interpreter, preparation/composition inputs and runtime. Its environment census must match the process-local full verification baseline established before capture. The new prepared verification mode refuses when that baseline is absent and never falls back to heavy regeneration after capture. Same-size payload edits still refuse. No serialized verdict grants admission. Capture-dependent readers, current-word locking and latest-claim checks still run.

Reservation-writing activation remains after guard consumption: reserved registration and started evidence, execution_capture, started_capture, genesis and journal retain their original boundary. Final freshness/reset checks and saved dispatch-observation binding remain immediately before transport dispatch. Limits, margins and no-retry semantics are unchanged.

## Validation

{chr(10).join(results)}

The broad run was interrupted after repeated setup errors exposed the frozen run_native_canary mismatch. Its partial counts are not a completed-suite pass. The component source-closure failure has the same mismatch. The initial identity-unit run passed 11 tests but the lane returned a cleanliness failure because later test edits were present. Historical worker failures exposed Darwin's refusal to signal a group containing only its exited leader; the later canary and final suite test the fix.

The sandboxed controls run was interrupted after local loopback socket binds were denied. Its failures are retained, not counted as a pass. A separate loopback canary passed with local socket permission and an upstream MockTransport. The serial controls-loopback rerun reached beyond 85 percent without a reported failure but timed out at 900 seconds; no completed native JUnit report or full pass is claimed for it. The controls-three rerun uses three workers and a 3600-second limit, following its own same-configuration loopback canary. No provider request or Claude binary was used. Some controls children created ignored bytecode directories under notes, which can produce lane cleanliness failures independently of test counts; summaries preserve those details.

The first public invocation failed collection on three unrelated fairscape_models.rocrate imports and never ran the selected case. The subsequent public-case invocation excludes only tests/test_fairscape_integration and selects the one requested correction case. It failed during setup with frozen native controller bytes changed: run_native_canary, before capture or dispatch. Its result is retained separately; no second correction case was attempted.

Saved gate waits: {'; '.join(waits)}. No gate was bypassed. Staging refusals cleared on the prescribed ten-second retries. No push or GitHub write was made.

The timing canary proved observer startup, completion and persistence of a non-empty file; it did not reach a final native callback. The native-controls canary proved the final boundary refuses without spawning a native binary. Each full run followed its same-path canary.

## Public correction and pin proposals

Capture-to-dispatch and final-callback timing are unavailable when the boundary is not reached; no time is inferred from process exit. Ignore-independent artifact search under {public_root}: {json.dumps(ledger['artifacts'], sort_keys=True)}.

Last completed callback spans: {json.dumps(last, sort_keys=True)}.

Pin proposals: {pin_path}. Protected-files check: {pins.get('protected_files_ok')}. No pin or protected file was edited. Reproduce with the primary checkout's compute_pin_chain_20261115.py, this worktree as root, and --propose --compact.

## Read-only review findings

The review identified frozen controller pin integration, empty-source initializer handling, delegated-deadline drift across preparation, full reconstruction calls after capture, process-group signaling after leader reaping, and the weaker guarantee of a standalone light census. Implementation findings were addressed with focused checks. Pin integration and full-stack validation remain with the lead. The complete failing-test roster and lane summaries are in {ledger_path}. GitHub issues were not filed because this helper assignment forbids GitHub writes.

## Plumbing fixes and provenance

The packet-directory IPC ruling is enforced by placement and attempt-disjointness checks. Saved-capture mutation tests explicitly request eager synthetic fixtures; the public synthetic fixture defaults to deferred capture. A fresh delegation check follows preparation. Empty package initializers use the source verifier rather than a non-empty wire reader.

The sequence retains the worker PID with WNOWAIT until cleanup. On Darwin's exited-only group refusal it confirms exit, reaps, and only probes group absence; it never sends another signal after reaping. A remaining or unverifiable group refuses. Streams close and the leader is reaped even when cleanup raises. This mirrors the existing transport's Darwin handling.

The isolated environment is a filesystem clone under scratch. Its editable-install path points to this worktree; restore data_sheets_schema.pth.bak-capture-order-20261116 beside data_sheets_schema.pth to undo that configuration. The primary environment was not edited. Generated notes caches were preserved under scratch/cache-evidence when moved out for final cleanliness checks.

Committed helper scripts under scripts/adhoc/: split_synthetic_capture_20261116.py, capture_order_timing_20261116.py, finish_worker_reaping_20261116.py, preserve_prepared_environment_baseline_20261116.py report_prepared_worker_20261116.py and finalize_prepared_report_20261116.py. The transformation scripts are one-time provenance; the reporting script can regenerate this top section. Prior handoffs follow.

---

'''
    old = HANDOFF.read_text()
    if old.startswith(TITLE):
        old = old.split('\n---\n\n', 1)[1]
    if chr(64) in body + old:
        raise ValueError('prohibited character in handoff')
    HANDOFF.write_text(body + old)
    print(str(HANDOFF))
    print(hashlib.sha256(HANDOFF.read_bytes()).hexdigest())


if __name__ == '__main__':
    main()

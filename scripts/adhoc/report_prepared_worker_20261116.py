"""Build the D156 helper handoff from saved lane evidence, 2026-11-16.

Inputs: scratch lane summaries, JUnit files, timing JSONL and pin proposals.
Outputs: a machine-readable review ledger and a new top handoff section.
Serves the Claude lead capture-order continuation; no external writes.
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
TITLE = '# D156 implementation committed; frozen controller pins block integrated validation'


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()


def counts(path):
    suites = ET.parse(path).getroot()
    rows = list(suites.iter('testcase'))
    failed = [row for row in rows if row.find('failure') is not None]
    errors = [row for row in rows if row.find('error') is not None]
    skipped = [row for row in rows if row.find('skipped') is not None]
    return {'tests': len(rows), 'passed': len(rows) - len(failed) - len(errors) - len(skipped),
        'failed': len(failed), 'errors': len(errors), 'skipped': len(skipped),
        'findings': [row.get('classname', '') + '::' + row.get('name', '')
                     for row in [*failed, *errors]]}


def main():
    head = git('rev-parse', 'HEAD')
    ledger = {'head': head, 'lanes': {}, 'artifacts': {}}
    results = []
    for name, relative in (
        ('worker-sequence', 'worker-sequence/results/unit.xml'),
        ('broad', 'broad/results/unit.xml'),
        ('components', 'components/results/unit.xml'),
        ('timing-canary', 'timing-canary/results/unit.xml'),
        ('controls-canary', 'controls-canary/results/native.xml'),
        ('controls-budget', 'controls/results/budget.xml'),
        ('controls-native', 'controls/results/native.xml'),
        ('public', 'public-correction/results/pytest.xml'),
        ('final-worker', 'final-worker/results/unit.xml')):
        path = SCRATCH / relative
        if not path.is_file():
            results.append('- ' + name + ': no completed JUnit report; not claimed as passing.')
            continue
        row = counts(path)
        ledger['lanes'][name] = row
        results.append('- ' + name + ': ' + ', '.join(str(row[key]) + ' ' + key
            for key in ('passed', 'failed', 'errors', 'skipped')) + '. Evidence: ' + str(path))
    waits = []
    for path in sorted(SCRATCH.glob('*summary.json')):
        doc = json.loads(path.read_text())
        if 'gate_wait_seconds' in doc:
            waits.append(path.name + ': ' + str(doc['gate_wait_seconds']) + ' seconds')
    public_root = SCRATCH / 'public-correction'
    for name in ('capture.json', 'subscription-dispatched.json', 'actual-result.json'):
        ledger['artifacts'][name] = [str(path) for path in public_root.rglob(name)]
    timings = SCRATCH / 'public-timings.jsonl'
    spans = [json.loads(line) for line in timings.read_text().splitlines()] if timings.exists() else []
    last = {name: next((row for row in reversed(spans) if row.get('function') == name), None)
            for name in ('_observe_event', 'at_callback')}
    ledger['last_callback_spans'] = last
    pin_path = SCRATCH / 'prepared-worker-pins.json'
    pins = json.loads(pin_path.read_text())
    ledger['pins'] = pins
    ledger_path = SCRATCH / 'prepared-worker-review.json'
    ledger_path.write_text(json.dumps(ledger, indent=2, sort_keys=True) + '\n')
    body = f'''{TITLE}

Preparation, worker rendezvous, production sequence wiring, deferred synthetic capture, fresh identity rechecks and process-group cleanup are implemented on the assigned branch. Integrated launch correctness and capture-to-dispatch improvement remain unverified: the frozen controller closure rejects the inherited run_native_canary changes. This is not launch-readiness evidence. The lead must review and integrate the pin proposals before the blocked suites can exercise the full implementation.

Final branch head: {head}.

## Implemented boundaries

The sequence starts launch in prepare mode, waits for its exact prepared record, then runs capture and guard as separate processes and publishes a one-use proceed record. IPC stays under the sequence packet, outside every registered reservation. Preparation verifies registration, classifier admission and source/environment authority, prewarms the controller and opens its non-reserving callback scope. Exact registration bytes, source and environment digests, attempt path, nonce and worker PID bind readiness. The wait retains the registered 1200-second limit.

Proceed performs fresh exact-byte checks and invokes the live registration recheck with a light environment census. That path recaptures Git HEAD, package roster and pins, committed source blobs, interpreter, preparation/composition inputs and runtime. Capture-dependent readers, current-word locking and latest-claim checks still run. Subsequent pre-dispatch unchanged checks use this fresh path too. No serialized verdict grants admission.

Reservation-writing activation remains after guard consumption: reserved registration and started evidence, execution_capture, started_capture, genesis and journal retain their original reservation boundary. The final freshness/reset check and saved dispatch-observation binding remain immediately before transport dispatch. Limits, margins and no-retry semantics were not changed.

## Validation

{chr(10).join(results)}

The broad run was deliberately interrupted after repeated setup errors exposed the frozen run_native_canary mismatch. Its partial counts are not a completed-suite pass. The component run's source-closure failure has that same pin mismatch. The initial identity-unit run passed its tests but the lane returned a cleanliness failure because later test edits were present; use the later committed runs for component evidence.

Saved gate waits: {'; '.join(waits)}. No load gate was bypassed. One staging attempt was refused; the prescribed ten-second retry succeeded. All implementation changes were committed locally; no push or GitHub write was made.

The timing canary verified that the observer starts, finishes and persists a non-empty file. It did not exercise a final native callback. The native-controls canary exercised the final transport refusal without spawning a native binary and persisted its JUnit report before the full controls run.

## Public correction and pins

One public correction case was requested through the native-public lane, using the isolated interpreter and the timing observer. Read its saved result rather than inferring dispatch from process exit. Capture-to-dispatch is unavailable unless a dispatch marker exists; no callback time is inferred from an unreached boundary.

Ignore-independent artifact search under {public_root}: {json.dumps(ledger['artifacts'], sort_keys=True)}.

Last completed callback spans: {json.dumps(last, sort_keys=True)}.

Pin proposals: {pin_path}. Protected-files check: {pins.get('protected_files_ok')}. No pin or protected file was edited. Reproduce with the primary checkout's compute_pin_chain_20261115.py, this worktree as root, and --propose --compact.

## Review findings for the lead ledger

The separate read-only review found the unresolved frozen controller pin integration, empty-source initializer handling, delegated-deadline drift across preparation, remaining full reconstruction calls after capture, and the risk of signaling a group after reaping its leader. The latter implementation findings were addressed and covered by focused checks. Pin integration and full-stack validation remain with the lead. The complete failing-test roster is retained in {ledger_path}; no GitHub issues were filed because this helper assignment forbids GitHub writes.

## Plumbing fixes and provenance

The accepted packet-directory IPC ruling is enforced by sequence placement and the worker's attempt-disjointness check. Legacy saved-capture mutation tests explicitly request eager synthetic fixtures; the public synthetic fixture defaults to deferred capture. The isolated environment is a filesystem clone under this scratch directory. Its editable-install path points at this worktree; undo that configuration by restoring data_sheets_schema.pth.bak-capture-order-20261116 beside data_sheets_schema.pth. The primary environment was not edited.

Helper scripts are committed under scripts/adhoc/: split_synthetic_capture_20261116.py, capture_order_timing_20261116.py and report_prepared_worker_20261116.py. Reproduce this section by running the last script from this checkout after the lane evidence and final pin proposal exist. The prior boundary and protocol handoffs remain below.

---

'''
    if chr(64) in body:
        raise ValueError('prohibited character in handoff')
    old = HANDOFF.read_text()
    if old.startswith(TITLE):
        old = old.split('\n---\n\n', 1)[1]
    HANDOFF.write_text(body + old)
    print(str(HANDOFF))
    print(hashlib.sha256(HANDOFF.read_bytes()).hexdigest())


if __name__ == '__main__':
    main()

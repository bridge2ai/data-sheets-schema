#!/usr/bin/env python3
"""Save static callback-path diagnosis for H2 issue 6200, 2026-11-13.
Inputs: inspected source bytes, Git diff, completed correction request and
unchanged boundary analysis. Output: scratch callback-static-diagnosis.json.
No project-code execution, tests, monitoring, probes or source mutations.
"""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-h2-resume-20261113'
ANCHORS = {
    'notes/matched_cborg_2026-09-13/native_controls/native_control.py': (
        'def _intake_history(', 'self._callback_intake.setdefault(event[',
        'def _service_history(', 'self._active_work is None and not self.outgoing and self._events',
        'def _check_response_bounds(', "self._start_work('observer'", "self._start_work('classifier'"),
    'src/data_sheets_schema/native_shared_controller_orchestration.py': (
        'def _phase_state(', 'def _observe(', 'def observe(',
        '_catalogs=self._receipt_catalogs', 'run, decision = self._phase_state(endpoints)'),
    'src/data_sheets_schema/native_shared_callback_capture.py': (
        'def reconstruct(', 'self.check_sources()', 'def base(', 'value = self.reconstruct()'),
    'src/data_sheets_schema/native_shared_capture.py': (
        'def _checked_observations(', 'def _loaded(', 'def decision(',
        'run._catalogs = receipt_api._catalog_context(_catalogs)', '_checked_observations(run)'),
    'src/data_sheets_schema/native_shared_receipts.py': (
        'class _ReceiptCatalogContext:', 'def schema_data(', 'def _catalog_context('),
    'src/data_sheets_schema/native_catalog_reuse.py': ('def runtime_token(',),
    'src/data_sheets_schema/native_shared_callback_orchestration.py': (
        'def preloaded_callback_utilities(', "'native_host_power', 'native_elapsed', 'native_attempt_timing'"),
    'src/data_sheets_schema/native_pre_dispatch_timing.py': (
        'def record(', 'if self.disabled or self.sealed:', '_handoff(trace)', 'def finish('),
}


def pin(path):
    assert path.is_file(), str(path)
    return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def main():
    evidence = []
    for relative, anchors in ANCHORS.items():
        path = ROOT / relative
        lines = path.read_text().splitlines()
        matches = [{'line': number, 'text': line.strip()}
                   for number, line in enumerate(lines, 1)
                   if any(anchor in line for anchor in anchors)]
        assert matches, relative
        evidence.append({**pin(path), 'excerpts': matches})
    analysis_path = SCRATCH / 'correction/callback-stop-analysis.json'
    analysis_raw = analysis_path.read_bytes()
    analysis = json.loads(analysis_raw)
    callback = analysis['answer']['stalled_callbacks'][0]
    request_path = Path(callback['request_file']['path'])
    request = json.loads(request_path.read_bytes())
    request_identity = {'cursor': request['payload']['cursor'],
                        'inner_request_kind': request['payload']['inner_request']['kind']}
    diff_paths = [
        'src/data_sheets_schema/native_shared_callback_orchestration.py',
        'src/data_sheets_schema/native_shared_capture.py',
        'src/data_sheets_schema/native_shared_controller_orchestration.py',
        'src/data_sheets_schema/native_shared_callback_capture.py',
        'src/data_sheets_schema/native_shared_receipts.py',
        'src/data_sheets_schema/native_pre_dispatch_timing.py',
    ]
    diff_command = ['git', 'diff', '309b58bd3..HEAD', '--', *diff_paths]
    diff = subprocess.check_output(diff_command, cwd=ROOT)
    changed = subprocess.check_output(['git', 'diff', '--name-only', '309b58bd3..HEAD', '--',
                                      'src/data_sheets_schema'], cwd=ROOT, text=True).splitlines()
    record = {
        'answer': 'No concrete algorithmic defect introduced by the H2 preload/timing repairs is demonstrated by this static examination. Issue 6200 remains blocked by incomplete public runs.',
        'issue': '6200',
        'scope': 'Read-only static callback-path and resume-delta examination; completed correction artifacts only, with no inspection of an active public run.',
        'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'callback': {'tool_use_id': callback['tool_use_id'], 'request_id': callback['request_id'],
                     'callback_id': callback['callback_id'], 'request': pin(request_path),
                     'request_identity': request_identity},
        'established': [
            'The response window starts at raw callback frame intake. The service pump processes one ordered event only after prior observation/classification and queued output finish.',
            'The pending Read therefore does not prove that its own observer or classifier began. Earlier ordered work, including the preceding advance result or assistant tool-use event, may still be active.',
            'Each current captured run reconstructs the execution body and rechecks source/input pins; it then validates historical observation joins and derives the current stage decision.',
            'The callback passes its existing receipt-catalog context into each live captured run. Catalog reuse remains guarded by runtime identity; this source inspection does not establish a cache hit or miss in the failed run.',
            'The examined resume delta adds host/timing module preloads and defers pre-dispatch diagnostic persistence. It does not change the inspected adapter replay, captured admission reconstruction or receipt-catalog implementation.',
            'The pre-dispatch launch trace is sealed after reservation and handed off at operation exit; it does not add a per-event flush to the inspected callback path.'
        ],
        'not_demonstrated': [
            'The worker operation active when the response window expired.',
            'A lost receipt-catalog context, an unbounded loop, or an accidental new repeated-verification path caused by the preload/timing delta.',
            'Any runtime duration attributable to schema reconstruction, history replay, module loads, caching, host contention or scheduling.'
        ],
        'next_boundary': 'Lead design/performance diagnosis is required without weakening validation, deadlines or response windows. Fresh verification and pure derivation reuse are distinct contracts.',
        'pin_implications': 'A proposed change to pinned controller files such as native_control.py or run_native_canary.py requires a review-only pin proposal; no controller change or pin rotation is proposed or applied here.',
        'source_evidence': evidence,
        'boundary_analysis_evidence': pin(analysis_path),
        'resume_diff': {'command': diff_command, 'sha256': hashlib.sha256(diff).hexdigest(),
                        'changed_package_paths': changed},
        'actions': {'tests_run': [], 'probes_run': [], 'monitoring_run': [],
                    'production_source_changes': [], 'controller_pin_changes': []},
    }
    assert analysis_path.read_bytes() == analysis_raw
    destination = SCRATCH / 'callback-static-diagnosis.json'
    raw = (json.dumps(record, indent=2) + '\n').replace(chr(64), '\\u0040').encode()
    with destination.open('xb') as stream:
        stream.write(raw)
    print(json.dumps(pin(destination)))


if __name__ == '__main__':
    main()

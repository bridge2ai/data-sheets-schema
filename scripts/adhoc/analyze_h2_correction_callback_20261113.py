#!/usr/bin/env python3
"""Summarize completed correction callback-stop evidence, 2026-11-13.
Inputs: correction cohort artifacts only; output: correction/callback-stop-analysis.json.
Provenance for the H2 integration handoff. No tests, monitoring, probes,
project imports, child execution or changes to source/evidence inputs.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COHORT = ROOT.parent / 'scratch-h2-resume-20261113/correction'
INPUTS = {}


def read(path, jsonl=False):
    assert path.is_file() and path.is_relative_to(COHORT), str(path)
    raw = path.read_bytes()
    INPUTS[path] = raw
    return [json.loads(line) for line in raw.splitlines()] if jsonl else json.loads(raw)


def pointer(path, line=None):
    raw = INPUTS[path]
    result = {'path': str(path), 'sha256': hashlib.sha256(raw).hexdigest()}
    if line is not None:
        result['line'] = line
    return result


def interval(start, end):
    delta = end['elapsed_ns'] - start['elapsed_ns']
    assert delta >= 0
    return {'elapsed_ns': delta, 'seconds': delta / 1_000_000_000}


def main():
    result_paths = sorted((COHORT / 'cases').rglob('actual-result.json'))
    assert len(result_paths) == 1
    result_path = result_paths[0]
    result = read(result_path)
    attempt = result_path.parent / 'native-attempt'
    timing_path = attempt / 'host-controller-timing.jsonl'
    control_path = attempt / 'control.jsonl'
    transcript_path = attempt / 'transcript.jsonl'
    phase_path = attempt / 'live-phase-report.json'
    timing, control, transcript = (read(path, jsonl=True)
                                  for path in (timing_path, control_path, transcript_path))
    phase = read(phase_path)
    summary_path = COHORT / 'public-summary.json'
    summary = read(summary_path)
    dispatch = next(row for row in timing if row['boundary'] == 'child_dispatch')
    cleanup = next(row for row in timing if row['boundary'] == 'execute_child_cleanup_entry')
    initialize = next(row for row in control if row['kind'] == 'initialize_sent')
    timeout = initialize['frame']['request']['hooks']['PreToolUse'][0]['timeout']
    by_tool = {}
    for number, row in enumerate(timing, 1):
        identity = row.get('tool_use_id')
        if identity:
            by_tool.setdefault(identity, {})[row['boundary']] = {'line': number, 'row': row}
    decisions = {}
    for number, row in enumerate(control, 1):
        if row['kind'] == 'decision':
            identity = row['request']['request']['input']['tool_use_id']
            decisions[identity] = {'line': number, 'row': row}
    completed = []
    for identity, events in by_tool.items():
        if not all(key in events for key in ('helper_requested', 'helper_start', 'helper_end')):
            continue
        requested, started, ended = (events[key] for key in ('helper_requested', 'helper_start', 'helper_end'))
        completed.append({'tool_use_id': identity, 'tool_name': requested['row']['tool_name'],
            'classification_basis': decisions.get(identity, {}).get('row', {}).get('basis'),
            'request_to_callback_response': interval(requested['row'], started['row']),
            'callback_response_to_result_intake': interval(started['row'], ended['row']),
            'timing_lines': [requested['line'], started['line'], ended['line']],
            'control_line': decisions.get(identity, {}).get('line')})
    stalled = []
    for identity in phase['pending_tool_ids']:
        events = by_tool[identity]
        requested = events['helper_requested']
        callbacks = [(number, row) for number, row in enumerate(transcript, 1)
                     if row.get('type') == 'control_request'
                     and row.get('request', {}).get('input', {}).get('tool_use_id') == identity]
        assert len(callbacks) == 1
        number, callback = callbacks[0]
        tool_input = callback['request']['input']
        path = Path(tool_input['tool_input']['file_path'])
        request_document = read(path)
        request_identity = {key: value for key, value in request_document.items()
                            if key in ('kind', 'stage', 'cursor', 'worker', 'request_id', 'id',
                                       'request_kind', 'sequence', 'version', 'action')}
        stalled.append({'tool_use_id': identity, 'tool_name': tool_input['tool_name'],
            'callback_id': callback['request']['callback_id'], 'request_id': callback['request_id'],
            'hook_event_name': tool_input['hook_event_name'],
            'request_file': pointer(path), 'request_identity': request_identity,
            'request_document_keys': sorted(request_document),
            'transcript_evidence': pointer(transcript_path, number),
            'request_timing_evidence': pointer(timing_path, requested['line']),
            'request_timing': requested['row'],
            'callback_response_boundary_recorded': 'helper_start' in events,
            'helper_result_boundary_recorded': 'helper_end' in events,
            'control_decision_recorded': identity in decisions,
            'request_to_cleanup_entry': interval(requested['row'], cleanup)})
    deadline_remaining = dispatch['deadline_elapsed_ns'] - cleanup['elapsed_ns']
    record = {
        'answer': {'first_stop': result['first_stop'], 'stalled_callbacks': stalled,
                   'interpretation': 'The saved trace identifies an unresolved Read callback and its elapsed interval to cleanup; it does not identify the worker internals responsible.'},
        'state': result['state'], 'result_evidence': pointer(result_path),
        'registered_callback_timeout_seconds_from_initialize': timeout,
        'dispatch_to_cleanup_entry': {'elapsed_ns': cleanup['elapsed_ns'] - dispatch['dispatch_elapsed_ns'],
                                     'seconds': (cleanup['elapsed_ns'] - dispatch['dispatch_elapsed_ns']) / 1_000_000_000},
        'remaining_child_deadline_at_cleanup_entry': {'elapsed_ns': deadline_remaining,
                                                    'seconds': deadline_remaining / 1_000_000_000},
        'cleanup_entry': cleanup,
        'capture_to_reservation': [span for item in summary['timing'] for span in item['capture_to_reservation']],
        'public_summary_evidence': pointer(summary_path),
        'requested_helper_count': len(by_tool), 'completed_helper_count': len(completed),
        'last_completed_helper': completed[-1] if completed else None,
        'largest_recorded_request_to_response_intervals': sorted(completed,
            key=lambda item: item['request_to_callback_response']['elapsed_ns'], reverse=True)[:3],
        'phase': {key: phase[key] for key in ('phase1_sealed', 'core_sealed', 'assembly_complete',
                  'native_terminal', 'pending_tool_ids', 'problems')},
        'phase_helper_checks': phase['checks'], 'shutdown': result['shutdown'],
        'evidence': [pointer(path) for path in (timing_path, control_path, transcript_path, phase_path)],
        'measurement_limits': [
            'Request-to-response spans include controller intake, callback handling, transport and scheduling; they are not callback CPU durations.',
            'The last requested callback has no recorded response/start, result/end or control decision in these complete saved files.',
            'Cleanup entry is the available ending timestamp; an exact callback-worker start or timeout-detection timestamp is not recorded here.',
            'No cause involving module loads, caching, host contention, scheduling or source defects is established.',
            'Only completed correction artifacts were read; ongoing omissions artifacts were not inspected.'
        ]
    }
    for path, before in INPUTS.items():
        assert path.read_bytes() == before, 'Input changed during read-only analysis: ' + str(path)
    destination = COHORT / 'callback-stop-analysis.json'
    raw = (json.dumps(record, indent=2) + '\n').replace(chr(64), '\\u0040').encode()
    with destination.open('xb') as stream:
        stream.write(raw)
    print(json.dumps({'path': str(destination), 'sha256': hashlib.sha256(raw).hexdigest(),
        'first_stop': result['first_stop'],
        'stalled': [{'tool_use_id': item['tool_use_id'], 'request_identity': item['request_identity'],
                     'request_to_cleanup_entry': item['request_to_cleanup_entry']}
                    for item in stalled],
        'remaining_child_deadline_at_cleanup_entry': record['remaining_child_deadline_at_cleanup_entry'],
        'last_completed_helper': record['last_completed_helper'],
        'requested_helper_count': len(by_tool), 'completed_helper_count': len(completed)}, indent=2))


if __name__ == '__main__':
    main()

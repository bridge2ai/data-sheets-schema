"""Join D156 live observer spans to transcript lines, 2026-11-16, PR 5968.

Inputs: completed timing spans and the public case's transcript/host timing.
Output: checked callback timing rows for the report; no production instrumentation.
"""
import json


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def callback_timings(public, timings):
    attempts = list((public / 'native-case').rglob('native-attempt'))
    if len(attempts) != 1:
        raise ValueError('expected one native attempt for timing joins')
    attempt = attempts[0]
    transcript_path = attempt / 'transcript.jsonl'
    if not transcript_path.exists():
        return {'status': 'no transcript', 'callbacks': [], 'final_callbacks': []}
    transcript = rows(transcript_path)
    spans = [row for row in timings if row.get('function') == '_observe_event']
    host_rows = rows(attempt / "host-controller-timing.jsonl")
    intake = {row["transcript_line"]: row for row in host_rows
              if row.get("boundary") == "turn_boundary"}
    helper_starts = {row["tool_use_id"]: row for row in host_rows
                     if row.get("boundary") == "helper_start"}
    # Controller.handle schedules exactly one ordered observer for every frame.
    # An incomplete/failed observer cannot be silently skipped in this join.
    if len(spans) != len(transcript):
        return {'status': 'incomplete observer coverage', 'completed': len(spans),
                'transcript_lines': len(transcript), 'callbacks': [], 'final_callbacks': []}
    callbacks = []
    last_advance_line = 0
    for line, (frame, span) in enumerate(zip(transcript, spans), 1):
        if line in intake:
            if intake[line]["event_type"] != frame["type"]:
                raise ValueError("observer transcript intake identity mismatch")
            if span["started_wall"] + 0.01 < intake[line]["wall_ns"] / 1e9:
                raise ValueError("observer began before its transcript frame intake")
        if frame.get('type') != 'control_request':
            continue
        data = frame['request']['input']
        start = helper_starts.get(data["tool_use_id"])
        if start is not None and span["completed_wall"] > start["wall_ns"] / 1e9 + 0.01:
            raise ValueError("callback observer completed after helper authorization")
        command = data.get('tool_input', {}).get('command', '')
        row = {**span, 'transcript_line': line, 'tool_use_id': data['tool_use_id'],
               'tool_name': data['tool_name'], 'command': command}
        callbacks.append(row)
        if 'native_shared_stage advance ' in command:
            last_advance_line = line
    final = [row for row in callbacks if last_advance_line and row['transcript_line'] > last_advance_line]
    peak = max((row["seconds"] for row in final), default=None)
    callback39 = next((row["seconds"] for row in callbacks if row["tool_use_id"] == "shared-test-39"), None)
    return {'status': 'complete ordered transcript and intake join', 'callbacks': callbacks,
            'final_callbacks': final, 'last_advance_callback_line': last_advance_line,
            "peak_final_callback_seconds": peak, "shared_test_39_seconds": callback39,
            "peak_final_stage_observer_seconds": max((row["seconds"] for row in spans[last_advance_line:]), default=None),
            'completed': len(spans), 'transcript_lines': len(transcript)}


if __name__ == '__main__':
    import argparse
    from pathlib import Path
    parser = argparse.ArgumentParser()
    parser.add_argument('public', type=Path)
    parser.add_argument('timings', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    value = callback_timings(args.public, rows(args.timings))
    args.output.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
    print(json.dumps({key: item for key, item in value.items()
                      if key not in ('callbacks', 'final_callbacks')}))

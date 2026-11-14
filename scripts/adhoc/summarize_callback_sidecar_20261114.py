"""Issue 6233, 2026-11-14: summarize saved controller timing JSONL.

Inputs: sidecar and output prefix. Outputs: JSON and Markdown callback table.
Request-to-response includes ordered queue work; it is not observer-only time.
"""
import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('sidecar', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    events = [json.loads(line) for line in args.sidecar.read_text().splitlines()]
    calls = {}
    for event in events:
        identity = event.get('tool_use_id')
        if identity is None:
            continue
        row = calls.setdefault(identity, {'id': identity, 'tool': event.get('tool_name')})
        row[event['boundary']] = event['elapsed_ns']
    rows = []
    for row in calls.values():
        request, start, end = (row.get(key) for key in ('helper_requested', 'helper_start', 'helper_end'))
        row['request_to_response_seconds'] = (start - request) / 1e9 if request and start else None
        row['response_to_result_seconds'] = (end - start) / 1e9 if start and end else None
        rows.append(row)
    result = {'events': events, 'callbacks': rows,
              'scope': 'Assistant tool-use intake to response flush, including ordered history queue work.'}
    args.output.with_suffix('.json').write_text(json.dumps(result, indent=2))
    lines = [result['scope'], '', '| Tool ID | Tool | Request to response s | Response to result s |',
             '| --- | --- | ---: | ---: |']
    for row in rows:
        values = ['not recorded' if row[key] is None else f'{row[key]:.6f}' for key in
                  ('request_to_response_seconds', 'response_to_result_seconds')]
        lines.append('| ' + row['id'] + ' | ' + row['tool'] + ' | ' + ' | '.join(values) + ' |')
    args.output.with_suffix('.md').write_text('\n'.join(lines) + '\n')
    print(json.dumps({'callbacks': len(rows), 'responses': sum(row['request_to_response_seconds'] is not None for row in rows)}))


if __name__ == '__main__':
    main()

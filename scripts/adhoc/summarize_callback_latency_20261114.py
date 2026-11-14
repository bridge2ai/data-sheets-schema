"""Issue 6233, 2026-11-14: turn saved diagnostic spans into reviewable tables.

Inputs: metrics JSON and output prefix. Outputs: JSON and Markdown; no estimates
are substituted for unobserved spans. Nested totals explicitly overlap.
"""
import argparse
from collections import defaultdict
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('metrics', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    data = json.loads(args.metrics.read_text())
    spans = [row for row in data['spans'] if 'wall' in row]
    totals = defaultdict(lambda: [0, 0., 0.])
    for row in spans:
        key = row['file'] + ':' + row['function']
        total = totals[key]
        total[0] += 1
        total[1] += row['wall']
        total[2] += row['cpu']
    categories = {
        'fresh verification': ('native_shared_callback_capture.py', 'Admission.reconstruct'),
        'source checks': ('native_shared_callback_orchestration.py', '_SourceCheck.__call__'),
        'history verification': ('native_shared_capture.py', '_checked_observations'),
        'hashing': ('native_shared_contract.py', 'sha'),
        'file reads': ('native_shared_evidence.py', 'read_regular'),
    }
    callbacks = []
    for row in spans:
        request = row.get('event', {}).get('request_id')
        if row['function'] != 'CallbackAdapter.observe' or not request:
            continue
        children = [child for child in spans if child['thread'] == row['thread']
                    and row['start'] <= child['start'] and child['end'] <= row['end']]
        values = {label: sum(child['wall'] for child in children
                            if (child['file'], child['function']) == key)
                  for label, key in categories.items()}
        entered = data['intakes'].get(request)
        classification = sum(child['wall'] for child in spans
            if child['file'] == 'native_control.py'
            and child['function'].endswith('._classify_frame')
            and child.get('event', {}).get('request_id') == request)
        inner = sum(child['wall'] for child in children
                    if child['function'] == 'CallbackAdapter._observe')
        callbacks.append({'request': request, 'observation': row['wall'],
                          'classification': classification,
                          'lock_and_wrapper_upper_bound': max(0., row['wall'] - inner),
                          'queue': None if entered is None else row['start'] - entered,
                          **values})
    result = {'callbacks': callbacks, 'inclusive_function_totals': dict(totals),
              'scope': 'Nested wall totals overlap. Queue is intake to observe start. '
                       'Lock bound is observe minus _observe: lock acquisition plus wrapper and '
                       'instrumentation overhead, not a direct lock measurement.'}
    args.output.with_suffix('.json').write_text(json.dumps(result, indent=2))
    lines = [result['scope'], '', '| Function | Calls | Inclusive wall s | Thread CPU s |',
             '| --- | ---: | ---: | ---: |']
    for key, values in sorted(totals.items(), key=lambda item: -item[1][1]):
        lines.append(f'| {key} | {values[0]} | {values[1]:.6f} | {values[2]:.6f} |')
    lines += ['', '| Callback | Queue s | Observe s | Classify s | Fresh verification s | Source checks s | History s | Hash s | Reads s | Lock + wrapper bound s |',
              '| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    for row in callbacks:
        values = ['unmeasured' if row[key] is None else f'{row[key]:.6f}' for key in
                  ('queue', 'observation', 'classification', 'fresh verification', 'source checks',
                   'history verification', 'hashing', 'file reads', 'lock_and_wrapper_upper_bound')]
        lines.append('| ' + row['request'] + ' | ' + ' | '.join(values) + ' |')
    args.output.with_suffix('.md').write_text('\n'.join(lines) + '\n')
    print(json.dumps({'callbacks': len(callbacks), 'completed_spans': len(spans)}))


if __name__ == '__main__':
    main()

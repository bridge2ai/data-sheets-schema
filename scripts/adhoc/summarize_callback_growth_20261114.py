"""Issue 6233, 2026-11-14: render measured callback evidence, never invent CPU.

Input: assigned scratch; outputs: summary JSON and Markdown with fitted slopes.
"""
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

scratch = Path(sys.argv[1])
cases = []
for log in sorted(scratch.glob('*/pytest.log')):
    path = log.parent / 'callback-cpu.jsonl'
    rows = [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []
    callbacks = [r for r in rows if r['event_type'] == 'control_request']
    fits = {}
    for work in ('_observe_event', '_classify_frame'):
        selected = [r for r in callbacks if r['work'] == work and not r['unwound'] and not r.get('cprofile_enabled')]
        if len(selected) < 2:
            continue
        xs, ys = [r['calls'] for r in selected], [r['thread_cpu'] for r in selected]
        xm, ym = sum(xs) / len(xs), sum(ys) / len(ys)
        xx = sum((x - xm) ** 2 for x in xs)
        xy = sum((x - xm) * (y - ym) for x, y in zip(xs, ys))
        yy = sum((y - ym) ** 2 for y in ys)
        slope = xy / xx if xx else None
        fits[work] = {'n': len(xs), 'slope_cpu_seconds_per_callback': slope,
                      'r_squared': xy * xy / (xx * yy) if xx and yy else None,
                      'maximum_thread_cpu': max(ys)}
    result_paths = list(path.parent.rglob('actual-result.json'))
    results = [json.loads(p.read_text()) for p in result_paths]
    junit_path = path.parent / 'junit.xml'
    junit = ET.parse(junit_path).getroot().find('testsuite').attrib if junit_path.exists() else None
    status_path = path.parent / 'exit-status.txt'
    status = int(status_path.read_text()) if status_path.exists() else None
    cases.append({'case': path.parent.name, 'source': str(path) if path.exists() else None, 'fits': fits,
                  'junit': junit, 'exit_status': status,
                  'rows': rows, 'results': [{'state': r['state'], 'first_stop': r['first_stop'],
                                           'runtime_gates_passed': r['runtime_gates_passed']} for r in results]})
destination = scratch / 'callback-summary.json'
destination.write_text(json.dumps(cases, indent=2) + '\n')
cases = json.loads(destination.read_text())
lines = ['Measurements include diagnostic overhead. Process CPU includes other threads; thread CPU isolates the worker.',
         'Callbacks with cProfile enabled have additional profiler overhead and are excluded from the fitted slopes.',
         'Read counts count successful capture returns, including repeats; stream capture reads each accepted extent twice.', '']
for case in cases:
    lines += [case['case'], '', '| Callback | Tool | Work | Thread CPU s | Process CPU s | Wall s | Transcript lines captured | Observation captures | Journal records captured | Record captures | cProfile |',
              '| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |']
    for r in case['rows']:
        if r['event_type'] != 'control_request':
            continue
        records = r['records']
        lines.append(f"| {r['calls']} | {r['tool']} | {r['work']} | {r['thread_cpu']:.6f} | {r['process_cpu']:.6f} | {r['wall']:.6f} | {records.get('transcript', 'not instrumented')} | {records.get('observation', 0)} | {records.get('journal', 0)} | {records.get('record', 0)} | {bool(r.get('cprofile_enabled'))} |")
    lines += ['', 'Fits: ' + json.dumps(case['fits'], sort_keys=True),
              '', 'Public results: ' + json.dumps(case['results'], sort_keys=True),
              '', 'JUnit: ' + json.dumps(case['junit'], sort_keys=True) + '; exit status: ' + str(case['exit_status']), '']
    lines += ['Other ordered observer barriers, grouped by the most recently announced tool call. These can delay the next callback; tool-result work is not part of the preceding permission grant.',
              '', '| Tool call | Event type | Transcript line | Thread CPU s | Wall s | Observation captures | Record captures |',
              '| ---: | --- | ---: | ---: | ---: | ---: | ---: |']
    for r in case['rows']:
        if r['work'] == '_observe_event' and r['event_type'] != 'control_request':
            lines.append(f"| {r['calls']} | {r['event_type']} | {r['line']} | {r['thread_cpu']:.6f} | {r['wall']:.6f} | {r['records'].get('observation', 0)} | {r['records'].get('record', 0)} |")
    lines.append('')
(scratch / 'callback-summary.md').write_text('\n'.join(lines) + '\n')
print(json.dumps([{'case': c['case'], 'fits': c['fits'], 'results': c['results'], 'rows': len(c['rows'])} for c in cases], indent=2))

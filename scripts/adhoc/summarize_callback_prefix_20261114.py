"""Issue 6233, 2026-11-14: summarize saved prefix-fix verification evidence.

Input: assigned scratch and case-directory names. Outputs: JSON and Markdown
with measured callback CPU, byte reads, semantic work and public outcomes.
"""
import json
from pathlib import Path
import statistics
import sys
import xml.etree.ElementTree as ET


def summarize(root, name):
    directory = root / name
    path = directory / 'callback-cpu.jsonl'
    rows = [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []
    selected = [row for row in rows if row['work'] == '_observe_event'
                and row['event_type'] == 'control_request' and not row['unwound']
                and not row.get('cprofile_enabled')]
    fit = None
    if len(selected) > 1:
        xs = [row['calls'] for row in selected]
        ys = [row['thread_cpu'] for row in selected]
        xm, ym = statistics.mean(xs), statistics.mean(ys)
        xx = sum((x - xm) ** 2 for x in xs)
        xy = sum((x - xm) * (y - ym) for x, y in zip(xs, ys))
        yy = sum((y - ym) ** 2 for y in ys)
        early = [row['thread_cpu'] for row in selected if row['calls'] <= 10]
        late = [row['thread_cpu'] for row in selected if row['calls'] > 10]
        fit = {'callbacks': len(selected), 'first_index': min(xs), 'last_index': max(xs),
            'early_range': [min(early), max(early)] if early else None,
            'early_median': statistics.median(early) if early else None,
            'later_range': [min(late), max(late)] if late else None,
            'later_median': statistics.median(late) if late else None,
            'slope_cpu_seconds_per_index': xy / xx if xx else None,
            'r_squared': xy * xy / (xx * yy) if xx and yy else None}
    junit = directory / 'junit.xml'
    suite = ET.parse(junit).getroot().find('testsuite') if junit.exists() else None
    result_paths = list(directory.rglob('actual-result.json'))
    results = []
    for result_path in result_paths:
        result = json.loads(result_path.read_text())
        results.append({'path': str(result_path), 'state': result.get('state'),
            'first_stop': result.get('first_stop'), 'runtime_gates_passed': result.get('runtime_gates_passed')})
    status_path = directory / 'exit-status.txt'
    return {'case': name, 'metrics': str(path) if path.exists() else None,
        'fit': fit, 'rows': rows, 'results': results,
        'junit': None if suite is None else suite.attrib,
        'exit_status': int(status_path.read_text()) if status_path.exists() else None}


def main():
    root = Path(sys.argv[1])
    result = [summarize(root, name) for name in sys.argv[2:]]
    output = root / 'prefix-final-summary.json'
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    result = json.loads(output.read_text())
    lines = ['Independent thread CPU includes diagnostic overhead. Read counts include complete repeated captures.',
        'The fitted slope is descriptive; transitions and final independent replay are not stationary work.', '']
    for case in result:
        lines.extend([case['case'], '', 'Fit: ' + json.dumps(case['fit'], sort_keys=True),
            'Public results: ' + json.dumps(case['results'], sort_keys=True),
            'JUnit: ' + json.dumps(case['junit'], sort_keys=True), '',
            '| Index | Event | CPU seconds | Stream bytes reread | Artifact captures | New observations checked | Stage checks | Response derivations |',
            '| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |'])
        for row in case['rows']:
            if row['work'] != '_observe_event':
                continue
            functions = row.get('functions', {})
            stages = functions.get('__init__.py:_stage_uncached', {}).get('calls', 0)
            responses = functions.get('__init__.py:_derive_response_uncached', {}).get('calls', 0)
            streams = sum(row.get('bytes', {}).get(role, 0) for role in ('transcript', 'control'))
            artifacts = sum(count for role, count in row.get('reads', {}).items() if role not in ('transcript', 'control'))
            observations = row.get('verification_inputs', {}).get('new_observations_checked', 'not instrumented')
            lines.append(f"| {row['calls']} | {row['event_type']} | {row['thread_cpu']:.6f} | {streams} | {artifacts} | {observations} | {stages} | {responses} |")
        lines.append('')
    (root / 'prefix-final-summary.md').write_text('\n'.join(lines) + '\n')
    print(json.dumps([{key: value for key, value in case.items() if key != 'rows'} for case in result], indent=2))


if __name__ == '__main__':
    main()

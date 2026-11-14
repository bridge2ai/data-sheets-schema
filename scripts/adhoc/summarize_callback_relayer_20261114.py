"""Issue 6233, 2026-11-14: summarize saved relayer CPU and validation evidence.

Inputs: scratch directory and read-only baseline metrics. Outputs: JSON and
per-callback Markdown table in scratch. No execution or provider calls.
"""
import hashlib
import json
from pathlib import Path
import statistics
import sys
import xml.etree.ElementTree as ET


def measured(path):
    raw = path.read_bytes() if path.exists() else None
    rows = [json.loads(line) for line in raw.decode().splitlines()] if raw is not None else []
    selected = [row for row in rows if row['work'] == '_observe_event'
                and row['event_type'] == 'control_request' and not row['unwound']
                and not row.get('cprofile_enabled')]
    fit = None
    if len(selected) > 1:
        xs, ys = [row['calls'] for row in selected], [row['thread_cpu'] for row in selected]
        xm, ym = statistics.mean(xs), statistics.mean(ys)
        xx = sum((x - xm) ** 2 for x in xs)
        xy = sum((x - xm) * (y - ym) for x, y in zip(xs, ys))
        yy = sum((y - ym) ** 2 for y in ys)
        fit = {'callbacks': len(xs), 'first_index': min(xs), 'last_index': max(xs),
            'first_ten_median': statistics.median(ys[:10]),
            'last_ten_median': statistics.median(ys[-10:]),
            'slope_cpu_seconds_per_index': xy / xx if xx else None,
            'r_squared': xy * xy / (xx * yy) if xx and yy else None}
    outcomes = []
    for result_path in path.parent.rglob('actual-result.json'):
        result = json.loads(result_path.read_text())
        outcomes.append({'path': str(result_path), 'state': result.get('state'),
            'first_stop': result.get('first_stop'), 'runtime_gates_passed': result.get('runtime_gates_passed')})
    return {'path': str(path), 'sha256': hashlib.sha256(raw).hexdigest() if raw is not None else None,
            'fit': fit, 'rows': selected,
            'outcomes': outcomes,
            'observer_rows': [row for row in rows if row['work'] == '_observe_event']}


def main():
    root, baseline = Path(sys.argv[1]), Path(sys.argv[2])
    output = {'interpreter': sys.version, 'baseline': measured(baseline), 'runs': {}, 'tests': {}}
    for path in sorted(root.glob('*/callback-cpu.jsonl')):
        output['runs'][path.parent.name] = measured(path)
    for path in sorted(root.rglob('*.xml')):
        if path.name == 'junit.xml' or path.parent == root:
            suites = ET.parse(path).getroot().findall('testsuite')
            if suites:
                output['tests'][str(path)] = {
                    key: sum(int(suite.get(key, '0')) for suite in suites)
                    for key in ('tests', 'failures', 'errors', 'skipped')}
    (root / 'summary.json').write_text(json.dumps(output, indent=2, sort_keys=True) + '\n')
    lines = ['Thread CPU at the observer boundary; diagnostic overhead included.',
        'Baseline and current runs are not matched host-load experiments.',
        'Fits are descriptive: stage transitions and final independent replay are distinct work.',
        'Function spans are inclusive and overlap; do not add their columns.', '']
    for name, run in [('baseline', output['baseline']), *output['runs'].items()]:
        lines.extend([name, '', 'Fit: ' + json.dumps(run['fit'], sort_keys=True), '',
            'Saved launch outcomes: ' + json.dumps(run['outcomes'], sort_keys=True), '',
            '| Callback | Observer CPU seconds | Phase-state CPU seconds | Observation CPU seconds | Stage-decision CPU seconds |',
            '| ---: | ---: | ---: | ---: | ---: |'])
        for row in run['rows']:
            def cpu(name):
                values = [value['thread_cpu'] for key, value in row.get('functions', {}).items()
                          if key.endswith(':' + name)]
                return f'{sum(values):.6f}' if values else 'not recorded'
            lines.append(f"| {row['calls']} | {row['thread_cpu']:.6f} | {cpu('_phase_state')} | {cpu('_checked_observations')} | {cpu('_stage_decision')} |")
        lines.append('')
        lines.extend(['All ordered observer barriers, indexed by the latest announced tool.', '',
            '| Callback | Event | CPU seconds | Wall seconds | New observations checked | Unwound |',
            '| ---: | --- | ---: | ---: | ---: | --- |'])
        for row in run['observer_rows']:
            count = row.get('verification_inputs', {}).get('new_observations_checked', 'not instrumented')
            lines.append(f"| {row['calls']} | {row['event_type']} | {row['thread_cpu']:.6f} | {row['wall']:.6f} | {count} | {row['unwound']} |")
        lines.append('')
    (root / 'callback-cpu.md').write_text('\n'.join(lines) + '\n')
    print(json.dumps({'baseline': output['baseline']['fit'],
        'runs': {name: value['fit'] for name, value in output['runs'].items()},
        'outcomes': {name: value['outcomes'] for name, value in output['runs'].items()},
        'tests': output['tests']}, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()

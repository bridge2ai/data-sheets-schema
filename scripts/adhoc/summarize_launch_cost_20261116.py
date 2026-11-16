"""Summarize launch profiling evidence for the Claude lead, 2026-11-16.

Inputs: diagnostic output directory. Outputs: JSON and Markdown timing and stack
reports. Every table derives from saved events, samples or production traces.
"""
from collections import Counter, defaultdict
from datetime import datetime
import json
from pathlib import Path
import sys


def main():
    root = Path(sys.argv[1])
    events = [json.loads(line) for line in (root / 'events.jsonl').read_text().splitlines()]
    samples = [json.loads(line) for line in (root / 'stacks.jsonl').read_text().splitlines()]
    entries = [row for row in events if row['event'] == 'launch_entry']
    launch = entries[0]['time'] if entries else float('inf')
    intervals = []
    starts = {}
    traces = sorted((root / 'case').rglob('host-pre-dispatch-*.jsonl'))
    for path in traces:
        for line in path.read_text().splitlines():
            row = json.loads(line)
            if row['wall_ns'] / 1e9 < launch:
                continue
            key = (row['trace_id'], row.get('step_id'))
            if row.get('phase') == 'start':
                starts[key] = row
            elif row.get('phase') == 'end' and key in starts:
                before = starts.pop(key)
                intervals.append({'phase': row['boundary'], 'start': before['wall_ns'] / 1e9,
                    'end': row['wall_ns'] / 1e9,
                    'seconds': (row['elapsed_ns'] - before['elapsed_ns']) / 1e9})
    light_start = next((row for row in events if row['event'] == 'call_start'
                        and row['function'] == '_light_live'), None)
    if light_start:
        light_end = next((row for row in events if row['event'] == 'call_end'
                         and row['function'] == '_light_live' and row['time'] > light_start['time']), None)
        if light_end:
            intervals.append({'phase': 'one_light_census', 'start': light_start['time'],
                              'end': light_end['time'], 'seconds': light_end['seconds']})
    wanted = {'controller_prewarm', 'registration.verified', 'admission_with_classifier', '_current_authority', 'one_light_census'}
    report = ['# Launch cost profile', '', 'Nested intervals overlap; do not add them.', '',
              '| Phase | Call | Seconds |', '| --- | ---: | ---: |']
    counts = Counter()
    profiles = []
    for span in sorted(intervals, key=lambda row: row['start']):
        if span['phase'] not in wanted:
            continue
        counts[span['phase']] += 1
        number = counts[span['phase']]
        report.append(f"| {span['phase']} | {number} | {span['seconds']:.3f} |")
        chosen = [row for row in samples if span['start'] <= row['time'] < span['end']]
        inclusive, leaves = Counter(), Counter()
        for row in chosen:
            names = [str(Path(frame[0]).name) + ':' + frame[1] for frame in row['stack']]
            inclusive.update(set(names))
            if names:
                leaves[names[0]] += 1
        profiles.append({**span, 'call': number, 'samples': len(chosen),
            'inclusive': inclusive.most_common(30), 'leaves': leaves.most_common(15)})
    report.extend(['', 'Sampling fractions estimate where the main thread was observed; they are not deterministic function timings.'])
    for row in profiles:
        report.extend(['', f"## {row['phase']} call {row['call']}", '',
                       '| Sampled leaf | Samples | Fraction |', '| --- | ---: | ---: |'])
        for name, count in row['leaves']:
            report.append(f"| {name} | {count} | {count / row['samples']:.3f} |")
        report.extend(['', '| Inclusive stack function | Samples | Fraction |', '| --- | ---: | ---: |'])
        for name, count in row['inclusive']:
            report.append(f"| {name} | {count} | {count / row['samples']:.3f} |")
    calls = Counter()
    for row in events:
        if row['event'] == 'call_start':
            caller = row['callers'][1] if len(row['callers']) > 1 else ['', '', 0]
            calls[(row['phase'], row['file'], row['function'], str(Path(caller[0]).name), caller[1], caller[2])] += 1
    report.extend(['', '## Verification caller inventory', '', '| Stage | Function | Caller | Calls |', '| --- | --- | --- | ---: |'])
    for (phase, file, function, caller_file, caller, line), count in sorted(calls.items()):
        report.append(f'| {phase} | {file}:{function} | {caller_file}:{caller}:{line} | {count} |')
    result = {'profiles': profiles, 'events': events, 'intervals': intervals}
    if entries:
        captured = datetime.fromisoformat(entries[0]['guard']['captured_at'].replace('Z', '+00:00')).timestamp()
        result['capture_to_launch_seconds'] = launch - captured
    (root / 'summary.json').write_text(json.dumps(result, indent=2))
    (root / 'profile.md').write_text('\n'.join(report) + '\n')
    print(json.dumps({'profiles': len(profiles), 'events': len(events), 'samples': len(samples),
                      'capture_to_launch_seconds': result.get('capture_to_launch_seconds')}))


if __name__ == '__main__':
    main()

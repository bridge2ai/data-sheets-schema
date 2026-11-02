#!/usr/bin/env python3
"""Summarize measured D76 SG2 process accumulation, PR #5213, 2026-11-02.

Inputs: immutable round-3 diagnostic run directory. Output: new JSON report of
the serial47+none+explicit sequence, phase times, peak RSS and cache counters.
Reports observations, not causal attribution or cross-host timing claims.
"""
import argparse
import hashlib
import json
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def summarize(root):
    plan = json.loads((root / 'plan.json').read_text())
    outcome = json.loads((root / 'outcome.json').read_text())
    artifacts = {path.name: digest(path) for path in root.glob('metrics-*.jsonl')}
    events, parse_errors = [], []
    for name in artifacts:
        for number, line in enumerate((root / name).read_bytes().splitlines(keepends=True), 1):
            try:
                if not line.endswith(b'\n'):
                    raise ValueError('unterminated metrics row')
                event = json.loads(line)
                if not isinstance(event, dict) or not all(key in event for key in ('pid', 'event', 'monotonic', 'state')):
                    raise ValueError('invalid metrics event shape')
                events.append(event)
            except (ValueError, UnicodeError) as exc:
                parse_errors.append({'file': name, 'line': number, 'reason': str(exc),
                    'bytes': len(line), 'sha256': hashlib.sha256(line).hexdigest()})
    pids = {event['pid'] for event in events}
    if plan['workers'] != 0 or len(pids) != 1:
        raise ValueError('diagnostic must be a single serial pytest process')
    events.sort(key=lambda event: event['monotonic'])
    starts, rows = {}, []
    for event in events:
        if event['event'] == 'test_start':
            starts[event['nodeid']] = event
        elif event['event'] == 'test_end':
            start = starts.pop(event['nodeid'], None)
            if start is None:
                parse_errors.append({'kind': 'test_end_without_valid_start',
                    'nodeid': event['nodeid'], 'pid': event['pid'], 'monotonic': event['monotonic']})
                continue
            before, after = start['state'], event['state']
            differences = {name: {'before': before['caches'].get(name), 'after': value}
                for name, value in after['caches'].items() if before['caches'].get(name) != value}
            rows.append({'nodeid': event['nodeid'], 'elapsed_seconds': event['elapsed_seconds'],
                'peak_rss_before_bytes': before['peak_rss_bytes'],
                'peak_rss_after_bytes': after['peak_rss_bytes'],
                'gc_before': before['gc_stats'], 'gc_after': after['gc_stats'],
                'cache_counter_changes': differences})
    sg2 = [row for row in rows if 'test_sg2_root_launch_completes_and_records_registered_paths[' in row['nodeid']]
    binding = [row for row in rows if 'test_wave7_5213_d76_round2_binding.py::' in row['nodeid']]
    sequence = [row['nodeid'] for row in rows]
    expected = (len(rows) == 49 and len(binding) == 47 and len(sg2) == 2 and rows[:47] == binding
                and sequence[-2].endswith('[none]') and sequence[-1].endswith('[explicit]'))
    for name in ('outcome.json', 'plan.json', 'nodes.json', 'phase-accounting.json', 'controller-rss.jsonl',
                 'deadline.json', 'pytest.xml', 'source-before.json', 'source-after.json'):
        if (root / name).is_file():
            artifacts[name] = digest(root / name)
    return {'head': plan['head'], 'run': str(root), 'single_pytest_pid': next(iter(pids)),
        'complete_required_sequence': expected and not starts and not parse_errors,
        'metrics_parse_errors': parse_errors,
        'completed_cases': rows, 'incomplete_started_nodes': list(starts), 'sg2_cases': sg2,
        'outcome': outcome, 'artifact_sha256': artifacts,
        'interpretation': 'Cache/RSS changes are observations, not proof of cause. Peak RSS never decreases; '
            'current controller RSS samples are separate. Concurrent host work prevents benchmark claims.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    result = summarize(args.run.resolve(strict=True))
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(args.output)
    print(digest(args.output))


if __name__ == '__main__':
    main()

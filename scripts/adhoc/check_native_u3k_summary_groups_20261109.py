#!/usr/bin/env python3
"""Check U3-K retained-timing grouping, 2026-11-09.

Inputs: synthetic overlapping/adjacent/cross-thread intervals and the summary
helper. Output: a fresh JSON witness under U3-K scratch. No project imports,
launches, profiling, subprocesses, network or changes to existing evidence.
"""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve()
HELPER = HERE.with_name('summarize_native_u3k_validation_20261109.py')
spec = importlib.util.spec_from_file_location('u3k_summary_groups', HELPER)
summary = importlib.util.module_from_spec(spec)
spec.loader.exec_module(summary)


def row(label, start, duration, cpu, *, thread=1, outcome='return'):
    return dict(label=label, entered_wall=start, inclusive_wall=duration,
                inclusive_thread_cpu=cpu, thread=thread, outcome=outcome)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    summary.quiet()
    summary.require(args.out.parent == summary.BASE and args.out.suffix == '.json'
                    and not args.out.exists(), 'fresh U3-K JSON output required')
    summary.physical(args.out.parent, directory=True)
    boundary = row('public_launch', 0, 10, 5, outcome='exception:ValueError')
    calls = [boundary, row('lookup', 1, 2, 0.7), row('lookup', 3, 1, 0.2),
             row('nested', 1, 4, 1), row('nested', 3, 4, 1),
             row('foreign', 1, 1, 99, thread=2), row('outside', 9, 2, 99),
             row('unfinished', 1, 1, 99, outcome='open')]
    actual = summary.public_call_groups(calls, [{'call_index': 0, **boundary}])
    summary.require(len(actual) == 1 and actual[0]['boundary_call_index'] == 0,
                    'exception-completed boundary omitted')
    labels = {item['label']: item for item in actual[0]['labels']}
    summary.require(set(labels) == {'lookup', 'nested', 'public_launch'},
                    'foreign, uncontained or open interval admitted')
    summary.require(labels['lookup']['call_indices'] == [1, 2]
        and labels['lookup']['calls'] == 2
        and labels['lookup']['same_label_intervals_disjoint'] is True
        and math.isclose(labels['lookup']['inclusive_thread_cpu_sum'], 0.9),
        'adjacent disjoint calls miscounted')
    summary.require(labels['nested']['call_indices'] == [3, 4]
        and labels['nested']['same_label_intervals_disjoint'] is False
        and labels['nested']['inclusive_thread_cpu_sum'] is None,
        'overlapping same-label CPU summed')
    summary.require(summary.public_call_groups(calls,
        [{'call_index': 0, **boundary, 'outcome': 'open'}]) == [],
        'unfinished boundary admitted')
    try:
        summary.public_call_groups([boundary, row('bad', 1, -1, 0)],
                                   [{'call_index': 0, **boundary}])
    except ValueError as error:
        summary.require(str(error) == 'invalid completed monitored interval',
                        'unexpected negative-interval refusal')
    else:
        raise AssertionError('negative interval admitted')
    value = {'kind': 'native_u3k_grouping_canary', 'passed': True,
        'checks': ['adjacent-and-thread-containment', 'nested-not-added',
                   'open-boundary-excluded', 'negative-interval-refused'],
        'actual_groups': actual,
        'helper_sha256': hashlib.sha256(HELPER.read_bytes()).hexdigest(),
        'check_script_sha256': hashlib.sha256(HERE.read_bytes()).hexdigest()}
    raw = (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()
    summary.quiet()
    with args.out.open('xb') as stream:
        stream.write(raw)
    summary.require(args.out.read_bytes() == raw, 'witness did not persist')
    print(json.dumps({'path': str(args.out), 'bytes': len(raw),
                      'sha256': hashlib.sha256(raw).hexdigest(), 'passed': True}))


if __name__ == '__main__':
    main()

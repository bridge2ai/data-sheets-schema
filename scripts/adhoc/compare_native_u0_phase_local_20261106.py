#!/usr/bin/env python3
"""Compare completed U0 phases from saved evidence, #4354/D92, 2026-11-06.

Input: the existing causal-pair analysis JSON and its pinned recorder JSONLs.
Output: one new JSON supplement. No measurement, production imports, subprocesses
or edits to the original analyzer/global-work gate. Boundary proof is conservative.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import importlib.util
import json
from pathlib import Path


_SPEC = importlib.util.spec_from_file_location('_u0_pair_saved_reader',
    Path(__file__).with_name('analyze_native_u0_causal_pair_20261106.py'))
analysis = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(analysis)
reader = analysis.reader
PRODUCERS = {
    'native_schema_member_visits': 'schema_snapshot:_capture_native_schema',
    'audit_omissions:_schema_yaml': 'audit_omissions:_schema_yaml',
    'audit_omissions:_mapping': 'audit_omissions:_mapping',
    'audit_omissions:_load_yaml': 'audit_omissions:_load_yaml',
    'native_shared_capture:_document': 'native_shared_capture:_document',
    # Count-only parser monitoring deliberately emits no phase-start event.
    'yaml:parse_started': None,
}
REQUIRED_WORK = ('native_schema_member_visits', 'audit_omissions:_schema_yaml')
ZERO = {'calls': 0, 'input_bytes': 0, 'hash_counts': {},
        'hash_coverage_complete': True, 'non_text_inputs': 0}


def document(value):
    if value is None:
        return dict(ZERO)
    counts = value.get('hash_counts', {})
    if (value.get('hash_coverage_complete') is not True or value.get('non_text_inputs') != 0
            or type(value.get('calls')) is not int or value['calls'] < 0
            or type(value.get('input_bytes')) is not int or value['input_bytes'] < 0
            or not isinstance(counts, dict)
            or not all(isinstance(key, str) and len(key) == 64 and type(count) is int and count > 0
                       for key, count in counts.items())
            or sum(counts.values()) != value['calls']):
        raise ValueError('document hash/count coverage is incomplete or malformed')
    return {key: value[key] for key in ZERO}


def subtract(end, start):
    counts = {key: end['hash_counts'].get(key, 0) - start['hash_counts'].get(key, 0)
        for key in end['hash_counts'].keys() | start['hash_counts'].keys()}
    result = {'calls': end['calls'] - start['calls'],
        'input_bytes': end['input_bytes'] - start['input_bytes'],
        'hash_counts': {key: value for key, value in counts.items() if value},
        'hash_coverage_complete': True, 'non_text_inputs': 0}
    if min([result['calls'], result['input_bytes'], *counts.values()], default=0) < 0:
        raise ValueError('document counts/bytes regressed')
    return document(result)


class SavedArm:
    def __init__(self, arm, rows, evidence):
        self.arm, self.rows, self.evidence = arm, rows, evidence
        starts = [row for row in rows if row['event'] == 'observer_start']
        if (len(starts) != 1 or starts[0].get('root') != arm['source_root']
                or evidence['parse_errors'] or any(row.get('valid') is False
                    or row['event'] == 'observer_error' for row in rows)):
            raise ValueError('recorder start/source/validity evidence differs')
        self.targets = {row['id'] for row in starts[0].get('targets', [])}
        self.snapshots = [row for row in rows if row['event'] == 'thread_cpu_checkpoint']
        if not self.snapshots:
            raise ValueError('no document checkpoints')
        counters = [row for row in rows if row['event'] == 'counter_snapshot']
        self.counts = counters[-1].get('stats', {}) if counters else {}
        self.starts = [row for row in rows if row['event'] == 'phase_start']
        self.start_count = Counter(row['target'] for row in self.starts)
        self.completed = {}
        self.partials = []
        ends = {row['call']: row for row in rows if row['event'] == 'phase_end'}
        if len(ends) != sum(row['event'] == 'phase_end' for row in rows):
            raise ValueError('duplicate phase ends')
        ordinals = Counter()
        calls = set()
        for start in self.starts:
            target, call = start['target'], start['call']
            if call in calls:
                raise ValueError('duplicate phase starts')
            calls.add(call)
            ordinals[target] += 1
            end = ends.get(call)
            if not end:
                self.partials.append({'target': target, 'call': call,
                    'ordinal': ordinals[target], 'start_sequence': start['sequence']})
                continue
            if (end['target'] != target or end['sequence'] <= start['sequence']
                    or end.get('outcome') not in ('returns', 'unwinds')
                    or not all(analysis.nonnegative(end.get('inclusive_rusage_delta', {}).get(key))
                               for key in analysis.CPU_FIELDS)):
                raise ValueError('invalid phase end/binding/CPU')
            self.completed[(target, ordinals[target])] = (start, end)
        # No source/import operations: this checks saved monotone document counters.
        self.document_errors = {}
        for name in PRODUCERS:
            previous = dict(ZERO)
            try:
                for checkpoint in self.snapshots:
                    current = document(checkpoint.get('documents', {}).get(name))
                    subtract(current, previous)
                    previous = current
            except Exception as exc:
                self.document_errors[name] = str(exc)

    def boundary(self, name, event, *, entry):
        """Bind a counter just before entry's update or just after phase exit.

        Document counters update before the corresponding phase_start event is
        emitted. A conceptual event position separates that update from entry.
        A neighboring snapshot is usable only when all producer entries are logged
        and none falls between it and the boundary. Equal bracketing snapshots
        also prove no counter increment, even for the count-only parser/capped phases.
        """
        producer = PRODUCERS[name]
        if name in self.document_errors:
            return {'verified': False, 'reason': self.document_errors[name]}
        target = producer or 'yaml:parse'
        if target not in self.targets:
            return {'verified': False, 'reason': 'document producer absent from monitored roster'}
        position = event['sequence'] + (-0.5 if entry else 0.5)
        before = [row for row in self.snapshots if row['sequence'] < position]
        after = [row for row in self.snapshots if row['sequence'] > position]
        left, right = (before[-1] if before else None), (after[0] if after else None)
        if left and right:
            a, b = (document(row.get('documents', {}).get(name)) for row in (left, right))
            if a == b:
                return {'verified': True, 'method': 'equal_monotone_bracketing_snapshots', 'value': a,
                    'snapshot_sequences': [left['sequence'], right['sequence']],
                    'boundary_event_sequence': event['sequence'], 'entry': entry}
        full_starts = bool(producer and producer in self.counts
            and self.counts[producer].get('calls') == self.start_count[producer])
        if not full_starts:
            return {'verified': False,
                'reason': 'no equal bracket and no complete producer-start coverage (count-only/capped/censored)'}
        for checkpoint in sorted(self.snapshots, key=lambda row: abs(row['sequence'] - position)):
            low, high = sorted((position, checkpoint['sequence']))
            crossing = [row['sequence'] for row in self.starts if row['target'] == producer
                and low < row['sequence'] - 0.25 < high]
            if crossing:
                continue
            return {'verified': True, 'method': 'complete_producer_start_roster_no_intervening_start',
                'value': document(checkpoint.get('documents', {}).get(name)),
                'snapshot_sequences': [checkpoint['sequence']],
                'boundary_event_sequence': event['sequence'], 'entry': entry,
                'producer': producer, 'producer_starts_in_saved_prefix': self.start_count[producer]}
        return {'verified': False, 'reason': 'every snapshot crosses a document-producing entry'}

    def phase(self, key):
        start, end = self.completed[key]
        work = {}
        for name in PRODUCERS:
            a = self.boundary(name, start, entry=True)
            b = self.boundary(name, end, entry=False)
            item = {'entry': a, 'exit': b, 'verified': a['verified'] and b['verified']}
            if item['verified']:
                try:
                    item['delta'] = subtract(b['value'], a['value'])
                except ValueError as exc:
                    item.update(verified=False, reason=str(exc))
            work[name] = item
        return {'call': start['call'], 'ordinal': key[1], 'target': key[0],
            'start_sequence': start['sequence'], 'end_sequence': end['sequence'],
            'start_elapsed_ns': start.get('elapsed_ns'), 'end_elapsed_ns': end.get('elapsed_ns'),
            'outcome': end['outcome'], 'inclusive_rusage_delta': end['inclusive_rusage_delta'],
            'work': work}


def load_arm(arm):
    if not arm.get('observed_measurement_prefix_valid') or not arm.get('source_preservation_verified'):
        raise ValueError('arm prefix/source preservation is not verified')
    recorder = arm['recorder']
    expected = recorder['observer_jsonl']['artifact']
    rows, evidence = reader.observer_events(Path(expected['path']))
    if evidence['artifact'] != expected:
        raise ValueError('saved recorder bytes differ from pair-analysis pin')
    return SavedArm(arm, rows, evidence)


def supplement(pair):
    if not pair.get('comparison', {}).get('matching_common_instrumentation_and_external_monitored_pins'):
        raise ValueError('pair lacks matching common instrumentation/interpreter/dependency pins')
    if not pair['comparison'].get('distinct_source_roots_and_heads'):
        raise ValueError('pair source roots/heads are not distinct')
    control, treatment = load_arm(pair['control']), load_arm(pair['treatment'])
    included, excluded = [], []
    keys = sorted(control.completed.keys() | treatment.completed.keys())
    for key in keys:
        if key not in control.completed or key not in treatment.completed:
            excluded.append({'target': key[0], 'ordinal': key[1], 'reason': 'completed call absent in one arm'})
            continue
        a, b = control.phase(key), treatment.phase(key)
        reasons = []
        if a['outcome'] != b['outcome']:
            reasons.append('call outcomes differ')
        for name in REQUIRED_WORK:
            aw, bw = a['work'][name], b['work'][name]
            if not aw['verified'] or not bw['verified']:
                reasons.append(name + ': boundary work not proved')
            elif any(aw[side]['value'] != bw[side]['value'] for side in ('entry', 'exit')):
                reasons.append(name + ': boundary multisets/counts differ')
            elif aw['delta'] != bw['delta']:
                reasons.append(name + ': completed call work differs')
        row = {'target': key[0], 'ordinal': key[1], 'control': a, 'treatment': b}
        if reasons:
            row['reasons'] = reasons
            excluded.append(row)
            continue
        row['inclusive_cpu_comparison'] = {}
        for field in analysis.CPU_FIELDS:
            c, t = a['inclusive_rusage_delta'][field], b['inclusive_rusage_delta'][field]
            row['inclusive_cpu_comparison'][field] = {'control': c, 'treatment': t,
                'treatment_minus_control': t - c, 'treatment_over_control': t / c if c else None}
        row['optional_document_equality'] = {name: (
            a['work'][name]['delta'] == b['work'][name]['delta']
            if a['work'][name]['verified'] and b['work'][name]['verified'] else None)
            for name in PRODUCERS if name not in REQUIRED_WORK}
        included.append(row)
    return {'format': 'native_u0_phase_local_saved_supplement_v1',
        'global_analyzer_gate_unchanged': pair['comparison']['matching_native_schema_member_work'],
        'scope': 'matching completed call observations only; no automatic causal/acceptance/timing verdict',
        'required_work': list(REQUIRED_WORK), 'compared_completed_calls': included,
        'excluded_calls': excluded, 'partial_control_calls': control.partials,
        'partial_treatment_calls': treatment.partials,
        'input_recorder_pins': {'control': control.evidence['artifact'], 'treatment': treatment.evidence['artifact']},
        'limitations': [*analysis.LIMITATIONS,
            'native_schema_member_visits counts requested member tuples at function entry, not completed validations.',
            'yaml:parse_started counts the generator first advancement, not accepted documents.',
            'A completed call is paired by target and per-target call ordinal; differing later calls do not change its endpoints.',
            'Boundary member/schema work equality does not establish equality of root/path-dependent manifests or all downstream outputs.',
            'Document counts require equal monotone bracketing snapshots or a complete producer-start roster without an intervening start.',
            'The full-run latest-member equality gate remains unchanged; this separately labeled supplement cannot override it.']}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pair-analysis', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(argv)
    if args.out.exists():
        parser.error('output already exists')
    pair, pin = reader.json_file(args.pair_analysis)
    result = supplement(pair)
    result.update(pair_analysis_pin=pin, helper_pin=reader.read_regular(Path(__file__))[1],
        analyzer_pin=reader.read_regular(Path(analysis.__file__))[1])
    analysis.write_result(args.out, result)
    print(json.dumps({'output': str(args.out), 'sha256': reader.read_regular(args.out)[1]['sha256'],
        'compared_completed_calls': len(result['compared_completed_calls']),
        'excluded_calls': len(result['excluded_calls']), 'wall_time_verdict': 'not_assessed'}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

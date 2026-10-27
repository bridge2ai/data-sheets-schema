#!/usr/bin/env python3
# Purpose: verify and summarize the failed Wave2 P1/#5149/#5212 idle gate privately.
# Inputs: seven existing idle-only gate files; outputs: exclusive summary and lossless archive.
# Date: 2026-10-27. No sampling, tests, providers, target edits or command/environment disclosure.
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HEAD = '01969cbed8eed93f420c640c1f1c306e5f58b033'
ARCHIVER_SHA = '58ed839ba30d30f1089741c0e233fba01477bade741ea6a0a3b8a6a59284f187'
GATE = Path('/private/tmp/d4d-recorder-measurements-20261026/idle-check-wave2-20261027')
ROSTER = frozenset({'idle-decision.json', 'outcome.json', 'uptime-before-tests.txt',
                    'plan.json', 'source-before.json', 'source-after.json', 'host.jsonl'})
THRESHOLDS = {'mean_cpu_percent': 15.0, 'peak_cpu_percent': 35.0,
              'one_minute_load_per_cpu': 0.5, 'foreign_process_cpu_percent': 5.0}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def archiver():
    path = ROOT / 'scripts/adhoc/archive_n2_restack_validation_20261027.py'
    if sha(path.read_bytes()) != ARCHIVER_SHA:
        raise ValueError('reviewed archive primitives differ')
    spec = importlib.util.spec_from_file_location('wave2_reviewed_archiver', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def snapshot(module):
    module.physical(GATE)
    paths = sorted(GATE.iterdir())  # Includes hidden/ignored entries, with no gitignore filtering.
    if {path.name for path in paths} != ROSTER:
        raise ValueError('gate evidence roster differs from the seven reviewed original files')
    return {path.name: module.read_file(path) for path in paths}


def numeric(value):
    return type(value) in (int, float) and math.isfinite(value)


def build_summary(files):
    def load(name):
        return json.loads(files[name]['raw'])
    before, after = load('source-before.json'), load('source-after.json')
    plan, outcome, decision = load('plan.json'), load('outcome.json'), load('idle-decision.json')
    if (files['source-before.json']['raw'] != files['source-after.json']['raw']
            or before != after or before['head'] != HEAD or before['pristine'] is not True
            or before['tracked_status'] or before['missing_python']
            or not all(row['committed_exact'] is True for row in before['files'].values())
            or plan['idle_only'] is not True or plan['idle_window_seconds'] != 60
            or plan['target'] != 'current' or plan['mode'] != 'idle'
            or outcome['status'] != 'blocked_host_busy' or outcome['source_unchanged'] is not True
            or outcome['returncode'] is not None or 'child_pid' in outcome):
        raise ValueError('saved exact-source or idle-only boundary differs')
    driver = ROOT / 'scripts/adhoc/native_recorder_measure_20261026.py'
    if plan['helper']['sha256'] != sha(driver.read_bytes()):
        raise ValueError('recorded measurement driver differs from retained reviewed source')
    samples = [json.loads(line) for line in files['host.jsonl']['raw'].splitlines()]
    if len(samples) != 60 or decision['samples'] != 60 or decision['thresholds'] != THRESHOLDS:
        raise ValueError('sample count or declared thresholds differ')
    previous = None
    by_time = {}
    for sample in samples:
        if (sample['stage'] != 'before' or not numeric(sample['cpu_percent'])
                or not 0 <= sample['cpu_percent'] <= 100
                or type(sample['logical_cpus']) is not int or sample['logical_cpus'] <= 0
                or not numeric(sample['monotonic'])
                or (previous is not None and sample['monotonic'] <= previous)
                or not isinstance(sample['at'], str) or sample['at'] in by_time
                or len(sample['load']) != 3 or not all(numeric(x) and x >= 0 for x in sample['load'])):
            raise ValueError('malformed or nonconsecutive host sample')
        previous = sample['monotonic']
        by_time[sample['at']] = sample
        seen = set()
        for row in sample['processes']:
            if (set(row) != {'pid', 'ppid', 'cpu_percent', 'name'}
                    or type(row['pid']) is not int or row['pid'] <= 0 or row['pid'] in seen
                    or type(row['ppid']) is not int or row['ppid'] < 0
                    or not numeric(row['cpu_percent']) or row['cpu_percent'] < 0
                    or not isinstance(row['name'], str) or not row['name']
                    or '\n' in row['name'] or '\r' in row['name']):
                raise ValueError('process sample is not the reviewed names-only shape')
            seen.add(row['pid'])
    measured = {
        'mean_cpu_percent': sum(row['cpu_percent'] for row in samples) / len(samples),
        'peak_cpu_percent': max(row['cpu_percent'] for row in samples),
        'max_one_minute_load_per_cpu': max(row['load'][0] / row['logical_cpus'] for row in samples),
    }
    if any(not numeric(decision[key]) or not math.isclose(value, decision[key], rel_tol=0, abs_tol=1e-10)
           for key, value in measured.items()):
        raise ValueError('retained decision aggregate differs from raw samples')
    competitors, observation_times = {}, set()
    for observation in decision['competing_process_observations']:
        at = observation['at']
        if at not in by_time or at in observation_times or not observation['processes']:
            raise ValueError('competing-process observation lacks unique raw sample')
        observation_times.add(at)
        seen = set()
        for row in observation['processes']:
            if (row not in by_time[at]['processes'] or row['cpu_percent'] < THRESHOLDS['foreign_process_cpu_percent']
                    or row['pid'] in seen):
                raise ValueError('reported competitor is not a unique above-threshold sampled process')
            seen.add(row['pid'])
            key = row['pid'], row['name']
            item = competitors.setdefault(key, {'pid': row['pid'], 'executable': Path(row['name']).name,
                'observed_above_threshold_samples': 0, 'sum_observed_cpu_percent': 0.0,
                'peak_observed_cpu_percent': 0.0})
            item['observed_above_threshold_samples'] += 1
            item['sum_observed_cpu_percent'] += row['cpu_percent']
            item['peak_observed_cpu_percent'] = max(item['peak_observed_cpu_percent'], row['cpu_percent'])
    failed = []
    for metric, threshold in (('mean_cpu_percent', 'mean_cpu_percent'), ('peak_cpu_percent', 'peak_cpu_percent'),
                              ('max_one_minute_load_per_cpu', 'one_minute_load_per_cpu')):
        if measured[metric] > THRESHOLDS[threshold]:
            failed.append(metric)
    if competitors:
        failed.append('above_threshold_competing_processes')
    if not failed or decision['idle'] is not False:
        raise ValueError('saved refusal does not follow the recorded gate conditions')
    ranked = sorted(competitors.values(), key=lambda row: (-row['sum_observed_cpu_percent'], row['pid'], row['executable']))
    for row in ranked:
        row['mean_cpu_percent_when_reported_above_threshold'] = row['sum_observed_cpu_percent'] / row['observed_above_threshold_samples']
    return {'format': 'd4d_wave2_recorder_gate_summary_v1', 'refs': ['#5149', '#5212', '#4354'],
        'original_directory': str(GATE), 'status': outcome['status'],
        'started_at': plan['started_at'], 'finished_at': outcome['finished_at'],
        'driver_wall_seconds': outcome['driver_wall_seconds'], 'samples': len(samples),
        'sample_interval_seconds': samples[-1]['monotonic'] - samples[0]['monotonic'],
        'sample_first_at': samples[0]['at'], 'sample_last_at': samples[-1]['at'],
        'measured': measured, 'thresholds': THRESHOLDS, 'failed_conditions': failed,
        'source': {'head': before['head'], 'tree': before['tree'], 'saved_inventories_byte_identical': True,
                   'saved_pristine_source': True, 'inventory_scope': before['inventory_scope'],
                   'new_target_source_inspection_performed': False},
        'measurement_driver_sha256': plan['helper']['sha256'],
        'recorder_trials_launched': 0, 'scientific_acceptance': 'not_assessed',
        'competing_observation_samples': len(observation_times), 'distinct_reported_competitors': len(ranked),
        'top_competitors': ranked[:10],
        'competitor_scope': 'Recorded driver classification; each entry joined to its raw sample and checked against threshold. Ownership exclusions are not independently recomputed.',
        'ranking_scope': 'Descending sum of reported above-threshold CPU percentages; this is a ranking statistic, not elapsed CPU time or host-CPU attribution. Unreported intervals are not assumed idle.',
        'privacy': 'Summary retains executable basename and PID only; no argv, environment values or executable directory paths. Original names-only raw files are preserved unchanged in the archive.',
        'limits': ['No assertion that pytest, uv, Claude or AGY test processes were absent.',
                   'Executable names do not establish process role or earlier-timeout causality.',
                   'Three unchanged trials and any paired diagnosis remain pending a qualifying host gate.',
                   'No recorder timing was measured and no production timeout was altered.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output
    if (not output.is_absolute() or output.resolve() != output or output.exists() or output.is_symlink()
            or not output.is_relative_to(ROOT / 'notes')):
        raise ValueError('fresh physical output under this repository notes required')
    module = archiver()
    files = snapshot(module)
    summary = build_summary(files)
    output.mkdir(parents=True, exist_ok=False)
    archive = output / 'gate1_originals.tar.gz'
    module.write_archive(archive, files)
    if snapshot(module) != files:
        raise ValueError('original gate evidence changed during preservation')
    helper = Path(__file__).resolve()
    summary.update(helper={'path': str(helper.relative_to(ROOT)), 'sha256': sha(helper.read_bytes())},
        archive_helper={'path': 'scripts/adhoc/archive_n2_restack_validation_20261027.py', 'sha256': ARCHIVER_SHA},
        archive={'path': archive.name, 'bytes': archive.stat().st_size, 'sha256': sha(archive.read_bytes()),
                 'every_original_file_archived': True, 'all_member_bytes_and_modes_verified': True},
        files={name: {'bytes': len(item['raw']), 'mode': item['mode'], 'sha256': sha(item['raw'])}
               for name, item in sorted(files.items())}, original_inputs_rechecked_unchanged=True)
    with (output / 'gate1_summary.json').open('x') as stream:
        json.dump(summary, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'summary': str(output / 'gate1_summary.json'), 'status': summary['status'],
                      'samples': summary['samples'], 'measured': summary['measured'],
                      'top_competitors': summary['top_competitors'], 'archive_sha256': summary['archive']['sha256']}, sort_keys=True))


if __name__ == '__main__':
    main()

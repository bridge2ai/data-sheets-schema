#!/usr/bin/env python3
"""Roll up explicitly supplied completed U3-K evidence, 2026-11-09.

Inputs: repeated --run physical completed U3-K directories; optional --parity-run
CANARY FULL from that same supplied set; frozen disjoint parity baselines.
Output: one fresh --out JSON directly under U3-K. Supports U3-K validation
reporting; no native/scientific acceptance. Standard library only; no project
imports, subprocesses, network, tests, evidence rewrites or pstats loading.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT.parent / 'scratch-native-u1u3/u3k'
LOCK = ROOT.parent / 'plans/native_quiet_window.lock'
LIMIT = 128 * 1024 * 1024
CPU = ('wall_monotonic', 'process_cpu', 'thread_cpu', 'self_user_cpu',
       'self_system_cpu', 'reaped_child_user_cpu', 'reaped_child_system_cpu')
PUBLIC = {
    'tests/test_native_shared_execution.py::test_actual_public_correction_three_workers_and_saved_completion',
    'tests/test_native_shared_execution_variant.py::test_actual_public_merged_omissions_and_all_chunk_statuses',
}
PARITY = frozenset({'generic.txt', 'tuned.txt', 'bc1.txt',
    'declared_heading_spans_v1.txt', 'captured_json_values_v1.txt'}
    | {'generic_v' + str(i) + '.txt' for i in range(2, 11)})
D127 = {
    'src/data_sheets_schema/shared_generation.py': '2ec18e60316423035f88a2a30263c56385bfbbc587303e84e805a8349ab4f781',
    'src/data_sheets_schema/api_runner.py': '3e8b7e5d3cc13c5ebc508e33f865e9ac484056fde16126118719d740656a4fb7',
    'src/download/prompts/canonical_hashes.yaml': '543e5cd6dc0da0f622ba2cd11a16a90732e9302a1ed0a4700efb61971299d252',
    'tests/utils/run_spec_boundary_contracts.json': 'b1e0cbd14c533a51b88eacb84b974cb93963e18d8f1fb71ae4ed3228f784d1ce',
}
CPU_POLICY = ('Worker process CPU, calling-thread CPU, self user/system CPU and '
    'reaped-child user/system CPU remain separate. Recorder helper CPU is not '
    'isolated. Coarse calls and pytest/explicit phases may nest or overlap; no '
    'nested durations are summed. Reaped-child CPU appears only after reaping.')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def quiet():
    if os.path.lexists(LOCK):
        raise RuntimeError('quiet-window lock active; summary stopped')


def physical(path, directory=False):
    quiet()
    require(path.is_absolute() and path.resolve(strict=True) == path
            and not path.is_symlink(), 'expected physical absolute path: ' + str(path))
    require(path.is_dir() if directory else path.is_file(),
            'wrong file kind: ' + str(path))


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def pairs(items):
    result = {}
    for key, value in items:
        require(key not in result, 'duplicate JSON key: ' + key)
        result[key] = value
    return result


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def stamp(value):
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    require(result.tzinfo is not None, 'timestamp lacks timezone')
    return result


class Evidence:
    def __init__(self):
        self.files, self.rosters = {}, {}

    def raw(self, path):
        physical(path)
        before = path.stat()
        require(0 < before.st_size <= LIMIT, 'empty or oversized input: ' + str(path))
        with path.open('rb') as stream:
            raw = stream.read(LIMIT + 1)
        after = path.stat()
        require(len(raw) == before.st_size and all(getattr(before, key) == getattr(after, key)
            for key in ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns')),
            'input changed during read: ' + str(path))
        item = {'path': str(path), 'bytes': len(raw), 'sha256': sha(raw)}
        require(self.files.setdefault(str(path), item) == item,
                'input changed between reads: ' + str(path))
        quiet()
        return raw

    def load(self, path):
        return json.loads(self.raw(path), object_pairs_hook=pairs,
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError('nonfinite JSON: ' + value)))

    def maybe(self, path):
        return self.load(path) if os.path.lexists(path) else None

    def directory(self, path):
        physical(path, directory=True)
        names = sorted(item.name for item in path.iterdir())
        require(self.rosters.setdefault(str(path), names) == names,
                'directory roster changed: ' + str(path))
        return [path / name for name in names]

    def verify(self):
        for path in tuple(self.files):
            self.raw(Path(path))
        for path in tuple(self.rosters):
            self.directory(Path(path))


def junit(path, evidence):
    counts = Counter(tests=0, passed=0, failed=0, errors=0, skipped=0)
    cases = []
    if not os.path.lexists(path):
        return {'available': False, 'counts': dict(counts), 'cases': cases}
    root = ET.fromstring(evidence.raw(path))
    tag = lambda item: item.tag.rsplit('}', 1)[-1]
    for item in root.iter():
        if tag(item) != 'testcase':
            continue
        diagnostics = [{'kind': tag(child), 'message': child.get('message'),
                        'text': ''.join(child.itertext())}
                       for child in item if tag(child) in {'failure', 'error', 'skipped'}]
        kinds = {row['kind'] for row in diagnostics}
        status = ('errors' if 'error' in kinds else 'failed' if 'failure' in kinds
                  else 'skipped' if 'skipped' in kinds else 'passed')
        counts['tests'] += 1
        counts[status] += 1
        cases.append({'classname': item.get('classname'), 'name': item.get('name'),
                      'status': status, 'seconds_reported': item.get('time'),
                      'diagnostics': diagnostics})
    return {'available': True, 'counts': dict(counts), 'cases': cases,
        'count_policy': 'Each nested testcase once; error > failure > skipped > passed. '
                        'Suite totals are not added. Counts are invocation instances.'}


def deltas(before, after):
    result = {}
    for key in CPU:
        require(finite(before.get(key)) and finite(after.get(key)),
                'missing or nonfinite CPU/wall sample: ' + key)
        result[key] = after[key] - before[key]
        require(result[key] >= 0, 'negative CPU/wall delta: ' + key)
    return result


def validate_elapsed(before, after, recorded):
    actual = deltas(before, after)
    require(all(finite(recorded.get(key)) and math.isclose(actual[key], recorded[key],
            rel_tol=1e-9, abs_tol=1e-9) for key in CPU), 'elapsed disagrees with endpoints')


def measurement(path, evidence):
    value = evidence.load(path)
    require(type(value.get('pid')) is int
            and path.name == str(value['pid']) + '-measurement.json',
            'measurement PID/filename mismatch')
    require(value.get('worker', '').startswith('gw')
            and value.get('mode') in {'control', 'cprofile'}, 'missing worker/profile identity')
    calls = value['calls']
    require(type(calls) is list, 'call table is not an array')
    coarse, failures = [], []
    for index, row in enumerate(calls):
        if row.get('outcome') == 'open':
            failures.append('open_call_row:' + str(index))
        if 'coarse_before' in row:
            coarse.append({'call_index': index, **row})
            if 'coarse_after' in row:
                validate_elapsed(row['coarse_before'], row['coarse_after'], row['coarse_elapsed'])
            else:
                failures.append('unfinished_coarse_row:' + str(index))
    for phase in value['phases'] + value['pytest_phases']:
        validate_elapsed(phase['before'], phase['after'], phase['elapsed'])
    windows = value.get('observed_reservation_windows', [])
    require(type(windows) is list, 'reservation windows are not an array')
    public = value['node'] in PUBLIC
    preflight = []
    if public:
        successful = [(i, row) for i, row in enumerate(calls)
                      if row['label'] == 'attempt_mkdir' and row['outcome'] == 'return']
        if not successful or not windows:
            failures.append('public_successful_reservation_window_missing')
        if len(windows) != len(successful):
            failures.append('public_reservation_window_count_mismatch')
        for index, mkdir in successful:
            matched = [window for window in windows
                if window.get('attempt_path') == mkdir.get('attempt_path')
                and window.get('reservation_entry_utc') == mkdir.get('entered_utc')
                and window.get('reservation_return_utc') == mkdir.get('left_utc')]
            launches = [(i, row) for i, row in enumerate(calls)
                if row['label'] == 'public_launch' and row['outcome'] != 'open'
                and row['thread'] == mkdir['thread']
                and row['entered_wall'] <= mkdir['entered_wall']
                and mkdir['entered_wall'] + mkdir['inclusive_wall']
                    <= row['entered_wall'] + row['inclusive_wall']]
            if len(matched) != 1 or not launches:
                failures.append('public_reservation_pair_missing_or_ambiguous:' + str(index))
                continue
            # Innermost containing public launch; later spent-attempt refusals and
            # saved readbacks cannot match this successful mkdir interval.
            launch_index, launch = max(launches, key=lambda item: item[1]['entered_wall'])
            window = matched[0]
            accepted = [row for row in calls if row['label'] == 'accept_saved_capture'
                and row['outcome'] == 'return' and row['thread'] == mkdir['thread']
                and row.get('guard_accepted_at') == window.get('guard_accepted_at')
                and launch['entered_wall'] <= row['entered_wall']
                and row['entered_wall'] + row['inclusive_wall'] <= mkdir['entered_wall']]
            valid_window = len(accepted) == 1 and type(window.get('capture')) is dict
            if valid_window:
                try:
                    capture_seconds = (stamp(mkdir['entered_utc'])
                        - stamp(window['capture']['captured_at'])).total_seconds()
                    accepted_seconds = (stamp(mkdir['entered_utc'])
                        - stamp(window['guard_accepted_at'])).total_seconds()
                    valid_window = (accepted[0].get('capture') == window['capture']
                        and capture_seconds >= 0 and accepted_seconds >= 0
                        and all(finite(window.get(key)) and math.isclose(window[key], actual,
                            rel_tol=1e-9, abs_tol=1e-6) for key, actual in (
                            ('capture_to_reservation_wall_seconds', capture_seconds),
                            ('accepted_to_reservation_wall_seconds', accepted_seconds))))
                except (KeyError, TypeError, ValueError, AttributeError):
                    valid_window = False
            if not valid_window:
                failures.append('public_recorded_capture_window_invalid:' + str(index))
            if 'coarse_before' not in launch or 'coarse_before' not in mkdir:
                failures.append('public_preflight_samples_missing:' + str(index))
                continue
            preflight.append({'public_launch_call_index': launch_index,
                'successful_mkdir_call_index': index, 'thread': mkdir['thread'],
                'before': launch['coarse_before'], 'after': mkdir['coarse_before'],
                'elapsed': deltas(launch['coarse_before'], mkdir['coarse_before']),
                'recorded_window': window, 'recorded_window_valid': valid_window})
    return {'artifact': evidence.files[str(path)], 'node': value['node'], 'pid': value['pid'],
        'worker': value['worker'], 'mode': value['mode'], 'public': public,
        'coarse_calls': coarse, 'phases': value['phases'], 'pytest_phases': value['pytest_phases'],
        'observed_reservation_windows': windows, 'public_preflight': preflight,
        'measurement_passed': not failures, 'failures': failures, 'cpu_policy': CPU_POLICY}


def read_run(path, evidence):
    require(path.parent == BASE, 'run must be an immediate U3-K directory')
    physical(path, directory=True)
    # Read only the terminal supervisor witness before admitting other artifacts.
    outcome = evidence.load(path / 'outcome.json')
    require(type(outcome.get('returncode')) is int and finite(outcome.get('seconds'))
            and os.path.lexists(path / 'u3k-harness.json'),
            'run is not completed; refusing to inspect other artifacts: ' + str(path))
    harness = evidence.load(path / 'u3k-harness.json')  # written last by the K adapter
    plan = evidence.load(path / 'plan.json')
    stability = evidence.maybe(path / 'source-stability.json') or {}
    worker = evidence.maybe(path / 'worker-outcome.json') or outcome.get('worker') or {}
    xml = junit(path / 'pytest.xml', evidence)
    manifest_path = Path(harness['manifest'])
    require(manifest_path.parent.parent == BASE
            and manifest_path.name == 'composition.json', 'manifest outside U3-K')
    manifest = evidence.load(manifest_path)
    source = Path(manifest['worktree'])
    identity = (evidence.files[str(manifest_path)]['sha256'] == harness['manifest_sha256']
        and manifest['kind'] == 'native_u3k_private_composition'
        and manifest['status'] == 'composed_not_tested'
        and manifest_path.parent.name == 'composition-' + manifest['source_commit'][:12]
        and source == BASE / ('worktree-' + manifest['source_commit'][:12])
        and plan['source_root'] == harness['source_root'] == str(source)
        and plan['source_commit'] == harness['composition'] == manifest['composition_commit']
        and plan['runner_sha256'] == harness['sha256']
        and plan['environment']['U3K_MANIFEST'] == str(manifest_path)
        and plan['environment']['U3K_MANIFEST_SHA'] == harness['manifest_sha256']
        and manifest['packet_postimages_sha256'] == D127)
    physical(source, directory=True)
    packet = {}
    for name, expected in D127.items():
        packet[name] = sha(evidence.raw(source / name))
        identity = identity and packet[name] == expected
    origins = {name: evidence.maybe(path / name) for name in (
        'origins-before.json', 'origins-after.json', 'subprocess-origins.json')}
    command = evidence.maybe(path / 'pytest-command.json')
    dependencies = evidence.maybe(path / 'dependency-links.json')
    checks = {
        'pytest_completion': outcome['returncode'] in (0, 1),
        'worker_completion': worker.get('returncode') == outcome['returncode']
            and outcome.get('worker_returncode') == outcome['returncode'],
        'cleanup': outcome.get('cleanup_verified') is True
            and outcome.get('forced_cleanup') is False and outcome.get('interrupted') is None
            and outcome.get('observed_surviving_pids') == [] and outcome.get('observation_errors') == [],
        'source_identity': identity,
        'source_stability': stability.get('unchanged') is True
            and stability.get('before') == stability.get('after')
            and stability.get('before', {}).get('head') == manifest['composition_commit'],
        'source_origins': worker.get('source_origin_checks_passed') is True
            and all(item is not None for item in origins.values()),
        'command_and_dependencies': command is not None and dependencies is not None,
        'junit': xml['available'] and xml['counts']['tests'] > 0,
        'tests_passed': outcome['returncode'] == 0 and xml['counts']['failed'] == 0
            and xml['counts']['errors'] == 0,
        'bounded': finite(plan.get('deadline_seconds')) and 0 <= outcome['seconds'] < 3300,
    }
    measured = []
    metrics_dir = path / 'phase-metrics'
    if os.path.lexists(metrics_dir):
        for item in evidence.directory(metrics_dir):
            evidence.raw(item)  # retain identity of every metric, including raw pstats
            if item.name.endswith('-measurement.json'):
                measured.append(measurement(item, evidence))
    selected = sorted(node for node in PUBLIC if node in plan.get('command', [])
        or any(case['name'] == node.split('::')[1] for case in xml['cases']))
    public_rows = []
    for node in selected:
        cases = [case for case in xml['cases'] if case['name'] == node.split('::')[1]]
        rows = [row for row in measured if row['node'] == node]
        passed = (len(cases) == 1 and cases[0]['status'] == 'passed'
                  and len(rows) == 1 and rows[0]['measurement_passed'])
        public_rows.append({'node': node, 'passed': passed, 'junit_cases': cases,
                            'measurement_count': len(rows)})
    checks['public_nodes'] = all(row['passed'] for row in public_rows)
    checks['metrics'] = (all(row['measurement_passed'] for row in measured)
        and (plan['environment'].get('U3K_OBSERVE') != '1' or bool(measured)))
    failures = [name for name, passed in checks.items() if not passed]
    return {'path': str(path), 'checks': checks, 'failures': failures,
        'software_validation_passed': not failures, 'outcome': outcome, 'worker': worker,
        'source_stability': stability, 'harness': harness, 'manifest': manifest,
        'observed_packet_sha256': packet, 'plan': plan, 'junit': xml,
        'public_nodes': public_rows, 'measurements': measured}


def parity(runs, evidence):
    baseline = {}
    for folder, expected in (
        ('parity2-canary-baseline', {'generic.txt'}),
        ('parity2-rest-baseline', PARITY - {'generic.txt'}),
    ):
        paths = evidence.directory(BASE.parent / folder / 'parity')
        require({path.name for path in paths} == expected
                and not set(baseline).intersection(expected), 'baseline roster differs or overlaps')
        baseline.update({path.name: evidence.raw(path) for path in paths})
    require(set(baseline) == PARITY and len(baseline) == 14, 'baseline is not exactly 14')
    comparisons = []
    for run, expected in zip(runs, ({'generic.txt'}, PARITY)):
        paths = evidence.directory(run / 'parity')
        require({path.name for path in paths} == expected, 'candidate parity roster differs')
        rows = [{'name': path.name, 'raw_bytes_equal': evidence.raw(path) == baseline[path.name],
                 'candidate': evidence.files[str(path)]} for path in paths]
        comparisons.append({'run': str(run), 'passed': all(row['raw_bytes_equal'] for row in rows),
                            'files': rows})
    return {'comparisons': comparisons, 'passed': all(row['passed'] for row in comparisons),
        'expected_full_names': sorted(PARITY),
        'policy': 'Direct nonempty raw byte equality; disjoint frozen baseline 1+13 names. '
                  'The repeated candidate canary is not a fifteenth rendering.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, action='append', required=True)
    parser.add_argument('--parity-run', type=Path, nargs=2, metavar=('CANARY', 'FULL'))
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    quiet()
    physical(BASE, directory=True)
    require(len(set(args.run)) == len(args.run), 'duplicate --run')
    require(args.out.is_absolute() and args.out.parent == BASE and args.out.suffix == '.json'
            and not os.path.lexists(args.out), 'output must be a fresh JSON directly under U3-K')
    if args.parity_run:
        require(len(set(args.parity_run)) == 2 and set(args.parity_run) <= set(args.run),
                'parity requires two distinct explicitly supplied --run paths')
    evidence = Evidence()
    runs = [read_run(path, evidence) for path in args.run]
    comparison = parity(args.parity_run, evidence) if args.parity_run else None
    totals = Counter()
    for run in runs:
        totals.update(run['junit']['counts'])
    evidence.raw(Path(__file__).resolve())
    value = {'kind': 'native_u3k_validation_rollup', 'version': 1,
        'created_utc': datetime.now(timezone.utc).isoformat(), 'runs': runs,
        'supplied_invocation_totals': dict(totals), 'parity': comparison,
        'software_validation_passed': all(run['software_validation_passed'] for run in runs)
            and (comparison is None or comparison['passed']),
        'cpu_policy': CPU_POLICY, 'artifacts': list(evidence.files.values()),
        'directory_rosters': evidence.rosters,
        'scope': 'Only explicit completed supplied runs; no claim of complete cohort coverage. '
            'Failed public nodes and missing windows remain failures. No native, provider, '
            'account, scientific or quiet-host acceptance; no filesystem cleanup/census.'}
    evidence.verify()
    quiet()
    raw = (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()
    with args.out.open('xb') as stream:
        stream.write(raw)
    physical(args.out)
    require(args.out.read_bytes() == raw, 'summary did not persist exactly')
    print(json.dumps({'path': str(args.out), 'bytes': len(raw), 'sha256': sha(raw),
                      'software_validation_passed': value['software_validation_passed']}))


if __name__ == '__main__':
    main()

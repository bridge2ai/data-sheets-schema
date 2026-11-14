#!/usr/bin/env python3
"""U3-K retained control/profile comparison, 2026-11-09.

Inputs: exactly two completed run directories (--control, --profile).
Output: exclusive --out JSON under scratch-native-u1u3/u3k. Read-only inputs;
stdlib only, no imports of project code, subprocesses, network or raw pstats
deserialization. Hashes raw profiler files and reads their recorded JSON export.
This is diagnostic evidence, not native completion or a quiet-host benchmark.
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
import re

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT.parent / 'scratch-native-u1u3/u3k'
LOCK = ROOT.parent / 'plans/native_quiet_window.lock'
LIMIT = 128 * 1024 * 1024
D127 = {
    'src/data_sheets_schema/shared_generation.py': '2ec18e60316423035f88a2a30263c56385bfbbc587303e84e805a8349ab4f781',
    'src/data_sheets_schema/api_runner.py': '3e8b7e5d3cc13c5ebc508e33f865e9ac484056fde16126118719d740656a4fb7',
    'src/download/prompts/canonical_hashes.yaml': '543e5cd6dc0da0f622ba2cd11a16a90732e9302a1ed0a4700efb61971299d252',
    'tests/utils/run_spec_boundary_contracts.json': 'b1e0cbd14c533a51b88eacb84b974cb93963e18d8f1fb71ae4ed3228f784d1ce',
}
CPU_FIELDS = ('wall_monotonic', 'process_cpu', 'thread_cpu', 'self_user_cpu',
    'self_system_cpu', 'reaped_child_user_cpu', 'reaped_child_system_cpu')
H4 = ('U3K-H4: CPython cProfile.snapshot_stats keys entries by filename, first line '
      'and function name, overwriting distinct reloaded code objects with equal labels. '
      'Raw pstats and exported JSON preserve that limitation. Source-loaded rows cannot '
      'establish aggregate calls/times; no lost rows are reconstructed. Required expensive-step '
      'totals come from code-object monitoring. External-library rows are descriptive hotspots; '
      'nested inclusive/caller times are not additive.')


def quiet():
    if os.path.lexists(LOCK):
        raise RuntimeError('quiet-window lock active; summary stopped')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def physical(path, *, directory=False):
    require(path.is_absolute() and path.resolve(strict=True) == path and not path.is_symlink(),
            'expected physical absolute path: ' + str(path))
    require(path.is_dir() if directory else path.is_file(), 'wrong file kind: ' + str(path))
    return path


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def object_pairs(pairs):
    value = {}
    for key, item in pairs:
        require(key not in value, 'duplicate JSON key: ' + key)
        value[key] = item
    return value


def finite(value):
    return type(value) in (float, int) and math.isfinite(value)


def stamp(value):
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    require(result.tzinfo is not None, 'timestamp must be timezone-aware')
    return result


class Evidence:
    def __init__(self):
        self.files, self.directories = {}, {}

    def identity(self, path):
        quiet()
        physical(path)
        before = path.stat()
        value = hashlib.sha256()
        with path.open('rb') as stream:
            while block := stream.read(1024 * 1024):
                value.update(block)
        after = path.stat()
        require(all(getattr(before, key) == getattr(after, key)
            for key in ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns')),
            'input changed while hashing: ' + str(path))
        result = {'path': str(path), 'bytes': after.st_size, 'sha256': value.hexdigest()}
        require(self.files.setdefault(str(path), result) == result,
                'input changed between reads: ' + str(path))
        return result

    def raw(self, path):
        identity = self.identity(path)
        require(0 < identity['bytes'] <= LIMIT, 'empty or oversized JSON input: ' + str(path))
        raw = path.read_bytes()
        require(digest(raw) == identity['sha256'], 'input changed before parse: ' + str(path))
        return raw

    def load(self, path):
        value = json.loads(self.raw(path), object_pairs_hook=object_pairs,
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError('nonfinite JSON: ' + token)))
        return value

    def directory(self, path):
        physical(path, directory=True)
        names = sorted(item.name for item in path.iterdir())
        require(self.directories.setdefault(str(path), names) == names,
                'directory entries changed: ' + str(path))
        return [path / name for name in names]

    def declared(self, claim, parent, *, parse=False):
        require(type(claim) is dict and set(('path', 'bytes', 'sha256')) <= set(claim),
                'malformed declared artifact')
        path = Path(claim['path'])
        require(path.parent == parent, 'profile artifact is outside its metrics directory')
        identity = self.identity(path)
        require(identity['bytes'] > 0 and all(identity[key] == claim[key]
                for key in ('path', 'bytes', 'sha256')), 'declared artifact hash/size differs')
        return self.load(path) if parse else identity

    def verify(self):
        for path in tuple(self.files):
            self.identity(Path(path))
        for path in tuple(self.directories):
            self.directory(Path(path))


def elapsed(phase):
    before, after = phase['before'], phase['after']
    result = {}
    for key in CPU_FIELDS:
        require(finite(before.get(key)) and finite(after.get(key)), 'missing phase CPU/wall sample')
        value = after[key] - before[key]
        require(value >= 0 and finite(phase['elapsed'].get(key))
                and math.isclose(value, phase['elapsed'][key], rel_tol=1e-9, abs_tol=1e-9),
                'phase duration disagrees with its endpoints')
        result[key] = value
    require(stamp(after['utc']) >= stamp(before['utc']), 'phase UTC moved backwards')
    return result


def normalized_function(row, source):
    path = row['file']
    if type(path) is str and path.startswith(source + '/'):
        path = '<source>/' + path[len(source) + 1:]
    return (path, row['name'], row['first_line'], row['label'], row['outcome'])


def monitored_attribution(rows):
    result = []
    for label in sorted({row['label'] for row in rows}):
        group = [row for row in rows if row['label'] == label]
        done = [row for row in group if row['outcome'] != 'open']
        result.append({'label': label, 'calls': len(group), 'completed_calls': len(done),
            'open_calls': len(group) - len(done),
            'outcomes': dict(Counter(row['outcome'] for row in group)),
            'distinct_code_objects': len({row['code_object_id'] for row in group}),
            'completed_inclusive_thread_cpu': sum(row['inclusive_thread_cpu'] for row in done),
            'completed_inclusive_wall': sum(row['inclusive_wall'] for row in done),
            'complete': len(done) == len(group)})
    return {'labels': result,
        'authority': 'sys.monitoring retained code-object identities across source reloads',
        'policy': 'Within-label sums of completed call intervals only. Open rows have no invented '
            'duration. Inclusive intervals overlap across nested labels and may overlap within '
            'recursive calls; these are not exclusive phase CPU and must never be summed across '
            'labels. Thread CPU excludes other threads/children; wall includes scheduling.'}


def hotspots(phase, directory, evidence, source, selected):
    if not phase.get('profiled'):
        require('profile' not in phase and 'profile_json' not in phase,
                'unprofiled phase unexpectedly declares profiler output')
        return None
    raw_profile = evidence.declared(phase['profile'], directory)
    require(phase['profile'].get('timer') == 'time.thread_time_ns'
            and phase['profile'].get('timeunit') == 1e-9,
            'unexpected cProfile timer or time unit')
    functions = evidence.declared(phase['profile_json'], directory, parse=True)['functions']
    require(type(functions) is list and functions, 'profiler function table is empty')
    for row in functions:
        require(all(type(row.get(key)) is int and row[key] >= 0
                    for key in ('calls', 'primitive_calls')), 'invalid profiler call count')
        require(all(finite(row.get(key)) and row[key] >= 0
                    for key in ('self_thread_cpu', 'inclusive_thread_cpu')),
                'invalid profiler time')
        require(type(row.get('callers')) is list, 'missing profiler caller table')
        row['potentially_reload_collided'] = row['file'].startswith(str(source) + '/')
        matched = [call for call in selected if (call['file'], call['first_line'], call['name'])
                   == (row['file'], row['line'], row['name'])]
        row['observed_distinct_code_objects'] = len({call['code_object_id'] for call in matched})
        row['observed_reload_collision'] = row['observed_distinct_code_objects'] > 1
    ordering = lambda key: sorted(functions,
        key=lambda row: (-row[key], row['file'], row['line'], row['name']))[:30]
    return {'raw_profile': raw_profile,
        'function_export': evidence.files[phase['profile_json']['path']],
        'function_count': len(functions), 'top_exclusive': ordering('self_thread_cpu'),
        'top_inclusive': ordering('inclusive_thread_cpu'),
        'caveat': H4, 'counts_authority': 'phase monitored_attribution',
        'policy': 'Raw rankings only. An unobserved collision does not establish uniqueness because '
            'monitoring is selective. Inclusive/caller times overlap; no hotspot sum is computed.'}


def read_run(path, expected_mode, evidence):
    require(path.parent == BASE, 'run must be an immediate U3-K scratch directory')
    physical(path, directory=True)
    # A completed supervisor outcome is required: never summarize an active run.
    required = ('plan.json', 'outcome.json', 'source-stability.json', 'u3k-harness.json',
                'origins-before.json', 'origins-after.json', 'subprocess-origins.json',
                'pytest-command.json', 'dependency-links.json')
    loaded = {name: evidence.load(path / name) for name in required}
    optional = {}
    for name in ('worker-outcome.json', 'network.json', 'bootstrap.json'):
        if os.path.lexists(path / name):
            optional[name] = evidence.load(path / name)
    plan, outcome, harness = (loaded[name] for name in ('plan.json', 'outcome.json', 'u3k-harness.json'))
    require(type(plan.get('workers')) is int and plan['workers'] == 1,
            'profiling pair requires exactly one worker')
    require(plan['environment']['U3K_PROFILE'] == expected_mode,
            'run mode differs from its selected control/profile role')
    manifest_path = Path(harness['manifest'])
    require(manifest_path.is_relative_to(BASE), 'composition manifest outside U3-K scratch')
    manifest = evidence.load(manifest_path)
    require(evidence.files[str(manifest_path)]['sha256'] == harness['manifest_sha256']
            and plan['environment']['U3K_MANIFEST'] == str(manifest_path),
            'manifest hash/path differs from harness evidence')
    require(manifest['kind'] == 'native_u3k_private_composition'
            and manifest['status'] == 'composed_not_tested'
            and manifest['packet_postimages_sha256'] == D127,
            'source composition or approved packet identity differs')
    source = Path(manifest['worktree'])
    require(source == BASE / ('worktree-' + manifest['source_commit'][:12])
            and plan['source_root'] == str(source)
            and harness['source_root'] == str(source)
            and plan['source_commit'] == harness['composition'] == manifest['composition_commit'],
            'source identity joins differ')
    physical(source, directory=True)
    packet_files = {name: evidence.identity(source / name) for name in D127}
    require(all(packet_files[name]['sha256'] == wanted for name, wanted in D127.items()),
            'private composition packet bytes changed')
    config = manifest.get('private_config', {})
    config_state = {}
    if config:
        for key in ('path', 'backup'):
            target = Path(config[key])
            require(target.is_relative_to(manifest_path.parent), 'private config path escaped composition')
            config_state[key] = evidence.identity(target)
        require(config_state['backup']['sha256'] == config['original_sha256'],
                'private Git config backup changed')
        current = config_state['path']['sha256']
        config_state['state_at_summary'] = ('restored' if current == config['original_sha256']
            else 'configured' if current == config['configured_sha256'] else 'changed_unexpectedly')
    worker = optional.get('worker-outcome.json') or outcome.get('worker') or {}
    reasons = []
    checks = {
        'supervisor_completion': type(outcome.get('returncode')) is int and outcome['returncode'] in (0, 1),
        'worker_completion': worker.get('returncode') == outcome.get('returncode')
            and outcome.get('worker_returncode') == outcome.get('returncode'),
        'cleanup': outcome.get('cleanup_verified') is True and outcome.get('forced_cleanup') is False
            and outcome.get('interrupted') is None and outcome.get('observed_surviving_pids') == []
            and outcome.get('observation_errors') == [],
        'origins': worker.get('source_origin_checks_passed') is True,
        'stable_source': loaded['source-stability.json'].get('unchanged') is True,
        'bound': finite(outcome.get('seconds')) and outcome['seconds'] < 3300,
    }
    reasons.extend(key for key, passed in checks.items() if not passed)
    directory = path / 'phase-metrics'
    entries = evidence.directory(directory)
    # Hash every immediate metrics artifact, including raw pstats; never overwrite it.
    for entry in entries:
        require(evidence.identity(entry)['bytes'] > 0, 'empty metrics artifact')
    measurements = [entry for entry in entries if entry.name.endswith('-measurement.json')]
    require(len(measurements) == 1, 'exactly one worker measurement is required')
    measured = evidence.load(measurements[0])
    require(measured.get('mode') == expected_mode and measured.get('worker') == 'gw0',
            'measurement worker/mode differs')
    require(type(measured.get('pid')) is int and measurements[0].name == str(measured['pid']) + '-measurement.json',
            'measurement PID identity differs')
    diagnostic_path = directory / (str(measured['pid']) + '-diagnostic.json')
    diagnostic = evidence.load(diagnostic_path) if os.path.lexists(diagnostic_path) else None
    if diagnostic is None:
        reasons.append('diagnostic_result_missing')
    calls = measured['calls']
    require(type(calls) is list, 'calls must be an array')
    recomputed = Counter()
    for row in calls:
        require(type(row['outcome']) is str, 'call outcome missing')
        require(type(row.get('code_object_id')) is int
            and re.fullmatch('[0-9a-f]{64}', row.get('bytecode_sha256', '')) is not None,
            'missing code-object identity')
        recomputed[row['phase'] + ':' + row['label']] += 1
        if row['outcome'] != 'open':
            require(all(finite(row.get(key)) and row[key] >= 0
                for key in ('inclusive_wall', 'inclusive_thread_cpu')), 'call interval missing or invalid')
            require(stamp(row['left_utc']) >= stamp(row['entered_utc']), 'call UTC moved backwards')
    open_count = sum(row['outcome'] == 'open' for row in calls)
    require(measured['call_counts'] == dict(recomputed)
            and measured['open_call_rows'] == open_count, 'recorded call counts disagree')
    if open_count:
        reasons.append('unbalanced_monitored_calls')
    phase_rows, seen = [], set()
    for phase in measured['phases']:
        name = phase['name']
        require(name in {'fixture', 'launch'} and name not in seen, 'unexpected or duplicated diagnostic phase')
        seen.add(name)
        timing = elapsed(phase)
        start, stop = phase['first_call_row'], phase['last_call_row_exclusive']
        require(type(start) is int and type(stop) is int and 0 <= start <= stop <= len(calls),
                'invalid phase call slice')
        selected = calls[start:stop]
        require(all(row['phase'] == name for row in selected), 'phase slice includes another phase')
        require([index for index, row in enumerate(calls) if row['phase'] == name]
            == list(range(start, stop)), 'phase slice omits observations')
        roster = [normalized_function(row, str(source)) for row in selected]
        phase_rows.append({'name': name, 'outcome': phase['outcome'], 'error': phase['error'],
            'elapsed': timing, 'profiled': phase['profiled'],
            'boundaries': {'before': phase['before'], 'after': phase['after']},
            'call_counts': dict(Counter(row['label'] for row in selected)),
            'monitored_attribution': monitored_attribution(selected),
            'ordered_call_roster': roster, 'balanced': all(row['outcome'] != 'open' for row in selected),
            'profiler': hotspots(phase, directory, evidence, source, selected)})
    require(all(row['profiled'] == (expected_mode == 'cprofile') for row in phase_rows),
            'explicit diagnostic phase profiler selection differs from run mode')
    passive = [{'name': phase['name'], 'elapsed': elapsed(phase),
                'outcome': phase['outcome']} for phase in measured['pytest_phases']]
    return {'path': str(path), 'mode': expected_mode, 'qualification': {'passed': not reasons,
        'reasons': reasons, 'checks': checks, 'scope': 'Completed diagnostic provenance only; failure remains failure.'},
        'node': measured['node'], 'pid': measured['pid'], 'supervisor': outcome,
        'phase_measurement': evidence.files[str(measurements[0])],
        'phases': phase_rows, 'passive_pytest_phases': passive,
        'diagnostic': diagnostic, 'observed_reservation_windows': measured.get('observed_reservation_windows'),
        'identity': {'source_commit': manifest['source_commit'],
            'source_tree': manifest['source_tree'], 'composition_commit': manifest['composition_commit'],
            'composition_tree': manifest['composition_tree'], 'manifest': evidence.files[str(manifest_path)],
            'runner_sha256': plan['runner_sha256'], 'harness_sha256': harness['sha256'],
            'packet_postimages_sha256': manifest['packet_postimages_sha256'],
            'protected_preimages_sha256': manifest['protected_preimages_sha256'],
            'packet_files': packet_files, 'dependency_records': loaded['dependency-links.json'].get('installed_distribution_records'),
            'fairscape_dependency': plan.get('fairscape_dependency')},
        'setup': {'private_git_config': config_state, 'declared_file_write_scope': plan.get('file_write_scope'),
            'native_execution_policy': plan.get('native_execution_policy'),
            'dependency_links_artifact': evidence.files[str(path / 'dependency-links.json')],
            'bootstrap': optional.get('bootstrap.json'), 'network': optional.get('network.json'),
            'diagnostic_side_effect_claims': None if diagnostic is None else {
                key: diagnostic.get(key) for key in ('attempt_exists', 'evidence_exists', 'outcome')},
            'scope': 'Recorded setup artifacts and diagnostic side-effect claims; not an independent recursive filesystem census.'}}


def compare(control, profile):
    identity_keys = ('source_commit', 'source_tree', 'composition_commit', 'composition_tree',
        'manifest', 'runner_sha256', 'harness_sha256', 'packet_postimages_sha256',
        'dependency_records', 'fairscape_dependency')
    identity_match = all(control['identity'][key] == profile['identity'][key] for key in identity_keys)
    rows = []
    for name in ('fixture', 'launch'):
        left = next((row for row in control['phases'] if row['name'] == name), None)
        right = next((row for row in profile['phases'] if row['name'] == name), None)
        reasons = []
        if not identity_match:
            reasons.append('pair_recorded_source_dependency_identity_differs')
        if not control['qualification']['passed'] or not profile['qualification']['passed']:
            reasons.append('invocation_or_metrics_not_qualified')
        if control['node'] != profile['node']:
            reasons.append('diagnostic_node_differs')
        if left is None or right is None:
            reasons.append('phase_missing')
        elif not left['balanced'] or not right['balanced']:
            reasons.append('phase_has_open_observations')
        elif (left['outcome'], left['error'], left['ordered_call_roster']) != (
                right['outcome'], right['error'], right['ordered_call_roster']):
            reasons.append('phase_outcome_or_ordered_call_roster_differs')
        overhead = None
        if not reasons:
            overhead = {}
            for key in ('wall_monotonic', 'process_cpu', 'thread_cpu'):
                before, after = left['elapsed'][key], right['elapsed'][key]
                overhead[key] = {'control': before, 'profile': after, 'difference': after - before,
                    'profile_over_control_ratio': after / before if before > 0 else None,
                    'fractional_overhead': (after - before) / before if before > 0 else None}
        rows.append({'phase': name, 'comparable': not reasons, 'reasons': reasons, 'overhead': overhead,
            'control': left, 'profile': right})
    return {'same_recorded_source_dependency_identity': identity_match, 'phases': rows,
        'policy': 'Overhead only for equal phase names/outcomes/errors and ordered monitored call rosters with matching recorded source/runner/dependency identities. This is not a separate interpreter-binary or host-state pin. Earlier genuine refusals remain unmatched coverage. One serial pair is descriptive, not a repeated causal estimate.',
        'input_identity_limit': 'Same frozen neutral fixture-building code and profile, with separate generated per-run paths/identities; no claim that registration bytes are identical.',
        'cpu_policy': 'Process, thread, self and reaped-child CPU remain separate; passive pytest and explicit phases overlap; nested profiler inclusive times are never added.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--control', type=Path, required=True)
    parser.add_argument('--profile', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    quiet()
    physical(BASE, directory=True)
    require(args.control != args.profile, 'control and profile must be distinct runs')
    require(args.out.is_absolute() and args.out.parent == BASE and args.out.suffix == '.json'
        and not args.out.is_relative_to(args.control) and not args.out.is_relative_to(args.profile)
        and args.out.parent.resolve(strict=True) == args.out.parent
        and not os.path.lexists(args.out), 'output must be a fresh physical path outside both runs')
    evidence = Evidence()
    control, profile = (read_run(args.control, 'control', evidence),
                        read_run(args.profile, 'cprofile', evidence))
    value = {'kind': 'native_u3k_control_profile_summary', 'version': 1,
        'created_utc': datetime.now(timezone.utc).isoformat(),
        'control': control, 'profile': profile, 'comparison': compare(control, profile),
        'helper': evidence.identity(Path(__file__).resolve()),
        'artifacts': sorted(evidence.files.values(), key=lambda row: row['path']),
        'directory_rosters': evidence.directories,
        'historical_comparison_limit': 'U3-J2 public 427–450 s measurements included launch_case and its legacy sys.setprofile consumer observer. This diagnostic calls synthetic_launch directly and omits that observer; it is not an interchangeable rerun, subtraction or replacement of the old public timings.',
        'profiler_label_limitation': H4,
        'acceptance': 'Offline diagnostic only. No native execution, provider, account, scientific or quiet-host acceptance.'}
    evidence.verify()
    quiet()
    raw = (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()
    with args.out.open('xb') as stream:
        stream.write(raw)
    require(args.out.read_bytes() == raw, 'summary output did not persist exactly')
    print(json.dumps({'path': str(args.out), 'bytes': len(raw), 'sha256': digest(raw),
        'phase_comparability': [{'phase': row['phase'], 'comparable': row['comparable'],
            'reasons': row['reasons'], 'overhead': row['overhead']} for row in value['comparison']['phases']]},
        sort_keys=True))


if __name__ == '__main__':
    main()

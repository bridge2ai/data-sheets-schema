#!/usr/bin/env python3
"""Summarize retained native U3-J2 validation evidence, 2026-11-09.

Inputs: immediate run directories under scratch-native-u1u3/u3j2, their
outcome/JUnit/worker-metric artifacts, and private composition/cleanup manifests.
Output: one exclusive --out JSON in that scratch directory. Standard library
only; no tests, project imports, subprocesses, network or evidence modification.
Nested JUnit testcases are counted once. CPU scopes stay separate; unavailable
measurements remain null. This supports U3-J2 reporting, not native acceptance.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
EXEC = ROOT.parent
BASE = EXEC / 'scratch-native-u1u3/u3j2'
LOCK = EXEC / 'plans/native_quiet_window.lock'
MAX_READ_BYTES = 128 * 1024 * 1024
CPU_KEYS = ('wall_monotonic', 'process_cpu', 'self_user_cpu', 'self_system_cpu',
            'reaped_child_user_cpu', 'reaped_child_system_cpu')
PUBLIC_TESTS = {
    'test_actual_public_correction_three_workers_and_saved_completion',
    'test_actual_public_merged_omissions_and_all_chunk_statuses',
}
D127 = {
    'src/data_sheets_schema/shared_generation.py': '2ec18e60316423035f88a2a30263c56385bfbbc587303e84e805a8349ab4f781',
    'src/data_sheets_schema/api_runner.py': '3e8b7e5d3cc13c5ebc508e33f865e9ac484056fde16126118719d740656a4fb7',
    'src/download/prompts/canonical_hashes.yaml': '543e5cd6dc0da0f622ba2cd11a16a90732e9302a1ed0a4700efb61971299d252',
    'tests/utils/run_spec_boundary_contracts.json': 'b1e0cbd14c533a51b88eacb84b974cb93963e18d8f1fb71ae4ed3228f784d1ce',
}


def quiet():
    if os.path.lexists(LOCK):
        raise RuntimeError('quiet-window lock active; summary stopped')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def fingerprint(path):
    quiet()
    if path.is_symlink() or not path.is_file() or path.resolve(strict=True) != path:
        raise ValueError('summary input must be a regular physical file: ' + str(path))
    before = path.stat()
    value = hashlib.sha256()
    with path.open('rb') as stream:
        while block := stream.read(1024 * 1024):
            quiet()
            value.update(block)
    after = path.stat()
    keys = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
    if any(getattr(before, key) != getattr(after, key) for key in keys):
        raise ValueError('input changed during summary: ' + str(path))
    return {'path': str(path), 'bytes': after.st_size, 'sha256': value.hexdigest()}


class Evidence:
    def __init__(self):
        self.artifacts = {}

    def record(self, path):
        identity = fingerprint(path)
        old = self.artifacts.setdefault(str(path), identity)
        if old != identity:
            raise ValueError('input changed between reads: ' + str(path))
        return identity

    def raw(self, path):
        identity = self.record(path)
        if identity['bytes'] > MAX_READ_BYTES:
            raise ValueError('parser input exceeds 128 MiB: ' + str(path))
        raw = path.read_bytes()
        if sha(raw) != identity['sha256']:
            raise ValueError('input changed before parsing: ' + str(path))
        return raw

    def optional_json(self, path):
        if not os.path.lexists(path):
            return None
        return json.loads(self.raw(path))

    def verify(self):
        for path, identity in self.artifacts.items():
            if fingerprint(Path(path)) != identity:
                raise ValueError('input changed before summary publication: ' + path)


def tag(element):
    return element.tag.rsplit('}', 1)[-1]


def number(value):
    if type(value) in (int, float) and math.isfinite(value):
        return value
    return None


def xml_report(path, evidence):
    if not os.path.lexists(path):
        return {'available': False, 'counts': None, 'testcases': [],
                'diagnostic_event_counts': None, 'synthetic_diagnostic_testcase_count': None,
                'reason': 'pytest.xml missing'}
    root = ET.fromstring(evidence.raw(path))
    counts = Counter(tests=0, passed=0, failed=0, errors=0, skipped=0)
    events = Counter(failure=0, error=0, skipped=0)
    cases = []
    for item in root.iter():
        if tag(item) != 'testcase':
            continue
        children = [child for child in item if tag(child) in ('failure', 'error', 'skipped')]
        kinds = {tag(child) for child in children}
        status = ('errors' if 'error' in kinds else 'failed' if 'failure' in kinds
                  else 'skipped' if 'skipped' in kinds else 'passed')
        counts['tests'] += 1
        counts[status] += 1
        diagnostics = []
        for child in children:
            events[tag(child)] += 1
            text = ''.join(child.itertext())
            diagnostics.append({'kind': tag(child), 'message': child.get('message'),
                                'type': child.get('type'), 'trace': text,
                                'trace_utf8_sha256': sha(text.encode())})
        cases.append({'classname': item.get('classname'), 'name': item.get('name'),
                      'file': item.get('file'), 'line': item.get('line'),
                      'seconds_reported': item.get('time'), 'status': status,
                      'role': ('pytest_internal_diagnostic' if item.get('classname') == 'pytest'
                               and item.get('name') == 'internal' else 'testcase'),
                      'diagnostics': diagnostics})
    claims = [{key: item.get(key) for key in ('name', 'tests', 'failures', 'errors', 'skipped', 'time')}
              for item in root.iter() if tag(item) == 'testsuite']
    return {'available': True, 'counts': dict(counts), 'testcases': cases,
            'count_unit': 'testcase_instances_including_synthetic_pytest_diagnostic_cases',
            'diagnostic_event_counts': dict(events),
            'diagnostic_event_count_unit': 'individual_failure_error_or_skipped_XML_elements',
            'synthetic_diagnostic_testcase_count': sum(row['role'] == 'pytest_internal_diagnostic' for row in cases),
            'suite_claims_not_summed': claims,
            'count_basis': 'Each nested testcase once; error then failure then skip then pass. Suite totals are not added.'}


def phase_metrics(directory, evidence):
    groups = defaultdict(list)
    artifacts = []
    if directory.exists():
        if directory.is_symlink():
            raise ValueError('phase-metrics directory is an alias')
        for path in sorted(directory.glob('*.jsonl')):
            raw = evidence.raw(path)
            artifacts.append(str(path))
            for line, encoded in enumerate(raw.splitlines(), 1):
                if not encoded.strip():
                    continue
                row = json.loads(encoded)
                if type(row) is not dict or not all(key in row for key in ('node', 'worker', 'pid', 'phase', 'event')):
                    raise ValueError('malformed phase metric at ' + str(path) + ':' + str(line))
                groups[(row['node'], row['worker'], row['pid'])].append(dict(row, evidence_line=line, evidence_path=str(path)))
    workers, controller_reports = [], []
    for (node, worker, pid), rows in sorted(groups.items()):
        begins = [row for row in rows if row['event'] == 'begin']
        ends = [row for row in rows if row['event'] == 'end']
        if not begins and not ends:
            controller_reports.append({'node': node, 'worker': worker, 'pid': pid,
                                       'reports': [row for row in rows if row['event'] == 'report'],
                                       'cpu_measurement': None,
                                       'reason': 'report-only process; not test-execution CPU'})
            continue
        phases = []
        for phase in dict.fromkeys(row['phase'] for row in rows):
            selected = [row for row in rows if row['phase'] == phase]
            phases.append({'phase': phase, 'begin_count': sum(row['event'] == 'begin' for row in selected),
                           'end_count': sum(row['event'] == 'end' for row in selected),
                           'elapsed_observations': [row.get('elapsed') for row in selected if row['event'] == 'end'],
                           'outcomes': [row.get('outcome') for row in selected if row['event'] == 'report'],
                           'events': selected})
        span = None
        if begins and ends:
            # These endpoints share both PID and worker. Reaped-child CPU stays
            # a separate field and is never added to own/controller CPU.
            first, last = begins[0].get('sample', {}), ends[-1].get('sample', {})
            span = {key: (last[key] - first[key] if number(first.get(key)) is not None
                          and number(last.get(key)) is not None else None) for key in CPU_KEYS}
        complete = (len(begins) == len(ends)
                    and all(row['begin_count'] == row['end_count'] for row in phases))
        workers.append({'node': node, 'worker': worker, 'pid': pid, 'phases': phases,
                        'observed_node_span': span, 'phase_intervals_balanced': complete,
                        'measurement_scope': 'Same worker PID, first observed begin through last observed end; '
                            'includes intervening pytest reporting. Missing endpoints stay null; '
                            'partial spans are not whole-test totals. Reaped child CPU excludes unreaped children.'})
    return {'artifacts': artifacts, 'workers': workers, 'report_only_processes': controller_reports,
            'aggregate_cpu': None, 'aggregation_policy': 'Never sum controller and worker CPU or own and reaped-child CPU.'}


def basetemp_from(command):
    if type(command) is not dict or type(command.get('args')) is not list:
        return None
    args = command['args']
    for index, value in enumerate(args):
        if value == '--basetemp' and index + 1 < len(args):
            return Path(args[index + 1])
        if type(value) is str and value.startswith('--basetemp='):
            return Path(value.split('=', 1)[1])
    return None


def public_details(run, xml, command, metrics, evidence):
    selected = [row for row in xml['testcases']
                if row.get('name') in PUBLIC_TESTS or str(row.get('name', '')).startswith('test_actual_public_')]
    if not selected and not run.name.startswith(('public-correction-', 'public-omissions-')):
        return None
    basetemp = basetemp_from(command)
    searched = False
    markers = []
    aliases = []
    if basetemp is not None and basetemp.exists():
        if not basetemp.is_relative_to(run) or basetemp.resolve() != basetemp or basetemp.is_symlink():
            raise ValueError('public basetemp is not its physical run-owned tree')
        for parent, directories, _ in os.walk(basetemp, followlinks=False):
            quiet()
            aliases.extend(str(Path(parent) / name) for name in directories if (Path(parent) / name).is_symlink())
        # Ignore-independent filesystem discovery; no Git or ripgrep defaults.
        for path in sorted(basetemp.rglob('started.json')):
            if path.is_symlink():
                markers.append({'path': str(path), 'kind': 'symlink', 'sha256': None})
            elif path.is_file():
                markers.append(evidence.record(path))
            else:
                markers.append({'path': str(path), 'kind': 'nonregular', 'sha256': None})
        searched = True
    text = '\n'.join((item.get('message') or '') + '\n' + item['trace']
                     for row in selected for item in row['diagnostics'])
    stale = 'subscription observation is stale or future-dated' in text
    phase = ('pre-reservation subscription freshness refusal'
             if searched and not markers and stale else 'not established by this summary')
    return {'nodes': selected, 'expected_attempt_limit_seconds': 900, 'expected_helper_limit_seconds': 180,
            'limits_basis': 'Required U3-J2 software-test limits; these constants are not observed timeout measurements.',
            'basetemp': str(basetemp) if basetemp is not None else None,
            'started_marker_search_performed': searched, 'started_markers': markers,
            'no_started_marker_in_literal_basetemp': not markers if searched else None,
            'symlink_directories_not_followed': aliases,
            'marker_search_scope': 'Ignore-independent rglob of literal basetemp; no claim about external symlink targets or arbitrary reservation directories.',
            'observed_stale_subscription_refusal': stale, 'failure_phase_inference': phase,
            'failure_phase_basis': 'Exact saved exception plus absence of started.json; no attempted execution is inferred from elapsed time.',
            'deadline_stop_phase': None,
            'deadline_stop_reason': 'No separate deadline-stop measurement is synthesized from a failure or duration.',
            'worker_measurements': metrics['workers']}


def qualification(loaded, xml):
    """Keep partial/internal-error observations out of completed-run totals.

    Qualification is only of this software-test invocation's provenance and
    completion. Exit 1 can be qualified failed tests; no pass/acceptance follows.
    Missing witnesses are unknown and therefore unqualified, never assumed true.
    """
    outcome = loaded['outcome.json'] or {}
    worker = loaded['worker-outcome.json'] or outcome.get('worker') or {}
    stability = loaded['source-stability.json'] or {}
    reasons = []
    status = outcome.get('returncode')
    worker_status = worker.get('returncode')
    if loaded['outcome.json'] is None:
        reasons.append('supervisor_outcome_missing')
    if not xml['available']:
        reasons.append('junit_missing')
    if type(status) is not int or status not in (0, 1):
        reasons.append('pytest_invocation_not_completed_with_exit_0_or_1')
    if status == 3 or xml.get('synthetic_diagnostic_testcase_count', 0):
        reasons.append('pytest_internal_error_diagnostic')
    if type(worker_status) is not int or worker_status != status:
        reasons.append('worker_exit_missing_or_disagrees_with_supervisor')
    if outcome.get('worker_returncode') != worker_status:
        reasons.append('supervisor_worker_exit_missing_or_disagrees')
    if outcome.get('interrupted') is not None:
        reasons.append('supervisor_interrupted')
    if outcome.get('forced_cleanup') is not False:
        reasons.append('forced_cleanup_or_missing_cleanup_mode')
    if outcome.get('cleanup_verified') is not True:
        reasons.append('cleanup_not_verified')
    if outcome.get('observed_surviving_pids') != []:
        reasons.append('observed_survivors_or_missing_survivor_witness')
    if outcome.get('observation_errors') != []:
        reasons.append('process_observation_errors_or_missing_witness')
    if worker.get('source_origin_checks_passed') is not True:
        reasons.append('source_origin_checks_not_verified')
    if stability.get('unchanged') is not True:
        reasons.append('source_stability_not_verified')
    for name in ('origins-before.json', 'origins-after.json', 'subprocess-origins.json', 'u3j2-harness.json'):
        if loaded[name] is None:
            reasons.append('missing_' + name)
    counts = xml['counts']
    if counts is not None:
        if status == 0 and counts['failed'] + counts['errors']:
            reasons.append('zero_exit_contradicts_failed_or_error_testcases')
        if status == 1 and not counts['failed'] + counts['errors']:
            reasons.append('failed_exit_has_no_failed_or_error_testcase')
    return {'qualified': not reasons,
            'status': 'qualified_completed_test_invocation' if not reasons else 'unqualified_partial_or_invalid_invocation',
            'reasons': reasons, 'pytest_exitcode': status, 'worker_exitcode': worker_status,
            'scope': 'Invocation provenance and pytest completion only; qualified failures remain failures, and this is not native acceptance.'}


def summarize_run(run, evidence):
    loaded = {}
    names = ('outcome.json', 'plan.json', 'worker-outcome.json', 'pytest-command.json',
             'u3j2-harness.json', 'source-stability.json', 'origins-before.json',
             'origins-after.json', 'subprocess-origins.json', 'network.json')
    for name in names:
        loaded[name] = evidence.optional_json(run / name)
    # Hash every immediate evidence file (including log/sandbox/checkpoint files)
    # without descending into venvs, cases, or archived repositories.
    artifacts = []
    for path in sorted(run.iterdir()):
        if path.is_file() and not path.is_symlink():
            artifacts.append(evidence.record(path))
    outcome = loaded['outcome.json'] or {}
    plan = loaded['plan.json'] or {}
    worker = loaded['worker-outcome.json'] or outcome.get('worker') or {}
    xml = xml_report(run / 'pytest.xml', evidence)
    metrics = phase_metrics(run / 'phase-metrics', evidence)
    return {'name': run.name, 'path': str(run), 'outcome_present': loaded['outcome.json'] is not None,
            'qualification': qualification(loaded, xml),
            'supervisor': {key: outcome.get(key) for key in (
                'returncode', 'seconds', 'worker_returncode', 'cleanup_verified', 'cleanup_scope',
                'forced_cleanup', 'interrupted', 'observed_surviving_pids', 'observation_errors')},
            'invocation_limit_seconds': plan.get('deadline_seconds'), 'workers_requested': plan.get('workers'),
            'source_commit': plan.get('source_commit'), 'source_root': plan.get('source_root'),
            'source_origin_checks_passed': worker.get('source_origin_checks_passed'),
            'source_stability': loaded['source-stability.json'], 'harness': loaded['u3j2-harness.json'],
            'origin_evidence': {name: evidence.artifacts.get(str(run / name)) for name in (
                'origins-before.json', 'origins-after.json', 'subprocess-origins.json')},
            'junit': xml, 'metrics': metrics,
            'public': public_details(run, xml, loaded['pytest-command.json'], metrics, evidence),
            'immediate_artifacts': artifacts}


def summarize_composition(directory, evidence):
    manifest = evidence.optional_json(directory / 'composition.json')
    cleanup = evidence.optional_json(directory / 'config-restored.json')
    if manifest is None:
        return None
    actual = {}
    worktree = Path(manifest['worktree']) if manifest.get('worktree') else None
    if worktree is not None:
        if not worktree.is_relative_to(BASE):
            raise ValueError('composition worktree is outside U3-J2 scratch')
        for path in D127:
            target = worktree / path
            actual[path] = evidence.record(target) if os.path.lexists(target) else None
    config = manifest.get('private_config') or {}
    config_artifacts = {}
    for name in ('path', 'backup'):
        if config.get(name):
            target = Path(config[name])
            if not target.is_relative_to(directory):
                raise ValueError('private config evidence lies outside its composition')
            config_artifacts[name] = evidence.record(target) if os.path.lexists(target) else None
    return {'manifest': evidence.artifacts[str(directory / 'composition.json')],
            'source_commit': manifest.get('source_commit'), 'source_tree': manifest.get('source_tree'),
            'composition_commit': manifest.get('composition_commit'), 'composition_tree': manifest.get('composition_tree'),
            'status': manifest.get('status'), 'worktree': manifest.get('worktree'),
            'approved_postimages_sha256': D127, 'recorded_postimages_sha256': manifest.get('packet_postimages_sha256'),
            'recorded_postimages_equal_d127': manifest.get('packet_postimages_sha256') == D127,
            'observed_worktree_postimages': actual,
            'observed_postimages_equal_d127': bool(actual) and all(actual[path] is not None
                and actual[path]['sha256'] == digest for path, digest in D127.items()),
            'private_config': config, 'config_artifacts': config_artifacts, 'cleanup': cleanup,
            'cleanup_manifest': evidence.artifacts.get(str(directory / 'config-restored.json'))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True, help='Exclusive physical JSON path under U3-J2 scratch')
    args = parser.parse_args()
    quiet()
    if BASE.resolve(strict=True) != BASE or ROOT.name != 'codex-native-u1u3':
        raise ValueError('assigned physical checkout and scratch root required')
    if (not args.out.is_absolute() or not args.out.is_relative_to(BASE)
            or args.out.parent.resolve(strict=True) != args.out.parent or os.path.lexists(args.out)):
        raise ValueError('--out must be a fresh physical path under U3-J2 scratch')
    evidence = Evidence()
    runs, compositions = [], []
    for path in sorted(BASE.iterdir()):
        quiet()
        if path.is_symlink() or not path.is_dir():
            continue
        if path.name.startswith('composition-'):
            value = summarize_composition(path, evidence)
            if value is not None:
                compositions.append(value)
        elif not path.name.startswith('worktree-') and any(os.path.lexists(path / name)
                for name in ('outcome.json', 'pytest.xml', 'phase-metrics')):
            runs.append(summarize_run(path, evidence))
    totals = Counter(tests=0, passed=0, failed=0, errors=0, skipped=0)
    qualified = Counter(tests=0, passed=0, failed=0, errors=0, skipped=0)
    invalid = Counter(tests=0, passed=0, failed=0, errors=0, skipped=0)
    for run in runs:
        if run['junit']['counts'] is not None:
            totals.update(run['junit']['counts'])
            (qualified if run['qualification']['qualified'] else invalid).update(run['junit']['counts'])
    payload = {'kind': 'native_u3j2_retained_validation_summary', 'version': 1,
               'created_utc': datetime.now(timezone.utc).isoformat(), 'input_root': str(BASE),
               'helper': fingerprint(Path(__file__).resolve()), 'runs': runs, 'compositions': compositions,
               'invocation_testcase_totals': dict(totals),
               'qualified_invocation_testcase_totals': dict(qualified),
               'unqualified_invocation_testcase_totals': dict(invalid),
               'totals_scope': 'Raw observed testcase instances across retained invocations, including synthetic diagnostic cases; repeated nodes are not unique coverage. Qualified and unqualified totals are separate. Missing XML is not a zero-test pass.',
               'incomplete_or_invalid_runs': [run['name'] for run in runs if not run['qualification']['qualified']],
               'missing_result_artifact_runs': [run['name'] for run in runs if not run['outcome_present'] or not run['junit']['available']],
               'artifacts': sorted(evidence.artifacts.values(), key=lambda row: row['path']),
               'artifact_scope': 'All consumed artifacts and immediate run evidence files; not a recursive hash of cases, dependencies or archives.',
               'cpu_policy': 'No cross-process CPU sum. Per-PID process CPU, self user/system, and reaped-child CPU remain separate.',
               'acceptance': 'Evidence summary only; no native execution, provider, quiet-host or acceptance claim.'}
    evidence.verify()
    quiet()
    raw = (json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()
    with args.out.open('xb') as stream:
        stream.write(raw)
    if args.out.read_bytes() != raw:
        raise ValueError('summary output did not persist exactly')
    print(json.dumps({'path': str(args.out), 'bytes': len(raw), 'sha256': sha(raw)}, sort_keys=True))


if __name__ == '__main__':
    main()

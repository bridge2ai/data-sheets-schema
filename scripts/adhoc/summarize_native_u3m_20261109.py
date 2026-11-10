#!/usr/bin/env python3
"""Report retained U3-M evidence, 2026-11-09; no tests or execution changes.

Inputs: repeated --run completed M directories, --partial uncertified M
directories, optional --parity LEFT RIGHT directories, and a fresh --out JSON.
Output: exact supplied-run counts, artifact identities/missing states, timing
evidence and raw parity. Standard library only; no subprocess, source edits,
archive, provider, native executable, environment mutation or cleanup.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT.parent / 'scratch-native-u1u3/u3m'
SOURCE = '672bcdb4586876e1e8932a8a2f1b59edee28aaab'
MAIN = '2cfc4666c2d81003d9cf5f432248b4217ef477e1'
HELPER = ROOT / 'scripts/adhoc/summarize_native_u3k_validation_20261109.py'
spec = importlib.util.spec_from_file_location('u3m_retained_report_reader', HELPER)
k = importlib.util.module_from_spec(spec)
spec.loader.exec_module(k)
POST = dict(k.D127, **{'src/data_sheets_schema/api_runner.py':
    '830eec1e12e96f807fa76ea26e066a1923b60380013c424cfa99f0012af0a881'})
MAIN_BYTES = {
    'src/data_sheets_schema/shared_generation.py': '94b3cf6845827c8fdf7bf05cc6251e2fb196ceb91ea8ce377f2c9e3b8be3773d',
    'src/data_sheets_schema/api_runner.py': '23dcc828d171000173bd521edfbc55b38bfcf6c0adb41c6b962c10f381e911bb',
    'src/download/prompts/canonical_hashes.yaml': '39b93c009457681a1d8d8b8afee5a869bbd6f5e70b6f4332522db5d7e22d0584',
    'tests/utils/run_spec_boundary_contracts.json': 'a7f96a253a37e994f0c62c7d9b2ab21b0a94d4f342975f84103cd274ef11af72',
}
OVERLAYS = {
    'scripts/adhoc/u3m_parity_plugin_20261109.py': 'fd04be9e3186146d0b4ba791728593ef5cabd960697d73da0d9178b57252d155',
    'tests/test_native_u1_api_parity.py': 'de0ca02326e90e426cfff9495cfa98824cf39d1e2d66d9442a431c910cb9f193',
}
ARTIFACTS = ('outcome.json', 'worker-outcome.json', 'u3m-harness.json', 'plan.json',
    'source-stability.json', 'origins-before.json', 'origins-after.json',
    'subprocess-origins.json', 'pytest-command.json', 'dependency-links.json',
    'bootstrap.json', 'network.json', 'network-denied.sb', 'pytest.xml', 'pytest.log',
    'early-cutoff.json', 'u3g-cutoff.json', 'host-load.json', 'dependency-write-denied.json')


class Evidence(k.Evidence):
    """Keep K's bounded JSON reader; additionally witness empty/missing files."""
    def __init__(self):
        super().__init__()
        self.states, self.parse_errors = {}, {}

    def inspect(self, path):
        k.quiet()
        k.require(path.is_absolute() and path.parent.resolve(strict=True) == path.parent,
                  'artifact parent must be physical: ' + str(path))
        if not os.path.lexists(path):
            row = dict(path=str(path), state='missing')
        else:
            before = path.lstat()
            k.require(stat.S_ISREG(before.st_mode) and path.resolve(strict=True) == path,
                      'artifact must be a physical regular file: ' + str(path))
            digest = hashlib.sha256()
            with path.open('rb') as stream:
                while block := stream.read(1024 * 1024):
                    digest.update(block)
            after = path.stat()
            k.require(all(getattr(before, key) == getattr(after, key) for key in
                ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns')),
                'artifact changed while hashing: ' + str(path))
            identity = dict(path=str(path), bytes=after.st_size, sha256=digest.hexdigest())
            k.require(self.files.setdefault(str(path), identity) == identity,
                      'artifact changed between reads: ' + str(path))
            row = dict(identity, state='present' if after.st_size else 'empty')
        k.require(self.states.setdefault(str(path), row) == row,
                  'artifact presence/content changed: ' + str(path))
        return row

    def optional(self, path):
        if self.inspect(path)['state'] != 'present':
            return None
        try:
            return self.load(path)
        except (ValueError, UnicodeError) as exc:
            self.parse_errors[str(path)] = type(exc).__name__ + ': ' + str(exc)
            return None

    def verify(self):
        for path in tuple(self.files) + tuple(self.states):
            self.inspect(Path(path))
        for path in tuple(self.rosters):
            self.directory(Path(path))


def classify(partial, checks):
    return 'partial_uncertified' if partial else (
        'complete_verified' if all(checks.values()) else 'complete_unverified')


def origin_matches(value, source, run):
    package = source / 'src/data_sheets_schema'
    return (type(value) is dict and value.get('package_paths') == [str(package)]
        and value.get('prefix') == str(run / 'venv') and value.get('editable_finders') == []
        and all(value.get(key) is True for key in ('no_user_site', 'safe_path', 'dont_write_bytecode'))
        and type(value.get('module_origins')) is dict
        and all(Path(path).is_relative_to(package) for path in value['module_origins'].values()))


def subprocess_origin_matches(value, source, run):
    return (type(value) is dict and set(value) == {'network', 'origins'}
        and type(value['network']) is dict
        and value['network'].get('network_bind_denied') is True
        and origin_matches(value['origins'], source, run))


def check_origin_envelopes():
    """Invented in-memory controls only; no filesystem or process operation."""
    source, run = Path('/u3m-control/source'), Path('/u3m-control/run')
    package = source / 'src/data_sheets_schema'
    origins = dict(package_paths=[str(package)], prefix=str(run / 'venv'),
        editable_finders=[], no_user_site=True, safe_path=True, dont_write_bytecode=True,
        module_origins={'data_sheets_schema.control': str(package / 'control.py')})
    envelope = dict(network={'network_bind_denied': True}, origins=origins)
    k.require(subprocess_origin_matches(envelope, source, run), 'valid subprocess envelope refused')
    invalid = [origins, dict(envelope, network={'network_bind_denied': False}),
        dict(envelope, origins=dict(origins, package_paths=['/foreign'])),
        dict(envelope, origins=dict(origins, module_origins={'foreign': '/foreign/module.py'}))]
    invalid.extend(dict(envelope, origins=dict(origins, **{flag: False}))
        for flag in ('no_user_site', 'safe_path', 'dont_write_bytecode'))
    k.require(all(not subprocess_origin_matches(value, source, run) for value in invalid),
              'invalid subprocess envelope admitted')


def source_identity(plan, harness, evidence):
    env = plan.get('environment', {})
    path = Path(env.get('U3M_MANIFEST', '/unrecorded-manifest'))
    allowed = {BASE / (prefix + SOURCE[:12]) / 'composition.json'
               for prefix in ('composition-', 'baseline-parity-')}
    k.require(path in allowed, 'manifest is not the measured U3-M source')
    manifest = evidence.load(path)
    baseline = manifest.get('kind') == 'native_u3m_parity_baseline_overlay'
    kind = 'native_u3m_parity_baseline_overlay' if baseline else 'native_u3m_private_composition'
    expected_commit = ('268662e53d8212a30128b5a82299d54156b03efa' if baseline else
                       'e1134dedd76d818cdb6f3cdf6b3e4437defb26ed')
    source = BASE / (('baseline-parity-worktree-' if baseline else 'worktree-') + SOURCE[:12])
    k.physical(source, directory=True)
    expected = MAIN_BYTES if baseline else POST
    pins = {name: k.sha(evidence.raw(source / name)) for name in expected}
    identity = (manifest.get('kind') == kind and manifest.get('source_commit') == SOURCE
        and manifest.get('status') == 'composed_not_tested'
        and manifest.get('composition_commit') == expected_commit
        and manifest.get('worktree') == str(source)
        and manifest.get('private_git') == str(path.parent / 'tree/.git')
        and plan.get('source_root') == str(source) and plan.get('source_commit') == expected_commit
        and env.get('U3M_MANIFEST_SHA') == evidence.files[str(path)]['sha256']
        and pins == expected)
    if baseline:
        overlay = {name: k.sha(evidence.raw(source / name)) for name in OVERLAYS}
        nodes = [x for x in plan.get('command', []) if x.startswith('tests/')]
        identity = (identity and manifest.get('baseline_commit') == MAIN
            and manifest.get('composition_parent') == MAIN
            and manifest.get('protected_source_sha256') == MAIN_BYTES
            and manifest.get('test_only_additions_sha256') == overlay == OVERLAYS
            and sorted(manifest.get('exact_delta_from_baseline', [])) == sorted(OVERLAYS)
            and bool(nodes) and all(x.split('::')[0] == 'tests/test_native_u1_api_parity.py' for x in nodes)
            and env.get('U3F_PARITY') == '1')
    else:
        identity = identity and manifest.get('packet_postimages_sha256') == POST
    if harness is not None:
        runner = ROOT / 'scripts/adhoc/run_native_u3m_20261109.py'
        identity = (identity and harness.get('commit') == SOURCE
            and harness.get('source_root') == str(source) and harness.get('composition') == expected_commit
            and harness.get('manifest') == str(path)
            and harness.get('manifest_sha256') == evidence.files[str(path)]['sha256']
            and harness.get('path') == str(runner)
            and harness.get('sha256') == plan.get('runner_sha256') == k.sha(evidence.raw(runner)))
    return dict(valid=bool(identity), baseline=baseline, manifest=str(path),
        manifest_sha256=evidence.files[str(path)]['sha256'], source_root=str(source),
        composition_commit=expected_commit, measured_source_commit=SOURCE,
        observed_protected_sha256=pins,
        scope='Recorded composition identity and current four pinned files; no fresh Git tree census.')


def read_run(path, partial, evidence):
    k.require(path.is_absolute() and path.parent == BASE, 'run must be an immediate M directory')
    k.physical(path, directory=True)
    members = evidence.directory(path)  # Includes hidden/ignored entries; no Git-filtered census.
    states = {name: evidence.inspect(path / name) for name in ARTIFACTS}
    parsed = {name: evidence.optional(path / name) for name in ARTIFACTS if name.endswith('.json')}
    outcome, worker, plan, harness, stability = (parsed[name] or {} for name in
        ('outcome.json', 'worker-outcome.json', 'plan.json', 'u3m-harness.json', 'source-stability.json'))
    xml = dict(available=False, counts=dict(tests=0, passed=0, failed=0, errors=0, skipped=0), cases=[])
    if states['pytest.xml']['state'] == 'present':
        try:
            xml = k.junit(path / 'pytest.xml', evidence)
        except (ValueError, k.ET.ParseError) as exc:
            evidence.parse_errors[str(path / 'pytest.xml')] = type(exc).__name__ + ': ' + str(exc)
    identity, identity_error = None, None
    if plan:
        try:
            identity = source_identity(plan, harness or None, evidence)
        except (ValueError, KeyError, OSError) as exc:
            identity_error = type(exc).__name__ + ': ' + str(exc)
    source = Path(identity['source_root']) if identity else BASE
    before, after = stability.get('before', {}), stability.get('after', {})
    checks = dict(
        terminal_outcome=type(outcome.get('returncode')) is int and outcome['returncode'] in (0, 1),
        worker_completion=type(worker.get('returncode')) is int
            and worker['returncode'] == outcome.get('returncode') == outcome.get('worker_returncode'),
        cleanup=outcome.get('cleanup_verified') is True and outcome.get('forced_cleanup') is False
            and outcome.get('interrupted') is None and outcome.get('observed_surviving_pids') == []
            and outcome.get('observation_errors') == [],
        source_identity=identity is not None and identity['valid'] and bool(harness),
        source_stability=stability.get('unchanged') is True and before == after
            and before.get('status') == '' and identity is not None
            and before.get('head') == identity['composition_commit'],
        source_origins=worker.get('source_origin_checks_passed') is True and all(
            origin_matches(parsed[name], source, path) for name in
            ('origins-before.json', 'origins-after.json'))
            and subprocess_origin_matches(parsed['subprocess-origins.json'], source, path),
        junit=xml['available'] and xml['counts']['tests'] > 0,
        bounded=k.finite(outcome.get('seconds')) and 0 <= outcome['seconds'] < 3300
            and k.finite(plan.get('deadline_seconds')) and 0 < plan['deadline_seconds'] < 3300,
        command_and_dependencies=parsed['pytest-command.json'] is not None
            and parsed['dependency-links.json'] is not None)
    measured, diagnostics, metric_errors = [], [], []
    metrics = path / 'phase-metrics'
    metrics_state = 'missing'
    if os.path.lexists(metrics):
        entries = evidence.directory(metrics)
        metrics_state = 'present' if entries else 'empty_directory'
        for item in entries:
            state = evidence.inspect(item)
            if state['state'] != 'present':
                metric_errors.append(dict(path=str(item), state=state['state']))
                continue
            try:
                if item.name.endswith('-measurement.json'):
                    measured.append(k.measurement(item, evidence))
                elif item.name.endswith('-diagnostic.json'):
                    diagnostics.append(evidence.load(item))
            except (ValueError, KeyError, TypeError) as exc:
                metric_errors.append(dict(path=str(item), error=type(exc).__name__ + ': ' + str(exc)))
    observed = plan.get('environment', {}).get('U3K_OBSERVE') == '1'
    checks['metric_artifacts'] = not metric_errors and (not observed or bool(measured))
    status = classify(partial, checks)
    k.require(partial or status == 'complete_verified',
              'complete run lacks terminal certification; declare --partial: ' + str(path)
              + ' ' + repr([key for key, ok in checks.items() if not ok]))
    return dict(path=str(path), classification=status, completion_certified=not partial,
        checks=checks, identity=identity, identity_error=identity_error,
        immediate_members=[item.name for item in members], artifact_states=states,
        outcome=outcome or None, worker=worker or None, junit=xml,
        metrics_directory_state=metrics_state, measurements=measured,
        diagnostics=diagnostics, metric_errors=metric_errors,
        measurement_result_available=bool(measured or diagnostics),
        no_measurement_policy='Absent/empty metrics establish no CPU, reservation or freshness result.',
        software_validation_passed=(not partial and outcome.get('returncode') == 0
            and xml['counts']['failed'] == xml['counts']['errors'] == 0
            and all(row['measurement_passed'] for row in measured)))


def parity(left, right, runs, evidence):
    selected = {Path(row['path']): row for row in runs}
    k.require(left.name == right.name == 'parity' and left.parent != right.parent
        and left.parent in selected and right.parent in selected
        and selected[left.parent]['identity']['baseline'] is True
        and selected[right.parent]['identity']['baseline'] is False,
        'parity requires distinct complete fixed-main and candidate run directories')
    rosters = [[p.name for p in evidence.directory(root)] for root in (left, right)]
    rows = []
    for name in sorted(k.PARITY):
        a, b = evidence.inspect(left / name), evidence.inspect(right / name)
        same = (a['state'] == b['state'] == 'present'
                and evidence.raw(left / name) == evidence.raw(right / name))
        rows.append(dict(name=name, baseline=a, candidate=b, raw_bytes_equal=same))
    return dict(baseline=str(left), candidate=str(right), rosters=rosters, files=rows,
        expected_names=sorted(k.PARITY),
        passed=all(set(roster) == k.PARITY for roster in rosters)
            and all(row['raw_bytes_equal'] for row in rows),
        scope='Direct nonempty raw bytes at all fourteen exact names; no normalization or old K outputs.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, action='append', default=[])
    parser.add_argument('--partial', type=Path, action='append', default=[])
    parser.add_argument('--parity', type=Path, nargs=2, metavar=('LEFT', 'RIGHT'))
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    k.quiet()
    supplied = args.run + args.partial
    k.require(supplied and len(set(supplied)) == len(supplied), 'unique supplied run directories required')
    k.physical(BASE, directory=True)
    k.require(args.out.is_absolute() and args.out.parent == BASE and args.out.suffix == '.json'
        and not os.path.lexists(args.out), 'fresh JSON directly under M required')
    # In-memory classification controls; never create or execute test fixtures.
    k.require(classify(True, {'gate': True}) == 'partial_uncertified'
        and classify(False, {'gate': False}) == 'complete_unverified'
        and classify(False, {'gate': True}) == 'complete_verified', 'classification control failed')
    check_origin_envelopes()
    evidence = Evidence()
    base_members = evidence.directory(BASE)
    complete = [read_run(path, False, evidence) for path in args.run]
    partial = [read_run(path, True, evidence) for path in args.partial]
    paired = parity(*args.parity, complete, evidence) if args.parity else None
    totals, observed_partial = Counter(), Counter()
    for run in complete:
        totals.update(run['junit']['counts'])
    for run in partial:
        if run['junit']['available']:
            observed_partial.update(run['junit']['counts'])
    markers = [evidence.inspect(BASE / (name + '.once.json'))
               for name in ('public-correction', 'public-omissions')]
    evidence.inspect(Path(__file__).resolve())
    evidence.inspect(HELPER)
    evidence.verify()
    value = dict(kind='native_u3m_supplied_evidence_rollup', version=1,
        created_utc=datetime.now(timezone.utc).isoformat(), measured_source_commit=SOURCE,
        complete_runs=complete, partial_runs=partial,
        certified_invocation_totals=dict(totals),
        partial_observed_xml_totals=dict(observed_partial), parity=paired,
        public_once_markers=markers, base_immediate_members_before_output=[p.name for p in base_members],
        directory_rosters=evidence.rosters, artifact_identities=list(evidence.files.values()),
        artifact_states=list(evidence.states.values()), parse_errors=evidence.parse_errors,
        software_validation_passed=not partial and all(row['software_validation_passed'] for row in complete)
            and (paired is None or paired['passed']), cpu_policy=k.CPU_POLICY,
        owner_api_postimage_approval='pending_not_covered_by_D127',
        scope='Only explicitly supplied runs. Partial XML counts are observed, never certified; missing/empty artifacts '
              'are not zero findings. Immediate physical directory membership includes hidden/ignored entries. '
              'No recursive source/dependency census, complete-cohort, native, scientific or quiet-host acceptance claim.')
    raw = (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()
    k.quiet()
    with args.out.open('xb') as stream:
        stream.write(raw)
    k.require(args.out.read_bytes() == raw, 'report did not persist exactly')
    print(json.dumps(dict(path=str(args.out), bytes=len(raw), sha256=k.sha(raw),
        certified_invocation_totals=dict(totals), partial_run_count=len(partial),
        software_validation_passed=value['software_validation_passed'])))


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Read-only WP1 contended CPU diagnostic arm assembler and comparator, 2026-11-10.

Inputs: two completed physical cpu-legacy and cpu-monitoring artifact directories
and a fresh output JSON path. Outputs: one new comparison JSON assembled from the
recorded outer, supervisor, harness, measurement and diagnostic artifacts via
compare_cpu_diagnostic_arms. Performs no test execution or runtime host sampling.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MAX_JSON_BYTES = 64 * 1024 * 1024


def _file_identity(path):
    path = Path(path)
    if not path.is_absolute() or path.is_symlink() or path != path.resolve(strict=True) or not path.is_file():
        raise ValueError('physical absolute file required: ' + str(path))
    raw = path.read_bytes()
    if not (0 < len(raw) <= MAX_JSON_BYTES):
        raise ValueError('empty or oversized file: ' + str(path))
    return raw, {
        'path': str(path),
        'bytes': len(raw),
        'sha256': hashlib.sha256(raw).hexdigest(),
    }


def _load_validator():
    path = ROOT / 'scripts/adhoc/native_wp1_validation_20261110.py'
    _, meta = _file_identity(path)
    spec = importlib.util.spec_from_file_location('native_wp1_validation', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, meta


def _unique_object_pairs(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError('duplicate JSON key: ' + key)
        value[key] = item
    return value


def _read_json_file(path):
    raw, meta = _file_identity(path)
    value = json.loads(
        raw,
        object_pairs_hook=_unique_object_pairs,
        parse_constant=lambda token: (_ for _ in ()).throw(ValueError('nonfinite JSON constant: ' + token)),
    )
    if not isinstance(value, dict):
        raise ValueError('JSON object required: ' + str(path))
    return value, meta


def _select_single_metrics_pair(metrics_dir):
    if (not metrics_dir.is_absolute() or metrics_dir.is_symlink()
            or metrics_dir != metrics_dir.resolve(strict=True) or not metrics_dir.is_dir()):
        raise ValueError('physical phase-metrics directory required: ' + str(metrics_dir))
    measurements = sorted(metrics_dir.glob('*-measurement.json'))
    diagnostics = sorted(metrics_dir.glob('*-diagnostic.json'))
    if len(measurements) != 1 or len(diagnostics) != 1:
        raise ValueError('exactly one measurement and one diagnostic file required in ' + str(metrics_dir))
    measurement_path = measurements[0]
    diagnostic_path = diagnostics[0]
    if set(metrics_dir.iterdir()) != {measurement_path, diagnostic_path}:
        raise ValueError('unexpected extra files in phase-metrics directory: ' + str(metrics_dir))
    measurement, measurement_meta = _read_json_file(measurement_path)
    diagnostic, diagnostic_meta = _read_json_file(diagnostic_path)
    pid = measurement.get('pid')
    if (type(pid) is not int or pid <= 1
            or measurement_path.name != f'{pid}-measurement.json'
            or diagnostic_path.name != f'{pid}-diagnostic.json'):
        raise ValueError('measurement and diagnostic files must share the recorded integer worker pid')
    return measurement, measurement_meta, diagnostic, diagnostic_meta


def load_cpu_diagnostic_arm(arm_dir, expected_kind, *, validator=None):
    """Read and verify one saved cpu-legacy or cpu-monitoring artifact directory."""
    if validator is None:
        validator, _ = _load_validator()
    if expected_kind not in validator.CPU_DIAGNOSTIC_KINDS:
        raise ValueError('expected cpu-legacy or cpu-monitoring kind, got ' + repr(expected_kind))
    expected_node, expected_arm, _ = validator.KINDS[expected_kind]
    arm_dir = Path(arm_dir)
    if (not arm_dir.is_absolute() or arm_dir.is_symlink()
            or arm_dir != arm_dir.resolve(strict=True) or not arm_dir.is_dir()):
        raise ValueError('physical absolute arm directory required: ' + str(arm_dir))
    outer, outer_meta = _read_json_file(arm_dir.with_suffix('.outer.json'))
    supervisor, supervisor_meta = _read_json_file(arm_dir.with_suffix('.supervisor.json'))
    harness, harness_meta = _read_json_file(arm_dir / 'wp1-harness.json')
    measurement, measurement_meta, diagnostic, diagnostic_meta = _select_single_metrics_pair(
        arm_dir / 'phase-metrics'
    )
    files = {
        'outer': outer_meta,
        'supervisor': supervisor_meta,
        'harness': harness_meta,
        'measurement': measurement_meta,
        'diagnostic': diagnostic_meta,
    }
    outcome_path = arm_dir / 'outcome.json'
    if os.path.lexists(outcome_path):
        outcome, outcome_meta = _read_json_file(outcome_path)
        if outcome.get('cleanup_verified') is not True or outcome.get('returncode') != 0:
            raise ValueError('recorded outcome.json cleanup or returncode failed: ' + str(outcome_path))
        files['outcome'] = outcome_meta

    for record_name, record in (('outer', outer), ('supervisor', supervisor), ('harness', harness)):
        if (record.get('kind') != expected_kind
                or record.get('measurement_class') != 'unqualified_contended_cpu_diagnostic'
                or record.get('host_qualified') is not False
                or record.get('wall_time_freshness_qualified') is not False
                or record.get('accepted_quiet_host_timing') is not False):
            raise ValueError(f'{record_name} lacks unqualified classification for {expected_kind}')
    if (outer.get('arm') != expected_arm or harness.get('arm') != expected_arm
            or outer.get('node') != expected_node or harness.get('node') != expected_node
            or measurement.get('node') != expected_node or measurement.get('mode') != 'control'
            or harness.get('metrics_profile') != 'control'
            or diagnostic.get('wp1_kind') != expected_kind
            or diagnostic.get('consumer_observer_arm') != expected_arm
            or diagnostic.get('measurement_class') != 'unqualified_contended_cpu_diagnostic'
            or diagnostic.get('host_qualified') is not False
            or diagnostic.get('wall_time_freshness_qualified') is not False
            or diagnostic.get('accepted_quiet_host_timing') is not False
            or diagnostic.get('metrics_profile_mode') != 'control'):
        raise ValueError('recorded arm, node or control metrics mode mismatch in ' + str(arm_dir))
    if (not isinstance(outer.get('manifest'), str) or not outer['manifest'].strip()
            or outer.get('manifest') != supervisor.get('manifest')
            or outer.get('manifest') != harness.get('manifest')
            or outer.get('manifest_sha256') != supervisor.get('manifest_sha256')
            or outer.get('manifest_sha256') != harness.get('manifest_sha256')
            or outer.get('source_commit') != harness.get('source_commit')):
        raise ValueError('outer, supervisor and harness identity fields disagree in ' + str(arm_dir))
    if (outer.get('quiet_lease') is not None
            or supervisor.get('qualification') is not None
            or supervisor.get('quiet_lease_release') is not None):
        raise ValueError('CPU diagnostic arm cannot carry quiet-lease or qualification records')
    handoff = supervisor.get('sandbox_handoff')
    if (outer.get('returncode') != 0 or outer.get('child_returncode') != 0
            or outer.get('timed_out') is not False or outer.get('interrupted') is not None
            or outer.get('cleanup_verified') is not True or outer.get('forced_cleanup') is not False
            or outer.get('observer_joined') is not True
            or outer.get('observed_surviving_pids') != []
            or outer.get('post_observer_cleanup_pids') != []
            or outer.get('observation_errors') != []
            or supervisor.get('returncode') != 0
            or supervisor.get('cleanup_verified') is not True
            or supervisor.get('forced_cleanup') is not False
            or supervisor.get('interrupted') is not None
            or supervisor.get('errors') != []
            or supervisor.get('cleanup_errors') != []
            or supervisor.get('lock_release_cleanup_verified') is not True
            or not isinstance(handoff, dict)
            or handoff.get('admitted') is not True
            or handoff.get('errors') != []
            or handoff.get('observed_surviving_pids') != []
            or harness.get('source_unchanged') is not True
            or diagnostic.get('attempt_exists') is not False
            or diagnostic.get('evidence_exists') is not False
            or diagnostic.get('profile_hook_restored') is not True
            or diagnostic.get('open_call_rows') != 0
            or diagnostic.get('open_thread_stacks') != 0
            or measurement.get('open_call_rows') != 0):
        raise ValueError('unverified cleanup or incomplete execution in ' + str(arm_dir))

    assembled = {
        **outer,
        'qualification': supervisor.get('qualification'),
        'supervisor': supervisor,
        'harness': harness,
        'interpreter': harness.get('interpreter'),
        'measurement': measurement,
        'diagnostic': diagnostic,
        'artifact_directory': str(arm_dir),
        'input_files': files,
    }
    if not validator._valid_arm_identity(assembled):
        raise ValueError('invalid recorded manifest, source commit or interpreter identity in ' + str(arm_dir))
    return assembled


def compare_saved_cpu_diagnostic_dirs(legacy_dir, monitoring_dir, out_path=None):
    """Assemble both saved CPU diagnostic arm directories, verify pair identity/cleanup, and compare."""
    validator, validator_meta = _load_validator()
    _, helper_meta = _file_identity(Path(__file__).resolve())
    legacy_path = Path(legacy_dir)
    monitoring_path = Path(monitoring_dir)
    legacy_arm = load_cpu_diagnostic_arm(legacy_path, 'cpu-legacy', validator=validator)
    monitoring_arm = load_cpu_diagnostic_arm(monitoring_path, 'cpu-monitoring', validator=validator)
    if legacy_path == monitoring_path:
        raise ValueError('cpu-legacy and cpu-monitoring directories must be distinct')
    for key in ('manifest', 'manifest_sha256', 'source_commit',
                'composition_manifest', 'composition_manifest_sha256',
                'implementation_sha256', 'interpreter'):
        if legacy_arm['harness'].get(key) != monitoring_arm['harness'].get(key):
            raise ValueError('recorded pair identity differs on ' + key)
    comparison = validator.compare_cpu_diagnostic_arms(legacy_arm, monitoring_arm)
    if not comparison.get('same_identity') or not comparison.get('arms_clean'):
        raise ValueError('CPU diagnostic arms failed comparator identity or cleanup verification')
    for arm_files in (legacy_arm['input_files'], monitoring_arm['input_files']):
        for meta in arm_files.values():
            if _file_identity(meta['path'])[1] != meta:
                raise ValueError('input artifact changed during comparison: ' + meta['path'])
    result = {
        **comparison,
        'source_commit': legacy_arm['source_commit'],
        'manifest': legacy_arm['harness'].get('manifest'),
        'manifest_sha256': legacy_arm['manifest_sha256'],
        'composition_manifest': legacy_arm['harness'].get('composition_manifest'),
        'composition_manifest_sha256': legacy_arm['harness'].get('composition_manifest_sha256'),
        'interpreter': dict(legacy_arm['interpreter']),
        'helper': helper_meta,
        'validator_helper': validator_meta,
        'input_arms': {
            'legacy': {
                'kind': 'cpu-legacy',
                'arm': 'legacy',
                'artifact_directory': legacy_arm['artifact_directory'],
                'worker_pid': legacy_arm['measurement']['pid'],
                'cleanup_verified': True,
                'returncode': 0,
                'files': legacy_arm['input_files'],
            },
            'monitoring': {
                'kind': 'cpu-monitoring',
                'arm': 'monitoring',
                'artifact_directory': monitoring_arm['artifact_directory'],
                'worker_pid': monitoring_arm['measurement']['pid'],
                'cleanup_verified': True,
                'returncode': 0,
                'files': monitoring_arm['input_files'],
            },
        },
    }
    if out_path is not None:
        target = Path(out_path)
        if (not target.is_absolute() or target.suffix != '.json'
                or os.path.lexists(target)
                or not target.parent.is_dir() or target.parent.is_symlink()
                or target.parent != target.parent.resolve(strict=True)
                or target.is_relative_to(legacy_path)
                or target.is_relative_to(monitoring_path)):
            raise ValueError('new physical external .json output path required: ' + str(target))
        validator.write_new(target, result)
    return result


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--legacy-out', '--cpu-legacy-out', '--legacy',
                        dest='legacy_out', type=Path, required=True,
                        help='Physical directory for the completed cpu-legacy arm')
    parser.add_argument('--monitoring-out', '--cpu-monitoring-out', '--monitoring',
                        dest='monitoring_out', type=Path, required=True,
                        help='Physical directory for the completed cpu-monitoring arm')
    parser.add_argument('--out', type=Path, required=True,
                        help='New physical .json path for the comparison artifact')
    return parser.parse_args()


def main():
    args = arguments()
    validator, _ = _load_validator()
    if os.path.lexists(validator.QUIET_LOCK) or 'U3WP1_LEASE_FD' in os.environ:
        raise ValueError('quiet-window lock or lease is active')
    compare_saved_cpu_diagnostic_dirs(args.legacy_out, args.monitoring_out, args.out)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

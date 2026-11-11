#!/usr/bin/env python3
"""Prepare bounded component evidence for #5867, 2026-11-11.

Inputs: one fixed selection, this checkout and existing dependency Python.
Outputs: fresh external sandbox/log/JUnit/deadline/capture-cleanup evidence.
Reuses the unchanged subprocess_deadline helper; no composition or new supervisor.
10s work plus 20s existing cleanup reserve: <=30s acceptance, not a hard alarm.
Every invocation requires its own release; canary never starts affected groups.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT.parent / 'scratch-native-postaccept-fusion-v2-20261111'
# #5869: fixed Git entry, selected target and approved Apple selector helper.
# Dependency allowance, not a claim that all three have been observed executing.
GIT_EXECUTABLES = ('/usr/bin/git', '/Library/Developer/CommandLineTools/usr/bin/git',
                   '/usr/bin/xcrun')
RESERVATION = 'tests/test_native_u4b_a3_reservation.py'
CAPTURES = 'tests/test_native_u4b_a3_captures.py'
# (module, function, expected parameterized cases); no caller-supplied node IDs.
SELECTIONS = {
    'canary': [(RESERVATION, 'test_deferred_capture_acceptance_exact_order_to_real_reservation', 1)],
    'values': [(RESERVATION, 'test_fused_lease_compares_original_current_and_fresh_execution', 3),
               (RESERVATION, 'test_fused_lease_refuses_engine_mutation_during_authorization_read', 1)],
    'inputs': [(RESERVATION, 'test_fused_lease_uses_actual_shared_input_checks', 3)],
    'direct': [(RESERVATION, 'test_registered_90_second_margin_permits_first_real_reservation_only', 1),
               (RESERVATION, 'test_registered_89_second_margin_refuses_before_any_attempt_directory', 1),
               (RESERVATION, 'test_source_recapture_time_is_charged_before_measuring_reservation_margin', 2)],
    'margin': [(RESERVATION, 'test_fused_lease_charges_controls_before_margin', 2)],
    'admission': [(RESERVATION, 'test_admission_changes_after_initial_join_refuse_before_attempt_reservation', 2),
                  (RESERVATION, 'test_deferred_capture_late_load_refuses_admission_mutation', 2)],
    'lease': [(CAPTURES, 'test_admission_lease_excludes_word_renewal_during_reservation', 1)],
}
PEER_COUNTS = {'canary': 1, 'values': 4, 'inputs': 3, 'direct': 4,
               'margin': 2, 'admission': 6, 'lease': 0}
PINNED = (RESERVATION, CAPTURES, 'tests/test_native_subscription_capture.py',
    'tests/test_native_u4b_runtime.py', 'tests/conftest.py', 'tests/utils/subprocess_deadline.py',
    'src/data_sheets_schema/native_execution_orchestration.py',
    'src/data_sheets_schema/native_shared_execution_orchestration.py',
    'src/data_sheets_schema/native_subscription_capture.py',
    'src/data_sheets_schema/native_capture_words.py',
    'scripts/adhoc/run_postaccept_fusion_checks_20261111.py')


def read(path, limit=4 * 1024 * 1024):
    if path.is_symlink() or not path.is_file():
        raise ValueError('regular evidence file required: ' + str(path))
    with path.open('rb') as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise ValueError('evidence exceeds bound: ' + str(path))
    return raw


def main():
    began = time.monotonic()
    if len(sys.argv) != 2 or sys.argv[1] not in SELECTIONS:
        raise ValueError('one fixed selection required')
    mode = sys.argv[1]
    if not (sys.flags.no_site and sys.flags.safe_path and sys.dont_write_bytecode):
        raise ValueError('existing dependency Python -S -P -B required')
    if os.path.lexists(ROOT.parent / 'plans/native_quiet_window.lock'):
        raise ValueError('quiet window occupied')
    identity = {name: hashlib.sha256(read(ROOT / name)).hexdigest() for name in PINNED}
    if mode != 'canary':
        prior = json.loads(read(BASE / 'canary/result.json'))
        if prior.get('passed') is not True or prior.get('selected_file_sha256') != identity:
            raise ValueError('same-source certified singleton canary required')
    out = BASE / mode
    out.mkdir(parents=True, exist_ok=False)
    for name in ('home', 'tmp'):
        (out / name).mkdir()
    dependency = Path(sys.executable).absolute().parent.parent / 'lib/python3.13/site-packages'
    if not dependency.is_dir() or dependency.resolve() != dependency:
        raise ValueError('existing physical dependency site required')
    profile = out / 'offline.sb'
    # Only this Python, fixed local Git paths and the ordinary-Python fixture may exec.
    # The canonical Python target is included for interpreter symlink resolution.
    permitted = sorted({str(Path(sys.executable).absolute()), str(Path(sys.executable).resolve()),
                        *GIT_EXECUTABLES})
    peer_pattern = '^' + re.escape(str(out / 'cases')) + '/[^/]+/durable-copy$'
    profile.write_text('(version 1)\n(allow default)\n(deny network*)\n'
        '(deny process-exec (require-all ' + ' '.join(
            '(require-not (literal ' + json.dumps(path) + '))' for path in permitted)
        + ' (require-not (regex #' + json.dumps(peer_pattern) + '))))\n'
        '(deny file-write* (require-all (require-not (subpath ' + json.dumps(str(out)) + '))'
        ' (require-not (literal "/dev/null")) (require-not (literal "/dev/tty"))))\n')
    env = dict(PATH='/usr/bin:/bin:/usr/sbin:/sbin', HOME=str(out / 'home'), TMPDIR=str(out / 'tmp'),
        PYTHONPATH=os.pathsep.join(map(str, (ROOT, ROOT / 'src', dependency))),
        PYTEST_DISABLE_PLUGIN_AUTOLOAD='1', PYTEST_ADDOPTS='', PYTHONDONTWRITEBYTECODE='1',
        PYTHONNOUSERSITE='1', PYTHONSAFEPATH='1', PYTHONPYCACHEPREFIX=str(out / 'unused-pycache'),
        GIT_CONFIG_GLOBAL='/dev/null', GIT_CONFIG_SYSTEM='/dev/null', GIT_NO_LAZY_FETCH='1',
        GIT_ALLOW_PROTOCOL='', UV_OFFLINE='1', PIP_NO_INDEX='1')
    spec = importlib.util.spec_from_file_location('fusion_deadline', ROOT / 'tests/utils/subprocess_deadline.py')
    guard = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = guard
    spec.loader.exec_module(guard)
    command = ['/usr/bin/sandbox-exec', '-f', str(profile), sys.executable, '-S', '-P', '-B',
        '-m', 'pytest', '-q', '-o', 'addopts=', '-p', 'no:cacheprovider',
        '--basetemp', str(out / 'cases'), '--junitxml', str(out / 'pytest.xml'),
        *[module + '::' + name for module, name, _ in SELECTIONS[mode]]]
    plan = dict(command=command, environment=env, selected_file_sha256=identity,
        work_seconds=10, cleanup_reserve_seconds=20, acceptance_seconds=30,
        scope='Acceptance budget only; unchanged process-group supervisor, no new hard alarm.')
    (out / 'plan.json').write_text(json.dumps(plan, indent=2) + '\n')
    remaining = 10 - (time.monotonic() - began)
    if remaining <= 0:
        raise ValueError('setup exhausted work budget; no child started')
    with (out / 'pytest.log').open('xb') as stream:
        result = guard.run(command, cwd=ROOT, env=env, evidence=out / 'deadline',
                           stream=stream, seconds=remaining)
    deadline = json.loads(read(out / 'deadline/deadline.json'))
    root = ET.fromstring(read(out / 'pytest.xml')) if (out / 'pytest.xml').is_file() else ET.Element('missing')
    cases = list(root.iter('testcase'))
    identities = [(case.get('classname'), case.get('name')) for case in cases]
    expected_count = sum(count for _, _, count in SELECTIONS[mode])
    exact_cases = len(cases) == expected_count and len(set(identities)) == len(cases)
    for module, name, count in SELECTIONS[mode]:
        classname = module[:-3].replace('/', '.')
        matched = [case for case in cases if case.get('classname') == classname and
                   (case.get('name') == name or case.get('name', '').startswith(name + '['))]
        exact_cases = exact_cases and len(matched) == count
    peers = []
    for path in sorted((out / 'cases').rglob('capture.json')):
        captured = json.loads(read(path))
        lifecycle = captured.get('lifecycle')
        expected_lifecycle = {'spawn_count': 1, 'returncode': 0,
            'cleanup': {'child_started': True, 'leader_reaped': True, 'group_absent': True}}
        valid = captured.get('kind') == 'd4d_native_subscription_capture_v1' and lifecycle == expected_lifecycle
        for name in ('stdout.jsonl', 'stderr.txt', 'observations.json'):
            raw = read(path.parent / name)
            pin = captured.get('files', {}).get(name, {})
            valid = valid and pin == {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
            if name != 'stderr.txt':
                valid = valid and bool(raw)
        valid = valid and bool(read(path.parent / 'claim.json'))
        peers.append(dict(path=str(path), lifecycle=lifecycle, status=captured.get('status'), verified=valid))
    failed = sum(peer['status'] == 'failed' for peer in peers)
    peer_checks = (len(peers) == PEER_COUNTS[mode] and all(peer['verified'] for peer in peers)
                   and failed == (2 if mode == 'admission' else 0)
                   and all(peer['status'] in ('captured', 'failed') for peer in peers))
    elapsed = time.monotonic() - began
    passed = (result.returncode == 0 and not result.expired and elapsed <= 30 and exact_cases
        and not any(list(root.iter(tag)) for tag in ('failure', 'error', 'skipped'))
        and deadline.get('returncode') == 0 and deadline.get('expired') is False
        and deadline.get('termination_verified') is True and deadline.get('signals') == [] and peer_checks)
    (out / 'result.json').write_text(json.dumps(dict(passed=passed, selection=mode,
        selected_file_sha256=identity, tests=len(cases), exact_cases=exact_cases,
        elapsed_seconds=elapsed, acceptance_seconds=30, returncode=result.returncode,
        expired=result.expired, peer_checks=peer_checks, peers=peers,
        scope='Isolated registration components; no genuine producer/native/freshness proof. '
              'Supervisor covers its group; peer cleanup relies separately on retained capture lifecycle.'),
        indent=2) + '\n')
    raise SystemExit(0 if passed else 1)


if __name__ == '__main__':
    main()

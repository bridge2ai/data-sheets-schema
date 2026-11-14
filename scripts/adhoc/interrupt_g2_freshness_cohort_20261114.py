#!/usr/bin/env python3
"""Review-gated SIGINT for the failed G2 engine cohort, 2026-11-14.

Inputs: exact final-engine-dependents command and the six owned process/start
identities observed read-only on 2026-11-14; exec session 45479. Outputs:
exclusive scratch-g2-20261114/final-engine-freshness-interruption evidence,
including before/after command, log, JUnit and outcome snapshots. The cohort
has three failure markers; traceback and cause remain unconfirmed. Serves the
G2 integration review; no new issue identity or freshness cause is asserted.
Adapted from interrupt_g2_publication_oracle_cohort_20261114.py, unchanged.
--inspect is read-only. After lead review, --interrupt may attempt one SIGINT
to the exact coordinator. --status/--wait observe original identities only;
no retry, force termination, descendant signal, test or source edit is offered.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import psutil

ROOT = Path(__file__).resolve().parents[2]
EXPECTED_ROOT = Path('/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-native-h2-integration-fixes-20261113')
SCRATCH = ROOT.parent / 'scratch-g2-20261114'
COHORT = SCRATCH / 'final-engine-dependents'
RECORDS = SCRATCH / 'final-engine-freshness-interruption'
PYTHON = ROOT.parent.parent / 'data-sheets-schema/.venv/bin/python'
HEAD = 'e428f6c31eec90b808bc43ae8415973a0494d0d1'
BRANCH = 'codex/native-h2-integration-fixes-20261113'
COMMAND_SHA256 = '5f56fa638c2c155b03c9b8d22ad5e21f754aae82b03db2002962b6222b33f5e6'
DRIVER_SHA256 = 'ac7cebd1e187f16d1f033d0c45f5183b96319507015fd5c6d6b6ad6b61058fc7'
BASE_SHA256 = 'dff66b0c12df58b65c9e1a7b395cccf472bf040edbe86fec193e727b46934675'
COORDINATOR_PID = 55815
RUNNER_PID = 55795
EXEC_SESSION = 45479
# UTC conversion of ps lstart, observed read-only before authoring this helper.
OBSERVED_STARTS = {
    55795: '2026-11-14T07:36:44+00:00', 55815: '2026-11-14T07:36:45+00:00',
    55826: '2026-11-14T07:36:46+00:00', 55829: '2026-11-14T07:36:46+00:00',
    55832: '2026-11-14T07:36:46+00:00', 55833: '2026-11-14T07:36:47+00:00',
}
WORKERS = frozenset((55826, 55829, 55832, 55833))
NODES = [
    'tests/test_native_admission_failure.py',
    'tests/test_native_u4b_a3_reservation.py',
    'tests/test_native_u3k_freshness_order.py',
    'tests/test_native_u4b_admission.py',
    'tests/test_native_u4b_addendum_authority.py',
    'tests/test_native_u4b_readback.py',
    'tests/test_native_u3d_round9_capabilities.py',
    'tests/test_native_u3d_guard_contract.py',
    'tests/test_native_execution_registration_v2.py',
    'tests/test_native_execution_engine.py',
    'tests/test_native_incomplete_retention.py',
    'tests/test_native_shared_callback_preloading.py',
    'tests/test_native_shared_execution_failure.py',
    'tests/test_native_failure_publication.py',
    'tests/test_native_shared_live_capture.py',
]
SOURCE_SCOPE = ('src', 'tests', 'notes/matched_cborg_2026-09-13', 'pyproject.toml',
                'poetry.lock', 'conftest.py', '.github/workflows/main.yaml')
ARTIFACTS = ('command.json', 'pytest.log', 'pytest.xml', 'outcome.json')
REASON = ('Three failure markers in the owned final-engine-dependents cohort; '
          'interrupt once to retain the traceback and review the failures. '
          'Pre-reservation fixture-age expiry is suspected only; no failure identity or cause is yet established.')


def require(value, message):
    if not value:
        raise ValueError(message)


def stamp():
    return datetime.now(timezone.utc).isoformat()


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()


def pin(path):
    path = Path(path)
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def write_new(path, raw):
    with path.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    require(path.read_bytes() == raw, 'evidence readback failed')
    return pin(path)


def write_record(name, value):
    return write_new(RECORDS / name, encoded(value))


def expected_command():
    require(ROOT == EXPECTED_ROOT and SCRATCH.resolve(strict=True) == SCRATCH,
            'helper checkout or physical scratch root differs')
    raw = (COHORT / 'command.json').read_bytes()
    require(hashlib.sha256(raw).hexdigest() == COMMAND_SHA256, 'saved cohort command changed')
    record = json.loads(raw)
    require(record['cwd'] == str(ROOT) and record['head'] == HEAD, 'saved cohort checkout/head differs')
    suffix = ['-n', '4', '--dist', 'load', '--maxschedchunk=1',
              '--basetemp=' + str(COHORT / 'cases'), '--junitxml=' + str(COHORT / 'pytest.xml')]
    command = [str(PYTHON), '-m', 'pytest', '-q', '-p', 'no:cacheprovider', *NODES, *suffix]
    require(record['command'] == command and record['canary'] is False,
            'saved scheduled coordinator invocation differs')
    driver = ROOT / 'scripts/adhoc/run_g2_scheduled_checks_20261114.py'
    base = ROOT / 'scripts/adhoc/run_g2_checks_20261114.py'
    require(record['producer'] == pin(driver) and record['producer']['sha256'] == DRIVER_SHA256
            and record['base_runner'] == pin(base) and record['base_runner']['sha256'] == BASE_SHA256,
            'saved runner identities differ from reviewed driver bytes')
    parent = [str(PYTHON), 'scripts/adhoc/run_g2_scheduled_checks_20261114.py',
              'final-engine-dependents', *NODES]
    return command, parent


def observed_process(pid):
    process = psutil.Process(pid)
    created = process.create_time()
    expected = datetime.fromisoformat(OBSERVED_STARTS[pid]).timestamp()
    require(int(created) == int(expected), 'observed process PID was replaced: ' + str(pid))
    require(process.uids().real == os.getuid(), 'process owner differs: ' + str(pid))
    return process


def identity(process):
    # No argv, environment, CPU or memory observations for workers/descendants.
    return {'pid': process.pid, 'created': process.create_time(),
            'parent_pid': process.ppid(), 'status': process.status()}


def verify_current():
    command, parent_command = expected_command()
    require(subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip() == HEAD,
            'checkout HEAD changed; require fresh review')
    require(subprocess.check_output(['git', 'branch', '--show-current'], cwd=ROOT, text=True).strip() == BRANCH,
            'checkout branch changed')
    require(subprocess.run(['git', 'diff', '--quiet', 'HEAD', '--', *SOURCE_SCOPE], cwd=ROOT).returncode == 0,
            'source/test/config bytes changed during the cohort')
    require(not (COHORT / 'outcome.json').exists(), 'cohort already has an outcome; do not interrupt it')
    runner = observed_process(RUNNER_PID)
    coordinator = observed_process(COORDINATOR_PID)
    require(coordinator.ppid() == RUNNER_PID, 'coordinator parent changed')
    # Only these two argv arrays are read, after exact PID/start/owner checks.
    require(runner.cmdline() == parent_command, 'runner argv differs from the exact expected invocation')
    require(coordinator.cmdline() == command, 'coordinator argv differs from saved command.json')
    require(runner.cwd() == coordinator.cwd() == str(ROOT), 'runner/coordinator cwd differs')
    require(runner.is_running() and coordinator.is_running(), 'runner/coordinator exited during identity check')
    require({child.pid for child in coordinator.children(recursive=False)} == WORKERS,
            'coordinator worker set changed; require fresh review')
    workers = []
    for pid in sorted(WORKERS):
        child = observed_process(pid)
        require(child.ppid() == COORDINATOR_PID and child.cwd() == str(ROOT),
                'worker parent or checkout differs')
        workers.append(identity(child))
    descendants = []
    for child in coordinator.children(recursive=True):
        try:
            require(child.uids().real == os.getuid(), 'descendant owner differs')
            descendants.append(identity(child))
        except psutil.NoSuchProcess:
            continue  # Already exited; never a signal target.
    return coordinator, {'observed_at': stamp(), 'coordinator': identity(coordinator),
        'runner': identity(runner), 'workers': workers, 'descendants': descendants,
        'cwd': str(ROOT), 'head': HEAD, 'exec_session': EXEC_SESSION,
        'coordinator_argv_matches_saved': True, 'runner_argv_matches_expected': True,
        'command': pin(COHORT / 'command.json')}


def same_identity(before, after):
    return before['pid'] == after['pid'] and before['created'] == after['created']


def process_state(saved):
    try:
        process = psutil.Process(saved['pid'])
        if process.create_time() != saved['created']:
            return {**saved, 'original_reaped': True, 'observation': 'PID now belongs to a later process'}
        # Zombies are deliberately not called reaped. No cleanup signal is sent.
        return {**saved, 'original_reaped': False, 'observation': process.status()}
    except psutil.NoSuchProcess:
        return {**saved, 'original_reaped': True, 'observation': 'original PID absent'}
    except psutil.AccessDenied:
        return {**saved, 'original_reaped': False, 'observation': 'identity unavailable'}


def retained_artifacts():
    return {name: pin(COHORT / name) if (COHORT / name).is_file() else None for name in ARTIFACTS}


def cleanup_status(intent):
    expected_command()
    saved = intent['verified_identity']
    coordinator = process_state(saved['coordinator'])
    runner = process_state(saved['runner'])
    workers = [process_state(row) for row in saved['workers']]
    observed = {(row['pid'], row['created']): row for row in saved['descendants']}
    attempt_path = RECORDS / 'signal-attempt.json'
    if attempt_path.is_file():
        attempt = json.loads(attempt_path.read_bytes())
        require(attempt['target_pid'] == COORDINATOR_PID and attempt['signal'] == 'SIGINT',
                'saved signal attempt differs')
        # Also retain descendants first seen in the final pre-signal observation.
        for row in attempt['verified_identity']['descendants']:
            observed[(row['pid'], row['created'])] = row
    descendants = [process_state(row) for row in observed.values()]
    artifacts = retained_artifacts()
    outcome = None
    problem = None
    if artifacts['outcome.json'] is not None:
        try:
            outcome = json.loads((COHORT / 'outcome.json').read_bytes())
            require(type(outcome.get('returncode')) is int, 'outcome lacks integer returncode')
        except (OSError, ValueError, TypeError) as error:
            problem = type(error).__name__ + ': incomplete runner outcome'
    complete = (outcome is not None and problem is None and coordinator['original_reaped']
                and runner['original_reaped'] and all(row['original_reaped'] for row in workers)
                and all(row['original_reaped'] for row in descendants)
                and all(record is not None and record['bytes'] > 0 for record in artifacts.values()))
    return {'observed_at': stamp(), 'status': 'cleanup-confirmed' if complete else 'cleanup-pending',
        'safe_to_release_source_freeze': complete, 'coordinator': coordinator, 'runner': runner,
        'workers': workers, 'observed_descendants': descendants, 'artifacts': artifacts,
        'outcome': outcome, 'problem': problem, 'signals_sent_by_this_status_check': 0,
        'limit': 'Reaping checks cover both saved identity observations; no later/unobserved descendant or unrelated process is claimed inspected.'}


def record_cleanup(status):
    if status['safe_to_release_source_freeze']:
        snapshots = {}
        for name in ARTIFACTS:
            source = COHORT / name
            raw = source.read_bytes()
            require(pin(source) == status['artifacts'][name], 'cohort artifact changed after completed cleanup')
            destination = RECORDS / ('after-' + name)
            if destination.exists():
                require(destination.read_bytes() == raw, 'retained after snapshot differs; preserve it')
                snapshots[name] = pin(destination)
            else:
                snapshots[name] = write_new(destination, raw)
            require(snapshots[name]['sha256'] == status['artifacts'][name]['sha256'],
                    'after snapshot differs from completed artifact')
        status['after_snapshots'] = snapshots
    write_record('cleanup-' + str(time.time_ns()) + '.json', status)
    print(json.dumps(status, indent=2))
    return 0 if status['safe_to_release_source_freeze'] else 3


def interrupt(reason):
    require(reason == REASON, 'the exact reviewed failure-retention reason is required')
    coordinator, before = verify_current()
    RECORDS.mkdir(exist_ok=False)  # Existing intent forbids automatic retry.
    originals = {}
    for name in ARTIFACTS:
        source = COHORT / name
        originals[name] = (write_new(RECORDS / ('before-' + name), source.read_bytes())
                           if source.is_file() else None)
    intent = {'recorded_at': stamp(), 'reason': reason, 'cohort': str(COHORT),
        'head': HEAD, 'exec_session': EXEC_SESSION, 'verified_identity': before,
        'before_snapshots': originals, 'producer': pin(Path(__file__).resolve()),
        'psutil_version': psutil.__version__, 'signal': 'SIGINT', 'target_pid': COORDINATOR_PID,
        'target_scope': 'exact coordinator only; no process-group, runner, worker or native-child signal',
        'policy': 'One signal attempt; no force kill, retry, restart or source changes.',
        'failure_identity_established': False, 'failure_cause_established': False}
    write_record('interruption-intent.json', intent)
    current, final = verify_current()
    require(same_identity(before['coordinator'], final['coordinator'])
            and same_identity(before['runner'], final['runner'])
            and all(same_identity(old, new) for old, new in zip(before['workers'], final['workers'])),
            'owned process identity changed before SIGINT')
    write_record('signal-attempt.json', {'recorded_at': stamp(), 'target_pid': COORDINATOR_PID,
        'signal': 'SIGINT', 'verified_identity': final})
    delivered = False
    failure = None
    try:
        # psutil uses the original Process object's creation identity for reuse checks.
        require(coordinator.is_running() and current.is_running(), 'coordinator exited before SIGINT')
        coordinator.send_signal(signal.SIGINT)
        delivered = True
    except (psutil.NoSuchProcess, psutil.AccessDenied, ValueError) as error:
        failure = type(error).__name__
    write_record('signal-result.json', {'recorded_at': stamp(), 'target_pid': COORDINATOR_PID,
        'signal': 'SIGINT', 'sent': delivered, 'failure': failure, 'retry_allowed': False})
    return record_cleanup(cleanup_status(intent))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--inspect', action='store_true')
    modes.add_argument('--interrupt', action='store_true')
    modes.add_argument('--status', action='store_true')
    modes.add_argument('--wait', action='store_true')
    parser.add_argument('--reason')
    parser.add_argument('--wait-seconds', type=int, default=45)
    args = parser.parse_args()
    require(sys.platform == 'darwin', 'this exact observed process plan is macOS-only')
    require(1 <= args.wait_seconds <= 45, 'wait window must be one through forty-five seconds')
    if args.inspect:
        _, value = verify_current()
        print(json.dumps({'mode': 'read-only inspection', 'identity': value,
                          'reason_required': REASON, 'signals_sent': 0, 'files_written': 0}, indent=2))
        return 0
    if args.interrupt:
        return interrupt(args.reason or '')
    intent = json.loads((RECORDS / 'interruption-intent.json').read_bytes())
    require(intent['target_pid'] == COORDINATOR_PID and intent['signal'] == 'SIGINT'
            and intent['cohort'] == str(COHORT) and intent['head'] == HEAD,
            'unexpected saved interruption intent')
    deadline = time.monotonic() + (args.wait_seconds if args.wait else 0)
    while True:
        status = cleanup_status(intent)
        if status['safe_to_release_source_freeze'] or time.monotonic() >= deadline:
            return record_cleanup(status)
        time.sleep(1)


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, psutil.Error) as error:
        # Never dump actual mismatched argv/environment into a diagnostic.
        print('Cohort interruption refused: ' + type(error).__name__ + ': ' + str(error), file=sys.stderr)
        raise SystemExit(2)

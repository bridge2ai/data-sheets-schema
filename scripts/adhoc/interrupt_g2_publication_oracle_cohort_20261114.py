#!/usr/bin/env python3
"""Review-gated SIGINT for the G2 publication test oracle defect, 2026-11-14.

Inputs: exact final-regressions command.json and the coordinator/runner/worker
identities observed read-only on 2026-11-14. Uses psutil process identity only;
no CPU monitoring, unrelated argv enumeration, project imports or test runs.
Outputs: immutable interruption evidence beside the original cohort, preserving
its command/log/outcome files. --inspect is read-only. --interrupt requires an
explicit reason and may send exactly one SIGINT to the verified coordinator.
--status/--wait only observe cleanup; they never send another signal or force
termination. Run --interrupt only after the lead reviews this helper.
Derived from interrupt_g2_obsolete_cohort_20261114.py; the original is preserved.
Reason: retain the confirmed serialization-oracle traceback and correct the test
contract. No runtime-hang cause is inferred.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import sys
import time

import psutil

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-g2-20261114'
COHORT = SCRATCH / 'final-regressions'
RECORDS = SCRATCH / 'final-regressions-interruption-6217-oracle'
PYTHON = ROOT.parent.parent / 'data-sheets-schema/.venv/bin/python'
COMMAND_SHA256 = '7e9841214a982e6199a5a35d7b62500cdd93bb359bc794e6a1631b010f740ada'
COORDINATOR_PID = 25231
RUNNER_PID = 25217
# Seconds are from ps lstart, independently observed before writing this helper.
OBSERVED_STARTS = {
    25217: '2026-11-14T05:55:39+00:00', 25231: '2026-11-14T05:55:39+00:00',
    25256: '2026-11-14T05:55:42+00:00', 25272: '2026-11-14T05:55:43+00:00',
    25279: '2026-11-14T05:55:44+00:00', 25282: '2026-11-14T05:55:44+00:00',
}
WORKERS = frozenset((25256, 25272, 25279, 25282))
REASON = ('Confirmed publication witness compact-versus-pretty serialization oracle defect; '
          'stop to retain the traceback and fix the test contract. This does not establish a runtime hang.')


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
    raw = (COHORT / 'command.json').read_bytes()
    require(hashlib.sha256(raw).hexdigest() == COMMAND_SHA256, 'saved cohort command changed')
    record = json.loads(raw)
    require(record['cwd'] == str(ROOT), 'saved cohort cwd differs')
    command = record['command']
    require(command[:6] == [str(PYTHON), '-m', 'pytest', '-q', '-p', 'no:cacheprovider'],
            'saved coordinator prefix differs')
    require(command[-4:] == ['-n', '4', '--basetemp=' + str(COHORT / 'cases'),
                            '--junitxml=' + str(COHORT / 'pytest.xml')],
            'saved coordinator worker/output arguments differ')
    nodes = command[6:-4]
    require(nodes == ['tests/test_native_publication_signals.py', 'tests/test_native_attempt_deadline.py'],
            'saved cohort selectors differ from the reviewed full-file invocation')
    parent = [str(PYTHON), 'scripts/adhoc/run_g2_checks_20261114.py', 'final-regressions', *nodes]
    return command, parent


def observed_process(pid):
    process = psutil.Process(pid)
    created = process.create_time()
    expected = datetime.fromisoformat(OBSERVED_STARTS[pid]).timestamp()
    require(int(created) == int(expected), 'observed process PID was replaced: ' + str(pid))
    require(process.uids().real == os.getuid(), 'process owner differs: ' + str(pid))
    return process


def identity(process):
    # No argv or environment is read for descendants/workers.
    return {'pid': process.pid, 'created': process.create_time(),
            'parent_pid': process.ppid(), 'status': process.status()}


def verify_current():
    command, parent_command = expected_command()
    require(not (COHORT / 'outcome.json').exists(), 'cohort already has an outcome; do not interrupt it')
    runner = observed_process(RUNNER_PID)
    coordinator = observed_process(COORDINATOR_PID)
    require(coordinator.ppid() == RUNNER_PID, 'coordinator parent changed')
    # These are the only two cmdline reads, after PID/start/owner checks. Compare
    # actual argv arrays, never a shell-split or flattened ps command string.
    require(runner.cmdline() == parent_command, 'runner argv differs from the exact expected invocation')
    require(coordinator.cmdline() == command, 'coordinator argv differs from saved command.json')
    require(runner.cwd() == coordinator.cwd() == str(ROOT), 'runner/coordinator cwd differs')
    require(runner.is_running() and coordinator.is_running(), 'runner/coordinator exited during identity check')
    children = coordinator.children(recursive=False)
    require({child.pid for child in children} == WORKERS, 'coordinator worker set changed; require fresh review')
    workers = []
    for pid in sorted(WORKERS):
        child = observed_process(pid)
        require(child.ppid() == COORDINATOR_PID, 'worker no longer belongs to coordinator')
        workers.append(identity(child))
    descendants = []
    for child in coordinator.children(recursive=True):
        try:
            descendants.append(identity(child))
        except psutil.NoSuchProcess:
            continue  # Already exited; never a signal target.
    return coordinator, {'observed_at': stamp(), 'coordinator': identity(coordinator),
        'runner': identity(runner), 'workers': workers, 'descendants': descendants,
        'cwd': str(ROOT), 'coordinator_argv_matches_saved': True,
        'runner_argv_matches_expected': True, 'command': pin(COHORT / 'command.json')}


def same_identity(before, after):
    return before['pid'] == after['pid'] and before['created'] == after['created']


def process_state(saved):
    try:
        process = psutil.Process(saved['pid'])
        if process.create_time() != saved['created']:
            return {**saved, 'original_reaped': True, 'observation': 'PID now belongs to a later process'}
        # Zombies are deliberately not called reaped.
        return {**saved, 'original_reaped': False, 'observation': process.status()}
    except psutil.NoSuchProcess:
        return {**saved, 'original_reaped': True, 'observation': 'original PID absent'}
    except psutil.AccessDenied:
        return {**saved, 'original_reaped': False, 'observation': 'identity unavailable'}


def retained_artifacts():
    return {name: pin(COHORT / name) if (COHORT / name).is_file() else None
            for name in ('command.json', 'pytest.log', 'pytest.xml', 'outcome.json')}


def cleanup_status(intent):
    expected_command()
    saved = intent['verified_identity']
    coordinator = process_state(saved['coordinator'])
    runner = process_state(saved['runner'])
    workers = [process_state(row) for row in saved['workers']]
    descendants = [process_state(row) for row in saved['descendants']]
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
                and all(row['original_reaped'] for row in descendants))
    return {'observed_at': stamp(), 'status': 'cleanup-confirmed' if complete else 'cleanup-pending',
        'safe_to_release_source_freeze': complete, 'coordinator': coordinator, 'runner': runner,
        'workers': workers, 'observed_descendants': descendants, 'artifacts': artifacts,
        'outcome': outcome, 'problem': problem, 'signals_sent_by_this_status_check': 0,
        'limit': 'Reaping checks cover the observed coordinator/runner/workers and saved descendants; no unrelated argv is read.'}


def interrupt(reason):
    require(reason == REASON, 'the exact reviewed oracle-defect interruption reason is required')
    coordinator, before = verify_current()
    RECORDS.mkdir(exist_ok=False)  # Existing intent prevents any automatic retry.
    originals = {}
    for name in ('command.json', 'pytest.log', 'pytest.xml', 'outcome.json'):
        source = COHORT / name
        originals[name] = (write_new(RECORDS / ('before-' + name), source.read_bytes())
                           if source.is_file() else None)
    intent = {'recorded_at': stamp(), 'reason': reason, 'cohort': str(COHORT),
        'verified_identity': before, 'before_snapshots': originals,
        'producer': pin(Path(__file__).resolve()), 'psutil_version': psutil.__version__,
        'signal': 'SIGINT', 'target_pid': COORDINATOR_PID,
        'target_scope': 'exact coordinator only; no process group, runner, worker or native-child signal',
        'policy': 'One signal attempt; no force kill, retry, restart or source changes.'}
    write_record('interruption-intent.json', intent)
    # Re-read all mutable identity after snapshot persistence, immediately before
    # the one permitted signal attempt. psutil additionally checks PID reuse.
    current, final = verify_current()
    require(same_identity(before['coordinator'], final['coordinator'])
            and same_identity(before['runner'], final['runner']), 'identity changed before SIGINT')
    write_record('signal-attempt.json', {'recorded_at': stamp(), 'target_pid': COORDINATOR_PID,
        'signal': 'SIGINT', 'verified_identity': final})
    delivered = False
    failure = None
    try:
        # The original Process object retains creation time for its reuse check.
        require(coordinator.is_running() and current.is_running(), 'coordinator exited before SIGINT')
        coordinator.send_signal(signal.SIGINT)
        delivered = True
    except (psutil.NoSuchProcess, psutil.AccessDenied, ValueError) as error:
        failure = type(error).__name__
    write_record('signal-result.json', {'recorded_at': stamp(), 'target_pid': COORDINATOR_PID,
        'signal': 'SIGINT', 'sent': delivered, 'failure': failure,
        'retry_allowed': False})
    status = cleanup_status(intent)
    write_record('cleanup-' + str(time.time_ns()) + '.json', status)
    print(json.dumps(status, indent=2))
    return 0 if status['safe_to_release_source_freeze'] else 3


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
                          'signals_sent': 0, 'files_written': 0}, indent=2))
        return 0
    if args.interrupt:
        return interrupt(args.reason or '')
    intent = json.loads((RECORDS / 'interruption-intent.json').read_bytes())
    require(intent['target_pid'] == COORDINATOR_PID and intent['signal'] == 'SIGINT', 'unexpected saved interruption intent')
    deadline = time.monotonic() + (args.wait_seconds if args.wait else 0)
    while True:
        status = cleanup_status(intent)
        if status['safe_to_release_source_freeze'] or time.monotonic() >= deadline:
            write_record('cleanup-' + str(time.time_ns()) + '.json', status)
            print(json.dumps(status, indent=2))
            return 0 if status['safe_to_release_source_freeze'] else 3
        time.sleep(1)


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, psutil.Error) as error:
        # Never dump actual mismatched argv/environment into a diagnostic.
        print('Cohort interruption refused: ' + type(error).__name__ + ': ' + str(error), file=sys.stderr)
        raise SystemExit(2)

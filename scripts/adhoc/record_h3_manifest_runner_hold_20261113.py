"""Retain the manifest canary's sandbox-start hold, 2026-11-13.

Inputs: the exact first refinement cohort's existing plan/log and an exact
runner-process query. Output: an explicit nonacceptance outcome; no test/native
execution. The parent observer's error is transcribed from retained tool output.
"""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
COHORT = ROOT.parent / 'scratch-h3-environment-manifest-20261113/tests/refinements-manifest-canary-01'
RUNNER = ROOT / 'scripts/adhoc/run_h3_environment_tests_20261113.py'


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def main():
    log = COHORT / 'pytest.log'
    if log.read_text() != 'sandbox-exec: sandbox_apply: Operation not permitted\n':
        raise ValueError('original runner log differs from the recorded startup refusal')
    query = subprocess.run(['/usr/bin/pgrep', '-fl', str(RUNNER)], capture_output=True, text=True)
    if query.returncode != 1 or query.stdout or query.stderr:
        raise ValueError('exact runner process query did not establish an empty observation')
    outcome = {'returncode': 125, 'worker_returncode': None, 'worker': None,
        'interrupted': 'parent_process_observation_permission_error', 'forced_cleanup': False,
        'cleanup_verified': False, 'observed_surviving_pids': [],
        'status': 'harness_startup_hold_nonacceptance',
        'parent_error': 'PermissionError: [Errno 1] Operation not permitted (originated from sysctl(KERN_PROC_ALL))',
        'parent_error_origin': 'Transcribed from the retained execution-tool output; no original parent traceback log was saved.',
        'cleanup_scope': 'Later exact runner process-name query found no matches; initial observation failed, so cleanup is not certified.',
        'plan': pin(COHORT / 'plan.json'), 'log': pin(log), 'recorder': pin(Path(__file__)),
        'query': {'argv': query.args, 'returncode': query.returncode, 'stdout': query.stdout, 'stderr': query.stderr},
        'test_acceptance': False}
    path = COHORT / 'outcome.json'
    raw = (json.dumps(outcome, indent=2, sort_keys=True) + '\n').encode()
    with path.open('xb') as stream:
        stream.write(raw)
    if path.read_bytes() != raw:
        raise ValueError('hold outcome did not persist')
    print(json.dumps(pin(path), sort_keys=True))


if __name__ == '__main__':
    main()

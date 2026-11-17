"""Apply D159 reviewed limit substitutions; inputs checkout, outputs diff and JSON.

Serves the Claude lead D159 assignment, 2026-11-17. Dry run by default;
--apply --only PATH supplies the one-file canary before the remaining batch.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
BASE = 'bc61c2b5ccf894a50a386044acf50ac5ee34cb54'
N = 'notes/matched_cborg_2026-09-13/native_controls/'
S = 'src/data_sheets_schema/'
SPECIAL = {
    S+'native_admission_timer.py': [('ADMISSION_SECONDS = 900', 'ADMISSION_SECONDS = 1500')],
    S+'native_prepared_worker.py': [('VERIFY_SECONDS = 300', 'VERIFY_SECONDS = 600')],
    S+'native_runtime_profiles.py': [('SYNTHETIC_DEADLINE_SECONDS = 7200', 'SYNTHETIC_DEADLINE_SECONDS = 9600')],
    S+'native_subscription_guard_v2.py': [('MAX_AGE_SECONDS = 1200', 'MAX_AGE_SECONDS = 1800')],
    S+'native_u4b_policy.py': [("'max_age_seconds': 1200", "'max_age_seconds': 1800")],
    S+'native_run_limits.py': [('21600', '28800'), ('43200', '57600')],
    S+'native_shared_callback_orchestration.py': [('CALLBACK_TEARDOWN_SECONDS = 2.0', 'CALLBACK_TEARDOWN_SECONDS = 4.0')],
    N+'native_control.py': [("'initialize_timeout_seconds': 30", "'initialize_timeout_seconds': 60"),
        ("'callback_timeout_seconds': 2", "'callback_timeout_seconds': 4"),
        ("'runtime_callback_timeout_seconds': 3", "'runtime_callback_timeout_seconds': 6"),
        ("'observer_timeout_seconds': 120", "'observer_timeout_seconds': 240"),
        ("'runtime_callback_timeout_seconds': 125", "'runtime_callback_timeout_seconds': 250"),
        ('CONTROL_WORKER_JOIN_SECONDS = .25', 'CONTROL_WORKER_JOIN_SECONDS = .5')],
    'notes/matched_cborg_2026-09-13/budgeted_cborg.py': [
        ('LEGACY_UPSTREAM_READ_SECONDS = 1800', 'LEGACY_UPSTREAM_READ_SECONDS = 2700'),
        ('UPSTREAM_CONNECT_SECONDS = 20', 'UPSTREAM_CONNECT_SECONDS = 40'),
        ('POLICY_COUNT_TRY_SECONDS = 120', 'POLICY_COUNT_TRY_SECONDS = 240'),
        ('POLICY_COUNT_PAUSE_SECONDS = 5', 'POLICY_COUNT_PAUSE_SECONDS = 10')],
    '.github/workflows/main.yaml': [("&& 45 || 60", "&& 60 || 80"), ('timeout-minutes: 180', 'timeout-minutes: 240'),
        ('two-hour attempt budget plus setup', '160-minute attempt budget plus 20-25 minutes of setup')],
    'tests/test_ci_sharding.py': [("&& 45 || 60", "&& 60 || 80"), ('LONG_NATIVE_LANES, "native", 180', 'LONG_NATIVE_LANES, "native", 240')],
    N+'test_native_history_control.py': [("['observer_timeout_seconds'] == 120", "['observer_timeout_seconds'] == 240")],
}

SPECIAL[S+'native_shared_permission_protocol.py'] = SPECIAL[N+'native_control.py']
SPECIAL[N+'native_control.py'] = SPECIAL[N+'native_control.py'] + [('selector.select(.05)', 'selector.select(.1)'),
    ('# Explicit opt-in; legacy initialization/replay stays byte-identical (#2420).', '# Explicit opt-in; both contracts use D159 time limits.')]
SPECIAL[S+'native_shared_callback_orchestration.py'] += [('existing 2-second window', 'D159 4-second window'),
    ('120-second observer acceptance window', '240-second observer acceptance window')]
SPECIAL[N+'run_native_canary.py'] = [('reap_observed(process, 2)', 'reap_observed(process, 4)'),
    ('await_leader_exit(process, 2)', 'await_leader_exit(process, 4)'),
    ('TimeoutExpired(process.args, 2)', 'TimeoutExpired(process.args, 4)')]
SPECIAL[S+'native_host_power.py'] = [('selected.select(min(remaining, 0.1))', 'selected.select(min(remaining, 0.2))')]
SPECIAL[S+'historical_digest.py'] = [('_GIT_SECONDS = 5.0', '_GIT_SECONDS = 10.0')]
SPECIAL['tests/test_native_permission_probe.py'] = [('kwargs["timeout"] == 10', 'kwargs["timeout"] == 20'), ('assert timeout == 2', 'assert timeout == 4')]
SPECIAL['tests/test_native_shared_permission_protocol.py'] = [("'initialize_timeout_seconds': 30.0", "'initialize_timeout_seconds': 60.0")]
SPECIAL['utils/native_ci_evidence.py'] = [("'attempt_seconds': 900, 'helper_seconds': 180, 'runner_seconds': 3600",
    "'attempt_seconds': 9600, 'helper_seconds': 1000, 'runner_seconds': 14400")]
SPECIAL['tests/test_native_ci_evidence.py'] = [("['attempt_seconds'] == 900", "['attempt_seconds'] == 9600"),
    ("['helper_seconds'] == 180", "['helper_seconds'] == 1000"), ("['runner_seconds'] == 3600", "['runner_seconds'] == 14400")]
SPECIAL[N+'test_native_history_control.py'] += [('observer_timeout_seconds=121', 'observer_timeout_seconds=241'),
    ('callback_timeout_seconds=3', 'callback_timeout_seconds=5'),
    ('runtime_callback_timeout_seconds=126', 'runtime_callback_timeout_seconds=251'),
    ('legacy host\'s 3 seconds', 'legacy host\'s 6 seconds'), ('2-second completion budget', '4-second completion budget'),
    ('clock[0] = 3.25', 'clock[0] = 6.25'), ('started + 121', 'started + 241'),
    ('clock[0] = 2.5', 'clock[0] = 4.5'), ('host 125s bound', 'host 250s bound'), ('clock[0] = 126.', 'clock[0] = 251.'),
    ("'timeout': 125", "'timeout': 250")]
SPECIAL[N+'probe_native_history.py'] = [('time.sleep(4.0)', 'time.sleep(8.0)'), ("observed[0]['at']>=4", "observed[0]['at']>=8")]
SPECIAL[N+'test_native_launch.py'] = [('deadline once per 0.05 s poll', 'deadline once per 0.1 s poll'),
    ('controller poll (0.05 s)', 'controller poll (0.1 s)')]
SPECIAL[N+'test_probe_native_history.py'] = [("'observer_duration_seconds':4.01", "'observer_duration_seconds':8.01"),
    ("['observer_duration_seconds']>=4", "['observer_duration_seconds']>=8")]
SHARED = [S+x+'.py' for x in ['prompt_registry', 'provenance', 'latch_journal', 'historical_digest']]

def transform(path, raw):
    text = raw
    for old, new in SPECIAL.get(path, []):
        text = text.replace(old, new)
    native = path.startswith(S+'native_') or path in SHARED + [N+'run_native_canary.py', N+'native_proxy.py', 'scripts/native_registration_timestamp.py']
    if native:
        # Literal execution waits and polling intervals; zero means nonblocking.
        for pattern in [r'(?<=timeout=)([0-9]+(?:\.[0-9]+)?)(?![\w.])',
                        r'(?<=timeout_seconds=)([0-9]+(?:\.[0-9]+)?)(?![\w.])',
                        r'(?<=time.sleep\()([0-9]+(?:\.[0-9]+)?)(?![\w.])',
                        r'(?<=.settimeout\()([0-9]+(?:\.[0-9]+)?)(?![\w.])',
                        r'(?<=time.monotonic\(\) \+ )([0-9]+(?:\.[0-9]+)?)(?![\w.])']:
            text = re.sub(pattern, lambda m: str(float(m[0])*2) if '.' in m[0] else str(int(m[0])*2), text)
        text = text.replace('POLL_SECONDS = 0.1', 'POLL_SECONDS = 0.2')
        text = text.replace('cleanup_timeout=2', 'cleanup_timeout=4').replace('server.timeout = 0.05', 'server.timeout = 0.1')
        text = text.replace('timeout=min(0.02,', 'timeout=min(0.04,')
        text = text.replace('settimeout(min(1.0,', 'settimeout(min(2.0,')
    fixture = path.startswith('tests/') and ('native' in path)
    if fixture:
        text = re.sub(r'\b(21599|21600|21601|43200|43201)\b', lambda m: {'21599':'28799', '21600':'28800', '21601':'28801', '43200':'57600', '43201':'57601'}[m[0]], text)
    if native or fixture or path == 'scripts/draft_native_probe_packet.py':
        text = re.sub(r'\b600000\b', '1000000', text)
    age_tests = ['test_native_u4b_a3_policy.py', 'test_native_launch_sequence.py', 'test_native_launch_sequence_signals.py', 'test_native_prepared_worker.py']
    if Path(path).name in age_tests:
        text = re.sub(r'\b(1199|1200|1201)\b', lambda m: str(int(m[0])+600), text)
    if path == 'tests/test_native_prepared_worker.py':
        text = text.replace('lambda: 1300.0', 'lambda: 1900.0')
    if path == 'tests/test_native_u4b_a3_policy.py':
        text = re.sub(r'\b(899|900|901)\b', lambda m: str(int(m[0])+600), text)
        text = text.replace('age_is_900_seconds', 'age_is_1500_seconds')
    if path == 'tests/test_native_shared_observations.py':
        text = text.replace("'runtime_callback_timeout_seconds':125", "'runtime_callback_timeout_seconds':250")
        text = text.replace("'timeout':125", "'timeout':250")
    if path == 'tests/test_native_synthetic_profiles.py':
        text = text.replace("'600001'", "'1000001'")
    if path in ['tests/test_native_admission_timer.py', 'tests/test_native_attempt_deadline.py', 'tests/test_native_admission_failure.py']:
        text = re.sub(r'\b(898|899|900|901)\b', lambda m: str(int(m[0])+600), text)
    if path == 'tests/test_native_dispatch_boundary_d156.py':
        text = text.replace('1201', '1801')
    return text

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--apply', action='store_true')
    p.add_argument('--only')
    args = p.parse_args()
    paths = set(SPECIAL)
    paths.update(SHARED)
    for pattern in [S+'native*.py', 'tests/*native*.py', 'tests/utils/*native*.py', 'tests/fixtures/native_shared_execution/*.py']:
        paths.update(str(x.relative_to(ROOT)) for x in ROOT.glob(pattern))
    paths.update(['scripts/draft_native_probe_packet.py', 'scripts/native_registration_timestamp.py', N+'run_native_canary.py', N+'native_proxy.py'])
    rows = []
    for path in sorted(paths):
        if args.only and path != args.only:
            continue
        target = ROOT / path
        old = subprocess.check_output(['git', 'show', BASE+':'+path], cwd=ROOT, text=True)
        new = transform(path, old)
        if old == new:
            continue
        changes = [{'line': i, 'old': a.replace(chr(64), '[at]'), 'new': b.replace(chr(64), '[at]')}
                   for i, (a,b) in enumerate(zip(old.splitlines(), new.splitlines()), 1) if a != b]
        rows.append({'path': path, 'changes': changes})
        if args.apply:
            target.write_text(new)
    print(json.dumps(rows, indent=2))

if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Fix issue 6218 power ordering and retained refusal evidence, 2026-11-14.
Inputs: assigned worktree source. Outputs: bounded power refusal and ordered
reservation/dispatch checks. No tests, provider calls or runtime probes.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def replace(path, old, new):
    text = path.read_text()
    if text.count(old) != 1:
        raise RuntimeError('expected exactly one edit target in ' + str(path))
    path.write_text(text.replace(old, new))


power = ROOT / 'src/data_sheets_schema/native_host_power.py'
replace(power, 'AC is required only at sequence/proof start. Clock divergence is suspension\n',
    'AC is required at sequence/proof start and native launch. Clock divergence is suspension\n')
replace(power, '''def dispatch_power():
    """Read the power source last, without a subsequent slow lid query."""
    battery = _local(['/usr/bin/pmset', '-g', 'batt'], limit=16384)
    reading = parse_power(battery['text'], '')
    if reading['source'] != 'ac' or battery['status'] != 'read':
        raise ValueError('host power must be positively observed as AC immediately before dispatch')
    return reading
''', '''class DispatchPowerRefused(ValueError):
    """A concrete refusal with normalized local evidence, never probe output."""
    def __init__(self, reading):
        self.reading = dict(reading)
        super().__init__('host power must be positively observed as AC before native launch; reading='
                         + json.dumps(self.reading, sort_keys=True, separators=(',', ':')))


def dispatch_power():
    """Read bounded power-source evidence without a subsequent slow lid query."""
    battery = _local(['/usr/bin/pmset', '-g', 'batt'], limit=16384)
    parsed = parse_power(battery['text'], '')
    status = battery.get('status')
    status = status if status in ('read', 'unknown') else 'unknown'
    reason = battery.get('reason')
    if reason not in (None, 'nonzero_exit', 'OSError', 'ValueError', 'TimeoutError', 'TimeoutExpired'):
        reason = 'unrecognized_probe_reason'
    code = battery.get('returncode')
    code = code if type(code) is int and -(2 ** 31) <= code < 2 ** 31 else None
    reading = {'source': parsed['source'], 'battery_percent': parsed['battery_percent'],
        'observed_wall_ns': time.time_ns(), 'probe_status': status,
        'probe_reason': reason, 'probe_returncode': code}
    if reading['source'] != 'ac' or status != 'read' or code not in (None, 0):
        raise DispatchPowerRefused(reading)
    return reading
''')
engine = ROOT / 'src/data_sheets_schema/native_execution_orchestration.py'
replace(engine, '    """Consume exact saved admission before the caller may activate/spawn."""',
    '    """Consume exact saved admission after launch checks and before spawn."""')
replace(engine, '''    # Hold the registration-wide word/limits lock through the first reservation
    # effect. A renewal cannot supersede the word between checking and mkdir.
    with pre_timing.step('reservation'), reservation_lease():
        controls.require_complete()
        # Source recapture can be slow: measure the preparation margin only
        # after it, immediately before the attempt identity is consumed.
        launch_guard.before_reservation()
        _require_launch_profile(value['runtime'], expected_profile)
        attempt.mkdir(mode=0o700)  # Even a partial reservation consumes the identity.
''', '''    from . import native_host_power as host_power
    # Hold the registration-wide word/limits lock through the first reservation
    # effect. A renewal cannot supersede the word between checking and mkdir.
    with pre_timing.step('reservation'), reservation_lease():
        controls.require_complete()
        _require_launch_profile(value['runtime'], expected_profile)
        try:
            power_reading = host_power.dispatch_power()
        except host_power.DispatchPowerRefused as exc:
            # Buffer only: the outer scope persists after refusal and lock release.
            pre_timing.record('reservation_power', passed=False, **exc.reading)
            raise
        pre_timing.record('reservation_power', passed=True, **power_reading)
        # Source recapture, profile verification and the bounded power probe can
        # be slow. Recheck the margin after them, immediately before reservation.
        launch_guard.before_reservation()
        attempt.mkdir(mode=0o700)  # Even a partial reservation consumes the identity.
''')
replace(engine, '''    from . import native_host_power as host_power
    host_power.observe(attempt, 'start', host_power.start_run, attempt)
''', '''    host_power.observe(attempt, 'start', host_power.start_run, attempt)
''')
replace(engine, '''                    _admit_subscription_guard(launch_guard, attempt, _file, durable_new)
                    contract.activate_before_dispatch(adapter, started_raw)
                    _require_launch_profile(value['runtime'], expected_profile)
                    host_power.dispatch_power()
''', '''                    contract.activate_before_dispatch(adapter, started_raw)
                    _require_launch_profile(value['runtime'], expected_profile)
                    try:
                        host_power.dispatch_power()
                    except host_power.DispatchPowerRefused as exc:
                        # The pre-reservation trace is sealed. The immutable final
                        # result retains this bounded reading through the sticky stop.
                        reason = 'dispatch power refused: ' + str(exc)
                        stopped(reason)
                        raise controls['run_native_canary'].BudgetStop(reason) from exc
                    _admit_subscription_guard(launch_guard, attempt, _file, durable_new)
''')

#!/usr/bin/env python3
"""Repair G2-REVIEW-6218-F1 without weakening guard checks, 2026-11-14.
Inputs: issue 6218 implementation and public synthetic regression file.
Outputs: guard-before-activation order plus consumed-byte/expiry regressions.
No tests, commits, provider calls or native execution are performed.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
engine = ROOT / 'src/data_sheets_schema/native_execution_orchestration.py'
raw = engine.read_text()
old = '''                    contract.activate_before_dispatch(adapter, started_raw)
                    _require_launch_profile(value['runtime'], expected_profile)
                    try:
                        host_power.dispatch_power()
'''
new = '''                    _require_launch_profile(value['runtime'], expected_profile)
                    try:
                        host_power.dispatch_power()
'''
assert raw.count(old) == 1
raw = raw.replace(old, new)
old = '''                    _admit_subscription_guard(launch_guard, attempt, _file, durable_new)
                observe = _guarded_observer'''
new = '''                    _admit_subscription_guard(launch_guard, attempt, _file, durable_new)
                    # Keep one-use stage writes behind the consumed-guard checks.
                    # A final check at actual Popen remains the separate 6207 gap.
                    contract.activate_before_dispatch(adapter, started_raw)
                observe = _guarded_observer'''
assert raw.count(old) == 1
raw = raw.replace(old, new)
raw = raw.replace('Consume exact saved admission after launch checks and before spawn.',
                  'Consume exact saved admission before stage activation and spawn.')
engine.write_text(raw)

test = ROOT / 'tests/test_native_attempt_deadline.py'
raw = test.read_text()
old = '''    assert (attempt / 'transcript.jsonl').read_bytes() == b''
    assert execute.read_final(case['raw']) == result


def test_slow_power_probe'''
new = '''    assert (attempt / 'transcript.jsonl').read_bytes() == b''
    assert all(not Path(case['selection'].role(role)).exists()
               for role in ('execution_capture', 'started_capture', 'journal'))
    assert execute.read_final(case['raw']) == result


def test_slow_power_probe'''
assert raw.count(old) == 1
raw = raw.replace(old, new)
raw += '''

@pytest.mark.parametrize('defect', ['changed_consumed_guard', 'expired_after_power'])
def test_dispatch_guard_refusal_precedes_stage_activation(tmp_path, monkeypatch, defect):
    from tests.test_native_shared_execution import make_case
    from data_sheets_schema import native_shared_execution_orchestration as execute
    from data_sheets_schema import native_execution_authority_v2 as authority
    from data_sheets_schema import native_execution_orchestration as engine
    from data_sheets_schema import native_subscription_guard_v2 as subscription
    monkeypatch.chdir(authority.ROOT)
    case = make_case(tmp_path / 'guard-before-activation')
    attempt = Path(case['value']['attempt_directory'])
    stage_paths = [Path(case['selection'].role(role))
                   for role in ('execution_capture', 'started_capture', 'journal')]
    assert all(not path.exists() for path in stage_paths)
    document = json.loads(Path(case['kwargs']['subscription_guard_path']).read_bytes())
    captured = subscription._timestamp(document['captured_at'], 'synthetic capture time')
    ticks = [captured + 1]
    monkeypatch.setattr(subscription, '_now', lambda: ticks[0])
    original_power = power.dispatch_power
    original_execute = engine._execute_child
    original_activate = engine.ExecutionContract.activate_before_dispatch
    probes, activated, refused, entered = [], [], [], []
    def observed_power():
        reading = original_power()
        probes.append(reading)
        if defect == 'expired_after_power' and len(probes) == 2:
            # Expire after launch_check's independent authority join, at the
            # last power probe; only the consuming guard can catch this change.
            ticks[0] = captured + document['max_age_seconds'] + 1
        return reading
    monkeypatch.setattr(power, 'dispatch_power', observed_power)
    def activation(self, adapter, started_raw):
        activated.append(True)
        return original_activate(self, adapter, started_raw)
    monkeypatch.setattr(engine.ExecutionContract, 'activate_before_dispatch', activation)
    def checked_transport(controls, argv, **kwargs):
        entered.append(True)
        if defect == 'changed_consumed_guard':
            consumed = attempt / 'subscription-guard.json'
            consumed.write_bytes(consumed.read_bytes() + b' ')
        runner = sys.modules['run_native_canary']
        real_popen = runner.subprocess.Popen
        def popen(command, *args, **named):
            if list(command) == list(argv):
                pytest.fail('refused guard reached child dispatch')
            return real_popen(command, *args, **named)
        with monkeypatch.context() as patch:
            patch.setattr(runner.subprocess, 'Popen', popen)
            try:
                return original_execute(controls, argv, **kwargs)
            except ValueError as exc:
                refused.append(str(exc))
                raise
    monkeypatch.setattr(engine, '_execute_child', checked_transport)
    if defect == 'changed_consumed_guard':
        # Publication must also refuse the changed consumed evidence; never
        # restore those bytes merely to manufacture a readable final record.
        with pytest.raises(ValueError, match='consumed subscription guard changed before dispatch'):
            execute.synthetic_launch(case['raw'], **case['kwargs'])
        assert refused == ['consumed subscription guard changed before dispatch']
    else:
        result = execute.synthetic_launch(case['raw'], **case['kwargs'])
        assert result['state'] == 'failed' and result['child_exit_code'] is None
        assert result['subscription_guard']['dispatched'] is False
        assert refused == ['subscription observation is stale or future-dated']
        assert execute.read_final(case['raw']) == result
    assert entered == [True] and len(probes) == 2
    assert activated == [] and all(not path.exists() for path in stage_paths)
    assert not (attempt / 'subscription-dispatched.json').exists()
    assert (attempt / 'transcript.jsonl').read_bytes() == b''
'''
test.write_text(raw)

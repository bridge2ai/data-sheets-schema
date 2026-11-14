#!/usr/bin/env python3
"""Add offline regressions for issue 6218, 2026-11-14.
Inputs: assigned worktree tests. Outputs: normalized-reading unit checks and
public synthetic early/late refusal regressions. Does not execute tests.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
host = ROOT / 'tests/test_native_host_power.py'
addition = '''

@pytest.mark.parametrize('battery,source,reason,admitted', [
    ({'status': 'read', 'reason': None, 'returncode': 0,
      'text': "Now drawing from 'AC Power'\\n90%; sensitive probe remainder"}, 'ac', None, True),
    ({'status': 'read', 'reason': None, 'returncode': 0,
      'text': "Now drawing from 'Battery Power'\\n12%; sensitive probe remainder"}, 'battery', None, False),
    ({'status': 'read', 'reason': None, 'returncode': 0,
      'text': 'unrecognized sensitive probe remainder'}, 'unknown', None, False),
    ({'status': 'unknown', 'reason': 'TimeoutError',
      'text': 'sensitive probe remainder'}, 'unknown', 'TimeoutError', False),
    ({'status': 'unknown', 'reason': 'nonzero_exit', 'returncode': 3,
      'text': 'sensitive probe remainder'}, 'unknown', 'nonzero_exit', False),
    ({'status': 'unknown', 'reason': 'sensitive probe remainder' * 1000,
      'returncode': 2 ** 100, 'text': 'sensitive probe remainder'},
     'unknown', 'unrecognized_probe_reason', False),
    ({'status': 'read', 'reason': None, 'returncode': 1,
      'text': "Now drawing from 'AC Power'\\nsensitive probe remainder"}, 'ac', None, False),
])
def test_dispatch_power_retains_only_bounded_normalized_reading(monkeypatch, battery, source, reason, admitted):
    calls = []
    def local(argv, **kwargs):
        calls.append((argv, kwargs))
        return battery
    monkeypatch.setattr(power, '_local', local)
    monkeypatch.setattr(power.time, 'time_ns', lambda: 123456789)
    if admitted:
        reading = power.dispatch_power()
    else:
        with pytest.raises(power.DispatchPowerRefused, match='positively observed as AC') as caught:
            power.dispatch_power()
        reading = caught.value.reading
        assert json.loads(str(caught.value).split('; reading=', 1)[1]) == reading
        assert 'sensitive probe remainder' not in str(caught.value)
        assert len(str(caught.value).encode()) < 1024
    assert set(reading) == {'source', 'battery_percent', 'observed_wall_ns',
                            'probe_status', 'probe_reason', 'probe_returncode'}
    assert reading['source'] == source and reading['probe_reason'] == reason
    assert reading['observed_wall_ns'] == 123456789
    assert 'sensitive probe remainder' not in json.dumps(reading)
    assert calls == [(['/usr/bin/pmset', '-g', 'batt'], {'limit': 16384})]


def test_dispatch_power_does_not_swallow_interruption(monkeypatch):
    def interrupted(*args, **kwargs):
        raise InterruptedError('synthetic operator interruption')
    monkeypatch.setattr(power, '_local', interrupted)
    with pytest.raises(InterruptedError, match='operator interruption'):
        power.dispatch_power()
'''
with host.open('a') as stream:
    stream.write(addition)

deadline = ROOT / 'tests/test_native_attempt_deadline.py'
text = deadline.read_text()
marker = "@pytest.mark.parametrize('source', ['Battery Power', 'unrecognized'])\ndef test_unplug_after_sequence_start_refuses_public_dispatch"
assert text.count(marker) == 1
text = text[:text.index(marker)]
text = text.replace('from pathlib import Path\n', 'from pathlib import Path\nimport json\nimport sys\n', 1)
text += '''def _power_refusal_probe(source):
    if source == 'probe_failure':
        return {'status': 'unknown', 'reason': 'TimeoutError', 'text': ''}
    return {'status': 'read', 'reason': None, 'returncode': 0,
            'text': "Now drawing from '" + source + "'\\n"}


@pytest.mark.parametrize('source,persistence_failure', [
    ('Battery Power', False), ('unrecognized', False), ('probe_failure', False),
    ('Battery Power', True),
])
def test_unplug_before_reservation_keeps_attempt_unspent(tmp_path, monkeypatch, source, persistence_failure):
    from tests.test_native_shared_execution import make_case
    from data_sheets_schema import native_shared_execution_orchestration as execute
    from data_sheets_schema import native_execution_authority_v2 as authority
    from data_sheets_schema import native_execution_orchestration as engine
    from data_sheets_schema import native_pre_dispatch_timing as timing
    monkeypatch.chdir(authority.ROOT)
    traces = []
    handoff = timing._handoff
    def remember(trace):
        traces.append(trace)
        handoff(trace)
    monkeypatch.setattr(timing, '_handoff', remember)
    power.sequence_start(tmp_path / 'sequence-start.json', 'synthetic')
    case = make_case(tmp_path / 'unplug-before-reservation')
    for trace in traces:
        assert trace._persisted.wait(5)
    traces.clear()
    attempt = Path(case['value']['attempt_directory'])
    evidence = Path(case['value']['evidence_directory'])
    sidecar = attempt.parent / ('host-pre-dispatch-' + execute.c.sha(case['raw']) + '.jsonl')
    before = sidecar.read_bytes() if sidecar.exists() else b''
    if persistence_failure:
        real_open = timing.os.open
        def unavailable(path, *args, **kwargs):
            if path == sidecar or path == str(sidecar):
                raise OSError('synthetic diagnostic disk failure')
            return real_open(path, *args, **kwargs)
        monkeypatch.setattr(timing.os, 'open', unavailable)
    def forbidden(*args, **kwargs):
        pytest.fail('power refusal reached reserved runtime work')
    monkeypatch.setattr(engine, '_execute_child', forbidden)
    monkeypatch.setattr(execute, '_synthetic_runtime_observation', forbidden)
    monkeypatch.setattr(power, '_local', lambda *a, **k: _power_refusal_probe(source))
    with pytest.raises(power.DispatchPowerRefused, match='positively observed as AC') as caught:
        execute.synthetic_launch(case['raw'], **case['kwargs'])
    assert not attempt.exists() and not evidence.exists()
    assert len(traces) == 1 and traces[0]._persisted.wait(5)
    assert traces[0].disabled is persistence_failure
    current = sidecar.read_bytes() if sidecar.exists() else b''
    if persistence_failure:
        assert current == before
    else:
        assert current.startswith(before)
        rows = [json.loads(line) for line in current[len(before):].splitlines()]
        power_rows = [row for row in rows if row['boundary'] == 'reservation_power']
        assert len(power_rows) == 1 and power_rows[0]['passed'] is False
        assert all(power_rows[0][key] == value for key, value in caught.value.reading.items())
        assert not any(row['boundary'] == 'attempt_reserved' for row in rows)


@pytest.mark.parametrize('source', ['Battery Power', 'unrecognized', 'probe_failure'])
def test_unplug_after_reservation_retains_reading_without_consuming_dispatch(tmp_path, monkeypatch, source):
    from tests.test_native_shared_execution import make_case
    from data_sheets_schema import native_shared_execution_orchestration as execute
    from data_sheets_schema import native_execution_authority_v2 as authority
    from data_sheets_schema import native_execution_orchestration as engine
    monkeypatch.chdir(authority.ROOT)
    case = make_case(tmp_path / 'unplug-after-reservation')
    original_execute = engine._execute_child
    original_power = power.dispatch_power
    readings, refusals, entered = [], [], []
    def observe_power():
        try:
            reading = original_power()
        except power.DispatchPowerRefused as exc:
            refusals.append(exc)
            raise
        readings.append(reading)
        return reading
    monkeypatch.setattr(power, 'dispatch_power', observe_power)
    def no_native_dispatch(controls, argv, **kwargs):
        entered.append(True)
        # Keep the actual reviewed transport, timer, verify_launch and error
        # handling. Only switch the synthetic power reading before admission.
        runner = sys.modules['run_native_canary']
        real_popen = runner.subprocess.Popen
        def popen(command, *args, **named):
            if list(command) == list(argv):
                pytest.fail('unplugged host reached child dispatch')
            return real_popen(command, *args, **named)
        with monkeypatch.context() as patch:
            patch.setattr(power, '_local', lambda *a, **k: _power_refusal_probe(source))
            patch.setattr(runner.subprocess, 'Popen', popen)
            return original_execute(controls, argv, **kwargs)
    monkeypatch.setattr(engine, '_execute_child', no_native_dispatch)
    result = execute.synthetic_launch(case['raw'], **case['kwargs'])
    assert entered == [True] and len(readings) == len(refusals) == 1
    assert readings[0]['source'] == 'ac'
    assert result['state'] == 'failed' and result['child_exit_code'] is None
    assert result['first_stop'] == 'dispatch power refused: ' + str(refusals[0])
    assert result['gates']['first_stop'] == {
        'checked': True, 'passed': False, 'reason': result['first_stop']}
    assert result['subscription_guard']['dispatched'] is False
    assert result['subscription_guard']['dispatched_at'] is None
    attempt = Path(case['value']['attempt_directory'])
    assert attempt.is_dir() and not (attempt / 'subscription-dispatched.json').exists()
    assert (attempt / 'transcript.jsonl').read_bytes() == b''
    assert execute.read_final(case['raw']) == result


def test_slow_power_probe_cannot_age_an_already_checked_reservation_margin(tmp_path, monkeypatch):
    from tests.test_native_shared_execution import make_case
    from data_sheets_schema import native_shared_execution_orchestration as execute
    from data_sheets_schema import native_execution_authority_v2 as authority
    from data_sheets_schema import native_execution_orchestration as engine
    from data_sheets_schema import native_subscription_guard_v2 as subscription
    monkeypatch.chdir(authority.ROOT)
    case = make_case(tmp_path / 'slow-power-probe')
    guard = json.loads(Path(case['kwargs']['subscription_guard_path']).read_bytes())
    captured = subscription._timestamp(guard['captured_at'], 'synthetic capture time')
    ticks = [captured + guard['max_age_seconds'] - guard['pre_reservation_margin_seconds'] - 1]
    monkeypatch.setattr(subscription, '_now', lambda: ticks[0])
    original = power.dispatch_power
    probes = []
    def slow_probe():
        probes.append(True)
        result = original()
        ticks[0] += 2  # Still fresh for dispatch, but below the required reserve margin.
        return result
    monkeypatch.setattr(power, 'dispatch_power', slow_probe)
    monkeypatch.setattr(engine, '_execute_child',
        lambda *a, **k: pytest.fail('expired preparation margin reached transport'))
    with pytest.raises(ValueError, match='pre-reservation freshness margin is insufficient'):
        execute.synthetic_launch(case['raw'], **case['kwargs'])
    assert probes == [True]
    assert not Path(case['value']['attempt_directory']).exists()
    assert not Path(case['value']['evidence_directory']).exists()
'''
deadline.write_text(text)

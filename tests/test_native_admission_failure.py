"""Real failure publisher and fake IOKit; no native/model execution.

Requires the lead's controller pin admission after the source change.
"""
import os

import pytest

from tests.test_native_execution_registration_v2 import isolated_modules  # noqa: F401

pytestmark = pytest.mark.usefixtures('isolated_modules')


def test_stalled_launch_verification_refuses_dispatch_releases_and_publishes(tmp_path, monkeypatch):
    from tests.test_native_execution import make_native_case, fake_observation
    from data_sheets_schema import native_execution as execute
    from data_sheets_schema import native_execution_authority as authority
    from data_sheets_schema.native_elapsed import elapsed_ns
    monkeypatch.chdir(authority.ROOT)
    case = make_native_case(tmp_path / 'stalled-admission', mode='no_correction', awake=True)
    monkeypatch.setattr(execute, '_platform', lambda: 'darwin')
    monkeypatch.setattr(execute, '_probe_runtime', fake_observation)
    fifo = tmp_path / 'verification-no-writer'
    os.mkfifo(fifo)
    unchanged = execute._unchanged
    calls, entered, active, released = [], [], set(), []
    advanced = [0]
    def verify(value, raw, authorization):
        calls.append(True)
        if len(calls) == 3:  # The real verify_launch callback, with IOKit held.
            assert len(active) == 3
            entered.append(True)
            advanced[0] = 901 * 10**9  # Expire only after verification is entered.
            descriptor = os.open(fifo, os.O_RDONLY)
            os.close(descriptor)
            pytest.fail('stalled verification returned')
        return unchanged(value, raw, authorization)
    monkeypatch.setattr(execute, '_unchanged', verify)
    class FakeIOKit:
        def create(self, kind):
            identity = len(active) + 1
            active.add(identity)
            return identity
        def release(self, identity):
            active.remove(identity)
            released.append(identity)
            return 0
    with authority.loaded_dependencies(case['value']['dependencies']) as modules:
        monkeypatch.setattr(modules['run_direct_canary_awake'], '_IOKit', FakeIOKit)
        # Keep the real 900-second bound and signal handler. The clock jump
        # avoids aging the expensive fixture/setup under a short test timeout.
        monkeypatch.setattr(modules['run_native_canary'], 'elapsed_ns', lambda: elapsed_ns() + advanced[0])
        result = execute.launch(case['raw'], **case['kwargs'])
    assert entered == [True]
    assert not active and len(released) == 3
    assert result['state'] == 'failed' and result['child_exit_code'] is None
    assert result['first_stop'] == 'native admission deadline elapsed; child was not dispatched'
    assert result['keep_awake']['releases']
    assert (case['root'] / 'native-attempt/transcript.jsonl').read_bytes() == b''
    assert execute.read_final(case['raw']) == result


def test_shared_engine_stalled_admission_publishes_and_stops_timing(tmp_path, monkeypatch):
    import json
    from tests.test_native_shared_execution import make_case
    from data_sheets_schema import native_shared_execution_orchestration as execute
    from data_sheets_schema import native_execution_orchestration as engine
    from data_sheets_schema import native_execution_authority_v2 as authority
    from data_sheets_schema import native_pre_dispatch_timing as timing
    from data_sheets_schema.native_elapsed import elapsed_ns
    monkeypatch.chdir(authority.ROOT)
    case = make_case(tmp_path / 'shared-stalled-admission')
    fifo = tmp_path / 'verification-no-writer'
    os.mkfifo(fifo)
    original = engine._execute_child
    entered = []
    traces = []
    handoff = timing._handoff
    def remember(trace):
        traces.append(trace)
        handoff(trace)
    monkeypatch.setattr(timing, '_handoff', remember)
    def stalled(controls, *args, **kwargs):
        runner = controls['run_native_canary']
        advance = [0]
        original_verify = kwargs['verify_launch']
        def verify():
            entered.append(True)
            # Exercise the actual late registration.verified call sites. If
            # finish() stops sealing the trace, these rows violate the check.
            original_verify()
            advance[0] = 901 * 10**9
            fd = os.open(fifo, os.O_RDONLY)
            os.close(fd)
            pytest.fail('stalled shared verification returned')
        with monkeypatch.context() as patch:
            patch.setattr(runner, 'elapsed_ns', lambda: elapsed_ns() + advance[0])
            patch.setattr(runner.subprocess, 'Popen', lambda *a, **k: pytest.fail('admission dispatched'))
            kwargs['verify_launch'] = verify
            return original(controls, *args, **kwargs)
    monkeypatch.setattr(engine, '_execute_child', stalled)
    result = execute.synthetic_launch(case['raw'], **case['kwargs'])
    assert entered == [True]
    assert result['state'] == 'failed' and result['child_exit_code'] is None
    assert result['first_stop'] == 'native admission deadline elapsed; child was not dispatched'
    assert (case['root'] / 'native-attempt/transcript.jsonl').read_bytes() == b''
    assert execute.read_final(case['raw']) == result
    assert len(traces) == 1
    assert traces[0]._persisted.wait(5)  # Only after outcome and readback.
    path = case['root'] / ('host-pre-dispatch-' + execute.c.sha(case['raw']) + '.jsonl')
    rows = [json.loads(line) for line in path.read_bytes().splitlines()]
    reserved = next(i for i, row in enumerate(rows) if row['boundary'] == 'attempt_reserved')
    assert all(row['boundary'] == 'reservation' and row.get('phase') == 'end'
               for row in rows[reserved + 1:])

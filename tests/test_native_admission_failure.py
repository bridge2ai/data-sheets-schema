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
    monkeypatch.chdir(authority.ROOT)
    case = make_native_case(tmp_path / 'stalled-admission', mode='no_correction', awake=True)
    monkeypatch.setattr(execute, '_platform', lambda: 'darwin')
    monkeypatch.setattr(execute, '_probe_runtime', fake_observation)
    fifo = tmp_path / 'verification-no-writer'
    os.mkfifo(fifo)
    unchanged = execute._unchanged
    calls, entered, active, released = [], [], set(), []
    def verify(value, raw, authorization):
        calls.append(True)
        if len(calls) == 3:  # The real verify_launch callback, with IOKit held.
            assert len(active) == 3
            entered.append(True)
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
        # Shorten only this test's alarm; production remains 900 seconds.
        monkeypatch.setattr(modules['run_native_canary'], 'ADMISSION_SECONDS', 2)
        result = execute.launch(case['raw'], **case['kwargs'])
    assert entered == [True]
    assert not active and len(released) == 3
    assert result['state'] == 'failed' and result['child_exit_code'] is None
    assert result['first_stop'] == 'native admission deadline elapsed; child was not dispatched'
    assert result['keep_awake']['releases']
    assert (case['root'] / 'native-attempt/transcript.jsonl').read_bytes() == b''
    assert execute.read_final(case['raw']) == result

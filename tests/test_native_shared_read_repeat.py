"""Repeated delivery uses real tool evidence but grants no second authority."""
from types import SimpleNamespace
import pytest

from data_sheets_schema import native_shared_capture_orchestration as host
from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_observations as observed
from data_sheets_schema import native_shared_stage as stage
from tests.native_shared_captured_fixture import (
    _events, _prefix, join_response, v2_case,
)
from tests.test_native_shared_stages import case, receipt_answer, supplied, publish
from tests.test_native_shared_observations import initial, SESSION, POLICY


def test_read_write_read_preserves_first_delivery_across_journal_change(case, monkeypatch):
    case = v2_case(case)
    current = stage.prepare_next(*case)
    # This fixture starts before request publication; publish the real proposal.
    case = (*case[:3], publish(case[3], current))
    current = stage.prepare_next(*case)
    _, observations, streams = join_response(case, current, receipt_answer(case))
    rows, controls = streams
    reads, read_control = _events('Read', current.request, 'second-read')
    _, _, runtime = initial()
    trace = observed.Trace(_prefix('transcript', rows + reads),
        _prefix('control', controls + read_control), session_id=SESSION, policy=POLICY, runtime=runtime)
    run = SimpleNamespace(decision=lambda: current, trace=lambda: trace,
        observations=observations,
        history=SimpleNamespace(journal=SimpleNamespace(pin=SimpleNamespace(sha256='f' * 64))))
    monkeypatch.setattr(host, '_persist_observation',
        lambda *args: pytest.fail('a repeated complete Read created another authority'))
    host.observe_request_read(run, 'second-read')
    assert sum(c.strict_json(item.raw)['observation_type'] == 'request_read' for item in observations) == 1

"""Fixed gate routing retains the old public runtime-observation fault seam."""
from pathlib import Path
from types import SimpleNamespace

import pytest

from data_sheets_schema import native_execution_gates as legacy
from data_sheets_schema import native_gate_engine as engine
from tests.test_native_execution_gates import selected


def test_unknown_gate_contract_refuses_before_any_adapter_import():
    with pytest.raises(ValueError, match='unknown private'):
        engine.check(None, None, None, None, kind='caller.module', exit_code=None,
            shutdown=None, live=None, first_stop=None, runtime_authority=None, keep_awake=None)


def test_legacy_public_check_retains_call_time_runtime_and_cleanup_seams(monkeypatch):
    prepared, runtime = selected()
    runtime.update(attempt_directory='/synthetic/attempt', keep_awake={'policy': 'not_applicable'})
    prepared['snapshot'] = SimpleNamespace(read=lambda path, role: b'captured raw observation')
    calls = []
    def runtime_check(raw, admitted, expected):
        calls.append(('runtime', raw, admitted, expected))
        return {'passed': False, 'diagnostic': 'selected injected runtime fault'}
    def cleanup_check(raw, observed, policy):
        calls.append(('cleanup', raw, observed, policy))
        return {'passed': False, 'diagnostic': 'selected injected cleanup fault'}
    monkeypatch.setattr(legacy, 'runtime_observation_result', runtime_check)
    monkeypatch.setattr(legacy, 'cleanup_result', cleanup_check)
    out = legacy.check(prepared, {}, runtime, {'run_direct_canary': SimpleNamespace()}, exit_code=0,
        shutdown=None, live={}, first_stop=None, runtime_authority={'passed': False},
        keep_awake={'passed': False}, keep_awake_raw=b'actual cleanup', runtime_authority_expected={'selected': True})
    assert set(out) == set(legacy.GATES)
    assert out['runtime_authority']['diagnostic'] == 'selected injected runtime fault'
    assert out['keep_awake']['diagnostic'] == 'selected injected cleanup fault'
    assert calls == [('runtime', b'captured raw observation', {'passed': False}, {'selected': True}),
                     ('cleanup', b'actual cleanup', {'passed': False}, {'policy': 'not_applicable'})]

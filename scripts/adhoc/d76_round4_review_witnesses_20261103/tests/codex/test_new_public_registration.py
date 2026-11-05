"""PR #5213 public native registration boundary probe, 2026-11-02.
Inputs: existing valid offline native fixture. Outputs: scratch pytest evidence.
Tests direct documented public registration APIs at both heads without providers.
"""
from pathlib import Path
import pytest
from data_sheets_schema import native_attribution_registration as registration
from tests.test_native_source_attribution import case  # noqa: F401
from tests.test_source_attribution_preflight import inputs  # noqa: F401


@pytest.mark.parametrize('entry', ['registration', 'write_registration'])
def test_native_registration_refuses_drift_before_reading_input_pins(case, monkeypatch, tmp_path, entry):
    spec = case[0]
    monkeypatch.chdir(spec.bundle.parent)
    assert 'instruction' in vars(spec), 'calibrate a normal already-rendered spec'
    spec.bundle = Path(spec.bundle.name)
    reached = []
    def read_inputs(*args):
        reached.append('input-pin-read')
        raise AssertionError('native registration input read preceded D76 guard')
    monkeypatch.setattr(registration, '_inputs', read_inputs)
    destination = tmp_path / 'must-not-publish.json'
    error = None
    try:
        if entry == 'registration':
            registration.registration(spec)
        else:
            registration.write_registration(spec, destination)
    except BaseException as exc:
        error = exc
    assert not reached, (reached, repr(error))
    assert not destination.exists()
    assert isinstance(error, ValueError) and 'registered input' in str(error), repr(error)

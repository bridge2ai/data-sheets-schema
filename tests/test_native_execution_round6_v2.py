"""R9-3 capture identity regressions, offline synthetic inputs, 2026-11-08."""
import importlib.util
import sys

import pytest

from data_sheets_schema import native_execution_registration_v2 as registration
from data_sheets_schema import native_shared_contract as contract
from tests.test_native_execution_registration_v2 import inputs, isolated_modules
from tests.test_native_shared_render import native_spec
from tests.test_native_shared_selection import declaration


@pytest.mark.parametrize('replace_contract', [False, True])
def test_verify_preparer_uses_current_runtime_capture(inputs, monkeypatch, replace_contract):
    """Replace the reader's class while retaining A's old imported reader."""
    import data_sheets_schema as package
    from data_sheets_schema import native_shared_render as render
    from data_sheets_schema import native_shared_evidence as evidence
    old_reader = registration.read_regular
    if replace_contract:
        name = contract.__name__
        spec = importlib.util.spec_from_file_location(name, contract.__file__)
        current = importlib.util.module_from_spec(spec)
        monkeypatch.setitem(sys.modules, name, current)
        spec.loader.exec_module(current)
        # This fixture changes only the runtime carrier's identity.
        current.NativeSelectionCapture = contract.NativeSelectionCapture
        monkeypatch.setattr(package, 'native_shared_contract', current)
        monkeypatch.setattr(render, 'c', current)
        name = evidence.__name__
        spec = importlib.util.spec_from_file_location(name, evidence.__file__)
        evidence = importlib.util.module_from_spec(spec)
        monkeypatch.setitem(sys.modules, name, evidence)
        spec.loader.exec_module(evidence)
        monkeypatch.setattr(package, 'native_shared_evidence', evidence)
        assert type(old_reader(str(inputs['runtime_path']), 'runtime_declaration',
            max_bytes=contract.HARD_LIMITS['input_bytes']).captured) is not current.CapturedArtifact
    else:
        current = contract
    seen = []
    reader = evidence.read_regular

    def read(*args, **kwargs):
        result = reader(*args, **kwargs)
        if args[1] == 'runtime_declaration':
            assert type(result.captured) is current.CapturedArtifact
            seen.append(result.captured)
        return result

    monkeypatch.setattr(evidence, 'read_regular', read)
    envelope = registration.prepare(inputs['selection'], inputs['runtime_path'], **inputs['kwargs'])
    body = registration.verify_preparer(contract.canonical(envelope), job_id=inputs['kwargs']['job_id'])
    assert body == envelope['registration']
    assert '# Model: historical-native-fixture-model' in body['instruction']
    assert len(seen) == 4  # initial and stability read in prepare and verify_preparer
    assert registration.read_regular is old_reader

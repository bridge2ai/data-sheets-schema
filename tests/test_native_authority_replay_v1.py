"""Saved M7 bytes remain version-specific without environment-gated CI skips."""
import json
from pathlib import Path
import pytest
from data_sheets_schema import native_attribution_registration_v2 as v2
from data_sheets_schema import native_attribution_registration as v1

FIXTURE = Path(__file__).parent/'fixtures/native_u2_m7'

def test_saved_m7_record_refuses_v2():
    raw = (FIXTURE/'registration.json').read_bytes()
    evidence = json.loads((FIXTURE/'verified.json').read_bytes())
    assert v1._sha(raw) == evidence['registration_sha256']
    assert v1._sha((FIXTURE/'composition.json').read_bytes()) == evidence['composition_sha256']
    assert json.loads(raw)['checker_source_tree_sha256'] != v1._code_pins()
    with pytest.raises(ValueError, match='unsupported native attribution registration version'):
        v2.verified(raw)

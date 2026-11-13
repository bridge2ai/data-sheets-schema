"""Build a synthetic registration and recheck it without dispatch or reservations."""
from pathlib import Path
import pytest
from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_registration_orchestration as registration
from tests.test_native_shared_execution import make_case
from tests.test_native_execution_registration_v2 import isolated_modules


def test_dispatch_recheck_rejects_changed_environment(tmp_path, monkeypatch, isolated_modules):
    monkeypatch.chdir(registration.authority.ROOT)
    case = make_case(tmp_path / 'SYNTHETIC-environment-only')
    body = case['value']
    assert body['kind'] == 'd4d_native_shared_execution_registration_v3'
    assert registration._recheck_verified(case['raw'], body) == body
    preparation = c.strict_json(body['preparation_raw_json'].encode())['registration']
    path = Path(preparation['environment_manifest']['path'])
    path.chmod(0o600)
    path.write_bytes(path.read_bytes() + b'\n')
    with pytest.raises(ValueError, match='environment manifest differs'):
        registration._recheck_verified(case['raw'], body)
    assert not Path(body['attempt_directory']).exists()
    assert not Path(body['evidence_directory']).exists()

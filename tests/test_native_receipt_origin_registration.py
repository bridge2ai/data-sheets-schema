"""Actual offline registrations, with existing synthetic permission fixtures.

No launch, authentication, token-count, model, provider or helper execution.
The underlying fixtures bind real local package/schema/source identities.
"""
from copy import deepcopy
from pathlib import Path
import socket
import subprocess

import pytest

from data_sheets_schema import native_receipt_origin as origin
from data_sheets_schema import native_attribution_registration as encoding
from data_sheets_schema import native_attempt_supervisor as supervisor
from data_sheets_schema import native_execution_registration as direct
from data_sheets_schema import native_shared_registration as shared
from data_sheets_schema import native_execution_authority as authority
from tests.test_native_attempt_supervisor import make_case
from tests.test_native_execution import make_native_case
from tests.test_native_shared_registration import execution
from tests.test_native_shared_controller import bound, native_spec, declaration


@pytest.fixture(autouse=True)
def no_dispatch(monkeypatch):
    original = subprocess.Popen
    def git_only(argv, *args, **kwargs):
        assert list(argv) == ['git', 'rev-parse', 'HEAD'], 'only the existing source-identity Git read is allowed'
        return original(argv, *args, **kwargs)
    monkeypatch.setattr(subprocess, 'Popen', git_only)
    monkeypatch.setattr(socket.socket, 'connect', lambda *a, **k: pytest.fail('network not allowed'))
    monkeypatch.chdir(authority.ROOT)


def check_registration(module, args, default, paths):
    zero = module.registration(**args, receipt_origin_version=0)
    assert encoding._encoded(zero) == encoding._encoded(default)
    assert origin.KEY not in zero
    one = module.registration(**args, receipt_origin_version=1)
    expected = origin.declaration(str(args['attempt_directory']), paths)
    assert one == {**default, origin.KEY: expected}
    assert module.verified(encoding._encoded(one)) == one
    for version in (0, True, None, 2):
        damaged = deepcopy(one)
        damaged[origin.KEY]['version'] = version
        with pytest.raises(ValueError, match='receipt-origin'):
            module.verified(encoding._encoded(damaged))
    for bad in (None, {**expected, 'unregistered': True}):
        damaged = deepcopy(one); damaged[origin.KEY] = bad
        with pytest.raises(ValueError, match='receipt-origin'):
            module.verified(encoding._encoded(damaged))
    damaged = deepcopy(one); damaged[origin.KEY]['receipt_path'] = '/other/receipt.yaml'
    with pytest.raises(ValueError, match='differs'):
        module.verified(encoding._encoded(damaged))
    assert not Path(args['attempt_directory']).exists()
    assert not Path(args['evidence_directory']).exists()


def test_actual_supervisor_registration_optin_preserves_default(tmp_path):
    case = make_case(tmp_path / 'supervisor')
    value = case['value']
    args = {'composition_path': value['composition'], 'fixture_path': value['fixture'],
        **{key: value[key] for key in ('attempt_id', 'attempt_directory', 'evidence_directory',
                                      'deadline_seconds', 'synthetic_runtime')}}
    check_registration(supervisor, args, value, case['spec']._agentic_artifact_paths)


def test_actual_direct_registration_optin_preserves_default(tmp_path):
    case = make_native_case(tmp_path / 'direct')
    value = case['value']
    args = {'composition_path': value['composition'], 'system_path': value['system_path'],
        'permission_probe_path': value['permission_probe'],
        **{key: value[key] for key in ('attempt_id', 'attempt_directory', 'evidence_directory', 'runtime')}}
    check_registration(direct, args, value, case['spec']._agentic_artifact_paths)


def test_actual_native26_registration_optin_preserves_default(execution):
    args, selected, _ = execution
    value = shared.registration(**args)
    spec = shared._selection(selected and Path(args['composition_path']).read_bytes())[1]
    check_registration(shared, args, value, spec._agentic_artifact_paths)

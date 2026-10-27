"""Real offline E reconstruction with explicitly fabricated saved probe data.

No native/auth/provider invocation is permitted. Ordinary local Git identity
queries are the only subprocess calls, and no attempt is reserved or launched.
"""
from pathlib import Path
import subprocess

import pytest

from tests.test_native_shared_controller import bound, native_spec, declaration
from tests.test_native_shared_permissions import fabricated_manifest
from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_controller as composition
from data_sheets_schema import native_shared_registration as registration
from data_sheets_schema import native_shared_policy as policy
from data_sheets_schema import native_execution_authority as authority

_SUBPROCESS = {name: getattr(subprocess, name) for name in ('run', 'Popen', 'check_output')}


@pytest.fixture
def execution(bound, tmp_path, monkeypatch):
    spec, runtime, instruction = bound
    for name, function in _SUBPROCESS.items():
        def git_only(argv, *a, _fn=function, **k):
            assert isinstance(argv, (list, tuple)) and argv[0] == 'git', 'native/auth/provider subprocess forbidden'
            return _fn(argv, *a, **k)
        monkeypatch.setattr(subprocess, name, git_only)
    selected = composition.compose(spec, runtime_path=runtime, instruction_path=instruction, max_draft_checks=3)
    comp = tmp_path.resolve() / 'composition.json'; comp.write_bytes(c.canonical(selected))
    system = tmp_path.resolve() / 'system.txt'; system.write_bytes(b'Explicit software test only.\n')
    attempt = tmp_path.resolve() / 'attempt'
    output = tmp_path.resolve() / 'evidence'
    dependencies = authority.dependency_identity()
    expected = registration.permission_expectation(c.strict_json(runtime.read_bytes()), selected, spec,
        system.read_text() + policy.command_guidance(selected['policy']), attempt/'cli_config', dependencies)
    cap = spec._native_shared_generation_capture
    manifest = fabricated_manifest(expected, cap.document(), tmp_path.resolve()/'invented-probe', spec.bundle.read_bytes())
    probe = tmp_path.resolve() / 'fabricated-observations.json'; probe.write_bytes(c.canonical(manifest))
    args = {'composition_path': comp, 'system_path': system, 'permission_probe_path': probe,
        'attempt_id': 'attempt', 'attempt_directory': attempt, 'evidence_directory': output, 'max_draft_checks': 3}
    return args, selected, expected


def test_closed_registration_checks_actual_selected_policy_and_does_not_reserve(execution):
    args, selected, expected = execution
    value = registration.registration(**args)
    raw = c.canonical(value)
    assert registration.verified(raw) == value
    assert value['kind'] == c.KINDS['execution']
    assert value['selection_sha256'] == selected['selection_sha256']
    assert value['runtime_declaration_sha256'] == selected['runtime_sha256']
    assert value['permission_expected_sha256'] == c.sha(c.canonical(expected))
    assert value['permission_observations']['passed'] is True
    assert value['max_draft_checks'] == selected['max_draft_checks'] == 3
    assert value['runtime'] == c.strict_json(selected['runtime_raw_json'].encode())
    assert value['argv'].count('--input-format') == 1
    assert any(row['module'] == 'data_sheets_schema.cli.__main__' for row in expected['production_sources'])
    assert any(row['module'] == 'data_sheets_schema.native_shared_policy' for row in expected['production_sources'])
    assert not args['attempt_directory'].exists() and not args['evidence_directory'].exists()
    assert not Path(c.parse_selection(selected['selection_raw_json'].encode())['stage_root']).exists()


def test_registration_refuses_separate_count_and_rehashed_permission_contradiction(execution):
    args, selected, expected = execution
    with pytest.raises(ValueError, match='allowance differs'):
        registration.registration(**{**args, 'max_draft_checks': 4})
    doc = c.strict_json(args['permission_probe_path'].read_bytes(), max_bytes=c.HARD_LIMITS['permission_wire_bytes'])
    doc['binding']['commands']['draft'] += ' --unregistered'
    args['permission_probe_path'].write_bytes(c.canonical(doc))
    with pytest.raises(ValueError): registration.registration(**args)
    assert not args['attempt_directory'].exists() and not args['evidence_directory'].exists()

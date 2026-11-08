"""Real offline E reconstruction with explicitly fabricated saved probe data.

No native/auth/provider invocation is permitted. Ordinary local Git identity
queries are the only subprocess calls, and no attempt is reserved or launched.
"""
from pathlib import Path
import subprocess
from copy import deepcopy

import pytest

from tests.test_native_shared_controller import bound, native_spec, declaration, synthetic_declaration
from tests.test_native_shared_permissions import fabricated_manifest
from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_controller_orchestration as composition
from data_sheets_schema import native_shared_registration_orchestration as registration
from data_sheets_schema import native_shared_policy as policy
from data_sheets_schema import native_execution_authority_v2 as authority
from data_sheets_schema import native_execution_registration_v2 as execution_v2
from tests.test_native_execution_registration_v2 import inputs, isolated_modules
from tests.utils.native_shared_consumer_scope import command_guidance, observe_consumer_calls

_SUBPROCESS = {name: getattr(subprocess, name) for name in ('run', 'Popen', 'check_output')}


@pytest.fixture
def execution(bound, tmp_path, monkeypatch):
    source, prepared, preparation_raw, instruction = bound
    runtime = source['runtime_path']
    for name, function in _SUBPROCESS.items():
        def git_only(argv, *a, _fn=function, **k):
            assert isinstance(argv, (list, tuple)) and Path(argv[0]).name == 'git', 'native/auth/provider subprocess forbidden'
            return _fn(argv, *a, **k)
        monkeypatch.setattr(subprocess, name, git_only)
    selected = composition.compose(preparation_raw, instruction_path=instruction)
    _, spec, cap = composition.reconstruct_composition(c.canonical(selected))
    comp = tmp_path.resolve() / 'composition.json'; comp.write_bytes(c.canonical(selected))
    system = tmp_path.resolve() / 'system.txt'; system.write_bytes(b'Explicit software test only.\n')
    attempt = tmp_path.resolve() / 'attempt'
    output = tmp_path.resolve() / 'evidence'
    dependencies = authority.dependency_identity()
    expected = registration.permission_expectation(c.strict_json(runtime.read_bytes()), selected, spec,
        system.read_text() + command_guidance(selected['policy']), attempt/'cli_config', dependencies)
    manifest = fabricated_manifest(expected, cap.document(), tmp_path.resolve()/'invented-probe', spec.bundle.read_bytes())
    probe = tmp_path.resolve() / 'fabricated-observations.json'; probe.write_bytes(c.canonical(manifest))
    args = {'composition_path': comp, 'system_path': system, 'permission_probe_path': probe,
        'attempt_id': 'attempt', 'attempt_directory': attempt, 'evidence_directory': output, 'max_draft_checks': prepared['registration']['max_draft_checks']}
    return args, selected, expected


def test_closed_registration_checks_actual_selected_policy_and_does_not_reserve(execution):
    args, selected, expected = execution
    targets = {('native_shared_registration', name): ()
               for name in ('_registration_body', 'command')}
    with observe_consumer_calls(targets) as calls:
        value = registration.registration(**args)
    assert set(targets) <= {key for key, _ in calls}
    raw = c.canonical(value)
    body = value['registration']
    assert value['authority_version'] == 2
    assert registration.verified_v2_body(c.canonical(body),
        preparation_raw=body['preparation_raw_json'].encode()) == body
    assert registration.verified(raw) == body
    value = body
    assert value['kind'] == execution_v2.EXECUTION_KIND
    assert value['selection_sha256'] == selected['selection_sha256']
    assert value['runtime_declaration_sha256'] == selected['runtime_sha256']
    assert value['permission_expected_sha256'] == c.sha(c.canonical(expected))
    assert value['permission_observations']['passed'] is True
    assert value['max_draft_checks'] == selected['max_draft_checks'] == 2
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


@pytest.mark.parametrize('change', ['unknown', 'schema_bool', 'legacy', 'missing_gate',
    'gate_order', 'preparation', 'runtime_budget', 'permission_verdict', 'argv', 'environment',
    'selection', 'system', 'dependency'])
def test_consumer_rederives_every_closed_body_field(execution, change, monkeypatch):
    args, _, _ = execution
    envelope = registration.registration(**args)
    body = deepcopy(envelope['registration'])
    preparation_raw = body['preparation_raw_json'].encode()
    if change == 'unknown': body['accepted'] = True
    elif change == 'schema_bool': body['schema_version'] = True
    elif change == 'legacy': body.update(kind='d4d_native_shared_execution_registration', version=1)
    elif change == 'missing_gate': body['execution_gates'].pop()
    elif change == 'gate_order': body['execution_gates'].reverse()
    elif change == 'preparation': body['preparation_sha256'] = '0' * 64
    elif change == 'runtime_budget': body['runtime']['budget_guard_usd'] = '2'
    elif change == 'permission_verdict': body['permission_observations']['cases'] = []
    elif change == 'argv': body['argv'].append('--unregistered')
    elif change == 'environment': body['environment']['ANTHROPIC_API_KEY'] = 'not-a-key'
    elif change == 'selection': body['selection']['label'] = 'foreign'
    elif change == 'system': body['effective_system'] += ' changed'
    else: body['dependencies']['version'] = 1
    monkeypatch.setattr(execution_v2, 'verified', lambda *_: pytest.fail('recursive outer verifier'))
    with pytest.raises(ValueError):
        registration.verified_v2_body(c.canonical(body), preparation_raw=preparation_raw)
    assert not args['attempt_directory'].exists()


def test_consumer_does_not_cache_permission_acceptance(execution, monkeypatch):
    args, _, _ = execution
    body = registration.registration(**args)['registration']
    raw = c.canonical(body)
    prepared = body['preparation_raw_json'].encode()
    assert registration.verified_v2_body(raw, preparation_raw=prepared) == body
    target = ('native_shared_permissions', 'verify_saved_probe')
    with observe_consumer_calls({target: ()},
            refuse=(target, ValueError('fresh permission classification refused'))) as calls:
        with pytest.raises(ValueError, match='fresh permission'):
            registration.verified_v2_body(raw, preparation_raw=prepared)
    assert [key for key, _ in calls] == [target]


def test_paths_include_stage_and_refuse_spent_or_overlapping_reservations(execution):
    args, selected, _ = execution
    body = registration.registration(**args)['registration']
    paths = registration.execution_paths_v2(body, fresh=True, extra_protected=())
    stage_root = Path(c.parse_selection(selected['selection_raw_json'].encode())['stage_root'])
    assert stage_root in paths and args['attempt_directory'] in paths
    with pytest.raises(ValueError, match='overlaps'):
        registration.execution_paths_v2(body, fresh=True, extra_protected=[str(stage_root / 'input')])
    args['attempt_directory'].mkdir()
    with pytest.raises(ValueError, match='spent'):
        registration.execution_paths_v2(body, fresh=True, extra_protected=())


def test_outer_route_refuses_bare_and_v1_envelopes(execution):
    args, _, _ = execution
    envelope = registration.registration(**args)
    for bad in (envelope['registration'], {**envelope, 'authority_version': 1},
                {**envelope, 'authority_version': True}):
        with pytest.raises(ValueError):
            registration.verified(c.canonical(bad))


@pytest.mark.parametrize('missing_module', [
    'native_shared_execution', 'native_gate_engine', 'native_shared_schema_gates'])
def test_outer_verifier_refuses_missing_fixed_gate_implementation_before_effects(execution, monkeypatch, missing_module):
    import builtins
    args, selected, _ = execution
    raw = c.canonical(registration.registration(**args))
    original = builtins.__import__
    def missing_gate(name, globals=None, locals=None, fromlist=(), level=0):
        if name == missing_module and level == 1:
            raise ImportError('deliberately unavailable fixed gate: ' + missing_module)
        return original(name, globals, locals, fromlist, level)
    monkeypatch.setattr(builtins, '__import__', missing_gate)
    with pytest.raises(ValueError, match='gate implementation is incomplete') as refused:
        registration.verified(raw)
    assert str(refused.value.__cause__) == 'deliberately unavailable fixed gate: ' + missing_module
    assert not args['attempt_directory'].exists()
    assert not args['evidence_directory'].exists()
    assert not Path(c.parse_selection(selected['selection_raw_json'].encode())['stage_root']).exists()

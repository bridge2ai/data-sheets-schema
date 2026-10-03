"""Registered successor selection; invented local inputs, never paid calls."""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import socket

import pytest

from data_sheets_schema import api_runner as api, shared_generation as sg, receipt_completion as rc
from data_sheets_schema import receipt_completion_policy as policy
from data_sheets_schema.schema_snapshot import capture_schema
from data_sheets_schema.resources import resource_path
from tests.test_generation_manifest_identity import external  # noqa: F401


def registration_for(spec):
    """An explicit synthetic registration; not a recommended experiment/cap."""
    import yaml
    if spec.manifest is not None:
        metadata = yaml.safe_load(spec.manifest.read_bytes())
        for row in metadata['projects'][spec.project]['sources']:
            row['processed_file'] = 'protocol'
        spec.manifest.write_text(yaml.safe_dump(metadata))
    directory = spec.bundle.parent
    context = directory / 'generation-context.json'
    context.write_bytes(sg.canonical({'format': 'omission_context_v1', 'root_class': 'Dataset',
        'scopes': [{'owner': '', 'referent': 'External Cohort', 'release': 'synthetic',
                    'scope': 'Only the supplied fictional source.'}],
        'source_policy': {'priority': ['protocol'], 'basis': 'Synthetic fixture only.'}, 'vocabulary': {}}))
    settings = api._model_settings()
    path = directory / 'shared-registration.json'
    reg = {'format': sg.FORMAT, 'registration_id': 'invented-local-test', 'registration_path': str(path),
        'run': {key: getattr(spec, key) for key in ('project', 'arm', 'method', 'label')},
        'selection': sg.descriptor(), 'inputs': {'project': spec.project,
            'bundle': sg.file_pin(spec.bundle), 'chunk_manifest': sg.file_pin(spec.chunk_manifest),
            'source_manifest': sg.file_pin(spec.manifest) if spec.manifest else None,
            'context': sg.file_pin(context), 'profile': {'name': spec.profile, 'basis': spec.profile_basis},
            'full_schema': sg.schema_pin(capture_schema(api.FULL_SCHEMA_PATH, strict=True)),
            'core_schema': sg.schema_pin(capture_schema(api.CORE_SCHEMA_PATH, strict=True))},
        'runtime': {'provider': 'Synthetic offline fixture', 'base_url': 'https://example.invalid',
            'model': settings['name'], 'temperature': settings['temperature'] if api.accepts_temperature(settings['name']) else None,
            'thinking': settings.get('thinking'), 'effort': settings.get('effort'),
            'config': sg.file_pin(resource_path(settings['config_path'])) if settings.get('config_path') else None},
        'audit_limits': {'max_paths': 96, 'max_inventory_bytes': 16384, 'max_workers': 16,
            'max_request_bytes': 32000000, 'max_input_tokens_per_call': 850000,
            'worker_output_tokens': 4000, 'omission_output_tokens': 4000, 'integration_output_tokens': 4000,
            'aggregate_input_tokens': 4000000, 'aggregate_output_tokens': 100000,
            'max_calls': 18, 'context_limit_tokens': 900000,
            'context_limit_basis': 'Synthetic assertion, not measured route capacity'},
        'audit_transport': {'transport_attempts': 1, 'sdk_max_retries': 0, 'malformed_response_retries': 0},
        'receipt': {'format': 'receipt_completion_registration_v2', 'registration_id': 'invented-receipt',
            'condition': 'generic_v10', 'runtime_policy_sha256': rc.policy_identity(version=2)['sha256'],
            'receipt_instrument_version': 4, 'max_output_tokens': 4000, 'max_request_bytes': 32000000,
            'context_limit_tokens': 900000, 'context_limit_basis': 'Synthetic fixture',
            'coverage_floor': {'state': 'pending', 'mode': 'diagnostic_pilot'}}}
    return reg


def selected_spec(spec, reg):
    raw = sg.canonical(reg)
    Path(reg['registration_path']).write_bytes(raw)
    return replace(spec, condition='generic_v10', render_version=25, shared_generation_version=1,
        shared_generation_registration=raw.decode(), api_playbook_version=2,
        receipt_completion_version=2, receipt_completion_registration=sg.canonical(reg['receipt']).decode(),
        provider=reg['runtime']['provider'])


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setattr(socket.socket, 'connect', lambda *a, **k: pytest.fail('network forbidden'))
    monkeypatch.setattr(api, 'provider_identity', lambda: {'provider': None, 'base_url': None, 'key_env': None})


@pytest.fixture
def selected(external):
    return selected_spec(external, registration_for(external))


def test_selected_instruction_receipt_and_replay(selected):
    spec = selected
    spec.bind_api_header_values(api._model_settings())
    text = spec.instruction
    assert 'Shared generation rules v1' in text and 'Role relationship review v1' in text
    for common in (api.ANONYMOUS_REMOVAL_CONTRACT_V15, api.SOURCE_METADATA_CONTRACT_V16, api.CLAIM_CLARIFICATION_CONTRACT_V17):
        assert text.count(common) == 1
        assert api.phase_instruction('report', 25).count(common) == 1
    recorded = spec.render_spec()
    assert policy.select_policy(render_spec=recorded)['registration']['format'].endswith('_v2')
    replay = api.RunSpec.from_render_spec(recorded, project=spec.project, method=spec.method, label=spec.label)
    assert replay.instruction == text
    assert api.assembly_digest(25, shared_generation_version=1, api_playbook_version=2, receipt_completion_version=2)


@pytest.mark.parametrize('changes', [{'condition': 'generic_v9'}, {'render_version': 24}, {'runtime': 'Claude Code'},
    {'api_playbook_version': 1}, {'receipt_completion_version': 1}, {'shared_generation_version': 0},
    {'shared_generation_version': True}, {'removal_repair_version': 1}])
def test_crossed_axes_refuse(selected, changes):
    with pytest.raises(ValueError):
        replace(selected, **changes)


@pytest.mark.parametrize('key', ['max_workers', 'worker_output_tokens', 'aggregate_input_tokens', 'max_calls'])
@pytest.mark.parametrize('value', [True, 0, -1, '4', None])
def test_explicit_exact_positive_limits(external, key, value):
    reg = registration_for(external)
    reg['audit_limits'][key] = value
    with pytest.raises(ValueError):
        selected_spec(external, reg)


@pytest.mark.parametrize('key', ['bundle', 'context', 'source_manifest'])
def test_authority_drift_stops_without_recapture(selected, key):
    before = sg.capture(selected)
    pin = before.document()['inputs'][key]
    path = Path(pin['path'])
    path.write_bytes(path.read_bytes() + b'\n')
    assert sg.capture(selected) is before
    with pytest.raises(ValueError, match='authority changed'):
        sg.assert_current(selected)


def test_registration_ambiguous_json_refuses(external):
    reg = registration_for(external)
    raw = sg.canonical(reg)
    raw = raw[:-1] + b',"format":"shared_generation_registration_v1"}'
    with pytest.raises(ValueError, match='duplicate'):
        sg.parse_registration(raw)


def test_output_owned_authority_refuses(external):
    reg = registration_for(external)
    external.out_dir.mkdir()
    current = Path(reg['inputs']['context']['path'])
    copied = external.out_dir / 'claimed-authority.json'
    copied.write_bytes(current.read_bytes())
    reg['inputs']['context'] = sg.file_pin(copied)
    with pytest.raises(ValueError, match='run-owned'):
        selected_spec(external, reg)


def test_legacy_registration_never_admits_v10():
    from tests.test_receipt_completion_runtime import registration
    with pytest.raises(ValueError, match='receipt-producing'):
        policy.parse_registration(registration('generic_v10').encode())


def test_final_report_wire_common_contract_once(selected):
    raw = 'id: urn:fictional\nname: Example\n'
    request = api.build_phase(selected, 'report', carry={'Audit findings': '{"findings": []}',
        'Original full record': raw, 'Original core record': raw, 'Reconciled full record': raw,
        'Completed core record': raw})
    text = '\n'.join(p['text'] for p in request.messages[0]['content'])
    for common in (api.ANONYMOUS_REMOVAL_CONTRACT_V15, api.SOURCE_METADATA_CONTRACT_V16, api.CLAIM_CLARIFICATION_CONTRACT_V17):
        assert text.count(common) == 1

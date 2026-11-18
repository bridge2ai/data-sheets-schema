"""Real v2 preparation/C, synthetic E attribution carriers; no admission proof.

No native executable is invoked. Saved replay retains only captured authority
and final output bytes after the genuine preparation/composition fixture.
"""
from copy import deepcopy
from pathlib import Path
import socket
import subprocess

import pytest

from data_sheets_schema import api_runner as api
from data_sheets_schema import native_attribution_registration_v2 as inherited
from data_sheets_schema import native_shared_attribution as attribution
from data_sheets_schema import native_shared_attribution_orchestration as live_attribution
from data_sheets_schema import native_shared_controller_orchestration as controller
from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_evidence as evidence
from data_sheets_schema import native_execution_registration_v2 as registration
from data_sheets_schema.native_shared_evidence import read_regular
from data_sheets_schema import source_attribution_preflight as preflight
from tests.test_native_shared_selection import pin, save, artifact
from tests.test_native_shared_controller import declaration, synthetic_declaration
from tests.test_native_shared_render import native_spec
from tests.test_native_execution_registration_v2 import inputs as execution_inputs, isolated_modules
from tests.test_source_attribution_preflight import inputs as attribution_inputs, edited, claim
from tests.test_native_source_attribution import call, result, write
from tests.utils.native_execution_carrier_v2 import execution_body


from tests.test_native_shared_attribution import case, construct, checked


def test_saved_replay_uses_captured_bytes_and_defers_superseded_passes(case, monkeypatch):
    cap, spec, composition, _, data, passed, _ = case
    earlier = {**data, 'report_raw': b'# Earlier formatting\n\n' + data['report_raw']}
    earlier_pass = preflight.check_bytes(**earlier)
    assert earlier_pass['passed'] and earlier_pass != passed
    def blocked(*args, **kwargs):
        pytest.fail('saved attribution attempted a live filesystem read')
    monkeypatch.setattr(Path, 'read_bytes', blocked)
    monkeypatch.setattr(Path, 'read_text', blocked)
    monkeypatch.setattr(Path, 'resolve', blocked)
    monkeypatch.setattr(live_attribution, 'read_regular', blocked)
    monkeypatch.setattr(evidence, 'read_regular', blocked)
    for key in ('Popen', 'run', 'check_output'):
        monkeypatch.setattr(subprocess, key, blocked)
    state = construct(case, saved=True)
    assert type(state).observe is inherited.NativeAttributionState.observe
    assert type(state).report is inherited.NativeAttributionState.report
    checked(state, composition, earlier_pass, identity='earlier')
    assert state.observations[0]['verified_against_current_saved_bytes'] is False
    state.observe(write('correction', spec._agentic_artifact_paths['report']))
    state.observe(result('correction', {}))
    checked(state, composition, passed, identity='current')
    out = state.finish()
    assert out['draft_gate_passed'] and out['checks'] == 2
    assert out['observations'][0]['verified_against_current_saved_bytes'] is False
    assert out['observations'][1]['verified_against_current_saved_bytes'] is True


def test_saved_final_byte_substitution_refuses_claimed_passing_payload(case):
    state = construct(case, saved=True, report=b'# Changed bytes\n\n' + case[4]['report_raw'])
    checked(state, case[2], case[5])
    assert not state.finish()['draft_gate_passed']


@pytest.mark.parametrize('change', ['role', 'path'])
def test_saved_final_artifacts_require_exact_roles_and_paths(case, change):
    cap, spec, composition, execution, data, _, captured_instruction = case
    full = artifact('wrong' if change == 'role' else 'final_full',
        spec._agentic_artifact_paths['full'] + ('.other' if change == 'path' else ''), data['record_raw'])
    with pytest.raises(ValueError, match='another role, path'):
        attribution.saved(cap, execution_raw=c.canonical(execution), spec=spec, composition_raw=c.canonical(composition),
            captured_instruction=captured_instruction,
            final_full=full, final_report=artifact('final_report', spec._agentic_artifact_paths['report'], data['report_raw']))


@pytest.mark.parametrize('change', ['bare_body', 'v1', 'bool', 'manifest', 'extra'])
def test_saved_attribution_refuses_non_v2_wire_before_any_live_read(case, monkeypatch, change):
    cap, spec, composition, execution, data, _, captured_instruction = case
    value = deepcopy(execution)
    if change == 'bare_body': value = value['registration']
    elif change == 'v1': value['authority_version'] = 1
    elif change == 'bool': value['authority_version'] = True
    elif change == 'manifest': value['controller_sources_sha256'] = '0' * 64
    else: value['extra'] = 'not an envelope field'

    def blocked(*args, **kwargs):
        pytest.fail('captured attribution consulted live authority')

    monkeypatch.setattr(controller, 'reconstruct_composition', blocked)
    monkeypatch.setattr(registration, 'verify_preparer', blocked)
    monkeypatch.setattr(live_attribution, 'read_regular', blocked)
    monkeypatch.setattr(evidence, 'read_regular', blocked)
    for name in ('read_bytes', 'read_text', 'open'):
        monkeypatch.setattr(Path, name, blocked)
    with pytest.raises(ValueError):
        attribution.saved(cap, execution_raw=c.canonical(value), spec=spec,
            composition_raw=c.canonical(composition),
            captured_instruction=captured_instruction,
            final_full=artifact('final_full', spec._agentic_artifact_paths['full'], data['record_raw']),
            final_report=artifact('final_report', spec._agentic_artifact_paths['report'], data['report_raw']))


@pytest.mark.parametrize('change', [
    'selection_pin', 'runtime_pin', 'runtime_bytes', 'instruction_bytes', 'render',
    'draft_bool', 'dependencies', 'selected_source_pin',
])
def test_saved_rehashed_preparation_still_binds_captured_authority(case, monkeypatch, change):
    cap, spec, composition, execution, data, _, captured_instruction = case
    composition, execution = deepcopy(composition), deepcopy(execution)
    body = execution['registration']
    preparation = c.strict_json(body['preparation_raw_json'].encode('utf-8'))
    prepared = preparation['registration']
    if change == 'selection_pin': prepared['selection']['bytes'] += 1
    elif change == 'runtime_pin': prepared['runtime']['sha256'] = '0' * 64
    elif change == 'runtime_bytes': prepared['runtime']['bytes'] += 1
    elif change == 'instruction_bytes': prepared['instruction'] += '\nchanged'
    elif change == 'render': prepared['render_spec']['run_date'] = '2026-11-08'
    elif change == 'draft_bool': prepared['max_draft_checks'] = True
    elif change == 'dependencies': prepared['dependencies']['version'] = 1
    else: prepared['pinned_files'][cap.registration.pin.path] = '0' * 64
    raw = c.canonical(preparation)
    for value in (body, composition):
        value['preparation_raw_json'] = raw.decode('utf-8')
        value['preparation_sha256'] = c.sha(raw)
    body['composition_raw_json'] = c.canonical(composition).decode('utf-8')
    body['composition_sha256'] = c.sha(c.canonical(composition))

    def blocked(*args, **kwargs):
        pytest.fail('saved preparation join tried fresh host verification')

    monkeypatch.setattr(controller, 'reconstruct_composition', blocked)
    monkeypatch.setattr(registration, 'verify_preparer', blocked)
    monkeypatch.setattr(Path, 'read_bytes', blocked)
    monkeypatch.setattr(Path, 'read_text', blocked)
    monkeypatch.setattr(Path, 'resolve', blocked)
    with pytest.raises(ValueError):
        attribution.saved(cap, execution_raw=c.canonical(execution), spec=spec,
            composition_raw=c.canonical(composition),
            captured_instruction=captured_instruction,
            final_full=artifact('final_full', spec._agentic_artifact_paths['full'], data['record_raw']),
            final_report=artifact('final_report', spec._agentic_artifact_paths['report'], data['report_raw']))


def test_saved_consistently_rehashed_instruction_refuses_genuine_artifact(case, monkeypatch):
    cap, spec, composition, execution, data, _, captured_instruction = case
    composition, execution = deepcopy(composition), deepcopy(execution)
    body = execution['registration']
    preparation = c.strict_json(body['preparation_raw_json'].encode('utf-8'))
    prepared = preparation['registration']
    prepared['instruction'] += '\nThis substituted instruction was never captured.\n'
    substituted_sha = c.sha(prepared['instruction'].encode('utf-8'))
    prepared['instruction_sha256'] = substituted_sha
    prepared['input_identity']['instruction']['sha256'] = substituted_sha
    raw = c.canonical(preparation)
    for value in (body, composition):
        value['preparation_raw_json'] = raw.decode('utf-8')
        value['preparation_sha256'] = c.sha(raw)
        value['instruction_sha256'] = substituted_sha
    body['composition_raw_json'] = c.canonical(composition).decode('utf-8')
    body['composition_sha256'] = c.sha(c.canonical(composition))
    assert captured_instruction.pin.sha256 != substituted_sha

    def blocked(*args, **kwargs):
        pytest.fail('saved instruction comparison consulted the host')

    monkeypatch.setattr(controller, 'reconstruct_composition', blocked)
    monkeypatch.setattr(registration, 'verify_preparer', blocked)
    monkeypatch.setattr(Path, 'read_bytes', blocked)
    monkeypatch.setattr(Path, 'read_text', blocked)
    monkeypatch.setattr(Path, 'resolve', blocked)
    with pytest.raises(ValueError, match='independent captured artifact'):
        attribution.saved(cap, execution_raw=c.canonical(execution), spec=spec,
            composition_raw=c.canonical(composition), captured_instruction=captured_instruction,
            final_full=artifact('final_full', spec._agentic_artifact_paths['full'], data['record_raw']),
            final_report=artifact('final_report', spec._agentic_artifact_paths['report'], data['report_raw']))


@pytest.mark.parametrize('change', ['role', 'path', 'raw'])
def test_saved_instruction_requires_the_exact_independent_artifact(case, change):
    cap, spec, composition, execution, data, _, captured_instruction = case
    supplied = artifact('foreign' if change == 'role' else 'instruction',
        captured_instruction.pin.path + ('.foreign' if change == 'path' else ''),
        captured_instruction.raw + (b'\nforeign bytes' if change == 'raw' else b''))
    with pytest.raises(ValueError, match='independent captured artifact'):
        attribution.saved(cap, execution_raw=c.canonical(execution), spec=spec,
            composition_raw=c.canonical(composition), captured_instruction=supplied,
            final_full=artifact('final_full', spec._agentic_artifact_paths['full'], data['record_raw']),
            final_report=artifact('final_report', spec._agentic_artifact_paths['report'], data['report_raw']))

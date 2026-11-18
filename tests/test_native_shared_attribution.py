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


@pytest.fixture
def case(execution_inputs, attribution_inputs, tmp_path, monkeypatch):
    original = execution_inputs['spec']
    doc = original._native_shared_generation_capture.document()
    data = {**attribution_inputs, 'protocol_version': 7, 'project': doc['run']['project'],
            'source_manifest_raw': attribution_inputs['source_manifest_raw'].replace(
                b'EXAMPLE:', (doc['run']['project'] + ':').encode('utf-8'))}
    for name in ('bundle', 'chunk_manifest', 'source_manifest'):
        path = Path(doc['inputs'][name]['path'])
        path.write_bytes(data[name + '_raw'])
        doc['inputs'][name] = pin(path, data[name + '_raw'])
    save(doc)
    monkeypatch.setattr(api, 'CONCAT_DIR', tmp_path.resolve() / 'outputs')
    preparation = registration.prepare(
        execution_inputs['selection'], execution_inputs['runtime_path'],
        **{**execution_inputs['kwargs'], 'max_draft_checks': 3})
    preparation_raw = c.canonical(preparation)
    prepared = preparation['registration']
    instruction = tmp_path.resolve() / 'instruction.md'
    instruction.write_bytes(prepared['instruction'].encode('utf-8'))
    composition = controller.compose(preparation_raw, instruction_path=str(instruction))
    composition_raw = c.canonical(composition)
    checked_composition, spec, cap = controller.reconstruct_composition(composition_raw)
    assert checked_composition == composition
    captured_instruction = read_regular(str(instruction), 'instruction',
        max_bytes=c.HARD_LIMITS['request_bytes']).captured
    for role, path in spec._agentic_artifact_paths.items():
        assert Path(path).is_relative_to(tmp_path.resolve())
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(spec._agentic_artifact_paths['full']).write_bytes(data['record_raw'])
    Path(spec._agentic_artifact_paths['report']).write_bytes(data['report_raw'])
    body = execution_body(**{
        'preparation_raw_json': preparation_raw.decode('utf-8'),
        'preparation_sha256': c.sha(preparation_raw),
        'job_id': prepared['job_id'], 'dependencies': prepared['dependencies'],
        'max_draft_checks': 3,
        'selection_sha256': cap.registration.pin.sha256,
        'runtime_declaration_sha256': prepared['runtime']['sha256'],
        'runtime': execution_inputs['runtime'],
        'composition_raw_json': composition_raw.decode('utf-8'),
        'composition_sha256': c.sha(composition_raw),
        'instruction_sha256': composition['instruction_sha256'],
        'working_directory': composition['working_directory']})
    execution = {'authority_version': 2,
        'controller_sources_sha256': preparation['controller_sources_sha256'],
        'registration': body}
    passed = preflight.check_bytes(**data)
    assert passed['passed'] and passed['protocol_version'] == 7
    def blocked(*args, **kwargs):
        pytest.fail('attribution invoked a native/process/network operation')
    # execution_inputs permits only local Git source proofs in subprocesses.
    monkeypatch.setattr(socket.socket, 'connect', blocked)
    return cap, spec, composition, execution, data, passed, captured_instruction


def construct(case, *, saved=False, full=None, report=None):
    cap, spec, composition, execution, data, _, captured_instruction = case
    kwargs = dict(execution_raw=c.canonical(execution), spec=spec, composition_raw=c.canonical(composition))
    if saved:
        return attribution.saved(cap, **kwargs,
            captured_instruction=captured_instruction,
            final_full=artifact('final_full', spec._agentic_artifact_paths['full'], full or data['record_raw']),
            final_report=artifact('final_report', spec._agentic_artifact_paths['report'], report or data['report_raw']))
    return live_attribution.live(cap, **kwargs)


def checked(state, composition, payload, identity='draft', status=0):
    state.observe(call(identity, composition['policy']['native_shared_helpers']['draft']))
    state.observe(result(identity, payload, status))


def test_live_reuses_observer_and_protocol7_on_exact_current_outputs(case, monkeypatch):
    cap, spec, composition, execution, data, passed, _ = case
    seen = []
    original = preflight.check_bytes
    def check(**kwargs):
        seen.append(kwargs)
        return original(**kwargs)
    monkeypatch.setattr(preflight, 'check_bytes', check)
    state = construct(case)
    assert state.reg['working_directory'] == composition['working_directory']
    assert state.commands == {composition['policy']['native_shared_helpers'][name]: kind for name, kind in
        {'draft': 'draft', 'audit_evidence': 'evidence', 'final_evidence': 'final_evidence',
         'original_source_inventory': 'source_inventory', 'final_source_inventory': 'source_inventory'}.items()}
    changed = state.commands
    changed.clear()
    assert len(state.commands) == 5
    assert type(state).observe is inherited.NativeAttributionState.observe
    assert type(state).report is inherited.NativeAttributionState.report
    checked(state, composition, passed)
    report = state.report(complete=True)
    assert report['draft_gate_passed'] and report['max_draft_checks'] == 3
    assert report['registration_sha256'] == c.sha(c.canonical(execution))
    assert report['observations'][0]['verified_against_current_saved_bytes']
    assert seen and all(value == data for value in seen)
    assert inherited.NativeAttributionState.observe.__qualname__ == 'NativeAttributionState.observe'


def test_live_readonly_lookup_preserves_pass_without_becoming_a_helper(case):
    state = construct(case); composition, passed = case[2], case[5]
    checked(state, composition, passed)
    command = 'cat ' + str(case[1].bundle)
    state.observe(call('lookup', command), preserved_shell_commands=(command,))
    state.observe(result('lookup', {}), preserved_shell_commands=(command,))
    assert state.report(complete=True)['draft_gate_passed']
    assert state.report()['checks'] == 1
    state.observe(call('unknown', 'echo altered'))
    state.observe(result('unknown', {}))
    assert not state.report(complete=True)['draft_gate_passed']


def test_live_uses_captured_sources_and_only_bounded_current_output_reads(case, monkeypatch):
    state = construct(case)  # The live entry freshly verifies preparation/C.
    def blocked(*args, **kwargs):
        pytest.fail('attribution reread a source or used an unbounded Path read')
    monkeypatch.setattr(Path, 'read_bytes', blocked)
    monkeypatch.setattr(Path, 'read_text', blocked)
    checked(state, case[2], case[5])
    assert state.report(complete=True)['draft_gate_passed']


@pytest.mark.parametrize('name', ['audit_evidence', 'final_evidence',
                                  'original_source_inventory', 'final_source_inventory'])
def test_selected_terminal_helper_failure_remains_sticky(case, name):
    state = construct(case); checked(state, case[2], case[5])
    state.observe(call('terminal-failure', case[2]['policy']['native_shared_helpers'][name]))
    state.observe(result('terminal-failure', {}, 1))
    report = state.report(complete=True)
    assert report['terminal_failure_observed'] and not report['draft_gate_passed']
    assert any('terminal evidence/source-inventory' in p for p in report['problems'])


@pytest.mark.parametrize('role', ['full', 'report'])
def test_live_changed_current_output_invalidates_old_draft_pass(case, role):
    state = construct(case); checked(state, case[2], case[5])
    path = Path(case[1]._agentic_artifact_paths[role])
    path.write_bytes(b'# changed current bytes\n' + path.read_bytes())
    report = state.report(complete=True)
    assert not report['draft_gate_passed'] and any('differs' in p for p in report['problems'])


def test_live_output_byte_bound_refuses(case):
    state = construct(case); checked(state, case[2], case[5])
    report_path = Path(case[1]._agentic_artifact_paths['report'])
    report_path.write_bytes(b'x' * (case[0].bounds()['max_input_bytes'] + 1))
    report = state.report(complete=True)
    assert not report['draft_gate_passed'] and any('byte bound' in p for p in report['problems'])






@pytest.mark.parametrize('role', ['full', 'core', 'phase1_full', 'phase1_core', 'phase1_receipt', 'audit'])
def test_correction_never_changes_protected_records_or_stage_artifacts(case, role):
    state = construct(case); checked(state, case[2], case[5])
    path = case[1]._agentic_artifact_paths[role] if role in ('full', 'core') else case[0].role(role)
    state.observe(write('forbidden', path))
    assert any('protected' in p for p in state.report()['problems'])


def test_failed_draft_can_be_corrected_but_limit_and_final_order_stay_inherited(case):
    cap, spec, composition, _, data, passed, _ = case
    confused = edited(data, lambda review: claim(review).update(attributed_to=['project_documentation']))
    failed = preflight.check_bytes(**confused)
    state = construct(case)
    checked(state, composition, failed, identity='failed', status=1)
    assert state.report()['problems'] == [] and not state.report()['draft_gate_passed']
    state.observe(write('correction', spec._agentic_artifact_paths['report']))
    state.observe(result('correction', {}))
    checked(state, composition, passed, identity='passing')
    assert state.report(complete=True)['draft_gate_passed']
    checked(state, composition, passed, identity='third')
    checked(state, composition, passed, identity='exhausted')
    assert any('limit exceeded' in p for p in state.report()['problems'])
    other = construct(case)
    other.observe(call('premature', composition['policy']['native_shared_helpers']['final_evidence']))
    assert any('precedes' in p for p in other.report()['problems'])


@pytest.mark.parametrize('mutation', ['selection', 'composition_raw', 'count', 'count_bool',
    'runtime', 'spec', 'instruction', 'policy_hash', 'helper', 'cwd'])
def test_mismatched_captured_selection_execution_or_policy_refuses(case, mutation):
    cap, spec, composition, execution, data, passed, _ = case
    composition, execution = deepcopy(composition), deepcopy(execution)
    body = execution['registration']
    if mutation == 'selection': body['selection_sha256'] = '0' * 64
    elif mutation == 'composition_raw': body['composition_raw_json'] += '\n'
    elif mutation == 'count': body['max_draft_checks'] = 4
    elif mutation == 'count_bool': body['max_draft_checks'] = True
    elif mutation == 'runtime': body['runtime']['model'] += '-other'
    elif mutation == 'spec': composition['render_spec']['run_date'] = '2026-11-08'
    elif mutation == 'instruction': body['instruction_sha256'] = '0' * 64
    elif mutation == 'policy_hash': composition['policy_sha256'] = '0' * 64
    elif mutation == 'helper':
        composition['policy']['native_shared_helpers']['draft'] += ' --unregistered'
        composition['policy']['attribution_command'] = composition['policy']['native_shared_helpers']['draft']
        composition['policy_sha256'] = c.sha(c.canonical(composition['policy']))
    else: body['working_directory'] = '/foreign'
    if mutation in ('policy_hash', 'helper', 'spec'):
        body.update(composition_raw_json=c.canonical(composition).decode(),
                    composition_sha256=c.sha(c.canonical(composition)))
    with pytest.raises(ValueError):
        live_attribution.live(cap, execution_raw=c.canonical(execution), spec=spec, composition_raw=c.canonical(composition))

"""Selected draft-state integration with synthetic E/C joins, not launch proof."""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import socket
import subprocess

import pytest

from data_sheets_schema import api_runner as api
from data_sheets_schema import native_attribution_registration as inherited
from data_sheets_schema import native_shared_attribution as attribution
from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_policy as policy
from data_sheets_schema import source_attribution_preflight as preflight
from tests.test_native_shared_selection import declaration, pin, save, artifact
from tests.test_native_shared_render import native_spec
from tests.test_source_attribution_preflight import inputs, edited, claim
from tests.test_native_source_attribution import call, result, write


@pytest.fixture
def case(native_spec, inputs, tmp_path, monkeypatch):
    original = native_spec
    doc = original._native_shared_generation_capture.document()
    data = {**inputs, 'protocol_version': 7, 'project': doc['run']['project'],
            'source_manifest_raw': inputs['source_manifest_raw'].replace(b'EXAMPLE:', b'SYNTHETIC:')}
    for name in ('bundle', 'chunk_manifest', 'source_manifest'):
        path = Path(doc['inputs'][name]['path'])
        path.write_bytes(data[name + '_raw'])
        doc['inputs'][name] = pin(path, data[name + '_raw'])
    save(doc)
    monkeypatch.setattr(api, 'CONCAT_DIR', tmp_path.resolve() / 'outputs')
    spec = replace(original, native_shared_generation_registration=c.canonical(doc).decode())
    spec._native_shared_runtime_capture = original._native_shared_runtime_capture
    spec._native_shared_max_draft_checks = 3
    cap = spec._native_shared_generation_capture
    for role, path in spec._agentic_artifact_paths.items():
        assert Path(path).is_relative_to(tmp_path.resolve())
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(spec._agentic_artifact_paths['full']).write_bytes(data['record_raw'])
    Path(spec._agentic_artifact_paths['report']).write_bytes(data['report_raw'])
    instruction = tmp_path.resolve() / 'instruction.md'
    instruction.write_bytes(spec.instruction.encode())
    selected_policy = policy.command_policy(spec, str(instruction))
    runtime = spec._native_shared_runtime_capture
    composition = {'kind': 'd4d_native_shared_callback_composition', 'version': 1,
        'selection_raw_json': cap.registration.raw.decode(), 'selection_sha256': cap.registration.pin.sha256,
        'runtime_path': runtime.pin.path, 'runtime_raw_json': runtime.raw.decode(),
        'runtime_sha256': runtime.pin.sha256, 'max_draft_checks': 3,
        'render_spec': spec.render_spec(), 'instruction_path': str(instruction),
        'instruction_sha256': c.sha(instruction.read_bytes()),
        'policy': selected_policy, 'policy_sha256': c.sha(c.canonical(selected_policy)),
        'working_directory': selected_policy['readonly_lookups']['repository']}
    execution = {'kind': c.KINDS['execution'], 'version': 1, 'max_draft_checks': 3,
        'selection_sha256': cap.registration.pin.sha256,
        'runtime_declaration_sha256': runtime.pin.sha256, 'runtime': c.strict_json(runtime.raw),
        'composition_raw_json': c.canonical(composition).decode(),
        'composition_sha256': c.sha(c.canonical(composition)),
        'instruction_sha256': composition['instruction_sha256'],
        'working_directory': composition['working_directory'],
        'selection': {**doc['run'], 'render_spec': spec.render_spec()}}
    passed = preflight.check_bytes(**data)
    assert passed['passed'] and passed['protocol_version'] == 7
    def blocked(*args, **kwargs):
        pytest.fail('attribution invoked a native/process/network operation')
    for key in ('Popen', 'run', 'check_output'):
        monkeypatch.setattr(subprocess, key, blocked)
    monkeypatch.setattr(socket.socket, 'connect', blocked)
    return cap, spec, composition, execution, data, passed


def construct(case, *, saved=False, full=None, report=None):
    cap, spec, composition, execution, data, _ = case
    kwargs = dict(execution_raw=c.canonical(execution), spec=spec, composition_raw=c.canonical(composition))
    if saved:
        return attribution.saved(cap, **kwargs,
            final_full=artifact('final_full', spec._agentic_artifact_paths['full'], full or data['record_raw']),
            final_report=artifact('final_report', spec._agentic_artifact_paths['report'], report or data['report_raw']))
    return attribution.live(cap, **kwargs)


def checked(state, composition, payload, identity='draft', status=0):
    state.observe(call(identity, composition['policy']['native_shared_helpers']['draft']))
    state.observe(result(identity, payload, status))


def test_live_reuses_observer_and_protocol7_on_exact_current_outputs(case, monkeypatch):
    cap, spec, composition, execution, data, passed = case
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
    def blocked(*args, **kwargs):
        pytest.fail('attribution reread a source or used an unbounded Path read')
    monkeypatch.setattr(Path, 'read_bytes', blocked)
    monkeypatch.setattr(Path, 'read_text', blocked)
    state = construct(case)
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


def test_saved_replay_uses_captured_bytes_and_defers_superseded_passes(case, monkeypatch):
    cap, spec, composition, _, data, passed = case
    earlier = {**data, 'report_raw': b'# Earlier formatting\n\n' + data['report_raw']}
    earlier_pass = preflight.check_bytes(**earlier)
    assert earlier_pass['passed'] and earlier_pass != passed
    def blocked(*args, **kwargs):
        pytest.fail('saved attribution attempted a live filesystem read')
    monkeypatch.setattr(Path, 'read_bytes', blocked)
    monkeypatch.setattr(Path, 'read_text', blocked)
    monkeypatch.setattr(Path, 'resolve', blocked)
    monkeypatch.setattr(attribution, 'read_regular', blocked)
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


@pytest.mark.parametrize('role', ['full', 'core', 'phase1_full', 'phase1_core', 'phase1_receipt', 'audit'])
def test_correction_never_changes_protected_records_or_stage_artifacts(case, role):
    state = construct(case); checked(state, case[2], case[5])
    path = case[1]._agentic_artifact_paths[role] if role in ('full', 'core') else case[0].role(role)
    state.observe(write('forbidden', path))
    assert any('protected' in p for p in state.report()['problems'])


def test_failed_draft_can_be_corrected_but_limit_and_final_order_stay_inherited(case):
    cap, spec, composition, _, data, passed = case
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
    cap, spec, composition, execution, data, passed = case
    composition, execution = deepcopy(composition), deepcopy(execution)
    if mutation == 'selection': execution['selection_sha256'] = '0' * 64
    elif mutation == 'composition_raw': execution['composition_raw_json'] += '\n'
    elif mutation == 'count': execution['max_draft_checks'] = 4
    elif mutation == 'count_bool': execution['max_draft_checks'] = True
    elif mutation == 'runtime': execution['runtime']['model'] += '-other'
    elif mutation == 'spec': execution['selection']['render_spec']['label'] = 'foreign'
    elif mutation == 'instruction': execution['instruction_sha256'] = '0' * 64
    elif mutation == 'policy_hash': composition['policy_sha256'] = '0' * 64
    elif mutation == 'helper':
        composition['policy']['native_shared_helpers']['draft'] += ' --unregistered'
        composition['policy']['attribution_command'] = composition['policy']['native_shared_helpers']['draft']
        composition['policy_sha256'] = c.sha(c.canonical(composition['policy']))
    else: execution['working_directory'] = '/foreign'
    if mutation in ('policy_hash', 'helper'):
        execution.update(composition_raw_json=c.canonical(composition).decode(),
                         composition_sha256=c.sha(c.canonical(composition)))
    with pytest.raises(ValueError):
        attribution.live(cap, execution_raw=c.canonical(execution), spec=spec, composition_raw=c.canonical(composition))


@pytest.mark.parametrize('change', ['role', 'path'])
def test_saved_final_artifacts_require_exact_roles_and_paths(case, change):
    cap, spec, composition, execution, data, _ = case
    full = artifact('wrong' if change == 'role' else 'final_full',
        spec._agentic_artifact_paths['full'] + ('.other' if change == 'path' else ''), data['record_raw'])
    with pytest.raises(ValueError, match='another role, path'):
        attribution.saved(cap, execution_raw=c.canonical(execution), spec=spec, composition_raw=c.canonical(composition),
            final_full=full, final_report=artifact('final_report', spec._agentic_artifact_paths['report'], data['report_raw']))

"""Actual selected adapter/owner capture with an ordinary declared Python peer.

S/C/E, permission reconstruction, source proof and stream publication are real.
The model/auth/permission/clock observations are explicit software fixtures.
The peer never executes a requested tool and cannot satisfy the final phases.
"""
from contextlib import ExitStack
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import json
import os
import shlex
import subprocess
import sys
import threading

import pytest

from data_sheets_schema import native_attribution_controller as inherited
from data_sheets_schema import native_execution_authority as authority
from data_sheets_schema import native_owner_profile_v1 as profile
from data_sheets_schema import native_owner_runner_v1 as runner_module
from data_sheets_schema import native_shared_capture as capture
from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_controller as controller
from data_sheets_schema import native_shared_evidence as evidence
from data_sheets_schema import native_shared_execution as execution
from data_sheets_schema import native_shared_policy as policy
from data_sheets_schema import native_shared_registration as registration
from data_sheets_schema import native_shared_streams as streams
from data_sheets_schema import native_stream_coordination_v1 as coordination
from data_sheets_schema.native_attempt_supervisor import durable_new
from data_sheets_schema.native_execution import _mkdir_durable
from tests.test_native_shared_controller import bound, native_spec, declaration
from tests.test_native_shared_permissions import fabricated_manifest
from tests.test_native_owner_runner import fixed_clock
from tests.test_native_owner_scoped_registration import no_nested_loaders


_REAL_PROCESS = {name: getattr(subprocess, name) for name in ('run', 'Popen', 'check_output')}
SESSION = '11111111-2222-4333-8444-555555555555'
TERMINAL_REFUSAL = 'native terminal precedes all final obligations'


PEER = r'''
import json, pathlib, sys
root = pathlib.Path(__file__).parent
(root / 'peer-argv.json').write_text(json.dumps(sys.argv))
def emit(value):
    print(json.dumps(value), flush=True)
init = json.loads(sys.stdin.buffer.readline())
emit({'type': 'control_response', 'response': {'subtype': 'success',
    'request_id': init['request_id'], 'response': {}}})
prompt = json.loads(sys.stdin.buffer.readline())
(root / 'peer-instruction.txt').write_bytes(prompt['message']['content'].encode('utf-8'))
cwd = str(pathlib.Path.cwd())
emit({'type': 'system', 'subtype': 'init', 'session_id': SESSION,
    'cwd': cwd, 'model': MODEL, 'claude_code_version': VERSION,
    'apiKeySource': 'none', 'tools': ['Bash', 'Read', 'Write']})
if COMMAND is not None:
    inputs = {'command': COMMAND}
    emit({'type': 'assistant', 'session_id': SESSION, 'message': {'content': [
        {'type': 'tool_use', 'id': 'fixture-tool', 'name': 'Bash', 'input': inputs}]}})
    emit({'type': 'control_request', 'request_id': 'fixture-request', 'request': {
        'subtype': 'hook_callback', 'callback_id': CALLBACK, 'input': {
            'hook_event_name': 'PreToolUse', 'tool_name': 'Bash',
            'tool_use_id': 'fixture-tool', 'tool_input': inputs, 'cwd': cwd}}})
    response = json.loads(sys.stdin.buffer.readline())
    (root / 'peer-response.json').write_text(json.dumps(response))
    assert response['response']['request_id'] == 'fixture-request'
    # No shell/tool invocation: only fictional settlement of the protocol call.
    content = 'Synthetic protocol settlement; command not executed.'
    emit({'type': 'user', 'session_id': SESSION, 'message': {'content': [
        {'type': 'tool_result', 'tool_use_id': 'fixture-tool', 'content': content,
         'is_error': False}]}, 'tool_use_result': {'exitCode': 0, 'stdout': content}})
# The real phase observer must reject this incomplete run after initialization.
emit({'type': 'result', 'session_id': SESSION, 'result': 'No complete phases or provider.'})
'''


def make_adapter_case(bound_case, root, controls, *, peer_mode='no_tools', max_evidence_bytes=None):
    """Prepare, reserve and bind without executing; fault seams install later."""
    if peer_mode not in ('no_tools', 'readonly'):
        raise ValueError('unknown ordinary peer fixture mode')
    old_spec, old_runtime, old_instruction = bound_case
    old_bytes = (old_runtime.read_bytes(), old_instruction.read_bytes())
    root = Path(root).resolve(); root.mkdir()
    original_selection = old_spec.native_shared_generation_registration.encode('utf-8')
    selection_document = c.parse_selection(original_selection)
    original_selection_path = Path(selection_document['registration_path'])
    assert original_selection_path.read_bytes() == original_selection
    if max_evidence_bytes is not None:
        # A fresh real S is selected before any new rendering/C/E/proof. The
        # original bound selection and its cached instruction remain intact.
        selection_document['registration_path'] = str(root / 'selection.json')
        selection_document['bounds']['max_evidence_bytes'] = max_evidence_bytes
        selected_raw = c.canonical(selection_document)
        c.parse_selection(selected_raw)
        (root / 'selection.json').write_bytes(selected_raw)
        spec = replace(old_spec, native_shared_generation_registration=selected_raw.decode('utf-8'))
    else:
        spec = replace(old_spec)
    assert 'instruction' not in spec.__dict__
    runtime = c.strict_json(old_bytes[0])
    callback = controls['native_control'].HISTORY_CONTRACT['callback_id']
    command = shlex.join(['cat', str(spec.bundle)]) if peer_mode == 'readonly' else None
    peer = root / 'ordinary-declared-peer'
    constants = ('SESSION = ' + repr(SESSION) + '\nMODEL = ' + repr(runtime['model']) +
        '\nVERSION = ' + repr(runtime['executable']['init_version']) +
        '\nCALLBACK = ' + repr(callback) + '\nCOMMAND = ' + repr(command) + '\n')
    peer.write_bytes(('#!' + sys.executable + '\n' + constants + PEER).encode('utf-8'))
    peer.chmod(0o700)
    runtime['executable'].update(path=str(peer), sha256=c.sha(peer.read_bytes()))
    runtime['environment']['PATH'] = str(Path(sys.executable).parent) + os.pathsep + '/usr/bin:/bin'
    runtime['keep_awake'] = {'policy': 'not_applicable', 'host_platform': sys.platform,
        'basis': 'Ordinary Python software peer; no native runtime observation.'}
    runtime_path = root / 'runtime.json'; runtime_path.write_bytes(c.canonical(runtime))
    controller.bind_runtime(spec, runtime_path, 3)
    instruction = root / 'instruction.md'; instruction.write_bytes(spec.instruction.encode('utf-8'))
    identity = authority.dependency_identity(stream_snapshot_profile=1)
    selected_profile = deepcopy(identity['stream_snapshot_profile'])
    composition = controller._compose_in_scope(spec, runtime_path=runtime_path,
        instruction_path=instruction, max_draft_checks=3, profile=selected_profile)
    comp_path = root / 'composition.json'; comp_raw = c.canonical(composition); comp_path.write_bytes(comp_raw)
    system = root / 'system.txt'; system.write_bytes(b'Explicit ordinary software fixture only.\n')
    attempt, output = root / 'attempt', root / 'evidence'
    expected = registration.permission_expectation(runtime, composition, spec,
        system.read_text() + policy._command_guidance_in_scope(composition['policy'], selected_profile),
        attempt / 'cli_config', identity)
    saved = fabricated_manifest(expected, spec._native_shared_generation_capture.document(),
        root / 'fabricated-permission-records', spec.bundle.read_bytes())
    permission = root / 'fabricated-permission.json'; permission.write_bytes(c.canonical(saved))
    value = registration._registration_in_scope(comp_path, system,
        permission_probe_path=permission, attempt_id=attempt.name,
        attempt_directory=attempt, evidence_directory=output, max_draft_checks=3)
    raw = c.canonical(value)
    assert registration._verified_in_scope(raw) == value
    authority.require_committed(value['dependencies'])
    assert value['argv'][0] == str(peer)
    assert (old_runtime.read_bytes(), old_instruction.read_bytes()) == old_bytes
    assert original_selection_path.read_bytes() == original_selection
    if max_evidence_bytes is not None:
        assert spec._native_shared_generation_capture.bounds()['max_evidence_bytes'] == max_evidence_bytes
    # Reserve the exact E/S destinations, without widening public launch entry.
    paths = registration._paths(value, composition, fresh=True)
    for path in paths:
        _mkdir_durable(path)
    durable_new(attempt / 'registration.json', raw)
    started = {'kind': c.KINDS['attempt'], 'version': 1, 'state': 'started',
        'attempt_id': value['attempt_id'], 'registration_sha256': c.sha(raw),
        'composition_sha256': value['composition_sha256'], 'dispatch_limit': 1}
    started_raw = c.canonical(started); durable_new(attempt / 'started.json', started_raw)
    _mkdir_durable(attempt / 'cli_config')
    adapter = controller._callback_adapter_in_scope(comp_raw, execution=value, registration_raw=raw)
    contract, _ = execution._engine_bindings()
    assert contract.transport_phase_spec(adapter) is None
    runner = profile.bind_runner(selected_profile, controls)
    proxy = controls['run_direct_canary'].NoProxy()
    stops, observed, classified = [], [], []
    # Actual _unchanged input-byte checks, without pretending these are signed
    # or approved external launch declarations. The public route stays closed.
    inputs, source_raw = {}, {}
    for name in ('review', 'ci', 'launch'):
        inputs[name] = root / (name + '-fixture-precondition.json')
        source_raw[name] = c.canonical({'fixture': name, 'execution_authorized': False})
        inputs[name].write_bytes(source_raw[name])
    authorization = {'inputs': inputs, 'raw': source_raw}
    case = {'root': root, 'attempt': attempt, 'evidence': output, 'peer': peer,
        'peer_mode': peer_mode, 'command': command, 'spec': spec, 'runtime': runtime,
        'runtime_path': runtime_path, 'instruction': instruction, 'instruction_path': instruction,
        'composition': composition, 'composition_raw': comp_raw, 'execution': value, 'value': value,
        'raw': raw, 'execution_raw': raw, 'started': started, 'started_raw': started_raw,
        'controls': controls, 'identity': identity, 'profile': selected_profile,
        'parent_scope': profile._ACTIVE.get(), 'selection': adapter.selection,
        'adapter': adapter, 'runner': runner, 'proxy': proxy, 'stops': stops,
        'observed': observed, 'classified': classified, 'authorization': authorization,
        'received_instruction': root / 'peer-instruction.txt', 'received_argv': root / 'peer-argv.json',
        'received_response': root / 'peer-response.json'}
    def launch_check():
        execution._unchanged_in_scope(value, raw, authorization)
        assert (attempt / 'registration.json').read_bytes() == raw
        assert (attempt / 'started.json').read_bytes() == started_raw
        adapter.activate_before_dispatch(started_raw, owner_raw=runner.owner_raw())
    def observe(event):
        adapter.observe(event)
        observed.append(deepcopy(event))
    def classify(*args):
        result = adapter.classify(*args)
        classified.append({'result': result, 'scope': profile._ACTIVE.get(),
            'budget': coordination.current_reader_budget(), 'thread': threading.current_thread()})
        return result
    case['kwargs'] = {'argv': list(value['argv']), 'proxy': proxy, 'instruction': instruction,
        'attempt': attempt, 'cwd': value['working_directory'], 'env': dict(value['environment']),
        'deadline_seconds': value['runtime']['deadline_seconds'], 'verify_launch': launch_check,
        'record_stop': stops.append, 'command_policy': adapter.policy,
        'command_classifier': classify, 'event_observer': observe,
        'execution_raw': raw, 'started_raw': started_raw}
    return case


@pytest.fixture
def adapter_factory(bound, fixed_clock, tmp_path, monkeypatch):
    """One fresh selected S/attempt; only Git and the exact declared peer run."""
    active = {'case': None, 'dispatches': 0, 'prepared': False}
    for name, real in _REAL_PROCESS.items():
        def bounded_process(argv, *args, _real=real, _name=name, **kwargs):
            assert isinstance(argv, (list, tuple)) and argv
            if argv[0] != 'git':
                case = active['case']
                assert case is not None and _name == 'Popen'
                assert list(argv) == case['execution']['argv']
                assert kwargs['cwd'] == case['execution']['working_directory']
                assert kwargs['env'] == case['execution']['environment']
                assert active['dispatches'] == 0
                active['dispatches'] += 1
            return _real(argv, *args, **kwargs)
        monkeypatch.setattr(subprocess, name, bounded_process)
    with ExitStack() as stack:
        identity = authority.dependency_identity(stream_snapshot_profile=1)
        controls = stack.enter_context(authority.loaded_dependencies(identity))
        def build(*, peer_mode='no_tools', max_evidence_bytes=None):
            assert active['prepared'] is False, 'one selected S cannot be reused for another attempt'
            active['prepared'] = True
            case = make_adapter_case(bound, tmp_path / 'adapter-fixture', controls,
                                     peer_mode=peer_mode, max_evidence_bytes=max_evidence_bytes)
            active['case'] = case
            case['dispatch_accounting'] = active
            return case
        yield build


@pytest.fixture
def adapter_case(adapter_factory):
    return adapter_factory()


def run_to_terminal_refusal(case):
    """Actual init/callback milestones, followed by honest incomplete-phase stop."""
    with pytest.raises(case['controls']['budgeted_cborg'].BudgetStop, match=TERMINAL_REFUSAL) as caught:
        case['runner'].execute_child(**case['kwargs'])
    case['terminal_error'] = caught.value
    assert case['runner'].report()['state'] == 'failed'
    assert case['dispatch_accounting']['dispatches'] == 1
    return case


def initialized_files(case):
    selected = case['selection']
    observations = tuple(sorted(Path(selected.role('observations_root')).glob('*.json')))
    assert len(observations) == 1
    return {'observation': c.strict_json(observations[0].read_bytes()),
        'binding': c.strict_json(Path(selected.role('session_binding')).read_bytes()),
        'journal': c.strict_json(Path(selected.role('journal')).read_bytes()),
        'records': tuple(c.strict_json(Path(row['path']).read_bytes()) for row in
            c.strict_json(Path(selected.role('journal')).read_bytes())['records'])}


def track_actual_readers(case, monkeypatch):
    """Observe real calls without substituting capture, limits or authority."""
    rows, runs = [], []
    read = streams.read_live_stream
    loaded = capture._loaded
    def tracked_read(path, role, **kwargs):
        context = kwargs.get('coordination')
        assert type(context) is coordination._OwnerReaderContext
        budget = coordination.current_reader_budget()
        scope = profile._ACTIVE.get()
        assert context.budget is budget and scope._parent is case['parent_scope']
        assert scope._budget is budget
        row = {'caller': sys._getframe(1).f_code.co_name, 'role': role,
            'context': context, 'scope': scope, 'budget': budget,
            'reader_scope': coordination._SCOPE.get(), 'thread': threading.current_thread()}
        member = read(path, role, **kwargs)
        row['member'] = member
        rows.append(row)
        return member
    def tracked_loaded(*args, **kwargs):
        run = loaded(*args, **kwargs)
        runs.append(run)
        return run
    monkeypatch.setattr(streams, 'read_live_stream', tracked_read)
    monkeypatch.setattr(capture, '_loaded', tracked_loaded)
    case.update(reader_rows=rows, captured_runs=runs)
    return case


def assert_actual_initialization(case):
    documents = initialized_files(case)
    observation, binding = documents['observation'], documents['binding']
    owner_raw = case['runner'].owner_raw()
    assert owner_raw == (case['attempt'] / 'stream-owner.json').read_bytes()
    owner = c.strict_json(owner_raw)
    assert owner['execution_sha256'] == c.sha(case['execution_raw'])
    assert owner['started_sha256'] == c.sha(case['started_raw'])
    assert observation['observation_type'] == 'initialized' and observation['version'] == 2
    assert observation['payload']['owner']['sha256'] == c.sha(owner_raw)
    assert observation['session_id'] == binding['session_id'] == SESSION
    assert binding['execution']['sha256'] == c.sha(case['execution_raw'])
    assert binding['started']['sha256'] == c.sha(case['started_raw'])
    assert documents['journal']['execution_sha256'] == c.sha(case['execution_raw'])
    assert [row['record_type'] for row in documents['records']] == ['genesis', 'session_bound']
    assert len(documents['journal']['records']) == 2
    assert (case['attempt'] / 'registration.json').read_bytes() == case['execution_raw']
    assert (case['attempt'] / 'started.json').read_bytes() == case['started_raw']
    assert case['received_instruction'].read_bytes() == case['instruction'].read_bytes()
    assert json.loads(case['received_argv'].read_text()) == case['execution']['argv']
    assert case['adapter']._initialized is True
    assert any(row.get('type') == 'system' and row.get('subtype') == 'init' for row in case['observed'])
    for role in ('phase1_full', 'phase1_receipt', 'phase1_core'):
        assert not Path(case['selection'].role(role)).exists()
    return documents


def test_actual_declared_peer_initializes_owner_capture_before_expected_phase_refusal(
        adapter_case, monkeypatch):
    case = track_actual_readers(adapter_case, monkeypatch)
    # #4737: the real scope and adapter retain different JSON encodings of
    # the same typed declaration; activation must compare normalized values.
    scope = case['parent_scope']
    assert scope is profile._ACTIVE.get() and scope._parent is None
    profile_raw = c.canonical(case['profile'])
    assert scope.profile != profile_raw
    assert c.canonical(c.strict_json(scope.profile)) == profile_raw
    assert case['adapter']._owner_profile_raw == profile_raw
    # Private real proof is exercised; the public selected launch remains shut.
    with pytest.raises(ValueError):
        registration.verified(case['execution_raw'])
    assert case['dispatch_accounting']['dispatches'] == 0
    with no_nested_loaders(monkeypatch, case['controls']):
        run_to_terminal_refusal(case)
    assert_actual_initialization(case)
    assert [row['type'] for row in case['observed']] == ['control_response', 'system']
    assert case['classified'] == [] and case['reader_rows'] and case['captured_runs']
    grouped = {}
    for row in case['reader_rows']:
        assert row['thread'] is not threading.current_thread()
        assert row['scope']._parent is case['parent_scope'] and not row['scope'].live
        assert row['reader_scope'].budget is row['budget']
        grouped.setdefault(id(row['context']), []).append(row)
    complete_layers = [rows for rows in grouped.values() if
        {'_observed_endpoint', '_live_streams'} <= {row['caller'] for row in rows}]
    assert complete_layers
    for rows in complete_layers:
        context = rows[0]['context']
        assert all(row['context'] is context and row['budget'] is context.budget for row in rows)
        for caller in ('_observed_endpoint', '_live_streams'):
            assert {r['role'] for r in rows if r['caller'] == caller} == {'transcript', 'control'}
        with pytest.raises(ValueError):
            context.require_current()
    for run in case['captured_runs']:
        assert run.value == case['execution'] and run.binding.session_id == SESSION
        assert run.binding.execution.raw == case['execution_raw']
        assert len(run.observations) == 1 and len(run.history.records) == 2
        owners = [row for row in run.pool.members if row.captured.pin.role == 'owner']
        assert len(owners) == 1 and owners[0].captured.raw == case['runner'].owner_raw()
    before = case['adapter'].report(complete=False)
    assert TERMINAL_REFUSAL in before['controller_stop']
    assert before['draft_gate_passed'] is False
    # Stopped selected diagnostics must never fall back to a new live loader.
    def forbidden(*args, **kwargs):
        pytest.fail('selected complete report invented a live reconstruction')
    with monkeypatch.context() as patch:
        patch.setattr(capture, '_load', forbidden)
        patch.setattr(capture, '_load_live', forbidden)
        patch.setattr(profile, 'bind_reader_context', forbidden)
        report = case['adapter'].report(complete=True)
    assert report['controller_stop'] == before['controller_stop']
    assert report['draft_gate_passed'] is False
    assert case['runner'].report()['execution_authorized'] is False


def test_actual_readonly_callback_uses_existing_short_classifier_budget(adapter_factory, monkeypatch):
    case = track_actual_readers(adapter_factory(peer_mode='readonly'), monkeypatch)
    starts = []
    from data_sheets_schema import native_owner_control_v1 as control_module
    from types import SimpleNamespace
    import time
    actual_ns = time.monotonic_ns
    def record_work_start():
        now = actual_ns()
        frame = sys._getframe(1)
        if frame.f_code.co_name == '_start_work':
            channel = frame.f_locals['self']
            starts.append({'kind': frame.f_locals['kind'], 'start_ns': now,
                'owner_budget': channel._owner_budget, 'contract': deepcopy(channel.contract)})
        return now
    monkeypatch.setattr(control_module, 'time', SimpleNamespace(monotonic_ns=record_work_start, sleep=time.sleep))
    with no_nested_loaders(monkeypatch, case['controls']):
        run_to_terminal_refusal(case)
    assert_actual_initialization(case)
    assert len(case['classified']) == 1
    classified = case['classified'][0]
    assert classified['result'][0] == 'prescribed'
    assert classified['thread'] is not threading.current_thread()
    assert classified['scope']._parent is case['parent_scope'] and not classified['scope'].live
    worker_starts = [row for row in starts if row['kind'] == 'classifier']
    assert len(worker_starts) == 1
    started = worker_starts[0]; owner_budget = started['owner_budget']
    assert started['contract']['callback_timeout_seconds'] == 2
    assert started['contract']['observer_timeout_seconds'] == 120
    assert started['contract']['runtime_callback_timeout_seconds'] == 125
    assert classified['budget'].deadline_ns == min(owner_budget.deadline_ns,
        started['start_ns'] + 2_000_000_000)
    assert all(a is b for a, b in zip(classified['budget'].stop_events, owner_budget.stop_events))
    response = c.strict_json(case['received_response'].read_bytes())
    assert response['response']['request_id'] == 'fixture-request'
    assert response['response']['subtype'] == 'success'
    assert any(row['type'] == 'user' for row in case['observed'])
    # This protocol settlement does not execute cat or any real helper.
    assert case['dispatch_accounting']['dispatches'] == 1


def test_default_constructor_keeps_its_independent_complete_permission_proof(adapter_case):
    case = adapter_case
    # Existing default paths still reconstruct full C/E, not selected C under a
    # dropped tag. The same inputs are freshly rendered through the real path.
    default = controller.compose(case['spec'], runtime_path=case['runtime_path'],
        instruction_path=case['instruction'], max_draft_checks=3)
    assert 'stream_snapshot_profile' not in default
    assert controller.verified_composition(c.canonical(default)) == default
    default_path = case['root'] / 'default-composition.json'; default_path.write_bytes(c.canonical(default))
    system = case['root'] / 'system.txt'
    expected = registration.permission_expectation(case['runtime'], default, case['spec'],
        system.read_text() + policy.command_guidance(default['policy']),
        case['attempt'] / 'cli_config', authority.dependency_identity())
    permission = case['root'] / 'default-fabricated-permission.json'
    permission.write_bytes(c.canonical(fabricated_manifest(expected,
        case['spec']._native_shared_generation_capture.document(),
        case['root'] / 'default-fabricated-permission-records', case['spec'].bundle.read_bytes())))
    value = registration.registration(default_path, case['root'] / 'system.txt',
        permission_probe_path=permission,
        attempt_id=case['attempt'].name, attempt_directory=case['attempt'],
        evidence_directory=case['evidence'], max_draft_checks=3)
    raw = c.canonical(value)
    assert registration.verified(raw) == value
    adapter = controller.CallbackAdapter(c.canonical(default), execution=value, registration_raw=raw)
    assert type(adapter) is controller.CallbackAdapter
    assert adapter.value == default and adapter.policy == case['adapter'].policy
    assert adapter._activated is adapter._initialized is False
    assert case['dispatch_accounting']['dispatches'] == 0
    # Merely possessing selected bytes cannot construct the public adapter.
    with pytest.raises(ValueError):
        controller.CallbackAdapter(case['composition_raw'], execution=case['execution'],
                                   registration_raw=case['execution_raw'])

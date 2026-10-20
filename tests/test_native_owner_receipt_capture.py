"""Receipt/recorder capture component controls, not independent helper success.

Parameter tests use a genuine bound rendering. Pending-call tests use a real
captured default run with explicitly fabricated protocol frames. Reader-scope
controls use the existing synthetic private association and actual lease types.
No test here claims that a selected recorder completed all final obligations.
"""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.test_native_shared_controller import bound, native_spec, declaration
from tests.test_native_shared_registration import execution
from tests.test_native_shared_live_capture import started
from tests.test_native_shared_results import initial
from tests.test_native_owner_live_reader import reader_case, entered_case
from tests.test_native_owner_runner import selected_controls, fixed_clock
from data_sheets_schema import native_shared_capture as capture
from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_observations as observed
from data_sheets_schema import native_shared_policy as policy
from data_sheets_schema import native_shared_selection as selections


def recorder_parameters(bound):
    """Parser-input fixture only; this helper supplies no owner/admission."""
    spec, _, instruction = bound
    value = policy.command_policy(spec, str(instruction))
    run = SimpleNamespace(composition={'policy': value,
        'render_spec': spec.render_spec(), 'instruction_path': str(instruction)})
    values = {'project': spec.project, 'method': spec.method, 'label': spec.label,
        'input_bundle': str(spec.bundle), 'prompts': tuple(selections.ASSET_HASHES),
        'prompt_text': None, 'condition': None, 'arm': 'baseline', 'runtime': None,
        'provider': None, 'bundle_for_spec': None, 'reasoning_effort': spec.reasoning_effort,
        'phase_specs': (), 'phases_skipped': (), 'manifest': str(spec.manifest),
        'chunk_manifest': str(spec.chunk_manifest), 'receipt_expected': False,
        'stated_profile': spec.profile,
        'render_spec_json': json.dumps(spec.render_spec(), sort_keys=True, separators=(',', ':')),
        'prompt_text_env': 'D4D_LAUNCH_INSTRUCTION'}
    supplied = {'project', 'method', 'label', 'input_bundle', 'prompts', 'manifest',
        'chunk_manifest', 'reasoning_effort', 'stated_profile', 'render_spec_json', 'prompt_text_env'}
    return run, spec, {'values': values,
        'sources': {key: 'COMMANDLINE' if key in supplied else 'DEFAULT' for key in values},
        'instruction_path': str(instruction)}


def test_recorder_parameter_envelope_uses_actual_render_and_original_instruction(bound):
    run, spec, parameters = recorder_parameters(bound)
    capture._recorder_parameters(run, spec, parameters)
    assert len(parameters['values']) == 20
    assert set(parameters['values']) == set(parameters['sources'])
    for change in ('method', 'manifest', 'prompt_order', 'prompt_list', 'source',
                   'extra_default_source', 'extra_option', 'missing', 'extra',
                   'instruction', 'render_json'):
        changed = deepcopy(parameters)
        if change == 'method': changed['values']['method'] += '_foreign'
        elif change == 'manifest': changed['values']['manifest'] += '.foreign'
        elif change == 'prompt_order': changed['values']['prompts'] = tuple(reversed(changed['values']['prompts']))
        elif change == 'prompt_list': changed['values']['prompts'] = list(changed['values']['prompts'])
        elif change == 'source': changed['sources']['project'] = 'DEFAULT'
        elif change == 'extra_default_source': changed['sources']['arm'] = 'COMMANDLINE'
        elif change == 'extra_option': changed['values']['receipt_expected'] = True
        elif change == 'missing': del changed['values']['runtime']
        elif change == 'extra': changed['values']['unregistered'] = None
        elif change == 'instruction': changed['instruction_path'] += '.foreign'
        else: changed['values']['render_spec_json'] += ' '
        with pytest.raises(ValueError):
            capture._recorder_parameters(run, spec, changed)
    capture._recorder_parameters(run, spec, parameters)


def test_recorder_parameter_schema_and_fixed_command_are_closed(bound):
    run, spec, parameters = recorder_parameters(bound)
    for bad in (None, [], {**parameters, 'trusted': True},
                {**parameters, 'sources': {**parameters['sources'], 'extra': 'DEFAULT'}},
                {**parameters, 'instruction_path': Path(parameters['instruction_path'])}):
        with pytest.raises(ValueError):
            capture._recorder_parameters(run, spec, bad)
    original = run.composition['policy']['native_shared_helpers']['recorder']
    for suffix in (' --unknown x', ' --project duplicate', ' --label'):
        run.composition['policy']['native_shared_helpers']['recorder'] = original + suffix
        with pytest.raises(ValueError):
            capture._recorder_parameters(run, spec, parameters)
    run.composition['policy']['native_shared_helpers']['recorder'] = original
    capture._recorder_parameters(run, spec, parameters)


def receipt_prefix(started):
    """Real default capture with synthetic prerequisite settlements, no helper."""
    run, _ = initial(started)
    session = run.binding.session_id
    contract = run.composition['policy']['pretool_control']
    native, parent = [], []
    paths = run.spec._agentic_artifact_paths
    commands = run.composition['policy']['native_shared_helpers']
    actions = [('Bash', {'command': commands['chunk_check']}),
        ('Bash', {'command': commands['source_scope']}),
        ('Write', {'file_path': paths['full'], 'content': 'fixture full'}),
        ('Write', {'file_path': paths['receipt'], 'content': 'fixture receipt'}),
        ('Bash', {'command': commands['full_schema']}),
        ('Bash', {'command': commands['full_terms']}),
        ('Bash', {'command': commands['phase1_receipts']})]
    for number, (tool, inputs) in enumerate(actions, 1):
        identity, callback_id = 'receipt-fixture-' + str(number), 'receipt-callback-' + str(number)
        native.append({'type': 'assistant', 'session_id': session, 'message': {'role': 'assistant',
            'content': [{'type': 'tool_use', 'id': identity, 'name': tool, 'input': deepcopy(inputs)}]}})
        request = {'type': 'control_request', 'request_id': callback_id,
            'request': {'subtype': 'hook_callback', 'callback_id': contract['callback_id'],
                'input': {'hook_event_name': contract['event'], 'cwd': run.binding.working_directory,
                    'tool_use_id': identity, 'tool_name': tool, 'tool_input': deepcopy(inputs)}}}
        native.append(request)
        parent.append({'kind': 'decision', 'request': deepcopy(request), 'classification': 'prescribed',
            'basis': 'fabricated component protocol fixture, not executed permission',
            'response': {'type': 'control_response', 'response': {'subtype': 'success',
                'request_id': callback_id, 'response': {}}}})
        if number != len(actions):
            native.append({'type': 'user', 'session_id': session,
                'message': {'role': 'user', 'content': [{'type': 'tool_result', 'tool_use_id': identity,
                    'is_error': False, 'content': 'fixture successful settlement'}]},
                'tool_use_result': {'exitCode': 0, 'stdout': 'fixture successful settlement'}})
    attempt = Path(run.value['attempt_directory'])
    for path, rows in ((attempt / 'transcript.jsonl', native), (attempt / 'control.jsonl', parent)):
        path.write_bytes(path.read_bytes() + b''.join(c.canonical(row) + b'\n' for row in rows))
    return capture._load(run.selection.registration.pin.path)


def _prefix_rows(prefix, rows):
    raw = b''.join(c.canonical(row) + b'\n' for row in rows)
    return c.EvidencePrefix(prefix.stream, prefix.path, raw, len(raw), c.sha(raw), len(rows))


def test_pending_receipt_requires_actual_call_callback_admission_and_phase(started):
    run = receipt_prefix(started)
    assert run.trace().pending() == ('receipt-fixture-7',)
    assert capture._pending_receipt_or_recorder(run, ('phase1_receipts',)) == 'phase1_receipts'
    with pytest.raises(ValueError, match='purpose'):
        capture._pending_receipt_or_recorder(run, ('recorder',))
    # Loss of the actual admission cannot be covered by the caller's chosen role.
    decisions = [row for _, _, row in observed.rows(run.control)]
    no_admission = replace(run, control=_prefix_rows(run.control, decisions[:-1]))
    with pytest.raises(ValueError, match='admission'):
        capture._pending_receipt_or_recorder(no_admission, ('phase1_receipts',))
    denied = deepcopy(decisions)
    denied[-1]['classification'] = 'not_prescribed'
    denied[-1]['response']['response']['response'] = {'hookSpecificOutput': {
        'hookEventName': 'PreToolUse', 'permissionDecision': 'deny',
        'permissionDecisionReason': 'Outside the registered tool policy: ' + denied[-1]['basis']}}
    with pytest.raises(ValueError, match='admission'):
        capture._pending_receipt_or_recorder(replace(run, control=_prefix_rows(run.control, denied)), ('phase1_receipts',))


def test_missing_context_never_defaults_inside_actual_selected_scope(reader_case, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('missing explicit context reached reconstruction or path work')
    monkeypatch.setattr(capture, '_load_live', forbidden)
    monkeypatch.setattr(capture, '_base', forbidden)
    # selected_controls already owns an original loader, before any reader entry.
    with pytest.raises(ValueError, match='explicit owner context'):
        capture._refuse_implicit_owner_context(None)
    with entered_case(reader_case) as context:
        capture._refuse_implicit_owner_context(context)
        for operation in (
            lambda: capture.require_recorder_write('/foreign', record={}),
            lambda: capture.selected_receipt_paths(reader_case['selection'].registration.pin.path),
            lambda: capture.live_receipt_block(reader_case['selection'].registration.pin.path,
                full_path='/full', receipt_path='/receipt'),
            lambda: capture.live_provenance_block(reader_case['selection'].registration.pin.path),
        ):
            with pytest.raises(ValueError, match='explicit owner context'):
                operation()


def test_escaped_or_foreign_owner_cannot_reconstruct_a_writer(reader_case, monkeypatch):
    with entered_case(reader_case) as context:
        pass
    monkeypatch.setattr(capture, '_load_live', lambda *a, **k: pytest.fail('expired context reached live capture'))
    with pytest.raises(ValueError):
        capture.require_recorder_write('/foreign', owner_context=context, record={})
    with pytest.raises(ValueError, match='exact owner context'):
        capture.require_recorder_write('/foreign', owner_context=object(), record={})


def test_default_writer_guard_is_refusal_only_without_selected_scope(monkeypatch):
    monkeypatch.setattr(capture, '_load_live', lambda *a, **k: pytest.fail('default writer acquired a live scope'))
    monkeypatch.setattr(capture, '_base', lambda *a, **k: pytest.fail('default writer reconstructed authority'))
    capture._refuse_implicit_owner_context(None)
    # Ordinary recorded/default writers retain their own path validation.
    assert capture.require_recorder_write('ordinary-relative-record.yaml', record={}) is None


def test_record_identity_uses_given_run_and_never_loads_another_basis(started, monkeypatch):
    run, _ = initial(started)
    record = {'prompts': {'request': {'spec': deepcopy(run.composition['render_spec'])}},
              'native_shared_generation': {}}
    monkeypatch.setattr(capture, '_load', lambda *a, **k: pytest.fail('record identity silently changed its run basis'))
    monkeypatch.setattr(capture, '_load_live', lambda *a, **k: pytest.fail('record identity reacquired another live run'))
    # An actual initialization prefix cannot be promoted to final recorder evidence.
    with pytest.raises(ValueError, match='complete freshly reconstructed selected stages'):
        capture._record_matches_run(run, run.spec, record)
    changed = deepcopy(record)
    changed['prompts']['request']['spec']['run_date'] = '2099-01-01'
    with pytest.raises(ValueError):
        capture._record_matches_run(run, run.spec, changed)
    with pytest.raises(ValueError, match='mapping'):
        capture._record_matches_run(run, run.spec, None)


def test_cli_process_tokens_and_origin_are_not_collapsed_parsed_options(monkeypatch):
    """Synthetic interpreter metadata controls; not a positive helper process."""
    import sys
    import shlex
    from importlib.machinery import ModuleSpec
    from types import ModuleType
    from data_sheets_schema import native_execution_authority as authority
    expected = authority.ROOT / 'src/data_sheets_schema/cli/__main__.py'
    words = [sys.executable, '-m', 'data_sheets_schema.cli', 'provenance', 'record',
             '--project', 'dataset', '--method', 'selected-method']
    command = shlex.join(words)

    def install():
        main = ModuleType('__main__')
        main.__package__ = 'data_sheets_schema.cli'
        main.__file__ = str(expected)
        main.__spec__ = ModuleSpec('data_sheets_schema.cli.__main__', loader=None, origin=str(expected))
        monkeypatch.setitem(sys.modules, '__main__', main)
        monkeypatch.setattr(sys, 'orig_argv', list(words), raising=False)
        monkeypatch.setattr(sys, 'argv', [str(expected), *words[3:]])
        return main

    install()
    capture._require_cli_process(command)
    # These can yield the same Click values and ParameterSource mapping.
    for original in (
        [*words, '--project', 'dataset'],
        [*words[:5], '--method', 'selected-method', '--project', 'dataset'],
        [*words[:5], '--project=dataset', '--method', 'selected-method'],
        [*words[:3], '--manifest', '/foreign', *words[3:]],
        [words[0], '-B', *words[1:]],
        tuple(words),
    ):
        install()
        monkeypatch.setattr(sys, 'orig_argv', original)
        with pytest.raises(ValueError, match='exact registered argv'):
            capture._require_cli_process(command)
    class Word(str):
        pass
    install()
    monkeypatch.setattr(sys, 'orig_argv', [Word(words[0]), *words[1:]])
    with pytest.raises(ValueError, match='exact registered argv'):
        capture._require_cli_process(command)
    for change in ('missing_orig', 'main_object', 'main_name', 'package', 'missing_spec',
                   'spec_name', 'file', 'spec_origin', 'argv_origin'):
        main = install()
        if change == 'missing_orig': monkeypatch.delattr(sys, 'orig_argv')
        elif change == 'main_object': monkeypatch.setitem(sys.modules, '__main__', SimpleNamespace())
        elif change == 'main_name': main.__name__ = 'foreign'
        elif change == 'package': main.__package__ = 'foreign'
        elif change == 'missing_spec': main.__spec__ = None
        elif change == 'spec_name': main.__spec__.name = 'foreign.__main__'
        elif change == 'file': main.__file__ = str(expected.parent / 'foreign.py')
        elif change == 'spec_origin': main.__spec__.origin = str(expected.parent / 'foreign.py')
        else: monkeypatch.setattr(sys, 'argv', [str(expected.parent / 'foreign.py'), *words[3:]])
        with pytest.raises(ValueError):
            capture._require_cli_process(command)
    install()
    capture._require_cli_process(command)

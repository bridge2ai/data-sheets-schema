"""PR 6302 boundary-diagnostic replay with invented evidence, 2026-11-21.

Reviewed wire literals seed fabricated frames; this is neither a real native
observation nor qualification evidence. No native binary or provider runs.
"""
from copy import deepcopy
import json
from uuid import UUID
from types import SimpleNamespace

import pytest

from data_sheets_schema import native_shared_permissions as p
from data_sheets_schema import native_shared_permission_protocol as protocol
from data_sheets_schema import native_shared_permission_wire as wire
from data_sheets_schema import native_stage_root_diagnostic as diagnostic


def pin(raw):
    return {'sha256': p._sha(raw), 'bytes': len(raw)}


def identity(number):
    return str(UUID(int=number))


def fabricated_boundary():
    """Build independent closed frames without calling the wire validator."""
    expected = {
        'selection': {'path': '/production/selection.json'},
        'source': {'path': '/inputs/source.txt'}, 'permission_environment': {},
        'runtime': {'executable': {'path': '/fixed/native', 'version': wire.VERSION,
                    'init_version': wire.INIT_VERSION, 'sha256': wire.EXECUTABLE_SHA256},
                    'model': 'claude-opus-5', 'effort': 'high', 'budget_guard_usd': '1'},
        'policy': {'allowed_tools': ['Read', 'Write', 'Bash'],
                   'pretool_control': protocol.history_contract(),
                   'readonly_lookups': {'repository': '/work/project',
                       'inputs': ['/inputs/source.txt'], 'output_directories': ['/production/stage']}},
    }
    selected = {'stage_root': '/production/stage'}
    launch = {key: '/probe/boundary/' + key for key in
              ('config_root', 'stub_root', 'effect_root', 'evidence_root')}
    launch['cwd'] = '/work/project'
    policy = diagnostic.boundary_policy(expected, selected, launch)
    launch.update(argv=p.probe_argv(expected, policy, effect_root=launch['effect_root']),
        provider_url='http://127.0.0.1:18455',
        provider_source_sha256=p._sha(p.recipe_sources()['recipe/provider.py'].encode()),
        executable=deepcopy(expected['runtime']['executable']), exit_code=0,
        environment={'CLAUDE_CONFIG_DIR': launch['config_root'], 'PYTHONPATH': launch['stub_root'],
            'ANTHROPIC_BASE_URL': 'http://127.0.0.1:18455',
            'ANTHROPIC_API_KEY': 'd4d-local-permission-probe-token'},
        shutdown={'control_initialized': True, 'control_shutdown_complete': True,
                  'unfinished_control_workers': 0, 'child_reaped': True})
    case = diagnostic.boundary_case(launch)
    session = identity(1)
    ui = {'type': 'system', 'subtype': 'ui_invalidate', 'event': 'ui.render',
          'uuid': identity(2), 'session_id': session}
    ack = deepcopy(wire._REVIEWED['ack'])
    ack['response']['response']['user_output_styles_dir'] = launch['config_root'] + '/output-styles'
    init = deepcopy(wire._REVIEWED['init'])
    init.update(cwd=launch['cwd'], original_cwd=launch['cwd'], session_id=session,
                uuid=identity(3), additional_directories=[launch['effect_root']])
    call = deepcopy(wire._REVIEWED['assistant_call'])
    call.update(session_id=session, uuid=identity(4))
    call['message']['content'] = [{'type': 'tool_use', 'id': case['id'],
                                   'name': 'Read', 'input': deepcopy(case['input'])}]
    callback = {'type': 'control_request', 'request_id': identity(20), 'request': {
        'subtype': 'hook_callback', 'callback_id': policy['pretool_control']['callback_id'],
        'tool_use_id': case['id'], 'input': {'session_id': session, 'cwd': launch['cwd'],
            'transcript_path': launch['config_root'] + '/projects/-work-project/' + session + '.jsonl',
            'prompt_id': identity(21), 'permission_mode': 'dontAsk', 'effort': {'level': 'high'},
            'hook_event_name': 'PreToolUse', 'tool_name': 'Read',
            'tool_input': deepcopy(case['input']), 'tool_use_id': case['id']}}}
    refusal = (case['input']['file_path'] + ' is outside ' + launch['cwd']
               + '; --restricted confines the file tools to the working directory.')
    denial = {'type': 'system', 'subtype': 'permission_denied', 'tool_name': 'Read',
        'tool_use_id': case['id'], 'decision_reason_type': 'other',
        'decision_reason': '--restricted: path outside the working directory',
        'message': refusal, 'uuid': identity(5), 'session_id': session}
    result = {'type': 'user', 'parent_tool_use_id': None, 'session_id': session,
        'uuid': identity(6), 'timestamp': '2026-11-21T22:00:00Z',
        'message': {'role': 'user', 'content': [{'type': 'tool_result',
            'tool_use_id': case['id'], 'is_error': True, 'content': refusal}]},
        'tool_use_result': 'Error: ' + refusal,
        'tool_result_meta': [{'id': case['id'], 'non_execution_kind': 'permission-rule',
            'permission_decision': {'decision': 'reject', 'source': 'config', 'reason_type': 'other'}}]}
    completion = deepcopy(wire._REVIEWED['assistant_completion'])
    completion.update(session_id=session, uuid=identity(7))
    completion['message']['id'] = 'd4d_permission_1'
    terminal = deepcopy(wire._REVIEWED['terminal'])
    terminal.update(session_id=session, uuid=identity(8), num_turns=2,
        permission_denials=[{'tool_name': 'Read', 'tool_use_id': case['id'],
                            'tool_input': deepcopy(case['input'])}])
    events = [ui, ack, init, call, callback, denial, result, completion, terminal]
    basis = 'a registered input the instruction reads'
    controls = [
        {'kind': 'initialize_sent', 'policy_sha256': protocol.policy_digest(policy),
         'frame': protocol.initialize_frame(policy['pretool_control'])},
        {'kind': 'initialize_ack', 'frame': deepcopy(ack)},
        {'kind': 'decision', 'request': deepcopy(callback), 'classification': 'prescribed',
         'basis': basis, 'response': {'type': 'control_response', 'response': {'subtype': 'success',
             'request_id': callback['request_id'], 'response': protocol.hook_output('prescribed', basis)}}},
    ]
    document = {'kind': 'native_stage_root_boundary_diagnostic', 'version': 1,
        'launch': launch, 'policy': policy,
        'sentinel': {'path': case['input']['file_path'],
                    'before': pin(diagnostic.SENTINEL_BYTES), 'after': pin(diagnostic.SENTINEL_BYTES)}}
    return expected, selected, document, events, controls


def validate_fabricated(expected, selected, document, events, controls, *, after=None):
    transcript = b''.join(p._encoded(row) + b'\n' for row in events)
    control = b''.join(p._encoded(row) + b'\n' for row in controls)
    document['transcript'] = {'relative_path': 'transcript.jsonl', **pin(transcript)}
    document['control'] = {'relative_path': 'control.jsonl', **pin(control)}
    return diagnostic.validate_boundary_diagnostic(document, expected=expected, selected=selected,
        transcript_raw=transcript, control_raw=control, sentinel_before=diagnostic.SENTINEL_BYTES,
        sentinel_after=diagnostic.SENTINEL_BYTES if after is None else after)


def test_boundary_accepts_exact_admitted_callback_then_native_restriction():
    data = fabricated_boundary()
    assert validate_fabricated(*data) == {'checked': True, 'native_refused': True,
        'observer_admitted': True, 'sentinel_unchanged': True}


def test_boundary_pin_byte_lengths_require_integer_json_types():
    for field in ('sentinel_before', 'sentinel_after', 'transcript', 'control'):
        expected, selected, document, events, controls = fabricated_boundary()
        transcript = b''.join(p._encoded(row) + b'\n' for row in events)
        control = b''.join(p._encoded(row) + b'\n' for row in controls)
        document['transcript'] = {'relative_path': 'transcript.jsonl', **pin(transcript)}
        document['control'] = {'relative_path': 'control.jsonl', **pin(control)}
        if field.startswith('sentinel_'):
            changed_pin = document['sentinel'][field.removeprefix('sentinel_')]
        else:
            changed_pin = document[field]
        # Same numerical value and unchanged SHA/bytes must still refuse an
        # unsupported JSON type; ordinary dictionary equality accepts it.
        changed_pin['bytes'] = float(changed_pin['bytes'])
        with pytest.raises(ValueError):
            diagnostic.validate_boundary_diagnostic(document, expected=expected, selected=selected,
                transcript_raw=transcript, control_raw=control,
                sentinel_before=diagnostic.SENTINEL_BYTES, sentinel_after=diagnostic.SENTINEL_BYTES)


def test_boundary_refuses_rehashed_wire_or_authority_deviations():
    changes = ('grant_parent', 'grant_missing', 'init_grant', 'call_path', 'callback_path',
               'observer_denied', 'denial_text', 'result_text', 'result_success',
               'duplicate_uuid', 'terminal_denials', 'extra_event', 'extra_control', 'sentinel')
    for change in changes:
        expected, selected, document, events, controls = fabricated_boundary()
        after = None
        if change in ('grant_parent', 'grant_missing'):
            argv = document['launch']['argv']
            index = argv.index('--settings') + 1
            settings = json.loads(argv[index])
            if change == 'grant_parent':
                settings['permissions']['additionalDirectories'] = ['/probe/boundary']
            else:
                del settings['permissions']['additionalDirectories']
            argv[index] = json.dumps(settings, separators=(',', ':'))
        elif change == 'init_grant':
            events[2]['additional_directories'] = []
        elif change == 'call_path':
            events[3]['message']['content'][0]['input']['file_path'] += '.foreign'
        elif change == 'callback_path':
            events[4]['request']['input']['tool_input']['file_path'] += '.foreign'
            controls[2]['request'] = deepcopy(events[4])
        elif change == 'observer_denied':
            controls[2]['classification'] = 'not_prescribed'
        elif change == 'denial_text':
            events[5]['message'] += ' unrelated'
        elif change == 'result_text':
            events[6]['message']['content'][0]['content'] = 'File has not been read yet'
        elif change == 'result_success':
            events[6]['message']['content'][0]['is_error'] = False
        elif change == 'duplicate_uuid':
            events[6]['uuid'] = events[5]['uuid']
        elif change == 'terminal_denials':
            events[8]['permission_denials'] = []
        elif change == 'extra_event':
            events.append(deepcopy(events[-1]))
        elif change == 'extra_control':
            controls.append(deepcopy(controls[-1]))
        else:
            after = b'changed sentinel'
            document['sentinel']['after'] = pin(after)
        with pytest.raises(ValueError):
            validate_fabricated(expected, selected, document, events, controls, after=after)


def test_boundary_observer_blocks_unscripted_effects_before_callback_dispatch():
    for change in ('none', 'call_before_init', 'wrong_tool', 'wrong_path', 'repeated_call',
                   'callback_before_call', 'wrong_callback', 'repeated_callback'):
        _, _, document, events, _ = fabricated_boundary()
        observer = diagnostic._BoundaryObserver(document['launch'], SimpleNamespace(check=lambda: None))
        if change == 'call_before_init':
            with pytest.raises(ValueError):
                observer(events[3])
            continue
        observer(events[2])
        assert observer.cases == [diagnostic.boundary_case(document['launch'])]
        if change == 'callback_before_call':
            with pytest.raises(ValueError):
                observer(events[4])
            continue
        if change in ('wrong_tool', 'wrong_path'):
            block = events[3]['message']['content'][0]
            if change == 'wrong_tool':
                block['name'] = 'Write'
            else:
                block['input']['file_path'] += '-other'
            with pytest.raises(ValueError):
                observer(events[3])
            continue
        observer(events[3])
        if change == 'repeated_call':
            with pytest.raises(ValueError):
                observer(events[3])
            continue
        if change == 'wrong_callback':
            events[4]['request']['input']['tool_input']['file_path'] += '-other'
            with pytest.raises(ValueError):
                observer(events[4])
            continue
        observer(events[4])
        if change == 'repeated_callback':
            with pytest.raises(ValueError):
                observer(events[4])
        else:
            assert observer.called and observer.callback_seen

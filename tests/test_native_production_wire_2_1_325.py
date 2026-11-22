"""Offline production-reader controls from retained 2.1.325 wire bytes.

Historical permission traces remain unmodified negative qualification evidence.
Runtime declarations and helper prerequisites below are software fixtures, not
production observations. Constructed helper outputs are explicitly separate
from the retained permission stubs. No process, account or provider is invoked.
"""
import base64
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_observations as observations
from data_sheets_schema import native_shared_gate_primitives as gates
from data_sheets_schema import native_wire_2_1_325 as wire
from data_sheets_schema.native_shared_phase import COMMAND_NAMES, PhaseState


PACK = Path(__file__).parent / 'fixtures/native_permission_2_1_325/retained.json'
LABELS = ('r4/settled', 'round1_plan06/settled')
BASH_LABELS = ('r4/settled',)


def _decoded(record):
    raw = base64.b64decode(record['raw_base64'], validate=True)
    assert type(record['decoded_bytes']) is int
    assert len(raw) == record['decoded_bytes']
    assert hashlib.sha256(raw).hexdigest() == record['decoded_sha256']
    return raw


def retained(label=LABELS[0]):
    """Read exact retained bytes; manufacture only the surrounding runtime."""
    pack = json.loads(PACK.read_bytes())
    trace = pack['traces'][label]
    assert trace['qualification_expected'] == 'refuse'
    files = trace['files']
    native = _decoded(files['transcript.jsonl'])
    control = _decoded(files['control.jsonl'])
    events = [json.loads(raw) for raw in native.splitlines()]
    launch = json.loads(_decoded(files['launch.before.json']))
    policy = json.loads(_decoded(files['evidence_root/projection.json']))['probe_policy']
    init = next(row for row in events if row.get('type') == 'system' and row.get('subtype') == 'init')
    runtime = {'executable': deepcopy(launch['executable']), 'model': 'claude-opus-5[1m]',
        'auth': {'expected_api_key_source': init['apiKeySource']},
        'auxiliary_models': [], 'effort': 'high',
        'limits': {'contextWindow': 1000000, 'maxOutputTokens': 64000},
        'limits_basis': json.dumps({'kind': 'd4d_native_u4b_provisional_runtime_basis', 'version': 2,
            'model_aliases': {'requested': 'claude-opus-5[1m]',
                'returned': 'claude-opus-5', 'reported': 'claude-opus-5'}})}
    return {'raw': native, 'control_raw': control, 'events': events,
        'controls': [json.loads(raw) for raw in control.splitlines()],
        'runtime': runtime, 'policy': policy, 'session': init['session_id']}


def _prefix(stream, raw):
    assert raw.endswith(b'\n')
    return c.EvidencePrefix(stream, '/software-fixture/' + stream, raw,
        len(raw), c.sha(raw), len(raw.split(b'\n')) - 1)


def _encoded_rows(rows):
    """Encode constructed or mutated copies, never replace retained bytes."""
    return b''.join(c.canonical(row) + b'\n' for row in rows)


def _trace(value, *, events=None, controls=None):
    return observations.Trace(
        _prefix('transcript', value['raw'] if events is None else _encoded_rows(events)),
        _prefix('control', value['control_raw'] if controls is None else _encoded_rows(controls)),
        session_id=value['session'], policy=value['policy'], runtime=value['runtime'])


def _bash(value):
    calls = {}
    for event in value['events']:
        message = event.get('message')
        blocks = message.get('content', []) if type(message) is dict else []
        for block in blocks:
            if block.get('type') == 'tool_use':
                calls[block['id']] = (event, block)
            if (block.get('type') == 'tool_result' and block.get('is_error') is False
                    and type(event.get('tool_use_result')) is dict
                    and 'stdout' in event['tool_use_result']
                    and calls[block['tool_use_id']][1]['name'] == 'Bash'):
                return calls[block['tool_use_id']][0], event, block
    raise AssertionError('retained trace lacks successful Bash wire evidence')


def _phase(value):
    commands = {name: ('/software-fixture/python', '-m', 'fixture.helper', name)
        for name in COMMAND_NAMES}
    state = PhaseState(commands, full_path='/software-fixture/full.yaml',
        core_path='/software-fixture/core.yaml', report_path='/software-fixture/report.md',
        receipt_path='/software-fixture/receipt.yaml', working_directory='/software-fixture',
        runtime=value['runtime'])
    return state


def _schema_case(value, *, original_stub=False):
    """Manufacture phase prerequisites; retain or openly replace helper text."""
    state = _phase(value)
    for event in value['events'][:3]:
        state.observe(event)
    state._written.add('full')
    state._passed.update(chunk_check=(), source_scope=())
    original_call, original_result, _ = _bash(value)
    if original_stub:
        call, result = original_call, original_result
        command = call['message']['content'][0]['input']['command']
        state.commands[command] = 'full_schema'
    else:
        call, result = deepcopy(original_call), deepcopy(original_result)
        call['message']['content'][0]['input'] = {'command': next(
            command for command, kind in state.commands.items() if kind == 'full_schema')}
        result['message']['content'][0]['content'] = 'No issues found\n'
        result['tool_use_result']['stdout'] = 'No issues found\n'
    return state, call, result


def test_retained_wire_recognition_is_separate_from_helper_or_run_qualification():
    for label in LABELS:
        value = retained(label)
        before = value['raw']
        assert wire.profile(value['runtime']) is True
        assert wire.ui_prefix_session(value['events'][0], value['runtime']) == value['session']
        if label in BASH_LABELS:
            _, event, block = _bash(value)
            assert wire.missing_numeric_bash_success(event, block, value['runtime']) is True
            assert 'd4d_shared_permission_stub' in json.loads(block['content'])
        assert value['raw'] == before
        assert json.loads(before.splitlines()[0]) == value['events'][0]


def test_profile_requires_the_complete_reviewed_executable_identity():
    value = retained()
    for field, altered in (('version', '2.1.325'), ('init_version', '2.1.324'),
                           ('sha256', '0' * 64), ('version', None), ('init_version', True)):
        runtime = deepcopy(value['runtime'])
        runtime['executable'][field] = altered
        assert wire.profile(runtime) is False
        with pytest.raises(ValueError):
            wire.ui_prefix_session(value['events'][0], runtime)
        _, event, block = _bash(value)
        assert wire.missing_numeric_bash_success(event, block, runtime) is False
    assert wire.profile(None) is False
    assert wire.profile({}) is False


def test_ui_prefix_closed_shape_and_uuid_types():
    value = retained()
    for field, altered in (('type', 'assistant'), ('subtype', 'init'), ('event', 'ui.other'),
                           ('session_id', 'not-a-uuid'), ('session_id', True),
                           ('uuid', value['events'][0]['uuid'].upper()),
                           ('uuid', 'not-a-uuid'), ('extra', False)):
        event = deepcopy(value['events'][0])
        event[field] = altered
        with pytest.raises(ValueError):
            wire.ui_prefix_session(event, value['runtime'])


def test_missing_numeric_result_requires_explicit_false_and_text():
    value = retained()
    _, original, _ = _bash(value)
    for field in ('interrupted', 'isImage', 'noOutputExpected'):
        for altered in (None, 0, '', [], True, 'false'):
            event = deepcopy(original)
            if altered is None:
                event['tool_use_result'].pop(field)
            else:
                event['tool_use_result'][field] = altered
            with pytest.raises(ValueError):
                wire.missing_numeric_bash_success(event, event['message']['content'][0], value['runtime'])
    for altered in (None, 0, '', True):
        event = deepcopy(original)
        event['message']['content'][0]['is_error'] = altered
        with pytest.raises(ValueError):
            wire.missing_numeric_bash_success(event, event['message']['content'][0], value['runtime'])
    for field in ('stdout', 'stderr'):
        event = deepcopy(original)
        event['tool_use_result'][field] = False
        with pytest.raises(ValueError):
            wire.missing_numeric_bash_success(event, event['message']['content'][0], value['runtime'])


def test_missing_numeric_result_refuses_effect_and_pending_metadata():
    value = retained()
    _, original, _ = _bash(value)
    for field, altered in (('error', 'failed'), ('backgroundTaskId', 'running'),
            ('background_task_id', 'running'), ('persistedOutputPath', '/software-fixture/output'),
            ('backgroundTaskId', False), ('background_task_id', 0),
            ('persistedOutputPath', ''), ('stdout', None)):
        event = deepcopy(original)
        event['tool_use_result'][field] = altered
        with pytest.raises(ValueError):
            wire.missing_numeric_bash_success(event, event['message']['content'][0], value['runtime'])


def test_numeric_aliases_never_select_the_missing_numeric_exception():
    value = retained()
    _, original, _ = _bash(value)
    for metadata in ({'exitCode': 0}, {'exit_code': 0}, {'exitCode': False},
            {'exitCode': 0.0}, {'exitCode': 0, 'exit_code': 1}, {'exit_code': None}):
        event = deepcopy(original)
        event['tool_use_result'].update(metadata)
        assert wire.missing_numeric_bash_success(
            event, event['message']['content'][0], value['runtime']) is False


def test_phase_accepts_retained_prefix_and_preserves_its_event_positions():
    for label in LABELS:
        value = retained(label)
        state = _phase(value)
        for event in value['events'][:3]:
            assert state.observe(event) == ()
        assert state._index == 3
        assert state._session == value['session']
        assert state.report()['passed'] is True


def test_phase_prefix_cannot_repeat_move_or_change_session():
    value = retained()
    prefix = value['events'][:3]
    variants = [prefix[:1] + prefix, [prefix[1], prefix[0], prefix[2]],
        [prefix[1], prefix[2], prefix[0]], prefix + prefix[:1]]
    foreign = deepcopy(prefix)
    foreign[0]['session_id'] = '00000000-0000-4000-8000-000000000099'
    variants.append(foreign)
    for rows in variants:
        state = _phase(value)
        with pytest.raises(ValueError):
            for event in rows:
                state.observe(event)
        assert state.report()['passed'] is False


def test_constructed_schema_success_retains_unknown_exit_status():
    value = retained()
    state, call, result = _schema_case(value)
    state.observe(call)
    state.observe(result)
    check = state.report()['checks'][-1]
    assert check['exit_code'] is None
    assert check['exit_status'] is None
    assert check['status_basis'] == wire.STATUS_BASIS
    assert 'full_schema' in state.report()['current_checks']


def test_retained_permission_stub_cannot_earn_a_production_helper_pass():
    for label in BASH_LABELS:
        state, call, result = _schema_case(retained(label), original_stub=True)
        state.observe(call)
        with pytest.raises(ValueError):
            state.observe(result)
        assert 'full_schema' not in state.report()['current_checks']


def test_phase_refuses_wrong_output_and_numeric_alias_bypasses():
    value = retained()
    for kind in ('random', 'disagree', 'boolean_exit', 'float_exit', 'conflicting_exit', 'interrupted'):
        state, call, result = _schema_case(value)
        meta = result['tool_use_result']
        block = result['message']['content'][0]
        if kind == 'random':
            meta['stdout'] = block['content'] = 'arbitrary successful-looking output'
        elif kind == 'disagree':
            meta['stdout'] = 'another output'
        elif kind == 'boolean_exit':
            meta['exitCode'] = False
        elif kind == 'float_exit':
            meta['exitCode'] = 0.0
        elif kind == 'conflicting_exit':
            meta.update(exitCode=0, exit_code=1)
        else:
            meta['interrupted'] = True
        state.observe(call)
        with pytest.raises(ValueError):
            state.observe(result)
        assert 'full_schema' not in state.report()['current_checks']


def test_retained_initialization_and_callbacks_keep_exact_physical_references():
    for label in LABELS:
        value = retained(label)
        trace = _trace(value)
        identity = value['events'][3]['message']['content'][0]['id']
        request = trace.request(identity)
        assert request.call.line == 4
        assert request.callback.line == 5
        assert request.session_id == value['session']
        assert trace.transcript.raw == value['raw']
        assert trace.control.raw == value['control_raw']


def test_initialization_and_callback_mutations_refuse_exact_join():
    for change in ('policy', 'session', 'cwd', 'model', 'callback_input',
                   'duplicate_callback', 'control_frame', 'ack_frame'):
        value = retained()
        events, controls = deepcopy(value['events']), deepcopy(value['controls'])
        callback = events[4]
        if change == 'policy':
            value['policy']['pretool_control']['callback_id'] += '-changed'
        elif change == 'session':
            value['session'] = '00000000-0000-4000-8000-000000000099'
        elif change == 'cwd':
            events[2]['cwd'] += '-foreign'
        elif change == 'model':
            events[2]['model'] = 'foreign-model'
        elif change == 'callback_input':
            callback['request']['input']['tool_input']['file_path'] += '-foreign'
        elif change == 'duplicate_callback':
            events.insert(5, deepcopy(callback))
        elif change == 'control_frame':
            row = next(row for row in controls if row.get('kind') == 'decision')
            row['request']['request']['input']['tool_input']['file_path'] += '-foreign'
        else:
            row = next(row for row in controls if row.get('kind') == 'initialize_ack')
            row['frame']['response']['response']['hooks_applied'] = False
        with pytest.raises(ValueError):
            _trace(value, events=events, controls=controls)


def test_retained_denials_are_never_successful_effects():
    for label in LABELS:
        value = retained(label)
        trace = _trace(value)
        denials = [event for event in value['events']
            if event.get('type') == 'system' and event.get('subtype') == 'permission_denied']
        assert denials
        for event in denials:
            assert wire.permission_denial(event, value['runtime']) is True
            classified = trace.denial(event['tool_use_id'])
            assert classified is not None
            assert classified['classification'] in ('prescribed', 'not_prescribed', 'unclassifiable')
        string_results = [event for event in value['events']
            if event.get('type') == 'user' and type(event.get('tool_use_result')) is str
            and any(row.get('non_execution_kind') == 'permission-rule'
                for row in event.get('tool_result_meta', []))]
        assert string_results
        for event in string_results:
            identity = event['message']['content'][0]['tool_use_id']
            assert trace.denial(identity) is not None


def test_system_denial_is_a_sticky_phase_failure():
    value = retained()
    denial = next(event for event in value['events']
        if event.get('type') == 'system' and event.get('subtype') == 'permission_denied')
    state = _phase(value)
    for event in value['events'][:3]:
        state.observe(event)
    with pytest.raises(ValueError):
        state.observe(denial)
    assert state.report()['passed'] is False
    with pytest.raises(ValueError):
        state.before('Read', {'file_path': '/software-fixture/source'})


def test_joined_prescribed_denial_fails_on_its_actual_result():
    value = retained()
    trace = _trace(value)
    denial = next(event for event in value['events']
        if event.get('type') == 'system' and event.get('subtype') == 'permission_denied')
    identity = denial['tool_use_id']
    call = value['events'][trace.calls[identity][0] - 1]
    result = value['events'][trace.results[identity][0] - 1]
    classified = trace.denial(identity)
    assert classified['classification'] == 'prescribed'
    state = _phase(value)
    for event in value['events'][:3]:
        state.observe(event)
    state.observe(call)
    state.observe(denial)
    assert identity in state.report()['pending_tool_ids']
    with pytest.raises(ValueError):
        state.observe(result, denials={identity: classified})
    assert state.report()['passed'] is False


def test_constructed_nonzero_usage_does_not_import_probe_accounting_rules():
    value = retained()
    events = deepcopy(value['events'])
    terminal = events[-1]
    assert terminal['type'] == 'result'
    terminal['usage'].update(input_tokens=123, output_tokens=17,
        cache_read_input_tokens=31, cache_creation_input_tokens=0)
    terminal['modelUsage']['claude-opus-5'].update(inputTokens=123, outputTokens=17,
        cacheReadInputTokens=31, cacheCreationInputTokens=0)
    terminal['total_cost_usd'] = 0.01
    assistant = next(row for row in events if row.get('type') == 'assistant')
    assistant['message']['id'] = 'ordinary-production-message'
    trace = _trace(value, events=events)
    assert trace.frames[trace.terminal]['total_cost_usd'] == 0.01
    assert trace.frames[trace.terminal]['usage']['input_tokens'] == 123
    assert value['events'][-1]['total_cost_usd'] == 0


def test_system_denial_shape_mutations_refuse_without_probe_message_rules():
    value = retained()
    original = next(event for event in value['events']
        if event.get('type') == 'system' and event.get('subtype') == 'permission_denied')
    for field, altered in (('tool_name', 'Unknown'), ('tool_use_id', False),
            ('uuid', 'not-a-uuid'), ('session_id', 'not-a-uuid'),
            ('decision_reason', None), ('message', False), ('extra', True)):
        event = deepcopy(original)
        event[field] = altered
        with pytest.raises(ValueError):
            wire.permission_denial(event, value['runtime'])
    event = deepcopy(original)
    event['tool_use_id'] = 'ordinary-production-tool-id'
    assert wire.permission_denial(event, value['runtime']) is True


def _helper_outputs():
    """Construct source-documented CLI outputs; these are not retained frames."""
    paths = {'full': '/software-fixture/full.yaml', 'core': '/software-fixture/core.yaml'}
    commands = {name: ('/software-fixture/python', '-m', 'fixture.helper', name)
        for name in COMMAND_NAMES}
    commands['chunk_check'] += ('--chunk-manifest', '/software-fixture/chunks.yaml')
    for name in ('source_scope', 'final_scope', 'recorder'):
        commands[name] += ('--project', 'EXTERNAL')
    outputs = {
        'chunk_check': '   ✓ current /software-fixture/chunks.yaml: 3 canonical chunks under the selected rule\n',
        'source_scope': 'EXTERNAL\n   about     Declared dataset  <https://example.invalid/dataset>\n',
        'full_schema': 'No issues found\n', 'core_schema': 'No issues found\n',
        'full_terms': '✅ Validation passed\n',
        'final_scope': 'EXTERNAL\n   about     Declared dataset  <https://example.invalid/dataset>\n'
            '2 record(s) checked against the declaration\n'
            '   ✓ none is about a dataset its project declares distinct\n',
        'pair': "PASS: 3 schema-identical slots; projected slots=['resources']; "
            "per-record slots (exempt, must differ)=['id']\n"
            'Presence context: unavailable; recorded digest=None; schema_moved=False; ledger inventory=unknown\n'
            'Historical core inventory: {"status": "not_needed", "reason": '
            '"the existing digest comparison keeps presence checks strict"}\n',
        'recorder': '✓ /software-fixture/EXTERNAL_provenance.yaml\n',
    }
    facts = {'derived': True,
        'rule': 'shared slots copied from the full record; resources projected by id '
            'with full-only nested slots dropped; distributions built from '
            'file_collections (one per collection over the shared slots, '
            'total_bytes as bytes) and from each collection\'s File entries (one '
            'per file over the slots CoreDistribution and File share); dialect '
            'from the File entries when they agree on one value, else absent',
        'from': {'path': paths['full'], 'md5': 'a' * 32}, 'identity_slots': 3,
        'projected_slots': ['resources'], 'distribution_slots': {'collection': [], 'file': []},
        'conditional': {'dialect':
            'derived only when every File-level dialect in the full record agrees on one value'}}
    outputs['derive_core'] = ('✓ ' + paths['core'] + '\n' + json.dumps(facts)
        + '\n  linkml-validate: No issues found\n')
    outputs['derive_final_core'] = outputs['derive_core']
    return commands, paths, outputs


def test_helper_stdout_accepts_source_documented_constructed_outputs_only():
    commands, paths, outputs = _helper_outputs()
    for kind, stdout in outputs.items():
        wire.helper_stdout(kind, stdout, commands, paths)
        with pytest.raises(ValueError):
            wire.helper_stdout(kind, 'arbitrary output\n', commands, paths)
    for label in BASH_LABELS:
        _, result, _ = _bash(retained(label))
        for kind in outputs:
            with pytest.raises(ValueError):
                wire.helper_stdout(kind, result['tool_use_result']['stdout'], commands, paths)


def test_helper_stdout_rejects_wrong_path_type_count_and_semantic_markers():
    commands, paths, outputs = _helper_outputs()
    mutations = [
        ('chunk_check', outputs['chunk_check'].replace('chunks.yaml', 'foreign.yaml')),
        ('chunk_check', outputs['chunk_check'].replace(': 3 ', ': 0 ')),
        ('chunk_check', outputs['chunk_check'].replace(': 3 ', ': True ')),
        ('source_scope', outputs['source_scope'].replace('EXTERNAL', 'FOREIGN')),
        ('source_scope', outputs['source_scope'] + 'unreviewed output\n'),
        ('full_schema', outputs['full_schema'] + '[ERROR] invalid\n'),
        ('core_schema', 'No issues found; ignored failure\n'),
        ('full_terms', 'Validation passed\n'),
        ('final_scope', outputs['final_scope'].replace('2 record(s)', '1 record(s)')),
        ('final_scope', outputs['final_scope'].replace('   ✓ none', '   ERROR none')),
        ('pair', outputs['pair'].replace('PASS:', 'FAIL:')),
        ('pair', outputs['pair'].replace('schema-identical slots', 'unchecked slots')),
        ('pair', outputs['pair'].replace('"not_needed"', 'false')),
        ('pair', outputs['pair'].replace('schema_moved=False', 'schema_moved=0')),
        ('recorder', outputs['recorder'].replace('EXTERNAL_', 'FOREIGN_')),
        ('recorder', outputs['recorder'].replace('/software-fixture/', '/foreign/')),
    ]
    for kind in ('derive_core', 'derive_final_core'):
        mutations.append((kind, outputs[kind].replace('  linkml-validate: No issues found\n', '')))
        for before, after in (('"derived": true', '"derived": 1'),
                ('"identity_slots": 3', '"identity_slots": true'),
                ('/software-fixture/full.yaml', '/foreign/full.yaml'),
                ('"md5": "' + 'a' * 32, '"md5": "' + 'g' * 32)):
            mutations.append((kind, outputs[kind].replace(before, after)))
    for kind, stdout in mutations:
        assert stdout != outputs[kind]
        with pytest.raises(ValueError):
            wire.helper_stdout(kind, stdout, commands, paths)


def test_final_scope_informational_warnings_stay_bound_to_selected_records(monkeypatch):
    """Use the actual CLI emitter; only input readers and repo setup are mocked."""
    import click
    from click.testing import CliRunner
    from data_sheets_schema import scope
    from data_sheets_schema.cli.download import scope_cmd

    commands, paths, _ = _helper_outputs()
    selected = tuple(Path(paths[role]) for role in ('full', 'core'))
    callback = scope_cmd.callback
    monkeypatch.setitem(callback.__globals__, 'require_repo_context', lambda *args: None)
    monkeypatch.setitem(callback.__globals__, 'setup_repo_imports', lambda: None)
    monkeypatch.setattr(scope, 'all_scopes', lambda manifest: {'EXTERNAL': {
        'referent': 'Declared dataset', 'referent_id': 'https://example.invalid/dataset',
        'related_but_distinct': [{'name': 'Related dataset',
            'id': 'https://example.invalid/related', 'express_as': 'related_datasets'}]}})
    monkeypatch.setattr(scope, 'malformed_entries', lambda *args: [])
    monkeypatch.setattr(scope, 'check_manifest', lambda manifest: [])
    monkeypatch.setattr(scope, 'related_ids', lambda *args: {'https://example.invalid/related'})
    state = {'status': 'ok', 'refs': {str(path): [] for path in selected}}
    monkeypatch.setattr(scope, 'check_record', lambda project, path, manifest:
        (state['status'], 'software fixture diagnostic') if path == selected[0] else ('ok', None))
    monkeypatch.setattr(scope, 'foreign_references', lambda project, path, manifest:
        state['refs'][str(path)])

    def invoke():
        return callback(project='EXTERNAL', do_check=True, strict=True,
            selected_records=selected, manifest='/software-fixture/manifest.yaml')

    command = click.Command('actual-scope-emitter', callback=invoke)
    runner = CliRunner()
    for counts in ((0, 0), (1, 0), (5, 2)):
        state['refs'] = {str(path): [
            {'path': 'resources[' + str(index) + '].id',
             'value': 'https://example.invalid/related/' + str(index)}
            for index in range(count)] for path, count in zip(selected, counts)}
        result = runner.invoke(command)
        assert result.exit_code == 0, result.output
        wire.helper_stdout('final_scope', result.stdout, commands, paths)

    # The last actual emission includes two records, seven values, and a
    # truncated five-value record. Mutations target those genuine bytes.
    stdout = result.stdout
    assert '2 record(s), 7 value(s)' in stdout and '      … 1 more\n' in stdout
    for altered in (
            stdout.replace(paths['full'], '/foreign/full.yaml'),
            stdout.replace(paths['core'], paths['full']),
            stdout.replace('2 record(s), 7 value(s)', '1 record(s), 7 value(s)'),
            stdout.replace('2 record(s), 7 value(s)', '2 record(s), 8 value(s)'),
            stdout.replace('      … 1 more\n', '      … 2 more\n'),
            stdout.replace('      … 1 more\n', ''),
            stdout.replace('outside its declared slot:', 'unchecked warning:'),
            stdout.replace('      resources[0].id = ', '      malformed-value '),
            stdout + 'unreadable record\n'):
        assert altered != stdout
        with pytest.raises(ValueError):
            wire.helper_stdout('final_scope', altered, commands, paths)

    state['refs'] = {str(path): [] for path in selected}
    for status in ('unreadable', 'out_of_scope'):
        state['status'] = status
        result = runner.invoke(command)
        assert result.exit_code == 1
        with pytest.raises(ValueError):
            wire.helper_stdout('final_scope', result.stdout, commands, paths)


def _saved_gate_case(value):
    state, call, result = _schema_case(value)
    state.observe(call)
    state.observe(result)
    command = call['message']['content'][0]['input']['command']
    return {'events': value['events'][:3] + [call, result, {'type': 'result'}],
        'state': SimpleNamespace(spec=object(), commands={command: None}),
        'value': {'runtime': value['runtime']},
        'policy': {'native_shared_helpers': {'full_schema': command}},
        'phase_report': state.report()}


def test_saved_gate_preserves_null_status_and_requires_actual_phase_credit():
    prepared = _saved_gate_case(retained())
    result = gates.tool_history(prepared)
    check = result['bash_results'][0]
    assert result['passed'] is True
    assert check['exit_code'] is None and check['exit_status'] is None
    assert check['status_basis'] == wire.STATUS_BASIS
    for change in ('zero_exit', 'boolean_exit', 'missing_status', 'different_basis',
                   'failed_phase', 'duplicate_credit', 'foreign_tool', 'foreign_helper',
                   'policy', 'stdout_disagreement', 'runtime'):
        changed = deepcopy(prepared)
        phase = changed['phase_report']
        row = phase['checks'][0]
        if change == 'zero_exit':
            row['exit_code'] = 0
        elif change == 'boolean_exit':
            row['exit_status'] = False
        elif change == 'missing_status':
            row.pop('exit_status')
        elif change == 'different_basis':
            row['status_basis'] = 'invented_zero'
        elif change == 'failed_phase':
            phase['passed'] = False
        elif change == 'duplicate_credit':
            phase['checks'].append(deepcopy(row))
        elif change == 'foreign_tool':
            row['tool_use_id'] += '-foreign'
        elif change == 'foreign_helper':
            row['helper'] = 'core_schema'
        elif change == 'policy':
            changed['policy']['native_shared_helpers']['full_schema'] += '-foreign'
        elif change == 'stdout_disagreement':
            changed['events'][-2]['tool_use_result']['stdout'] = 'another output'
        else:
            changed['value']['runtime']['executable']['sha256'] = '0' * 64
        with pytest.raises(ValueError):
            gates.tool_history(changed)


def test_saved_gate_refuses_explicit_system_denial_before_completion():
    value = retained()
    prepared = _saved_gate_case(value)
    denial = next(row for row in value['events']
        if row.get('type') == 'system' and row.get('subtype') == 'permission_denied')
    prepared['events'].insert(-1, denial)
    with pytest.raises(ValueError):
        gates.tool_history(prepared)

"""Explicit CLI 2.1.325 label contract; sanitized evidence, no native calls.

The captured shape comes from a refused scripted observation. Tests grant no
account authority or execution acceptance. Dates are derived at test time.
"""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path

import pytest

from data_sheets_schema import native_capture_words as words
from data_sheets_schema import native_model_aliases as aliases
from data_sheets_schema import native_u4b_probe_sequence as sequence
from data_sheets_schema import native_u4b_runtime as runtime_reader
from data_sheets_schema import native_shared_runtime_values as runtime_values
from tests.test_native_model_aliases import current_stream, gate_result
from tests.test_native_shared_gates import isolated_modules, pure_gate_members
from tests.test_native_shared_observations import (
    SESSION, POLICY, alias_trace_frames, prefix,
)
from tests.test_native_shared_permissions import (
    fixture, fabricated_manifest, rows, put_rows, get, put, verify,
    prohibit_real_transports,
)
from tests.utils.native_shared_consumer_scope import observe_consumer_calls
from tests.utils.native_u4b_fixtures import admission_policy

FIXTURE = Path(__file__).parent / 'fixtures/native_cli_2_1_325'
PAIR = {'requested': 'claude-opus-5[1m]', 'returned': 'claude-opus-5',
        'reported': 'claude-opus-5'}
OLD_PAIR = {key: PAIR[key] for key in ('requested', 'returned')}


def raw(value):
    return sequence.canonical(value)


def load_fixture():
    events = [json.loads(line) for line in (FIXTURE / 'stdout.jsonl').read_bytes().splitlines()]
    stamp = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat().replace('+00:00', 'Z')
    for event in events:
        if event.get('timestamp') == 'FIXTURE_RELATIVE_UTC':
            event['timestamp'] = stamp
    return events, json.loads((FIXTURE / 'request.json').read_bytes())


def selected(*, version=4, provisional=False):
    new = version == (2 if provisional else 4)
    return {'model': PAIR['requested'], 'auxiliary_models': [],
        'executable': {'init_version': '2.1.325'},
        'limits': {'contextWindow': 1000000, 'maxOutputTokens': 64000},
        'limits_basis': raw({'kind': aliases.PROVISIONAL_KIND if provisional else aliases.KIND,
            'version': version, 'model_aliases': PAIR if new else OLD_PAIR}).decode()}


def transcript(events):
    return b''.join(raw(event) + b'\n' for event in events)


def legacy_events():
    events, request = load_fixture()
    events[1]['model'] = PAIR['requested']
    events[-1]['modelUsage'] = {PAIR['requested']: events[-1]['modelUsage'][PAIR['reported']]}
    return events, request


def mutate(events, change):
    events = deepcopy(events)
    usage = events[-1]['modelUsage']
    own = usage[PAIR['reported']]
    if change == '200k':
        own['contextWindow'] = 200000
    elif change == 'bool_context':
        own['contextWindow'] = True
    elif change == 'old_init':
        events[1]['model'] = PAIR['requested']
    elif change == 'old_usage':
        events[-1]['modelUsage'] = {PAIR['requested']: own}
    elif change == 'old_assistant':
        events[2]['message']['model'] = PAIR['requested']
    elif change == 'mixed_assistant':
        events[2]['model'] = PAIR['requested']
    elif change == 'mixed_usage':
        usage[PAIR['requested']] = deepcopy(own)
    elif change == 'ui_model':
        events[0]['model'] = PAIR['requested']
    elif change == 'init_message':
        events[1]['message'] = {'model': PAIR['requested']}
    elif change == 'terminal_model':
        events[-1]['model'] = PAIR['requested']
    elif change == 'terminal_message':
        events[-1]['message'] = {'model': PAIR['requested']}
    else:
        raise AssertionError(change)
    return events


def test_sanitized_real_shape_is_pinned_and_keeps_scripted_dummy_key():
    provenance = json.loads((FIXTURE / 'provenance.json').read_bytes())
    for name, expected in provenance['fixture_files'].items():
        content = (FIXTURE / name).read_bytes()
        assert len(content) == expected['bytes']
        assert hashlib.sha256(content).hexdigest() == expected['sha256']
        assert bytes([64]) not in content and b'/Users/' not in content
    invocation = json.loads((FIXTURE / 'invocation.json').read_bytes())
    assert invocation['environment']['ANTHROPIC_API_KEY'] == 'd4d-local-permission-probe-token'
    assert invocation['environment']['CLAUDE_CODE_DISABLE_1M_CONTEXT'] == '0'
    events, request = load_fixture()
    assert [(event['type'], event.get('subtype')) for event in events] == [
        ('system', 'ui_invalidate'), ('system', 'init'), ('assistant', None), ('result', 'success')]
    assert request['model'] == PAIR['returned'] and request['max_tokens'] == 64000
    assert request['thinking'] == {'type': 'adaptive'}
    assert request['output_config'] == {'effort': 'high'}
    assert provenance['source_is_successful_admission'] is False


def test_new_declaration_is_explicit_and_old_declarations_keep_exact_pair():
    for runtime in (selected(), selected(version=2, provisional=True)):
        assert aliases.model_aliases(runtime) == PAIR
    for version in (2, 3):
        assert aliases.model_aliases(selected(version=version)) == OLD_PAIR
    assert aliases.model_aliases(selected(version=1, provisional=True)) == OLD_PAIR
    for version, provisional in ((4, False), (2, True)):
        for change in ('missing_reported', 'wrong_reported', 'wrong_requested', 'extra'):
            runtime = selected(version=version, provisional=provisional)
            basis = json.loads(runtime['limits_basis'])
            if change == 'missing_reported':
                del basis['model_aliases']['reported']
            elif change == 'wrong_reported':
                basis['model_aliases']['reported'] = PAIR['requested']
            elif change == 'wrong_requested':
                runtime['model'] = basis['model_aliases']['requested'] = PAIR['returned']
            else:
                basis['model_aliases']['extra'] = 'not allowed'
            runtime['limits_basis'] = raw(basis).decode()
            with pytest.raises(ValueError):
                aliases.model_aliases(runtime)


def test_new_invocation_requires_exact_requested_alias_once():
    argv = json.loads((FIXTURE / 'invocation.json').read_bytes())['argv']
    aliases.require_invocation_model(argv, PAIR)
    index = argv.index('--model')
    variants = [argv[:index] + argv[index + 2:], argv + ['--model', PAIR['requested']],
                argv + ['--model=' + PAIR['requested']],
                argv[:index] + ['--model=' + PAIR['requested']] + argv[index + 2:]]
    wrong = list(argv)
    wrong[index + 1] = PAIR['reported']
    variants.append(wrong)
    for candidate in variants:
        with pytest.raises(ValueError):
            aliases.require_invocation_model(candidate, PAIR)


def test_real_shape_observation_and_saved_runtime_reader_accept_new_version_only(tmp_path):
    events, request = load_fixture()
    sequence._observed(transcript(events), raw(request), selected(version=2, provisional=True))
    path = tmp_path / 'transcript.jsonl'
    path.write_bytes(transcript(events))
    pin, observed = runtime_reader._saved_probe(str(path), PAIR)
    assert observed == {'model': PAIR['reported'],
        'limits': {'contextWindow': 1000000, 'maxOutputTokens': 64000}, 'init_version': '2.1.325'}
    assert pin['terminal_line'] == 4
    for change in ('200k', 'bool_context', 'old_init', 'old_usage', 'old_assistant',
                   'mixed_assistant', 'mixed_usage', 'ui_model', 'init_message',
                   'terminal_model', 'terminal_message'):
        changed = mutate(events, change)
        with pytest.raises(ValueError):
            sequence._observed(transcript(changed), raw(request), selected(version=2, provisional=True))
        path.write_bytes(transcript(changed))
        with pytest.raises(ValueError):
            runtime_reader._saved_probe(str(path), PAIR)
    path.write_bytes(transcript(events))
    with pytest.raises(ValueError):
        sequence._observed(transcript(events), raw(request), selected(version=1, provisional=True))
    with pytest.raises(ValueError):
        runtime_reader._saved_probe(str(path), OLD_PAIR)
    old, request = legacy_events()
    sequence._observed(transcript(old), raw(request), selected(version=1, provisional=True))
    path.write_bytes(transcript(old))
    assert runtime_reader._saved_probe(str(path), OLD_PAIR)[1]['model'] == PAIR['requested']


def test_frame_and_usage_consumers_require_exact_new_labels_and_integer_million():
    events, _ = load_fixture()
    for event in events:
        aliases.require_frame_models(event, PAIR)
    aliases.require_model_usage(events[-1], PAIR)
    for change in ('200k', 'bool_context', 'old_usage', 'mixed_usage'):
        with pytest.raises(ValueError):
            aliases.require_model_usage(mutate(events, change)[-1], PAIR)
    for change in ('old_init', 'old_assistant', 'mixed_assistant', 'ui_model',
                   'init_message', 'terminal_model', 'terminal_message'):
        with pytest.raises(ValueError):
            for event in mutate(events, change):
                aliases.require_frame_models(event, PAIR)
    old, _ = legacy_events()
    for event in old:
        aliases.require_frame_models(event, OLD_PAIR)
    aliases.require_model_usage(old[-1], OLD_PAIR)
    with pytest.raises(ValueError):
        aliases.require_frame_models(events[1], OLD_PAIR)
    with pytest.raises(ValueError):
        aliases.require_model_usage(events[-1], OLD_PAIR)
    for kind in ('system', 'control_request', 'control_response'):
        aliases.require_frame_models({'type': kind, 'model': PAIR['reported']}, PAIR)
        with pytest.raises(ValueError):
            aliases.require_frame_models({'type': kind, 'model': PAIR['requested']}, PAIR)
        changed = deepcopy(events)
        changed.insert(-1, {'type': kind, 'model': PAIR['requested']})
        with pytest.raises(ValueError):
            sequence._observed(transcript(changed), raw(load_fixture()[1]),
                               selected(version=2, provisional=True))


def prepared_case(root, *, old=False):
    """Mint date-relative software evidence around inert binary bytes only."""
    root.mkdir()
    root = root.resolve()
    updater = root / 'updater'
    updater.mkdir()
    inert = b'Inert CLI-label fixture bytes; never execute.\n'
    source, copied = updater / 'current', root / 'durable-copy'
    for path in (source, copied):
        path.write_bytes(inert)
        path.chmod(0o700)
    runtime = {'route': runtime_values.ROUTE,
        'executable': {'path': str(copied), 'sha256': hashlib.sha256(inert).hexdigest(),
                       'version': 'Offline fixture 2.1.325', 'init_version': '2.1.325'},
        'model': PAIR['requested'], 'auxiliary_models': [], 'effort': 'high',
        'limits': {'contextWindow': 1000000, 'maxOutputTokens': 64000},
        'limits_basis': selected(version=1 if old else 2, provisional=True)['limits_basis'],
        'provider': 'synthetic-first-party-selection',
        'auth': {'loggedIn': True, 'authMethod': 'claude.ai', 'apiProvider': 'firstParty',
                 'subscriptionType': 'max', 'expected_api_key_source': 'none'},
        'environment': {'PATH': '/usr/bin:/bin', 'HOME': str(root / 'runtime-home'),
            'BASH_DEFAULT_TIMEOUT_MS': '1000000', 'BASH_MAX_TIMEOUT_MS': '1000000',
            'PYSTOW_HOME': str(root / 'attempt/helper-cache'),
            'CLAUDE_SECURESTORAGE_CONFIG_DIR': '', 'CLAUDE_CODE_DISABLE_1M_CONTEXT': '0'},
        'deadline_seconds': 28800, 'budget_guard_usd': '90',
        'keep_awake': {'policy': 'macos_iokit_ims_v1', 'host_platform': 'darwin',
                       'basis': 'Offline fixture, never host admission'}}
    directory = root / 'probe-sequence'
    observation = directory / 'observation'
    observation.mkdir(parents=True)
    events, request = legacy_events() if old else load_fixture()
    transcript_path, request_path = observation / 'transcript.jsonl', observation / 'native_request.json'
    transcript_path.write_bytes(transcript(events))
    request_path.write_bytes(raw(request))
    now = datetime.now(timezone.utc) - timedelta(seconds=2)
    stamp = now.isoformat().replace('+00:00', 'Z')
    authorization = {'kind': sequence.AUTH_KIND, 'version': 1,
        'owner': 'Invented offline fixture owner', 'authorized_at': stamp,
        'word': 'AUTHORIZE_TWO_SCRIPTED_NATIVE_PROBES', 'directory': str(directory),
        'provisional_runtime_sha256': sequence.sha(raw(runtime)),
        'observation_deadline_seconds': 60, 'permission_deadline_seconds': 60,
        'provider': sequence.PROVIDER, 'permission_protocol': sequence.PERMISSION_PROTOCOL}
    authorized = raw(authorization)
    process = {'spawn_count': 1, 'returncode': 0,
        'cleanup': {'child_started': True, 'leader_reaped': True, 'group_absent': True}}
    provider_url = 'http://127.0.0.1:18455'
    document = sequence.observation_document(authorized, runtime,
        transcript_raw=transcript_path.read_bytes(), request_raw=request_path.read_bytes(),
        provider_url=provider_url, started_at=stamp, finished_at=stamp, process=process)
    for name, value in {'authorization.json': authorization, 'provisional-runtime.json': runtime,
            'observation-claim.json': sequence.observation_claim(authorized, runtime, stamp),
            'observation/invocation.json': sequence.observation_invocation(runtime, directory, provider_url),
            'observation/observation.json': document}.items():
        (directory / name).write_bytes(raw(value))
    arguments = {'probe_init_path': str(transcript_path), 'native_request_path': str(request_path),
        'updater_source': str(source), 'updater_root': str(updater),
        'thinking_setting': {'type': 'adaptive'}, 'thinking_basis': 'Explicit offline fixture setting',
        'observation_probe_path': str(observation / 'observation.json'),
        'admission_policy': admission_policy(root / 'one-capture')}
    return runtime, arguments


def test_prepared_runtime_roundtrip_declares_final_four_and_refuses_old_provisional(tmp_path):
    runtime, arguments = prepared_case(tmp_path / 'new')
    original = deepcopy(runtime)
    final = runtime_reader.prepare_runtime(runtime, **arguments)
    basis = json.loads(final['limits_basis'])
    assert runtime == original
    assert basis['version'] == 4 and basis['model_aliases'] == PAIR
    assert basis['observed']['model'] == PAIR['reported']
    assert basis['observed']['limits'] == {'contextWindow': 1000000, 'maxOutputTokens': 64000}
    assert runtime_reader.validate_prepared_runtime(final) == final
    old, old_arguments = prepared_case(tmp_path / 'old', old=True)
    old_final = runtime_reader.prepare_runtime(old, **old_arguments)
    assert json.loads(old_final['limits_basis'])['version'] == 3
    assert runtime_reader.validate_prepared_runtime(old_final) == old_final
    wrong_final = deepcopy(old)
    wrong_final['limits_basis'] = selected()['limits_basis']
    with pytest.raises(ValueError, match='provisional model-label declaration'):
        sequence.validate_observation(old_arguments['observation_probe_path'], final_runtime=wrong_final)
    with pytest.raises(ValueError):
        runtime_reader.prepare_runtime(wrong_final, **old_arguments)


def test_capture_limits_use_reported_key_and_keep_refusal_evidence():
    events, _ = load_fixture()
    runtime = selected()
    assert words.observed_limits(raw(events[-1]), runtime)[2] == runtime['limits']
    mismatch = mutate(events, '200k')[-1]
    assert words.observed_primary_limits(raw(mismatch), runtime)[2]['contextWindow'] == 200000
    for change in ('200k', 'bool_context', 'old_usage', 'mixed_usage',
                   'terminal_model', 'terminal_message'):
        with pytest.raises(ValueError):
            words.observed_limits(raw(mutate(events, change)[-1]), runtime)
    old, _ = legacy_events()
    assert words.observed_limits(raw(old[-1]), selected(version=3))[2] == runtime['limits']
    with pytest.raises(ValueError):
        words.observed_limits(raw(events[-1]), selected(version=3))


def test_real_terminal_and_accounting_gates_use_reported_label(tmp_path, pure_gate_members):
    prepared, runtime, projections = current_stream(tmp_path)
    runtime['limits_basis'] = selected()['limits_basis']
    prepared['events'][0]['model'] = PAIR['reported']
    terminal = prepared['events'][-1]
    terminal['modelUsage'] = {PAIR['reported']: terminal['modelUsage'][PAIR['requested']]}
    result = gate_result(prepared, runtime, projections, pure_gate_members)
    assert result['terminal']['passed'] is result['accounting']['passed'] is True
    for change in ('200k', 'bool_context', 'old_init', 'old_usage', 'mixed_assistant'):
        candidate = deepcopy(prepared)
        if change in ('200k', 'bool_context'):
            candidate['events'][-1]['modelUsage'][PAIR['reported']]['contextWindow'] = 200000 if change == '200k' else True
        elif change == 'old_init':
            candidate['events'][0]['model'] = PAIR['requested']
        elif change == 'old_usage':
            usage = candidate['events'][-1]['modelUsage']
            candidate['events'][-1]['modelUsage'] = {PAIR['requested']: usage[PAIR['reported']]}
        else:
            candidate['events'][1]['model'] = PAIR['requested']
        result = gate_result(candidate, runtime, projections, pure_gate_members)
        assert result['terminal']['passed'] is False, change
        if change in ('200k', 'bool_context', 'old_usage'):
            assert result['accounting']['passed'] is False, change


def test_shared_tool_trace_binds_init_and_nonassistant_reported_labels():
    from data_sheets_schema import native_shared_observations as observations
    native, parent, runtime = alias_trace_frames()
    runtime['limits_basis'] = selected()['limits_basis']
    for event in native:
        if event.get('type') != 'assistant' and event.get('model') == PAIR['requested']:
            event['model'] = PAIR['reported']
        if event.get('type') == 'result':
            event['modelUsage'] = {PAIR['reported']: {'contextWindow': 1000000, 'maxOutputTokens': 64000}}
    value = observations.Trace(prefix('transcript', native), prefix('control', parent),
        session_id=SESSION, policy=POLICY, runtime=runtime)
    assert value.settled('tool-1').call.tool_use_id == 'tool-1'
    for kind in ('system', 'assistant', 'user', 'result'):
        changed = deepcopy(native)
        event = next(event for event in changed if event.get('type') == kind and
                     (kind != 'system' or event.get('subtype') == 'init'))
        event['model'] = PAIR['requested']
        with pytest.raises(ValueError):
            observations.Trace(prefix('transcript', changed), prefix('control', parent),
                session_id=SESSION, policy=POLICY, runtime=runtime)


def test_genuine_saved_permission_consumer_rechecks_new_labels(fixture):
    expected = deepcopy(fixture['expected'])
    expected['runtime']['model'] = PAIR['requested']
    expected['runtime']['auxiliary_models'] = []
    expected['runtime']['limits_basis'] = selected()['limits_basis']
    expected['runtime']['limits'] = {'contextWindow': 1000000, 'maxOutputTokens': 64000}
    manifest = fabricated_manifest(expected, fixture['selection'],
        fixture['root'] / 'new-label-probes', fixture['source_raw'])
    names = [name for name in manifest['members'] if name.endswith('/transcript.jsonl')]
    for name in names:
        events = rows(manifest, name)
        for event in events:
            if event.get('type') == 'system' and event.get('subtype') == 'init':
                event['model'] = PAIR['reported']
            if event.get('type') == 'result' and 'modelUsage' in event:
                event['modelUsage'] = {PAIR['reported']: event['modelUsage'][PAIR['requested']]}
        put_rows(manifest, name, events)
        if name == 'traces/settled/transcript.jsonl':
            outcome = get(manifest, 'traces/settled/outcome.json')
            outcome['terminal_sha256'] = sequence.sha(raw(events[-1]))
            put(manifest, 'traces/settled/outcome.json', outcome)
    targets = {('native_shared_permissions', '_trace_body'): ()}
    with observe_consumer_calls(targets) as calls:
        result = verify(manifest, expected)
    assert targets.keys() <= {key for key, _ in calls}
    assert result['passed'] is True
    for change in ('200k', 'old_init', 'old_usage', 'mixed_assistant'):
        changed = deepcopy(manifest)
        name = 'traces/settled/transcript.jsonl'
        events = rows(changed, name)
        if change == 'old_init':
            events[1]['model'] = PAIR['requested']
        elif change == 'mixed_assistant':
            events[2]['model'] = PAIR['requested']
        elif change == 'old_usage':
            events[-1]['modelUsage'] = {PAIR['requested']: events[-1]['modelUsage'][PAIR['reported']]}
        else:
            events[-1]['modelUsage'][PAIR['reported']]['contextWindow'] = 200000
        put_rows(changed, name, events)
        outcome = get(changed, 'traces/settled/outcome.json')
        outcome['terminal_sha256'] = sequence.sha(raw(events[-1]))
        put(changed, 'traces/settled/outcome.json', outcome)
        with pytest.raises(ValueError):
            verify(changed, expected)

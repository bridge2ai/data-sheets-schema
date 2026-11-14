"""D117 offline software checks, 2026-11-08; never execute a native program.

Observation transport is replaced at its process/listener boundaries. Bound
phase tests run the genuine saved-permission consumer on fabricated traces;
they do not construct or approve a complete native execution registration.
"""
from contextlib import contextmanager
from copy import deepcopy
import io
import json
from pathlib import Path
import socket
import sys
import time
from types import SimpleNamespace

import pytest

from data_sheets_schema import native_u4b_probe_sequence as sequence
from data_sheets_schema import native_u4b_runtime as runtime_module
from data_sheets_schema import native_model_aliases as aliases
from data_sheets_schema import native_probe_provider as provider
from data_sheets_schema import native_permission_probe as producer
from tests.test_native_u4b_runtime import runtime_inputs
from tests.test_native_shared_permissions import fixture, fabricated_manifest, prohibit_real_transports
from tests.utils.native_u4b_observation import mint_observation
from tests.utils.native_shared_consumer_scope import observe_consumer_calls


@pytest.fixture(autouse=True)
def no_listener(monkeypatch):
    monkeypatch.setattr(socket.socket, 'bind', lambda *a, **k: pytest.fail('offline sequence opened a listener'))


@pytest.fixture
def prepared(tmp_path):
    runtime, arguments = runtime_inputs(tmp_path)
    final = runtime_module.prepare_runtime(runtime, **arguments)
    path = Path(arguments['observation_probe_path'])
    root = path.parent.parent
    return {'runtime': final, 'initial': runtime, 'arguments': arguments, 'path': path,
            'root': root, 'authorization': (root / 'authorization.json').read_bytes(),
            'provisional': sequence.strict_json((root / 'provisional-runtime.json').read_bytes())}


def test_real_observation_consumer_keeps_two_phase_dependency_acyclic(prepared):
    final = prepared['runtime']
    basis = json.loads(final['limits_basis'])
    observed = sequence.validate_observation(prepared['path'], expected_pin=basis['observation_probe'],
        final_runtime=final, transcript_path=basis['probe']['path'], request_path=basis['request']['path'])
    assert observed['authorization_sha256'] == sequence.sha(prepared['authorization'])
    assert observed['pin']['sha256'] == sequence.sha(prepared['path'].read_bytes())
    assert observed['transcript']['sha256'] == basis['probe']['sha256']
    assert observed['request']['sha256'] == basis['request']['sha256']
    assert basis['thinking']['observed']['value'] == {'type': 'adaptive'}
    assert not (prepared['root'] / 'sequence.json').exists()
    assert not (prepared['root'] / 'permission').exists()
    assert runtime_module.validate_prepared_runtime(final) == final


@pytest.mark.parametrize('field', ['model', 'effort', 'provider', 'auth', 'environment',
                                  'executable', 'deadline_seconds', 'budget_guard_usd', 'keep_awake'])
def test_final_runtime_cannot_change_other_provisional_fields(prepared, field):
    changed = deepcopy(prepared['runtime'])
    if field == 'model': changed[field] = 'other-model'
    elif field == 'effort': changed[field] = 'medium'
    elif field == 'provider': changed[field] = 'other-provider'
    elif field == 'auth': changed[field]['subscriptionType'] = 'other'
    elif field == 'environment': changed[field]['HOME'] += '/different'
    elif field == 'executable': changed[field]['version'] += '-other'
    elif field == 'deadline_seconds': changed[field] += 1
    elif field == 'budget_guard_usd': changed[field] = '90.0'
    else: changed[field]['basis'] += ' altered'
    with pytest.raises(ValueError, match='outside limits/basis/thinking'):
        sequence.validate_observation(prepared['path'], final_runtime=changed)


def test_only_limits_and_nested_basis_are_mutable_before_final_validation(prepared):
    changed = deepcopy(prepared['runtime'])
    changed['limits'] = {'contextWindow': 999999, 'maxOutputTokens': 50000}
    changed['limits_basis'] = 'A changed draft basis; not final admission'
    sequence.validate_observation(prepared['path'], final_runtime=changed)
    with pytest.raises(ValueError):
        runtime_module.validate_prepared_runtime(changed)


@pytest.mark.parametrize('role', ['manifest', 'transcript', 'request'])
def test_runtime_cannot_use_bound_probe_as_its_own_observation(prepared, role):
    runtime = deepcopy(prepared['runtime'])
    basis = json.loads(runtime['limits_basis'])
    bound = prepared['root'] / 'permission/permission-probe.json'
    bound.parent.mkdir()
    source = prepared['path'] if role == 'manifest' else Path(basis['probe' if role == 'transcript' else 'request']['path'])
    raw = source.read_bytes()
    bound.write_bytes(raw)
    key = {'manifest': 'observation_probe', 'transcript': 'probe', 'request': 'request'}[role]
    basis[key].update(path=str(bound), sha256=sequence.sha(raw), bytes=len(raw))
    runtime['limits_basis'] = runtime_module._canonical(basis)
    with pytest.raises(ValueError, match='observation|bound probe'):
        runtime_module.validate_prepared_runtime(runtime)


@pytest.mark.parametrize('member', ['authorization.json', 'provisional-runtime.json',
    'observation-claim.json', 'observation/invocation.json', 'observation/transcript.jsonl',
    'observation/native_request.json'])
def test_saved_observation_pin_mutation_refuses_without_remint(prepared, member):
    path = prepared['root'] / member
    path.write_bytes(path.read_bytes() + b'\n')
    with pytest.raises(ValueError, match='pinned bytes'):
        sequence.validate_observation(prepared['path'])


@pytest.mark.parametrize('mutation', ['owner_word', 'remote_provider', 'unknown_protocol',
    'wrong_runtime', 'bool_deadline', 'extra', 'timestamp'])
def test_authorization_is_closed_and_never_dispatches(prepared, monkeypatch, mutation):
    value = sequence.strict_json(prepared['authorization'])
    field, replacement = {
        'owner_word': ('word', 'AUTHORIZE_ONE_NATIVE_ATTEMPT'),
        'remote_provider': ('provider', 'firstParty'),
        'unknown_protocol': ('permission_protocol', 'arbitrary'),
        'wrong_runtime': ('provisional_runtime_sha256', '0' * 64),
        'bool_deadline': ('observation_deadline_seconds', True),
        'extra': ('other', 'not closed'), 'timestamp': ('authorized_at', '2026-11-08T00:00:00+00:00'),
    }[mutation]
    value[field] = replacement
    monkeypatch.setattr(provider, 'local_provider', lambda **k: pytest.fail('invalid authorization opened transport'))
    with pytest.raises(ValueError):
        sequence.produce_observation(sequence.canonical(value), prepared['provisional'])


@pytest.mark.parametrize('location', ['source', 'source_child', 'source_parent', 'binary', 'binary_parent'])
def test_observation_cannot_write_source_or_executable_envelope(prepared, monkeypatch, location):
    selected = sequence.strict_json(prepared['authorization'])
    binary = Path(prepared['provisional']['executable']['path'])
    selected['directory'] = str({'source': sequence.ROOT, 'source_child': sequence.ROOT / 'new-probe',
        'source_parent': sequence.ROOT.parent, 'binary': binary, 'binary_parent': binary.parent}[location])
    monkeypatch.setattr(producer, '_identity', lambda *a: pytest.fail('overlap reached binary identity'))
    monkeypatch.setattr(provider, 'local_provider', lambda **k: pytest.fail('overlap reached transport'))
    with pytest.raises(ValueError, match='overlaps'):
        sequence.produce_observation(sequence.canonical(selected), prepared['provisional'])


def _existing_case_alias(path):
    """Find a real case alias by identity; never create or rename a source."""
    for index in range(len(path.parts) - 1, 0, -1):
        parts = list(path.parts)
        parts[index] = parts[index].swapcase()
        alias = Path(*parts)
        if alias == path:
            continue
        try:
            if alias.samefile(path):
                return alias
        except FileNotFoundError:
            continue
    pytest.skip('filesystem has no case alias for this protected path')


@pytest.mark.skipif(sys.platform != 'darwin', reason='real macOS case-alias regression')
@pytest.mark.parametrize('location', ['source_child', 'source_parent', 'binary_parent'])
def test_real_case_alias_overlap_refuses_before_effects(prepared, monkeypatch, location, tmp_path):
    selected = sequence.strict_json(prepared['authorization'])
    binary = Path(prepared['provisional']['executable']['path'])
    if location == 'source_child':
        target = _existing_case_alias(sequence.ROOT) / ('not-created-' + tmp_path.name)
        assert not target.exists()
    else:
        target = _existing_case_alias(sequence.ROOT.parent if location == 'source_parent' else binary.parent)
    selected['directory'] = str(target)
    monkeypatch.setattr(producer, '_identity', lambda *a: pytest.fail('case overlap reached binary identity'))
    monkeypatch.setattr(provider, 'local_provider', lambda **k: pytest.fail('case overlap reached transport'))
    monkeypatch.setattr(sequence, '_new', lambda *a: pytest.fail('case overlap wrote an artifact'))
    monkeypatch.setattr(Path, 'mkdir', lambda *a, **k: pytest.fail('case overlap created a directory'))
    with pytest.raises(ValueError, match='overlaps'):
        sequence.produce_observation(sequence.canonical(selected), prepared['provisional'])
    if location == 'source_child':
        assert not target.exists()


def test_ordinary_prospective_sibling_is_disjoint_and_not_created(prepared):
    selected = sequence.strict_json(prepared['authorization'])
    target = prepared['root'].parent / 'ordinary-sibling'
    selected['directory'] = str(target)
    assert sequence.authorization(sequence.canonical(selected), prepared['provisional']) == selected
    assert not target.exists()


def test_source_symlink_alias_still_refuses_before_effects(prepared, monkeypatch, tmp_path):
    link = tmp_path / 'source-alias'
    link.symlink_to(sequence.ROOT, target_is_directory=True)
    selected = sequence.strict_json(prepared['authorization'])
    selected['directory'] = str(link / 'not-created')
    monkeypatch.setattr(producer, '_identity', lambda *a: pytest.fail('symlink overlap reached binary identity'))
    monkeypatch.setattr(provider, 'local_provider', lambda **k: pytest.fail('symlink overlap reached transport'))
    monkeypatch.setattr(Path, 'mkdir', lambda *a, **k: pytest.fail('symlink overlap created a directory'))
    with pytest.raises(ValueError, match='canonical and unaliased'):
        sequence.produce_observation(sequence.canonical(selected), prepared['provisional'])


def test_observation_manifest_rejects_wrong_init_version_before_publication(prepared):
    transcript = Path(prepared['arguments']['probe_init_path']).read_bytes()
    events = [json.loads(line) for line in transcript.splitlines()]
    events[0]['claude_code_version'] = 'another-binary-version'
    changed = b''.join(sequence.canonical(event) + b'\n' for event in events)
    document = json.loads(prepared['path'].read_bytes())
    with pytest.raises(ValueError, match='initialization version'):
        sequence.observation_document(prepared['authorization'], prepared['provisional'],
            transcript_raw=changed, request_raw=Path(prepared['arguments']['native_request_path']).read_bytes(),
            provider_url=document['provider_url'], started_at=document['started_at'],
            finished_at=document['finished_at'], process=document['process'])


@pytest.mark.parametrize('source', ['missing', 'none', 'ANTHROPIC_AUTH_TOKEN', '', None, True, 0, [], {}])
def test_observation_refuses_missing_or_other_auth_source_before_publication(prepared, source):
    saved = prepared['path'].read_bytes()
    transcript = Path(prepared['arguments']['probe_init_path']).read_bytes()
    events = [json.loads(line) for line in transcript.splitlines()]
    if source == 'missing':
        events[0].pop('apiKeySource')
    else:
        events[0]['apiKeySource'] = source
    changed = b''.join(sequence.canonical(event) + b'\n' for event in events)
    document = json.loads(saved)
    with pytest.raises(ValueError, match='scripted-provider API-key source'):
        sequence.observation_document(prepared['authorization'], prepared['provisional'],
            transcript_raw=changed, request_raw=Path(prepared['arguments']['native_request_path']).read_bytes(),
            provider_url=document['provider_url'], started_at=document['started_at'],
            finished_at=document['finished_at'], process=document['process'])
    assert prepared['path'].read_bytes() == saved


def test_observation_readback_refuses_rehashed_subscription_auth_claim(prepared):
    transcript_path = Path(prepared['arguments']['probe_init_path'])
    lines = transcript_path.read_bytes().splitlines(keepends=True)
    original_terminal = lines[-1]
    initial = json.loads(lines[0])
    initial['apiKeySource'] = 'none'
    lines[0] = sequence.canonical(initial) + b'\n'
    changed = b''.join(lines)
    transcript_path.write_bytes(changed)
    document = json.loads(prepared['path'].read_bytes())
    assert lines[-1] == original_terminal
    assert document['terminal']['sha256'] == sequence.sha(original_terminal.removesuffix(b'\n'))
    document['transcript'].update(bytes=len(changed), sha256=sequence.sha(changed))
    prepared['path'].write_bytes(sequence.canonical(document))
    with pytest.raises(ValueError, match='scripted-provider API-key source'):
        sequence.validate_observation(prepared['path'])


def test_observation_and_subscription_auth_sources_remain_distinct(prepared):
    events = [json.loads(line) for line in Path(prepared['arguments']['probe_init_path']).read_bytes().splitlines()]
    assert events[0]['apiKeySource'] == 'ANTHROPIC_API_KEY'
    assert prepared['runtime']['auth']['expected_api_key_source'] == 'none'
    assert sequence.validate_observation(prepared['path'])


def producer_case(prepared):
    authorized = sequence.strict_json(prepared['authorization'])
    root = prepared['root'].parent / 'produced-probe-sequence'
    authorized['directory'] = str(root)
    return sequence.canonical(authorized), root


def scripted_boundaries(monkeypatch, prepared, *, requests=1, failure=None):
    holder, observed = {}, []
    @contextmanager
    def memory_provider(**kwargs):
        assert kwargs['cases']() == [] and kwargs['model'] == aliases.RETURNED
        holder['observer'] = kwargs['observation_request']
        holder['server'] = SimpleNamespace(failure=None)
        observed.append('provider')
        yield holder['server'], 'http://127.0.0.1:18455'
        observed.append('closed')
    def child(invocation, deadline, server, outputs, state):
        root = Path(invocation['cwd']).parent.parent
        assert (root / 'observation-claim.json').is_file()
        assert invocation['argv'][invocation['argv'].index('--model') + 1] == aliases.REQUESTED
        assert invocation['environment']['ANTHROPIC_BASE_URL'] == 'http://127.0.0.1:18455'
        assert invocation['environment']['ANTHROPIC_API_KEY'] == 'd4d-local-permission-probe-token'
        assert invocation['argv'][-1] == sequence.PROMPT
        assert invocation['argv'][invocation['argv'].index('--tools') + 1] == ''
        observed.append('child')
        state.update(spawn_count=1, returncode=0,
            cleanup={'child_started': True, 'leader_reaped': True, 'group_absent': True})
        outputs['stdout'].extend(Path(prepared['arguments']['probe_init_path']).read_bytes())
        for _ in range(requests):
            holder['observer'](Path(prepared['arguments']['native_request_path']).read_bytes(), endpoint='/v1/messages')
        if failure is not None:
            raise failure
    monkeypatch.setattr(provider, 'local_provider', memory_provider)
    monkeypatch.setattr(sequence, '_run_observation', child)
    return observed


def test_observation_producer_persists_exact_bytes_and_consumes_phase_once(prepared, monkeypatch):
    authorization, root = producer_case(prepared)
    observed = scripted_boundaries(monkeypatch, prepared)
    output = sequence.produce_observation(authorization, prepared['provisional'])
    result = sequence.validate_observation(output, final_runtime=prepared['runtime'])
    assert result['request']['sha256'] == sequence.sha((root / 'observation/requests/000001.json').read_bytes())
    assert (root / 'observation/requests/000001.endpoint').read_text() == '/v1/messages'
    assert (root / 'observation/stdout.jsonl').read_bytes() == Path(result['transcript']['path']).read_bytes()
    assert (root / 'observation/stderr.txt').exists()
    with pytest.raises(FileExistsError):
        sequence.produce_observation(authorization, prepared['provisional'])
    assert observed == ['provider', 'child', 'closed']


def test_multiple_request_bodies_are_retained_and_never_select_first(prepared, monkeypatch):
    authorization, root = producer_case(prepared)
    scripted_boundaries(monkeypatch, prepared, requests=2)
    with pytest.raises(ValueError, match='multiple model requests'):
        sequence.produce_observation(authorization, prepared['provisional'])
    assert (root / 'observation/requests/000001.json').is_file()
    assert (root / 'observation/requests/000002.json').is_file()
    assert (root / 'observation/failure.json').is_file()
    assert not (root / 'observation/observation.json').exists()
    assert not (root / 'observation/native_request.json').exists()


@pytest.mark.parametrize('error', [TimeoutError('invented deadline'), PermissionError('invented cleanup refusal')])
def test_observation_failure_retains_spent_claim_and_raw_outputs(prepared, monkeypatch, error):
    authorization, root = producer_case(prepared)
    scripted_boundaries(monkeypatch, prepared, failure=error)
    with pytest.raises(type(error)):
        sequence.produce_observation(authorization, prepared['provisional'])
    assert (root / 'observation-claim.json').is_file()
    assert (root / 'observation/stdout.jsonl').stat().st_size > 0
    assert not (root / 'observation/observation.json').exists()
    with pytest.raises(FileExistsError):
        sequence.produce_observation(authorization, prepared['provisional'])


def test_real_http_handler_captures_raw_body_and_no_tool_response_in_memory(tmp_path):
    directory = tmp_path / 'requests'; directory.mkdir()
    raw = b'{"model":"claude-opus-5","messages":[],"thinking":false}'
    observer = sequence._Requests(directory)
    server = SimpleNamespace(deadline=time.monotonic() + 60, requests=0, observation_request=observer,
        case_supplier=lambda: [], model=aliases.RETURNED, reply=None, failure=None)
    handler = object.__new__(provider._Handler)
    handler.path, handler.server = '/v1/messages', server
    handler.headers = {'Content-Length': str(len(raw))}
    handler.connection = SimpleNamespace(settimeout=lambda timeout: None)
    handler.rfile, handler.wfile = io.BytesIO(raw), io.BytesIO()
    handler.send_response = lambda code: None
    handler.send_header = lambda *args: None
    handler.end_headers = lambda: None
    handler.send_error = lambda *args: pytest.fail('valid in-memory request refused')
    handler.do_POST()
    assert server.failure is None and observer.messages == [raw]
    assert (directory / '000001.json').read_bytes() == raw
    payload = json.loads(handler.wfile.getvalue())
    assert payload['model'] == aliases.RETURNED and payload['stop_reason'] == 'end_turn'
    assert payload['content'] == [{'type': 'text', 'text': 'OFFLINE_COMPLETE'}]


def bound_case(prepared, fixture):
    expected = deepcopy(fixture['expected'])
    expected['runtime'] = deepcopy(prepared['runtime'])
    expected['permission_environment'].update(prepared['runtime']['environment'])
    expected['permission_environment']['CLAUDE_CONFIG_DIR'] = str(
        Path(prepared['runtime']['environment']['PYSTOW_HOME']).parent / 'cli_config')
    return expected


def test_bound_phase_runs_genuine_saved_verifier_after_mocked_child_boundary(prepared, fixture, monkeypatch):
    expected = bound_case(prepared, fixture)
    calls = []
    reads = []
    actual_read = sequence._read
    def bounded_read(path, limit):
        if Path(path).name == 'permission-probe.json':
            reads.append(limit)
            assert limit == sequence.HARD_LIMITS['permission_wire_bytes']
        return actual_read(path, limit)
    monkeypatch.setattr(sequence, '_read', bounded_read)
    def saved_transport(submitted, directory, *, deadline_seconds):
        assert submitted == expected
        assert (prepared['root'] / 'bound-claim.json').is_file()
        calls.append(str(directory))
        document = fabricated_manifest(submitted, fixture['selection'], directory, fixture['source_raw'])
        directory.mkdir()
        output = directory / 'permission-probe.json'
        output.write_bytes(sequence.canonical(document))
        return output
    monkeypatch.setattr(producer, 'produce_saved_probe', saved_transport)
    targets = {('native_shared_permissions', '_trace_body'): ()}
    with observe_consumer_calls(targets) as observed:
        output = sequence.produce_bound_probe(prepared['authorization'], expected)
        result = sequence.validate_bound_probe(prepared['runtime'], output)
    assert targets.keys() <= {key for key, _ in observed}
    assert result['checked'] is result['passed'] is True
    assert len(calls) == 1
    assert len(reads) >= 3 and set(reads) == {196_000_000}
    assert result['permission']['sha256'] == sequence.sha(output.read_bytes())
    with pytest.raises(FileExistsError):
        sequence.produce_bound_probe(prepared['authorization'], expected)
    assert len(calls) == 1
    # Repinning a corrupted complete manifest cannot replace actual verification.
    document = sequence.strict_json(output.read_bytes())
    del document['members']['traces/settled/transcript.jsonl']
    output.write_bytes(sequence.canonical(document))
    completion_path = prepared['root'] / 'sequence.json'
    completion = sequence.strict_json(completion_path.read_bytes())
    completion['permission'] = sequence._pin(output, output.read_bytes())
    completion_path.write_bytes(sequence.canonical(completion))
    with pytest.raises(ValueError):
        sequence.validate_bound_probe(prepared['runtime'], output)


def test_bound_phase_refuses_other_authorization_before_claim_or_transport(prepared, fixture, monkeypatch):
    expected = bound_case(prepared, fixture)
    authorized = sequence.strict_json(prepared['authorization'])
    authorized['owner'] += ' another'
    monkeypatch.setattr(producer, 'produce_saved_probe', lambda *a, **k: pytest.fail('other authorization dispatched'))
    with pytest.raises(ValueError, match='exact observation authorization'):
        sequence.produce_bound_probe(sequence.canonical(authorized), expected)
    assert not (prepared['root'] / 'bound-claim.json').exists()


def test_bound_phase_failure_is_spent_and_cannot_publish_completion(prepared, fixture, monkeypatch):
    expected = bound_case(prepared, fixture)
    calls = []
    def refused(*args, **kwargs):
        calls.append(True)
        raise ValueError('invented failed permission transcript')
    monkeypatch.setattr(producer, 'produce_saved_probe', refused)
    with pytest.raises(ValueError, match='invented failed permission'):
        sequence.produce_bound_probe(prepared['authorization'], expected)
    assert (prepared['root'] / 'bound-claim.json').exists()
    assert not (prepared['root'] / 'sequence.json').exists()
    failure_path = prepared['root'] / 'bound-failure.json'
    failure_raw = failure_path.read_bytes()
    assert sequence.strict_json(failure_raw) == {
        'error_type': 'ValueError', 'message': 'invented failed permission transcript',
        'authorization_sha256': sequence.sha(prepared['authorization']),
        'permission_directory_exists': False}
    with pytest.raises(FileExistsError):
        sequence.produce_bound_probe(prepared['authorization'], expected)
    assert failure_path.read_bytes() == failure_raw
    assert calls == [True]

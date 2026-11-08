"""D117 two-phase scripted probe evidence, 2026-11-08 (#4354).

Only the explicit produce_* functions launch a selected binary. Observation
is one no-tools child; the bound permission phase retains its seven-trace
protocol plus version check. Both use only the scripted loopback provider.
Saved records prove byte consistency, not human signatures, authenticated
account state or an independently observed operating-system history.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import os
from pathlib import Path
import selectors
import subprocess
import time
from urllib.parse import urlsplit

from . import native_model_aliases as aliases
from . import native_shared_runtime_values as values
from .native_subscription_guard import canonical, sha, strict_json
from .native_subscription_guard_v2 import _timestamp
from .native_subscription_capture import _read, _new, _sync, _cleanup, _signals, ISOLATION_FLAGS

AUTH_KIND = 'd4d_native_u4b_probe_authorization_v1'
OBSERVATION_KIND = 'd4d_native_u4b_observation_v1'
COMPLETION_KIND = 'd4d_native_u4b_probe_sequence_v1'
PROVIDER = 'scripted_loopback_only'
PERMISSION_PROTOCOL = 'shared_seven_trace_v1_plus_version_check'
MAX_BYTES = 4_000_000
ROOT = Path(__file__).resolve().parents[2]
PROMPT = 'Reply with OK.'
BASIS = 'Retained local scripted observations; not authenticated human/account authority or native acceptance.'
AUTH_KEYS = {'kind', 'version', 'owner', 'authorized_at', 'word', 'directory',
             'provisional_runtime_sha256', 'observation_deadline_seconds',
             'permission_deadline_seconds', 'provider', 'permission_protocol'}
OBSERVATION_KEYS = {'kind', 'version', 'directory', 'authorization', 'provisional_runtime',
                    'claim', 'invocation', 'transcript', 'request', 'terminal',
                    'provider_url', 'started_at', 'finished_at', 'process', 'basis'}


def _closed(value, keys, label):
    if type(value) is not dict or set(value) != set(keys):
        raise ValueError(label + ' has missing or unknown fields')


def _path(value):
    if type(value) is not str or not value or '\0' in value:
        raise ValueError('probe sequence path must be explicit absolute text')
    path = Path(value)
    if not path.is_absolute() or '..' in path.parts or str(path) != value or path.resolve() != path:
        raise ValueError('probe sequence path must be canonical and unaliased')
    return path


def _pin(path, raw):
    return {'path': str(path), 'sha256': sha(raw), 'bytes': len(raw)}


def _read_pin(pin, path, *, limit=MAX_BYTES):
    _closed(pin, {'path', 'sha256', 'bytes'}, 'probe artifact pin')
    if (pin['path'] != str(path) or type(pin['bytes']) is not int
            or not 0 < pin['bytes'] <= limit):
        raise ValueError('probe artifact path/size differs from its fixed role')
    raw = _read(path, limit)
    if _pin(path, raw) != pin:
        raise ValueError('probe artifact differs from its pinned bytes')
    return raw


def _utc():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def validate_provisional_runtime(value):
    """The closed pre-observation declaration is never a final admission basis."""
    runtime = values.validate_runtime(value)
    if (runtime['model'] != aliases.REQUESTED or runtime['auxiliary_models'] != []
            or runtime['effort'] != 'high' or runtime['auth']['subscriptionType'] != 'max'
            or runtime['environment']['CLAUDE_CODE_DISABLE_1M_CONTEXT'] != '0'
            or runtime['budget_guard_usd'] != '90'):
        raise ValueError('provisional probe must retain the selected U4b runtime profile')
    basis = strict_json(runtime['limits_basis'])
    _closed(basis, {'kind', 'version', 'model_aliases'}, 'provisional runtime basis')
    if (basis['kind'] != aliases.PROVISIONAL_KIND or type(basis['version']) is not int
            or basis['version'] != 1):
        raise ValueError('observation requires the explicit provisional runtime basis')
    aliases.model_aliases(runtime)
    return runtime


def authorization(raw, provisional):
    if type(raw) is not bytes or not 0 < len(raw) <= 16384:
        raise ValueError('probe authorization requires bounded saved bytes')
    value = strict_json(raw)
    _closed(value, AUTH_KEYS, 'two-probe authorization')
    if (value['kind'] != AUTH_KIND or type(value['version']) is not int or value['version'] != 1
            or value['word'] != 'AUTHORIZE_TWO_SCRIPTED_NATIVE_PROBES'
            or value['provider'] != PROVIDER or value['permission_protocol'] != PERMISSION_PROTOCOL
            or canonical(value) != raw):
        raise ValueError('not the closed scripted two-phase probe authorization')
    values._text(value['owner'], 'probe owner', 256)
    _timestamp(value['authorized_at'], 'probe authorized_at')
    runtime = validate_provisional_runtime(provisional)
    directory = _path(value['directory'])
    for protected in (ROOT, _path(runtime['executable']['path'])):
        if directory == protected or directory in protected.parents or protected in directory.parents:
            raise ValueError('probe sequence directory overlaps source or the selected executable')
    if value['provisional_runtime_sha256'] != sha(canonical(runtime)):
        raise ValueError('probe authorization names another provisional runtime')
    for field in ('observation_deadline_seconds', 'permission_deadline_seconds'):
        if type(value[field]) is not int or not 0 < value[field] <= min(600, runtime['deadline_seconds']):
            raise ValueError('probe authorization deadline is outside the selected bound')
    return value


def observation_claim(authorization_raw, provisional_runtime, started_at):
    authorized = authorization(authorization_raw, provisional_runtime)
    if _timestamp(started_at, 'observation start') < _timestamp(authorized['authorized_at'], 'probe authorized_at'):
        raise ValueError('observation claim predates authorization')
    return {'kind': 'd4d_native_u4b_observation_claim_v1', 'version': 1,
            'authorization_sha256': sha(authorization_raw),
            'provisional_runtime_sha256': authorized['provisional_runtime_sha256'],
            'started_at': started_at, 'process_limit': 1, 'provider': PROVIDER}


def observation_invocation(runtime, directory, provider_url):
    root = _path(str(directory)) / 'observation'
    parsed = urlsplit(provider_url)
    if (parsed.scheme != 'http' or parsed.hostname != '127.0.0.1' or not parsed.port
            or parsed.path or parsed.query or parsed.fragment or parsed.username or parsed.password
            or provider_url != 'http://127.0.0.1:' + str(parsed.port)):
        raise ValueError('observation provider must be the explicit loopback endpoint')
    runtime = validate_provisional_runtime(runtime)
    environment = {**runtime['environment'], **values.POLICY_ENV,
        'CLAUDE_CONFIG_DIR': str(root / 'config'), 'ANTHROPIC_BASE_URL': provider_url,
        'ANTHROPIC_API_KEY': 'd4d-local-permission-probe-token', 'DISABLE_AUTOUPDATER': '1'}
    return {'argv': [runtime['executable']['path'], *ISOLATION_FLAGS,
        '--model', runtime['model'], '--effort', runtime['effort'],
        '--max-budget-usd', runtime['budget_guard_usd'], PROMPT],
        'environment': environment, 'cwd': str(root / 'cwd'), 'stdin': 'DEVNULL',
        'process_limit': 1, 'prompt_sha256': sha(PROMPT.encode())}


def _observed(transcript_raw, request_raw, runtime):
    if (type(transcript_raw) is not bytes or not 0 < len(transcript_raw) <= MAX_BYTES
            or not transcript_raw.endswith(b'\n') or type(request_raw) is not bytes
            or not 0 < len(request_raw) <= MAX_BYTES):
        raise ValueError('observation requires complete bounded transcript and request bytes')
    lines = transcript_raw.splitlines()
    if len(lines) > 10000 or any(not row.strip() for row in lines):
        raise ValueError('observation transcript row bound or blank row refused')
    events = [strict_json(row) for row in lines]
    if any(type(row) is not dict for row in events):
        raise ValueError('observation transcript contains a non-object')
    init = [(index, row) for index, row in enumerate(events)
            if row.get('type') == 'system' and row.get('subtype') == 'init']
    terminals = [(index, row) for index, row in enumerate(events) if row.get('type') == 'result']
    if len(init) != 1 or len(terminals) != 1:
        raise ValueError('observation requires one init and one terminal result')
    begin, initial = init[0]
    end, terminal = terminals[0]
    if (begin >= end or end != len(events) - 1 or initial.get('model') != aliases.REQUESTED
            or terminal.get('is_error') is not False or terminal.get('subtype') != 'success'):
        raise ValueError('observation does not have an ordered successful terminal')
    if initial.get('claude_code_version') != runtime['executable']['init_version']:
        raise ValueError('observation initialization version differs from the selected executable')
    session = initial.get('session_id')
    values._text(session, 'observation session')
    pair = {'requested': aliases.REQUESTED, 'returned': aliases.RETURNED}
    for index, event in enumerate(events):
        if event.get('type') in ('assistant', 'user', 'result'):
            if index <= begin or event.get('session_id') != session or event.get('parent_tool_use_id') is not None:
                raise ValueError('observation frame is outside its initialized parent session')
            aliases.require_frame_models(event, pair)
    aliases.require_model_usage(terminal, pair)
    own = terminal['modelUsage'][aliases.REQUESTED]
    limits = {key: own.get(key) for key in ('contextWindow', 'maxOutputTokens')}
    if (any(type(value) is not int or value <= 0 for value in limits.values())
            or limits['maxOutputTokens'] > limits['contextWindow']):
        raise ValueError('observation terminal has no usable limits')
    body = strict_json(request_raw)
    if (type(body) is not dict or body.get('model') != aliases.RETURNED or 'thinking' not in body
            or body['thinking'] is None or type(body['thinking']) not in (dict, str, bool)
            or body['thinking'] == {} or (type(body['thinking']) is str and not body['thinking'].strip())
            or len(canonical(body['thinking'])) > 1024
            or any(key in body for key in ('thinkingEnabled', 'thinking_enabled', 'alwaysThinkingEnabled'))):
        raise ValueError('observation request lacks the exact model and explicit thinking')
    return {'line': end + 1, 'sha256': sha(lines[end])}


def observation_document(authorization_raw, provisional_runtime, *, transcript_raw, request_raw,
                         provider_url, started_at, finished_at, process):
    """Serialize supplied observations; this pure builder authenticates nothing."""
    authorized = authorization(authorization_raw, provisional_runtime)
    directory = _path(authorized['directory'])
    claim = observation_claim(authorization_raw, provisional_runtime, started_at)
    start, finish = (_timestamp(value, label) for value, label in
                     ((started_at, 'observation start'), (finished_at, 'observation finish')))
    if not 0 <= finish - start <= authorized['observation_deadline_seconds'] + 5:
        raise ValueError('observation duration differs from its bounded claim')
    expected_process = {'spawn_count': 1, 'returncode': 0,
        'cleanup': {'child_started': True, 'leader_reaped': True, 'group_absent': True}}
    if canonical(process) != canonical(expected_process):
        raise ValueError('observation process/cleanup did not explicitly succeed')
    invocation = observation_invocation(provisional_runtime, directory, provider_url)
    return {'kind': OBSERVATION_KIND, 'version': 1, 'directory': str(directory),
        'authorization': _pin(directory / 'authorization.json', authorization_raw),
        'provisional_runtime': _pin(directory / 'provisional-runtime.json', canonical(provisional_runtime)),
        'claim': _pin(directory / 'observation-claim.json', canonical(claim)),
        'invocation': _pin(directory / 'observation/invocation.json', canonical(invocation)),
        'transcript': _pin(directory / 'observation/transcript.jsonl', transcript_raw),
        'request': _pin(directory / 'observation/native_request.json', request_raw),
        'terminal': _observed(transcript_raw, request_raw, provisional_runtime), 'provider_url': provider_url,
        'started_at': started_at, 'finished_at': finished_at, 'process': deepcopy(process), 'basis': BASIS}


def validate_observation(path, *, expected_pin=None, final_runtime=None,
                         transcript_path=None, request_path=None):
    path = _path(str(path))
    raw = _read(path, MAX_BYTES)
    pin = _pin(path, raw)
    if expected_pin is not None and canonical(expected_pin) != canonical(pin):
        raise ValueError('observation manifest differs from its selected pin')
    manifest = strict_json(raw)
    _closed(manifest, OBSERVATION_KEYS, 'observation manifest')
    directory = _path(manifest['directory'])
    if path != directory / 'observation/observation.json':
        raise ValueError('observation cannot name the bound probe or another manifest path')
    authorization_raw = _read_pin(manifest['authorization'], directory / 'authorization.json', limit=16384)
    provisional_raw = _read_pin(manifest['provisional_runtime'], directory / 'provisional-runtime.json', limit=65536)
    provisional = strict_json(provisional_raw)
    claim = _read_pin(manifest['claim'], directory / 'observation-claim.json', limit=16384)
    invocation = _read_pin(manifest['invocation'], directory / 'observation/invocation.json', limit=65536)
    transcript = _read_pin(manifest['transcript'], directory / 'observation/transcript.jsonl')
    request = _read_pin(manifest['request'], directory / 'observation/native_request.json')
    if transcript_path is not None and str(transcript_path) != manifest['transcript']['path']:
        raise ValueError('runtime transcript is not its observation probe transcript')
    if request_path is not None and str(request_path) != manifest['request']['path']:
        raise ValueError('runtime request is not its observation probe request')
    derived = observation_document(authorization_raw, provisional, transcript_raw=transcript,
        request_raw=request, provider_url=manifest['provider_url'], started_at=manifest['started_at'],
        finished_at=manifest['finished_at'], process=manifest['process'])
    if (canonical(derived) != raw or canonical(provisional) != provisional_raw
            or sha(claim) != derived['claim']['sha256'] or sha(invocation) != derived['invocation']['sha256']):
        raise ValueError('observation manifest differs from freshly derived saved evidence')
    if final_runtime is not None:
        final = values.validate_runtime(final_runtime)
        omit = {'limits', 'limits_basis'}  # The thinking field is nested in limits_basis.
        if canonical({key: value for key, value in final.items() if key not in omit}) != canonical(
                {key: value for key, value in provisional.items() if key not in omit}):
            raise ValueError('final runtime differs from provisional outside limits/basis/thinking')
    return {'pin': pin, 'provisional_runtime': provisional, 'transcript': derived['transcript'],
            'request': derived['request'], 'authorization_sha256': sha(authorization_raw),
            'sequence_directory': str(directory), 'terminal': derived['terminal']}


class _Requests:
    """Persist every bounded request before deciding whether it is authoritative."""
    def __init__(self, directory):
        self.directory, self.total, self.messages, self.count = directory, 0, [], 0

    def __call__(self, raw, *, endpoint):
        if type(raw) is not bytes or self.count >= 8 or self.total + len(raw) > 16_000_000:
            raise ValueError('observation request inventory exceeds its bound')
        self.count += 1
        self.total += len(raw)
        _new(self.directory / ('%06d.json' % self.count), raw)
        _new(self.directory / ('%06d.endpoint' % self.count), endpoint.encode())
        body = strict_json(raw)
        if type(body) is not dict or body.get('model') != aliases.RETURNED:
            raise ValueError('observation request names another model')
        if endpoint == '/v1/messages':
            self.messages.append(raw)
            if len(self.messages) != 1:
                raise ValueError('observation has multiple model requests; no single thinking source')
        elif endpoint != '/v1/messages/count_tokens':
            raise ValueError('observation request endpoint is not scripted')


def _run_observation(invocation, deadline, server, outputs, process_state):
    process = None
    try:
        with selectors.DefaultSelector() as selector:
            process = subprocess.Popen(invocation['argv'], cwd=invocation['cwd'], env=invocation['environment'],
                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
            process_state['spawn_count'] = 1
            for name in outputs:
                stream = getattr(process, name)
                os.set_blocking(stream.fileno(), False)
                selector.register(stream, selectors.EVENT_READ, name)
            while selector.get_map() or process.poll() is None:
                if time.monotonic() >= deadline:
                    raise TimeoutError('observation probe deadline elapsed')
                if server.failure is not None:
                    raise ValueError('observation scripted provider failed') from server.failure
                for key, _ in selector.select(timeout=0.02):
                    remaining = MAX_BYTES - len(outputs[key.data])
                    raw = os.read(key.fd, min(65536, remaining + 1))
                    if not raw:
                        selector.unregister(key.fileobj)
                    else:
                        outputs[key.data].extend(raw[:remaining])
                        if len(raw) > remaining:
                            raise ValueError('observation stream exceeds its bound')
            process_state['returncode'] = process.returncode
            if process.returncode != 0:
                raise ValueError('observation process failed')
    finally:
        try:
            process_state['cleanup'] = _cleanup(process)
        finally:
            if process is not None:
                process_state['returncode'] = process.poll()
                for stream in (process.stdout, process.stderr):
                    if stream is not None:
                        stream.close()


def produce_observation(authorization_raw, provisional_runtime, directory=None):
    """Explicit one-child observation; no retries or inherited provider route."""
    from .native_probe_provider import local_provider
    from .native_permission_probe import _identity
    runtime = validate_provisional_runtime(provisional_runtime)
    authorized = authorization(authorization_raw, runtime)
    root = _path(authorized['directory'])
    if directory is not None and _path(str(directory)) != root:
        raise ValueError('observation directory differs from authorization')
    if not root.parent.is_dir():
        raise ValueError('probe sequence requires an existing physical parent')
    _identity({'runtime': runtime})
    started_at = _utc()
    claim = observation_claim(authorization_raw, runtime, started_at)
    root.mkdir(mode=0o700, exist_ok=False)
    _sync(root.parent)
    _new(root / 'authorization.json', authorization_raw)
    _new(root / 'provisional-runtime.json', canonical(runtime))
    _new(root / 'observation-claim.json', canonical(claim))
    observed = root / 'observation'
    observed.mkdir(mode=0o700)
    for name in ('config', 'cwd', 'requests'):
        (observed / name).mkdir(mode=0o700)
    _new(observed / 'config/settings.json', b'{}')
    requests = _Requests(observed / 'requests')
    outputs, state = {'stdout': bytearray(), 'stderr': bytearray()}, {'spawn_count': 0}
    deadline = time.monotonic() + authorized['observation_deadline_seconds']
    try:
        with local_provider(cases=lambda: [], model=aliases.RETURNED, deadline=deadline,
                            observation_request=requests) as (server, url):
            invocation = observation_invocation(runtime, root, url)
            _new(observed / 'invocation.json', canonical(invocation))
            with _signals():
                _run_observation(invocation, deadline, server, outputs, state)
            if server.failure is not None or len(requests.messages) != 1:
                raise ValueError('observation did not retain exactly one successful model request')
        _identity({'runtime': runtime})
        request_raw = requests.messages[0]
        document = observation_document(authorization_raw, runtime, transcript_raw=bytes(outputs['stdout']),
            request_raw=request_raw, provider_url=url, started_at=started_at, finished_at=_utc(), process=state)
        _new(observed / 'native_request.json', request_raw)
        _new(observed / 'transcript.jsonl', bytes(outputs['stdout']))
        _new(observed / 'observation.json', canonical(document))
        validate_observation(observed / 'observation.json')
        return observed / 'observation.json'
    except BaseException as exc:
        _new(observed / 'failure.json', canonical({'error_type': type(exc).__name__,
             'error': str(exc), 'process': state, 'authorization_sha256': sha(authorization_raw)}))
        raise
    finally:
        _new(observed / 'stdout.jsonl', bytes(outputs['stdout']))
        _new(observed / 'stderr.txt', bytes(outputs['stderr']))


def _bound_claim(auth_raw, observation, runtime, expected_raw):
    return {'kind': 'd4d_native_u4b_bound_probe_claim_v1', 'version': 1,
            'authorization_sha256': sha(auth_raw), 'observation': observation['pin'],
            'runtime_sha256': sha(canonical(runtime)), 'expectation_sha256': sha(expected_raw),
            'permission_protocol': PERMISSION_PROTOCOL}


def produce_bound_probe(authorization_raw, expected, directory=None):
    """Consume phase two once; retain the genuine seven-trace permission verifier."""
    from . import native_permission_probe as producer
    from .native_u4b_runtime import validate_prepared_runtime
    expected = strict_json(canonical(expected))
    runtime = validate_prepared_runtime(expected['runtime'])
    basis = strict_json(runtime['limits_basis'])
    observed = validate_observation(basis['observation_probe']['path'],
        expected_pin=basis['observation_probe'], final_runtime=runtime,
        transcript_path=basis['probe']['path'], request_path=basis['request']['path'])
    root = _path(observed['sequence_directory'])
    authorized = authorization(authorization_raw, observed['provisional_runtime'])
    if (sha(authorization_raw) != observed['authorization_sha256']
            or directory is not None and _path(str(directory)) != root):
        raise ValueError('bound phase does not share the exact observation authorization')
    expected_raw = canonical(expected)
    if len(expected_raw) > MAX_BYTES:
        raise ValueError('bound permission expectation exceeds its byte bound')
    producer.require_u4_expectation(expected)
    # Exclusive durable claim precedes every version/probe process. A failed
    # phase stays spent; deleting or retrying its retained directory is forbidden.
    claim = _bound_claim(authorization_raw, observed, runtime, expected_raw)
    _new(root / 'bound-claim.json', canonical(claim))
    _new(root / 'expectation.json', expected_raw)
    output = producer.produce_saved_probe(expected, root / 'permission',
                                          deadline_seconds=authorized['permission_deadline_seconds'])
    raw = _read(output, 100_000_000)
    completion = {'kind': COMPLETION_KIND, 'version': 1,
        'authorization_sha256': sha(authorization_raw), 'observation': observed['pin'],
        'runtime_sha256': sha(canonical(runtime)), 'expectation': _pin(root / 'expectation.json', expected_raw),
        'claim': _pin(root / 'bound-claim.json', canonical(claim)),
        'permission': _pin(root / 'permission/permission-probe.json', raw), 'basis': BASIS}
    _new(root / 'sequence.json', canonical(completion))
    validate_bound_probe(runtime, output)
    return output


def validate_bound_probe(runtime, permission_probe_path):
    """Recheck the acyclic completion plus the actual saved permission consumer."""
    from . import native_shared_permission_orchestration as permission
    from .native_u4b_runtime import validate_prepared_runtime
    runtime = validate_prepared_runtime(runtime)
    basis = strict_json(runtime['limits_basis'])
    observed = validate_observation(basis['observation_probe']['path'],
        expected_pin=basis['observation_probe'], final_runtime=runtime,
        transcript_path=basis['probe']['path'], request_path=basis['request']['path'])
    root = _path(observed['sequence_directory'])
    path = _path(str(permission_probe_path))
    if path != root / 'permission/permission-probe.json':
        raise ValueError('bound permission cannot be its own observation or another sequence')
    raw = _read(root / 'sequence.json', MAX_BYTES)
    value = strict_json(raw)
    _closed(value, {'kind', 'version', 'authorization_sha256', 'observation', 'runtime_sha256',
                    'expectation', 'claim', 'permission', 'basis'}, 'probe sequence completion')
    if (value['kind'] != COMPLETION_KIND or type(value['version']) is not int or value['version'] != 1
            or value['basis'] != BASIS or canonical(value) != raw
            or canonical(value['observation']) != canonical(observed['pin'])
            or value['authorization_sha256'] != observed['authorization_sha256']
            or value['runtime_sha256'] != sha(canonical(runtime))):
        raise ValueError('bound completion differs from its observation, authorization or final runtime')
    expected_raw = _read_pin(value['expectation'], root / 'expectation.json')
    expected = strict_json(expected_raw)
    if canonical(expected['runtime']) != canonical(runtime):
        raise ValueError('bound permission used another final runtime')
    auth_raw = _read(root / 'authorization.json', 16384)
    claim_raw = _read_pin(value['claim'], root / 'bound-claim.json', limit=16384)
    if claim_raw != canonical(_bound_claim(auth_raw, observed, runtime, expected_raw)):
        raise ValueError('bound phase claim differs from its exact inputs')
    permission_raw = _read_pin(value['permission'], path, limit=100_000_000)
    if sha(permission_raw) in {observed[key]['sha256'] for key in ('pin', 'transcript', 'request')}:
        raise ValueError('observation evidence cannot be the bound permission result')
    result = permission.verify_saved_probe(permission_raw, expected=expected)
    if result.get('checked') is not True or result.get('passed') is not True:
        raise ValueError('bound permission evidence did not pass its genuine verifier')
    return {'checked': True, 'passed': True, 'sequence': _pin(root / 'sequence.json', raw),
            'observation': observed['pin'], 'permission': value['permission'], 'basis': BASIS}

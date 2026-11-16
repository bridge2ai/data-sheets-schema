"""Single-use prepared verification in a clean interpreter, outside consumer scopes."""
import sys

from . import native_subscription_guard as wire


def verify(request):
    from . import native_execution_authority_v2 as authority
    from . import native_shared_registration_orchestration as registration
    if request['interpreter'] != [sys.executable, sys.version, sys.implementation.cache_tag]:
        raise ValueError('prepared verifier interpreter changed')
    raw = request['registration'].encode()
    if request['registration_path'] is not None:
        if wire.read_regular(request['registration_path'], limit=32 * 1024 * 1024) != raw:
            raise ValueError('prepared worker registration file changed')
    value_raw = request['value'].encode()
    value = wire.strict_json(value_raw)
    for path, digest in request['sources']:
        try:
            authority._verified_source_bytes(path, digest)
        except (OSError, ValueError) as exc:
            raise ValueError('prepared worker source bytes changed') from exc
    for path, body in request['inputs']:
        if wire.read_regular(path, limit=32 * 1024 * 1024) != body.encode():
            raise ValueError('prepared worker authority bytes changed')
    if request['prepared'] is not None:
        path, body = request['prepared']
        if wire.read_regular(path) != body.encode():
            raise ValueError('prepared worker record bytes changed')
        if wire.strict_json(body.encode())['registration_sha256'] != wire.sha(raw):
            raise ValueError('prepared worker record registration changed')
    if request['mode'] == 'construct':
        current = registration.verified(raw)
    elif request['mode'] in ('recheck', 'unchanged'):
        current = registration._recheck_verified(raw, value, environment_mode='prepared')
    else:
        raise ValueError('unknown prepared verification mode')
    if wire.canonical(current) != value_raw:
        raise ValueError('prepared worker registration changed')
    if request['mode'] == 'unchanged':
        from .native_shared_execution_orchestration import _unchanged_inputs
        authorization = {'inputs': {}, 'raw': {}}
        for index, (path, body) in enumerate(request['inputs']):
            name = str(index)
            authorization['inputs'][name] = path
            authorization['raw'][name] = body.encode()
        _unchanged_inputs(value, authorization)


def main():
    raw = sys.stdin.buffer.read(64 * 1024 * 1024 + 1)
    if len(raw) > 64 * 1024 * 1024:
        raise ValueError('prepared verifier request exceeds bound')
    request = wire.strict_json(raw)
    if wire.canonical(request) != raw:
        raise ValueError('prepared verifier requires exact canonical inputs')
    paths = request['import_paths']
    if type(paths) is not list or any(type(path) is not str for path in paths):
        raise ValueError('prepared verifier import paths must be exact strings')
    # Census the parent's actual paths, with no inherited modules or finders.
    sys.path[:] = paths
    verify(request)
    sys.stdout.buffer.write(wire.canonical({'nonce': request['nonce'],
        'request_sha256': wire.sha(raw), 'passed': True}))


if __name__ == '__main__':
    main()

"""Single-use direct native execution, requiring explicit external authority.

Preparation and readback never invoke a runtime. Only launch() can do so, after
all supplied review/CI/owner and saved permission evidence is checked. Tests use
ordinary Python fake children and private discovery seams, not a public bypass.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import os
from pathlib import Path
import signal
import stat
import subprocess
import sys
import threading

from data_sheets_schema import native_attribution_controller as composition
from data_sheets_schema import native_attribution_registration as draft
from data_sheets_schema import native_attribution_results as replay
from data_sheets_schema import native_execution_authority as authority
from data_sheets_schema import native_execution_registration as registration
from data_sheets_schema import native_execution_gates as gates
from data_sheets_schema import native_supervisor_gates as shared
from data_sheets_schema.native_attempt_supervisor import _file, durable_new, _sync_directory

KIND = 'd4d_native_attribution_attempt'
VERSION = 1
REQUIRED_CHECKS = tuple(f'Python 3.12 / shard {n}' for n in range(1, 7)) + (
    'Python 3.12 / offline audit and finalization', 'Python 3.12 / offline evaluation', 'test', 'large-files')
UNASSESSED = {'scientific_acceptance': 'not_assessed', 'provider_billing': 'not_verified',
              'evidence_authentication': 'not_cryptographically_authenticated'}


def _platform():
    return sys.platform


def _now():
    return datetime.now(timezone.utc).isoformat()


def authorizations(raw, value, *, review_path, ci_path, launch_word_path):
    """Check exact saved external declarations without web discovery."""
    from data_sheets_schema import native_execution_engine
    contract, _ = _engine_bindings()
    return native_execution_engine.authorizations(raw, value, review_path=review_path,
        ci_path=ci_path, launch_word_path=launch_word_path, contract=contract, file=_file)


def _probe_runtime(value):
    """Only called by explicitly authorized launch; no secret output is stored."""
    runtime, env = value['runtime'], value['environment']
    executable = runtime['executable']['path']
    # The subprocess API is a private test seam; there is no public mock route.
    version = subprocess.run([executable, '--version'], cwd=value['working_directory'],
        env=env, capture_output=True, timeout=30, check=True)
    if len(version.stdout) > 65536 or version.stdout.decode('utf-8').strip() != runtime['executable']['version']:
        raise ValueError('observed native binary version differs from its registered identity')
    auth = subprocess.run([executable, 'auth', 'status', '--json'], cwd=value['working_directory'],
        env=env, capture_output=True, timeout=30, check=True)
    if len(auth.stdout) > 1024 * 1024:
        raise ValueError('auth response exceeds the bounded observation contract')
    data = draft._json(auth.stdout)
    if not isinstance(data, dict):
        raise ValueError('auth response is not an explicit mapping')
    keys = ('loggedIn', 'authMethod', 'apiProvider', 'subscriptionType')
    observed = {key: data.get(key) for key in keys}
    expected = {key: runtime['auth'][key] for key in keys}
    if draft._encoded(observed) != draft._encoded(expected):
        raise ValueError('fresh native auth identity differs from the supplied declaration')
    return {'checked': True, 'passed': True, 'observed_at': _now(),
            'binary': registration.executable_identity(executable),
            'version': version.stdout.decode('utf-8').strip(), 'auth': observed,
            'environment_sha256': draft._sha(draft._encoded(env)),
            'scope': 'Fresh version and filtered auth observation; no credential bytes or provider request.'}


def expected_runtime_observation(value):
    """Derive selected identity without observing native auth or invoking a runtime."""
    runtime = value['runtime']
    declared = runtime['executable']
    binary = registration.executable_identity(declared['path'])
    if (binary['path'] != declared['path'] or binary['sha256'] != declared['sha256']
            or type(binary['bytes']) is not int or not 0 <= binary['bytes'] <= 1024**3):
        raise ValueError('runtime executable identity changed from its selected declaration')
    return {'binary': binary, 'version': declared['version'],
        'auth': {key: runtime['auth'][key] for key in ('loggedIn', 'authMethod', 'apiProvider', 'subscriptionType')},
        'environment_sha256': draft._sha(draft._encoded(value['environment']))}


@contextmanager
def _signals(observed):
    if threading.current_thread() is not threading.main_thread():
        raise ValueError('native launch requires the main thread for bounded signal cleanup')
    previous = {sig: signal.getsignal(sig) for sig in (signal.SIGINT, signal.SIGTERM)}
    def interrupt(signum, _frame):
        observed.append(signum)
        if len(observed) == 1:
            raise KeyboardInterrupt(f'native attempt received signal {signum}')
        # Additional signals are recorded while the first interruption cleans up.
    try:
        for sig in previous:
            signal.signal(sig, interrupt)
        yield
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)


def _mkdir_durable(path):
    """Create missing output ancestors, persisting every new directory entry."""
    missing = []
    parent = Path(path)
    while not parent.exists():
        missing.append(parent)
        parent = parent.parent
    if not parent.is_dir() or parent.is_symlink():
        raise ValueError('output ancestor is not a regular directory')
    for directory in reversed(missing):
        directory.mkdir(mode=0o700)
        _sync_directory(directory.parent)


def _unchanged(value, raw, authorization):
    if registration.verified(raw) != value:
        raise ValueError('native execution selection changed')
    authority.require_committed(value['dependencies'])
    for name, path in authorization['inputs'].items():
        if _file(path, name + ' evidence') != authorization['raw'][name]:
            raise ValueError('external launch authority changed')
    if _platform() != value['runtime']['keep_awake']['host_platform']:
        raise ValueError('registered execution host differs from this process')


def _engine_bindings():
    from data_sheets_schema.native_execution_engine import ExecutionContract, ExecutionEffects
    contract = ExecutionContract(kind=KIND, registration=registration, composition=composition,
        authority=authority, gates=gates, replay=replay, shared=shared)
    effects = ExecutionEffects(file=_file, durable_new=durable_new, sync_directory=_sync_directory,
        mkdir_durable=_mkdir_durable, signals=_signals, now=_now, probe_runtime=_probe_runtime,
        expected_runtime_observation=expected_runtime_observation, authorizations=authorizations,
        unchanged=_unchanged, sys=sys)
    return contract, effects


def launch(registration_raw, *, review_path, ci_path, launch_word_path):
    """Consume one explicitly authorized native attempt, never retry or resume."""
    from data_sheets_schema import native_execution_engine
    contract, effects = _engine_bindings()
    return native_execution_engine.launch(registration_raw, review_path=review_path,
        ci_path=ci_path, launch_word_path=launch_word_path, contract=contract, effects=effects)


def read_final(registration_raw):
    """Check complete publication and immutable saved identities; never resume."""
    from data_sheets_schema import native_execution_engine
    contract, effects = _engine_bindings()
    return native_execution_engine.read_final(registration_raw, contract=contract, effects=effects)


def main(argv=None):
    import argparse
    import json
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    prepare = commands.add_parser('prepare', help='offline explicit registration; no runtime or auth calls')
    for name in ('composition', 'system', 'permission-probe', 'runtime', 'attempt-id', 'attempt-directory', 'evidence-directory', 'output'):
        prepare.add_argument('--' + name, required=True)
    prepare.add_argument('--receipt-origin-version', type=int, choices=(0, 1), default=0,
                         help='explicit reported-only captured receipt origin; default keeps legacy output')
    execute = commands.add_parser('launch', help='separately authorized single native attempt; can invoke runtime/auth')
    for name in ('registration', 'review', 'ci', 'launch-word'):
        execute.add_argument('--' + name, required=True)
    read = commands.add_parser('read-final', help='read-only saved publication check')
    read.add_argument('--registration', required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'prepare':
            result = registration.write_registration(args.output, composition_path=args.composition,
                system_path=args.system, permission_probe_path=args.permission_probe,
                runtime=draft._json(_file(args.runtime, 'runtime declaration')), attempt_id=args.attempt_id,
                attempt_directory=args.attempt_directory, evidence_directory=args.evidence_directory,
                receipt_origin_version=args.receipt_origin_version)
        elif args.command == 'launch':
            result = launch(_file(args.registration, 'native registration'), review_path=args.review,
                            ci_path=args.ci, launch_word_path=args.launch_word)
        else:
            result = read_final(_file(args.registration, 'native registration'))
        print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
        return 1 if result.get('runtime_gates_passed') is False else 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f'native execution refused: {type(exc).__name__}: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())

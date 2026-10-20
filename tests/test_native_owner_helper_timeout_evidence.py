"""Pure controls for the literal ordinary peer's timeout evidence helpers.

Only the peer's three function definitions are compiled, never its executable
body or project imports. Popen is a finite fake; no child campaign runs here.
"""
import ast
import hashlib
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest


MISSING = object()


class Child:
    def __init__(self, first, *, drained=(b'drained stdout', b'drained stderr'),
                 kill_error=None, drain_error=None, exit_error=None, suppress=False):
        self.first, self.drained = first, drained
        self.kill_error, self.drain_error, self.exit_error = kill_error, drain_error, exit_error
        self.suppress = suppress
        self.pid, self.returncode = 12345, None
        self.events, self.exit_exception = [], None

    def __enter__(self):
        self.events.append('enter')
        return self

    def __exit__(self, kind, error, traceback):
        self.events.append('exit')
        self.exit_exception = error
        if self.exit_error is not None:
            raise self.exit_error
        return self.suppress

    def communicate(self, timeout=MISSING):
        if timeout is not MISSING:
            self.events.append(('communicate', timeout))
            if isinstance(self.first, BaseException):
                raise self.first
            self.returncode = 0
            return self.first
        self.events.append('drain')
        if self.drain_error is not None:
            raise self.drain_error
        self.returncode = -9
        return self.drained

    def kill(self):
        self.events.append('kill')
        if self.kill_error is not None:
            raise self.kill_error


def peer_functions(root, child):
    source = Path(__file__).with_name('test_native_owner_stage_helper.py').read_text()
    tree = ast.parse(source)
    peer = ast.literal_eval(next(node.value for node in tree.body
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name)
            and target.id == 'PEER' for target in node.targets)))
    definitions = [node for node in ast.parse(peer).body if isinstance(node, ast.FunctionDef)
                   and node.name in {'encoded', 'retain_helper_timeout', 'run_helper'}]
    assert {node.name for node in definitions} == {'encoded', 'retain_helper_timeout', 'run_helper'}
    argv = ['/registered/python', '-m', 'data_sheets_schema.native_shared_stage',
            'advance', '--registration', '/registered/selection.json']
    calls = []
    def popen(*args, **kwargs):
        calls.append((args, kwargs))
        if isinstance(child, BaseException):
            raise child
        return child
    namespace = {'hashlib': hashlib, 'json': json, 'root': root, 'argv': argv,
        'execution': {'working_directory': '/registered/source'},
        'environment': {'FIXTURE_ONLY': 'unchanged'}, 'remaining': 0.25,
        'subprocess': SimpleNamespace(Popen=popen, PIPE=subprocess.PIPE,
                                     TimeoutExpired=subprocess.TimeoutExpired)}
    exec(compile(ast.Module(body=definitions, type_ignores=[]), '<literal-peer-helpers>', 'exec'), namespace)
    return namespace, calls


def timeout(*, output=b'prefix out', stderr=b'prefix err'):
    return subprocess.TimeoutExpired(['fixed helper'], 0.25, output=output, stderr=stderr)


def report(root):
    return json.loads((root / 'helper-timeout.json').read_bytes())


def assert_primary(namespace, primary):
    with pytest.raises(subprocess.TimeoutExpired) as caught:
        namespace['run_helper']()
    assert caught.value is primary
    assert caught.value.timeout == 0.25
    assert str(caught.value) == str(primary)


def test_success_and_non_timeout_failures_keep_original_exchange(tmp_path):
    child = Child((b'{"state":"await_core"}', b''))
    namespace, calls = peer_functions(tmp_path, child)
    stdout, stderr, result = namespace['run_helper']()
    assert stdout == child.first[0] and stderr == b''
    assert result == {'argv': namespace['argv'], 'cwd': '/registered/source',
        'environment_sha256': hashlib.sha256(namespace['encoded'](namespace['environment'])).hexdigest(),
        'pid': 12345, 'returncode': 0, 'stdout_bytes': len(stdout),
        'stdout_sha256': hashlib.sha256(stdout).hexdigest(), 'stderr_bytes': 0,
        'stderr_sha256': hashlib.sha256(b'').hexdigest()}
    assert calls == [((namespace['argv'],), {'cwd': '/registered/source',
        'env': namespace['environment'], 'stdout': subprocess.PIPE, 'stderr': subprocess.PIPE})]
    assert child.events == ['enter', ('communicate', 0.25), 'exit']
    assert list(tmp_path.iterdir()) == []
    for error_site in ('popen', 'communicate', 'context_exit'):
        primary = RuntimeError(error_site)
        failed = (primary if error_site == 'popen' else
                  Child(primary if error_site == 'communicate' else (b'out', b'err'),
                        exit_error=primary if error_site == 'context_exit' else None))
        namespace, _ = peer_functions(tmp_path, failed)
        with pytest.raises(RuntimeError) as caught:
            namespace['run_helper']()
        assert caught.value is primary
        if error_site == 'communicate':
            assert failed.events == ['enter', ('communicate', 0.25), 'kill', 'drain', 'exit']
        assert list(tmp_path.iterdir()) == []


def test_timeout_saves_complete_drain_as_replacement_after_exit(tmp_path):
    primary = timeout(output=b'prefix', stderr=b'err-prefix')
    child = Child(primary, drained=(b'prefix plus suffix', b'err-prefix plus suffix'))
    namespace, calls = peer_functions(tmp_path, child)
    actual_writer = namespace['retain_helper_timeout']
    def after_exit(*args):
        assert child.events[-1] == 'exit'
        return actual_writer(*args)
    namespace['retain_helper_timeout'] = after_exit
    assert_primary(namespace, primary)
    assert len(calls) == 1 and child.exit_exception is primary
    assert child.events == ['enter', ('communicate', 0.25), 'kill', 'drain', 'exit']
    data = report(tmp_path)
    assert data['status'] == 'timeout' and data['drain_completed'] is True
    assert data['context_exit_outcome'] == 'primary_propagated' and data['cleanup_errors'] == {}
    assert data['argv'] == namespace['argv'] and data['cwd'] == '/registered/source'
    assert data['pid'] == 12345 and data['returncode'] == -9
    assert data['primary_error_type'] == 'subprocess.TimeoutExpired'
    for name, raw in zip(('stdout', 'stderr'), child.drained):
        assert (tmp_path / ('helper-timeout-' + name + '.bin')).read_bytes() == raw
        assert data['streams'][name] == {'available': True, 'observed_bytes': len(raw),
            'truncated': False, 'saved': True, 'retained_bytes': len(raw),
            'retained_sha256': hashlib.sha256(raw).hexdigest(), 'capture_error_type': None}
    assert primary.output == b'prefix' and primary.stderr == b'err-prefix'
    assert {p.name for p in tmp_path.iterdir()} == {
        'helper-timeout.json', 'helper-timeout-stdout.bin', 'helper-timeout-stderr.bin'}


def test_unavailable_and_observed_empty_fallback_are_distinct(tmp_path):
    for number, buffers in enumerate(((None, b''), (b'', None), (None, None))):
        root = tmp_path / str(number); root.mkdir()
        primary = timeout(output=buffers[0], stderr=buffers[1])
        child = Child(primary, drain_error=OSError('drain failed'))
        namespace, _ = peer_functions(root, child)
        assert_primary(namespace, primary)
        data = report(root)
        assert data['drain_completed'] is False and data['cleanup_errors'] == {'drain': 'builtins.OSError'}
        for name, raw in zip(('stdout', 'stderr'), buffers):
            row = data['streams'][name]; path = root / ('helper-timeout-' + name + '.bin')
            assert row['available'] is (raw is not None)
            if raw is None:
                assert not path.exists() and row['saved'] is False
                assert row['observed_bytes'] is row['retained_bytes'] is row['retained_sha256'] is None
            else:
                assert path.read_bytes() == b'' and row['saved'] is True
                assert row['observed_bytes'] == row['retained_bytes'] == 0
                assert row['retained_sha256'] == hashlib.sha256(b'').hexdigest()


def test_cleanup_and_context_failures_never_replace_timeout(tmp_path):
    for name, options, expected_errors, exit_outcome in (
        ('kill', {'kill_error': OSError('kill')}, {'kill': 'builtins.OSError'}, 'primary_propagated'),
        ('drain', {'drain_error': RuntimeError('drain')}, {'drain': 'builtins.RuntimeError'}, 'primary_propagated'),
        ('exit', {'exit_error': LookupError('exit')}, {'context_exit': 'builtins.LookupError'}, 'secondary_error'),
        ('suppression', {'suppress': True}, {}, 'primary_suppressed'),
    ):
        root = tmp_path / name; root.mkdir()
        primary = timeout(); child = Child(primary, **options)
        namespace, _ = peer_functions(root, child)
        assert_primary(namespace, primary)
        data = report(root)
        assert data['cleanup_errors'] == expected_errors and data['context_exit_outcome'] == exit_outcome
        assert child.events.count('kill') == 1 and child.events.count('exit') == 1
        assert child.events.count('drain') == (0 if name == 'kill' else 1)
        assert data['drain_completed'] is (name not in ('kill', 'drain'))
        assert child.exit_exception is primary


def test_output_prefixes_are_capped_with_truthful_lengths_and_hashes(tmp_path):
    limit = 1024 * 1024
    buffers = (b'A' * (2 * limit + 7), b'B' * limit)
    primary = timeout(); child = Child(primary, drained=buffers)
    namespace, _ = peer_functions(tmp_path, child)
    assert_primary(namespace, primary)
    data = report(tmp_path)
    assert len((tmp_path / 'helper-timeout.json').read_bytes()) <= 16 * 1024
    for name, raw in zip(('stdout', 'stderr'), buffers):
        prefix = raw[:limit]; row = data['streams'][name]
        assert (tmp_path / ('helper-timeout-' + name + '.bin')).read_bytes() == prefix
        assert row['observed_bytes'] == len(raw) and row['retained_bytes'] == len(prefix)
        assert row['retained_sha256'] == hashlib.sha256(prefix).hexdigest()
        assert row['truncated'] is (len(raw) > limit) and row['saved'] is True
    assert 'environment' not in data


class FaultRoot:
    def __init__(self, root, name, mode):
        self.root, self.name, self.mode = root, name, mode

    def __truediv__(self, name):
        path = self.root / name
        return FaultPath(path, self.mode) if name == self.name else path


class FaultPath:
    def __init__(self, path, mode):
        self.path, self.mode = path, mode

    def open(self, mode):
        assert mode == 'xb'
        if self.mode == 'open':
            raise PermissionError('fixture evidence refusal')
        return FaultStream(self.path.open(mode), self.mode)


class FaultStream:
    def __init__(self, stream, mode):
        self.stream, self.mode = stream, mode

    def __enter__(self):
        return self

    def write(self, raw):
        if self.mode == 'short':
            return self.stream.write(raw[:-1])
        return self.stream.write(raw)

    def __exit__(self, *args):
        self.stream.close()
        if self.mode == 'close':
            raise OSError('fixture close failure')


def test_failed_and_partial_writes_do_not_claim_successful_retention(tmp_path):
    for mode in ('open', 'short', 'close'):
        root = tmp_path / mode; root.mkdir()
        primary = timeout(); child = Child(primary)
        namespace, _ = peer_functions(FaultRoot(root, 'helper-timeout-stdout.bin', mode), child)
        assert_primary(namespace, primary)
        data = report(root); row = data['streams']['stdout']
        assert row['available'] is True and row['observed_bytes'] == len(child.drained[0])
        assert row['saved'] is False and row['retained_bytes'] is row['retained_sha256'] is None
        assert row['capture_error_type'] == ('builtins.PermissionError' if mode == 'open' else 'builtins.OSError')
        assert data['streams']['stderr']['saved'] is True
        assert not (root / 'helper-result.json').exists()
    # Existing artifacts are never replaced by a retry or partial writer.
    root = tmp_path / 'existing'; root.mkdir()
    (root / 'helper-timeout-stdout.bin').write_bytes(b'preserved old bytes')
    primary = timeout(); namespace, _ = peer_functions(root, Child(primary))
    assert_primary(namespace, primary)
    assert (root / 'helper-timeout-stdout.bin').read_bytes() == b'preserved old bytes'
    assert report(root)['streams']['stdout']['capture_error_type'] == 'builtins.FileExistsError'


def test_metadata_and_unexpected_writer_failures_keep_original_timeout(tmp_path):
    for mode in ('open', 'short', 'close'):
        root = tmp_path / mode; root.mkdir()
        primary = timeout(); child = Child(primary)
        namespace, _ = peer_functions(FaultRoot(root, 'helper-timeout.json', mode), child)
        assert_primary(namespace, primary)
        assert not (root / 'helper-result.json').exists()
        assert (root / 'helper-timeout-stdout.bin').read_bytes() == child.drained[0]
    root = tmp_path / 'oversized'; root.mkdir()
    primary = timeout(); namespace, _ = peer_functions(root, Child(primary))
    namespace['argv'] = ['x' * (17 * 1024)]
    assert_primary(namespace, primary)
    assert not (root / 'helper-timeout.json').exists()
    root = tmp_path / 'unexpected'; root.mkdir()
    primary = timeout(); child = Child(primary)
    namespace, _ = peer_functions(root, child)
    def broken_writer(*args):
        assert child.events[-1] == 'exit'
        raise KeyboardInterrupt('diagnostic only')
    namespace['retain_helper_timeout'] = broken_writer
    assert_primary(namespace, primary)
    assert list(root.iterdir()) == []

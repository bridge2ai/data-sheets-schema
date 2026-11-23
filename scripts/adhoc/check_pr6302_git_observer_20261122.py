"""Check optional Git observation without real subprocesses, PR6302, 2026-11-22.

Input: fresh output directory. Output: software-only JSONL cases and result.json.
Fabricated caller code and fake CompletedProcess objects exercise the observer;
no production agent module, Git command, native runtime or provider is invoked.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.adhoc import test_pr6302_round2_20261121 as runner


def caller(invoke, *, depth=0, filename=None, function='_git'):
    """Give compiled software control frames the exact reviewed source label."""
    def forwarding(next_call):
        def local_git_only(*args, **kwargs):
            return next_call(*args, **kwargs)
        return local_git_only
    for _ in range(depth):
        invoke = forwarding(invoke)
    argv = ['git', 'show', 'HEAD:.claude/agents/software-fixture.md']
    env = {'SYNTHETIC_SECRET': 'PRIVATE_ENV_NOT_RETAINED'}
    namespace = {'invoke': invoke, 'Path': Path, 'call_args': (argv,),
        'call_kwargs': {'cwd': Path('/software/resources'), 'capture_output': True,
                        'text': True, 'env': env}}
    source = ('def ' + function + '():\n'
        '    root = Path("/software/resources")\n'
        '    kind = "checkout"\n'
        '    return invoke(*call_args, **call_kwargs)\n')
    exec(compile(source, filename or str(ROOT / 'src/data_sheets_schema/agent_pin.py'), 'exec'), namespace)
    return namespace[function], argv, env


def exercise(directory, name, result, *, error=None, depth=0, filename=None,
             function='_git', recording_error=False):
    selected = directory / name
    selected.mkdir()
    observer = runner.AgentGitObserver(selected)
    forwarded = []
    def fake(*args, **kwargs):
        forwarded.append((args, kwargs))
        if error is not None:
            raise error
        return result
    def broken_record(record):
        raise OSError('synthetic recording failure')
    if recording_error:
        observer._append = broken_record
    with patch.object(runner.subprocess, 'run', fake):
        observer.install()
        invoke, argv, env = caller(runner.subprocess.run, depth=depth,
                                  filename=filename, function=function)
        if error is None:
            assert invoke() is result
        else:
            try:
                invoke()
            except BaseException as caught:
                assert caught is error
            else:
                raise AssertionError('original exception disappeared')
    assert len(forwarded) == 1
    args, kwargs = forwarded[0]
    assert args[0] is argv and kwargs['env'] is env
    assert kwargs['cwd'] == Path('/software/resources')
    assert kwargs['capture_output'] is True and kwargs['text'] is True
    return observer


def guard_fixture(directory):
    """Five process witnesses are software controls, not an executed suite."""
    root = directory / 'five-process-guard'
    for index, worker in enumerate(('controller', 'gw0', 'gw1', 'gw2', 'gw3')):
        pid = 100 + index
        process = root / 'workers' / (worker + '-' + str(pid))
        process.mkdir(parents=True)
        runner._new_json(process / 'start.json', {'worker_id': worker, 'pid': pid,
            'requested_workers': 4 if worker == 'controller' else 0,
            'archive_root': str(root / 'tree'), 'agent_git_observer_requested': True})
        runner._new_json(process / 'imports.json', {'worker_id': worker, 'pid': pid,
            'package_roots': [str(root / 'tree/src/data_sheets_schema')],
            'fairscape_roots': [str(root / 'tree/fairscape_models/fairscape_models')],
            'plugin_path': str(root / 'tree/scripts/adhoc/test_pr6302_round2_20261121.py')})
        observer = runner.AgentGitObserver(process)
        observer.installed = True  # explicit software witness, never a real run
        runner._new_json(process / 'offline-guard.json', {'worker_id': worker, 'pid': pid,
            'session_finished': True, 'pytest_exit_code': 0, 'guard_installed': True,
            'namespace_valid': True, 'namespace_error': None, 'zero_guard_denials': True,
            'denials': [], 'passed': True, 'agent_git_observer': observer.report()})
        if worker != 'controller':
            (root / 'expected-workers').mkdir(exist_ok=True)
            runner._new_json(root / 'expected-workers' / (worker + '.json'),
                             {'worker_id': worker, 'controller_pid': 100})
    return root


def main():
    directory = Path(sys.argv[1]).resolve()
    directory.mkdir(parents=True, exist_ok=False)
    assert 'data_sheets_schema.agent_pin' not in sys.modules
    result = subprocess.CompletedProcess(['unused'], 0,
        stdout='PRIVATE_STDOUT_NOT_RETAINED\n', stderr='synthetic Git stderr\n')
    rows = []
    for name, depth in (('immediate', 0), ('fixture-forwarder', 1), ('last-in-bound', 7)):
        observer = exercise(directory, name, result, depth=depth)
        report = observer.report()
        assert report['records'] == report['attempts'] == 1 and report['problems'] == []
        raw = observer.path.read_bytes()
        record = json.loads(raw)
        assert record['context'] == {'source': str(ROOT / 'src/data_sheets_schema/agent_pin.py'),
            'function': '_git', 'caller_depth': depth, 'resource_root': '/software/resources',
            'resource_kind': 'checkout'}
        assert record['cwd'] == '/software/resources' and record['returncode'] == 0
        assert record['argv'] == ['git', 'show', 'HEAD:.claude/agents/software-fixture.md']
        assert record['stdout'] == {'type': 'str', 'basis': 'returned_text_utf8_surrogatepass',
            'bytes': len(result.stdout.encode()), 'sha256': hashlib.sha256(result.stdout.encode()).hexdigest()}
        assert record['stderr']['text'] == result.stderr
        assert b'PRIVATE_STDOUT_NOT_RETAINED' not in raw and b'PRIVATE_ENV_NOT_RETAINED' not in raw
        rows.append({'control': name, 'passed': True})
    for name, options in (
            ('unrelated-source', {'filename': '/software/unrelated/agent_pin.py'}),
            ('unrelated-function', {'function': 'other_function'}),
            ('beyond-bound', {'depth': 8})):
        observer = exercise(directory, name, result, **options)
        assert observer.report()['records'] == 0 and not observer.path.exists()
        rows.append({'control': name, 'passed': True, 'observed': False})
    for name, error in (('oserror-identity', OSError(4, 'synthetic interrupted operation')),
                        ('interrupt-identity', KeyboardInterrupt('synthetic stop'))):
        observer = exercise(directory, name, result, error=error)
        record = json.loads(observer.path.read_bytes())
        assert record['outcome'] == 'exception' and record['exception_type'] == type(error).__name__
        assert record['returncode'] is None and observer.report()['problems'] == []
        rows.append({'control': name, 'passed': True})
    binary = subprocess.CompletedProcess(['unused'], 128, stdout=b'\xffraw', stderr=b'\xff' * 10000)
    observer = exercise(directory, 'bounded-binary-stderr', binary)
    record = json.loads(observer.path.read_bytes())
    assert record['returncode'] == 128 and record['stdout']['basis'] == 'returned_bytes'
    assert record['stderr']['truncated'] is True and record['stderr']['bytes'] == 10000
    assert len(record['stderr']['text'].encode()) <= runner.AgentGitObserver.STDERR_BYTES
    assert record['stderr']['sha256'] == hashlib.sha256(binary.stderr).hexdigest()
    rows.append({'control': 'bounded-binary-stderr', 'passed': True})
    expanded = subprocess.CompletedProcess(['unused'], 128, stdout=b'', stderr=b'\xff' * 4000)
    observer = exercise(directory, 'decode-expansion-truncation', expanded)
    record = json.loads(observer.path.read_bytes())
    assert record['stderr']['bytes'] < runner.AgentGitObserver.STDERR_BYTES
    assert record['stderr']['truncated'] is True
    assert len(record['stderr']['text'].encode()) <= runner.AgentGitObserver.STDERR_BYTES
    rows.append({'control': 'decode-expansion-truncation', 'passed': True})
    for name, error in (('recording-failure-return', None),
                        ('recording-failure-exception', RuntimeError('original operation failed'))):
        observer = exercise(directory, name, result, error=error, recording_error=True)
        assert observer.report()['problems'] and observer.records == 0 and observer.attempts == 1
        rows.append({'control': name, 'passed': True})
    session = SimpleNamespace(config=SimpleNamespace(_pr6302_evidence={
        'directory': observer.path.parent, 'worker_id': 'controller', 'pid': 123,
        'denials': [], 'guard_installed': True, 'agent_git_observer': observer}), exitstatus=0)
    with patch.object(runner, '_archive_imports', lambda *args, **kwargs: {}):
        runner.pytest_sessionfinish(session, 0)
    assert session.exitstatus == 1
    finish = json.loads((observer.path.parent / 'offline-guard.json').read_bytes())
    assert finish['passed'] is False and finish['agent_git_observer']['problems']
    rows.append({'control': 'recording-failure-gates-finish', 'passed': True})
    for stage in ('context', 'record', 'finish'):
        selected = directory / ('operator-interrupt-' + stage)
        selected.mkdir()
        observer = runner.AgentGitObserver(selected)
        stop = KeyboardInterrupt('software operator interrupt')
        calls = []
        def interrupted(*args, **kwargs):
            raise stop
        def completed(*args, **kwargs):
            calls.append(True)
            return result
        with patch.object(runner.subprocess, 'run', completed):
            observer.install()
            invoke, _, _ = caller(runner.subprocess.run)
            if stage == 'context':
                observer._context = interrupted
            elif stage == 'record':
                observer._append = interrupted
            else:
                observer.path.write_text('')
            try:
                if stage == 'finish':
                    with patch.object(Path, 'read_bytes', interrupted):
                        observer.report()
                else:
                    invoke()
            except KeyboardInterrupt as caught:
                assert caught is stop
            else:
                raise AssertionError('diagnostics swallowed an operator interrupt')
        assert len(calls) == (1 if stage == 'record' else 0)
        rows.append({'control': 'operator-interrupt-' + stage, 'passed': True})
    guard = guard_fixture(directory)
    assert runner._guard_results(guard)['passed'] is True
    target = guard / 'workers/gw2-103/offline-guard.json'
    original = target.read_bytes()
    document = json.loads(original)
    read_bytes = Path.read_bytes
    start_target = target.with_name('start.json')
    start_document = json.loads(start_target.read_bytes())
    for mutation in ('missing', 'problem', 'record_count', 'attempt_type', 'hash',
                     'worker_exit', 'worker_observer_omission'):
        changed = deepcopy(document)
        start_changed = deepcopy(start_document)
        if mutation == 'missing':
            del changed['agent_git_observer']
        elif mutation == 'problem':
            changed['agent_git_observer']['problems'] = ['synthetic failure']
        elif mutation == 'record_count':
            changed['agent_git_observer']['records'] = 0.0
        elif mutation == 'attempt_type':
            changed['agent_git_observer']['attempts'] = False
        elif mutation == 'hash':
            changed['agent_git_observer']['sha256'] = '0' * 64
        elif mutation == 'worker_exit':
            changed['pytest_exit_code'] = 2
        else:
            start_changed['agent_git_observer_requested'] = False
            changed['agent_git_observer'] = None
        replacement = json.dumps(changed).encode()
        start_replacement = json.dumps(start_changed).encode()
        def read(path):
            if path == target:
                return replacement
            return start_replacement if path == start_target else read_bytes(path)
        with patch.object(Path, 'read_bytes', read):
            assert runner._guard_results(guard)['passed'] is False
        rows.append({'control': 'five-process-' + mutation, 'passed': True})
    assert target.read_bytes() == original and 'data_sheets_schema.agent_pin' not in sys.modules
    record = {'passed': True, 'software_controls_only': True, 'controls': rows,
        'limitation': 'Exact agent source/function within eight caller frames only; replacement bypasses and deeper chains are unobserved.'}
    runner._new_json(directory / 'result.json', record)
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    main()

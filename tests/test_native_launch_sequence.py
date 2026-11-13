"""Offline sequence contracts. All three native commands are replaced by fakes.

The subprocess witness copies only the sequence and pure wire helper into an
isolated test package with a fabricated native_generation module.
"""
from pathlib import Path
import builtins
import json
import os
import subprocess
import sys

import pytest

from data_sheets_schema import native_launch_sequence as seq
from data_sheets_schema import native_launch_entry as entry
from data_sheets_schema import native_subscription_guard as guard
from data_sheets_schema import native_host_power as host_power

REAL_RUN = subprocess.run


def run_sequence(arguments):
    return entry.main(arguments)


@pytest.fixture(autouse=True)
def deny_real_commands(monkeypatch):
    monkeypatch.setattr(host_power, 'probe', lambda: {
        'source': 'ac', 'battery_percent': 90, 'lid': 'closed'})
    def refuse(*args, **kwargs):
        pytest.fail('test must not execute native_generation or any native binary')
    monkeypatch.setattr(seq.subprocess, 'run', refuse)
    # Test-only clock substitution AFTER the entry verifies and compiles the
    # real fixture-pinned bytes. Production has no clock/verification bypass.
    def fixture_exec(code, namespace):
        builtins.exec(code, namespace)
        namespace['_utc_now'] = seq._utc_now
    monkeypatch.setattr(entry, 'exec', fixture_exec, raising=False)


def paths(tmp_path):
    base = tmp_path.resolve()
    result = {name: base / (name + '.json') for name in
              ('registration', 'review', 'launch-word', 'account-choice', 'ci')}
    for path in result.values():
        path.write_bytes(b'{}\n')
    digest=guard.sha(Path(seq.__file__).read_bytes())
    result['registration'].write_bytes(guard.canonical({'registration': {
        'attempt_directory': str(base / 'NEVER-RESERVED-ATTEMPT'),
        'evidence_directory': str(base / 'NEVER-RESERVED-EVIDENCE'),
        'attempt_id': 'sequence-fixture',
        'runtime': {'deadline_seconds': 21600, 'model': 'fixture-model',
            'limits': {'contextWindow': 100, 'maxOutputTokens': 10},
            'keep_awake': {'policy': 'macos_iokit_ims_v1', 'host_platform': 'darwin', 'basis': 'offline fixture'},
            'limits_basis': json.dumps({'kind': 'd4d_native_u4b_runtime_basis', 'version': 3,
                'admission': {'capture_state_directory': str(base / 'word-state'),
                    'valid_from': '2026-11-05T00:00:00Z', 'valid_until': '2026-11-19T00:00:00Z',
                    'max_starting_weekly_utilization': 0.5, 'max_starting_five_hour_utilization': 0.25,
                    'max_age_seconds': 1200, 'pre_reservation_margin_seconds': 90}})},
        'dependencies': {'base': {'package_sources': {'src/data_sheets_schema/native_launch_sequence.py': digest}}}}}))
    result['review'].write_bytes(guard.canonical({'kind': 'd4d_native_execution_review_bundle_v3',
        'version': 3, 'registration_sha256': guard.sha(result['registration'].read_bytes()),
        'sequence_script_sha256': digest}))
    from data_sheets_schema import native_capture_words as words
    reg_raw = result['registration'].read_bytes()
    value = guard.strict_json(reg_raw)['registration']
    word = {'authorized_at': '2026-11-11T00:00:00Z', 'attempt_id': value['attempt_id'],
            'registration_sha256': guard.sha(reg_raw), 'review_sha256': guard.sha(result['review'].read_bytes())}
    result['launch-word'].write_bytes(guard.canonical(word))
    with words.locked(value, reg_raw, create=True) as journal:
        journal.activate(result['launch-word'].read_bytes(), result['review'].read_bytes(), value,
                         now=words._timestamp(word['authorized_at'], 'fixture word'))
    result.update({'output-directory': base / 'captures', 'subscription-guard': base / 'guard.json',
                   'packet-directory': base / 'packet'})
    return result


def argv(paths):
    return [part for key, path in paths.items() for part in ('--' + key, str(path))]


def record(paths):
    return json.loads((paths['packet-directory'] / 'sequence.json').read_bytes())


def manifest(paths):
    return paths['output-directory'] / 'captures' / guard.sha(paths['launch-word'].read_bytes()) / 'capture-1/capture.json'


def fake_commands(monkeypatch, paths, *, mutate=None, fail=None, fail_exception=None):
    calls = []
    def run(command, **kwargs):
        assert command[:6] == [sys.executable, '-I', '-B', '-c', seq.BOOTSTRAP, str(seq.SOURCE_ROOT / 'src')]
        name = command[6]
        assert name == seq.COMMANDS[len(calls)], 'wrong order, repeated command or retry'
        calls.append((command, kwargs))
        assert kwargs['stdin'] == subprocess.DEVNULL and kwargs['check'] is False
        assert kwargs['cwd'] == seq.SOURCE_ROOT
        assert kwargs['env'] == seq.CHILD_ENV
        assert kwargs['stdout'].name is not None and kwargs['stderr'].name is not None
        pins = guard.strict_json(command[command.index('--sequence-inputs') + 1].encode())
        names = {'registration', 'review', 'launch_word', 'account_choice', 'ci'}
        if name == seq.COMMANDS[1]: names.add('capture')
        if name == seq.COMMANDS[2]: names.add('subscription_guard')
        assert set(pins) == names
        for key, pin in pins.items():
            assert guard.sha(Path(pin['path']).read_bytes()) == pin['sha256']
        if fail_exception == name:
            raise OSError('PRIVATE sentinel must not be printed')
        if name == seq.COMMANDS[0]:
            path = manifest(paths)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'{"invented":"capture"}\n')
            body = {'capture_manifest': str(path), 'sha256': guard.sha(path.read_bytes())}
        elif name == seq.COMMANDS[1]:
            assert command[command.index('--capture') + 1] == str(manifest(paths))
            target = paths['subscription-guard']
            target.write_bytes(b'{"invented":"guard"}\n')
            body = {'path': str(target), 'guard_sha256': guard.sha(target.read_bytes())}
        else:
            assert command[command.index('--subscription-guard-sha256') + 1] == guard.sha(paths['subscription-guard'].read_bytes())
            body = {'state': 'completed_pending_independent_review', 'runtime_gates_passed': True}
        document = {'command': name, 'result': body}
        data = mutate(name, document) if mutate else None
        raw = guard.canonical(document) if data is None else data
        kwargs['stdout'].write(raw)
        kwargs['stderr'].write(b'PRIVATE child diagnostic\n')
        return subprocess.CompletedProcess(command, 17 if fail == name else 0)
    monkeypatch.setattr(seq.subprocess, 'run', run)
    return calls


def test_order_files_bytes_hashes_times_and_no_environment_input(tmp_path, monkeypatch, capsys):
    p = paths(tmp_path)
    monkeypatch.setenv('PYTHONPATH', '/foreign/secret')
    monkeypatch.setenv('ANTHROPIC_API_KEY', 'PRIVATE')
    monkeypatch.setenv('D4D_OUTPUT', '/foreign/output')
    calls = fake_commands(monkeypatch, p)
    assert run_sequence(argv(p)) == 0
    doc = record(p)
    assert doc['status'] == 'completed' and len(calls) == 3
    assert doc['capture_manifest'] == str(manifest(p))
    for index, step in enumerate(doc['steps']):
        assert step['step'] == seq.COMMANDS[index]
        assert doc['started_at'] <= step['started_at'] <= step['completed_at'] <= doc['completed_at']
        raw = Path(step['output_path']).read_bytes()
        assert step['output_sha256'] == guard.sha(raw)
        assert Path(step['stderr_path']).read_bytes() == b'PRIVATE child diagnostic\n'
        flags = calls[index][0][7:]
        from data_sheets_schema.native_generation import parser
        parsed = parser().parse_args([step['step'], *flags])
        assert parsed.registration == str(p['registration'])
    assert capsys.readouterr().out == ''


@pytest.mark.parametrize('step', seq.COMMANDS)
@pytest.mark.parametrize('exception', [False, True])
def test_nonzero_or_spawn_error_stops_without_retry(tmp_path, monkeypatch, capsys, step, exception):
    p = paths(tmp_path)
    calls = fake_commands(monkeypatch, p, **({'fail_exception': step} if exception else {'fail': step}))
    assert run_sequence(argv(p)) == 1
    expected = seq.COMMANDS.index(step) + 1
    assert len(calls) == expected and len(record(p)['steps']) == expected
    assert record(p)['status'] == 'stopped'
    for name in seq.OUTPUTS[expected:]:
        assert not (p['packet-directory'] / name).exists()
    assert 'PRIVATE' not in capsys.readouterr().err


@pytest.mark.parametrize('step', seq.COMMANDS)
@pytest.mark.parametrize('bad', ['empty', 'malformed', 'duplicate', 'root', 'command_missing', 'command_wrong', 'result_missing', 'result_empty'])
def test_bad_response_stops_before_next_command(tmp_path, monkeypatch, step, bad):
    p = paths(tmp_path)
    def mutate(name, doc):
        if name != step:
            return
        if bad == 'empty': return b''
        if bad == 'malformed': return b'{'
        if bad == 'duplicate': return b'{"result":{},"result":{}}'
        if bad == 'root': return b'[]'
        if bad == 'command_missing': doc.pop('command')
        if bad == 'command_wrong': doc['command'] = 'PRIVATE'
        if bad == 'result_missing': doc.pop('result')
        if bad == 'result_empty': doc['result'] = {}
    calls = fake_commands(monkeypatch, p, mutate=mutate)
    assert run_sequence(argv(p)) == 1
    assert len(calls) == seq.COMMANDS.index(step) + 1


@pytest.mark.parametrize('step,key,value', [
    (0, 'capture_manifest', None), (0, 'capture_manifest', '/foreign/capture.json'),
    (0, 'sha256', None), (0, 'sha256', 'f' * 64), (0, 'sha256', 'bad'),
    (1, 'path', None), (1, 'path', '/foreign/guard.json'),
    (1, 'guard_sha256', None), (1, 'guard_sha256', 'f' * 64), (1, 'guard_sha256', 'bad'),
    (2, 'state', None), (2, 'state', 'failed'), (2, 'state', 'unknown'),
    (2, 'runtime_gates_passed', None), (2, 'runtime_gates_passed', False),
    (2, 'runtime_gates_passed', 1),
])
def test_required_result_values_fail_closed(tmp_path, monkeypatch, step, key, value):
    p = paths(tmp_path)
    def mutate(name, doc):
        if name == seq.COMMANDS[step]:
            if value is None: doc['result'].pop(key)
            else: doc['result'][key] = value
    calls = fake_commands(monkeypatch, p, mutate=mutate)
    assert run_sequence(argv(p)) == 1
    assert len(calls) == step + 1


def test_latest_capture_refusal_is_terminal(tmp_path, monkeypatch):
    p = paths(tmp_path)
    calls = fake_commands(monkeypatch, p, fail=seq.COMMANDS[1])
    assert run_sequence(argv(p)) == 1
    assert len(calls) == 2
    assert record(p)['steps'][-1]['return_code'] == 17


@pytest.mark.parametrize('name', [*seq.OUTPUTS, 'capture-command.stderr.txt', 'guard-command.stderr.txt',
                                 'launch-command.stderr.txt', 'sequence.json', seq.START_FILENAME, 'guard'])
@pytest.mark.parametrize('symlink', [False, True])
def test_existing_outputs_never_overwritten_or_dispatched(tmp_path, name, symlink):
    p = paths(tmp_path)
    p['packet-directory'].mkdir()
    target = p['subscription-guard'] if name == 'guard' else p['packet-directory'] / name
    if symlink:
        target.symlink_to(tmp_path / 'missing')
    else:
        target.write_bytes(b'unchanged')
    assert run_sequence(argv(p)) == 1
    assert target.is_symlink() if symlink else target.read_bytes() == b'unchanged'


def test_repeated_packet_cannot_recapture(tmp_path, monkeypatch):
    p = paths(tmp_path)
    calls = fake_commands(monkeypatch, p)
    assert run_sequence(argv(p)) == 0
    before = {f.name: f.read_bytes() for f in p['packet-directory'].iterdir()}
    assert run_sequence(argv(p)) == 1
    assert len(calls) == 3
    assert {f.name: f.read_bytes() for f in p['packet-directory'].iterdir()} == before


@pytest.mark.parametrize('after', [0, 1])
def test_mutated_inputs_stop_before_later_command(tmp_path, monkeypatch, after):
    p = paths(tmp_path)
    def mutate(name, doc):
        if name == seq.COMMANDS[after]: p['review'].write_bytes(b'changed')
    calls = fake_commands(monkeypatch, p, mutate=mutate)
    assert run_sequence(argv(p)) == 1
    assert len(calls) == after + 1


def test_returned_old_capture_is_refused(tmp_path, monkeypatch):
    p = paths(tmp_path)
    m = manifest(p)
    m.parent.mkdir(parents=True)
    m.write_bytes(b'previous capture')
    calls = fake_commands(monkeypatch, p)
    assert run_sequence(argv(p)) == 1
    assert len(calls) == 1


@pytest.mark.parametrize('change', ['relative', 'missing_input', 'symlink_input', 'guard_collision'])
def test_preflight_refusal_starts_no_command(tmp_path, change):
    p = paths(tmp_path)
    if change == 'relative': p['ci'] = Path('relative.json')
    if change == 'missing_input': p['ci'].unlink()
    if change == 'symlink_input':
        p['ci'].unlink(); p['ci'].symlink_to(p['registration'])
    if change == 'guard_collision': p['subscription-guard'] = p['packet-directory'] / seq.OUTPUTS[0]
    assert run_sequence(argv(p)) == 1


@pytest.mark.parametrize('flag', ['--skip', '--resume', '--reuse-capture', '--continue-on-error'])
def test_no_retry_or_skip_flags(tmp_path, flag):
    with pytest.raises(SystemExit):
        run_sequence([*argv(paths(tmp_path)), flag])


def test_saved_output_exists_before_parse(tmp_path, monkeypatch):
    p = paths(tmp_path)
    original = guard.strict_json
    seen = []
    def parsed(raw):
        doc = original(raw)
        if 'command' not in doc:
            return doc
        path = p['packet-directory'] / seq.OUTPUTS[seq.COMMANDS.index(doc['command'])]
        assert path.read_bytes() == raw
        seen.append(path)
        return doc
    monkeypatch.setattr(guard, 'strict_json', parsed)
    fake_commands(monkeypatch, p)
    assert run_sequence(argv(p)) == 0 and len(seen) == 3


@pytest.mark.parametrize('entry_module', ['native_launch_sequence', 'native_launch_entry'])
def test_isolated_real_subprocess_uses_only_copied_fake_command(tmp_path, entry_module):
    p = paths(tmp_path)
    root = tmp_path / 'isolated'
    package = root / 'src/data_sheets_schema'
    package.mkdir(parents=True)
    (package / '__init__.py').write_bytes(b'')
    for name in ('native_launch_sequence', 'native_subscription_guard', 'native_sequence_start', 'native_launch_entry',
                 'native_capture_words', 'native_subscription_guard_v2', 'native_u4b_policy',
                 'native_shared_runtime_values', 'native_runtime_profiles', 'native_host_power'):
        (package / (name + '.py')).write_bytes((seq.SOURCE_ROOT / 'src/data_sheets_schema' / (name + '.py')).read_bytes())
    (package / 'native_generation.py').write_text('''import json, hashlib, os, sys
from pathlib import Path

def main():
    assert 'PRIVATE_TOKEN' not in os.environ and 'PYTHONPATH' not in os.environ
    name = sys.argv[1]
    flags = dict(zip(sys.argv[2::2], sys.argv[3::2]))
    if name == 'capture-subscription-event':
        word = Path(flags['--launch-word']).read_bytes()
        path = Path(flags['--output-directory']) / 'captures' / hashlib.sha256(word).hexdigest() / 'capture-1/capture.json'
        path.parent.mkdir(parents=True)
        path.write_bytes(b'{}')
        body = {'capture_manifest': str(path), 'sha256': hashlib.sha256(b'{}').hexdigest()}
    elif name == 'prepare-subscription-guard-v2':
        path = Path(flags['--output']); path.write_bytes(b'{}')
        body = {'path': str(path), 'guard_sha256': hashlib.sha256(b'{}').hexdigest()}
    elif name == 'launch':
        body = {'state': 'completed_pending_independent_review', 'runtime_gates_passed': True}
    else:
        raise AssertionError('unexpected command')
    print(json.dumps({'command': name, 'result': body}))
    return 0
''')
    bootstrap = ("import sys,runpy; sys.path.insert(0,sys.argv.pop(1)); name=sys.argv.pop(1); "
                 "from data_sheets_schema import native_host_power; "
                 "native_host_power.probe=lambda: {'source':'ac','battery_percent':90,'lid':'closed'}; "
                 "runpy.run_module(name,run_name='__main__',alter_sys=True)")
    result = REAL_RUN([sys.executable, '-I', '-B', '-c', bootstrap, str(root / 'src'), 'data_sheets_schema.' + entry_module, *argv(p)],
                      env={'PRIVATE_TOKEN': 'secret', 'PYTHONPATH': '/foreign'},
                      cwd=root, capture_output=True, timeout=20)
    assert result.returncode == 0, result.stderr
    assert record(p)['status'] == 'completed'
    assert all(step['argv'][5] == str(root / 'src') for step in record(p)['steps'])


def test_no_new_run_spec_boundaries():
    from tests.utils.run_spec_boundaries import discover
    assert not [item for item in discover(seq.SOURCE_ROOT)
                if item.path == 'src/data_sheets_schema/native_launch_sequence.py']


def test_own_script_bytes_saved_before_any_command_without_self_hash(tmp_path, monkeypatch):
    p = paths(tmp_path)
    running_bytes = Path(seq.__file__).read_bytes()
    seen = []
    def inspect(name, doc):
        saved = p['packet-directory'] / seq.SCRIPT_FILENAME
        assert saved.read_bytes() == running_bytes
        seen.append(name)
    fake_commands(monkeypatch, p, mutate=inspect)
    assert run_sequence(argv(p)) == 0
    doc = record(p)
    assert len(seen) == 3
    assert Path(doc['script_path']).read_bytes() == running_bytes
    assert 'script_sha256' not in doc and 'self_sha256' not in doc
    assert guard.sha(running_bytes) not in json.dumps(doc)


@pytest.mark.parametrize('direction,confirmation,accepted', [
    ('2026-11-12T11:59:00Z', '2026-11-12T11:58:00Z', True),
    ('2026-11-12T11:30:00Z', '2026-11-12T11:30:00Z', True),
    ('2026-11-12T12:00:00Z', '2026-11-12T12:00:00Z', True),
    ('2026-11-12T11:29:59Z', '2026-11-12T11:59:00Z', False),
    ('2026-11-12T11:59:00Z', '2026-11-12T11:29:59Z', False),
    ('2026-11-12T12:00:01Z', '2026-11-12T11:59:00Z', False),
    ('2026-11-12T11:59:00Z', '2026-11-12T12:00:01Z', False),
    ('2026-11-12T11:59:00Z', None, False),
    (None, '2026-11-12T11:59:00Z', False),
    (None, None, True),
])
def test_delegated_start_requires_both_independent_windows(tmp_path, monkeypatch, direction, confirmation, accepted):
    p = paths(tmp_path)
    now = '2026-11-12T12:00:00Z'
    monkeypatch.setattr(seq, '_utc_now', lambda: now)
    calls = fake_commands(monkeypatch, p)
    arguments = argv(p)
    if direction is not None: arguments += ['--direction-recorded-at', direction]
    if confirmation is not None: arguments += ['--host-confirmed-at', confirmation]
    assert run_sequence(arguments) == (0 if accepted else 1)
    assert len(calls) == (3 if accepted else 0)
    doc = record(p)
    assert doc['direction_recorded_at'] == direction and doc['host_confirmed_at'] == confirmation
    assert doc['started_at'] == now
    if not accepted:
        assert doc['steps'] == []
        assert not p['output-directory'].exists()


@pytest.mark.parametrize('timestamp', [
    '2026-11-12', '2026-11-12 12:00:00Z', '2026-11-12T12:00:00+00:00',
    '2026-11-12T12:00:00z', '2026-11-12T12:00Z', '2026-11-12T12:00:00.1234567Z',
    '2026-02-30T12:00:00Z', '2026-11-12T12:00:60Z', '2026-11-12T24:00:00Z', '',
])
def test_delegation_refuses_non_strict_utc_without_commands(tmp_path, monkeypatch, timestamp):
    p = paths(tmp_path)
    monkeypatch.setattr(seq, '_utc_now', lambda: '2026-11-12T12:00:00Z')
    assert run_sequence([*argv(p), '--direction-recorded-at', timestamp,
                     '--host-confirmed-at', '2026-11-12T11:59:00Z']) == 1
    assert record(p)['steps'] == []


def test_elapsed_preflight_cannot_cross_delegation_limit(tmp_path, monkeypatch):
    p = paths(tmp_path)
    times = iter(['2026-11-12T12:00:00Z', '2026-11-12T12:00:01Z', '2026-11-12T12:00:01Z'])
    monkeypatch.setattr(seq, '_utc_now', lambda: next(times))
    assert run_sequence([*argv(p), '--direction-recorded-at', '2026-11-12T11:30:00Z',
                     '--host-confirmed-at', '2026-11-12T11:30:00Z']) == 1
    assert record(p)['steps'] == []
    assert record(p)['delegation_checked_at'] == '2026-11-12T12:00:01Z'


def test_existing_saved_script_refuses_without_overwrite_or_command(tmp_path):
    p = paths(tmp_path)
    p['packet-directory'].mkdir()
    saved = p['packet-directory'] / seq.SCRIPT_FILENAME
    saved.write_bytes(b'prior script')
    assert run_sequence(argv(p)) == 1
    assert saved.read_bytes() == b'prior script'


@pytest.mark.parametrize('source,expected,calls_expected', [('ac', 0, 3), ('battery', 1, 0), ('unknown', 1, 0)])
def test_sequence_power_admission_retains_reading_before_any_child(tmp_path, monkeypatch, source, expected, calls_expected):
    p = paths(tmp_path)
    reading = {'source': source, 'battery_percent': 1, 'lid': 'closed'}
    monkeypatch.setattr(host_power, 'probe', lambda: reading)
    calls = fake_commands(monkeypatch, p)
    assert run_sequence(argv(p)) == expected
    assert len(calls) == calls_expected
    start = json.loads((p['packet-directory'] / seq.START_FILENAME).read_bytes())
    assert start['host_power'] == reading
    assert set(start['clock']) == {'label', 'wall_ns', 'monotonic_ns'}

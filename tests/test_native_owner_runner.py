"""Private runner software fixtures; these E/S documents authorize no native run."""
from copy import deepcopy
import json
import os
from pathlib import Path
import sys
import threading
from types import SimpleNamespace

import pytest

from data_sheets_schema import native_execution_authority as authority
from data_sheets_schema import native_owner_profile_v1 as profile
from data_sheets_schema import native_owner_runner_v1 as runner_module
from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_clock_domain_v1 as clocks


SYNTHETIC_CLOCK = {'format': 'native_clock_domain_v1', 'platform': 'darwin',
    'clock': 'monotonic_ns', 'implementation': 'mach_absolute_time()',
    'boot_uuid': '11111111-2222-4333-8444-555555555555',
    'timebase': {'numerator': 1, 'denominator': 1}}


@pytest.fixture
def fixed_clock(monkeypatch):
    """Invented backend only; keep actual lease lifetime/thread/equality code."""
    monkeypatch.setattr(clocks, '_capture', lambda: (deepcopy(SYNTHETIC_CLOCK), None))
    return deepcopy(SYNTHETIC_CLOCK)


PEER = r'''
import json, pathlib, sys
def emit(value):
    print(json.dumps(value), flush=True)
init = json.loads(sys.stdin.buffer.readline())
emit({'type': 'control_response', 'response': {'subtype': 'success',
    'request_id': init['request_id'], 'response': {}}})
prompt = json.loads(sys.stdin.buffer.readline())
pathlib.Path('received-instruction.txt').write_bytes(prompt['message']['content'].encode('utf-8'))
session = '11111111-2222-4333-8444-555555555555'
emit({'type': 'system', 'subtype': 'init', 'session_id': session, 'cwd': str(pathlib.Path.cwd())})
emit({'type': 'result', 'session_id': session, 'result': 'No tools or providers.'})
'''


class Proxy:
    def __init__(self):
        self.failed = threading.Event()
        self.failure = None
        self.closed = False
        self.state = threading.RLock()

    def close_admission(self):
        self.closed = True


@pytest.fixture
def selected_controls(fixed_clock):
    identity = authority.dependency_identity(stream_snapshot_profile=1)
    with authority.loaded_dependencies(identity) as controls:
        yield controls


def make_case(root, controls, *, deadline_seconds=30):
    """Minimal local association, deliberately not public registration.verified."""
    root = Path(root).resolve()
    root.mkdir()
    attempt = root / 'attempt'
    attempt.mkdir()
    instruction = root / 'instruction.txt'
    instruction.write_bytes('Invented instruction\r\nPreserve café and final newline.\n'.encode())
    peer = root / 'ordinary-peer.py'
    peer.write_text(PEER)
    identity = authority.dependency_identity(stream_snapshot_profile=1)
    policy = {'pretool_control': deepcopy(controls['native_control'].HISTORY_CONTRACT),
              'python': sys.executable, 'readonly_lookups': {
                  'repository': str(root), 'inputs': [], 'output_directories': []}}
    composition = {'kind': 'd4d_native_shared_callback_composition', 'version': 1,
        'working_directory': str(root), 'instruction_path': str(instruction),
        'instruction_sha256': c.sha(instruction.read_bytes()),
        'policy': deepcopy(policy), 'policy_sha256': c.sha(c.canonical(policy)),
        'scope': 'Synthetic private association only; not a verified public composition.'}
    argv = [sys.executable, '-I', '-B', str(peer), '--input-format', 'stream-json']
    env = {'PATH': str(Path(sys.executable).parent) + os.pathsep + '/usr/bin:/bin',
           'LANG': 'en_US.UTF-8'}
    execution = {'kind': c.KINDS['execution'], 'version': 1, 'attempt_id': attempt.name,
        'attempt_directory': str(attempt), 'working_directory': str(root), 'dependencies': identity,
        'argv': list(argv), 'environment': dict(env), 'runtime': {'deadline_seconds': deadline_seconds},
        'instruction_sha256': composition['instruction_sha256'],
        'composition_raw_json': c.canonical(composition).decode(),
        'composition_sha256': c.sha(c.canonical(composition)),
        'scope': 'Explicitly synthetic software fixture. No native permission/review/owner proof.'}
    execution_raw = c.canonical(execution)
    started = {'kind': 'd4d_native_shared_attempt', 'version': 1, 'state': 'started',
        'attempt_id': attempt.name, 'registration_sha256': c.sha(execution_raw),
        'composition_sha256': execution['composition_sha256'], 'dispatch_limit': 1}
    proxy, observed, stops = Proxy(), [], []
    kwargs = {'argv': argv, 'proxy': proxy, 'instruction': instruction, 'attempt': attempt,
        'cwd': str(root), 'env': env, 'deadline_seconds': deadline_seconds,
        'verify_launch': lambda: None, 'record_stop': stops.append,
        'command_policy': policy, 'command_classifier': lambda *a: ('prescribed', 'No tool expected'),
        'event_observer': observed.append, 'execution_raw': execution_raw, 'started_raw': c.canonical(started)}
    return {'root': root, 'attempt': attempt, 'instruction': instruction, 'composition': composition,
        'execution': execution, 'started': started, 'identity': identity, 'controls': controls,
        'runner': profile.bind_runner(identity['stream_snapshot_profile'], controls),
        'proxy': proxy, 'observed': observed, 'stops': stops, 'kwargs': kwargs}


@pytest.fixture
def runner_case(tmp_path, selected_controls):
    return make_case(tmp_path / 'case', selected_controls)


def test_actual_private_runner_preserves_instruction_and_owner_identity(runner_case):
    case = runner_case
    expected = case['instruction'].read_bytes()
    assert case['runner'].execute_child(**case['kwargs']) == 0
    assert (case['root'] / 'received-instruction.txt').read_bytes() == expected
    raw = case['runner'].owner_raw()
    owner = json.loads(raw)
    assert raw == (case['attempt'] / 'stream-owner.json').read_bytes()
    assert owner['format'] == 'native_stream_owner_v2'
    assert owner['clock_domain'] == SYNTHETIC_CLOCK
    assert owner['execution_sha256'] == c.sha(case['kwargs']['execution_raw'])
    assert owner['started_sha256'] == c.sha(case['kwargs']['started_raw'])
    assert owner['deadline_ns'] - owner['start_ns'] == owner['duration_ns'] == 30_000_000_000
    assert set(owner['coordination_profile']['implementations']) == {'runner', 'control', 'coordination', 'clock'}
    for role in ('transcript', 'control'):
        path = case['attempt'] / (role + '.jsonl')
        st = path.stat()
        assert owner[role] == {'path': str(path), 'device': st.st_dev, 'inode': st.st_ino}
    marker = json.loads((case['attempt'] / 'stream-owner-stop.json').read_bytes())
    assert marker == {'format': 'native_stream_owner_stop_v1', 'owner_sha256': c.sha(raw)}
    result = case['runner'].report()
    assert result['state'] == 'completed' and result['dispatches'] == 1
    assert result['owner_published'] is result['stop_marker_published'] is True
    assert result['primary_error'] is None and result['cleanup_errors'] == []
    assert result['control_close']['format'] == 'native_owner_close_v2'
    assert result['control_close']['capture_complete'] is True
    assert result['control_close']['close_deadline_ns'] - result['control_close']['close_start_ns'] == 250_000_000
    assert result['execution_authorized'] is False
    assert case['proxy'].closed and case['proxy'].control_shutdown['control_shutdown_complete']
    assert case['observed'] and case['stops'] == []
    result['state'] = 'invented'
    assert case['runner'].report()['state'] == 'completed'
    assert case['runner'].owner_raw() == raw
    before = {p.name: p.read_bytes() for p in case['attempt'].iterdir() if p.is_file()}
    with pytest.raises(ValueError, match='one-use'):
        case['runner'].execute_child(**case['kwargs'])
    assert {p.name: p.read_bytes() for p in case['attempt'].iterdir() if p.is_file()} == before


@pytest.mark.parametrize('point', ['instruction_capture', 'verify_launch'])
def test_original_attempt_clock_includes_setup_and_verification(runner_case, monkeypatch, point):
    case = runner_case
    clock = [1_000_000_000]
    monkeypatch.setattr(runner_module, 'time', SimpleNamespace(monotonic_ns=lambda: clock[0]))
    elapsed = case['kwargs']['deadline_seconds'] * 1_000_000_000
    if point == 'instruction_capture':
        read = runner_module.evidence.read_regular
        def capture(*args, **kwargs):
            result = read(*args, **kwargs)
            if args[1] == 'instruction': clock[0] += elapsed
            return result
        monkeypatch.setattr(runner_module.evidence, 'read_regular', capture)
    else:
        case['kwargs']['verify_launch'] = lambda: clock.__setitem__(0, clock[0] + elapsed)
    def forbidden(*args, **kwargs):
        raise AssertionError('expired setup must not dispatch a child')
    monkeypatch.setattr(runner_module, '_spawn', forbidden)
    with pytest.raises(case['controls']['budgeted_cborg'].BudgetStop, match='deadline elapsed'):
        case['runner'].execute_child(**case['kwargs'])
    assert case['runner'].report()['dispatches'] == 0
    assert case['runner'].report()['state'] == 'failed'
    if point == 'verify_launch':
        declared = json.loads(case['runner'].owner_raw())
        assert declared['start_ns'] == 1_000_000_000
        assert declared['deadline_ns'] == 1_000_000_000 + elapsed
    else:
        assert case['runner'].owner_raw() is None


@pytest.mark.parametrize('name', runner_module.FILES)
def test_existing_fixed_output_never_gets_replaced(runner_case, name):
    case = runner_case
    path = case['attempt'] / name
    path.write_bytes(b'existing sentinel')
    with pytest.raises(ValueError, match='destination already exists'):
        case['runner'].execute_child(**case['kwargs'])
    assert path.read_bytes() == b'existing sentinel'
    assert sorted(p.name for p in case['attempt'].iterdir()) == [name]
    assert case['runner'].report()['dispatches'] == 0


def test_old_two_role_profile_cannot_bind_runner(selected_controls):
    selected = profile.source_profile(1)
    selected['implementations'].pop('runner')
    selected['implementations'].pop('clock')
    with pytest.raises(ValueError, match='selected loader scope'):
        profile.bind_runner(selected, selected_controls)


def test_private_association_is_not_an_accepted_public_execution(runner_case):
    from data_sheets_schema import native_shared_registration as registration
    with pytest.raises(ValueError):
        registration.verified(runner_case['kwargs']['execution_raw'])
    assert list(runner_case['attempt'].iterdir()) == []

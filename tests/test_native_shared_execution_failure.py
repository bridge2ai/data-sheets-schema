"""Actual public failed publication; runtime observation fails before dispatch."""
from pathlib import Path
import os
import signal
import socket
import subprocess
import pytest
from tests.test_native_shared_execution import make_case
from data_sheets_schema import native_shared_execution_orchestration as execute
from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_execution_authority_v2 as authority


@pytest.fixture
def execution_case(tmp_path, monkeypatch):
    monkeypatch.chdir(authority.ROOT)
    case = make_case(tmp_path / 'v2-lifecycle')
    return case


@pytest.mark.parametrize('missing', ['review_path', 'ci_path', 'launch_word_path'])
def test_missing_external_gate_refuses_before_reservation_or_probe(tmp_path, monkeypatch, missing):
    monkeypatch.chdir(authority.ROOT)
    case = make_case(tmp_path / 'missing-authority')
    path = Path(case['kwargs'][missing])
    path.rename(path.with_suffix('.retained'))
    before = {str(item.relative_to(case['root'])): item.read_bytes()
        for item in case['root'].rglob('*') if item.is_file()}
    def forbidden(*args, **kwargs):
        pytest.fail('missing v2 external gate reached an effect')
    monkeypatch.setattr(execute, '_synthetic_runtime_observation', forbidden)
    monkeypatch.setattr(execute, 'durable_new', forbidden)
    monkeypatch.setattr(execute, '_mkdir_durable', forbidden)
    with pytest.raises((ValueError, FileNotFoundError)):
        execute.synthetic_launch(case['raw'], **case['kwargs'])
    assert not Path(case['value']['attempt_directory']).exists()
    assert not Path(case['value']['evidence_directory']).exists()
    assert {str(item.relative_to(case['root'])): item.read_bytes()
        for item in case['root'].rglob('*') if item.is_file()} == before


def test_public_pre_dispatch_failure_is_readable_and_cannot_resume(tmp_path, monkeypatch):
    original = subprocess.Popen
    calls = []
    def git_only(argv, *args, **kwargs):
        assert isinstance(argv, (list, tuple)) and argv[0] in ('git', '/usr/bin/git'), 'unexpected child dispatch'
        return original(argv, *args, **kwargs)
    def forbidden(*args, **kwargs):
        pytest.fail('pre-dispatch failure made a network connection')
    monkeypatch.setattr(subprocess, 'Popen', git_only)
    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    monkeypatch.chdir(authority.ROOT)
    case = make_case(tmp_path / 'case')
    def observation_failure(value):
        calls.append(value['attempt_id'])
        raise RuntimeError('intentional software-test observation failure; no auth executed')
    monkeypatch.setattr(execute, '_synthetic_runtime_observation', observation_failure)
    result = execute.synthetic_launch(case['raw'], **case['kwargs'])
    (case['root'] / 'actual-failed-result.json').write_bytes(c.canonical(result))
    assert result['state'] == 'failed' and result['runtime_gates_passed'] is False
    assert result['first_stop'] is not None
    assert result['gates']['runtime_authority']['passed'] is False
    verification = result['subscription_observation_verification']
    assert verification['checked'] is verification['complete'] is verification['passed'] is False
    assert 'not independently verified' in verification['basis']
    assert calls == [case['value']['attempt_id']]
    reread = execute.read_final(case['raw'])
    assert reread == result
    with pytest.raises(ValueError, match='new|resume'):
        execute.synthetic_launch(case['raw'], **case['kwargs'])
    assert calls == [case['value']['attempt_id']]
    attempt = Path(case['value']['attempt_directory'])
    assert (attempt / 'started.json').is_file()
    assert not (attempt / 'transcript.jsonl').exists()
    assert result['scientific_acceptance'] == 'not_assessed'


@pytest.mark.parametrize('boundary', ['attempt_parent', 'registration.json', 'started.json', 'evidence_parent'])
def test_v2_partial_reservation_stays_spent_without_probe(execution_case, monkeypatch, boundary):
    case = execution_case
    real_write, real_sync = execute.durable_new, execute._sync_directory
    calls = 0
    def sync(path):
        nonlocal calls
        calls += 1
        if (boundary == 'attempt_parent' and calls == 1) or (boundary == 'evidence_parent' and calls == 2):
            raise OSError('synthetic reservation durability failure')
        return real_sync(path)
    def write(path, raw):
        if Path(path).name == boundary:
            raise OSError('synthetic reservation durability failure')
        return real_write(path, raw)
    monkeypatch.setattr(execute, '_sync_directory', sync)
    monkeypatch.setattr(execute, 'durable_new', write)
    monkeypatch.setattr(execute, '_synthetic_runtime_observation', lambda value: pytest.fail('probe preceded durable reservation'))
    with pytest.raises(OSError, match='durability'):
        execute.synthetic_launch(case['raw'], **case['kwargs'])
    assert Path(case['value']['attempt_directory']).is_dir()
    with pytest.raises(ValueError, match='new|resume'):
        execute.synthetic_launch(case['raw'], **case['kwargs'])


def test_subscription_expiring_during_admission_refuses_before_reservation(execution_case, monkeypatch):
    from data_sheets_schema import native_execution_registration_v2 as admission
    from data_sheets_schema import native_subscription_guard_v2 as subscription
    case = execution_case
    now = [subscription._now()]
    monkeypatch.setattr(subscription, '_now', lambda: now[0])
    real_admit = admission.admit
    completed = []
    def slow_admission(raw, **kwargs):
        result = real_admit(raw, **kwargs)
        completed.append(True)
        now[0] += subscription.MAX_AGE_SECONDS + 1
        return result
    monkeypatch.setattr(admission, 'admit', slow_admission)
    monkeypatch.setattr(execute, '_synthetic_runtime_observation', lambda value: pytest.fail('expired guard reached probe'))
    monkeypatch.setattr(execute, 'durable_new', lambda *args: pytest.fail('expired guard reached durable write'))
    with pytest.raises(ValueError, match='stale|future-dated'):
        execute.synthetic_launch(case['raw'], **case['kwargs'])
    assert completed == [True]
    assert not Path(case['value']['attempt_directory']).exists()
    assert not Path(case['value']['evidence_directory']).exists()


def test_v2_signal_is_sticky_and_previous_handlers_are_restored(execution_case, monkeypatch):
    case = execution_case
    previous = {sig: signal.getsignal(sig) for sig in (signal.SIGTERM, signal.SIGINT)}
    def interrupt_before_native(value):
        os.kill(os.getpid(), signal.SIGTERM)
        pytest.fail('the installed attempt signal handler did not interrupt')
    monkeypatch.setattr(execute, '_synthetic_runtime_observation', interrupt_before_native)
    result = execute.synthetic_launch(case['raw'], **case['kwargs'])
    assert result['state'] == 'failed' and result['runtime_gates_passed'] is False
    assert result['keep_awake']['signals_received'] == [signal.SIGTERM]
    assert result['first_stop'] is not None
    assert all(signal.getsignal(sig) == handler for sig, handler in previous.items())
    assert not (Path(case['value']['attempt_directory']) / 'transcript.jsonl').exists()
    assert execute.read_final(case['raw']) == result


def test_v2_injected_transport_timeout_keeps_registered_limit_and_failure(execution_case, monkeypatch):
    """Inject the transport timeout; no native or Python peer is dispatched."""
    from data_sheets_schema import native_execution_orchestration as lifetime
    case = execution_case
    calls = []
    def timeout(controls, argv, **kwargs):
        calls.append((argv, kwargs['deadline_seconds']))
        assert kwargs['deadline_seconds'] == case['value']['runtime']['deadline_seconds'] == 900
        raise subprocess.TimeoutExpired(argv, kwargs['deadline_seconds'])
    monkeypatch.setattr(lifetime, '_execute_child', timeout)
    result = execute.synthetic_launch(case['raw'], **case['kwargs'])
    assert calls == [(case['value']['argv'], 900)]
    assert result['state'] == 'failed' and result['runtime_gates_passed'] is False
    assert 'TimeoutExpired' in result['first_stop']
    assert result['subscription_guard']['dispatched'] is False
    assert execute.read_final(case['raw']) == result


@pytest.mark.parametrize('boundary', ['final.json', 'published.json'])
def test_v2_publication_failure_preserves_first_error(execution_case, monkeypatch, boundary):
    case = execution_case
    initial_error = RuntimeError('synthetic pre-dispatch observation failure')
    later_error = OSError('synthetic publication failure')
    def failed_probe(value):
        raise initial_error
    original_write = execute.durable_new
    def interrupted(path, raw):
        if Path(path).name == boundary:
            raise later_error
        return original_write(path, raw)
    monkeypatch.setattr(execute, '_synthetic_runtime_observation', failed_probe)
    monkeypatch.setattr(execute, 'durable_new', interrupted)
    with pytest.raises(RuntimeError) as caught:
        execute.synthetic_launch(case['raw'], **case['kwargs'])
    assert caught.value is initial_error
    assert caught.value.__cause__ is later_error
    assert not (Path(case['value']['evidence_directory']) / 'published.json').exists()
    assert (Path(case['value']['attempt_directory']) / 'started.json').is_file()
    with pytest.raises(ValueError, match='new|resume'):
        execute.synthetic_launch(case['raw'], **case['kwargs'])


@pytest.mark.parametrize('filename', ['runtime-observation.json', 'keep-awake.json'])
def test_v2_saved_failure_rechecks_runtime_and_cleanup_after_successful_read(execution_case, monkeypatch, filename):
    case = execution_case
    def failed_probe(value):
        raise RuntimeError('synthetic refusal before any native operation')
    monkeypatch.setattr(execute, '_synthetic_runtime_observation', failed_probe)
    result = execute.synthetic_launch(case['raw'], **case['kwargs'])
    assert execute.read_final(case['raw']) == result
    attempt = Path(case['value']['attempt_directory'])
    path = attempt / filename
    path.write_bytes(path.read_bytes() + b' ')
    # Each case changes only its selected artifact after a successful read.
    # Neither may borrow the earlier runtime/cleanup acceptance.
    with pytest.raises(ValueError):
        execute.read_final(case['raw'])


@pytest.mark.parametrize('role,expected', [
    pytest.param('review', 'review independence, roles or decision differs',
                 id='review-independent v2 approval'),
    pytest.param('ci', 'v2 CI check roster differs from the exact required event roster',
                 id='ci-full v2 required CI'),
])
def test_saved_readback_revalidates_consumed_v2_approvals(execution_case, monkeypatch, role, expected):
    """A partial capture cannot omit its consumed independent approval checks."""
    case = execution_case
    def failed_probe(value):
        raise RuntimeError('synthetic refusal before native dispatch')
    monkeypatch.setattr(execute, '_synthetic_runtime_observation', failed_probe)
    result = execute.synthetic_launch(case['raw'], **case['kwargs'])
    assert execute.read_final(case['raw']) == result
    path = Path(case['value']['attempt_directory']) / (role + '.json')
    changed = c.strict_json(path.read_bytes())
    if role == 'review':
        changed['reviews'][0]['decision'] = 'rejected'
    else:
        changed['checks'].pop(next(iter(changed['checks'])))
    path.write_bytes(c.canonical(changed))
    with pytest.raises(ValueError, match=expected):
        execute.read_final(case['raw'])

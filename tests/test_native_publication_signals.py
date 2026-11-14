"""Issue 6217: publication signals retain readable immutable final evidence.

The public witnesses stop before any peer dispatch. Host readings are invented
by isolated_modules; unit cases have no child, network or host probe.
"""
from pathlib import Path
import signal
from types import SimpleNamespace

import pytest

from data_sheets_schema import native_execution as legacy
from data_sheets_schema import native_execution_orchestration as engine
from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_subscription_admission as subscription
from tests.test_native_execution_registration_v2 import isolated_modules  # noqa: F401

pytestmark = pytest.mark.usefixtures('isolated_modules')


@pytest.mark.parametrize('signum', [signal.SIGINT, signal.SIGTERM])
@pytest.mark.parametrize('unexpected_error', [False, True])
def test_record_only_survives_first_and_repeated_signals_and_restores_handlers(signum, unexpected_error):
    previous = {sig: signal.getsignal(sig) for sig in (signal.SIGINT, signal.SIGTERM)}
    observed = []
    sentinel = RuntimeError('declared publication failure')
    try:
        with legacy._signals(observed) as record_only:
            record_only()
            signal.raise_signal(signum)
            signal.raise_signal(signum)
            assert observed == [signum, signum]
            if unexpected_error:
                raise sentinel
    except RuntimeError as exc:
        assert unexpected_error and exc is sentinel
    else:
        assert not unexpected_error
    assert all(signal.getsignal(sig) == handler for sig, handler in previous.items())


@pytest.mark.parametrize('signum', [signal.SIGINT, signal.SIGTERM])
def test_preparation_first_signal_still_interrupts_then_cleanup_records(signum):
    previous = {sig: signal.getsignal(sig) for sig in (signal.SIGINT, signal.SIGTERM)}
    observed = []
    with legacy._signals(observed) as record_only:
        with pytest.raises(KeyboardInterrupt, match='native attempt received signal'):
            try:
                signal.raise_signal(signum)
            finally:
                record_only()
        signal.raise_signal(signum)
    assert observed == [signum, signum]
    assert all(signal.getsignal(sig) == handler for sig, handler in previous.items())


@pytest.mark.parametrize('initial_completed,earlier_stop', [(False, 'earlier failure'), (True, None)])
def test_late_signal_revalidates_exact_failed_mode_once(monkeypatch, initial_completed, earlier_stop):
    observed, calls = [], []
    failed = {'checked': False, 'complete': False, 'passed': False,
              'transcript_diagnostic': {'declared': 'failed-mode replay'}}
    successful = {'checked': True, 'complete': True, 'passed': True}
    def observations(*args, complete, **kwargs):
        calls.append(complete)
        observed.append(signal.SIGINT if len(calls) == 1 else signal.SIGTERM)
        return successful if complete else failed
    monkeypatch.setattr(subscription, 'context', lambda *a, **k: (
        SimpleNamespace(validate_saved_observations=observations), {}))
    guard = SimpleNamespace(raw=b'guard', snapshot=lambda: {'dispatched': True})
    snapshot, verdict, failure, received, first_stop = engine._publication_signal_cutoff(
        guard, b'registration', {}, {'raw': {'launch_word': b'word', 'review': b'review'}},
        b'transcript', completed=initial_completed, signals=observed, first_stop=earlier_stop)
    assert snapshot == {'dispatched': True} and failure is None
    assert verdict is failed
    assert calls == ([True, False] if initial_completed else [False])
    assert received == (signal.SIGINT,)
    assert first_stop == (earlier_stop or 'launcher interrupted by signal ' + str(signal.SIGINT))
    # A signal during failed-mode revalidation cannot reopen the fixed decision.
    assert observed == ([signal.SIGINT, signal.SIGTERM] if initial_completed else [signal.SIGINT])


def test_signal_cutoff_does_not_turn_validation_refusal_into_success(monkeypatch):
    calls, observed = [], []
    def refuse(*args, **kwargs):
        calls.append(True)
        observed.append(signal.SIGTERM)
        raise ValueError('declared validation refusal')
    monkeypatch.setattr(subscription, 'context', refuse)
    guard = SimpleNamespace(raw=b'guard', snapshot=lambda: {'dispatched': False})
    _, verdict, failure, received, first_stop = engine._publication_signal_cutoff(
        guard, b'registration', {}, {'raw': {'launch_word': b'word', 'review': b'review'}},
        None, completed=True, signals=observed, first_stop=None)
    assert calls == [True] and received == (signal.SIGTERM,)
    assert verdict['passed'] is verdict['complete'] is False
    assert failure['reason'] == 'declared validation refusal'
    assert first_stop == 'launcher interrupted by signal ' + str(signal.SIGTERM)


def test_signal_after_cutoff_keeps_the_original_successful_decision(monkeypatch):
    observed = []
    verdict = {'checked': True, 'complete': True, 'passed': True}
    monkeypatch.setattr(subscription, 'context', lambda *a, **k: (
        SimpleNamespace(validate_saved_observations=lambda *a, **k: verdict), {}))
    guard = SimpleNamespace(raw=b'guard', snapshot=lambda: {'dispatched': True})
    with legacy._signals(observed) as record_only:
        record_only()
        _, saved, failure, received, first_stop = engine._publication_signal_cutoff(
            guard, b'registration', {}, {'raw': {'launch_word': b'word', 'review': b'review'}},
            b'transcript', completed=True, signals=observed, first_stop=None)
        signal.raise_signal(signal.SIGINT)
        signal.raise_signal(signal.SIGTERM)
    assert failure is None and received == () and first_stop is None and saved is verdict
    assert observed == [signal.SIGINT, signal.SIGTERM]


@pytest.mark.parametrize('signum', [signal.SIGINT, signal.SIGTERM])
def test_public_first_signal_during_publication_keeps_exact_readback(tmp_path, monkeypatch, signum):
    from tests.test_native_shared_execution import make_case
    from data_sheets_schema import native_shared_execution_orchestration as execute
    from data_sheets_schema import native_execution_authority_v2 as authority
    monkeypatch.chdir(authority.ROOT)
    case = make_case(tmp_path / 'publication-signals')
    previous = {sig: signal.getsignal(sig) for sig in (signal.SIGINT, signal.SIGTERM)}
    def fail_before_dispatch(value):
        raise RuntimeError('declared offline failure before any peer dispatch')
    monkeypatch.setattr(execute, '_synthetic_runtime_observation', fail_before_dispatch)
    def forbidden_transport(*args, **kwargs):
        pytest.fail('publication signal witness dispatched a child')
    monkeypatch.setattr(engine, '_execute_child', forbidden_transport)
    original_publication = engine._publication_subscription
    consumed, boundaries = {}, []
    def interrupted_publication(*args, **kwargs):
        cleanup = Path(case['value']['attempt_directory']) / 'keep-awake.json'
        consumed['cleanup'] = cleanup.read_bytes()
        boundaries.append('subscription')
        signal.raise_signal(signum)
        return original_publication(*args, **kwargs)
    monkeypatch.setattr(engine, '_publication_subscription', interrupted_publication)
    original_write = execute.durable_new
    def interrupted_write(path, raw):
        if Path(path).name in ('final.json', 'published.json'):
            boundaries.append(Path(path).name)
            signal.raise_signal(signum)
        return original_write(path, raw)
    monkeypatch.setattr(execute, 'durable_new', interrupted_write)
    result = execute.synthetic_launch(case['raw'], **case['kwargs'])
    assert boundaries == ['subscription', 'final.json', 'published.json']
    assert result['state'] == 'failed' and result['runtime_gates_passed'] is False
    assert result['first_stop'] == 'launch or runtime failed: RuntimeError'
    assert result['gates']['first_stop'] == {
        'checked': True, 'passed': False, 'reason': result['first_stop']}
    assert all(signal.getsignal(sig) == handler for sig, handler in previous.items())
    attempt = Path(case['value']['attempt_directory'])
    evidence = Path(case['value']['evidence_directory'])
    assert (attempt / 'keep-awake.json').read_bytes() == consumed['cleanup']
    assert result['keep_awake'] == c.strict_json(consumed['cleanup'])
    assert (evidence / 'final.json').read_bytes() == c.canonical(result)
    marker = c.strict_json((evidence / 'published.json').read_bytes())
    assert marker['final_sha256'] == c.sha((evidence / 'final.json').read_bytes())
    assert execute.read_final(case['raw']) == result

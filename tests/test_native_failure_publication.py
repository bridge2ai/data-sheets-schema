"""#5967: diagnostic publication cannot become successful verification."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

from data_sheets_schema import native_execution_orchestration as engine
from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_subscription_admission as subscription
from tests.test_native_execution_registration_v2 import isolated_modules  # noqa: F401

# Historical and v2 closures share bare aliases. Preserve the production
# origin refusal while isolating collection imports and prior test cases.
pytestmark = pytest.mark.usefixtures('isolated_modules')


@pytest.mark.parametrize('stage', ['context', 'observations'])
def test_runtime_validation_failure_never_returns_success(monkeypatch, stage):
    def declared_runtime_failure(*args, **kwargs):
        raise ValueError('declared fixture: runtime validation failed')
    monkeypatch.setattr(subscription, 'context', declared_runtime_failure if stage == 'context'
        else lambda *args, **kwargs: (SimpleNamespace(validate_saved_observations=declared_runtime_failure), {}))
    guard = SimpleNamespace(raw=b'guard', snapshot=lambda: {'dispatched': False})
    snapshot, verification, failure = engine._publication_subscription(
        guard, b'registration', {}, {'raw': {'launch_word': b'word', 'review': b'review'}},
        None, completed=True)
    assert snapshot == {'dispatched': False}
    assert verification['checked'] is verification['passed'] is verification['complete'] is False
    expected_stage = 'subscription_admission.context' if stage == 'context' else 'subscription_guard.validate_saved_observations'
    assert failure == {'stage': expected_stage, 'error_type': 'ValueError',
                       'reason': 'declared fixture: runtime validation failed'}


def test_success_publication_runs_context_and_complete_observation_checks(monkeypatch):
    calls = []
    verdict = {'checked': True, 'passed': True, 'complete': True}
    def observations(*args, **kwargs):
        calls.append(('observations', kwargs))
        return verdict
    def context(*args, **kwargs):
        calls.append(('context', kwargs))
        return SimpleNamespace(validate_saved_observations=observations), {'owner_statement': 'exact'}
    monkeypatch.setattr(subscription, 'context', context)
    guard = SimpleNamespace(raw=b'guard', snapshot=lambda: {'dispatched': True})
    _, result, failure = engine._publication_subscription(
        guard, b'registration', {'runtime': 'exact'},
        {'raw': {'launch_word': b'word', 'review': b'review'}}, b'transcript', completed=True)
    assert result is verdict and failure is None
    assert [name for name, _ in calls] == ['context', 'observations']
    assert calls[0][1]['runtime'] == {'runtime': 'exact'}
    assert calls[1][1]['complete'] is True
    assert calls[1][1]['transcript_raw'] == b'transcript'
    assert calls[1][1]['owner_statement'] == 'exact'


def test_successful_readback_still_requires_fresh_verification(tmp_path, monkeypatch):
    from data_sheets_schema import native_shared_execution_orchestration as execute
    contract, effects = execute._engine_bindings()
    # A normal publication must still enter the unchanged guarded verifier.
    sentinel = ValueError('successful reader reached fresh registration verification')
    def verify(raw):
        raise sentinel
    monkeypatch.setattr(contract.registration, 'verified', verify)
    from dataclasses import replace
    body = dict.fromkeys(engine.admission.EXECUTION_KEYS)
    body.update(kind=engine.admission.EXECUTION_KIND, schema_version=2,
        execution=engine.admission.EXECUTION_SCOPE, execution_gates=list(engine.GATES),
        attempt_directory=str(tmp_path / 'attempt'), evidence_directory=str(tmp_path / 'evidence'))
    raw = c.canonical({'authority_version': 2, 'controller_sources_sha256': 'a' * 64,
                       'registration': body})
    effects = replace(effects, file=lambda *args: c.canonical({'state': 'completed_pending_independent_review'}))
    with pytest.raises(ValueError) as caught:
        engine.read_final(raw, contract=contract, effects=effects)
    assert caught.value is sentinel


@pytest.mark.parametrize('observation_failure', [None, 'start', 'end'])
def test_public_declared_runtime_failure_publishes_exact_readback(tmp_path, monkeypatch, observation_failure):
    from tests.test_native_shared_execution import make_case
    from data_sheets_schema import native_shared_execution_orchestration as execute
    from data_sheets_schema import native_execution_authority_v2 as authority
    from data_sheets_schema import native_host_power as power
    monkeypatch.setattr(power, 'probe', lambda: {'source': 'ac'})
    if observation_failure:
        write = power._write_new
        def broken_sidecar(path, value):
            if path.name == 'host-clock-' + observation_failure + '.json':
                raise OSError('synthetic persistence failure')
            return write(path, value)
        monkeypatch.setattr(power, '_write_new', broken_sidecar)
    monkeypatch.chdir(authority.ROOT)
    case = make_case(tmp_path / 'runtime-validation-failure')
    def invalidate_runtime(value):
        # Intentional fixture condition, independent of the PyStow HOME defect.
        home = Path(value['environment']['HOME'])
        (home / 'declared-invalid-runtime').write_text('offline test fixture\n')
        raise RuntimeError('declared fixture invalidated runtime before any peer dispatch')
    monkeypatch.setattr(execute, '_synthetic_runtime_observation', invalidate_runtime)
    result = execute.synthetic_launch(case['raw'], **case['kwargs'])
    (case['root'] / 'actual-failed-result.json').write_bytes(c.canonical(result))
    assert result['state'] == 'failed' and result['runtime_gates_passed'] is False
    assert result['gates']['first_stop']['passed'] is False
    assert result['first_stop'] == 'launch or runtime failed: RuntimeError'
    if observation_failure:
        diagnostic = Path(case['value']['attempt_directory']) / ('host-observation-error-' + observation_failure + '.json')
        assert c.strict_json(diagnostic.read_bytes()) == {'boundary': observation_failure, 'error_type': 'OSError'}
    assert result['publication_validation_failure']['stage'] == 'subscription_admission.context'
    assert 'synthetic HOME' in result['publication_validation_failure']['reason']
    assert execute.read_final(case['raw']) == result
    evidence = Path(case['value']['evidence_directory'])
    final_path, marker_path = evidence / 'final.json', evidence / 'published.json'
    saved_final, saved_marker = final_path.read_bytes(), marker_path.read_bytes()
    for change in ('state', 'runtime_gates_passed', 'first_stop', 'all_gates',
                   'cleanup_assessment', 'lifecycle_hash', 'cleanup_gate', 'remove_diagnostic'):
        forged = deepcopy(result)
        if change == 'state':
            forged['state'] = 'completed_pending_independent_review'
        elif change == 'runtime_gates_passed':
            forged['runtime_gates_passed'] = True
        elif change == 'first_stop':
            forged['first_stop'] = None
        elif change == 'all_gates':
            forged['gates'] = {key: {'checked': True, 'passed': True} for key in engine.GATES}
        elif change == 'cleanup_assessment':
            forged['keep_awake']['passed'] = not forged['keep_awake']['passed']
        elif change == 'lifecycle_hash':
            forged['lifecycle_artifacts']['keep-awake.json']['sha256'] = '0' * 64
        elif change == 'cleanup_gate':
            forged['gates']['keep_awake']['passed'] = not forged['gates']['keep_awake']['passed']
        else:
            del forged['publication_validation_failure']
        final_path.write_bytes(c.canonical(forged))
        marker = c.strict_json(saved_marker)
        marker['final_sha256'] = c.sha(final_path.read_bytes())
        marker_path.write_bytes(c.canonical(marker))
        expected = ('cleanup evidence' if change in ('cleanup_assessment', 'cleanup_gate')
                    else 'lifecycle pins' if change == 'lifecycle_hash'
                    else 'synthetic HOME' if change == 'remove_diagnostic'
                    else 'failure diagnostic')
        with pytest.raises(ValueError, match=expected):
            execute.read_final(case['raw'])
    final_path.write_bytes(saved_final)
    marker_path.write_bytes(saved_marker)
    attempt = Path(case['value']['attempt_directory'])
    runtime_path = attempt / 'runtime-observation.json'
    runtime_raw = runtime_path.read_bytes()
    runtime_path.write_bytes(runtime_raw + b' ')
    try:
        with pytest.raises(ValueError, match='evidence'):
            execute.read_final(case['raw'])
    finally:
        runtime_path.write_bytes(runtime_raw)
    runtime_path.unlink()
    with pytest.raises(ValueError, match='evidence cannot be read'):
        execute.read_final(case['raw'])
    replacement = attempt / 'replacement-runtime.json'
    replacement.write_bytes(runtime_raw)
    runtime_path.symlink_to(replacement)
    with pytest.raises(ValueError, match='evidence cannot be read'):
        execute.read_final(case['raw'])
    runtime_path.unlink()
    runtime_path.write_bytes(runtime_raw)
    assert execute.read_final(case['raw']) == result


def test_publication_pins_consumed_lifecycle_and_reports_later_change(tmp_path, monkeypatch):
    from tests.test_native_shared_execution import make_case
    from data_sheets_schema import native_shared_execution_orchestration as execute
    from data_sheets_schema import native_execution_authority_v2 as authority
    monkeypatch.chdir(authority.ROOT)
    case = make_case(tmp_path / 'changed-cleanup')
    attempt = Path(case['value']['attempt_directory'])
    def invalidate_runtime(value):
        (Path(value['environment']['HOME']) / 'declared-invalid-runtime').write_text('fixture')
        raise RuntimeError('fixture runtime failure')
    monkeypatch.setattr(execute, '_synthetic_runtime_observation', invalidate_runtime)
    original = engine._publication_subscription
    consumed = {}
    def change_after_assessment(*args, **kwargs):
        path = attempt / 'keep-awake.json'
        consumed['raw'] = path.read_bytes()
        path.write_bytes(consumed['raw'] + b' ')
        return original(*args, **kwargs)
    monkeypatch.setattr(engine, '_publication_subscription', change_after_assessment)
    result = execute.synthetic_launch(case['raw'], **case['kwargs'])
    pin = result['failure_evidence']['keep-awake.json']
    assert result['state'] == 'failed'
    assert pin['sha256'] == c.sha(consumed['raw'])
    assert pin['sha256'] == result['lifecycle_artifacts']['keep-awake.json']['sha256']
    assert pin['changed_after_consumption'] == 'disk bytes differ from consumed bytes'
    with pytest.raises(ValueError, match='failure evidence'):
        execute.read_final(case['raw'])
    (attempt / 'keep-awake.json').write_bytes(consumed['raw'])
    assert execute.read_final(case['raw']) == result


def test_successful_readback_runtime_failure_is_not_downgraded(tmp_path, monkeypatch):
    """A normal completed record must still refuse a current runtime failure.

    This is a reader routing unit, not fabricated proof of a successful launch.
    Registration/authority semantics are test seams; disk bindings are real.
    """
    from data_sheets_schema import native_shared_execution_orchestration as execute
    contract, effects = execute._engine_bindings()
    attempt, evidence = tmp_path / 'attempt', tmp_path / 'evidence'
    attempt.mkdir(); evidence.mkdir()
    body = dict.fromkeys(engine.admission.EXECUTION_KEYS)
    body.update(kind=engine.admission.EXECUTION_KIND, schema_version=2,
        execution=engine.admission.EXECUTION_SCOPE, execution_gates=list(engine.GATES),
        attempt_directory=str(attempt), evidence_directory=str(evidence),
        attempt_id='reader-unit', composition_sha256='a' * 64, runtime={})
    raw = c.canonical({'authority_version': 2, 'controller_sources_sha256': 'b' * 64, 'registration': body})
    started = b'{}\n'
    for name, data in {'registration.json': raw, 'started.json': started,
                       'subscription-guard.json': b'{}', 'launch_word.json': b'{}', 'review.json': b'{}'}.items():
        (attempt / name).write_bytes(data)
    result = {'kind': contract.kind, 'version': 1, 'attempt_id': body['attempt_id'],
        'composition_sha256': body['composition_sha256'], 'registration_sha256': c.sha(raw),
        'started_sha256': c.sha(started), **engine.UNASSESSED,
        'state': 'completed_pending_independent_review', 'runtime_gates_passed': True,
        'subscription_guard': {}}
    final = c.canonical(result)
    (evidence / 'final.json').write_bytes(final)
    (evidence / 'published.json').write_bytes(c.canonical({'final_sha256': c.sha(final),
        'registration_sha256': c.sha(raw), 'started_sha256': c.sha(started)}))
    monkeypatch.setattr(contract.registration, 'verified', lambda supplied: body)
    monkeypatch.setattr(engine, '_saved_authorizations', lambda *args, **kwargs: None)
    def invalid_runtime(*args, **kwargs):
        raise ValueError('declared successful-readback runtime failure')
    monkeypatch.setattr(subscription, 'context', invalid_runtime)
    with pytest.raises(ValueError, match='successful-readback runtime failure'):
        execute.read_final(raw)

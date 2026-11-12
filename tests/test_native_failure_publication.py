"""#5967: diagnostic publication cannot become successful verification."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

from data_sheets_schema import native_execution_orchestration as engine
from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_subscription_admission as subscription


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


def test_public_declared_runtime_failure_publishes_exact_readback(tmp_path, monkeypatch):
    from tests.test_native_shared_execution import make_case
    from data_sheets_schema import native_shared_execution_orchestration as execute
    from data_sheets_schema import native_execution_authority_v2 as authority
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
    assert result['publication_validation_failure']['stage'] == 'subscription_admission.context'
    assert 'synthetic HOME' in result['publication_validation_failure']['reason']
    assert execute.read_final(case['raw']) == result
    evidence = Path(case['value']['evidence_directory'])
    final_path, marker_path = evidence / 'final.json', evidence / 'published.json'
    saved_final, saved_marker = final_path.read_bytes(), marker_path.read_bytes()
    for change in ('state', 'runtime_gates_passed', 'first_stop', 'all_gates'):
        forged = deepcopy(result)
        if change == 'state':
            forged['state'] = 'completed_pending_independent_review'
        elif change == 'runtime_gates_passed':
            forged['runtime_gates_passed'] = True
        elif change == 'first_stop':
            forged['first_stop'] = None
        else:
            forged['gates'] = {key: {'checked': True, 'passed': True} for key in engine.GATES}
        final_path.write_bytes(c.canonical(forged))
        marker = c.strict_json(saved_marker)
        marker['final_sha256'] = c.sha(final_path.read_bytes())
        marker_path.write_bytes(c.canonical(marker))
        with pytest.raises(ValueError, match='failure diagnostic'):
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

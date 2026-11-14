"""Issue 6233: prefix anchors, transactional suffixes and sticky binding guards."""
from dataclasses import fields, is_dataclass, replace
from types import ModuleType

import pytest

from data_sheets_schema import native_shared_callback_capture as owner_api
from data_sheets_schema import native_shared_callback_orchestration as guards
from data_sheets_schema import native_shared_capture as capture
from data_sheets_schema import native_shared_stage as stage
from tests.test_native_shared_saved_advance import advance, captured_run
from tests import test_native_shared_saved_advance as saved_fixture
from tests.test_native_shared_stages import case, artifact, respond, receipt_answer, publish, add_core, full_roundtrip
from tests.test_typed_audit import supplied


def guard_for(module):
    return guards._ValidatorGuard((module,), lambda: None, b'fixed admission')


def test_effective_binding_alias_change_is_sticky():
    module = ModuleType('test_validator')
    dependency = ModuleType('data_sheets_schema.typed_audit')
    module.typed = dependency
    guard = guard_for(module)
    assert guard.reusable()
    module.typed = ModuleType(dependency.__name__)
    assert not guard.reusable()
    module.typed = dependency
    assert not guard.reusable()


def test_default_and_closure_changes_are_sticky():
    original = ModuleType('data_sheets_schema.typed_audit')
    changed = ModuleType(original.__name__)
    def factory(binding):
        def validator(default=binding):
            return default, binding
        return validator
    for kind in ('default', 'closure'):
        module = ModuleType('test_validator')
        module.validator = factory(original)
        guard = guard_for(module)
        assert guard.reusable()
        if kind == 'default':
            defaults = module.validator.__defaults__
            module.validator.__defaults__ = (changed,)
        else:
            module.validator.__closure__[0].cell_contents = changed
        assert not guard.reusable()
        if kind == 'default':
            module.validator.__defaults__ = defaults
        else:
            module.validator.__closure__[0].cell_contents = original
        assert not guard.reusable()


def test_guard_covers_private_bounds_and_refuses_unknown_package_binding():
    module = ModuleType('test_validator')
    module._LIMITS = {'response': 12}
    guard = guard_for(module)
    module._LIMITS['response'] = 13
    assert not guard.reusable()
    module.dependency = ModuleType('data_sheets_schema.unreviewed_validator')
    with pytest.raises(ValueError, match='outside its closed graph'):
        guard_for(module)


def checked(owner, run):
    run._prefix = owner.begin(run)
    result = capture._checked_observations(run)
    current = run.decision()
    if current is None or current.state != 'failed':
        run._prefix.commit()
    return result


def test_valid_extension_matches_full_replay_and_only_checks_suffix(advance):
    owner = owner_api._PrefixOwner(guard_for(ModuleType('test_validator')))
    first, _ = captured_run(advance, saved=False)
    assert len(checked(owner, first)) == 2
    second, _ = captured_run(advance)
    full, _ = captured_run(advance)
    expected = capture._checked_observations(full)
    suffix = checked(owner, second)
    assert suffix == expected[2:]
    assert second.decision() == full.decision()
    repeated, _ = captured_run(advance)
    assert checked(owner, repeated) == ()
    assert len(owner.observations) == 3
    assert all(key[0] in ('decision', 'request', 'stage', 'packet', 'receipt_request',
                         'receipt_zero', 'response') for key in owner.semantic)


def test_failed_suffix_does_not_commit_checkpoint(advance):
    owner = owner_api._PrefixOwner(guard_for(ModuleType('test_validator')))
    first, _ = captured_run(advance, saved=False)
    first.transcript = capture.observation(first.observations[-1], first.selection,
        first.binding, first.pool)[1]
    checked(owner, first)
    before = (owner.records, owner.observations, dict(owner.semantic), owner.observation_state)
    broken, _ = captured_run(advance, 'state')
    with pytest.raises(ValueError, match='reconstructed resulting state'):
        checked(owner, broken)
    assert before == (owner.records, owner.observations, owner.semantic, owner.observation_state)


def test_rehashed_observation_and_record_replacements_refuse(advance):
    for kind in ('observation', 'record', 'transcript', 'control'):
        owner = owner_api._PrefixOwner(guard_for(ModuleType('test_validator')))
        first, _ = captured_run(advance)
        checked(owner, first)
        changed, _ = captured_run(advance)
        if kind == 'observation':
            old = changed.observations[0]
            changed.observations = (artifact(old.pin.role, old.pin.path, old.raw + b' '),) + changed.observations[1:]
        elif kind == 'record':
            old = changed.history.records[0]
            changed.history = replace(changed.history, records=(
                artifact(old.pin.role, old.pin.path, old.raw + b' '),) + changed.history.records[1:])
        else:
            old = getattr(changed, kind)
            raw = b' ' + old.raw[1:]
            setattr(changed, kind, replace(old, raw=raw, sha256=capture.c.sha(raw)))
        with pytest.raises(ValueError, match='replaced its verified prefix'):
            checked(owner, changed)


def test_binding_change_forces_full_replay_and_keeps_anchors(advance):
    module = ModuleType('test_validator')
    module.typed = ModuleType('data_sheets_schema.typed_audit')
    original = module.typed
    owner = owner_api._PrefixOwner(guard_for(module))
    first, _ = captured_run(advance)
    checked(owner, first)
    module.typed = ModuleType(original.__name__)
    second, _ = captured_run(advance)
    assert len(checked(owner, second)) == 3
    assert not owner.semantic
    module.typed = original
    third, _ = captured_run(advance)
    assert len(checked(owner, third)) == 3
    assert owner.records and owner.observations and owner.streams


def test_completed_stage_delta_skips_only_previously_checked_response(case, monkeypatch):
    updated, transition = respond(case, receipt_answer(case))
    assert transition.disposition == 'checked'
    owner = owner_api._PrefixOwner(guard_for(ModuleType('test_validator')))
    transaction = owner_api._PrefixTransaction(owner, None, True)
    catalogs = stage.nr._ReceiptCatalogContext()
    counts = []
    original = stage._Replay._derive_response
    def counted(self, cursor, inner, raw):
        counts.append(cursor.kind)
        return original(self, cursor, inner, raw)
    monkeypatch.setattr(stage._Replay, '_derive_response', counted)
    wait = stage._prepare_next(*updated, catalogs, _prefix=transaction)
    assert counts == ['receipt']
    extended = add_core((*updated[:3], publish(updated[3], wait)))
    resumed = stage._prepare_next(*extended, catalogs, _prefix=transaction)
    assert counts == ['receipt']
    complete = stage.prepare_next(*extended)
    assert counts == ['receipt', 'receipt']
    assert resumed == complete


def test_checkpoint_storage_does_not_retain_journal_prefix_copies(case):
    owner = owner_api._PrefixOwner(guard_for(ModuleType('test_validator')))
    transaction = owner_api._PrefixTransaction(owner, None, True)
    stage._prepare_next(*case, stage.nr._ReceiptCatalogContext(), _prefix=transaction)
    seen = set()
    def walk(value):
        if id(value) in seen:
            return
        seen.add(id(value))
        if isinstance(value, (stage.c.CapturedArtifact, stage.c.ProposedArtifact)):
            assert value.pin.role != 'journal'
        if is_dataclass(value) and not isinstance(value, type):
            for field in fields(value):
                walk(getattr(value, field.name))
        elif isinstance(value, dict):
            for key, item in value.items():
                walk(key)
                walk(item)
        elif isinstance(value, (tuple, list, set, frozenset)):
            for item in value:
                walk(item)
    walk(transaction.pending)


def test_older_transaction_cannot_rewind_newer_checkpoint(advance):
    owner = owner_api._PrefixOwner(guard_for(ModuleType('test_validator')))
    older, _ = captured_run(advance, saved=False)
    older._prefix = owner.begin(older)
    capture._checked_observations(older)
    newer, _ = captured_run(advance)
    checked(owner, newer)
    anchors = owner.records, owner.observations, owner.streams
    with pytest.raises(ValueError, match='overlapping callback'):
        older._prefix.commit()
    assert anchors == (owner.records, owner.observations, owner.streams)


def test_semantically_valid_rehashed_old_history_still_refuses(advance, monkeypatch):
    owner = owner_api._PrefixOwner(guard_for(ModuleType('test_validator')))
    original, _ = captured_run(advance)
    checked(owner, original)
    events = saved_fixture.events
    def alternate_transport():
        calls, control, extra = events()
        calls[0]['uninterpreted_transport_marker'] = 'coherently replaced old bytes'
        return calls, control, extra
    monkeypatch.setattr(saved_fixture, 'events', alternate_transport)
    replacement, _ = captured_run(advance)
    assert len(capture._checked_observations(replacement)) == 3
    with pytest.raises(ValueError, match='replaced its verified prefix'):
        checked(owner, replacement)


def test_all_resumed_stage_decisions_equal_independent_full_replay(case, monkeypatch):
    owner = owner_api._PrefixOwner(guard_for(ModuleType('test_validator')))
    transaction = owner_api._PrefixTransaction(owner, None, True)
    catalogs = stage.nr._ReceiptCatalogContext()
    full = stage.prepare_next
    compared = []
    def compare(*args):
        expected = full(*args)
        actual = stage._prepare_next(*args, catalogs, _prefix=transaction)
        assert actual == expected
        compared.append(actual.state)
        return actual
    monkeypatch.setattr(stage, 'prepare_next', compare)
    completed, completion = full_roundtrip(case)
    assert full(*completed).completion == completion
    assert {'await_core', 'request_ready', 'awaiting_response', 'assembly_complete'} <= set(compared)
    assert all(value[0].state != 'assembly_complete' for key, value in transaction.pending.items()
               if key[0] == 'decision')


def test_retained_transaction_cannot_reuse_after_owner_closes(advance):
    owner = owner_api._PrefixOwner(guard_for(ModuleType('test_validator')))
    run, _ = captured_run(advance)
    checked(owner, run)
    assert owner.semantic
    owner.close()
    assert not owner.semantic and owner.observation_state is None
    with pytest.raises(ValueError, match='admission has closed'):
        run._prefix.get(('decision', run.history.journal.pin))
    with pytest.raises(ValueError, match='admission has closed'):
        run._prefix.commit()

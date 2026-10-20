"""Exact-byte schema reuse in actual private reader bindings, not admission.

These use the existing synthetic E/owner and clock backend with actual selected
loader, captured schemas, reader scopes and local stream files. They establish
neither full-schema timing nor an independently launched helper's acceptance.
"""
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import replace

import pytest

from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_selection as selections
from tests.test_native_owner_live_reader import (
    declaration, entered_case, fixed_clock, read_case, reader_case,
    selected_controls,
)


def fresh_views(monkeypatch):
    monkeypatch.setattr(selections, '_SCHEMA_DERIVATIONS', selections._SchemaDerivationCache())
    actual = selections.captured_view
    seen = []

    @contextmanager
    def observed(snapshot):
        seen.append(str(snapshot.sources[0][1]))
        with actual(snapshot) as view:
            yield view

    monkeypatch.setattr(selections, 'captured_view', observed)
    return seen


def test_repeated_reader_bind_reuses_schema_views_without_reusing_context(reader_case, monkeypatch):
    case = reader_case
    views = fresh_views(monkeypatch)
    expected = [case['selection'].document()['inputs'][kind + '_schema']['root']
                for kind in ('full', 'core')]
    deadline = case['budget'].deadline_ns
    raw = case['paths']['transcript'].read_bytes()
    contexts = []
    for _ in range(2):
        with entered_case(case) as context:
            contexts.append(context)
            assert context.budget is case['budget']
            assert context.budget.deadline_ns == deadline
            assert read_case(case, context).captured.raw == raw
        assert views == expected
        with pytest.raises(ValueError, match='inactive'):
            context.require_current()
    assert contexts[0] is not contexts[1]
    assert not any(context._live for context in contexts)


def test_warm_reader_key_keeps_carrier_authority_clock_and_stop_checks(reader_case, monkeypatch):
    case = reader_case
    views = fresh_views(monkeypatch)
    with entered_case(case):
        pass
    assert len(views) == 2

    # Same registered raw bytes, but a contradictory supplied projection.
    projection = deepcopy(case['selection'])
    bounds = projection.bounds()
    bounds['max_submissions'] -= 1
    object.__setattr__(projection, 'bounds_json', c.canonical(bounds))
    with pytest.raises(ValueError, match='selection differs from captured reconstruction'):
        with entered_case(case, selection=projection):
            pytest.fail('warm metadata admitted a contradictory selection projection')

    # A self-consistent new carrier pin does not change the registered authority.
    bundle = next(a for a in case['selection'].authority if a.pin.role == 'bundle')
    raw = bundle.raw + b'\n'
    changed = c.CapturedArtifact(c.ArtifactPin('bundle', bundle.pin.path, len(raw), c.sha(raw)), raw)
    authority = tuple(changed if a is bundle else a for a in case['selection'].authority)
    with pytest.raises(ValueError, match='captured authority differs from selected identity: bundle'):
        with entered_case(case, selection=replace(case['selection'], authority=authority)):
            pytest.fail('warm metadata admitted unregistered non-schema bytes')

    # Captured domain disagreement must refuse before interpreting the deadline.
    owner = deepcopy(case['owner'])
    owner['clock_domain']['boot_uuid'] = 'aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee'
    with pytest.raises(ValueError, match='clock domain differs from its owner'):
        with entered_case(case, owner_raw=c.canonical(owner)):
            pytest.fail('warm metadata admitted a different owner clock domain')

    case['stop'].set()
    try:
        with pytest.raises(ValueError, match='coordination stopped'):
            with entered_case(case):
                pytest.fail('warm metadata ignored the current stop event')
    finally:
        case['stop'].clear()
    case['stop_path'].write_bytes(b'{}')
    try:
        with pytest.raises(ValueError, match='stop marker forbids live reads'):
            with entered_case(case):
                pytest.fail('warm metadata ignored the actual owner stop marker')
    finally:
        case['stop_path'].unlink()

    with entered_case(case) as context:
        assert read_case(case, context).captured.raw == case['paths']['transcript'].read_bytes()
    assert len(views) == 2

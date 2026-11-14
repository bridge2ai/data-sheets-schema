#!/usr/bin/env python3
"""Repair G07-F4 assertions, 2026-11-12.
Input/output: test_native_subscription_capture.py. Preserve production code and
other mutations' recheck requirements for the Claude lead helper-2 assignment.
"""
from pathlib import Path
path = Path(__file__).resolve().parents[2] / 'tests/test_native_subscription_capture.py'
text = path.read_text()
old = "    assert trace == ['verified', 'inner-claims']"
assert text.count(old) == 1
text = text.replace(old, "    assert trace == ['verified', 'outer-claims']")
old = """    with pytest.raises(ValueError):
        capture.read_capture_for_event(
            arguments['directory'], **read_arguments(arguments), require_current=True,
            **{key: event[key] for key in ('event_json', 'event_sha256', 'captured_at')})
    assert trace[:2] == ['verified', 'mutated']
    assert 'recheck_verified' in trace
    assert trace.count('verified') == 1"""
new = """    with pytest.raises(ValueError) as refused:
        capture.read_capture_for_event(
            arguments['directory'], **read_arguments(arguments), require_current=True,
            **{key: event[key] for key in ('event_json', 'event_sha256', 'captured_at')})
    if mutation == 'review_document':
        assert str(refused.value) == 'review document differs from its pinned bytes'
        assert trace == ['verified', 'mutated']
    else:
        assert trace[:2] == ['verified', 'mutated']
        assert 'recheck_verified' in trace
        assert trace.count('verified') == 1"""
assert text.count(old) == 1
path.write_text(text.replace(old, new))

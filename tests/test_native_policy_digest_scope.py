"""Exact policy-byte digest reuse; all runtime evidence here is fabricated.

No timing assertions, provider requests or native-binary execution. The saved
trace oracle compares all seven replays with memoization explicitly disabled.
"""
from collections import Counter
from contextlib import nullcontext
from copy import deepcopy
from dataclasses import replace

import pytest

from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_effects as effects
from data_sheets_schema import native_shared_permissions as permissions
from data_sheets_schema import native_shared_policy as policy
from tests.test_native_shared_policy import selected, bound, native_spec, declaration
from tests.test_native_shared_permissions import fixture, get, prohibit_real_transports


def routed(commands, stage):
    return policy.stage_overlay_governs(replace(stage), tool_name='Bash',
        tool_input={'command': commands['native_shared_helpers']['advance']},
        policy=commands)


def outcome(function, *args):
    try:
        return 'returned', function(*args)
    except Exception as error:
        return 'raised', type(error), error.args


def test_one_current_hash_keeps_every_view_and_helper_check(selected, monkeypatch):
    commands, stage = selected
    raw = c.canonical(commands)
    actual_sha, actual_helper = c.sha, policy.helper_commands
    actual_effect = effects.governs_stage_effect
    counts = Counter()

    def sha(value):
        if value == raw:
            counts['policy_sha'] += 1
        return actual_sha(value)

    def helper(value):
        counts['helper'] += 1
        return actual_helper(value)

    def effect(*args, **kwargs):
        counts['effect'] += 1
        return actual_effect(*args, **kwargs)

    monkeypatch.setattr(c, 'sha', sha)
    monkeypatch.setattr(policy, 'helper_commands', helper)
    monkeypatch.setattr(effects, 'governs_stage_effect', effect)
    assert policy._TRACE_POLICY_DIGEST.get() is None
    with policy._policy_digest_scope():
        for _ in range(3):
            assert routed(commands, stage) is True
        assert counts == {'policy_sha': 1, 'helper': 3, 'effect': 3}
    assert policy._TRACE_POLICY_DIGEST.get() is None
    assert routed(commands, stage) is True
    assert routed(commands, stage) is True
    assert counts['policy_sha'] == 3
    with policy._policy_digest_scope():
        assert routed(commands, stage) is True
    assert counts['policy_sha'] == 4


def test_policy_mutation_refuses_repeatedly_and_restoration_stays_exact(selected):
    commands, stage = selected
    original = deepcopy(commands)
    with policy._policy_digest_scope():
        assert routed(commands, stage) is True
        commands['readonly_lookups']['inputs'].append('/changed/authority')
        for _ in range(2):
            result = outcome(routed, commands, stage)
            assert result[0:2] == ('raised', ValueError)
            assert result[2] == ('stage routing policy differs from the selected view',)
        commands.clear()
        commands.update(deepcopy(original))
        assert routed(commands, stage) is True
        commands['readonly_lookups']['inputs'].append('/another/authority')
        matching = replace(stage, static_policy_sha256=c.sha(c.canonical(commands)))
        assert routed(commands, matching) is True
        assert outcome(routed, commands, stage)[0:2] == ('raised', ValueError)
    assert policy._TRACE_POLICY_DIGEST.get() is None


def test_scope_restores_nested_state_and_cleans_up_after_refusal(selected, monkeypatch):
    commands, stage = selected
    raw = c.canonical(commands)
    actual_sha = c.sha
    calls = []

    def sha(value):
        if value == raw:
            calls.append(value)
        return actual_sha(value)

    monkeypatch.setattr(c, 'sha', sha)
    with policy._policy_digest_scope():
        assert routed(commands, stage) is True
        outer = policy._TRACE_POLICY_DIGEST.get()
        with pytest.raises(ValueError, match='explicit refusal'):
            with policy._policy_digest_scope():
                assert policy._TRACE_POLICY_DIGEST.get() == ()
                assert routed(commands, stage) is True
                raise ValueError('explicit refusal')
        assert policy._TRACE_POLICY_DIGEST.get() is outer
        assert routed(commands, stage) is True
    assert len(calls) == 2
    assert policy._TRACE_POLICY_DIGEST.get() is None


def test_scope_keeps_invalid_view_then_helper_then_encoding_error_order(selected, monkeypatch):
    commands, stage = selected
    broken_commands = deepcopy(commands)
    broken_commands['native_shared_helpers']['advance'] = 'not a canonical helper'
    invalid_view = replace(stage)
    object.__setattr__(invalid_view, 'protocol', 'invalid-protocol')
    nonfinite = deepcopy(commands)
    nonfinite['unregistered_nonfinite'] = float('nan')
    cases = [(broken_commands, invalid_view), (broken_commands, stage), (nonfinite, stage)]

    def exact_route(arguments):
        current, view = arguments
        return policy.stage_overlay_governs(view, tool_name='Bash',
            tool_input={'command': stage.stage_command}, policy=current)

    expected = [outcome(exact_route, row) for row in cases]
    assert all(row[0:2] == ('raised', ValueError) for row in expected)
    with policy._policy_digest_scope():
        assert routed(commands, stage) is True
        for _ in range(2):
            assert [outcome(exact_route, row) for row in cases] == expected
    assert policy._TRACE_POLICY_DIGEST.get() is None


def test_changed_hash_implementation_cannot_use_a_previous_digest(selected, monkeypatch):
    commands, stage = selected
    with policy._policy_digest_scope():
        assert routed(commands, stage) is True
        calls = []

        def changed(raw):
            calls.append(raw)
            return 'f' * 64

        monkeypatch.setattr(c, 'sha', changed)
        assert outcome(routed, commands, stage)[0:2] == ('raised', ValueError)
        assert calls == [c.canonical(commands)]
    assert policy._TRACE_POLICY_DIGEST.get() is None


def test_changed_hash_constructor_cannot_use_a_previous_digest(selected, monkeypatch):
    commands, stage = selected
    unchanged_implementation = c.sha
    with policy._policy_digest_scope():
        assert routed(commands, stage) is True
        calls = []

        class ChangedDigest:
            def hexdigest(self):
                return 'f' * 64

        def changed(raw):
            calls.append(raw)
            return ChangedDigest()

        with monkeypatch.context() as patch:
            patch.setattr(c.hashlib, 'sha256', changed)
            assert c.sha is unchanged_implementation
            assert outcome(routed, commands, stage)[0:2] == ('raised', ValueError)
            assert calls == [c.canonical(commands)]
        assert routed(commands, stage) is True
    assert policy._TRACE_POLICY_DIGEST.get() is None


def test_oversized_policy_digest_is_not_retained(selected, monkeypatch):
    commands, stage = selected
    raw = c.canonical(commands)
    actual_sha = c.sha
    calls = []

    def sha(value):
        if value == raw:
            calls.append(value)
        return actual_sha(value)

    monkeypatch.setattr(c, 'sha', sha)
    monkeypatch.setattr(policy, '_TRACE_POLICY_DIGEST_BYTES', 1)
    with policy._policy_digest_scope():
        assert routed(commands, stage) is True
        assert routed(commands, stage) is True
        assert policy._TRACE_POLICY_DIGEST.get() == ()
    assert len(calls) == 2


def test_all_seven_traces_keep_exact_outputs_and_classifier_validation_counts(fixture, monkeypatch):
    policy_bytes = {c.canonical(get(fixture['manifest'], f'traces/{name}/projection.json')['probe_policy'])
                    for name in permissions.TRACES}
    assert len(policy_bytes) == 7
    actual_sha = c.sha
    actual_construct = c.NativeEffectView.__init__
    actual_validate = c._validate_carrier
    actual_governs = effects.governs_stage_effect
    actual_effect = effects.classify_effect
    actual_bash = policy.classify_bash
    actual_route = policy.stage_overlay_governs
    current_scope = policy._policy_digest_scope

    def run(scope):
        counts = Counter()

        def sha(raw):
            if raw in policy_bytes:
                counts['policy_sha'] += 1
            return actual_sha(raw)

        def construct(view, *args, **kwargs):
            counts['construct'] += 1
            return actual_construct(view, *args, **kwargs)

        def validate(view):
            if type(view) is c.NativeEffectView:
                counts['validate'] += 1
            return actual_validate(view)

        def governs(*args, **kwargs):
            counts['governs'] += 1
            return actual_governs(*args, **kwargs)

        def effect(*args, **kwargs):
            counts['effect'] += 1
            return actual_effect(*args, **kwargs)

        def bash(*args, **kwargs):
            counts['bash'] += 1
            return actual_bash(*args, **kwargs)

        def route(*args, **kwargs):
            counts['route'] += 1
            return actual_route(*args, **kwargs)

        with monkeypatch.context() as patch:
            patch.setattr(policy, '_policy_digest_scope', scope)
            patch.setattr(c, 'sha', sha)
            patch.setattr(c.NativeEffectView, '__init__', construct)
            patch.setattr(c, '_validate_carrier', validate)
            patch.setattr(effects, 'governs_stage_effect', governs)
            patch.setattr(effects, 'classify_effect', effect)
            patch.setattr(policy, 'classify_bash', bash)
            patch.setattr(policy, 'stage_overlay_governs', route)
            result = permissions.verify_saved_probe(
                c.canonical(fixture['manifest']), expected=fixture['expected'])
        assert policy._TRACE_POLICY_DIGEST.get() is None
        return c.canonical(result), counts

    baseline, before = run(nullcontext)
    actual, after = run(current_scope)
    assert actual == baseline
    assert before.pop('policy_sha') == 25
    assert after.pop('policy_sha') == 7
    assert after == before
    assert after['route'] == 25
    assert after['construct'] == 125
    assert after['validate'] == 251

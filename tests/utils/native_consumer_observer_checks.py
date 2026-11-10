"""WP1 consumer-observer equivalence checks, 2026-11-10.

Inputs: genuine source-loaded consumers, synthetic Python functions and the
active passive metrics Recorder. Output: assertion-backed canary metadata.
Only test observation machinery is varied; no production callable is replaced.
"""
import sys
import threading

import pytest

from tests.utils.native_shared_consumer_scope import loaded_consumer, observe_consumer_calls


class _InjectedRefusal(RuntimeError):
    pass


class _PriorHookRefusal(RuntimeError):
    pass


def _compiled_entry():
    namespace = {}
    source = ('def consumer_entry(value, effects, *, flag=False):\n'
              '    unassigned = "body-only"\n'
              '    effects.append(value)\n'
              '    return value, flag\n')
    # The basename contract must also work outside the metrics repository root.
    exec(compile(source, '/u3wp1-outside-tree/native_observer_canary.py', 'exec'), namespace)
    return namespace['consumer_entry']


def _compiled_generator():
    namespace = {}
    source = ('def consumer_generator(value, effects):\n'
              '    effects.append("start")\n'
              '    try:\n'
              '        incoming = yield value\n'
              '        effects.append(incoming)\n'
              '        yield incoming\n'
              '    except LookupError:\n'
              '        effects.append("caught")\n'
              '        yield "caught"\n'
              '    finally:\n'
              '        effects.append("closed")\n')
    exec(compile(source, '/u3wp1-outside-tree/native_observer_canary.py', 'exec'), namespace)
    return namespace['consumer_generator']


def _slots(monitor):
    return {tool: (monitor.get_tool(tool), monitor.get_events(tool)) for tool in range(6)}


def _assert_call(calls, key, value, effects, flag):
    assert len(calls) == 1
    assert calls[0][0] == key
    assert set(calls[0][1]) == {'value', 'effects', 'flag'}
    assert calls[0][1]['value'] == value
    assert calls[0][1]['effects'] is effects
    assert calls[0][1]['flag'] is flag


def _basic_equivalence(arm, entry, key, targets):
    before = sys.getprofile()
    effects = []
    with observe_consumer_calls(targets, arm=arm) as calls:
        assert entry(7, effects, flag=True) == (7, True)
    _assert_call(calls, key, 7, effects, True)
    assert effects == [7]
    assert sys.getprofile() is before

    # Reuse an already executed code object after a scope where it was not a
    # target. A DISABLE result must never hide the later matched invocation.
    with observe_consumer_calls({('elsewhere', 'different'): ()}, arm=arm) as calls:
        entry(8, [], flag=False)
    assert calls == []
    with observe_consumer_calls(targets, arm=arm) as calls:
        assert entry(9, [], flag=False) == (9, False)
    assert len(calls) == 1 and calls[0][1]['value'] == 9

    injected = _InjectedRefusal('WP1 injected entry refusal')
    effects = []
    with pytest.raises(_InjectedRefusal) as caught:
        with observe_consumer_calls(targets, refuse=(key, injected), arm=arm) as calls:
            entry(10, effects, flag=True)
    assert caught.value is injected
    _assert_call(calls, key, 10, effects, True)
    assert effects == []
    assert sys.getprofile() is before

    # CPython clears a raising legacy profile callback, even if the caller
    # catches the refusal inside the still-open observation scope.
    effects = []
    with observe_consumer_calls(targets, refuse=(key, injected), arm=arm) as calls:
        with pytest.raises(_InjectedRefusal) as caught:
            entry(23, effects, flag=False)
        assert caught.value is injected
        assert entry(24, effects, flag=True) == (24, True)
    assert len(calls) == 1 and calls[0][1]['value'] == 23
    assert effects == [24] and sys.getprofile() is before

    effects = []
    with pytest.raises(AssertionError, match='forbidden production operation'):
        with observe_consumer_calls(targets, refuse=(key, injected), forbid=True, arm=arm) as calls:
            entry(11, effects, flag=False)
    _assert_call(calls, key, 11, effects, False)
    assert effects == []
    assert sys.getprofile() is before

    # The legacy profile observer is scoped to the installing thread.
    thread_errors = []
    def other_thread():
        try:
            entry(12, [], flag=False)
        except BaseException as error:
            thread_errors.append(error)
    with observe_consumer_calls(targets, arm=arm) as calls:
        thread = threading.Thread(target=other_thread, name='wp1-observer-thread-canary')
        thread.start()
        thread.join(timeout=2)
        assert not thread.is_alive(), 'consumer observer thread canary did not finish'
        entry(13, [], flag=True)
    assert thread_errors == []
    assert len(calls) == 1 and calls[0][1]['value'] == 13
    assert sys.getprofile() is before

    def body_hook(frame, event, argument):
        return None
    with observe_consumer_calls(targets, arm=arm):
        sys.setprofile(body_hook)
        assert sys.getprofile() is body_hook
    assert sys.getprofile() is before


def _prior_hook_equivalence(arm, entry, key, targets):
    before = sys.getprofile()
    state = {'calls': [], 'seen': [], 'raise': False}
    refused = _PriorHookRefusal('WP1 prior hook refusal')
    def prior(frame, event, argument):
        if event == 'call' and frame.f_code is entry.__code__:
            state['seen'].append(len(state['calls']))
            assert state['calls'] == [], 'prior profile hook did not run before observation'
            if state['raise']:
                raise refused
    sys.setprofile(prior)
    try:
        effects = []
        with observe_consumer_calls(targets, arm=arm) as calls:
            state['calls'] = calls
            assert entry(14, effects, flag=True) == (14, True)
        assert state['seen'] == [0]
        _assert_call(calls, key, 14, effects, True)
        assert sys.getprofile() is prior

        state.update(calls=[], seen=[])
        injected = _InjectedRefusal('WP1 refusal after prior hook')
        effects = []
        with pytest.raises(_InjectedRefusal) as caught:
            with observe_consumer_calls(targets, refuse=(key, injected), arm=arm) as calls:
                state['calls'] = calls
                entry(15, effects, flag=False)
        assert caught.value is injected
        assert state['seen'] == [0]
        _assert_call(calls, key, 15, effects, False)
        assert effects == [] and sys.getprofile() is prior

        state.update(calls=[], seen=[], **{'raise': True})
        effects = []
        with pytest.raises(_PriorHookRefusal) as caught:
            with observe_consumer_calls(targets, forbid=True, arm=arm) as calls:
                state['calls'] = calls
                entry(16, effects, flag=False)
        assert caught.value is refused
        assert state['seen'] == [0] and calls == [] and effects == []
        assert sys.getprofile() is prior
    finally:
        sys.setprofile(before)


def _loaded_equivalence():
    from data_sheets_schema import native_execution_authority_v2 as authority
    dependencies = authority.dependency_identity()
    key = ('native_shared_permissions', '_encoded')
    codes = []
    for _ in range(2):
        with loaded_consumer('native_shared_permissions', dependencies) as consumer:
            code = consumer._encoded.__code__
            assert all(code is not prior for prior in codes)
            codes.append(code)
            value = {'wp1': ['genuine source loader', 17]}
            expected = consumer._encoded(value)
            for arm in ('legacy', 'monitoring'):
                with observe_consumer_calls({key: ('value', 'absent')}, arm=arm) as calls:
                    assert consumer._encoded(value) == expected
                assert calls == [(key, {'value': value})]
                refusal = _InjectedRefusal('WP1 loaded consumer refusal')
                with pytest.raises(_InjectedRefusal) as caught:
                    with observe_consumer_calls({key: ('value',)}, refuse=(key, refusal), arm=arm) as calls:
                        consumer._encoded(value)
                assert caught.value is refusal and calls == [(key, {'value': value})]
                with pytest.raises(AssertionError, match='forbidden production operation'):
                    with observe_consumer_calls({key: ('value',)}, forbid=True, arm=arm) as calls:
                        consumer._encoded(value)
                assert calls == [(key, {'value': value})]
    return [{'file': code.co_filename, 'name': code.co_name, 'code_object_id': id(code)}
            for code in codes]


def _generator_equivalence():
    function = _compiled_generator()
    key = ('native_observer_canary', 'consumer_generator')
    observed = {}
    for arm in ('legacy', 'monitoring'):
        effects = []
        generator = function(25, effects)
        try:
            with observe_consumer_calls({key: ('value', 'incoming')}, arm=arm) as calls:
                assert next(generator) == 25
                assert generator.send(26) == 26
                assert generator.throw(LookupError('WP1 generator throw')) == 'caught'
                generator.close()
            assert effects == ['start', 26, 'caught', 'closed']
            assert len(calls) == 4
            observed[arm] = calls
        finally:
            generator.close()
    assert observed['legacy'] == observed['monitoring']


def _prior_hook_tool_management(entry, targets):
    monitor = sys.monitoring
    before = sys.getprofile()
    initial_slots = _slots(monitor)
    watched = (monitor.use_tool_id, monitor.get_tool)
    seen = []
    def prior(frame, event, argument):
        if event == 'c_return' and any(argument is function for function in watched):
            seen.append(argument.__name__)
            raise _PriorHookRefusal('profile hook interrupted monitoring tool management')
    sys.setprofile(prior)
    try:
        with observe_consumer_calls(targets, arm='monitoring') as calls:
            entry(27, [], flag=False)
        assert len(calls) == 1 and sys.getprofile() is prior
        assert seen == []
    finally:
        sys.setprofile(before)
    assert _slots(monitor) == initial_slots


def _monitoring_lifetime(monkeypatch, recorder, entry, targets):
    monitor = sys.monitoring
    before = _slots(monitor)
    assert before[recorder.tool][0] == 'u3k-boundaries'
    available = [tool for tool in (5, 4, 3) if monitor.get_tool(tool) is None]
    assert available, 'no free monitoring tool ID for the experimental arm'
    for sole_free in available:
        held = []
        try:
            # Force each available supported slot in turn. Existing tool owners,
            # including the active Recorder, retain names and event masks.
            for tool in available:
                if tool != sole_free:
                    monitor.use_tool_id(tool, 'wp1-occupied-canary-' + str(tool))
                    held.append(tool)
            occupied = _slots(monitor)
            with observe_consumer_calls(targets, arm='monitoring') as calls:
                assert monitor.get_tool(sole_free) is not None
                assert all(_slots(monitor)[tool] == occupied[tool]
                           for tool in occupied if tool != sole_free)
                entry(18, [], flag=False)
            assert len(calls) == 1 and _slots(monitor) == occupied
            monitor.use_tool_id(sole_free, 'wp1-all-occupied-canary')
            held.append(sole_free)
            all_occupied = _slots(monitor)
            with pytest.raises(RuntimeError):
                with observe_consumer_calls(targets, arm='monitoring'):
                    pytest.fail('observer entered with all supported tool IDs occupied')
            assert _slots(monitor) == all_occupied
        finally:
            for tool in reversed(held):
                monitor.free_tool_id(tool)
        assert _slots(monitor) == before

    register = monitor.register_callback
    set_events = monitor.set_events
    for failure_at in (1, 2, 3, 'activation'):
        initialized, activated = [], []
        failed = _InjectedRefusal('WP1 observer initialization failure: ' + str(failure_at))
        def fail_registration(tool, event, callback):
            if tool != recorder.tool and callback is not None:
                initialized.append((tool, event))
                if len(initialized) == failure_at:
                    raise failed
            return register(tool, event, callback)
        def fail_activation(tool, events):
            if tool != recorder.tool and events != 0:
                activated.append((tool, events))
                if failure_at == 'activation':
                    raise failed
            return set_events(tool, events)
        with monkeypatch.context() as patch:
            patch.setattr(monitor, 'register_callback', fail_registration)
            patch.setattr(monitor, 'set_events', fail_activation)
            with pytest.raises(_InjectedRefusal) as caught:
                with observe_consumer_calls(targets, arm='monitoring'):
                    pytest.fail('observer entered after failed initialization')
            assert caught.value is failed
            assert len(initialized) == (3 if failure_at == 'activation' else failure_at)
            assert len(activated) == (1 if failure_at == 'activation' else 0)
        assert _slots(monitor) == before
        with observe_consumer_calls(targets, arm='monitoring') as calls:
            entry(28, [], flag=False)
        assert len(calls) == 1 and calls[0][1]['value'] == 28
        assert _slots(monitor) == before

    captured = []
    def remember_callback(tool, event, callback):
        if tool != recorder.tool and event == monitor.events.PY_START and callback is not None:
            captured.append(callback)
        return register(tool, event, callback)
    with monkeypatch.context() as patch:
        patch.setattr(monitor, 'register_callback', remember_callback)
        with observe_consumer_calls(targets, arm='monitoring') as calls:
            assert len(captured) == 1
            with pytest.raises(RuntimeError, match='consumer monitoring frame identity mismatch'):
                captured[0](entry.__code__, 0)
            assert calls == []
    assert _slots(monitor) == before
    with observe_consumer_calls(targets, arm='monitoring') as calls:
        entry(19, [], flag=True)
    assert len(calls) == 1 and _slots(monitor) == before


def check_consumer_observers(monkeypatch, recorder):
    """Assert both observer contracts without a native registration or launch."""
    assert recorder.mode == 'control'
    assert sys.getprofile() is None, 'WP1 equivalence requires no inherited profile hook'
    assert hasattr(sys, 'monitoring'), 'WP1 requires a sys.monitoring interpreter'
    initial_slots = _slots(sys.monitoring)
    entry = _compiled_entry()
    key = ('native_observer_canary', 'consumer_entry')
    targets = {key: ('value', 'effects', 'flag', 'unassigned')}
    with pytest.raises(ValueError, match='consumer observer arm must be legacy or monitoring'):
        with observe_consumer_calls(targets, arm='invalid'):
            pytest.fail('unknown consumer observer arm was admitted')
    assert sys.getprofile() is None and _slots(sys.monitoring) == initial_slots
    for arm in ('legacy', 'monitoring'):
        _basic_equivalence(arm, entry, key, targets)
        _prior_hook_equivalence(arm, entry, key, targets)
        second = _compiled_entry()
        assert second.__code__ is not entry.__code__
        with observe_consumer_calls(targets, arm=arm) as calls:
            entry(20, [], flag=False)
            second(21, [], flag=True)
        assert [row[1]['value'] for row in calls] == [20, 21]
        assert _slots(sys.monitoring) == initial_slots
    # Omitting the selector continues to install the historical profile hook.
    with observe_consumer_calls(targets) as calls:
        assert sys.getprofile() is not None
        entry(22, [], flag=True)
    assert len(calls) == 1 and sys.getprofile() is None
    loaded = _loaded_equivalence()
    _generator_equivalence()
    _prior_hook_tool_management(entry, targets)
    _monitoring_lifetime(monkeypatch, recorder, entry, targets)
    assert sys.getprofile() is None and _slots(sys.monitoring) == initial_slots
    return {'arms': ['legacy', 'monitoring'], 'loaded_consumers': loaded,
            'prior_hook_compatibility_checked': True, 'current_thread_scope_checked': True,
            'dynamic_reload_checked': True, 'formerly_nontarget_checked': True,
            'generator_resume_throw_checked': True, 'caught_refusal_disables_checked': True,
            'body_hook_restoration_checked': True, 'prior_hook_tool_management_checked': True,
            'invalid_arm_refused': True, 'initialization_failure_stages_checked': [1, 2, 3, 'activation'],
            'tool_ownership_and_cleanup_checked': True, 'frame_identity_checked': True,
            'scope': 'Observer equivalence only; no native preparation, launch or acceptance.'}

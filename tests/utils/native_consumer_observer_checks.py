"""WP1 scoped consumer checks and a separate limitation witness, 2026-11-10.

Inputs: genuine source-loaded consumers, synthetic Python functions and the
active passive metrics Recorder. Output: assertion-backed canary metadata.
Only test observation machinery is varied; no production callable is replaced.
WP1-L1's profile-mutation divergence is recorded separately from passing cases.
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


def check_profile_mutation_limitation(recorder):
    """WP1-L1: witness divergence; this is not an equivalence acceptance test.

    Each scope starts with no profile hook. The body clears or replaces the
    profile hook and then calls the same target, including refusal variants.
    No production observer behavior is changed to make the arms agree.
    """
    assert recorder.mode == 'control'
    assert sys.getprofile() is None, 'WP1-L1 witness requires no prior profile hook'
    assert hasattr(sys, 'monitoring'), 'WP1-L1 requires a sys.monitoring interpreter'
    initial_slots = _slots(sys.monitoring)
    entry = _compiled_entry()
    key = ('native_observer_canary', 'consumer_entry')
    cases = []
    for mutation in ('clear', 'replace'):
        for mode in ('observe', 'forbid', 'refuse'):
            paired = {}
            for arm in ('legacy', 'monitoring'):
                assert sys.getprofile() is None
                effects, replacement_calls = [], []
                def replacement(frame, event, argument):
                    if event == 'call' and frame.f_code is entry.__code__:
                        replacement_calls.append(event)
                injected = _InjectedRefusal('WP1-L1 refusal after profile-hook mutation')
                options = ({'forbid': True} if mode == 'forbid' else
                           {'refuse': (key, injected)} if mode == 'refuse' else {})
                error = None
                returned = None
                with observe_consumer_calls({key: ('value',)}, arm=arm, **options) as calls:
                    changed_hook = None if mutation == 'clear' else replacement
                    sys.setprofile(changed_hook)
                    assert sys.getprofile() is changed_hook
                    try:
                        returned = entry(29, effects, flag=True)
                    except (AssertionError, _InjectedRefusal) as caught:
                        error = caught
                assert sys.getprofile() is None
                assert _slots(sys.monitoring) == initial_slots
                if arm == 'legacy':
                    assert calls == [] and error is None
                    assert returned == (29, True) and effects == [29]
                else:
                    assert calls == [(key, {'value': 29})]
                    if mode == 'observe':
                        assert error is None and returned == (29, True) and effects == [29]
                    elif mode == 'forbid':
                        assert type(error) is AssertionError
                        assert str(error) == 'forbidden production operation: ' + '.'.join(key)
                        assert returned is None and effects == []
                    else:
                        assert error is injected and returned is None and effects == []
                paired[arm] = {
                    'entry_profile_hook': 'none',
                    'mutation': 'sys.setprofile(None)' if mutation == 'clear' else 'sys.setprofile(replacement)',
                    'observed_calls': calls, 'target_body_effects': effects,
                    'returned': list(returned) if returned is not None else None,
                    'outcome': 'returned' if error is None else 'refused',
                    'exception_type': type(error).__name__ if error is not None else None,
                    'exception_message': str(error) if error is not None else None,
                    'replacement_target_call_events': len(replacement_calls),
                    'profile_hook_restored': True, 'monitoring_slots_restored': True}
            assert paired['legacy']['observed_calls'] != paired['monitoring']['observed_calls']
            if mode != 'observe':
                assert paired['legacy']['outcome'] != paired['monitoring']['outcome']
            cases.append({'mutation': mutation, 'mode': mode, 'arms': paired,
                          'equivalent': False})
    assert len(cases) == 6
    return {'finding': 'WP1-L1', 'classification': 'profile_mutation_non_equivalence_witness',
            'general_replacement_equivalence': False, 'cases': cases,
            'proposed_disposition': 'Opt-in diagnostic only while the observed body does not mutate sys.setprofile.',
            'disposition_status': 'pending_lead_review',
            'precondition_enforcement': 'Not implemented; entry and exit hook checks cannot establish no intervening mutation.',
            'scope': 'Explicit short synthetic witness of a limitation; not an observer fix, timing arm, or equivalence gate pass.'}


def check_profile_stability_guards():
    """Synthetic guard checks only; no native fixture, Recorder or source loader."""
    import cProfile
    import _lsprof
    from tests.utils.native_profile_stability import ProfileMutationRefused, profile_stability_scope
    assert sys.getprofile() is None
    initial_slots = _slots(sys.monitoring)
    initial_thread_hook = threading.getprofile()
    entry = _compiled_entry()
    key = ('native_observer_canary', 'consumer_entry')
    targets = {key: ('value',)}
    saved_setprofile = sys.setprofile
    cases = []
    def replacement(frame, event, argument):
        return None
    def completed(state, expected, *, drift=()):
        assert state['kind'] == 'wp1_profile_stability'
        assert state['installation_verified'] is True and state['reserved_profiler_tool'] == 2
        assert state['restored'] is True and state['completed'] is expected
        assert state['drift'] == list(drift)
        assert threading.getprofile() is initial_thread_hook
    for arm in ('legacy', 'monitoring'):
        with observe_consumer_calls(targets, arm=arm) as calls:
            active_hook = sys.getprofile()
            with profile_stability_scope() as state:
                assert sys.monitoring.get_tool(2) is not None
                assert sys.monitoring.get_events(2) == 0
                assert entry(30, [], flag=False) == (30, False)
            completed(state, True)
            assert state['attempts'] == [] and sys.getprofile() is active_hook
        assert calls == [(key, {'value': 30})]
        cases.append({'arm': arm, 'case': 'stable_body', 'state': state})

        for mutation in ('clear', 'replacement', 'saved_alias', 'trace', 'monitor_callback'):
            effects = []
            with observe_consumer_calls(targets, arm=arm) as calls:
                active_hook = sys.getprofile()
                with pytest.raises(ProfileMutationRefused):
                    with profile_stability_scope() as state:
                        if mutation == 'saved_alias':
                            saved_setprofile(None)
                        elif mutation == 'trace':
                            sys.settrace(None)
                        elif mutation == 'monitor_callback':
                            sys.monitoring.register_callback(2, sys.monitoring.events.PY_START, None)
                        else:
                            sys.setprofile(replacement if mutation == 'replacement' else None)
                        entry(31, effects, flag=False)
                assert sys.getprofile() is active_hook
                completed(state, False)
            assert calls == [] and effects == [] and state['attempts']
            cases.append({'arm': arm, 'case': mutation, 'state': state,
                          'target_body_ran': False})

        with observe_consumer_calls(targets, arm=arm):
            active_hook = sys.getprofile()
            with pytest.raises(ProfileMutationRefused):
                with profile_stability_scope() as state:
                    with pytest.raises(ProfileMutationRefused):
                        saved_setprofile(None)
                    assert sys.getprofile() is active_hook
                    continued_after_caught_refusal = True
            assert continued_after_caught_refusal
            completed(state, False)
            assert state['attempts'] and sys.getprofile() is active_hook
        cases.append({'arm': arm, 'case': 'caught_refusal_is_sticky', 'state': state,
                      'body_continued_after_catch': True})

        for name, constructor in (('cProfile', cProfile.Profile), ('_lsprof', _lsprof.Profiler)):
            profiler = constructor()
            with observe_consumer_calls(targets, arm=arm):
                active_hook = sys.getprofile()
                with profile_stability_scope() as state:
                    reserved = _slots(sys.monitoring)
                    with pytest.raises((ValueError, RuntimeError)) as caught:
                        profiler.enable()
                    error = caught.value
                    assert 'profil' in str(error).lower()
                    assert _slots(sys.monitoring) == reserved
                    assert sys.getprofile() is active_hook
                completed(state, True)
                assert state['attempts'] == [] and sys.getprofile() is active_hook
            cases.append({'arm': arm, 'case': name + '_enable_refused', 'state': state,
                          'exception_type': type(error).__name__, 'exception_message': str(error)})
            del profiler

        ready, release = threading.Event(), threading.Event()
        thread_errors = []
        def all_thread_mutation():
            ready.set()
            if not release.wait(timeout=2):
                thread_errors.append(RuntimeError('guard witness release timed out'))
                return
            try:
                threading.setprofile_all_threads(replacement)
            except BaseException as error:
                thread_errors.append(error)
        worker = threading.Thread(target=all_thread_mutation, daemon=True,
                                  name='wp1-all-thread-profile-guard-witness')
        worker.start()
        try:
            assert ready.wait(timeout=2), 'guard witness worker did not start'
            with observe_consumer_calls(targets, arm=arm):
                active_hook = sys.getprofile()
                with pytest.raises(ProfileMutationRefused):
                    with profile_stability_scope() as state:
                        release.set()
                        worker.join(timeout=2)
                        assert not worker.is_alive(), 'guard witness worker did not finish'
                        assert len(thread_errors) == 1
                        assert isinstance(thread_errors[0], ProfileMutationRefused)
                        assert sys.getprofile() is active_hook
                completed(state, False, drift=('future_thread_profile',))
                assert state['attempts'] and sys.getprofile() is active_hook
            cases.append({'arm': arm, 'case': 'other_thread_all_threads_sticky_refusal',
                          'state': state, 'future_thread_default_restored': True,
                          'exception_type': type(thread_errors[0]).__name__,
                          'exception_message': str(thread_errors[0])})
        finally:
            release.set()
            worker.join(timeout=2)
        assert not worker.is_alive()
        assert sys.getprofile() is None and _slots(sys.monitoring) == initial_slots
        assert threading.getprofile() is initial_thread_hook
    return {'scope': 'Synthetic profile-stability guard only; no native execution or timing claim.',
            'cases': cases, 'recorder_instantiated': False, 'source_loader_called': False,
            'profile_hook_restored': True, 'monitoring_slots_restored': True,
            'future_thread_default_restored': True}


def check_consumer_observers(monkeypatch, recorder):
    """Assert selected contracts; WP1-L1 prevents a general-equivalence claim."""
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
            'general_replacement_equivalence': False,
            'known_limitation': 'WP1-L1: profile-hook mutation disables legacy observation but not monitoring.',
            'limitation_witness_node': 'tests/test_native_u3k_profile.py::test_consumer_observer_profile_mutation_limitation_witness',
            'diagnostic_stability_boundary': 'Both diagnostic arms use the common profile_stability_scope; raw observer mutation remains non-equivalent.',
            'precondition_status': 'Guard implemented for the diagnostic route; runtime enforcement validation remains pending.',
            'prior_hook_compatibility_checked': True, 'current_thread_scope_checked': True,
            'dynamic_reload_checked': True, 'formerly_nontarget_checked': True,
            'generator_resume_throw_checked': True, 'caught_refusal_disables_checked': True,
            'body_hook_restoration_checked': True, 'prior_hook_tool_management_checked': True,
            'invalid_arm_refused': True, 'initialization_failure_stages_checked': [1, 2, 3, 'activation'],
            'tool_ownership_and_cleanup_checked': True, 'frame_identity_checked': True,
            'scope': 'Selected observer-contract checks only, not general replacement equivalence; no native preparation, launch or acceptance.'}

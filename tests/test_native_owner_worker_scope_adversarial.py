"""Independent private worker-scope controls; no native/provider acceptance.

Clock acquisition uses the shared invented backend, with real leases, ordinary
Threads, captured selection reconstruction and the actual selected reader.
"""
from contextvars import copy_context
from copy import deepcopy
import sys
import threading
import time

import pytest

from data_sheets_schema import native_clock_domain_v1 as clocks
from data_sheets_schema import native_owner_profile_v1 as profile
from data_sheets_schema import native_stream_coordination_v1 as coordination
from tests.test_native_owner_live_reader import (
    bind_case, declaration, read_case, reader_case,
)
from tests.test_native_owner_runner import fixed_clock, selected_controls
from tests.test_native_owner_worker_scope import (
    install_reader_operation, read_in_worker, worker_case,
)


def in_thread(operation, *, context=None):
    """Propagate assertions/errors instead of leaving pytest thread warnings."""
    returned, errors = [], []

    def work():
        try:
            returned.append(operation() if context is None else context.run(operation))
        except BaseException as error:
            errors.append(error)

    thread = threading.Thread(target=work)
    thread.start()
    thread.join(60)
    assert not thread.is_alive(), 'ordinary worker exceeded its fixture bound'
    if errors:
        raise errors[0]
    assert len(returned) == 1
    return returned[0]


def owner_budget(domain):
    return coordination.ReaderBudget(time.monotonic_ns() + 120_000_000_000,
        (threading.Event(), threading.Event()), clock_domain=domain)


def child_budget(owner, **changes):
    values = {'deadline_ns': owner.deadline_ns - 1,
              'stop_events': owner.stop_events, 'clock_domain': owner.clock_domain()}
    values.update(changes)
    return coordination.ReaderBudget(**values)


@pytest.mark.parametrize('role', ['transcript', 'control'])
def test_fresh_worker_scope_reads_real_capture_and_never_reuses_parent(reader_case, role):
    case = reader_case
    parent = profile._ACTIVE.get()
    expected = case['paths'][role].read_bytes()

    def work():
        assert profile._ACTIVE.get() is None
        budget = child_budget(case['budget'])
        with coordination.reader_budget(budget):
            with profile._worker_scope(parent, case['budget']) as scope:
                assert type(scope) is profile._Scope and scope is not parent
                assert scope._parent is parent
                assert scope._creator is threading.current_thread()
                assert scope._budget is budget
                with bind_case(case, budget=budget) as reader:
                    result = read_case(case, reader, role)
                assert result.captured.raw == expected
        assert profile._ACTIVE.get() is None and not scope.live
        return scope

    scope = in_thread(work)
    assert scope is not parent and profile._ACTIVE.get() is parent
    parent.require()


@pytest.mark.parametrize('binder', ['reader', 'control', 'runner'])
def test_copied_live_parent_context_cannot_bind_from_new_thread(reader_case, binder):
    case = reader_case
    parent = profile._ACTIVE.get()
    copied = copy_context()

    def work():
        assert profile._ACTIVE.get() is parent and parent.live
        with coordination.reader_budget(child_budget(case['budget'])) as budget_scope:
            # This is a fresh legitimate clock scope, not an expired copied one.
            budget_scope.budget.remaining()
            with pytest.raises(ValueError):
                if binder == 'reader':
                    bind_case(case, budget=budget_scope.budget)
                elif binder == 'control':
                    profile.bind_control(case['profile'], case['controls'])
                else:
                    profile.bind_runner(case['profile'], case['controls'])

    in_thread(work, context=copied)
    assert parent.live and profile._ACTIVE.get() is parent
    parent.require()


def test_worker_entry_is_terminal_but_next_invocation_is_fresh(selected_controls, fixed_clock):
    parent, owner = profile._ACTIVE.get(), owner_budget(fixed_clock)

    def work():
        budget = child_budget(owner)
        with coordination.reader_budget(budget):
            entry = profile._worker_scope(parent, owner)
            with entry:
                captured = copy_context()
                entry.require()
            assert not entry.live and profile._ACTIVE.get() is None
            with pytest.raises(ValueError):
                captured.run(entry.require)
            with pytest.raises(ValueError):
                entry.__enter__()
            # A new scope, without a renewed budget, is the next invocation.
            with profile._worker_scope(parent, owner) as next_entry:
                assert next_entry is not entry
                next_entry.require()
            with pytest.raises(ValueError):
                captured.run(entry.require)

    in_thread(work)
    parent.require()


def test_failed_worker_entry_cannot_be_revived_by_installing_budget(selected_controls, fixed_clock):
    parent, owner = profile._ACTIVE.get(), owner_budget(fixed_clock)

    def work():
        entry = profile._worker_scope(parent, owner)
        with pytest.raises(ValueError):
            entry.__enter__()
        assert profile._ACTIVE.get() is None and not entry.live
        with coordination.reader_budget(child_budget(owner)):
            with pytest.raises(ValueError):
                entry.__enter__()
            with profile._worker_scope(parent, owner) as fresh:
                fresh.require()

    in_thread(work)


@pytest.mark.parametrize('mutation', [
    'missing', 'unbound', 'owner_reused', 'later_deadline', 'different_domain',
    'replaced_event', 'missing_event', 'extra_event', 'reordered_events',
])
def test_worker_binding_refuses_wrong_actual_budget_join(
        selected_controls, fixed_clock, monkeypatch, mutation):
    parent, owner = profile._ACTIVE.get(), owner_budget(fixed_clock)

    def work():
        values = {}
        if mutation == 'unbound':
            values['clock_domain'] = None
        elif mutation == 'later_deadline':
            values['deadline_ns'] = owner.deadline_ns + 1
        elif mutation == 'different_domain':
            domain = deepcopy(fixed_clock)
            domain['boot_uuid'] = 'aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee'
            values['clock_domain'] = domain
        elif mutation == 'replaced_event':
            values['stop_events'] = (threading.Event(), owner.stop_events[1])
        elif mutation == 'missing_event':
            values['stop_events'] = owner.stop_events[:1]
        elif mutation == 'extra_event':
            values['stop_events'] = (*owner.stop_events, threading.Event())
        elif mutation == 'reordered_events':
            values['stop_events'] = tuple(reversed(owner.stop_events))
        budget = owner if mutation == 'owner_reused' else child_budget(owner, **values)
        entry = profile._worker_scope(parent, owner)
        if mutation == 'missing':
            with pytest.raises(ValueError):
                entry.__enter__()
        else:
            with monkeypatch.context() as patch:
                if mutation == 'different_domain':
                    patch.setattr(clocks, '_capture',
                        lambda: (deepcopy(values['clock_domain']), None))
                with coordination.reader_budget(budget):
                    # The scope itself is valid for this supplied domain. Only
                    # its association to the parent owner is wrong.
                    budget.remaining()
                    with pytest.raises(ValueError):
                        entry.__enter__()
        assert not entry.live and profile._ACTIVE.get() is None
        with coordination.reader_budget(child_budget(owner)):
            with pytest.raises(ValueError):
                entry.__enter__()

    in_thread(work)
    parent.require()


def test_worker_entry_cannot_be_created_on_parent_thread(selected_controls, fixed_clock):
    parent, owner = profile._ACTIVE.get(), owner_budget(fixed_clock)
    with coordination.reader_budget(child_budget(owner)):
        with pytest.raises(ValueError):
            with profile._worker_scope(parent, owner):
                pytest.fail('worker authority was admitted on the parent thread')
    parent.require()


def test_entry_constructed_by_parent_cannot_transfer_to_worker(selected_controls, fixed_clock):
    parent, owner = profile._ACTIVE.get(), owner_budget(fixed_clock)
    entry = profile._worker_scope(parent, owner)

    def work():
        with coordination.reader_budget(child_budget(owner)):
            with pytest.raises(ValueError):
                entry.__enter__()
            assert not entry.live and profile._ACTIVE.get() is None
            with pytest.raises(ValueError):
                entry.__enter__()
            with profile._worker_scope(parent, owner) as fresh:
                fresh.require()

    in_thread(work)
    parent.require()


@pytest.mark.parametrize('binder', ['control', 'runner', 'nested_worker'])
def test_borrowed_scope_is_reader_only(selected_controls, fixed_clock, binder):
    parent, owner = profile._ACTIVE.get(), owner_budget(fixed_clock)
    declaration = profile.source_profile(1)

    def work():
        with coordination.reader_budget(child_budget(owner)):
            with profile._worker_scope(parent, owner) as entry:
                with pytest.raises(ValueError):
                    if binder == 'control':
                        profile.bind_control(declaration, selected_controls)
                    elif binder == 'runner':
                        profile.bind_runner(declaration, selected_controls)
                    else:
                        with profile._worker_scope(entry, owner):
                            pytest.fail('borrowed reader scope became a worker parent')
                entry.require()

    in_thread(work)
    parent.require()


@pytest.mark.parametrize('mutation', ['parent_expired', 'controls_map', 'bare_graph', 'bare_origin'])
@pytest.mark.parametrize('body_error', [False, True])
def test_parent_change_refuses_success_but_preserves_original_body_error(
        selected_controls, fixed_clock, mutation, body_error):
    parent, owner = profile._ACTIVE.get(), owner_budget(fixed_clock)
    marker = OSError('original worker operation failed')

    def work():
        with coordination.reader_budget(child_budget(owner)):
            entry = profile._worker_scope(parent, owner)
            key = 'native_control'
            original = selected_controls[key]
            original_path = original.__file__
            try:
                with pytest.raises(OSError if body_error else ValueError) as caught:
                    with entry:
                        if mutation == 'parent_expired':
                            parent.live = False
                        elif mutation == 'controls_map':
                            selected_controls[key] = object()
                        elif mutation == 'bare_graph':
                            sys.modules[key] = object()
                        else:
                            original.__file__ = '/invented/not-the-selected-native-control.py'
                        if body_error:
                            raise marker
                if body_error:
                    assert caught.value is marker
                assert not entry.live and profile._ACTIVE.get() is None
            finally:
                parent.live = True
                selected_controls[key] = original
                sys.modules[key] = original
                original.__file__ = original_path
            with profile._worker_scope(parent, owner) as next_entry:
                next_entry.require()

    in_thread(work)
    parent.require()


@pytest.mark.parametrize('mutation', ['different_origin', 'missing_origin'])
def test_bare_origin_drift_refuses_entry_even_when_module_objects_match(
        selected_controls, fixed_clock, mutation):
    parent, owner = profile._ACTIVE.get(), owner_budget(fixed_clock)
    module = selected_controls['native_control']
    original_path = module.__file__

    def work():
        with coordination.reader_budget(child_budget(owner)):
            entry = profile._worker_scope(parent, owner)
            try:
                if mutation == 'different_origin':
                    module.__file__ = '/invented/not-the-selected-native-control.py'
                else:
                    del module.__file__
                assert sys.modules['native_control'] is module
                assert selected_controls['native_control'] is module
                with pytest.raises(ValueError):
                    entry.__enter__()
                assert not entry.live and profile._ACTIVE.get() is None
            finally:
                module.__file__ = original_path
            with pytest.raises(ValueError):
                entry.__enter__()
            with profile._worker_scope(parent, owner) as fresh:
                fresh.require()

    in_thread(work)
    parent.require()


@pytest.mark.parametrize('nested', ['worker', 'other_budget', 'same_budget', 'foreign_thread'])
@pytest.mark.parametrize('body_error', [False, True])
def test_wrong_exit_cannot_invalidate_actual_worker_entry(
        selected_controls, fixed_clock, nested, body_error):
    parent, owner = profile._ACTIVE.get(), owner_budget(fixed_clock)
    marker = OSError('foreign caller body error') if body_error else None

    def work():
        budget = child_budget(owner)
        with coordination.reader_budget(budget):
            with profile._worker_scope(parent, owner) as entry:
                def wrong_exit():
                    with pytest.raises(ValueError):
                        entry.require()
                    with pytest.raises(ValueError):
                        entry.__exit__(None if marker is None else type(marker), marker, None)
                    assert entry.live

                if nested == 'worker':
                    with profile._worker_scope(parent, owner) as inner:
                        wrong_exit()
                        inner.require()
                elif nested in ('other_budget', 'same_budget'):
                    other = budget if nested == 'same_budget' else child_budget(owner)
                    with coordination.reader_budget(other):
                        wrong_exit()
                else:
                    in_thread(wrong_exit, context=copy_context())
                assert profile._ACTIVE.get() is entry and entry.live
                entry.require()
            assert not entry.live and profile._ACTIVE.get() is None

    in_thread(work)
    parent.require()


@pytest.mark.parametrize('kind', ['observer', 'classifier'])
@pytest.mark.parametrize('error_kind', ['ordinary', 'budget_stop'])
def test_actual_runner_worker_reads_then_preserves_its_operation_error(
        worker_case, kind, error_kind):
    case = install_reader_operation(worker_case, kind)
    BudgetStop = case['controls']['budgeted_cborg'].BudgetStop
    primary = (BudgetStop('exact worker stop after selected read') if error_kind == 'budget_stop'
               else OSError('original observer or classifier failed after selected read'))

    def failing_read():
        read_in_worker(case)
        raise primary

    if kind == 'observer':
        def observe(event):
            case['observed'].append(event)
            if event.get('type') == 'system' and event.get('subtype') == 'init':
                failing_read()
        case['kwargs']['event_observer'] = observe
    else:
        case['kwargs']['command_classifier'] = lambda *args: failing_read()

    with pytest.raises(BudgetStop) as caught:
        case['runner'].execute_child(**case['kwargs'])
    if error_kind == 'budget_stop':
        assert caught.value is primary
    else:
        assert caught.value.__cause__ is primary
    assert len(case['reader_observations']) == 1
    row = case['reader_observations'][0]
    assert row['thread'] is not threading.current_thread()
    assert row['scope'] is not case['parent_scope'] and not row['scope'].live
    assert row['member'].captured.raw
    report = case['runner'].report()
    assert report['state'] == 'failed' and report['dispatches'] == 1
    assert report['owner_published'] is True and report['stop_marker_published'] is True
    assert report['primary_error'] is not None
    assert case['stops']
    if kind == 'classifier':
        assert not (case['root'] / 'received-response.json').exists()
    assert profile._ACTIVE.get() is case['parent_scope'] and case['parent_scope'].live
    case['parent_scope'].require()


@pytest.mark.parametrize('body_error', [False, True])
def test_stop_during_body_never_renews_budget_or_masks_operation_failure(
        selected_controls, fixed_clock, body_error):
    parent, owner = profile._ACTIVE.get(), owner_budget(fixed_clock)
    marker = OSError('body failure remains first')

    def work():
        budget = child_budget(owner)
        deadline = budget.deadline_ns
        with coordination.reader_budget(budget):
            entry = profile._worker_scope(parent, owner)
            try:
                with pytest.raises(OSError if body_error else ValueError) as caught:
                    with entry:
                        owner.stop_events[0].set()
                        if body_error:
                            raise marker
                if body_error:
                    assert caught.value is marker
                assert not entry.live and budget.deadline_ns == deadline
            finally:
                owner.stop_events[0].clear()

    in_thread(work)

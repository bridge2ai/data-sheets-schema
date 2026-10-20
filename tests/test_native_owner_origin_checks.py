"""Current qualified origins remain checked once on each reader entry.

Offline regression for the #4354 owner-lifetime performance integration,
2026-10-20: real loader/worker scopes and an invented clock backend; no helper
or provider execution.
"""
import sys
import threading
import time

import pytest

from data_sheets_schema import native_owner_profile_v1 as profile
from data_sheets_schema import native_stream_coordination_v1 as coordination
from .test_native_owner_runner import fixed_clock, selected_controls


@pytest.mark.parametrize('worker', [False, True])
@pytest.mark.parametrize('role', profile._MODULES)
def test_each_parent_or_worker_entry_checks_all_current_qualified_origins(
        selected_controls, fixed_clock, tmp_path, monkeypatch, worker, role):
    parent = profile._ACTIVE.get()
    assert parent._parent is None and parent.controls is selected_controls
    actual = profile._origin
    checked = []

    def inspect(current_role, module):
        checked.append(current_role)
        return actual(current_role, module)

    monkeypatch.setattr(profile, '_origin', inspect)

    def check(scope):
        checked.clear()
        coordination._selected_reader_scope(scope)
        assert checked == list(profile._MODULES)
        module = sys.modules[profile._MODULES[role]]
        with monkeypatch.context() as change:
            change.setattr(module, '__file__', str(tmp_path / 'foreign.py'))
            with pytest.raises(ValueError, match='foreign qualified origin'):
                coordination._selected_reader_scope(scope)
        checked.clear()
        coordination._selected_reader_scope(scope)
        assert checked == list(profile._MODULES)

    if not worker:
        check(parent)
        return
    stop = threading.Event()
    deadline = time.monotonic_ns() + 10_000_000_000
    owner = coordination.ReaderBudget(deadline, (stop,), clock_domain=fixed_clock)
    errors = []

    def consume():
        try:
            budget = coordination.ReaderBudget(deadline, (stop,), clock_domain=fixed_clock)
            with coordination.reader_budget(budget):
                with profile._worker_scope(parent, owner) as scope:
                    check(scope)
        except BaseException as error:
            errors.append(error)

    thread = threading.Thread(target=consume)
    thread.start()
    thread.join(10)
    assert not thread.is_alive()
    if errors:
        raise errors[0]

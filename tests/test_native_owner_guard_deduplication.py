"""Adjacent guard deduplication for #4354, 2026-10-20.

Real private loader/reader scopes with an invented clock backend. No helper,
provider, accepted generation, or relaxed lifetime deadline is involved.
"""
import fcntl
import os
import sys

import pytest

from data_sheets_schema import native_owner_profile_v1 as profile
from data_sheets_schema import native_stream_coordination_v1 as coordination
from tests.test_native_owner_live_reader import declaration, entered_case, reader_case
from tests.test_native_owner_runner import fixed_clock, selected_controls
from tests.test_native_owner_worker_scope_adversarial import (
    child_budget, in_thread, owner_budget,
)


@pytest.mark.parametrize('worker', [False, True])
@pytest.mark.parametrize('role', profile._MODULES)
def test_reconstruction_keeps_each_fresh_origin_sweep_and_exit_refusal(
        selected_controls, fixed_clock, tmp_path, monkeypatch, worker, role):
    parent = profile._ACTIVE.get()
    actual = profile._origin
    checked = []

    def inspect(current_role, module):
        checked.append(current_role)
        return actual(current_role, module)

    monkeypatch.setattr(profile, '_origin', inspect)

    def exercise():
        checked.clear()
        with profile._reconstruction_controls() as controls:
            assert controls is selected_controls
            # One lifetime sweep and one fresh source-profile sweep on entry.
            assert checked == list(profile._MODULES) * 2
        assert checked == list(profile._MODULES) * 4
        module = sys.modules[profile._MODULES[role]]
        with monkeypatch.context() as change:
            change.setattr(module, '__file__', str(tmp_path / 'foreign.py'))
            with pytest.raises(ValueError, match='foreign qualified origin'):
                with profile._reconstruction_controls():
                    pytest.fail('foreign origin reached reconstruction body')
        original = module.__file__
        try:
            with pytest.raises(ValueError, match='foreign qualified origin'):
                with profile._reconstruction_controls():
                    module.__file__ = str(tmp_path / 'changed-after-entry.py')
        finally:
            module.__file__ = original
        with profile._reconstruction_controls() as controls:
            assert controls is selected_controls

    if not worker:
        exercise()
        return
    owner = owner_budget(fixed_clock)

    def consume():
        with coordination.reader_budget(child_budget(owner)):
            with profile._worker_scope(parent, owner):
                exercise()

    in_thread(consume)
    parent.require()


def test_selected_metadata_keeps_three_owner_boundaries_without_direct_budget_repeat(
        reader_case, monkeypatch):
    case = reader_case
    path = case['paths']['transcript']
    fd = os.open(path, os.O_RDONLY)
    writer = os.open(path, os.O_RDWR)
    actual_current = coordination._OwnerReaderContext.require_current
    actual_remaining = coordination.ReaderBudget.remaining
    current_calls, direct_remaining = [], []
    try:
        with entered_case(case) as context:
            def current(self, *args, **kwargs):
                if self is context:
                    current_calls.append((args, kwargs))
                return actual_current(self, *args, **kwargs)

            def remaining(self):
                if sys._getframe(1).f_code.co_name == 'sample_metadata':
                    direct_remaining.append(self)
                return actual_remaining(self)

            with monkeypatch.context() as patch:
                patch.setattr(coordination._OwnerReaderContext, 'require_current', current)
                patch.setattr(coordination.ReaderBudget, 'remaining', remaining)
                before, opened = coordination.sample_metadata(
                    fd, str(path), case['budget'], include_path=True, reader_context=context)
            assert before == opened
            assert current_calls == [(('transcript', str(path)), {})] * 3
            assert direct_remaining == []
            # A fresh writer can acquire EX: the SH lease has been released.
            lease = coordination.try_lease(writer, fcntl.LOCK_EX)
            assert lease is not None
            with lease:
                pass
    finally:
        os.close(fd)
        os.close(writer)


@pytest.mark.parametrize('boundary', [1, 2, 3])
def test_selected_metadata_stop_at_each_boundary_refuses_and_releases_lease(
        reader_case, monkeypatch, boundary):
    case = reader_case
    path = case['paths']['transcript']
    fd = os.open(path, os.O_RDONLY)
    writer = os.open(path, os.O_RDWR)
    actual = coordination._OwnerReaderContext.require_current
    calls = []
    try:
        with entered_case(case) as context:
            def current(self, *args, **kwargs):
                if self is context:
                    calls.append(len(calls) + 1)
                    if len(calls) == boundary:
                        case['stop_path'].write_bytes(b'{"stop":true}')
                return actual(self, *args, **kwargs)

            try:
                with monkeypatch.context() as patch:
                    patch.setattr(coordination._OwnerReaderContext, 'require_current', current)
                    with pytest.raises(ValueError, match='stop marker'):
                        coordination.sample_metadata(
                            fd, str(path), case['budget'], include_path=True, reader_context=context)
                assert len(calls) == boundary
                lease = coordination.try_lease(writer, fcntl.LOCK_EX)
                assert lease is not None
                with lease:
                    pass
            finally:
                case['stop_path'].unlink(missing_ok=True)
    finally:
        os.close(fd)
        os.close(writer)

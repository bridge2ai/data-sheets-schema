"""U3-K worker-local pre-reservation measurements, 2026-11-09.

Inputs: explicit pytest plugin, U3K_METRICS physical output directory and
U3K_PROFILE=control|cprofile. Outputs: exclusive per-process phase JSON, raw
cProfile data and function statistics. No source/guard/clock monkeypatches.
The control retains the same boundary observer; cProfile is the only difference.
Per-thread inclusive function times overlap and are never summed as phase CPU.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import cProfile
import hashlib
import json
import os
from pathlib import Path
import pstats
import resource
import sys
import threading
import time

import pytest


TARGETS = {
    ('test_native_shared_execution.py', 'make_case'): 'public_fixture',
    ('test_native_shared_execution.py', 'launch_case'): 'public_test_launch',
    ('test_native_shared_execution.py', 'assert_completed_case'): 'public_assert_and_readbacks',
    ('native_shared_execution_orchestration.py', 'synthetic_launch'): 'public_launch',
    ('native_execution_orchestration.py', 'synthetic_launch'): 'engine_entry',
    ('native_shared_controller_orchestration.py', 'prewarm_before_acceptance'): 'controller_prewarm',
    ('native_shared_controller_orchestration.py', 'activate_before_dispatch'): 'controller_activate',
    ('native_execution_orchestration.py', '_execute_child'): 'execute_child',
    ('native_shared_results_orchestration.py', 'capture'): 'final_capture',
    ('native_shared_results_orchestration.py', 'prepare'): 'saved_prepare',
    ('native_shared_results_orchestration.py', 'check_capture'): 'saved_gate_replay',
    ('native_shared_execution_orchestration.py', 'read_final'): 'public_saved_readback',
    ('native_execution_orchestration.py', 'read_final'): 'engine_saved_readback',
    ('native_shared_selection.py', 'capture'): 'selection_capture',
    ('native_shared_selection.py', '_rebuild'): 'selection_rebuild',
    ('native_shared_selection.py', '_schemas'): 'schema_reconstruction',
    ('native_shared_selection.py', '_cached_schemas'): 'schema_cache_lookup',
    ('schema_snapshot.py', '_capture_native_schema'): 'schema_capture',
    ('native_shared_registration_orchestration.py', 'verified'): 'shared_registration_verified',
    ('native_execution_registration_v2.py', 'verified'): 'execution_registration_verified',
    ('native_execution_registration_v2.py', 'verify_preparer'): 'preparer_verified',
    ('native_execution_registration_v2.py', 'admit'): 'fresh_admission',
    ('native_shared_runtime_values.py', 'executable_identity'): 'shared_binary_fingerprint',
    ('native_execution_registration.py', 'executable_identity'): 'legacy_binary_fingerprint',
    ('native_u4b_runtime.py', '_binary_pin'): 'u4b_binary_fingerprint',
    ('native_runtime_profiles.py', 'require_synthetic'): 'synthetic_peer_fingerprint',
    ('native_subscription_admission.py', 'load_current'): 'accept_saved_capture',
    ('native_subscription_guard_v2.py', 'before_reservation'): 'freshness_before_reservation',
    ('native_subscription_guard_v2.py', 'before_dispatch'): 'freshness_before_dispatch',
    ('native_subscription_guard_v2.py', '_fresh'): 'freshness_check',
    ('native_execution_orchestration.py', '_launch'): 'launch_engine',
    ('test_native_u3k_profile.py', 'u3k_dynamic_witness'): 'canary_dynamic_code',
    ('test_native_u3k_profile.py', 'u3k_cpu_witness'): 'canary_cpu',
}
COARSE_LABELS = frozenset(('public_fixture', 'public_test_launch', 'public_assert_and_readbacks',
    'public_launch', 'engine_entry', 'launch_engine', 'controller_prewarm', 'controller_activate',
    'execute_child', 'final_capture', 'saved_prepare', 'saved_gate_replay',
    'public_saved_readback', 'engine_saved_readback', 'attempt_mkdir',
    'accept_saved_capture', 'canary_cpu'))
ROOT = Path(__file__).resolve().parents[2]
_ACTIVE = None


def sample():
    own = resource.getrusage(resource.RUSAGE_SELF)
    child = resource.getrusage(resource.RUSAGE_CHILDREN)
    return {'wall_monotonic': time.monotonic(), 'process_cpu': time.process_time(),
        'thread_cpu': time.thread_time(), 'self_user_cpu': own.ru_utime,
        'self_system_cpu': own.ru_stime, 'reaped_child_user_cpu': child.ru_utime,
        'reaped_child_system_cpu': child.ru_stime,
        'utc': datetime.now(timezone.utc).isoformat()}


def delta(before, after):
    return {key: after[key] - before[key] for key in before if key != 'utc'}


class Recorder:
    def __init__(self, node):
        self.node = node
        self.worker = os.environ.get('PYTEST_XDIST_WORKER', 'controller')
        if self.worker == 'controller':
            raise RuntimeError('U3-K measurement requires the explicit xdist worker')
        self.mode = os.environ.get('U3K_PROFILE')
        if self.mode not in {'control', 'cprofile'}:
            raise ValueError('U3K_PROFILE must be control or cprofile')
        self.directory = Path(os.environ['U3K_METRICS'])
        if (not self.directory.is_absolute() or self.directory.is_symlink()
                or self.directory.parent.resolve(strict=True) != self.directory.parent):
            raise ValueError('U3-K output requires a physical absolute parent')
        self.directory.mkdir(exist_ok=True)
        if self.directory.resolve(strict=True) != self.directory:
            raise ValueError('U3-K output directory is an alias')
        self.rows = []
        self.phases = []
        self.pytest_phases = []
        self.codes = {}
        self.stacks = {}
        self.current = None
        self.pytest_current = None
        self.attempt_path = None
        self.mkdir_code = Path.mkdir.__code__
        self.monitor = sys.monitoring
        self.tool = next((i for i in (3, 4) if self.monitor.get_tool(i) is None), None)
        if self.tool is None:
            raise RuntimeError('no separate monitoring slot for U3-K observer')
        self.monitor.use_tool_id(self.tool, 'u3k-boundaries')
        self.monitor.register_callback(self.tool, self.monitor.events.PY_START, self.enter)
        self.monitor.register_callback(self.tool, self.monitor.events.PY_RETURN, self.leave)
        self.monitor.register_callback(self.tool, self.monitor.events.PY_UNWIND, self.unwind)
        self.monitor.set_events(self.tool,
            self.monitor.events.PY_START | self.monitor.events.PY_UNWIND)

    def _key(self, code, frame):
        if code is self.mkdir_code:
            path = frame.f_locals.get('self')
            return 'attempt_mkdir' if (isinstance(path, Path) and self.attempt_path is not None
                                       and str(path) == self.attempt_path) else None
        path = Path(code.co_filename)
        if not path.is_absolute() or not path.is_relative_to(ROOT):
            return None
        return TARGETS.get((path.name, code.co_name))

    def enter(self, code, offset):
        frame = sys._getframe(1)
        label = self._key(code, frame)
        if label is None:
            # mkdir can become the reservation boundary later in this run.
            return None if code is self.mkdir_code else self.monitor.DISABLE
        identity = id(code)
        if identity not in self.codes:
            self.codes[identity] = (code, {'label': label, 'file': code.co_filename,
                'name': code.co_name, 'first_line': code.co_firstlineno,
                'code_object_id': identity,
                'bytecode_sha256': hashlib.sha256(code.co_code).hexdigest()})
            self.monitor.set_local_events(self.tool, code, self.monitor.events.PY_RETURN)
        phase = self.current or self.pytest_current
        if phase is None:
            return
        row = {**self.codes[identity][1], 'phase': phase, 'thread': threading.get_ident(),
            'entered_wall': time.monotonic(), 'entered_thread_cpu': time.thread_time(),
            'entered_utc': datetime.now(timezone.utc).isoformat(), 'outcome': 'open'}
        if label in COARSE_LABELS:
            row['coarse_before'] = sample()
        if label == 'launch_engine':
            raw = frame.f_locals.get('registration_raw')
            if type(raw) is bytes:
                try:
                    path = json.loads(raw)['registration']['attempt_directory']
                    if type(path) is str and Path(path).is_absolute():
                        self.attempt_path = path
                        row['attempt_path'] = path
                except (ValueError, KeyError, TypeError):
                    row['attempt_path'] = None
        if label.startswith('freshness_'):
            try:
                raw = object.__getattribute__(frame.f_locals['self'], '_raw')
                if type(raw) is bytes:
                    value = json.loads(raw)
                    row['capture'] = {key: value.get(key) for key in (
                        'captured_at', 'max_age_seconds', 'pre_reservation_margin_seconds')}
            except (AttributeError, KeyError, TypeError, ValueError):
                row['capture'] = None
        if label == 'attempt_mkdir':
            row['attempt_path'] = self.attempt_path
        self.rows.append(row)
        self.stacks.setdefault(threading.get_ident(), []).append((code, row))

    def _leave(self, code, outcome):
        stack = self.stacks.get(threading.get_ident(), [])
        if not stack or stack[-1][0] is not code:
            return
        _, row = stack.pop()
        row.update(outcome=outcome, inclusive_wall=time.monotonic() - row['entered_wall'],
            inclusive_thread_cpu=time.thread_time() - row['entered_thread_cpu'],
            left_utc=datetime.now(timezone.utc).isoformat())
        if 'coarse_before' in row:
            row['coarse_after'] = sample()
            row['coarse_elapsed'] = delta(row['coarse_before'], row['coarse_after'])
            row['coarse_scope'] = ('Inclusive boundary: worker process/self, calling thread and '
                'reaped children separately. Nested boundaries overlap. Peer recorder helper CPU '
                'is not isolated; child CPU can appear only after reaping.')
        return row

    def leave(self, code, offset, value):
        row = self._leave(code, 'return')
        if row is not None and row['label'] == 'accept_saved_capture':
            row['guard_accepted_at'] = row['left_utc']
            try:
                raw = object.__getattribute__(value, '_raw')
                if type(raw) is bytes:
                    guard = json.loads(raw)
                    row['capture'] = {key: guard.get(key) for key in (
                        'captured_at', 'max_age_seconds', 'pre_reservation_margin_seconds')}
            except (AttributeError, TypeError, ValueError):
                row['capture'] = None

    def unwind(self, code, offset, exception):
        if id(code) in self.codes:
            self._leave(code, 'exception:' + type(exception).__name__)

    def save(self, name, value):
        path = self.directory / (str(os.getpid()) + '-' + name)
        raw = (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()
        with path.open('xb') as stream:
            stream.write(raw)
        if path.read_bytes() != raw:
            raise RuntimeError('U3-K measurement failed to persist exactly')
        return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}

    @contextmanager
    def phase(self, name, *, force_profile=False, force_unprofiled=False):
        if self.current is not None or not name.replace('_', '').isalnum():
            raise ValueError('U3-K phases must be nonnested literal names')
        if force_profile and force_unprofiled:
            raise ValueError('U3-K phase cannot force both profiling modes')
        self.current = name
        first = len(self.rows)
        profiler = cProfile.Profile(timer=time.thread_time_ns, timeunit=1e-9) \
            if not force_unprofiled and (self.mode == 'cprofile' or force_profile) else None
        before = sample()
        outcome, error = 'return', None
        if profiler is not None:
            profiler.enable()
        try:
            yield
        except BaseException as exc:
            outcome, error = 'exception', type(exc).__name__ + ': ' + str(exc)
            raise
        finally:
            if profiler is not None:
                profiler.disable()
            after = sample()
            self.current = None
            row = {'name': name, 'before': before, 'after': after,
                'elapsed': delta(before, after), 'outcome': outcome, 'error': error,
                'profiled': profiler is not None, 'first_call_row': first,
                'last_call_row_exclusive': len(self.rows)}
            if profiler is not None:
                path = self.directory / (str(os.getpid()) + '-' + name + '.pstats')
                if os.path.lexists(path):
                    raise ValueError('U3-K profile path already exists')
                profiler.dump_stats(str(path))
                raw = path.read_bytes()
                if not raw:
                    raise ValueError('U3-K profile was not persisted')
                stats = pstats.Stats(profiler)
                functions = []
                for key, counts in stats.stats.items():
                    functions.append({'file': key[0], 'line': key[1], 'name': key[2],
                        'primitive_calls': counts[0], 'calls': counts[1],
                        'self_thread_cpu': counts[2], 'inclusive_thread_cpu': counts[3],
                        'callers': [{'file': caller[0], 'line': caller[1], 'name': caller[2],
                            'counts': list(values) if isinstance(values, tuple) else values}
                            for caller, values in counts[4].items()]})
                functions.sort(key=lambda item: (-item['inclusive_thread_cpu'], item['file'], item['line'], item['name']))
                row['profile'] = {'path': str(path), 'bytes': len(raw),
                    'sha256': hashlib.sha256(raw).hexdigest(), 'timer': 'time.thread_time_ns',
                    'timeunit': 1e-9, 'scope': 'Calling worker thread only; other-thread/child CPU excluded.'}
                row['profile_json'] = self.save(name + '-functions.json', {'functions': functions})
            self.phases.append(row)

    def finish(self):
        self.monitor.set_events(self.tool, 0)
        for code, _ in self.codes.values():
            self.monitor.set_local_events(self.tool, code, 0)
        self.monitor.free_tool_id(self.tool)
        counts = {}
        for row in self.rows:
            key = row['phase'] + ':' + row['label']
            counts[key] = counts.get(key, 0) + 1
        accepted = [row for row in self.rows if row['label'] == 'accept_saved_capture'
                    and row['outcome'] == 'return']
        reservation = [row for row in self.rows if row['label'] == 'attempt_mkdir'
                       and row['outcome'] == 'return']
        windows = []
        for row in reservation:
            preceding = [guard for guard in accepted if guard['entered_wall'] <= row['entered_wall']]
            guard = preceding[-1] if preceding else None
            captured = guard.get('capture') if guard is not None else None
            try:
                capture_time = datetime.fromisoformat(captured['captured_at'].replace('Z', '+00:00'))
                capture_to_reservation = (datetime.fromisoformat(row['entered_utc']) - capture_time).total_seconds()
            except (KeyError, TypeError, ValueError, AttributeError):
                capture_to_reservation = None
            windows.append({'attempt_path': row['attempt_path'], 'reservation_entry_utc': row['entered_utc'],
                'reservation_return_utc': row['left_utc'], 'capture': captured,
                'guard_accepted_at': guard['guard_accepted_at'] if guard is not None else None,
                'capture_to_reservation_wall_seconds': capture_to_reservation,
                'accepted_to_reservation_wall_seconds': (datetime.fromisoformat(row['entered_utc'])
                    - datetime.fromisoformat(guard['guard_accepted_at'])).total_seconds() if guard is not None else None,
                'scope': 'Observed original Path.mkdir entry and successful return; clock timestamps are not independent authority.'})
        self.save('measurement.json', {'node': self.node, 'pid': os.getpid(),
            'worker': self.worker, 'mode': self.mode, 'phases': self.phases,
            'pytest_phases': self.pytest_phases,
            'calls': self.rows, 'call_counts': counts,
            'registered_code_objects': [row for _, row in self.codes.values()],
            'observed_reservation_windows': windows,
            'open_call_rows': sum(row['outcome'] == 'open' for row in self.rows),
            'cpu_policy': 'Phase process/thread CPU, self user/system and reaped-child CPU are separate. Inclusive function times overlap and are not added across functions.',
            'scope': 'Offline synthetic diagnostic; no production clock/guard change or native acceptance.'})


def active():
    if _ACTIVE is None:
        raise RuntimeError('explicit U3-K pytest worker plugin is required')
    return _ACTIVE


def _selected(item):
    return ('U3K_METRICS' in os.environ and item.path.name in {
        'test_native_u3k_profile.py', 'test_native_shared_execution.py',
        'test_native_shared_execution_variant.py'})


def _pytest_end(recorder, phase, before, result):
    after = sample()
    recorder.pytest_phases.append({'name': phase, 'before': before, 'after': after,
        'elapsed': delta(before, after), 'outcome': 'exception' if result.excinfo else 'return',
        'scope': 'Passive pytest lifecycle phase; may enclose explicit diagnostic phases, so do not add both.'})
    recorder.pytest_current = None


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_setup(item):
    global _ACTIVE
    if not _selected(item):
        yield
        return
    _ACTIVE = Recorder(item.nodeid)
    _ACTIVE.pytest_current = 'pytest_setup'
    before = sample()
    result = yield
    _pytest_end(_ACTIVE, 'setup', before, result)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item):
    if not _selected(item):
        yield
        return
    _ACTIVE.pytest_current = 'pytest_call'
    before = sample()
    result = yield
    _pytest_end(_ACTIVE, 'call', before, result)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_teardown(item):
    global _ACTIVE
    if not _selected(item) or _ACTIVE is None:
        yield
        return
    recorder = _ACTIVE
    recorder.pytest_current = 'pytest_teardown'
    before = sample()
    try:
        result = yield
        _pytest_end(recorder, 'teardown', before, result)
    finally:
        _ACTIVE = None
        recorder.finish()

"""Issue 6233, 2026-11-14: measure real offline public callback CPU.

Inputs: pytest arguments; output: CALLBACK_METRICS JSONL and supplemental
host-controller timing rows. Uses monitoring without replacing pinned functions.
"""
import json
import os
from pathlib import Path
import sys
import threading
import time
import cProfile
import pstats
from dataclasses import replace

import pytest

OUTPUT = Path(os.environ['CALLBACK_METRICS'])
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
monitor = sys.monitoring
tool = 0
active = {}
detail_names = {'_checked_observations', '_prepare_next', 'phase_replay', '_loaded', 'reconstruct', '_history',
                '_stage_uncached', '_derive_response_uncached'}
names = {'_observe_event', '_classify_frame', 'read_regular', 'read_live_stream'} | detail_names
stacks = {}
snapshots = {}
largest = []
profile_indices = {int(value) for value in os.environ.get('CALLBACK_PROFILE_INDICES', '').split(',') if value}
live_profiles = {}


def start(code, offset):
    if code.co_name not in names:
        return monitor.DISABLE
    filename = code.co_filename.rsplit('/', 1)[-1]
    thread = threading.get_ident()
    if code.co_name in detail_names:
        if thread in active and (filename.startswith('native_shared_') or
                (filename == '__init__.py' and '/native_shared_stage/' in code.co_filename)):
            stacks.setdefault(thread, []).append((code, time.thread_time(), time.perf_counter()))
            local = sys._getframe(1).f_locals
            counts = active[thread]['verification_inputs']
            if code.co_name == '_history' and 'history' in local:
                counts['stage_records'] = counts.get('stage_records', 0) + len(local['history'].records)
            if code.co_name == '_checked_observations' and 'run' in local:
                counts['observations'] = counts.get('observations', 0) + len(local['run'].observations)
        return
    if filename != 'native_control.py' or code.co_name == 'read_regular':
        return
    frame = sys._getframe(1)
    if frame.f_code is not code:
        raise RuntimeError('measurement frame mismatch')
    local = frame.f_locals
    event = local.get('event', local.get('frame', {}))
    controller = local['self']
    data = event.get('request', {}).get('input', {})
    active[threading.get_ident()] = {
        'kind': 'callback_cpu', 'boundary': 'callback_cpu', 'work': code.co_name,
        'event_type': event.get('type'), 'tool': data.get('tool_name'),
        'tool_use_id': data.get('tool_use_id'), 'line': controller.event_line,
        'calls': len(controller.calls), 'reads': {}, 'bytes': {},
        'records': {}, 'verification_inputs': {}, 'functions': {}, 'timing_directory': str(controller.timing.directory) if controller.timing else None,
        '_timing': controller.timing,
        '_clock': (time.thread_time(), time.process_time(), time.perf_counter()),
    }
    if (profile_indices and code.co_name in ('_observe_event', '_classify_frame')
            and event.get('type') == 'control_request' and len(controller.calls) in profile_indices):
        if monitor.get_tool(monitor.PROFILER_ID) is not None:
            raise RuntimeError('live cProfile requires the standalone diagnostic, never the guarded public test')
        # Built-in elapsed timer avoids a Python clock call at every profile
        # event. Worker CPU is measured separately; profile times are elapsed.
        profile = cProfile.Profile()
        live_profiles[thread] = profile
        profile.enable()


def end(code, offset, value):
    if code.co_name not in names:
        return monitor.DISABLE
    row = active.get(threading.get_ident())
    if row is None:
        return
    filename = code.co_filename.rsplit('/', 1)[-1]
    thread = threading.get_ident()
    if code.co_name in detail_names:
        stack = stacks.get(thread, [])
        if stack and stack[-1][0] is code:
            _, cpu, wall = stack.pop()
            key = filename + ':' + code.co_name
            detail = row['functions'].setdefault(key, {'calls': 0, 'thread_cpu': 0, 'wall': 0})
            detail['calls'] += 1
            detail['thread_cpu'] += time.thread_time() - cpu
            detail['wall'] += time.perf_counter() - wall
            if code.co_name == '_checked_observations' and value is not UNWOUND:
                counts = row['verification_inputs']
                counts['new_observations_checked'] = counts.get('new_observations_checked', 0) + len(value)
            if code.co_name == '_loaded' and value is not UNWOUND:
                frame = sys._getframe(1)
                if frame.f_code is code:
                    snapshots[thread] = (value, frame.f_globals['_checked_observations'])
        return
    if ((code.co_name == 'read_regular' and filename == 'native_shared_evidence.py')
            or (code.co_name == 'read_live_stream' and filename == 'native_shared_streams.py')):
        if hasattr(value, 'captured'):
            item = value.captured
            role = item.pin.role
            row['reads'][role] = row['reads'].get(role, 0) + 1
            row['bytes'][role] = row['bytes'].get(role, 0) + len(item.raw)
            count = 1
            if role in ('transcript', 'control'):
                count = item.raw.count(b'\n')
            elif role == 'journal':
                count = len(json.loads(item.raw).get('records', []))
            row['records'][role] = row['records'].get(role, 0) + count
        return
    if filename != 'native_control.py' or code.co_name not in ('_observe_event', '_classify_frame'):
        return
    clocks = (time.thread_time(), time.process_time(), time.perf_counter())
    active.pop(threading.get_ident())
    for key, finish, begin in zip(('thread_cpu', 'process_cpu', 'wall'), clocks, row.pop('_clock')):
        row[key] = finish - begin
    timing = row.pop('_timing')
    row['unwound'] = value is UNWOUND
    profile = live_profiles.pop(thread, None)
    row['cprofile_enabled'] = profile is not None
    if profile is not None:
        profile.disable()
        profile_path = OUTPUT.parent / f"callback-{row['calls']}-line-{row['line']}-{row['event_type']}-{row['work'].lstrip('_')}.prof"
        profile.dump_stats(str(profile_path))
        if not profile_path.stat().st_size or not pstats.Stats(str(profile_path)).stats:
            raise RuntimeError('live profile did not persist populated statistics')
        with profile_path.with_suffix('.txt').open('w') as stream:
            pstats.Stats(profile, stream=stream).sort_stats('cumulative').print_stats(50)
    snapshot = snapshots.pop(thread, None)
    if snapshot is not None and row['event_type'] == 'control_request' and not row['unwound']:
        largest.append((row['thread_cpu'], row['calls'], snapshot))
        largest.sort(key=lambda item: item[0], reverse=True)
        del largest[2:]
    raw = (json.dumps(row, sort_keys=True) + '\n').encode()
    destinations = [OUTPUT]
    for path in destinations:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        try:
            if os.write(fd, raw) != len(raw):
                raise OSError('incomplete callback diagnostic write')
        finally:
            os.close(fd)
    if timing is not None:
        timing.record('callback_cpu', **{key: row[key] for key in (
            'work', 'event_type', 'tool', 'tool_use_id', 'line', 'calls',
            'thread_cpu', 'process_cpu', 'wall', 'records', 'unwound', 'cprofile_enabled')})


UNWOUND = object()


def unwind(code, offset, exception):
    end(code, offset, UNWOUND)


monitor.use_tool_id(tool, 'callback-cpu-diagnostic')
monitor.register_callback(tool, monitor.events.PY_START, start)
monitor.register_callback(tool, monitor.events.PY_RETURN, end)
monitor.register_callback(tool, monitor.events.PY_UNWIND, unwind)
monitor.set_events(tool, monitor.events.PY_START | monitor.events.PY_RETURN | monitor.events.PY_UNWIND)
try:
    if any(value in sys.argv for value in ('--standalone-omissions', '--standalone-correction')):
        # Same public synthetic API and unchanged production checks. This is
        # a profiling diagnostic, not a replacement or claimed pytest pass.
        # No test profile-stability guard is entered or modified.
        sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
        from tests.test_native_shared_execution import make_case
        from data_sheets_schema import native_shared_execution_orchestration as execute
        omission = '--standalone-omissions' in sys.argv
        case = make_case(OUTPUT.parent / 'case', fixture='omission' if omission else 'neutral',
                         receipt_origin_version=1 if omission else 0)
        result = execute.synthetic_launch(case['raw'], **case['kwargs'])
        (case['root'] / 'actual-result.json').write_text(json.dumps(result, sort_keys=True) + '\n')
        status = 0 if result['runtime_gates_passed'] else 1
    else:
        if profile_indices:
            raise RuntimeError('live cProfile is restricted to the standalone diagnostic')
        status = pytest.main(sys.argv[1:])
finally:
    monitor.set_events(tool, 0)
    monitor.free_tool_id(tool)
for ordinal, (cpu, index, (run, checked)) in enumerate([] if profile_indices else largest):
    profile = cProfile.Profile(timer=time.thread_time)
    outcome = {'callback': index, 'live_observer_thread_cpu': cpu,
               'scope': 'Retained immutable capture replay of _checked_observations only; not a second live observer invocation.'}
    try:
        replay = replace(run)
        replay._catalogs = run._catalogs
        profile.runcall(checked, replay)
        outcome['result'] = 'completed'
    except Exception as error:
        outcome['result'] = type(error).__name__ + ': ' + str(error)
    profile.dump_stats(str(OUTPUT.parent / f'largest-{ordinal}.prof'))
    with (OUTPUT.parent / f'largest-{ordinal}.txt').open('w') as stream:
        stream.write(json.dumps(outcome) + '\n')
        pstats.Stats(profile, stream=stream).sort_stats('cumulative').print_stats(35)
raise SystemExit(status)

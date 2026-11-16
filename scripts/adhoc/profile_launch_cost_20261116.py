"""Profile launch costs for the Claude lead assignment, 2026-11-16.

Inputs: scratch output directory and mode. Outputs: sampled main-thread stacks,
phase events, light census cProfile and pytest evidence. No gate replacement.
"""
import cProfile
import json
import os
from pathlib import Path
import pstats
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path[0] = str(ROOT)


def main():
    output = Path(sys.argv[1])
    mode = sys.argv[2]
    if mode == 'configure':
        path = output / 'isolated-venv/lib/python3.13/site-packages/data_sheets_schema.pth'
        backup = path.with_name(path.name + '.bak-launch-cost-20261116')
        if backup.exists():
            raise ValueError('already configured')
        backup.write_bytes(path.read_bytes())
        path.write_text(str(ROOT / 'src') + '\n')
        print(json.dumps({'path': str(path), 'backup': str(backup), 'prefix': sys.prefix}))
        return
    output.mkdir(parents=True, exist_ok=False)
    from tests.test_native_shared_execution import make_case, launch_case
    import pytest
    if mode == 'light':
        from data_sheets_schema import native_environment_manifest as environment
        value = json.loads(Path(sys.argv[3]).read_bytes())
        profile = cProfile.Profile()
        started = time.monotonic()
        profile.runcall(environment._light_live, value)
        elapsed = time.monotonic() - started
        profile.dump_stats(str(output / 'light.pstats'))
        with (output / 'light-profile.txt').open('w') as stream:
            pstats.Stats(profile, stream=stream).sort_stats('cumulative').print_stats(70)
        (output / 'result.json').write_text(json.dumps({'seconds': elapsed, 'load': os.getloadavg()}))
        print(json.dumps({'seconds': elapsed}))
        return
    finished = threading.Event()
    main_id = threading.get_ident()
    phase = ['make_case']
    def sample():
        with (output / 'stacks.jsonl').open('x', buffering=1) as stream:
            while not finished.wait(0.02):
                frame = sys._current_frames().get(main_id)
                stack = []
                while frame is not None:
                    stack.append([frame.f_code.co_filename, frame.f_code.co_name, frame.f_lineno])
                    frame = frame.f_back
                stream.write(json.dumps({'time': time.time(), 'phase': phase[0], 'stack': stack}) + '\n')
    worker = threading.Thread(target=sample, daemon=True)
    worker.start()
    with (output / 'events.jsonl').open('x', buffering=1) as events:
        def event(name, **fields):
            events.write(json.dumps({'event': name, 'time': time.time(), 'load': os.getloadavg(), **fields}) + '\n')
        monitor = sys.monitoring
        monitor.use_tool_id(4, 'launch-cost-observer')
        selected = {
            'native_environment_manifest.py': {'verify', '_light_live'},
            'native_shared_registration_orchestration.py': {'verified'},
            'native_subscription_capture.py': {'_current_authority'},
        }
        active = {}
        def started(code, offset):
            filename = os.path.basename(code.co_filename)
            if code.co_name not in selected.get(filename, ()):
                return monitor.DISABLE
            frame = sys._getframe(1)
            callers = []
            while frame is not None:
                callers.append([frame.f_code.co_filename, frame.f_code.co_name, frame.f_lineno])
                frame = frame.f_back
            identity = (threading.get_ident(), code)
            active.setdefault(identity, []).append(time.monotonic())
            event('call_start', file=filename, function=code.co_name, phase=phase[0], callers=callers)
            monitor.set_local_events(4, code, monitor.events.PY_RETURN)
        def returned(code, offset, value):
            stack = active.get((threading.get_ident(), code))
            if stack:
                event('call_end', file=os.path.basename(code.co_filename), function=code.co_name,
                      phase=phase[0], seconds=time.monotonic() - stack.pop())
        monitor.register_callback(4, monitor.events.PY_START, started)
        monitor.register_callback(4, monitor.events.PY_RETURN, returned)
        monitor.set_events(4, monitor.events.PY_START)
        case = None
        try:
            event('make_case_start')
            case = make_case(output / 'case')
            guard = json.loads(case['kwargs']['subscription_guard_path'].read_bytes())
            event('launch_entry', guard=guard)
            phase[0] = 'launch'
            try:
                with pytest.MonkeyPatch.context() as patch:
                    result = launch_case(case, patch)
                event('launch_return', result=result)
            except Exception as exc:
                event('launch_error', error=type(exc).__name__ + ': ' + str(exc))
                import traceback
                traceback.print_exc()
            phase[0] = 'light'
            from data_sheets_schema import native_environment_manifest as environment
            manifests = list((output / 'case').rglob('environment-manifest.json'))
            value = json.loads(manifests[0].read_bytes())
            profile = cProfile.Profile()
            started = time.monotonic()
            profile.runcall(environment._light_live, value)
            elapsed = time.monotonic() - started
            profile.dump_stats(str(output / 'light.pstats'))
            with (output / 'light-profile.txt').open('w') as stream:
                pstats.Stats(profile, stream=stream).sort_stats('cumulative').print_stats(70)
            event('light_profile', seconds=elapsed)
        finally:
            monitor.set_events(4, 0)
            for identity in active:
                monitor.set_local_events(4, identity[1], 0)
            monitor.free_tool_id(4)
            finished.set()
            worker.join()
            event('finished')


if __name__ == '__main__':
    main()

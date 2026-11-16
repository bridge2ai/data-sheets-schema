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
            finished.set()
            worker.join()
            event('finished')


if __name__ == '__main__':
    main()

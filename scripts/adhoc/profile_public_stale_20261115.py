"""Profile public preparation, 2026-11-15, for the stale-observation assignment.

Inputs: copied isolated venv and scratch path. Outputs: profile, phase log,
case artifacts. No provider calls. Run from repository root with PYTHONPATH=src.
"""
import cProfile
import json
import os
from pathlib import Path
import pstats
import signal
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[2]
sys.path[0] = str(ROOT)

def main():
    mode, scratch_arg = sys.argv[1:3]
    scratch = Path(scratch_arg).resolve()
    if mode == 'configure':
        path = scratch / 'isolated-venv/lib/python3.13/site-packages/data_sheets_schema.pth'
        backup = path.with_name(path.name + '.bak-public-stale-20261115')
        if backup.exists():
            raise ValueError('already configured')
        backup.write_bytes(path.read_bytes())
        path.write_text(str(ROOT / 'src') + '\n')
        assert path.read_text() == str(ROOT / 'src') + '\n'
        print(json.dumps({'path': str(path), 'backup': str(backup), 'undo': 'restore adjacent backup'}))
        return
    if mode == 'bounded':
        seconds = int(sys.argv[3])
        command = sys.argv[4:]
        start = time.monotonic()
        child = subprocess.Popen(command, start_new_session=True)
        try:
            code = child.wait(timeout=seconds)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGTERM)
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()
            code = 124
        print(json.dumps({'command': command, 'elapsed': time.monotonic()-start, 'returncode': code}), flush=True)
        sys.exit(code)
    if (scratch / mode).exists():
        raise ValueError('diagnostic case already exists; preserve prior evidence')
    from tests.test_native_shared_execution import make_case
    if mode == 'phases':
        monitoring = sys.monitoring
        tool = 4
        monitoring.use_tool_id(tool, 'public-stale-phase-profile')
        selected = {
            'native_environment_manifest.py': {'write', 'generate', 'verify', '_light_live'},
            'native_shared_fixture.py': {'build_native_fixture'},
            'test_native_shared_execution.py': {'make_case'},
            'native_synthetic_evidence.py': {'runtime_for', 'bound_permission_for', 'authority_for'},
            'native_execution_registration_v2.py': {'prepare', 'prepare_synthetic'},
            'native_shared_registration_orchestration.py': {'verified', 'synthetic_registration'},
            'native_shared_controller_orchestration.py': {'compose', 'reconstruct_composition'},
            'native_subscription_capture.py': {'_current_authority'},
        }
        active = {}
        stream = (scratch / 'phases.jsonl').open('w', buffering=1)
        origin = time.monotonic()
        def start(code, offset):
            name = Path(code.co_filename).name
            if code.co_name not in selected.get(name, ()):
                return monitoring.DISABLE
            active.setdefault(code, []).append(time.monotonic())
            monitoring.set_local_events(tool, code, monitoring.events.PY_RETURN)
        def finish(code, offset, value):
            stack = active.get(code)
            if stack:
                begin = stack.pop()
                stream.write(json.dumps({'file': Path(code.co_filename).name, 'function': code.co_name,
                    'start': begin-origin, 'seconds': time.monotonic()-begin}) + '\n')
        monitoring.register_callback(tool, monitoring.events.PY_START, start)
        monitoring.register_callback(tool, monitoring.events.PY_RETURN, finish)
        monitoring.set_events(tool, monitoring.events.PY_START)
        try:
            case = make_case(scratch / mode)
            guard = json.loads(case['kwargs']['subscription_guard_path'].read_text())
            print(json.dumps({'seconds': time.monotonic()-origin, 'guard': guard,
                              'ready_wall_ns': time.time_ns()}), flush=True)
        finally:
            monitoring.set_events(tool, 0)
            for code in active:
                monitoring.set_local_events(tool, code, 0)
            monitoring.free_tool_id(tool)
            stream.close()
        return
    profile = cProfile.Profile()
    def interrupted(signum, frame):
        raise TimeoutError('external watchdog stopped profiling')
    signal.signal(signal.SIGTERM, interrupted)
    started = time.monotonic()
    profile.enable()
    try:
        case = make_case(scratch / mode)
        print(json.dumps({'phase': 'make_case', 'seconds': time.monotonic()-started,
                          'guard': str(case['kwargs']['subscription_guard_path'])}), flush=True)
    except BaseException:
        traceback.print_exc()
        raise
    finally:
        profile.disable()
        profile.dump_stats(str(scratch / (mode + '.prof')))
        with (scratch / (mode + '-profile.txt')).open('w') as stream:
            pstats.Stats(profile, stream=stream).sort_stats('cumulative').print_stats(100)
        print(json.dumps({'phase': 'profile_complete', 'seconds': time.monotonic()-started}), flush=True)

if __name__ == '__main__':
    main()

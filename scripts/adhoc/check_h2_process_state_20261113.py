#!/usr/bin/env python3
"""Check independent own-child state in the CI sandbox, 2026-11-13.
Issues 6201/6202. Inputs: installed psutil and the exact offline sandbox.
Output: retained zombie/parent observation before reaping, no CPU/load data.
No privileged binary, sandbox escape, network or native-agent call.
"""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def runner_module():
    path = Path(__file__).with_name('run_h2_integration_20261113.py')
    spec = importlib.util.spec_from_file_location('integration_runner', path)
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    return runner


def worker():
    runner = runner_module()
    sys.path.append(str(runner.dependency_site()))
    import psutil
    child = subprocess.Popen([sys.executable, '-S', '-P', '-B', str(Path(__file__).resolve()), '--exit-child'])
    try:
        process = psutil.Process(child.pid)
        until = time.monotonic() + 5
        while process.status() != psutil.STATUS_ZOMBIE:
            assert time.monotonic() < until, 'child never became an unreaped zombie'
            time.sleep(.01)
        assert process.ppid() == os.getpid()
        assert child.returncode is None
        result = {'zombie_observed_before_reap': True, 'parent_pid_verified': True,
                  'child_pid': child.pid, 'parent_pid': os.getpid(),
                  'psutil_origin': psutil.__file__, 'cpu_or_load_queried': False}
    finally:
        if child.poll() is None:
            child.kill()
        child.wait()
    print(json.dumps(result))


if __name__ == '__main__':
    if '--exit-child' in sys.argv:
        raise SystemExit(0)
    if '--worker' in sys.argv:
        worker()
    else:
        runner = runner_module()
        out = runner.SCRATCH_BASE / 'process-state-preflight'
        out.mkdir(exist_ok=False)
        profile = out / 'network-denied.sb'
        profile.write_text(runner.sandbox_profile(allow_loopback=True))
        command = ['/usr/bin/sandbox-exec', '-f', str(profile), sys.executable,
                   '-S', '-P', '-B', str(Path(__file__).resolve()), '--worker']
        result = subprocess.run(command, capture_output=True, text=True, timeout=15)
        runner.save(out / 'result.json', {'command': command, 'returncode': result.returncode,
            'stdout': result.stdout, 'stderr': result.stderr, 'profile_sha256': runner.digest(profile)})
        assert result.returncode == 0, result.stderr
        print(result.stdout.strip())

#!/usr/bin/env python3
"""Validate macOS CI process-state checks without setuid, 2026-11-13.
Issues 6201/6202. Input: exact /bin/ps bytes and the offline runner sandbox.
Output: owned executable with privilege bits cleared, hashes and own-PID state.
No CPU/load query, sandbox escape, network or native-agent invocation.
"""
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess

runner_path = Path(__file__).with_name('run_h2_integration_20261113.py')
spec = importlib.util.spec_from_file_location('integration_runner', runner_path)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
out = runner.SCRATCH_BASE / 'unprivileged-ps-preflight'
out.mkdir(exist_ok=False)
source, copy = Path('/bin/ps'), out / 'ps'
copy.write_bytes(source.read_bytes())
copy.chmod(0o755)
assert runner.digest(source) == runner.digest(copy)
assert not copy.stat().st_mode & (stat.S_ISUID | stat.S_ISGID)
profile = out / 'network-denied.sb'
profile.write_text(runner.sandbox_profile(allow_loopback=True))
command = ['/usr/bin/sandbox-exec', '-f', str(profile), str(copy),
           '-p', str(os.getpid()), '-o', 'pid=,stat=']
result = subprocess.run(command, capture_output=True, text=True, timeout=10)
record = {'command': command, 'returncode': result.returncode,
    'stdout': result.stdout, 'stderr': result.stderr,
    'source_sha256': runner.digest(source), 'copy_sha256': runner.digest(copy),
    'source_mode': oct(stat.S_IMODE(source.stat().st_mode)),
    'copy_mode': oct(stat.S_IMODE(copy.stat().st_mode)),
    'profile_sha256': runner.digest(profile), 'cpu_or_load_queried': False}
runner.save(out / 'result.json', record)
assert result.returncode == 0, result.stderr
assert result.stdout.split()[0] == str(os.getpid())
print(json.dumps(record, indent=2))

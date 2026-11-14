#!/usr/bin/env python3
"""Share and exercise copied-process cleanup for issue 6208 review F3, 2026-11-14.
Inputs: two synthetic sequence test files. Outputs: shared cleanup helper and
failure-path regressions. No tests, processes, commits or provider calls run.
"""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
path = ROOT / 'tests/test_native_launch_sequence.py'
raw = path.read_text()
anchor = '\n\ndef run_sequence(arguments):\n'
helper = '''\n\ndef finish_copied_process(child):
    """Reap only a test-owned copied-package witness, including failed tests."""
    if child.poll() is None:
        try:
            child.send_signal(signal.SIGTERM)
        except ProcessLookupError:
            pass
    try:
        child.communicate(timeout=20)
    except subprocess.TimeoutExpired:
        try:
            child.kill()
        except ProcessLookupError:
            pass
        child.communicate()
'''
assert anchor in raw and 'def finish_copied_process' not in raw
raw = raw.replace(anchor, helper + anchor, 1)
old = """        # Test-only cleanup of this exact copied-package process. A failing
        # witness must not leave its synthetic supervisor or pipes alive.
        if child.poll() is None:
            child.send_signal(signal.SIGTERM)
        try:
            child.communicate(timeout=20)
        except subprocess.TimeoutExpired:
            child.kill()
            child.communicate()
"""
assert old in raw
raw = raw.replace(old, "        finish_copied_process(child)\n", 1)
compile(raw, str(path), 'exec')
path.write_text(raw)
path = ROOT / 'tests/test_native_launch_sequence_signals.py'
raw = path.read_text()
old = """        finally:
            if process.poll() is None:
                # Test-only escape: ask the copied supervisor to stop normally.
                # The fake command also has its own finite readiness watchdog.
                process.send_signal(signal.SIGTERM)
                process.wait(timeout=20)
"""
new = """        finally:
            # Test-only cleanup of the exact copied supervisor. Its fake child
            # also has a finite readiness watchdog; no real controller runs.
            fixture.finish_copied_process(process)
"""
assert old in raw
raw = raw.replace(old, new, 1)
compile(raw, str(path), 'exec')
path.write_text(raw)
print('Added shared copied-process cleanup; no tests executed.')

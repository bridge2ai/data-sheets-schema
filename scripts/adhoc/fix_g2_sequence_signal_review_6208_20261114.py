#!/usr/bin/env python3
"""Correct recorded issue-6208 review findings F1-F3, 2026-11-14.
Inputs: reviewed sequence implementation and synthetic signal fixtures.
Outputs: latch-only handlers, coherent final signal cutoff, reaped test witness.
No tests, commits, provider calls or native commands are run.
"""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
path = ROOT / 'src/data_sheets_schema/native_launch_sequence.py'
raw = path.read_text()
raw = raw.replace("MAX_COMMAND_OUTPUT_BYTES = 32 * 1024 * 1024\n", "MAX_COMMAND_OUTPUT_BYTES = 32 * 1024 * 1024\nCOMMAND_WAIT_POLL_SECONDS = 0.1\n", 1)
raw = raw.replace("    by this parent-side guarantee. Signals after the immutable sequence record\n    is serialized are deferred but cannot be added retroactively to its bytes.\n", "    by this parent-side guarantee. The outcome uses one received-signal tuple\n    captured after the completion clock sample and before record serialization.\n    Later signals are deferred and cannot alter the already decided outcome.\n", 1)
raw = raw.replace("        # Latch before the call: another Python signal may arrive inside it.\n", "        # Ordinary control only: the handler never polls or signals a PID.\n        # Latch before the call; another signal may arrive while it executes.\n", 1)
raw = raw.replace("            # A signal handler must not interrupt the controller's cleanup.\n            # Keep bounded diagnostics; never arbitrary exception text.\n", "            # Keep cleanup running with bounded diagnostics, never arbitrary\n            # exception text. A failed delivery does not permit a second send.\n", 1)
raw = raw.replace("    def receive(self, signum, _frame):\n        self.received.append(signum)\n        self._forward()\n", "    def receive(self, signum, _frame):\n        # No process API here: waitpid may have reaped the child while Popen's\n        # returncode is not set yet. Sending from this handler could hit a\n        # recycled PID. Ordinary control forwards only between wait polls.\n        self.received.append(signum)\n", 1)
old = """        self._child = child
        self._forward()  # Deliver a signal latched while Popen was constructing.
        try:
            while True:
                try:
                    return child.wait()
                except InterruptedError:
                    continue
                except KeyboardInterrupt:
                    # Defensive support for an independently raised interrupt;
                    # our installed handlers themselves never raise.
                    self.receive(signal.SIGINT, None)
"""
new = """        self._child = child
        try:
            while True:
                self._forward()  # Includes a signal latched during Popen.
                try:
                    return child.wait(timeout=COMMAND_WAIT_POLL_SECONDS)
                except (subprocess.TimeoutExpired, InterruptedError):
                    # Polling bounds signal-forwarding latency; it is not an
                    # overall cleanup deadline and never authorizes a kill.
                    continue
                except KeyboardInterrupt:
                    # Defensive support for an independently raised interrupt;
                    # our installed handlers themselves never raise.
                    self.receive(signal.SIGINT, None)
"""
assert old in raw
raw = raw.replace(old, new, 1)
raw = raw.replace("            # No Popen context, communicate(), wait timeout, kill or terminate:\n            # the command owns its cleanup and registered execution deadline.\n", "            # No overall cleanup timeout, Popen context, kill or terminate:\n            # the command owns its cleanup and registered execution deadline.\n", 1)
raw = raw.replace("            record['stop_reason'] = ('signal ' + str(interrupts.received[0])\n                                     if interrupts.received else type(exc).__name__)\n", "            record['stop_reason'] = type(exc).__name__\n", 1)
old = """        finally:
            if interrupts.received:
                record['status'] = 'stopped'
                if record['stop_reason'] is None:
                    record['stop_reason'] = 'signal ' + str(interrupts.received[0])
            record['signals_received'] = list(interrupts.received)
            record['signal_forwarding_errors'] = list(interrupts.forwarding_errors)
            record['completed_at'] = _utc_now()
"""
new = """        finally:
            record['completed_at'] = _utc_now()
            # This single immutable tuple is the outcome's signal cutoff.
            # A signal during later serialization/persistence cannot create
            # contradictory status, reason and received-signal fields.
            received = tuple(interrupts.received)
            if received:
                record['status'] = 'stopped'
                record['stop_reason'] = 'signal ' + str(received[0])
            record['signals_received'] = list(received)
            record['signal_forwarding_errors'] = list(interrupts.forwarding_errors)
            record['signal_recording_cutoff'] = 'after completion clock sample, before immutable record serialization'
"""
assert old in raw
raw = raw.replace(old, new, 1)
compile(raw, str(path), 'exec')
path.write_text(raw)

path = ROOT / 'tests/test_native_launch_sequence.py'
raw = path.read_text()
raw = raw.replace('import os\nimport subprocess\n', 'import os\nimport signal\nimport subprocess\n', 1)
raw = raw.replace("return SimpleNamespace(returncode=code, wait=lambda: code, poll=lambda: code,", "return SimpleNamespace(returncode=code, wait=lambda timeout: code, poll=lambda: code,", 1)
old = """    stdout, stderr = child.communicate(timeout=20)
    assert child.returncode == 0, stderr
"""
new = """    try:
        stdout, stderr = child.communicate(timeout=20)
        assert child.returncode == 0, stderr
    finally:
        # Test-only cleanup of this exact copied-package process. A failing
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
raw = raw.replace(old, new, 1)
compile(raw, str(path), 'exec')
path.write_text(raw)

path = ROOT / 'tests/test_native_launch_sequence_signals.py'
raw = path.read_text()
old = """        def wait():
            assert len(synced) == before_sync, 'streams must sync only after child reap'
            if when == 'wait':
                os.kill(os.getpid(), signal.SIGINT)
            os.kill(os.getpid(), signal.SIGTERM)
            kwargs['stderr'].write(b'cleanup completed\\n')
            waited.append(True)
            child.returncode = 23
            return child.returncode
"""
new = """        polls = []
        def wait(timeout):
            assert timeout == seq.COMMAND_WAIT_POLL_SECONDS
            assert len(synced) == before_sync, 'streams must sync only after child reap'
            polls.append(True)
            if len(polls) == 1:
                if when == 'wait':
                    os.kill(os.getpid(), signal.SIGINT)
                os.kill(os.getpid(), signal.SIGTERM)
                raise subprocess.TimeoutExpired(args[0], timeout)
            kwargs['stderr'].write(b'cleanup completed\\n')
            waited.append(True)
            child.returncode = 23
            return child.returncode
"""
assert old in raw
raw = raw.replace(old, new, 1)
raw = raw.replace('wait=lambda: waited.append(True) or 7', 'wait=lambda timeout: waited.append(True) or 7', 1)
raw = raw.replace('    def wait():\n        waits.append(True)\n', '    def wait(timeout):\n        assert timeout == seq.COMMAND_WAIT_POLL_SECONDS\n        waits.append(True)\n', 1)
compile(raw, str(path), 'exec')
path.write_text(raw)
print('Corrected the three recorded sequence-signal review findings without running tests.')

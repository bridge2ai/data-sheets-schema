#!/usr/bin/env python3
"""Implement issue 6208 sequence-owned interruption cleanup, 2026-11-14.
Inputs: native_launch_sequence.py at the reviewed G2 base.
Output: the sequence implementation; synthetic tests are authored separately.
No tests, commits, subprocesses or provider/native calls are performed.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
path = ROOT / 'src/data_sheets_schema/native_launch_sequence.py'
raw = path.read_text()
assert 'class _SequenceSignals:' not in raw
raw = raw.replace('import re\nimport subprocess\nimport sys\n',
                  'import re\nimport signal\nimport subprocess\nimport sys\nimport threading\n')
start = raw.index('def _run_step(')
stop = raw.index('\n\ndef parser():', start)
raw = raw[:start] + '''class _SequenceSignals:
    """Defer interruption until the owned command has reaped and synced.

    The first signal is forwarded once to the exact command PID. Its fresh
    session prevents a terminal signal from reaching both parent and child.
    Child startup before its own cleanup handler is installed is not covered
    by this parent-side guarantee. Signals after the immutable sequence record
    is serialized are deferred but cannot be added retroactively to its bytes.
    """

    def __init__(self):
        self.received = []
        self.forwarding_errors = []
        self._child = None
        self._forwarded = False
        self._previous = {}

    def _forward(self):
        if self._child is None or not self.received or self._forwarded:
            return
        # Latch before the call: another Python signal may arrive inside it.
        self._forwarded = True
        try:
            self._child.send_signal(self.received[0])
        except ProcessLookupError:
            pass  # The command exited before delivery; it is still reaped.
        except BaseException as exc:
            # A signal handler must not interrupt the controller's cleanup.
            # Keep bounded diagnostics; never arbitrary exception text.
            self.forwarding_errors.append(type(exc).__name__)

    def receive(self, signum, _frame):
        self.received.append(signum)
        self._forward()

    def check(self):
        if self.received:
            raise KeyboardInterrupt('native sequence received signal ' + str(self.received[0]))

    def wait(self, child):
        self._child = child
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
        finally:
            self._child = None

    def __enter__(self):
        if threading.current_thread() is not threading.main_thread():
            raise ValueError('native sequence requires main-thread signal ownership')
        self._previous = {sig: signal.getsignal(sig) for sig in (signal.SIGINT, signal.SIGTERM)}
        try:
            for sig in self._previous:
                signal.signal(sig, self.receive)
        except BaseException:
            for sig, handler in self._previous.items():
                signal.signal(sig, handler)
            raise
        return self

    def __exit__(self, *_error):
        for sig, handler in self._previous.items():
            signal.signal(sig, handler)


def _run_step(command, flags, output, steps, interrupts):
    interrupts.check()
    argv = [sys.executable, '-I', '-B', '-c', BOOTSTRAP, str(SOURCE_ROOT / 'src'), command, *flags]
    stderr_path = output.with_suffix('.stderr.txt')
    step = {'step': command, 'argv': argv, 'started_at': _utc_now(),
            'completed_at': None, 'return_code': None, 'output_path': str(output),
            'stderr_path': str(stderr_path)}
    # Reserve both outputs before the command, including on spawn failure.
    with _new(output) as stdout, _new(stderr_path) as stderr:
        steps.append(step)
        try:
            interrupts.check()
            child = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
                                     cwd=SOURCE_ROOT, env=dict(CHILD_ENV), start_new_session=True)
            # No Popen context, communicate(), wait timeout, kill or terminate:
            # the command owns its cleanup and registered execution deadline.
            step['return_code'] = interrupts.wait(child)
        finally:
            stdout.flush(); stderr.flush()
            os.fsync(stdout.fileno()); os.fsync(stderr.fileno())
            step['completed_at'] = _utc_now()
    interrupts.check()
    if step['return_code'] != 0:
        raise ValueError(command + ' exited nonzero; see retained command output')
    raw = guard.read_regular(output, limit=MAX_COMMAND_OUTPUT_BYTES)
    step['output_sha256'] = guard.sha(raw)
    try:
        doc = guard.strict_json(raw)
    except ValueError as exc:
        raise ValueError(command + ' output is not strict JSON') from exc
    if type(doc) is not dict or doc.get('command') != command:
        raise ValueError(command + ' output lacks its exact command identity')
    body = doc.get('result')
    if type(body) is not dict or not body:
        raise ValueError(command + ' output lacks its result object')
    return body
''' + raw[stop:]
raw = raw.replace("    sequence = None\n    try:\n", "    sequence = None\n    with _SequenceSignals() as interrupts:\n        try:\n", 1)
start = raw.index('        inputs = {_path(', raw.index('def _run_verified'))
stop = raw.index("    return 0 if record['status']", start)
body = raw[start:stop]
body = '\n'.join('    ' + line if line else line for line in body.split('\n'))
raw = raw[:start] + body + raw[stop:]
raw = raw.replace("            sequence = sequence_candidate\n", "            sequence = sequence_candidate\n            interrupts.check()\n", 1)
raw = raw.replace("            from .native_sequence_start import claim\n", "            interrupts.check()\n            from .native_sequence_start import claim\n", 1)
raw = raw.replace("outputs[0], record['steps'])", "outputs[0], record['steps'], interrupts)", 1)
raw = raw.replace("outputs[1], record['steps'])", "outputs[1], record['steps'], interrupts)", 1)
raw = raw.replace("outputs[2], record['steps'])", "outputs[2], record['steps'], interrupts)", 1)
raw = raw.replace("            record['status'] = 'completed'\n        except Exception as exc:\n", "            interrupts.check()\n            record['status'] = 'completed'\n        except BaseException as exc:\n", 1)
raw = raw.replace("            record['stop_reason'] = type(exc).__name__\n", "            record['stop_reason'] = ('signal ' + str(interrupts.received[0])\n                                     if interrupts.received else type(exc).__name__)\n", 1)
raw = raw.replace("        finally:\n            record['completed_at'] = _utc_now()\n", "        finally:\n            if interrupts.received:\n                record['status'] = 'stopped'\n                if record['stop_reason'] is None:\n                    record['stop_reason'] = 'signal ' + str(interrupts.received[0])\n            record['signals_received'] = list(interrupts.received)\n            record['signal_forwarding_errors'] = list(interrupts.forwarding_errors)\n            record['completed_at'] = _utc_now()\n", 1)
compile(raw, str(path), 'exec')
path.write_text(raw)
print(path)

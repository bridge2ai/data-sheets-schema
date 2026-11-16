"""Synthetic local probe transport for source-verified host-power modules.

Keep the verified probe, parser and AC refusal callable identities unchanged.
Only the subprocess interface consumes the fixture's invented host readings.
"""
import os


class SyntheticPowerSubprocess:
    def __init__(self, ambient):
        self.ambient = ambient

    def __getattr__(self, name):
        return getattr(self.ambient.subprocess, name)

    def Popen(self, argv, **kwargs):
        if argv[0] not in ('/usr/bin/pmset', '/usr/sbin/ioreg'):
            raise AssertionError('unexpected synthetic host command')
        reading = self.ambient._local(argv, limit=16384)
        if reading.get('status') != 'read':
            reason = reading.get('reason')
            if reason == 'TimeoutError':
                raise TimeoutError('invented host probe timeout')
            raise OSError('invented unavailable host probe')
        return SyntheticPowerProcess(reading)


class SyntheticPowerProcess:
    def __init__(self, reading):
        raw = reading['text'].encode()
        if len(raw) > 4096:
            raise AssertionError('invented host reading exceeds fixture pipe bound')
        reader, writer = os.pipe()
        self.stdout = os.fdopen(reader, 'rb')
        try:
            os.write(writer, raw)
        finally:
            os.close(writer)
        self.returncode = reading.get('returncode', 0)

    def poll(self):
        return self.returncode

    def wait(self, timeout=None):
        return self.returncode

    def kill(self):
        raise AssertionError('completed synthetic host probe cannot need killing')

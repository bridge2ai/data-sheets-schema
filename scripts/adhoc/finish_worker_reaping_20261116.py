"""Apply Darwin-safe prepared-worker cleanup for D156, 2026-11-16.

Inputs/outputs: native_launch_sequence.py and its prepared-sequence tests.
Uses the existing transport's exited-leader refusal rule without changing pins.
Run once after active validation releases the source snapshot.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
source = ROOT / 'src/data_sheets_schema/native_launch_sequence.py'
tests = ROOT / 'tests/test_native_prepared_sequence.py'


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('unexpected source shape')
    return text.replace(old, new, 1)


text = source.read_text()
text = replace_once(text, '    def close(self):\n', '''    def _kill_group(self):
        try:
            os.killpg(self.child.pid, signal.SIGKILL)
            return
        except ProcessLookupError:
            return
        except PermissionError as error:
            refusal = error
        # Darwin can refuse a group containing only its zombie leader. Match
        # the existing transport rule: verify exit before reaping, then only
        # probe. A remaining or recycled group is a refusal, never a target.
        if self._exit_status() is None:
            raise refusal
        self.child.wait()
        deadline = time.monotonic() + 2
        while True:
            try:
                os.killpg(self.child.pid, 0)
            except ProcessLookupError:
                return
            except PermissionError:
                if time.monotonic() < deadline:
                    time.sleep(0.02)
                    continue
            raise refusal

    def close(self):
''')
text = replace_once(text, '''                    if not self.complete:
                        try:
                            os.killpg(self.child.pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
''', '''                    if not self.complete:
                        self._kill_group()
''')
test_text = tests.read_text()
test_text = replace_once(test_text,
    "    owned.child = SimpleNamespace(pid=123, wait=lambda: reaped.append(True) or 9)\n",
    "    owned.child = SimpleNamespace(pid=123, wait=lambda: reaped.append(True) or 9)\n"
    "    owned._exit_status = lambda: None\n")
test_text += '''

def test_cleanup_never_signals_an_unverifiable_group_after_reaping(tmp_path, monkeypatch):
    owned = sequence._PreparedStep([], tmp_path / 'worker.json', [], sequence._SequenceSignals())
    reaped, calls = [], []
    owned.child = SimpleNamespace(pid=123, wait=lambda: reaped.append(True) or 7)
    owned._exit_status = lambda: 7
    def signal_group(pid, signum):
        calls.append(signum)
        if signum:
            raise PermissionError('synthetic group refusal')
        assert reaped
    monkeypatch.setattr(sequence.os, 'killpg', signal_group)
    with pytest.raises(PermissionError, match='synthetic group refusal'):
        owned.close()
    assert calls == [signal.SIGKILL, 0]
    assert owned.step['return_code'] == 7
'''
source.write_text(text)
tests.write_text(test_text)

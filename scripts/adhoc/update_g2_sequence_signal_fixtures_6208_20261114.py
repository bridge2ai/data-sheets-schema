#!/usr/bin/env python3
"""Update synthetic sequence fixtures for issue 6208, 2026-11-14.
Inputs: launch sequence and start test fixtures after issue 6215.
Outputs: Popen fakes and an outer real-Popen witness; runs no tests or commands.
"""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
path = ROOT / 'tests/test_native_launch_sequence.py'
raw = path.read_text()
raw = raw.replace('from pathlib import Path\n', 'from pathlib import Path\nfrom types import SimpleNamespace\n', 1)
raw = raw.replace('REAL_RUN = subprocess.run', 'REAL_POPEN = subprocess.Popen', 1)
raw = raw.replace("monkeypatch.setattr(seq.subprocess, 'run', refuse)", "monkeypatch.setattr(seq.subprocess, 'Popen', refuse)", 1)
raw = raw.replace("assert kwargs['stdin'] == subprocess.DEVNULL and kwargs['check'] is False", "assert kwargs['stdin'] == subprocess.DEVNULL and kwargs['start_new_session'] is True\n        assert 'check' not in kwargs", 1)
raw = raw.replace("        return subprocess.CompletedProcess(command, 17 if fail == name else 0)\n    monkeypatch.setattr(seq.subprocess, 'run', run)", "        code = 17 if fail == name else 0\n        return SimpleNamespace(returncode=code, wait=lambda: code, poll=lambda: code,\n                               send_signal=lambda signum: None)\n    monkeypatch.setattr(seq.subprocess, 'Popen', run)", 1)
old = """    result = REAL_RUN([sys.executable, '-I', '-B', '-c', bootstrap, str(root / 'src'), 'data_sheets_schema.' + entry_module, *argv(p)],
                      env={'PRIVATE_TOKEN': 'secret', 'PYTHONPATH': '/foreign'},
                      cwd=root, capture_output=True, timeout=20)
    assert result.returncode == 0, result.stderr
"""
new = """    child = REAL_POPEN([sys.executable, '-I', '-B', '-c', bootstrap, str(root / 'src'), 'data_sheets_schema.' + entry_module, *argv(p)],
                       env={'PRIVATE_TOKEN': 'secret', 'PYTHONPATH': '/foreign'},
                       cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = child.communicate(timeout=20)
    assert child.returncode == 0, stderr
"""
assert old in raw
raw = raw.replace(old, new, 1)
compile(raw, str(path), 'exec')
path.write_text(raw)
path = ROOT / 'tests/test_native_sequence_start.py'
raw = path.read_text()
assert 'fake = seq.subprocess.run' in raw
raw = raw.replace('fake = seq.subprocess.run', 'fake = seq.subprocess.Popen', 1)
raw = raw.replace("monkeypatch.setattr(seq.subprocess, 'run', child)", "monkeypatch.setattr(seq.subprocess, 'Popen', child)", 1)
compile(raw, str(path), 'exec')
path.write_text(raw)
print('Updated only the two sequence subprocess fixture seams.')

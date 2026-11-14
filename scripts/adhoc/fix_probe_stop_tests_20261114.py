"""Update offline signal regressions for issue 6236, 2026-11-14.
Input/output: tests/test_native_permission_probe.py; no runtime execution.
"""
from pathlib import Path

path = Path('tests/test_native_permission_probe.py')
text = path.read_text().replace('pytest.raises(InterruptedError, match="permission probe stopped")',
                              'pytest.raises(probe.ProbeStopped, match="permission probe stopped")')
text = text.replace('"overflow", "sigterm"]', '"overflow", "sigterm", "cleanup_sigterm"]')
text = text.replace('def close(self):\n            self.control_shutdown_complete = True',
                    'def close(self):\n            if mode == "cleanup_sigterm":\n                probe.signal.raise_signal(probe.signal.SIGTERM)\n            self.control_shutdown_complete = True')
text = text.replace('pytest.raises((ValueError, TimeoutError, InterruptedError))',
                    'pytest.raises((ValueError, TimeoutError, probe.ProbeStopped))')
path.write_text(text)

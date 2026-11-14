"""6233, 2026-11-14: update explicit runtime fixtures and synthetic peer pin.

Input/output: named repository fixtures; no execution or external calls.
"""
from pathlib import Path
import hashlib
import re

root = Path(__file__).resolve().parents[2]
for name in ('tests/utils/native_synthetic_evidence.py',
             'tests/test_native_execution_registration_v2.py',
             'tests/test_native_synthetic_profiles.py',
             'tests/test_native_u4b_runtime.py',
             'tests/test_native_recorder_env.py'):
    path = root / name
    text = path.read_text()
    marker = "'PYSTOW_HOME':"
    assert marker in text
    text = text.replace(marker, "'BASH_DEFAULT_TIMEOUT_MS': '600000', 'BASH_MAX_TIMEOUT_MS': '600000', " + marker)
    for obj in ('old', 'legacy'):
        marker = f"    {obj}['environment'].pop('PYSTOW_HOME')"
        if marker in text:
            text = text.replace(marker, marker + f"\n    {obj}['environment'].pop('BASH_DEFAULT_TIMEOUT_MS')\n    {obj}['environment'].pop('BASH_MAX_TIMEOUT_MS')")
    text = text.replace('test_explicit_synthetic_profile_is_distinct_and_preserves_900_180',
                        'test_explicit_synthetic_profile_is_distinct_and_registers_bash_timeout')
    text = text.replace("    assert b'timeout=180)' in raw", "    assert b\"timeout=int(os.environ['BASH_DEFAULT_TIMEOUT_MS']) / 1000\" in raw")
    path.write_text(text)
path = root / 'src/data_sheets_schema/native_runtime_profiles.py'
digest = hashlib.sha256((root / 'tests/fixtures/native_shared_execution/fake_cli.py').read_bytes()).hexdigest()
path.write_text(re.sub(r"SYNTHETIC_PEER_SHA256 = '[a-f0-9]+'", f"SYNTHETIC_PEER_SHA256 = '{digest}'", path.read_text()))
print('synthetic_peer_sha256', digest)

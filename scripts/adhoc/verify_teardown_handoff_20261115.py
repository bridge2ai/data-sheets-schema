"""Issue 6214, 2026-11-15: verify final authored files and protected source bytes."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys
root = Path.cwd()
scratch = root.parent / 'scratch-callback-teardown-20261115'
protected = ['src/data_sheets_schema/shared_generation.py', 'src/data_sheets_schema/api_runner.py', 'src/download/prompts/canonical_hashes.yaml', 'tests/utils/run_spec_boundary_contracts.json']
checks = {}
for name in protected:
    old = subprocess.check_output(['git', 'show', 'b9192ff75:' + name])
    raw = Path(name).read_bytes()
    checks[name] = dict(old=hashlib.sha256(old).hexdigest(), current=hashlib.sha256(raw).hexdigest())
    assert old == raw, name
status = subprocess.check_output(['git', 'status', '--porcelain'], text=True)
files = [line[3:] for line in status.splitlines()]
for name in files:
    path = Path(name)
    assert path.is_file() and path.stat().st_size
    if path.suffix == '.py':
        ast.parse(path.read_text(), filename=name)
    if name.startswith('scripts/adhoc/') or name == 'tests/test_native_shared_callback_teardown.py':
        assert chr(64) not in path.read_text(), name
diff = subprocess.check_output(['git', 'diff', '--no-ext-diff', '--unified=0'], text=True)
assert all(chr(64) not in line for line in diff.splitlines() if line.startswith('+') and not line.startswith('+++'))
subprocess.run(['git', 'diff', '--check'], check=True)
result = dict(protected=checks, authored_files=files, added_at_signs=0)
if len(sys.argv) > 1:
    path = Path(sys.argv[1])
    raw = path.read_bytes()
    assert raw and chr(64).encode() not in raw
    result['handoff'] = dict(path=str(path), sha256=hashlib.sha256(raw).hexdigest())
(scratch / 'verification.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))

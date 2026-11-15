"""Issue 6260, 2026-11-15: summarize saved profiles and verify scoped changes.

Inputs: scratch run artifacts and this worktree. Outputs: evidence-summary.json
and verification.json in scratch. No tests, network calls or source edits.
"""
import hashlib
import json
from pathlib import Path
import pstats
import subprocess
import sys

root = Path(__file__).resolve().parents[2]
scratch = Path(sys.argv[1]).resolve(strict=True)
allowed = {
    'src/data_sheets_schema/native_catalog_reuse.py',
    'src/data_sheets_schema/native_shared_capture.py',
    'src/data_sheets_schema/native_shared_callback_capture.py',
    'src/data_sheets_schema/native_shared_observations.py',
    'src/data_sheets_schema/typed_audit.py',
    'tests/test_native_shared_callback_prefix.py',
    'tests/test_native_catalog_fast_guards.py',
}
base = 'f10e8ae20d5450d1933e624c6cb88bdd98900c9b'
changed = subprocess.check_output(['git', 'diff', '--name-only', base], cwd=root, text=True).splitlines()
untracked = subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard'],
                                   cwd=root, text=True).splitlines()
paths = sorted(set(changed + untracked))
assert all(path in allowed or path.startswith('scripts/adhoc/') for path in paths), paths
diff = subprocess.check_output(['git', 'diff', '--no-ext-diff', '--unified=0', base], cwd=root)
added = b'\n'.join(line for line in diff.splitlines() if line.startswith(b'+') and not line.startswith(b'+++'))
assert bytes([64]) not in added
for path in untracked:
    assert bytes([64]) not in (root / path).read_bytes(), path
for path in paths:
    assert (root / path).stat().st_size

summary = {}
for directory in sorted(scratch.iterdir()):
    if not directory.is_dir():
        continue
    metrics, result = directory / 'metrics.json', directory / 'result.json'
    if metrics.is_file():
        value = json.loads(metrics.read_bytes())
        profile = directory / 'costs.prof'
        if profile.is_file():
            stats = pstats.Stats(str(profile)).stats
            matches = [row for (filename, line, name), row in stats.items()
                       if filename.endswith('/native_catalog_reuse.py') and name == '_state']
            value['state_calls'] = sum(row[1] for row in matches)
            value['state_cumulative_seconds'] = sum(row[3] for row in matches)
            value['state_self_seconds'] = sum(row[2] for row in matches)
        summary[directory.name] = value
    elif result.is_file():
        value = json.loads(result.read_bytes())
        log = directory / 'output.log'
        if log.is_file():
            value['last_lines'] = log.read_text(errors='replace').splitlines()[-8:]
        summary[directory.name] = value

source = 'src/data_sheets_schema/typed_audit.py'
old = subprocess.check_output(['git', 'show', base + ':' + source], cwd=root)
verification = {
    'base': base,
    'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
    'files': {path: hashlib.sha256((root / path).read_bytes()).hexdigest() for path in paths},
    'pin_proposal': {source: {'old_sha256': hashlib.sha256(old).hexdigest(),
        'new_sha256': hashlib.sha256((root / source).read_bytes()).hexdigest(),
        'consumer': 'shared_generation.REQUEST_CODE'}},
    'scope_verified': True, 'authored_character_check': True,
}
for name, value in (('evidence-summary.json', summary), ('verification.json', verification)):
    path = scratch / name
    path.write_text(json.dumps(value, indent=2) + '\n')
    assert json.loads(path.read_bytes()) == value
    print(str(path), hashlib.sha256(path.read_bytes()).hexdigest())

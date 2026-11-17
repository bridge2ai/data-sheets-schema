"""Build D159 change inventory and integrity evidence from git and JSON.

Inputs: assignment base, working tree, scratch pin/timing outputs. Outputs:
notes/d159_limits_20261117 inventory and scratch integrity.json. 2026-11-17.
"""
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import difflib

root = Path(__file__).resolve().parents[2]
base = 'bc61c2b5ccf894a50a386044acf50ac5ee34cb54'
evidence = root.parent / 'scratch-d159-limits-20261117/evidence'
out = root / 'notes/d159_limits_20261117'
out.mkdir(exist_ok=True)
def git(*args):
    return subprocess.check_output(['git', *args], cwd=root)
def clean(s):
    return s.replace(chr(64), '[at]')
paths = git('diff', '--name-only', base).decode().splitlines()
rows = []
for path in paths:
    if path.startswith('notes/d159_limits_20261117/') or path.startswith('scripts/adhoc/'):
        continue
    old = git('show', base+':'+path).decode()
    new = (root / path).read_text()
    if path.endswith('.py'):
        ast.parse(new, filename=path)
    for i, (a, b) in enumerate(zip(old.splitlines(), new.splitlines()), 1):
        if a != b:
            rows.append({'path': path, 'line': i, 'old': clean(a.strip()), 'new': clean(b.strip())})
(out / 'changes.json').write_text(json.dumps(rows, indent=2)+'\n')
text = ['# D159 changed locations', '', 'Generated from changes.json by scripts/adhoc/report_d159_limits_20261117.py.', '',
        '| Location | Before | After |', '|---|---|---|']
def cell(s):
    return s.replace('|', '&#124;').replace('`', '&#96;')
text += ['| '+cell(x['path'])+':'+str(x['line'])+' | '+cell(x['old'])+' | '+cell(x['new'])+' |' for x in rows]
text += ['', 'Unchanged limits and review findings are recorded in scripts/adhoc/d159_review_findings_20261117.json.',
    '', 'Inventory includes grep -rnE over src, native_controls, tests, scripts, utils, .claude, workflow and runbook; grep does not consult gitignore.',
    'Historical observed timings, test-controlled short fault deadlines, caller-supplied durations, zero/nonblocking waits,',
    'numeric size/count bounds, minimum floors and age rules are not reinterpreted as production work-time defaults.', '']
(out / 'change_inventory.md').write_text('\n'.join(text))
protected = ['src/data_sheets_schema/shared_generation.py', 'src/data_sheets_schema/api_runner.py',
    'src/download/prompts/canonical_hashes.yaml', 'tests/utils/run_spec_boundary_contracts.json']
integrity = {'protected': {}, 'changed_locations': len(rows), 'changed_files': len({x['path'] for x in rows})}
for path in protected:
    raw = (root / path).read_bytes()
    integrity['protected'][path] = {'sha256': hashlib.sha256(raw).hexdigest(), 'unchanged': raw == git('show', base+':'+path)}
    assert integrity['protected'][path]['unchanged']
peer = 'tests/fixtures/native_shared_execution/fake_cli.py'
raw = (root / peer).read_bytes()
integrity['synthetic_peer'] = {'path': peer, 'sha256': hashlib.sha256(raw).hexdigest(), 'unchanged': raw == git('show', base+':'+peer)}
# Compare declarations directly; pin-gated loading is deliberately left to lead rotation.
def contracts(path, names):
    body = ast.parse((root / path).read_text()).body
    return [ast.literal_eval(next(x.value for x in body if isinstance(x, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in x.targets))) for name in names]
integrity['pure_and_historical_contracts_equal'] = contracts('src/data_sheets_schema/native_shared_permission_protocol.py', ['_CONTRACT', '_HISTORY_CONTRACT']) == contracts('notes/matched_cborg_2026-09-13/native_controls/native_control.py', ['CONTRACT', 'HISTORY_CONTRACT'])
assert integrity['pure_and_historical_contracts_equal']
(evidence / 'integrity.json').write_text(json.dumps(integrity, indent=2)+'\n')
print(json.dumps(integrity, indent=2))

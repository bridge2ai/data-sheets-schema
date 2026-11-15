"""Issue 6259, 2026-11-15: append audit pin proposal without editing pins.

Inputs: existing controller proposal JSON and Git parent audit source.
Output: complete proposal JSON, including byte-identical classifier proof.
"""
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[2]
report = json.loads(Path(sys.argv[1]).read_text())
path = 'notes/matched_cborg_2026-09-13/audit_controls/native.py'
old = subprocess.check_output(['git', 'show', 'f10e8ae20:' + path], cwd=root)
new = (root / path).read_bytes()
def classifier(raw):
    tree = ast.parse(raw)
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'classify_command')
    return b''.join(raw.splitlines(keepends=True)[node.lineno - 1:node.end_lineno])
assert classifier(old) == classifier(new)
report['audit_classifier_unchanged_sha256'] = hashlib.sha256(classifier(new)).hexdigest()
allowlist_path = root / 'notes/matched_cborg_2026-09-13/audit_controls/checkpoint_eligibility.py'
tree = ast.parse(allowlist_path.read_bytes())
mapping = next(n.value for n in tree.body if isinstance(n, ast.Assign)
               and any(isinstance(t, ast.Name) and t.id == 'SUPPORTED_SOURCES' for t in n.targets))
mismatches = []
for key, value in zip(mapping.keys, mapping.values):
    relative = ast.literal_eval(key)
    approved = ast.literal_eval(value.args[0])
    actual = hashlib.sha256((root / 'notes/matched_cborg_2026-09-13' / relative).read_bytes()).hexdigest()
    if actual not in approved:
        mismatches.append(dict(file=relative, actual=actual))
assert [row['file'] for row in mismatches] == ['audit_controls/native.py']
report['audit_allowlist_mismatches'] = mismatches
report['proposals'].append(dict(
    file='notes/matched_cborg_2026-09-13/audit_controls/checkpoint_eligibility.py',
    field="SUPPORTED_SOURCES['audit_controls/native.py'] (append approved hash; retain historical hashes)",
    old=hashlib.sha256(old).hexdigest(), new=hashlib.sha256(new).hexdigest()))
scanner = '.claude/skills/d4d-generation-specificity-audit/scan.py'
wire = 'src/data_sheets_schema/native_shared_authority_wire.py'
report['proposals'].append(dict(file=scanner,
    field='_NATIVE_V3_RENDER_SOURCES[' + wire + ']',
    old=hashlib.sha256((root / wire).read_bytes()).hexdigest(),
    new=report['proposed_file_hashes'][wire]))
scanner_raw = (root / scanner).read_bytes()
for item in report['proposals']:
    if item['file'] == scanner:
        assert item['old'].encode() in scanner_raw
        scanner_raw = scanner_raw.replace(item['old'].encode(), item['new'].encode())
report['proposed_file_hashes'][scanner] = hashlib.sha256(scanner_raw).hexdigest()
report['scanner_scope'] = 'Keep historical base v2 table; integrated v2 changes flow into v3, plus explicit v3 wire rotation.'
print(json.dumps(report, indent=2))

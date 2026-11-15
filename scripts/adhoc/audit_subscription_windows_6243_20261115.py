"""Issue 6243 read-only pin and capture-shape audit, 2026-11-15.
Inputs: base/current guard, pin tables and private capture. Output: scratch JSON.
Only capture keys and types are retained; account values never enter the repo.
"""
import ast
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-subscription-windows-6243-20261115'
REL = 'src/data_sheets_schema/native_subscription_guard_v2.py'
BASE = 'f5c7c312f41e555c8023b880eeb3da327aa815cb'
old = hashlib.sha256(subprocess.check_output(['git', 'show', BASE + ':' + REL], cwd=ROOT)).hexdigest()
new = hashlib.sha256((ROOT / REL).read_bytes()).hexdigest()
searches = {}
for label, text in [('old_digest', old), ('guard_name', 'native_subscription_guard_v2')]:
    result = subprocess.run(['rg', '--hidden', '--no-ignore', '-n', '-F', text,
                             '--glob', '!.git', '.'], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode in (0, 1), result.stderr
    (SCRATCH / (label + '-references.txt')).write_text(result.stdout)
    searches[label] = {'returncode': result.returncode, 'lines': len(result.stdout.splitlines())}
scanner = ROOT / '.claude/skills/d4d-generation-specificity-audit/scan.py'
tables = []
for node in ast.walk(ast.parse(scanner.read_text())):
    if isinstance(node, (ast.Assign, ast.AnnAssign)):
        value = node.value
        if value is not None and ('native_subscription_guard_v2' in ast.unparse(value) or old in ast.unparse(value)):
            tables.append({'line': node.lineno, 'source': ast.unparse(node)})
controllers = {}
for path in (ROOT / 'src/data_sheets_schema').glob('native_controller_sources*.json'):
    manifest = json.loads(path.read_text())
    controllers[path.name] = [key for key, pin in manifest['modules'].items()
                             if pin['path'] == REL or pin['sha256'] == old]
# Examine the capture in place; emit no utilization, timestamps or account IDs.
path = ROOT.parent / 'scratch-lead-6243-capture-20261115/rate_limit_events.jsonl'
shapes = []
for line in path.read_bytes().splitlines():
    event = json.loads(line)
    info = event['rate_limit_info']
    shapes.append({'top_fields': {k: type(v).__name__ for k, v in info.items()},
                   'windows': {name: {k: type(v).__name__ for k, v in row.items()}
                               for name, row in info.get('unifiedWindows', {}).items()}})
result = {'base': BASE, 'old_guard_sha256': old, 'new_guard_sha256': new,
          'searches_including_ignored': searches, 'scanner_matching_assignments': tables,
          'controller_entries': controllers, 'capture_shapes': shapes}
(SCRATCH / 'audit.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))

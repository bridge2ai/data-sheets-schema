"""Issue 6260, 2026-11-15: point a copied offline venv at this worktree.

Input: copied scratch venv. Output: backed-up own-project path file, isolation
record on stdout. Does not alter the primary venv or production source checks.
"""
import hashlib
import json
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[2]
venv = Path(sys.argv[1]).resolve(strict=True)
assert venv.parent.name == 'scratch-tier-a-6260-20261115'
path = venv / 'lib/python3.13/site-packages/data_sheets_schema.pth'
backup = path.with_name(path.name + '.bak-isolation-20261115')
if backup.exists():
    raise ValueError('isolation configuration already exists')
backup.write_bytes(path.read_bytes())
path.write_text(str(root / 'src') + '\n')
assert path.read_text() == str(root / 'src') + '\n'
print(json.dumps({'venv': str(venv), 'path': str(path), 'backup': str(backup),
    'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
    'undo': 'restore the adjacent backup over the copied path file'}))

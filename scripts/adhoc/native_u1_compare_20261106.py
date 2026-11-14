"""U1 #4354, 2026-11-06: compare exact render bytes and scanner findings.
Inputs: scratch before/after artifacts; output: comparison JSON (no normalization).
"""
from pathlib import Path
import hashlib
import json
ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-native-u1'
rows = []
for before in sorted((SCRATCH / 'parity-before').glob('*.txt')):
    after = SCRATCH / 'parity-after' / before.name
    a, b = before.read_bytes(), after.read_bytes()
    rows.append({'condition': before.stem, 'bytes_before': len(a), 'bytes_after': len(b),
                 'sha256_before': hashlib.sha256(a).hexdigest(), 'sha256_after': hashlib.sha256(b).hexdigest(), 'equal': a == b})
assert len(rows) == 14, len(rows)
assert {p.name for p in (SCRATCH / 'parity-after').glob('*.txt')} == {p.name for p in (SCRATCH / 'parity-before').glob('*.txt')}
(SCRATCH / 'api-render-parity.json').write_text(json.dumps(rows, indent=2) + '\n')
print(json.dumps(rows, indent=2))
raise SystemExit(0 if all(row['equal'] for row in rows) else 1)

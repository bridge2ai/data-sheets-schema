"""Inspect U3-F full scanner facts for the seven suite failures, 2026-11-09.

Input: retained composed full JSON. Output: selected evidence in assigned
scratch and stdout, for offline repair review; no new scan or execution.
"""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[2].parent / 'scratch-native-u1u3/u3f'
doc = json.loads((root / 'validated-composed-scanner.json').read_bytes())
print(list(doc))
result = {'interactive': doc['facts']['interactive'],
          'deterministic_sys_path': doc['facts']['deterministic_sys_path']}
for key, value in doc.items():
    if isinstance(value, dict) and 'audit_continuations' in value:
        result['audit_continuations'] = value['audit_continuations']
(root / 'suite-failure-diagnostics.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps(result, indent=2))

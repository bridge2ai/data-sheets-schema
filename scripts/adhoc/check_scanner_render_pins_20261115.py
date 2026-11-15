#!/usr/bin/env python3
"""Compare every scanner render-source pin with the working bytes.

Purpose: the controller pin verifier checks only the v2 render tables; after
merging the v3 manifest branch into the native candidate (draft PR 5968), the
lead needs every _NATIVE_*_RENDER_SOURCES table checked, v3 included.
Input: checkout root (default cwd). Output: one line per mismatch, then a
count; exit 1 if any current (non-historical) table mismatches.
Written by the Claude lead, 2026-11-15.
"""
import hashlib, importlib.util, sys
from pathlib import Path
root = Path(sys.argv[1] if len(sys.argv) > 1 else '.').resolve()
spec = importlib.util.spec_from_file_location('scan', root / '.claude/skills/d4d-generation-specificity-audit/scan.py')
scan = importlib.util.module_from_spec(spec); sys.modules["scan"] = scan; spec.loader.exec_module(scan)
bad = 0
for name in sorted(n for n in dir(scan) if n.startswith('_NATIVE') and n.endswith('_SOURCES')):
    table = getattr(scan, name)
    if not isinstance(table, dict):
        continue
    for path, pinned in sorted(table.items()):
        if not (isinstance(pinned, str) and len(pinned) == 64):
            continue
        f = root / path
        actual = hashlib.sha256(f.read_bytes()).hexdigest() if f.is_file() else 'missing'
        if actual != pinned:
            print(f'{name} {path} pinned={pinned[:12]} actual={actual[:12]}')
            if 'V2_RENDER' not in name and 'V2_INTEGRATED' not in name:
                bad += 1
print('current-table mismatches:', bad)
sys.exit(1 if bad else 0)

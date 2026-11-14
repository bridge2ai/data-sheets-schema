#!/usr/bin/env python3
"""Read the explicitly assigned issues 6193-6202; 2026-11-13.
Inputs: public issue numbers named by the lead. Output: retained JSON bodies
and hashes in the local scratch evidence. Read-only GitHub GETs; no writes.
"""
import hashlib
import json
from pathlib import Path
import subprocess

BASE = Path.home() / 'agent-work/data-sheets-schema/helper2-integration-fixes-20261113/issues'
BASE.mkdir(parents=True, exist_ok=True)
for number in range(6193, 6203):
    path = BASE / f'{number}.json'
    if path.exists():
        raise FileExistsError(path)
    raw = subprocess.check_output(['gh', 'issue', 'view', str(number), '--repo',
        'bridge2ai/data-sheets-schema', '--json', 'number,title,body,url'])
    value = json.loads(raw)
    path.write_text(json.dumps(value, indent=2).replace('@', '\\u0040') + '\n')
    print(json.dumps({'number': number, 'path': str(path),
                      'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}), flush=True)

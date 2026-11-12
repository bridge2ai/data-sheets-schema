#!/usr/bin/env python3
"""H1 offline scanner provenance, 2026-11-12.

Inputs: accepted G07 helper bytes in the assigned integration worktree.
Outputs: separately named H1 helpers using a fresh sibling scratch root.
The behavior and isolated test environment are otherwise unchanged.
"""
from pathlib import Path
import hashlib
import json

ROOT = Path('/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-native-main-integration-20261112')
ROWS = (
    ('native_g07_packets_20261112.py', 'native_h1_packets_20261112.py'),
    ('run_native_g07_tests_20261112.py', 'run_native_h1_tests_20261112.py'),
)
results = []
for source, target in ROWS:
    before = (ROOT / 'scripts/adhoc' / source).read_bytes()
    after = before.replace(b'scratch-native-main-integration-20261112', b'scratch-native-h1-scanner-20261112')
    after = after.replace(b'G07', b'H1').replace(b'config.bak-g07-', b'config.bak-h1-')
    path = ROOT / 'scripts/adhoc' / target
    with path.open('xb') as stream:
        stream.write(after)
    assert path.read_bytes() == after
    results.append({'source': source, 'source_sha256': hashlib.sha256(before).hexdigest(),
                    'target': str(path), 'target_sha256': hashlib.sha256(after).hexdigest()})
print(json.dumps(results, indent=2))

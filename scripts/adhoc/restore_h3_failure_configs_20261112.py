#!/usr/bin/env python3
"""2026-11-12 #5967: restore own private composition CI config byte-exactly.
Inputs: named completed composition plus original backup; output: restore receipt.
Never changes the primary Git config or another helper's scratch.
"""
import argparse
import hashlib
import json
from pathlib import Path

base = Path(__file__).resolve().parents[3] / 'scratch-h3-failure-record-20261112'
parser = argparse.ArgumentParser()
parser.add_argument('names', nargs='+')
args = parser.parse_args()
for name in args.names:
    root = base / name
    if root.parent != base or root.resolve(strict=True) != root:
        raise ValueError('only own direct physical compositions may be restored')
    record = json.loads((root / 'composition.json').read_bytes())
    config = root / 'tree/.git/config'
    backup = config.with_name('config.bak-h3-failure-20261112')
    before = hashlib.sha256(config.read_bytes()).hexdigest()
    original = backup.read_bytes()
    expected = hashlib.sha256(original).hexdigest()
    assert expected == record['config_original_sha256']
    assert before == record['config_configured_sha256']
    config.write_bytes(original)
    assert config.read_bytes() == original
    receipt = {'config': str(config), 'before_sha256': before, 'restored_sha256': expected,
               'byte_exact': True}
    with (root / 'config-restoration.json').open('x') as stream:
        stream.write(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt))

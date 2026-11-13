#!/usr/bin/env python3
"""Restore H1 private Git configs, 2026-11-12.

Input: one H1 composition manifest and byte-exact private config backup.
Output: restored config and immutable receipt, including failed setup attempts.
No shared configuration or source files are changed.
"""
import argparse
import hashlib
import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[3] / 'scratch-native-h1-scanner-20261112'
ORIGINAL = '95a1f7d19be439847af9384dfe1a1f7678aa0902b1601b24c56cc60d783388b1'
CONFIGURED = '8a96cf34356a4adffb3c4cf8f07358fcde3857c9a2ed57a1c15cb9822f329b76'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    path = parser.parse_args().manifest.absolute()
    assert path.resolve(strict=True) == path and path.parent.parent == BASE
    raw = path.read_bytes()
    manifest = json.loads(raw)
    private = path.parent / 'tree/.git'
    assert private.is_dir() and private.resolve() == private
    receipt = path.parent / 'config-restored.json'
    assert not receipt.exists()
    config = private / 'config'
    backup = private / 'config.bak-h1-20261112'
    before, original = config.read_bytes(), backup.read_bytes()
    # The failed Python-3.9 extraction happened after this exact config write,
    # before the success manifest fields. Preserve that failure; restore only
    # the same audited G07/H1 private config bytes.
    assert sha(before) == manifest.get('config_configured_sha256', CONFIGURED)
    assert sha(original) == manifest.get('config_original_sha256', ORIGINAL)
    assert before == original + b'[d4d]\n\tciRepositoryUrl = https://github.com/bridge2ai/data-sheets-schema.git\n'
    config.write_bytes(original)
    assert config.read_bytes() == original
    result = {'manifest': str(path), 'manifest_sha256': sha(raw),
              'composition_status': manifest['status'], 'config': str(config),
              'backup': str(backup), 'before_sha256': sha(before),
              'restored_sha256': sha(original), 'restored': True,
              'scope': 'private test-only Git configuration'}
    with receipt.open('x') as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write('\n')
    assert json.loads(receipt.read_bytes()) == result
    print(json.dumps({'path': str(receipt), 'sha256': sha(receipt.read_bytes())}))


if __name__ == '__main__':
    main()

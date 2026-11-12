#!/usr/bin/env python3
"""Restore the G07 private test-only Git config, 2026-11-12.

Inputs: a completed scratch composition manifest and its exact config backup.
Outputs: restored private config and a separate immutable restoration receipt.
No shared config, evidence deletion, project imports or network operations.
"""
import argparse
import hashlib
import json
from pathlib import Path


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    args = parser.parse_args()
    base = Path(__file__).resolve().parents[3] / 'scratch-native-main-integration-20261112'
    path = args.manifest.absolute()
    if path.resolve(strict=True) != path or path.parent.parent != base:
        raise ValueError('only a physical assigned scratch manifest is supported')
    raw = path.read_bytes()
    value = json.loads(raw)
    git = Path(value['private_git'])
    if git != path.parent / 'tree/.git' or not git.is_dir() or git.resolve() != git:
        raise ValueError('not the isolated private Git directory')
    receipt = path.parent / 'config-restored.json'
    if receipt.exists():
        raise ValueError('restoration already recorded')
    config = git / 'config'
    backup = git / 'config.bak-g07-20261112'
    before, original = config.read_bytes(), backup.read_bytes()
    if digest(before) != value['config_configured_sha256']:
        raise ValueError('private config changed since setup; refusing to overwrite')
    if digest(original) != value['config_original_sha256']:
        raise ValueError('private original backup hash differs')
    config.write_bytes(original)
    if config.read_bytes() != original:
        raise ValueError('restored bytes differ')
    result = {'manifest': str(path), 'manifest_sha256': digest(raw),
              'config': str(config), 'backup': str(backup),
              'before_sha256': digest(before), 'restored_sha256': digest(original),
              'restored': True, 'scope': 'private test-only Git configuration'}
    with receipt.open('x') as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write('\n')
    assert json.loads(receipt.read_bytes()) == result
    print(receipt)
    print(digest(receipt.read_bytes()))


if __name__ == '__main__':
    main()

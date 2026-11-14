#!/usr/bin/env python3
"""Materialize the pinned local FAIRSCAPE tree for G04 collection, 2026-11-12.

Inputs: assigned HEAD gitlink and existing local submodule object store.
Outputs: new worktree FAIRSCAPE files and .temp/native-main-integration setup evidence.
Offline only; no submodule update, checkout changes elsewhere, native or provider call.
"""
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[2]
PRIMARY = ROOT.parent.parent / 'data-sheets-schema'
PIN = '8c80311d7d8b0fadac07dca9567d632103691f48'


def main():
    assert ROOT.name == 'codex-native-main-integration-20261112'
    gitlink = subprocess.check_output(['/usr/bin/git', 'ls-tree', 'HEAD', 'fairscape_models'], cwd=ROOT, text=True)
    assert gitlink.split()[2] == PIN
    out = ROOT / '.temp/native-main-integration'
    out.mkdir(parents=True, exist_ok=True)
    target = ROOT / 'fairscape_models'
    target.mkdir(exist_ok=True)
    assert not any(target.iterdir()), 'never overwrite an existing dependency tree'
    raw = subprocess.check_output(['/usr/bin/git', '-C', str(PRIMARY / 'fairscape_models'), 'archive', PIN])
    with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
        archive.extractall(target, filter='data')
    files = sorted(p for p in target.rglob('*') if p.is_file())
    assert files and (target / 'fairscape_models').is_dir()
    evidence = {'gitlink': PIN, 'local_source': str(PRIMARY / 'fairscape_models'),
                'archive_sha256': hashlib.sha256(raw).hexdigest(),
                'files': {str(p.relative_to(target)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
    destination = out / 'environment-setup.json'
    with destination.open('x') as stream:
        json.dump(evidence, stream, indent=2); stream.write('\n')
    assert json.loads(destination.read_text()) == evidence
    print(str(destination))
    print(hashlib.sha256(destination.read_bytes()).hexdigest())


if __name__ == '__main__':
    main()

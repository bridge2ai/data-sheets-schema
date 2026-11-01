#!/usr/bin/env python3
"""#5212, 2026-11-01: materialize a pinned offline archive for validation.

Inputs: local commit, fresh scratch destination, optional round-4 test overlay.
Outputs: archived tree + FAIRSCAPE at its gitlink pin + preparation JSON.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import tarfile

root = Path(__file__).resolve().parents[2]
p = argparse.ArgumentParser()
p.add_argument('commit')
p.add_argument('destination', type=Path)
p.add_argument('--regressions', action='store_true')
a = p.parse_args()
assert 'scratch-5212fix' in a.destination.parts and not a.destination.exists()
head = subprocess.check_output(['git', 'rev-parse', a.commit], cwd=root, text=True).strip()
raw = subprocess.check_output(['git', 'archive', head], cwd=root)
a.destination.mkdir(parents=True)
with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
    archive.extractall(a.destination, filter='data')
pin = subprocess.check_output(['git', 'ls-tree', head, 'fairscape_models'], cwd=root, text=True).split()[2]
common = Path(subprocess.check_output(['git', 'rev-parse', '--git-common-dir'], cwd=root, text=True).strip()).resolve()
subgit = common.parent / 'fairscape_models/.git'
subraw = subprocess.check_output(['git', '--git-dir=' + str(subgit), 'archive', pin])
with tarfile.open(fileobj=io.BytesIO(subraw)) as archive:
    archive.extractall(a.destination / 'fairscape_models', filter='data')
# Supply only local history for ancestry/repository-aware tests. The source
# bytes remain the pinned archive; never check out or fetch another revision.
subprocess.run(['git', 'init', '-q', str(a.destination)], check=True)
(a.destination / '.git/objects/info/alternates').write_text(str(common / 'objects') + '\n')
subprocess.run(['git', 'update-ref', '--no-deref', 'HEAD', head], cwd=a.destination, check=True)
subprocess.run(['git', 'read-tree', head], cwd=a.destination, check=True)
overlay = {}
if a.regressions:
    for name in ('test_d69_round4_ownership.py', 'test_d69_artifact_completeness.py'):
        source = root / 'tests' / name
        shutil.copyfile(source, a.destination / 'tests' / name)
        overlay[name] = hashlib.sha256(source.read_bytes()).hexdigest()
a.destination.with_suffix('.preparation.json').write_text(json.dumps({
    'head': head, 'archive_sha256': hashlib.sha256(raw).hexdigest(),
    'fairscape_pin': pin, 'regression_overlay': overlay}, indent=2))
print(head, a.destination)

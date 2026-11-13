"""6065 development replay: before/after recorder change on fixed input recipes.

Inputs: two local source commits, accepted replay aid and its frozen fixtures.
Outputs: owned scratch exports, snapshots, exact artifact difference inventory.
2026-11-13. No native/provider calls. This is not registration equivalence.
The copied driver only adapts its synthetic HOME/cache paths to merged 5966.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[2]
E = ROOT.parent
Q = E / 'codex-native-equivalence-comparison-20261112'
OLD = E / 'scratch-h3-equivalence-20261112'
OUT = E / 'scratch-h3-recorder-20261113' / sys.argv[3]
OUT.mkdir()
policy = json.loads((Q / 'scripts/native_equivalence_compare.json').read_bytes())
trees = []
for side, commit in zip(('before', 'after'), sys.argv[1:3]):
    tree = OUT / side
    tree.mkdir()
    archive = OUT / (side + '.tar')
    with archive.open('xb') as stream:
        subprocess.run(['git', '-C', str(ROOT), 'archive', commit], stdout=stream, check=True)
    with tarfile.open(archive) as stream:
        stream.extractall(tree, filter='data')
    # Both sides use exactly the accepted development recipes, not mutable
    # candidate tests. The policy's hashes still check every recipe byte.
    for path, digest in policy['fixture_sources'].items():
        raw = (OLD / 'candidate' / path).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == digest
        (tree / path).parent.mkdir(parents=True, exist_ok=True)
        (tree / path).write_bytes(raw)
    trees.append(tree)
source = (Q / 'scripts/native_equivalence_compare.py').read_text()
old = "'HOME': str(work),"
assert source.count(old) == 1
source = source.replace(old, "'HOME': str(work / 'home'), 'PYSTOW_HOME': str(work / 'helper-cache'),")
driver = OUT / 'development_driver.py'
driver.write_text(source)
spec = importlib.util.spec_from_file_location('recorder_development_replay', driver)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
result = module.compare(*trees, OUT / 'comparison', policy,
    json.loads((OLD / 'inputs.json').read_bytes()),
    E.parent / 'data-sheets-schema/.venv/lib/python3.13/site-packages')
manifest = {'scope': 'Development aid only; not a stratum gate or launch authority',
    'commits': sys.argv[1:3], 'original_driver_sha256': hashlib.sha256((Q / 'scripts/native_equivalence_compare.py').read_bytes()).hexdigest(),
    'adapted_driver_sha256': hashlib.sha256(driver.read_bytes()).hexdigest(),
    'adaptation': 'Same synthetic HOME and required helper cache on both sides; frozen fixture bytes unchanged',
    'status': result['status'], 'holds': result['holds']}
snapshot_paths = [OUT / 'comparison' / (side + '.json') for side in ('left', 'right')]
if all(path.is_file() for path in snapshot_paths):
    left, right = [json.loads(path.read_bytes()) for path in snapshot_paths]
    manifest['snapshots'] = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in snapshot_paths}
    a, b = left['artifacts'], right['artifacts']
    manifest['raw_changed_artifacts'] = [key for key in sorted(set(a) | set(b)) if a.get(key) != b.get(key)]
    manifest['unchanged_artifact_count'] = sum(a.get(key) == b.get(key) for key in set(a) | set(b))
(OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
print(json.dumps(manifest))

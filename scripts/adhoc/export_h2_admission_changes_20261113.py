#!/usr/bin/env python3
"""Export changed helper-2 source without integrating or repinning, 2026-11-13.
Input: exact power branch head. Outputs: new outside-execution after tree and
manifest for isolated unit tests/scanner. Admitted rerun tree is untouched.
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess

R = Path(__file__).resolve().parents[2]
HP = R.parent / 'codex-native-host-power-20261113'
B = Path.home() / 'agent-work/data-sheets-schema/helper2-pins-admission-20261113'
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--name', choices=('after', 'unaffected', 'before'), default='after')
args = parser.parse_args()
tree = B / args.name
def git(root, *args):
    return subprocess.check_output(['git', *args], cwd=root, text=True).strip()
assert not (B / (args.name + '.json')).exists(), 'closed export cannot be rewritten'
if not tree.exists():
    tree.mkdir(exist_ok=False)
    git(tree, 'init', '-q')
    (tree / '.git/objects/info/alternates').write_text(git(HP, 'rev-parse', '--path-format=absolute', '--git-path', 'objects') + '\n')
    git(tree, 'symbolic-ref', 'HEAD', 'refs/heads/offline-unadmitted-unit-tests')
    git(tree, 'update-ref', 'HEAD', git(HP, 'rev-parse', 'HEAD'))
    git(tree, 'sparse-checkout', 'set', '--cone', 'src', 'tests', 'scripts', 'docs', '.claude', '.github',
        'project', 'utils', 'notes', 'config', 'configs', 'examples', 'linkml_mappings',
        'data/rubric', 'data/preprocessed', 'data/_wcrate', 'data/ro-crate_packages', 'data/d4d_concatenated')
    git(tree, 'read-tree', '-mu', 'HEAD')
assert git(tree, 'rev-parse', 'HEAD') == git(HP, 'rev-parse', 'HEAD')
git(tree, 'config', '--local', 'd4d.ciRepositoryUrl', 'https://github.com/bridge2ai/data-sheets-schema.git')
shutil.copytree(B / 'fixed/fairscape_models', tree / 'fairscape_models', dirs_exist_ok=True)
(B / (args.name + '.json')).write_text(json.dumps({'tree': str(tree), 'commit': git(tree, 'rev-parse', 'HEAD'),
    'status': 'unadmitted source; unchanged controller pins; unit and scanner checks only'}, indent=2) + '\n')
print(B / (args.name + '.json'))

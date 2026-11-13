"""Add read-only Git history to an owned CI export for real registration tests.

Inputs: CI export manifest and local object store; outputs: private Git metadata
with no remote and a literal synthetic CI URL. No network. 6065 triage, 2026-11-13.
"""
from pathlib import Path
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
tree = Path(sys.argv[1]).resolve(strict=True)
assert tree.parent == Path('/Users/marcin/agent-work/data-sheets-schema')
assert tree.name.startswith('ci-sim-h3-recorder-')
manifest = json.loads((tree.parent / (tree.name + '.json')).read_bytes())
assert manifest['tree'] == str(tree)
assert not (tree / '.git').exists()
def git(*args, cwd=tree):
    return subprocess.check_output(['git', '-C', str(cwd), *args], text=True).strip()
objects = git('rev-parse', '--path-format=absolute', '--git-path', 'objects', cwd=ROOT)
git('init', '-q')
(tree / '.git/objects/info/alternates').write_text(objects + '\n')
git('update-ref', '--no-deref', 'HEAD', manifest['commit'])
git('read-tree', manifest['commit'])
git('config', '--local', 'd4d.ciRepositoryUrl', 'https://github.com/bridge2ai/data-sheets-schema.git')
assert not git('remote')
print(json.dumps({'tree': str(tree), 'head': git('rev-parse', 'HEAD'), 'remote': None}))

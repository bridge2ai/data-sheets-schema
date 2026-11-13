#!/usr/bin/env python3
"""Validate independent #6167/#6168/#6169/#6172 before changed controls, 2026-11-13.
Inputs committed pre-clock power revision and run-limit branch; outputs private
CI composition. Does not modify any controller or authority pin.
"""
from pathlib import Path
import json
import shutil
import subprocess
R = Path(__file__).resolve().parents[2]; E = R.parent
HP = E / 'codex-native-host-power-20261113'; C = E / 'codex-native-production-run-limits-20261112'
B = Path.home() / 'agent-work/data-sheets-schema/helper2-review-fixes-20261113'
tree = B / 'unaffected'; tree.mkdir(exist_ok=False)
def git(root, *args):
    return subprocess.check_output(['git', *args], cwd=root, text=True).strip()
git(tree, 'init', '-q')
(tree / '.git/objects/info/alternates').write_text(git(HP, 'rev-parse', '--path-format=absolute', '--git-path', 'objects') + '\n')
git(tree, 'symbolic-ref', 'HEAD', 'refs/heads/offline-unaffected-fixes')
git(tree, 'update-ref', 'HEAD', git(HP, 'rev-parse', 'f377dba1d'))
git(tree, 'sparse-checkout', 'set', '--cone', 'src', 'tests', 'scripts', 'docs', '.claude', '.github',
    'project', 'utils', 'notes', 'config', 'configs', 'examples', 'linkml_mappings',
    'data/rubric', 'data/preprocessed', 'data/_wcrate', 'data/ro-crate_packages', 'data/d4d_concatenated')
git(tree, 'read-tree', '-mu', 'HEAD')
git(tree, 'merge', '--no-ff', git(C, 'rev-parse', 'HEAD'), '-m', 'Private pre-clock review-fix composition')
git(tree, 'cherry-pick', git(HP, 'rev-parse', '916ad3af0'))
fixture = 'tests/test_native_execution_registration_v2.py'
(tree / fixture).write_bytes((HP / fixture).read_bytes())
git(tree, 'add', fixture)
git(tree, 'commit', '-m', 'Use explicit offline AC interface fixture in pre-clock proof')
git(tree, 'config', '--local', 'd4d.ciRepositoryUrl', 'https://github.com/bridge2ai/data-sheets-schema.git')
shutil.copytree(B / 'fixed/fairscape_models', tree / 'fairscape_models', dirs_exist_ok=True)
(B / 'unaffected.json').write_text(json.dumps({'tree': str(tree), 'commit': git(tree, 'rev-parse', 'HEAD'),
    'purpose': 'Independent pre-clock fixes only; not validation of deadline/timing implementation'}, indent=2) + '\n')
runner = R / 'scripts/adhoc/run_h2_review_fixes_20261113.py'
source = runner.read_text()
source = source.replace("('before', 'after', 'fixed')", "('before', 'after', 'fixed', 'unaffected')")
runner.write_text(source)
print(B / 'unaffected.json')

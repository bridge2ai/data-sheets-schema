#!/usr/bin/env python3
"""Admitted-pin rerun: exact branch export and offline runner, 2026-11-13.
Inputs lead-applied pins and current power/run-limit heads. Outputs new CI tree
outside d4d-executions, manifest and isolated network/native-denied runner.
"""
from pathlib import Path
import json
import shutil
import subprocess

R = Path(__file__).resolve().parents[2]; E = R.parent
B = Path.home() / 'agent-work/data-sheets-schema/helper2-pins-admission-20261113'
HP = E / 'codex-native-host-power-20261113'; C = E / 'codex-native-production-run-limits-20261112'
def git(root, *args):
    return subprocess.check_output(['git', *args], cwd=root, text=True).strip()
B.mkdir(exist_ok=False, parents=True)
tree = B / 'fixed'; tree.mkdir()
git(tree, 'init', '-q')
(tree / '.git/objects/info/alternates').write_text(git(HP, 'rev-parse', '--path-format=absolute', '--git-path', 'objects') + '\n')
git(tree, 'symbolic-ref', 'HEAD', 'refs/heads/offline-admitted-rerun')
git(tree, 'update-ref', 'HEAD', git(HP, 'rev-parse', 'HEAD'))
git(tree, 'sparse-checkout', 'set', '--cone', 'src', 'tests', 'scripts', 'docs', '.claude', '.github',
    'project', 'utils', 'notes', 'config', 'configs', 'examples', 'linkml_mappings',
    'data/rubric', 'data/preprocessed', 'data/_wcrate', 'data/ro-crate_packages', 'data/d4d_concatenated')
git(tree, 'read-tree', '-mu', 'HEAD')
git(tree, 'merge', '--no-ff', git(C, 'rev-parse', 'HEAD'), '-m', 'Private admitted controller proof composition')
git(tree, 'config', '--local', 'd4d.ciRepositoryUrl', 'https://github.com/bridge2ai/data-sheets-schema.git')
prior = Path.home() / 'agent-work/data-sheets-schema/helper2-review-fixes-20261113/fixed/fairscape_models'
shutil.copytree(prior, tree / 'fairscape_models', dirs_exist_ok=True)
(B / 'fixed.json').write_text(json.dumps({'tree': str(tree), 'commit': git(tree, 'rev-parse', 'HEAD'),
    'power': git(HP, 'rev-parse', 'HEAD'), 'limits': git(C, 'rev-parse', 'HEAD')}, indent=2) + '\n')
source = (R / 'scripts/adhoc/run_h2_review_fixes_20261113.py').read_text()
source = source.replace('helper2-review-fixes-20261113', 'helper2-pins-admission-20261113')
source = source.rstrip() + '\n'
(R / 'scripts/adhoc/run_h2_pins_admission_20261113.py').write_text(source)
print(B / 'fixed.json')

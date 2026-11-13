#!/usr/bin/env python3
"""#6167–6172 isolated CI export; inputs local branch heads, outputs fresh proof.
No network, host probe, provider or native executable. 2026-11-13.
"""
from pathlib import Path
import json
import shutil
import subprocess

R = Path(__file__).resolve().parents[2]
E = R.parent
B = Path.home() / 'agent-work/data-sheets-schema/helper2-review-fixes-20261113'
HP = E / 'codex-native-host-power-20261113'
C = E / 'codex-native-production-run-limits-20261112'
def git(root, *args):
    return subprocess.check_output(['/usr/bin/git', *args], cwd=root).decode().strip()

B.mkdir(exist_ok=False, parents=True)
tree = B / 'fixed'; tree.mkdir()
git(tree, 'init', '-q')
(tree / '.git/objects/info/alternates').write_text(git(HP, 'rev-parse', '--path-format=absolute', '--git-path', 'objects') + '\n')
git(tree, 'symbolic-ref', 'HEAD', 'refs/heads/offline-review-proof')
git(tree, 'update-ref', 'HEAD', git(HP, 'rev-parse', 'HEAD'))
git(tree, 'sparse-checkout', 'set', '--cone', 'src', 'tests', 'scripts', 'docs', '.claude', '.github',
    'project', 'utils', 'notes', 'config', 'configs', 'examples', 'linkml_mappings',
    'data/rubric', 'data/preprocessed', 'data/_wcrate', 'data/ro-crate_packages', 'data/d4d_concatenated')
git(tree, 'read-tree', '-mu', 'HEAD')
git(tree, 'merge', '--no-ff', git(C, 'rev-parse', 'HEAD'), '-m', 'Private offline composition of review fixes')
git(tree, 'config', '--local', 'd4d.ciRepositoryUrl', 'https://github.com/bridge2ai/data-sheets-schema.git')
prior = Path.home() / 'agent-work/data-sheets-schema/helper2-ci-20261113/after/fairscape_models'
shutil.copytree(prior, tree / 'fairscape_models', dirs_exist_ok=True)
(B / 'fixed.json').write_text(json.dumps({'tree': str(tree), 'commit': git(tree, 'rev-parse', 'HEAD'),
    'power': git(HP, 'rev-parse', 'HEAD'), 'limits': git(C, 'rev-parse', 'HEAD')}, indent=2) + '\n')
source = (R / 'scripts/adhoc/run_h2_ci_recheck_20261113.py').read_text()
start = source.index('SCRATCH_BASE = '); end = source.index('\n', start)
source = source[:start] + "SCRATCH_BASE = Path.home() / 'agent-work/data-sheets-schema/helper2-review-fixes-20261113'" + source[end:]
# Child HOME is isolated, so use the explicit --tree parent for the same root.
source = source.replace('global ROOT\n    tree', 'global ROOT, SCRATCH_BASE, SCRATCH\n    tree')
source = source.replace('tree = args.tree.absolute()', "tree = args.tree.absolute()\n    SCRATCH_BASE = tree.parent\n    SCRATCH = SCRATCH_BASE / 'tests'\n    if tree.parent.name != 'helper2-review-fixes-20261113':\n        parser.error('not this proof export')")
start = source.index('NATIVE_PATHS = ('); end = source.index('\n\n\ndef sandbox_profile', start)
source = source[:start] + "NATIVE_PATHS = tuple(str(path) for name in ('claude', 'codex', 'gemini', 'agy')\n    for path in (Path.home() / '.local/bin' / name, Path('/opt/homebrew/bin') / name, Path('/usr/local/bin') / name))" + source[end:]
start = source.index('    host, host_path = host_module()'); end = source.index('    python = make_test_venv', start)
source = source[:start] + source[end:]
source = source.replace(', "host_module_sha256": digest(host_path)', '')
start = source.index('    host_result = host.finish_run(out)'); end = source.index('    save(out / "outcome.json", outcome)', start)
source = source[:start] + '    outcome["host_observation"] = "not collected: offline review fixtures only"\n' + source[end:]
(R / 'scripts/adhoc/run_h2_review_fixes_20261113.py').write_text(source)
print(B / 'fixed.json')

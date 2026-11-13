#!/usr/bin/env python3
"""Refresh only own CI export from committed review-fix branches, 2026-11-13.
Inputs branch commits; outputs updated private commit/manifest with old retained.
No source-authority pin edits, network, probe or model execution.
"""
from pathlib import Path
import json
import subprocess
R = Path(__file__).resolve().parents[2]
B = Path.home() / 'agent-work/data-sheets-schema/helper2-review-fixes-20261113'
tree = B / 'fixed'
def git(root, *args):
    return subprocess.check_output(['git', *args], cwd=root, text=True).strip()
manifest = B / 'fixed.json'
old = json.loads(manifest.read_bytes())
saved = B / ('manifest-' + old['commit'] + '.json')
if not saved.exists(): saved.write_bytes(manifest.read_bytes())
heads = {}
for name, branch in [('power', 'codex-native-host-power-20261113'), ('limits', 'codex-native-production-run-limits-20261112')]:
    heads[name] = git(R.parent / branch, 'rev-parse', 'HEAD')
    git(tree, 'merge', '--no-ff', heads[name], '-m', 'Refresh private offline review-fix composition')
manifest.write_text(json.dumps({'tree': str(tree), 'commit': git(tree, 'rev-parse', 'HEAD'), **heads}, indent=2) + '\n')
print(manifest)

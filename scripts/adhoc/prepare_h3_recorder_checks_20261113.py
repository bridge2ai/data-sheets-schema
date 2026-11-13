"""Prepare offline CI exports and isolated runner for 6065 and merged-stack triage.

Inputs: local Git commits and existing isolated CI runner. Outputs: immutable
CI-like trees outside d4d-executions and an adapted runner. 2026-11-13.
"""
from pathlib import Path
import subprocess
import tarfile
import json
import hashlib

ROOT = Path(__file__).resolve().parents[2]
DEST = Path('/Users/marcin/agent-work/data-sheets-schema')
runner = (ROOT / 'scripts/adhoc/run_h3_ci_tests_20261112.py').read_text()
runner = runner.replace('agy-native-ci-collection-20261112', ROOT.name).replace('scratch-h3-ci-20261112', 'scratch-h3-recorder-20261113')
runner = runner.replace('    save(out / "plan.json",', "    if ROOT != SCRIPT_ROOT:\n        commit = json.loads((ROOT.parent / (ROOT.name + '.json')).read_bytes())['commit']\n    save(out / \"plan.json\",")
(ROOT / 'scripts/adhoc/run_h3_recorder_tests_20261113.py').write_text(runner)
for commit in ('6561dac3c3af50cbfce1ba3c8b6ad21d9cd4b834', '672057484'):
    full = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', commit], text=True).strip()
    tree = DEST / ('ci-sim-h3-recorder-' + full[:12])
    tree.mkdir()
    archive = tree.parent / (tree.name + '.tar')
    with archive.open('xb') as stream:
        subprocess.run(['git', '-C', str(ROOT), 'archive', full], stdout=stream, check=True)
    with tarfile.open(archive) as stream:
        stream.extractall(tree, filter='data')
    (tree.parent / (tree.name + '.json')).write_text(json.dumps({'commit': full, 'tree': str(tree), 'archive_sha256': hashlib.sha256(archive.read_bytes()).hexdigest()}, indent=2)+'\n')
    print(tree)

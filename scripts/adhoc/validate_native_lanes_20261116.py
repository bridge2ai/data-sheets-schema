"""Run assigned offline native refusal lanes serially for PR 5968, saving evidence; 2026-11-16.

Inputs: worktree, isolated interpreter, scratch, case names. Outputs: launcher logs
and JSON summaries. Uses the lead's required gate, no provider or public cases.
"""
import argparse
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument('--scratch', type=Path, required=True)
parser.add_argument('--cases', nargs='+', required=True)
parser.add_argument('--label', required=True)
args = parser.parse_args()
root = Path(__file__).resolve().parents[2]
python = args.scratch / 'isolated-venv/bin/python'
launcher = root.parent.parent / 'data-sheets-schema/scripts/adhoc/run_lane_20261115.py'
for case in args.cases:
    if not case.startswith(('native-failure-', 'native-capacity-')):
        raise ValueError('only assigned single offline lanes permitted')
commands = []
for case in args.cases:
    target = args.scratch / (args.label + '-' + case)
    command = [str(python), str(launcher), '--root', str(root), '--lane', 'native-public',
        '--case', case, '--python', str(python), '--scratch-dir', str(target),
        '--gate-wait-seconds', '1800', '--json-summary', str(target) + '-summary.json']
    with Path(str(target) + '-plan.txt').open('w') as stream:
        subprocess.run(command + ['--dry-run'], check=True, stdout=stream, stderr=subprocess.STDOUT)
    commands.append((target, command))
for target, command in commands:
    print('Starting ' + target.name, flush=True)
    with Path(str(target) + '-launcher.log').open('w') as stream:
        result = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT)
    if result.returncode:
        raise SystemExit(result.returncode)
    assert (target / 'results/pytest.xml').stat().st_size
    assert Path(str(target) + '-summary.json').stat().st_size
    print('Completed ' + target.name, flush=True)

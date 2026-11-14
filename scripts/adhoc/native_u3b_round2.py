"""Launch fixed round-2 review rosters offline, 2026-11-07.

Inputs: group, unique scratch output directory, optional archived base tree.
Outputs: roster, source-attributed pytest log, events and XML under that directory.
Serves accepted findings P2-2/P2-3; all work uses the bounded quiet-aware launcher.
"""
from pathlib import Path
import argparse
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser()
parser.add_argument('group', choices=['api', 'shared', 'bc1', 'collect'])
parser.add_argument('output', type=Path)
parser.add_argument('--tree', type=Path, default=ROOT)
parser.add_argument('--plan', action='store_true')
parser.add_argument('--name')
args = parser.parse_args()
patterns = {
    'api': ['test_api_*.py', 'test_source_heading*.py', 'test_renderer_contract_captures.py'],
    'shared': ['test_shared_generation*.py', 'test_typed_audit*.py', 'test_audit_omission*.py'],
    'bc1': ['test_bc1*.py', 'test_wave7*bc1*.py'],
}
files = sorted({p.relative_to(args.tree).as_posix() for pattern in patterns.get(args.group, [])
                for p in (args.tree / 'tests').glob(pattern)})
if args.group == 'api':
    files.append('tests/test_download/test_api_runner.py')
if args.group == 'collect':
    files = ['tests', '--collect-only']
name = args.name or args.group + ('-base' if args.tree != ROOT else '')
cmd = [sys.executable, str(ROOT / 'scripts/adhoc/validate_native_u3b.py'), name,
       '--workers', '0' if args.group in ('api', 'collect') else '2',
       '--output-dir', str(args.output), '--tree', str(args.tree), *files,
       '-q', '--tb=short', '--junitxml=' + str(args.output / (name + '.xml'))]
if args.plan:
    print('\n'.join(cmd))
else:
    args.output.mkdir(parents=True, exist_ok=True)
    roster = args.output / (name + '-roster.txt')
    if roster.exists():
        raise SystemExit('Refusing to overwrite roster')
    roster.write_text('\n'.join(files) + '\n')
    raise SystemExit(subprocess.call(cmd, cwd=ROOT))

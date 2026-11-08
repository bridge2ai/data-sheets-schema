"""PR5531 fix B offline acceptance, 2026-11-08.

Inputs: fix-A's recorded suite list plus canary/grounding suites. Outputs:
scratch logs and XML, through the same quiet-window/deadline runner as canary.
"""
import ast
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-pr5531-fix'
runner = ROOT / 'scripts/adhoc/pr5531_fix_a_run.py'
previous = ast.literal_eval((SCRATCH / 'acceptance.log').read_text().splitlines()[0])
files = [p for p in previous if p.startswith('tests/')]
files += sorted(str(p.relative_to(ROOT)) for pattern in ('test_canary*.py', 'test_grounding*.py', 'test_name_grounding*.py') for p in (ROOT / 'tests').glob(pattern))
command = [sys.executable, '-m', 'pytest', *files, '-q', '-n', '2', '-p', 'no:cacheprovider',
           f'--basetemp={SCRATCH}/fix-b-acceptance', f'--junitxml={SCRATCH}/fix-b-acceptance.xml']
sys.exit(subprocess.call([sys.executable, str(runner), 'fix-b-acceptance', *command]))

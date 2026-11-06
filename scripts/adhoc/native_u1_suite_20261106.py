"""U1 #4354 2026-11-06: select required offline API/shared/BC1/D76 regressions.
Inputs: tests tree. Output: scratch roster and bounded check log. No provider.
"""
from pathlib import Path
import subprocess
import sys
ROOT = Path(__file__).resolve().parents[2]
patterns = ('test_api_*.py', 'test_shared_generation*.py', 'test_bc1*.py',
            'test_wave7*bc1*.py', 'test_wave7*5213*.py', 'test_source_heading*.py',
            'test_*schema_snapshot*.py', 'test_renderer_contract_captures.py')
files = sorted({p.relative_to(ROOT).as_posix() for pat in patterns for p in (ROOT / 'tests').glob(pat)} | {'tests/test_download/test_api_runner.py'})
(ROOT.parent / 'scratch-native-u1/regression-roster.txt').write_text('\n'.join(files) + '\n')
raise SystemExit(subprocess.call([sys.executable, str(ROOT / 'scripts/adhoc/native_u1_check_20261106.py'), 'api-regressions', sys.executable, '-m', 'pytest', *files, '-n', '2', '-q', '-p', 'no:cacheprovider'], cwd=ROOT))

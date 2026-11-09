"""PR5531 fix C offline acceptance selection, 2026-11-08.

Inputs: tests (including ignored files for digest-literal search). Outputs:
scratch logs/JUnit and selected-file manifest, with two workers and 3600s limit.
"""
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-pr5531-fix'
mode = sys.argv[1]
if mode in ('bc1', 'final'):
    files = sorted(str(p.relative_to(ROOT)) for pattern in
                   ('test_bc1_*.py', 'test_wave7_bc1*.py') for p in (ROOT / 'tests').glob(pattern))
    if mode == 'final':
        files += ['tests/test_download/test_api_runner.py', 'tests/test_removals.py',
                  'tests/test_semantic_exchange/test_comprehensive_sssom.py',
                  'tests/test_semantic_exchange/test_sssom_validation.py',
                  'tests/test_profiles.py', 'tests/test_pr5531_regressions.py']
elif mode == 'normaliser':
    files = ['tests/test_download/test_api_runner.py', 'tests/test_removals.py',
             'tests/test_semantic_exchange/test_comprehensive_sssom.py',
             'tests/test_semantic_exchange/test_sssom_validation.py']
else:
    patterns = ('test_*digest*.py', 'test_profiles.py', 'test_schema_sync*.py',
                'test_schema_release*.py', 'test_release_inventory.py', 'test_pr5531_regressions.py',
                'test_nested_string_lists.py', 'test_identifier_form.py', 'test_enum_alias_normalisation.py',
                'test_british_normaliser.py', 'test_mailto_ids.py', 'test_ci_timing_update.py',
                'test_neutral_generation_schema.py', 'test_external_dataset_onboarding.py',
                'test_generation_specificity_skill.py')
    files = {str(p.relative_to(ROOT)) for pattern in patterns for p in (ROOT / 'tests').rglob(pattern)}
    # Path.rglob includes hidden/ignored files; literal and named digest pins.
    pins = {str(p.relative_to(ROOT)) for p in (ROOT / 'tests').rglob('test_*.py')
            if re.search(r'(?i)[\"\'][a-f0-9]{32}[\"\']|(?:CURRENT|EXPECTED|PINNED)_?(?:STUDY|NEUTRAL|DIGEST)', p.read_text())}
    files = sorted(files | pins)
    (SCRATCH / 'fix-c-digest-constant-test-files.json').write_text(json.dumps(sorted(pins), indent=2) + '\n')
label = 'fix-c-' + mode
out = SCRATCH / label
out.mkdir(exist_ok=True)
(out / 'files.json').write_text(json.dumps(files, indent=2) + '\n')
command = [sys.executable, '-m', 'pytest', *files, '-q', '-n', '2', '--dist', 'worksteal',
           '-p', 'no:cacheprovider', f'--basetemp={out}/basetemp', f'--junitxml={out}/pytest.xml']
sys.exit(subprocess.call([sys.executable, str(ROOT / 'scripts/adhoc/pr5531_fix_a_run.py'), label, *command]))

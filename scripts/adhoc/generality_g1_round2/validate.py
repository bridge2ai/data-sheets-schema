"""Serial offline validation for P4a findings 4/5, 2026-10-30.

Inputs: current checkout, CI shard plugin and affected suite paths.
Outputs: commands, logs, JUnit, exit codes in .g1-round2-evidence; no run writes.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / '.g1-round2-evidence'
HERE = Path(__file__).resolve().parent
# Corpus discovery deliberately walks parents. A basetemp inside the checkout
# makes unrelated fixtures inherit this real corpus rather than their own cwd.
TEMPS = ROOT.parent / 'rev-g1r2/out/g1-round2-basetemps'
TEMPS.mkdir(parents=True, exist_ok=True)
PATTERNS = (
    'test_generality*.py', 'test_profiles.py', 'test_historical_profile*.py',
    'test_profile_review*.py', 'test_form_defects.py', 'test_review_pack*.py',
    'test_blind_review_pack.py', 'test_d4d_pair_consistency.py',
    'test_pair_cli_recorded_digest.py', 'test_receipt_completion*.py',
    'test_rereceipt_completion.py', 'test_schema*.py', 'test_digest_isolation.py',
    'test_historical_digest*.py', 'test_d4d_full_schema.py',
    'test_neutral_generation_schema.py', 'test_core_schema_targets.py',
)
paths = sorted({str(p.relative_to(ROOT)) for pat in PATTERNS for p in (ROOT / 'tests').glob(pat)})
paths += ['tests/test_schema', 'tests/test_cli/test_schema_cli.py']
UNITS = {
    'schema-canary': ['tests/test_d4d_full_schema.py'],
    'fixture-canary': ['tests/test_historical_digest.py', 'tests/test_profile_review_r8.py',
                       'tests/test_profile_review_r9.py'],
    'canary-final': ['tests/test_generality_profiles.py', 'tests/test_generality_substrate.py'],
    'focused-final': paths,
    'collect-final': ['tests', '--collect-only'],
    'shard-1': ['tests', '-p', 'utils.pytest_shard', '--ci-shard=1/6',
                '--ci-shard-timings=utils/ci_test_durations.json', '--ci-lane=ordinary'],
}
for name in sys.argv[1:]:
    if name in ('shard-loopback-canary', 'shard-loopback'):
        from scripts.adhoc.generality_g1_round2.shard_failures import read_failures
        args = [f['node'] for f in read_failures() if f['kind'] == 'loopback_setup']
        assert args
        if name.endswith('canary'):
            args = args[:1]
    else:
        args = UNITS[name]
    command = ['bash', str(HERE / 'run.sh'), 'pytest', *args, '-q', '-p', 'no:cacheprovider',
               f'--basetemp={TEMPS / name}', f'--junitxml={OUT / (name + ".xml")}']
    started = time.time()
    print('START', name, flush=True)
    with (OUT / (name + '.log')).open('w') as log:
        proc = subprocess.Popen(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        (OUT / (name + '.pid')).write_text(str(proc.pid))
        try:
            returncode = proc.wait()
        except KeyboardInterrupt:
            import signal
            proc.send_signal(signal.SIGINT)
            proc.wait()
            raise
    info = {'command': command, 'returncode': returncode, 'seconds': time.time() - started,
            'python': sys.version, 'head': subprocess.check_output(
                ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()}
    (OUT / (name + '.result.json')).write_text(json.dumps(info, indent=2) + '\n')
    print('END', name, returncode, flush=True)
    assert (OUT / (name + '.xml')).stat().st_size
    if 'canary' in name or name.startswith('collect'):
        assert returncode == 0
    else:
        assert returncode in (0, 1)

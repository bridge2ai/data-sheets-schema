#!/usr/bin/env python3
"""Serial offline validation after the admitted rerun, 2026-11-13.
Inputs fixed/unaffected export manifests. Outputs isolated canary, unit,
pin-refusal, scanner and generation-guard cohorts. Max two xdist workers.
No live probes, binaries, captures, reservations or publication.
"""
import json
from pathlib import Path
import subprocess
import sys
import time

R = Path(__file__).resolve().parents[2]
B = Path.home() / 'agent-work/data-sheets-schema/helper2-pins-admission-20261113'
runner = R / 'scripts/adhoc/run_h2_pins_admission_20261113.py'
while not (B / 'tests/admitted-touched-files/outcome.json').exists():
    time.sleep(5)
time.sleep(2)  # Allow the earlier runner's final cleanup/lock release.
rows = []
def run(name, nodes=(), workers=0, scanner=False):
    out = B / 'tests' / name
    command = [sys.executable, '-S', '-P', '-B', str(runner), '--tree', str(B / 'unaffected'),
        '--out', str(out), '--workers', str(workers), '--timeout-seconds', '7200']
    command += ['--scanner'] if scanner else list(nodes)
    code = subprocess.run(command, cwd=R).returncode
    result = json.loads((out / 'outcome.json').read_bytes())
    rows.append(dict(name=name, runner_exit=code, result=result))
    (B / 'new-checks.json').write_text(json.dumps(rows, indent=2) + '\n')
    return code
if run('admission-alarm-canary', ['tests/test_native_admission_timer.py::test_stalled_fifo_open_is_interrupted_and_alarm_is_restored[False]']) != 0:
    raise SystemExit('new source canary failed; retained evidence; no batch')
run('new-unit-files', ['tests/test_native_admission_timer.py', 'tests/test_native_pre_dispatch_timing.py'], workers=2)
run('publication-awaiting-pins', ['tests/test_native_admission_failure.py'])
run('specificity', scanner=True)
run('generation-guards', ['tests/test_generation_specificity_skill.py', 'tests/test_neutral_generation_schema.py',
    'tests/test_profiles.py', 'tests/test_external_dataset_onboarding.py'], workers=2)

#!/usr/bin/env python3
"""End only the redundant blocked guard cohort gracefully, 2026-11-13.
Inputs exact task runner command and saved scanner refusal. Outputs identified
SIGINT receipt; pytest retains partial XML/logs and the owner runner cleans up.
Never signals the admitted cohort, other helpers, or any native process.
"""
import json
from pathlib import Path
import signal

import psutil

R = Path(__file__).resolve().parents[2]
B = Path.home() / 'agent-work/data-sheets-schema/helper2-pins-admission-20261113'
out = B / 'tests/generation-guards'
assert not (out / 'outcome.json').exists(), 'already complete'
assert 'v2 envelope authority source changed' in (B / 'tests/specificity/pytest.log').read_text()
assert json.loads((B / 'tests/admitted-touched-files/outcome.json').read_bytes())['returncode'] == 0
expected = [str(R / 'scripts/adhoc/run_h2_pins_admission_20261113.py'), '--worker',
    '--tree', str(B / 'unaffected'), '--out', str(out), '--workers', '2',
    '--timeout-seconds', '7200', 'tests/test_generation_specificity_skill.py',
    'tests/test_neutral_generation_schema.py', 'tests/test_profiles.py',
    'tests/test_external_dataset_onboarding.py']
matches = []
for process in psutil.process_iter(['pid', 'cmdline']):
    cmd = process.info['cmdline'] or []
    if cmd[3:] == expected and cmd[1:3] == ['-P', '-B']:
        matches.append(process)
assert len(matches) == 1, [process.pid for process in matches]
process = matches[0]
parent = process.parent()
assert parent is not None and str(out) in parent.cmdline()
record = dict(pid=process.pid, created=process.create_time(), command=process.cmdline(),
    parent_pid=parent.pid, parent_created=parent.create_time(), signal='SIGINT',
    reason='supplementary guard suite cannot validate its source fixture while the scanner frozen authority contract refuses; requested eight-file rerun is complete',
    scope='partial supplementary guard results, never a complete guard pass')
process.send_signal(signal.SIGINT)
with (B / 'blocked-guards-interruption.json').open('x') as stream:
    json.dump(record, stream, indent=2); stream.write('\n')
print(json.dumps(record, indent=2))

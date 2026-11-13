"""Stop this task's obsolete pre-race-fix cohort by verified runner identity, 2026-11-13."""
import json
import argparse
from pathlib import Path
import signal
import sys

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser()
parser.add_argument('--cohort', choices=['focused-01', 'final-boundaries-01', 'final-boundaries-02'], default='focused-01')
options = parser.parse_args()
OUT = ROOT.parent / 'scratch-h3-environment-manifest-20261113/tests' / options.cohort
sys.path.append('/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/lib/python3.13/site-packages')
import psutil

runner = str(ROOT / 'scripts/adhoc/run_h3_environment_tests_20261113.py')
matches = []
for process in psutil.process_iter(['pid', 'create_time', 'cmdline']):
    args = process.info['cmdline'] or []
    if runner in args and str(OUT) in args and '--worker' not in args:
        matches.append(process)
assert len(matches) == 1, 'expected exactly one owned cohort parent'
process = matches[0]
created = process.create_time()
record = {'pid': process.pid, 'create_time': created, 'cmdline': process.cmdline(),
          'reason': ('Stop incomplete old-source cohort to repair confirmed RECORD-during-census stale-read race.'
                     if options.cohort == 'focused-01' else
                     'Narrow dispatch fixture before its unrelated synthetic capture-authority construction.')}
assert process.create_time() == created
with (OUT / 'interruption-request.json').open('x') as stream:
    json.dump(record, stream, indent=2)
process.send_signal(signal.SIGINT)
print(json.dumps(record))

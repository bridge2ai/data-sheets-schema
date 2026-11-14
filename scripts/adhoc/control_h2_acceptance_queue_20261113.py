#!/usr/bin/env python3
"""Retire only the H2 acceptance queue between cohorts, 2026-11-13.
Inputs: exact owned queue PID, worktree cwd and focused outcome. Outputs:
scratch control ledger. Pauses the waiting parent only; never signals tests.
This permits a fresh four-worker canary before the remaining assigned suites.
"""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-h2-resume-20261113'
PYTHON = ROOT.parent.parent / 'data-sheets-schema/.venv/bin/python'
LEDGER = SCRATCH / 'acceptance-queue-control.json'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('hold', 'retire'))
    parser.add_argument('pid', type=int)
    args = parser.parse_args()
    assert args.pid > 1
    command = subprocess.check_output(['ps', '-p', str(args.pid), '-o', 'command='], text=True).strip()
    assert command == str(PYTHON) + ' scripts/adhoc/queue_h2_resume_20261113.py acceptance'
    locations = subprocess.check_output(['lsof', '-a', '-p', str(args.pid), '-d', 'cwd', '-Fn'], text=True)
    assert [line[1:] for line in locations.splitlines() if line.startswith('n')] == [str(ROOT)]
    if args.phase == 'hold':
        assert not LEDGER.exists()
        record = {'pid': args.pid, 'command': command, 'cwd': str(ROOT), 'state': 'hold_planned',
                  'reason': 'Complete focused unchanged, then canary the permitted four-worker mode for remaining suites.',
                  'signals_target_only_queue_parent': True}
        LEDGER.write_text(json.dumps(record, indent=2) + '\n')
        os.kill(args.pid, signal.SIGSTOP)
        for _ in range(20):
            state = subprocess.check_output(['ps', '-p', str(args.pid), '-o', 'state='], text=True).strip()
            if 'T' in state:
                break
            time.sleep(0.05)
        assert 'T' in state
        record['state'] = 'queue_held_tests_untouched'
    else:
        record = json.loads(LEDGER.read_bytes())
        assert record['pid'] == args.pid and record['state'] == 'queue_held_tests_untouched'
        outcome = SCRATCH / 'focused/outcome.json'
        assert outcome.is_file() and (SCRATCH / 'focused/pytest.xml').is_file()
        record['focused_outcome'] = json.loads(outcome.read_bytes())
        assert not (SCRATCH / 'failure/command.json').exists()
        os.kill(args.pid, signal.SIGTERM)
        os.kill(args.pid, signal.SIGCONT)
        record['state'] = 'queue_retired_after_focused_saved'
    LEDGER.write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record))


if __name__ == '__main__':
    main()

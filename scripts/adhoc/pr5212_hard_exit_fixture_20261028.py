#!/usr/bin/env python3
"""PR #5212/D57, 2026-10-28: offline subprocess hard-exit fixture.

Inputs: output directory, completed phase, optional prior head for fresh start. Outputs: synthetic artifacts,
an independently captured monitor head on stderr, then process exit 23.
Used by test_usage_ledger; FakeClient never contacts a provider.
"""
import os
from pathlib import Path
import sys

from data_sheets_schema import api_runner as api, latch_journal
from tests.test_download.test_api_runner import FakeClient, spec


def main():
    save, generate = api._save_progress, api._generate_phase
    def stop(run):
        print('test launch monitor head=' + latch_journal.head_sha256(run), file=sys.stderr, flush=True)
        os._exit(23)
    def exit_after_progress(run, completed, audit):
        save(run, completed, audit)
        if sys.argv[2] in completed:
            stop(run)
    def exit_before_progress(run, *args, **kwargs):
        if sys.argv[2] == 'before_progress':
            stop(run)
        return generate(run, *args, **kwargs)
    api._save_progress = exit_after_progress
    api._generate_phase = exit_before_progress
    fresh = len(sys.argv) > 3
    api.execute(spec(out_dir=Path(sys.argv[1])), client=FakeClient(), resume=not fresh,
                expect_journal_head_sha256=sys.argv[3] if fresh else None)


if __name__ == '__main__':
    main()

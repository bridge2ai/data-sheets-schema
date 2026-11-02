#!/usr/bin/env python3
"""R1/#5212, 2026-10-28: offline SIGTERM checkpoint fixture.

Input: temporary output directory. Output: durable usage/journal plus READY on
stdout; wait between writes so the test can send the real api-stop SIGTERM.
Uses a fake client for the read-only startup check (round 4, 2026-11-01).
This tests termination/anchoring, not phase recovery.
"""
from pathlib import Path
import socket
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from data_sheets_schema import api_runner as api, usage_ledger as ledger
from tests.test_download.test_api_runner import FakeClient, spec


def between_phases(selected, **kwargs):
    ledger.prepare_usage(selected, resume=False)
    print('READY', flush=True)
    sys.stdin.read()
    raise AssertionError('fixture must be terminated')


def refuse_network(*args, **kwargs):
    raise AssertionError('offline fixture forbids network')


if __name__ == '__main__':
    socket.socket.connect = refuse_network
    api._execute = between_phases
    api.execute(spec(out_dir=Path(sys.argv[1])), client=FakeClient())

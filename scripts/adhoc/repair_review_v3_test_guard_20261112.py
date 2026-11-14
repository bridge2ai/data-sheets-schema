#!/usr/bin/env python3
"""Repair the context refusal fixture to reach its intended bundle gate.
Input/output: test_native_review_bundle_v3.py. Helper-2 Part C, 2026-11-12.
"""
from pathlib import Path
path = Path(__file__).resolve().parents[2] / 'tests/test_native_review_bundle_v3.py'
raw = path.read_text()
old = "    guard_raw = wire.canonical({'version': 2, 'capture_index': 1, 'capture_claim_count': 1})"
assert raw.count(old) == 1
path.write_text(raw.replace(old, """    from data_sheets_schema import native_subscription_guard_v2 as guard
    # A closed selection shape reaches the bundle gate; the unused guard
    # contents are not evidence and must never reach guard reconstruction.
    guard_raw = wire.canonical({**dict.fromkeys(guard.KEYS), 'kind': guard.KIND,
                               'version': 2, 'capture_index': 1, 'capture_claim_count': 1})"""))

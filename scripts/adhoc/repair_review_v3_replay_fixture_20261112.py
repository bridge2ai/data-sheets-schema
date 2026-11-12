#!/usr/bin/env python3
"""Supply complete historical delivery for replay success, retaining stop refusal.
Input/output: test_native_review_bundle_v3.py. Helper-2 Part C, 2026-11-12.
"""
from pathlib import Path
path = Path(__file__).resolve().parents[2] / 'tests/test_native_review_bundle_v3.py'
raw = path.read_text()
old = '    old = build(case)\n    old_snapshot = old.snapshot()'
assert raw.count(old) == 1
raw = raw.replace(old, """    old = build(case)
    old.before_dispatch()
    old.observe(case['event'])
    old_snapshot = old.snapshot()
    transcript = wire.canonical(case['event']) + b'\\n'
    baseline = saved(case, old, transcript, snapshot=old_snapshot, complete=True)
    assert baseline['passed'] is True""")
old = "    assert saved(case, old, b'', snapshot=old_snapshot, complete=False)['passed'] is True"
assert raw.count(old) == 1
raw = raw.replace(old, """    assert saved(case, old, transcript, snapshot=old_snapshot, complete=True) == baseline
    incomplete = saved(case, old, transcript, snapshot=old_snapshot, complete=False)
    assert incomplete['checked'] is False and incomplete['passed'] is False
    assert incomplete['transcript_diagnostic']['observed_rate_limit_events'] == 1""")
path.write_text(raw)

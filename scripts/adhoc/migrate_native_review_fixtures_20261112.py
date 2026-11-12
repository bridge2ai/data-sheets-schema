#!/usr/bin/env python3
"""Move current test producers to new fixtures; preserve historical builders.
Inputs: helper-2 branch tests. Outputs: current fixture imports and script pin.
Serves approved bundle-v3 migration, 2026-11-12; no recorded fixture rewrite.
"""
from pathlib import Path
root = Path(__file__).resolve().parents[2]
for name in ('tests/test_native_subscription_capture.py', 'tests/test_native_u4b_readback.py',
             'tests/utils/native_synthetic_evidence.py'):
    path = root / name
    raw = path.read_text()
    old = 'from tests.utils.native_u4b_fixtures import bundle_for'
    assert raw.count(old) == 1
    raw = raw.replace(old, 'from tests.utils.native_review_v3_fixtures import current_bundle_for as bundle_for')
    if name.endswith('test_native_subscription_capture.py'):
        raw = raw.replace('def component(tmp_path, monkeypatch, *, mode=', 'def component(tmp_path, monkeypatch, *, mode=')
        old = "'dependencies': {'base': {'source_commit': 'a' * 40}}}"
        assert raw.count(old) == 1
        raw = raw.replace(old, "'dependencies': {'base': {'source_commit': 'a' * 40,\n                                  'package_sources': sequence_pin()}}}")
        raw = raw.replace('    # Capture traps/counters', '    from tests.utils.native_review_v3_fixtures import sequence_pin\n    # Capture traps/counters')
    path.write_text(raw)

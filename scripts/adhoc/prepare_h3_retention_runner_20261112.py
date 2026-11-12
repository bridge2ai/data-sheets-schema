#!/usr/bin/env python3
"""2026-11-12 retention: adapt the accepted isolated runner to this own branch.
Input Part 1 runner; output Part 2 runner; same offline scratch and denials.
"""
from pathlib import Path
root = Path(__file__).resolve().parents[2]
raw = (root / 'scripts/adhoc/run_h3_failure_tests_20261112.py').read_text()
raw = raw.replace('codex-native-failure-record-20261112', root.name)
(root / 'scripts/adhoc/run_h3_retention_tests_20261112.py').write_text(raw)

#!/usr/bin/env python3
"""2026-11-12 #5989: copy candidate offline runner into assigned helper scope.
Input committed G07 runner; output own runner with same isolation checks.
"""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
raw=(root/'scripts/adhoc/run_native_g07_tests_20261112.py').read_text()
raw=raw.replace('codex-native-main-integration-20261112','codex-native-launch-sequence-hardening-20261112').replace('scratch-native-main-integration-20261112','scratch-h3-launch-hardening-20261112')
(root/'scripts/adhoc/run_h3_hardening_tests_20261112.py').write_text(raw)

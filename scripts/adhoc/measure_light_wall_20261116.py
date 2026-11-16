"""Measure one unprofiled light census for launch-cost review, 2026-11-16.

Inputs: saved manifest. Output: elapsed seconds, host load and fingerprint count.
Uses the same import setup as the standalone census profiler; no caches reused.
"""
import json
import os
from pathlib import Path
import sys
import time

root = Path(__file__).resolve().parents[2]
sys.path[0] = str(root)
from tests.test_native_shared_execution import make_case, launch_case
import pytest
from data_sheets_schema import native_environment_manifest as environment

value = json.loads(Path(sys.argv[1]).read_bytes())
started = time.monotonic()
fingerprints = environment._light_live(value)
print(json.dumps({'seconds': time.monotonic() - started, 'fingerprints': len(fingerprints),
                  'load': os.getloadavg()}))

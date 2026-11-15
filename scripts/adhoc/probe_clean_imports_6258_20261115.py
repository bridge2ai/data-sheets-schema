"""Issue 6258, 2026-11-15: diagnose setup without editable-install hooks.

Run with assigned venv Python -S; inputs: pytest args; outputs: pytest log.
Loads physical dependency site only, as existing offline test runners do.
Does not replace package paths, source pins, fixtures, or production guards.
"""
from pathlib import Path
import sys

assert sys.flags.no_site
root = Path(__file__).resolve().parents[2]
site = Path(sys.executable).parent.parent / 'lib' / ('python' + '.'.join(map(str, sys.version_info[:2]))) / 'site-packages'
assert site.is_dir()
sys.path.extend([str(root), str(site)])
from tests.utils.native_test_environment import origin_witness
import json
print(json.dumps(origin_witness(root)), flush=True)
import pytest
raise SystemExit(pytest.main(sys.argv[1:]))

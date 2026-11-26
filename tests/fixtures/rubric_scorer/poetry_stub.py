# Offline Poetry shim for issue 6315, 2026-11-25.
# Inputs: runner's exact Poetry argv. Output: the real validator's exit status.
# This only selects the existing test interpreter; validation is not mocked.
import json
import os
from pathlib import Path
import sys

if sys.argv[1:3] != ["run", "python"]:
    raise SystemExit("unexpected Poetry test argv")
(Path(__file__).parent / "validator-invocation.json").write_text(
    json.dumps({"argv": sys.argv[1:], "cwd": os.getcwd()}, indent=2))
os.execv(sys.executable, [sys.executable, *sys.argv[3:]])

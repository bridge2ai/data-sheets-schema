"""Run offline PR 6372/6396 repair checks with retained logs and receipts.

2026-11-26. Inputs: this checkout, an interpreter, a named lane and a fresh
evidence directory. Outputs: pytest log, JUnit XML and exit/timing receipt.
Inherited provider credentials are removed before collection. No model call.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import time


LANES = {
    "focused": ["tests/test_q19_rationale_lint.py", "tests/test_q19_blind_second_reading.py",
                "tests/test_instrument_provenance.py", "tests/test_evaluation"],
    "corpus": ["tests", "-m", "corpus"],
    "corpus-collect": ["tests", "-m", "corpus", "--collect-only"],
    "scanner": [
        "tests/test_native_d128_scanner_comparison.py",
        "tests/test_native_d128_pr6325_successor.py",
        "tests/test_native_d128_successor.py",
        "tests/test_generation_specificity_skill.py",
        "tests/test_generation_specificity_delegated.py",
        "tests/test_native_u5_scanner_comparison.py",
    ],
}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--python", required=True, type=Path)
    ap.add_argument("--lane", choices=LANES, required=True)
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()
    root = Path(__file__).resolve().parents[2]
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    env = dict(os.environ)
    for key in tuple(env):
        if key.endswith("_API_KEY") or key in {
            "ANTHROPIC_AUTH_TOKEN", "CLAUDE_CODE_OAUTH_TOKEN",
            "ANTHROPIC_BASE_URL", "OPENAI_BASE_URL",
        }:
            del env[key]
    env.update({"PYTHONPATH": str(root / "src") + os.pathsep + str(root),
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONPYCACHEPREFIX": str(output / "bytecode")})
    command = [str(args.python), "-B", "-m", "pytest", *LANES[args.lane],
               "-q", "-p", "no:cacheprovider", "--basetemp=" + str(output / "tmp"),
               "--junitxml=" + str(output / "junit.xml")]
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    started = datetime.now(timezone.utc).isoformat()
    clock = time.monotonic()
    with (output / "pytest.log").open("x") as log:
        result = subprocess.run(command, cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT)
    receipt = {"lane": args.lane, "head": head, "command": command,
               "started_utc": started, "finished_utc": datetime.now(timezone.utc).isoformat(),
               "elapsed_seconds": time.monotonic() - clock, "exit_code": result.returncode,
               "provider_environment_cleared_before_collection": True,
               "nice_value": os.getpriority(os.PRIO_PROCESS, 0),
               "log": str(output / "pytest.log"), "junit": str(output / "junit.xml")}
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, sort_keys=True))
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()

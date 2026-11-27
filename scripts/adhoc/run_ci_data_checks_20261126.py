"""Run offline PR 6372/6396 repair checks with retained logs and receipts.

2026-11-26. Inputs: this checkout, an interpreter, a named lane and a fresh
evidence directory. Outputs: pytest log, JUnit XML and exit/timing receipt.
Inherited provider credentials are removed before collection. No model call.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import xml.etree.ElementTree as ET


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
            "PYTEST_ADDOPTS", "PYTEST_PLUGINS",
        }:
            del env[key]
    env.update({"PYTHONPATH": str(root / "src") + os.pathsep + str(root),
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONPYCACHEPREFIX": str(output / "bytecode")})
    command = [str(args.python), "-B", "-m", "pytest", *LANES[args.lane],
               "-q", "-p", "no:cacheprovider", "--basetemp=" + str(output / "tmp"),
               "--junitxml=" + str(output / "junit.xml")]
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    diff_hash = hashlib.sha256(subprocess.check_output(["git", "diff", "HEAD", "--"], cwd=root)).hexdigest()
    started = datetime.now(timezone.utc).isoformat()
    clock = time.monotonic()
    with (output / "pytest.log").open("x") as log:
        result = subprocess.run(command, cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT)
    post_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    post_diff_hash = hashlib.sha256(subprocess.check_output(["git", "diff", "HEAD", "--"], cwd=root)).hexdigest()
    counts = {}
    try:
        report = ET.parse(output / "junit.xml").getroot()
        suites = [report] if report.tag == "testsuite" else report.findall("testsuite")
        counts = {key: sum(int(suite.get(key, "0")) for suite in suites)
                  for key in ("tests", "failures", "errors", "skipped")}
    except (OSError, ET.ParseError, ValueError):
        pass
    artifacts_present = (output / "pytest.log").stat().st_size > 0 and bool(counts)
    stable_source = head == post_head and diff_hash == post_diff_hash
    accepted = (result.returncode == 0 and artifacts_present and stable_source
                and counts["failures"] == 0 and counts["errors"] == 0
                and (args.lane == "corpus-collect" or counts["tests"] > 0))
    receipt = {"lane": args.lane, "head": head, "command": command,
               "started_utc": started, "finished_utc": datetime.now(timezone.utc).isoformat(),
               "elapsed_seconds": time.monotonic() - clock, "exit_code": result.returncode,
               "provider_environment_cleared_before_collection": True,
               "pytest_environment_overrides_cleared": True,
               "nice_value": os.getpriority(os.PRIO_PROCESS, 0),
               "post_head": post_head, "tracked_diff_sha256": diff_hash,
               "stable_tracked_source": stable_source, "junit_counts": counts,
               "artifacts_present": artifacts_present, "accepted": accepted,
               "log": str(output / "pytest.log"), "junit": str(output / "junit.xml")}
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, sort_keys=True))
    raise SystemExit(result.returncode if result.returncode else (0 if accepted else 3))


if __name__ == "__main__":
    main()

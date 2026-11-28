#!/usr/bin/env python3
"""Exercise the CI data launcher using a fake interpreter, issue 6422.

2026-11-26. Input: a fresh output path. Outputs: stand-in argv/environment,
launcher receipt and control result. This file acts as the fake interpreter
when invoked with -m pytest; it never runs pytest, a model or a native binary.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys


def fake_interpreter() -> None:
    forbidden = ("PYTEST_ADDOPTS", "PYTEST_PLUGINS", "OPENAI_API_KEY")
    observation = {"argv": sys.argv[1:], "unexpected_environment": [key for key in forbidden if key in os.environ]}
    Path(os.environ["CI_DATA_FAKE_OBSERVATION"]).write_text(json.dumps(observation))
    junit = next(arg.split("=", 1)[1] for arg in sys.argv if arg.startswith("--junitxml="))
    mismatch = os.environ.get("CI_DATA_FAKE_MISMATCH", "none")
    failures, errors = int(mismatch == "failures"), int(mismatch == "errors")
    Path(junit).write_text(f'<testsuites><testsuite tests="1" failures="{failures}" errors="{errors}" skipped="0"/></testsuites>\n')
    print("Stand-in only: no pytest test or model call was executed.")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    env = dict(os.environ)
    env.update({"PYTEST_ADDOPTS": "-k nonexistent_filter -n 4",
                "PYTEST_PLUGINS": "nonexistent_injected_plugin",
                "OPENAI_API_KEY": "synthetic-control-only",
                "CI_DATA_FAKE_OBSERVATION": str(output / "received.json")})
    launcher = Path(__file__).with_name("run_ci_data_checks_20261126.py")
    result = subprocess.run([sys.executable, "-B", str(launcher),
                             "--python", str(Path(__file__).resolve()),
                             "--lane", "focused", "--output", str(output / "lane")],
                            env=env, capture_output=True, text=True)
    (output / "controller.stdout").write_text(result.stdout)
    (output / "controller.stderr").write_text(result.stderr)
    if result.returncode:
        raise SystemExit("fake-interpreter launcher failed; see retained output")
    received = json.loads((output / "received.json").read_text())
    receipt = json.loads((output / "lane/receipt.json").read_text())
    assert received["unexpected_environment"] == []
    assert received["argv"][:3] == ["-B", "-m", "pytest"]
    for test in ("tests/test_q19_rationale_lint.py", "tests/test_q19_blind_second_reading.py",
                 "tests/test_instrument_provenance.py", "tests/test_evaluation"):
        assert test in received["argv"]
    assert not any(arg in ("-k", "-n", "-n4") for arg in received["argv"])
    assert receipt["accepted"] and receipt["pytest_environment_overrides_cleared"]
    assert receipt["stable_tracked_source"] and receipt["artifacts_present"]
    assert receipt["junit_counts"] == {"tests": 1, "failures": 0, "errors": 0, "skipped": 0}
    for mismatch in ("failures", "errors"):
        env["CI_DATA_FAKE_MISMATCH"] = mismatch
        env["CI_DATA_FAKE_OBSERVATION"] = str(output / (mismatch + "-received.json"))
        negative = subprocess.run([sys.executable, "-B", str(launcher),
                                    "--python", str(Path(__file__).resolve()),
                                    "--lane", "focused", "--output", str(output / mismatch)],
                                   env=env, capture_output=True, text=True)
        (output / (mismatch + ".stdout")).write_text(negative.stdout)
        (output / (mismatch + ".stderr")).write_text(negative.stderr)
        refused = json.loads((output / mismatch / "receipt.json").read_text())
        assert negative.returncode == 3 and not refused["accepted"]
        assert refused["exit_code"] == 0 and refused["junit_counts"][mismatch] == 1
    final = {"status": "PASS", "mode": "stand-in only", "actual_tests_run": 0,
             "inherited_filters_plugins_and_credentials_removed": True,
             "complete_focused_argv_preserved": True, "controls_passed": 3,
             "zero_exit_with_failed_or_errored_junit_refused": True}
    (output / "result.json").write_text(json.dumps(final, indent=2) + "\n")
    print(json.dumps(final))


if __name__ == "__main__":
    if "-m" in sys.argv and "pytest" in sys.argv:
        fake_interpreter()
    else:
        main()

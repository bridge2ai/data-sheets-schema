"""CI writes no bytecode into the checkout's pinned notes/ or tests/ (#3865, #3866)."""
import os
from pathlib import Path
import subprocess

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
JOBS = yaml.safe_load((ROOT / ".github/workflows/main.yaml").read_text())["jobs"]


def steps():
    for job, spec in JOBS.items():
        for index, step in enumerate(spec.get("steps", [])):
            yield job, index, step


def runs_pytest_on(step, tree):
    run = step.get("run", "")
    return "pytest" in run and f" {tree}" in run.replace("\n", " ")


NOTES_STEPS = [(job, index, step) for job, index, step in steps() if runs_pytest_on(step, "notes/")]
CHECKS = [(job, index, step) for job, index, step in steps()
          if "git status --ignored --porcelain -- notes/" in step.get("run", "")]


def test_the_notes_controls_run_without_bytecode_and_without_a_prefix():
    """A prefix would trip transport_probe.verify_bytecode, so not that one."""
    assert {job for job, _, _ in NOTES_STEPS} == {"python-tests", "offline-audit", "offline-evaluation"}
    assert len(NOTES_STEPS) == 4
    for job, _, step in NOTES_STEPS:
        env = step.get("env", {})
        assert env.get("PYTHONDONTWRITEBYTECODE") == "1", (job, step["name"])
        assert "PYTHONPYCACHEPREFIX" not in env, (job, step["name"])


def test_the_tests_lane_compiles_its_conftest_outside_the_checkout():
    [(_, _, step)] = [s for s in steps() if runs_pytest_on(s[2], "tests ")]
    assert step["env"]["PYTHONPYCACHEPREFIX"].startswith("${{ runner.temp }}/")
    assert "PYTHONDONTWRITEBYTECODE" not in step["env"]


def trailing_check(job):
    """The check after the job's last notes/ control step."""
    last = max(index for name, index, _ in NOTES_STEPS if name == job)
    later = [step for name, index, step in CHECKS if name == job and index > last]
    assert later, job
    return later[0]


def test_every_notes_control_step_is_followed_by_a_check_in_its_job():
    for job, _, step in NOTES_STEPS:
        assert trailing_check(job).get("if") == step.get("if"), (job, step["name"])


CLEAN = ""
BYTECODE = "!! notes/matched_cborg_2026-09-13/audit_controls/__pycache__/\n"
LOCK = "!! notes/matched_cborg_2026-09-13/.canary.lock\n"
EDITED = " M notes/matched_cborg_2026-09-13/budgeted_cborg.py\n"


def check(step, tmp_path, porcelain):
    """Run the step's script against a git that reports *porcelain*."""
    stub = tmp_path / "bin"
    stub.mkdir(exist_ok=True)
    (stub / "git").write_text("#!/bin/sh\nprintf '%s' \"$STUB_PORCELAIN\"\n")
    (stub / "git").chmod(0o755)
    env = {**os.environ, "PATH": f"{stub}{os.pathsep}{os.environ['PATH']}",
           "STUB_PORCELAIN": porcelain}
    return subprocess.run(["bash", "-e", "-c", step["run"]], cwd=tmp_path, env=env,
                          capture_output=True, text=True, timeout=10)


@pytest.mark.parametrize("job", ["python-tests", "offline-audit"])
def test_scrubbed_child_bytecode_is_reported_and_anything_else_fails(job, tmp_path):
    """Pinned controls start their Python child with a whitelisted environment,
    which no step variable reaches: its bytecode is a warning, any other path fails."""
    step = trailing_check(job)
    assert check(step, tmp_path, CLEAN).returncode == 0
    reported = check(step, tmp_path, BYTECODE)
    assert reported.returncode == 0
    assert "::warning::" in reported.stdout and "audit_controls/__pycache__/" in reported.stdout
    for porcelain in (LOCK, EDITED, BYTECODE + LOCK):
        failed = check(step, tmp_path, porcelain)
        assert failed.returncode == 1, porcelain
        assert porcelain.strip().splitlines()[-1] in failed.stdout


def test_the_evaluation_lane_fails_on_any_path_including_bytecode(tmp_path):
    step = trailing_check("offline-evaluation")
    assert check(step, tmp_path, CLEAN).returncode == 0
    for porcelain in (BYTECODE, LOCK, EDITED):
        assert check(step, tmp_path, porcelain).returncode == 1, porcelain

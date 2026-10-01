"""Bytecode CI leaves in the checkout (#3865, #3866).

The suite step compiles tests/ and utils/ outside the checkout, and its check
fails on any path under notes/, tests/ or utils/. The notes/ control steps run
without writing bytecode, but a Python child the pinned controls start with a
scrubbed environment can still leave __pycache__/ under notes/: the trailing
checks on shard 1 and offline-audit report that as a warning and fail on any
other path; offline-evaluation fails on any path. This is why #3865 stays open.
"""
import os
from pathlib import Path
import subprocess

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = yaml.safe_load((ROOT / ".github/workflows/main.yaml").read_text())
JOBS = WORKFLOW["jobs"]


def steps():
    for job, spec in JOBS.items():
        for index, step in enumerate(spec.get("steps", [])):
            yield job, index, step


def effective_env(job, step, workflow=None):
    """The environment a step runs with: workflow, then job, then step `env:`.

    A variable set at workflow or job level reaches every step, so a test of a
    step's environment must read all three levels, not the step's alone (#3988).
    """
    workflow = WORKFLOW if workflow is None else workflow
    env = {}
    for level in (workflow.get("env"), workflow["jobs"][job].get("env"), step.get("env")):
        env.update(level or {})
    return env


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
        env = effective_env(job, step)
        assert env.get("PYTHONDONTWRITEBYTECODE") == "1", (job, step["name"])
        assert "PYTHONPYCACHEPREFIX" not in env, (job, step["name"])


def test_the_tests_lane_compiles_its_conftest_outside_the_checkout():
    [(job, _, step)] = [s for s in steps() if runs_pytest_on(s[2], "tests ")]
    env = effective_env(job, step)
    assert env["PYTHONPYCACHEPREFIX"].startswith("${{ runner.temp }}/")
    assert "PYTHONDONTWRITEBYTECODE" not in env


@pytest.mark.parametrize("level", ["workflow", "job", "step"])
def test_the_effective_env_reads_every_level(level):
    """A prefix at any level reaches the step, so each level must be seen (#3988)."""
    step = {"env": {"PYTHONDONTWRITEBYTECODE": "1"}}
    workflow = {"jobs": {"offline-audit": {"steps": [step]}}}
    target = {"workflow": workflow, "job": workflow["jobs"]["offline-audit"], "step": step}[level]
    target.setdefault("env", {})["PYTHONPYCACHEPREFIX"] = "/tmp/x"
    env = effective_env("offline-audit", step, workflow)
    assert env["PYTHONPYCACHEPREFIX"] == "/tmp/x"
    assert env["PYTHONDONTWRITEBYTECODE"] == "1"


def trailing_check(job):
    """The check after the job's last notes/ control step."""
    last = max(index for name, index, _ in NOTES_STEPS if name == job)
    later = [step for name, index, step in CHECKS if name == job and index > last]
    assert later, job
    return later[0]


def suite_check():
    """The check between the tests/ suite step and the first notes/ control step."""
    [(_, suite, _)] = [s for s in steps() if runs_pytest_on(s[2], "tests ")]
    first_notes = min(index for name, index, _ in NOTES_STEPS if name == "python-tests")
    [step] = [step for name, index, step in CHECKS
              if name == "python-tests" and suite < index < first_notes]
    return step


def test_every_notes_control_step_is_followed_by_a_check_in_its_job():
    for job, _, step in NOTES_STEPS:
        assert trailing_check(job).get("if") == step.get("if"), (job, step["name"])


CLEAN = ""
BYTECODE = "!! notes/matched_cborg_2026-09-13/audit_controls/__pycache__/\n"
LOCK = "!! notes/matched_cborg_2026-09-13/.canary.lock\n"
EDITED = " M notes/matched_cborg_2026-09-13/budgeted_cborg.py\n"


def check(step, tmp_path, porcelain, pathspec="notes/"):
    """Run the step's script against a git that reports *porcelain*, and require
    that the script asked git about exactly *pathspec* (the stub cannot narrow it)."""
    stub = tmp_path / "bin"
    stub.mkdir(exist_ok=True)
    (stub / "git").write_text("#!/bin/sh\nprintf '%s\\n' \"$*\" >> \"$STUB_ARGS\"\n"
                              "printf '%s' \"$STUB_PORCELAIN\"\n")
    (stub / "git").chmod(0o755)
    args = tmp_path / "git-args"
    args.write_text("")
    env = {**os.environ, "PATH": f"{stub}{os.pathsep}{os.environ['PATH']}",
           "STUB_PORCELAIN": porcelain, "STUB_ARGS": str(args)}
    result = subprocess.run(["bash", "-e", "-c", step["run"]], cwd=tmp_path, env=env,
                            capture_output=True, text=True, timeout=10)
    assert args.read_text().splitlines() == [f"status --ignored --porcelain -- {pathspec}"]
    return result


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


SUITE_BYTECODE = "!! tests/__pycache__/\n"
UTILS_BYTECODE = "!! utils/__pycache__/\n"


def test_the_suite_check_covers_notes_tests_and_utils_and_fails_on_any_path(tmp_path):
    """#3866: the prefix keeps tests/ and utils/ free of bytecode, so any path fails."""
    step = suite_check()
    spec = "notes/ tests/ utils/"
    assert check(step, tmp_path, CLEAN, spec).returncode == 0
    for porcelain in (SUITE_BYTECODE, UTILS_BYTECODE, BYTECODE, LOCK, EDITED):
        failed = check(step, tmp_path, porcelain, spec)
        assert failed.returncode == 1, porcelain
        assert porcelain.strip() in failed.stdout

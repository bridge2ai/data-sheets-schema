"""Focused Make commands must replace full discovery and retain failures."""

import json
import os
from pathlib import Path
import shlex
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
SUFFIX = ["-p", "no:cacheprovider", "--durations=25"]


def _make(*variables, dry_run=False):
    # A developer's outer Make invocation must not select paths for these
    # command-contract controls. The tested variables are explicit below.
    env = os.environ.copy()
    for name in ("MAKEFLAGS", "MFLAGS", "MAKEOVERRIDES", "PYTEST_PATHS", "PYTEST_ARGS"):
        env.pop(name, None)
    return subprocess.run(
        ["make", "--no-print-directory", *(["-n"] if dry_run else []),
         "test-python", *variables],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=30,
    )


def _recorder(tmp_path, exit_code=0):
    """Record actual shell argv without launching a second pytest session."""
    result = tmp_path / "arguments.json"
    script = tmp_path / "record arguments.py"
    script.write_text(
        "import json, pathlib, sys\n"
        f"pathlib.Path({str(result)!r}).write_text(json.dumps(sys.argv[1:]))\n"
        f"raise SystemExit({exit_code})\n"
    )
    run = "RUN=" + shlex.join([sys.executable, str(script)])
    return run, result


def test_default_make_command_retains_complete_selection():
    result = _make(dry_run=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert shlex.split(result.stdout.strip()) == [
        "poetry", "run", "pytest", "tests", "-q", *SUFFIX,
    ]


@pytest.mark.parametrize("selection, expected", [
    (None, ["tests"]),
    ("tests/test_ci_sharding.py", ["tests/test_ci_sharding.py"]),
    ("tests/test_ci_sharding.py::test_failure_and_empty_selection_cannot_pass[False]",
     ["tests/test_ci_sharding.py::test_failure_and_empty_selection_cannot_pass[False]"]),
    ("tests/test_resources.py tests/test_profiles.py",
     ["tests/test_resources.py", "tests/test_profiles.py"]),
    ("'tests/test_sample.py::test_value[two words]'",
     ["tests/test_sample.py::test_value[two words]"]),
])
def test_explicit_paths_reach_the_command_without_implicit_full_collection(tmp_path, selection, expected):
    run, recorded = _recorder(tmp_path)
    paths = [] if selection is None else ["PYTEST_PATHS=" + selection]
    result = _make(run, *paths, "PYTEST_ARGS=-v -x")
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(recorded.read_text()) == ["pytest", *expected, "-v", "-x", *SUFFIX]


@pytest.mark.parametrize("selection", ["", "   \t "])
def test_empty_selection_refuses_before_launching_any_runner(tmp_path, selection):
    run, recorded = _recorder(tmp_path)
    result = _make(run, "PYTEST_PATHS=" + selection)
    assert result.returncode != 0
    assert "PYTEST_PATHS must name at least one test path or node" in result.stderr
    assert not recorded.exists()


def test_focused_command_preserves_runner_failure(tmp_path):
    run, recorded = _recorder(tmp_path, exit_code=7)
    result = _make(run, "PYTEST_PATHS=tests/test_ci_sharding.py")
    assert result.returncode != 0
    assert json.loads(recorded.read_text()) == [
        "pytest", "tests/test_ci_sharding.py", "-q", *SUFFIX,
    ]

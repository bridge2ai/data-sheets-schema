"""The tests/ lane writes nothing under notes/ (#3771, #3772)."""
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace

import pytest

from tests import conftest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "notes/matched_cborg_2026-09-13/native_controls/native_control.py"


def outside_the_checkout(path):
    return not Path(path).resolve().is_relative_to(ROOT.resolve())


def test_bytecode_for_a_notes_tool_is_written_outside_the_checkout():
    assert sys.pycache_prefix is not None
    assert outside_the_checkout(sys.pycache_prefix)
    assert outside_the_checkout(importlib.util.cache_from_source(str(TOOL)))


def test_a_subprocess_inherits_the_bytecode_prefix():
    code = "import importlib.util, sys; print(importlib.util.cache_from_source(sys.argv[1]))"
    shown = subprocess.run([sys.executable, "-c", code, str(TOOL)], check=True,
                           capture_output=True, text=True).stdout.strip()
    assert outside_the_checkout(shown)


@pytest.fixture
def notes(monkeypatch, tmp_path):
    root = tmp_path / "notes"
    (root / "dated").mkdir(parents=True)
    (root / "dated" / "tool.py").write_text("")
    monkeypatch.setattr(conftest, "NOTES", root)
    return root


def finished(config, exitstatus=pytest.ExitCode.OK):
    session = SimpleNamespace(config=config, exitstatus=exitstatus)
    conftest.pytest_sessionfinish(session, exitstatus)
    return session


def test_a_path_added_under_notes_fails_a_passing_session(notes):
    config = SimpleNamespace()
    conftest.pytest_configure(config)
    (notes / "dated" / "__pycache__").mkdir()
    (notes / "dated" / ".canary.lock").write_text("")
    session = finished(config)
    assert session.exitstatus == pytest.ExitCode.TESTS_FAILED
    assert config._d4d_notes_added == [os.path.join("dated", ".canary.lock"),
                                       os.path.join("dated", "__pycache__")]


def test_paths_the_tree_already_had_are_not_reported(notes):
    config = SimpleNamespace()
    conftest.pytest_configure(config)
    (notes / "dated" / "tool.py").write_text("edited")
    session = finished(config)
    assert session.exitstatus == pytest.ExitCode.OK
    assert config._d4d_notes_added == []


def test_a_failing_session_keeps_its_own_status(notes):
    config = SimpleNamespace()
    conftest.pytest_configure(config)
    (notes / "leak").write_text("")
    session = finished(config, pytest.ExitCode.INTERRUPTED)
    assert session.exitstatus == pytest.ExitCode.INTERRUPTED


def test_an_xdist_worker_takes_no_listing(notes):
    config = SimpleNamespace(workerinput={})
    conftest.pytest_configure(config)
    (notes / "leak").write_text("")
    session = finished(config)
    assert session.exitstatus == pytest.ExitCode.OK
    assert not hasattr(config, "_d4d_notes_added")


LEAKING = '''
from pathlib import Path
NOTES = Path(__file__).resolve().parents[1] / "notes"

def test_leaves_a_file():
    (NOTES / "dated" / ".canary.lock").write_text("")

def test_removes_what_it_writes():
    staged = NOTES / "dated" / "staging"
    staged.write_text("")
    staged.unlink()
'''


@pytest.mark.parametrize("workers", [[], ["-n", "2"]], ids=["serial", "xdist"])
def test_the_guard_fails_a_real_run_that_leaks(tmp_path, workers):
    """Through pytest itself, with and without workers: the leak fails the
    run and is named; a file a test removes again is not a leak."""
    (tmp_path / "pytest.ini").write_text("[pytest]\n")
    (tmp_path / "notes" / "dated").mkdir(parents=True)
    (tmp_path / "tests").mkdir()
    shutil.copy(Path(conftest.__file__), tmp_path / "tests" / "conftest.py")
    (tmp_path / "tests" / "test_leak.py").write_text(LEAKING)
    run = subprocess.run([sys.executable, "-m", "pytest", "tests", "-p", "no:cacheprovider",
                          *workers], cwd=tmp_path, capture_output=True, text=True)
    assert run.returncode == pytest.ExitCode.TESTS_FAILED, run.stdout + run.stderr
    assert "2 passed" in run.stdout
    assert "notes/dated/.canary.lock" in run.stdout
    assert "staging" not in run.stdout

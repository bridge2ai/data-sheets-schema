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


def original_notes_listing(root):
    """The original per-entry normalization, kept as an equivalence oracle."""
    found = set()
    for directory, dirnames, filenames in os.walk(root):
        for name in dirnames + filenames:
            found.add(os.path.relpath(os.path.join(directory, name), root))
    return frozenset(found)


@pytest.mark.parametrize("spelling", ["path", "absolute", "relative", "trailing", "dotted", "bytes"])
def test_listing_matches_original_for_all_entries(tmp_path, monkeypatch, spelling):
    root = tmp_path / "notes"
    (root / ".hidden" / "empty").mkdir(parents=True)
    (root / "ignored" / "nested").mkdir(parents=True)
    (root / ".gitignore").write_text("ignored/\n")
    (root / ".hidden" / "space café.txt").write_text("")
    (root / "ignored" / "nested" / "tool.py").write_text("")
    monkeypatch.chdir(tmp_path)
    argument = {
        "path": root,
        "absolute": str(root),
        "relative": "notes",
        "trailing": str(root) + os.sep,
        "dotted": os.path.join(".", "notes", "..", "notes"),
        "bytes": os.fsencode(root),
    }[spelling]
    expected = {
        ".hidden", os.path.join(".hidden", "empty"),
        os.path.join(".hidden", "space café.txt"), ".gitignore", "ignored",
        os.path.join("ignored", "nested"), os.path.join("ignored", "nested", "tool.py"),
    }
    if isinstance(argument, bytes):
        expected = {os.fsencode(path) for path in expected}
    assert conftest.notes_listing(argument) == original_notes_listing(argument) == frozenset(expected)


@pytest.mark.parametrize("kind", ["empty", "missing", "file"])
def test_listing_empty_or_non_directory_roots_matches_original(tmp_path, kind):
    root = tmp_path / kind
    if kind == "empty":
        root.mkdir()
    elif kind == "file":
        root.write_text("")
    for argument in (root, os.fsencode(root)):
        assert conftest.notes_listing(argument) == original_notes_listing(argument) == frozenset()


def test_listing_includes_links_without_following_directory_links(tmp_path):
    root = tmp_path / "notes"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "not_walked.txt").write_text("")
    root_link = tmp_path / "notes_link"
    try:
        (root / "directory_link").symlink_to(outside, target_is_directory=True)
        (root / "file_link").symlink_to(outside / "not_walked.txt")
        (root / "broken_link").symlink_to(tmp_path / "missing_target")
        root_link.symlink_to(root, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"symlink creation unavailable: {error}")
    expected = frozenset({"directory_link", "file_link", "broken_link"})
    for argument in (root, root_link):
        assert conftest.notes_listing(argument) == original_notes_listing(argument) == expected
    encoded = os.fsencode(root)
    assert conftest.notes_listing(encoded) == original_notes_listing(encoded) == {
        os.fsencode(path) for path in expected
    }


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

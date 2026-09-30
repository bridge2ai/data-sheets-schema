"""Lane-wide hygiene for the tests/ collection: no test writes under notes/.

Two parts, both scoped to this directory's collection. A repository-root
conftest would also reach the ``pytest notes/matched_cborg_2026-09-13/...``
jobs CI runs separately, and that environment is left as it is.

* Bytecode goes outside the checkout (#3771). Tests import and
  ``exec_module`` the dated execution tools under ``notes/``, which wrote
  ``__pycache__`` beside them, into pinned directories. ``sys.pycache_prefix``
  moves every ``.pyc`` this process writes, and ``PYTHONPYCACHEPREFIX`` does
  the same for the subprocesses that inherit the environment. A prefix
  already chosen by the caller (``-X pycache_prefix`` or the variable) is
  kept.
* No test may add a path under ``notes/`` (#3772). The tree is listed once
  when the session is configured and again when it finishes, in the process
  that runs the session: under pytest-xdist that is the controller, before
  any worker starts and after every worker has stopped, so a sibling
  worker's in-flight file is never read as a leak (#3778). Paths the tree
  already had are not reported, so a stale checkout does not fail. A note
  written by hand into the same checkout during the run is reported too;
  the listing cannot tell who wrote it.
"""
import os
from pathlib import Path
import sys
import tempfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
NOTES = ROOT / "notes"

if sys.pycache_prefix is None:
    sys.pycache_prefix = str(Path(tempfile.gettempdir()) / "d4d-tests-pycache")
os.environ.setdefault("PYTHONPYCACHEPREFIX", sys.pycache_prefix)


def notes_listing(root):
    """Every file, directory and link under *root*, relative to it."""
    found = set()
    for directory, dirnames, filenames in os.walk(root):
        for name in dirnames + filenames:
            found.add(os.path.relpath(os.path.join(directory, name), root))
    return frozenset(found)


def _runs_the_session(config):
    """False in a pytest-xdist worker, which sees only its share of tests."""
    return not hasattr(config, "workerinput")


def pytest_configure(config):
    if _runs_the_session(config):
        config._d4d_notes_before = notes_listing(NOTES)


def pytest_sessionfinish(session, exitstatus):
    before = getattr(session.config, "_d4d_notes_before", None)
    if before is None:
        return
    added = sorted(notes_listing(NOTES) - before)
    session.config._d4d_notes_added = added
    if added and session.exitstatus == pytest.ExitCode.OK:
        session.exitstatus = pytest.ExitCode.TESTS_FAILED


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    added = getattr(config, "_d4d_notes_added", None)
    if not added:
        return
    terminalreporter.section("paths added under notes/ during the run (#3772)", red=True)
    for path in added[:50]:
        terminalreporter.write_line(f"notes/{path}")
    if len(added) > 50:
        terminalreporter.write_line(f"... and {len(added) - 50} more")
    terminalreporter.write_line(
        "A test must write under tmp_path, never into the checkout's notes/.")

"""D68-D70/#5212 review item 7 / LR8 logger canary, 2026-10-30.

Input: pytest checkout and basetemp. Output: one phase report proving live
logging leaves the complete checkout unchanged outside the designated scratch.
Outside CI; this validates the serial gate harness, not production behavior.
"""
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def unchanged_checkout(tmp_path_factory):
    scratch = tmp_path_factory.getbasetemp().resolve()

    def snapshot():
        entries = {}
        for directory, dirs, files in os.walk(ROOT):
            base = Path(directory)
            dirs[:] = [name for name in dirs
                       if name != ".git" and (base / name).resolve() != scratch]
            for name in dirs + files:
                path = base / name
                if path == ROOT / ".git":
                    continue
                stat = path.lstat()
                entries[str(path.relative_to(ROOT))] = (
                    stat.st_mode, stat.st_size, stat.st_mtime_ns, stat.st_ino)
        return entries

    before = snapshot()
    yield
    assert snapshot() == before, "logger changed checkout outside pytest scratch"


def test_live_log_preserves_checkout(unchanged_checkout):
    # Pytest emits the call-result marker before the fixture's teardown check.
    assert ROOT.is_dir()

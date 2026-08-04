"""Tests for the large-file guard.

The pure part is tested directly; the git-facing part is exercised against a
real throwaway repository rather than a mock, because what this check has to get
right is exactly the thing a mock would paper over — which commits `git diff`
considers, and whether a merge base is used.
"""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from check_large_files import (  # noqa: E402
    MAX_BYTES,
    blob_size,
    changed_files,
    human,
    main,
    oversized,
)


class TestHumanSize(unittest.TestCase):
    """Fixed MB printed every sub-megabyte offender as "0.00 MB"."""

    def test_scales_to_the_magnitude(self):
        self.assertEqual(human(512), "512 B")
        self.assertEqual(human(5 * 1024), "5.00 KB")
        self.assertEqual(human(5 * 1024 ** 2), "5.00 MB")
        self.assertEqual(human(3 * 1024 ** 3), "3.00 GB")

    def test_no_size_renders_as_zero_of_a_larger_unit(self):
        for n in (1, 999, 5000, 1048575):
            self.assertNotIn("0.00 MB", human(n))


class TestOversized(unittest.TestCase):
    def test_nothing_over_the_limit(self):
        self.assertEqual(oversized({"a": 10, "b": 20}, limit=100), [])

    def test_boundary_is_exclusive(self):
        """Exactly at the limit passes; one byte over does not."""
        self.assertEqual(oversized({"a": 100}, limit=100), [])
        self.assertEqual(oversized({"a": 101}, limit=100), [("a", 101)])

    def test_every_offender_is_reported_largest_first(self):
        """Not just the first.

        A PR adding three large files should learn that in one run, and a
        report that shows a subset reads as "this is all of it".
        """
        found = oversized({"small": 1, "big": 300, "mid": 200, "huge": 900}, limit=100)
        self.assertEqual([p for p, _ in found], ["huge", "big", "mid"])

    def test_the_default_limit_is_the_documented_one(self):
        self.assertEqual(MAX_BYTES, 10 * 1024 * 1024)


class TestAgainstARealRepository(unittest.TestCase):
    """Against real git, because the mock-able parts are not the risky parts."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        self._git("init", "-q", "-b", "main")
        self._git("config", "user.email", "t@example.invalid")
        self._git("config", "user.name", "T")
        (self.repo / "base.txt").write_text("base")
        self._git("add", "-A")
        self._git("commit", "-qm", "base")
        self._git("checkout", "-q", "-b", "feature")

    def tearDown(self):
        self._tmp.cleanup()

    def _git(self, *args):
        return subprocess.run(("git",) + args, cwd=self.repo,
                              capture_output=True, text=True, check=True).stdout

    def _commit(self, name, content):
        (self.repo / name).write_text(content)
        self._git("add", "-A")
        self._git("commit", "-qm", f"add {name}")

    def test_added_file_is_seen_and_sized(self):
        self._commit("new.txt", "x" * 5000)
        import os
        cwd = os.getcwd()
        os.chdir(self.repo)
        try:
            self.assertIn("new.txt", changed_files("main"))
            self.assertEqual(blob_size("new.txt"), 5000)
        finally:
            os.chdir(cwd)

    def test_a_deletion_is_not_an_offence(self):
        """Removing a large file is the fix, not the problem."""
        import os
        (self.repo / "gone.txt").write_text("y" * 5000)
        self._git("add", "-A")
        self._git("commit", "-qm", "add gone")
        self._git("rm", "-q", "gone.txt")
        self._git("commit", "-qm", "remove gone")
        cwd = os.getcwd()
        os.chdir(self.repo)
        try:
            self.assertNotIn("gone.txt", changed_files("main"))
        finally:
            os.chdir(cwd)

    def test_files_landing_on_the_base_afterwards_are_not_blamed(self):
        """Merge base, not base tip.

        A long-running branch must be judged on what it adds. Diffing against
        the moving tip of main would blame it for a large file somebody else
        committed in the meantime, and the author could do nothing about it.
        """
        import os
        self._commit("mine.txt", "small")
        self._git("checkout", "-q", "main")
        (self.repo / "theirs.txt").write_text("z" * 9000)
        self._git("add", "-A")
        self._git("commit", "-qm", "someone else adds a big file")
        self._git("checkout", "-q", "feature")
        cwd = os.getcwd()
        os.chdir(self.repo)
        try:
            changed = changed_files("main")
            self.assertIn("mine.txt", changed)
            self.assertNotIn("theirs.txt", changed,
                             "the branch must not be blamed for main's files")
        finally:
            os.chdir(cwd)

    def test_main_fails_on_an_oversized_file_and_passes_otherwise(self):
        import os
        self._commit("big.bin", "q" * 4096)
        cwd = os.getcwd()
        os.chdir(self.repo)
        try:
            self.assertEqual(main(["--base", "main", "--limit", "10000"]), 0)
            self.assertEqual(main(["--base", "main", "--limit", "1000"]), 1)
        finally:
            os.chdir(cwd)

    def test_no_changes_is_a_pass_not_a_crash(self):
        import os
        cwd = os.getcwd()
        os.chdir(self.repo)
        try:
            self.assertEqual(main(["--base", "main"]), 0)
        finally:
            os.chdir(cwd)

    def test_a_true_rename_adds_no_bytes_and_is_ignored(self):
        """The blob already exists in history; moving it costs nothing (#267).

        The file has to pre-exist on `main` for this to be a rename at all. A
        file created on the branch and then moved is, relative to the merge
        base, simply a new file at its final path — and flagging that is right,
        because its blob is new to history either way.
        """
        import os
        self._git("checkout", "-q", "main")
        (self.repo / "big.bin").write_text("x" * 9000)
        self._git("add", "-A")
        self._git("commit", "-qm", "big.bin lands on main")
        self._git("checkout", "-q", "feature")
        self._git("merge", "-q", "main", "-m", "merge")
        self._git("mv", "big.bin", "moved.bin")
        self._git("commit", "-qm", "rename")
        cwd = os.getcwd()
        os.chdir(self.repo)
        try:
            self.assertNotIn("moved.bin", changed_files("main"),
                             "moving an existing blob adds nothing to history")
        finally:
            os.chdir(cwd)

    def test_a_rename_detected_new_blob_is_still_weighed(self):
        """Similar-but-not-identical is a new object wearing a rename's clothes.

        git reports >50%-similar delete+add as R. The destination is a blob
        that does not exist in history yet, so it has to be sized.
        """
        import os
        self._commit("orig.bin", "y" * 9000)
        (self.repo / "orig.bin").unlink()
        (self.repo / "copy.bin").write_text("y" * 8000 + "DIFFERENT" * 100)
        self._git("add", "-A")
        self._git("commit", "-qm", "delete one, add a similar one")
        cwd = os.getcwd()
        os.chdir(self.repo)
        try:
            self.assertIn("copy.bin", changed_files("main"),
                          "a rename-detected new blob must not slip past")
        finally:
            os.chdir(cwd)

    def test_a_missing_base_ref_fails_closed_with_a_readable_message(self):
        """#266: exit non-zero, and say what to do about it."""
        import io
        import os
        from contextlib import redirect_stderr
        cwd = os.getcwd()
        os.chdir(self.repo)
        try:
            err = io.StringIO()
            with redirect_stderr(err):
                code = main(["--base", "origin/does-not-exist"])
            self.assertEqual(code, 1, "must fail closed, never wave the PR through")
            self.assertIn("not found", err.getvalue())
            self.assertIn("fetch-depth", err.getvalue())
        finally:
            os.chdir(cwd)


if __name__ == "__main__":
    unittest.main()

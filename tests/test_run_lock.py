"""A sweep must be findable and stoppable without guessing a pattern (#513).

On 2026-08-11 a `d4d api batch` was asked to stop. `pkill -f "d4d api"` matched
nothing and `pgrep -f "d4d api"` returned 0, so it was reported stopped. It ran
for about two more hours, because a console-script entry point runs as
`python -c import sys; from importlib import import_module; …` and carries none
of its own name.

A second batch was then launched for the same labels while the first was alive,
so two processes wrote the same directories for two hours.
"""

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from data_sheets_schema import run_lock


class TestAcquireAndRelease(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)

    def test_a_lock_names_the_process_and_what_it_is_doing(self):
        run_lock.acquire("2026-08-11_x", ["AI_READI", "CHORUS"], self.dir)
        [lock] = run_lock.live(self.dir)
        self.assertEqual(lock.pid, os.getpid())
        self.assertEqual(lock.label_prefix, "2026-08-11_x")
        self.assertEqual(lock.projects, ["AI_READI", "CHORUS"])

    def test_a_second_acquire_is_refused(self):
        """Two batches on one label is not a race to tolerate: both write
        phase snapshots and a progress file under the same names."""
        run_lock.acquire("dup", ["A"], self.dir)
        with self.assertRaises(run_lock.AlreadyRunning):
            run_lock.acquire("dup", ["A"], self.dir)

    def test_the_refusal_says_how_to_stop_it(self):
        run_lock.acquire("dup", ["A"], self.dir)
        with self.assertRaises(run_lock.AlreadyRunning) as ctx:
            run_lock.acquire("dup", ["A"], self.dir)
        self.assertIn("d4d api stop", str(ctx.exception))

    def test_a_different_label_is_not_blocked(self):
        run_lock.acquire("one", ["A"], self.dir)
        run_lock.acquire("two", ["A"], self.dir)
        self.assertEqual(len(run_lock.live(self.dir)), 2)

    def test_release_frees_the_label(self):
        path = run_lock.acquire("x", ["A"], self.dir)
        run_lock.release(path)
        run_lock.acquire("x", ["A"], self.dir)     # must not raise

    def test_release_of_a_missing_lock_is_not_an_error(self):
        """Release must never be the thing that fails at the end of an
        otherwise successful sweep."""
        run_lock.release(self.dir / "absent.json")

    def test_no_locks_is_not_an_error(self):
        self.assertEqual(run_lock.live(self.dir), [])
        self.assertEqual(run_lock.stale(self.dir), [])


class TestStaleLocks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)

    def _write(self, pid, label="x"):
        (self.dir / f"{label}.json").write_text(json.dumps({
            "pid": pid, "label_prefix": label, "projects": [],
            "started": "t"}), encoding="utf-8")

    def test_a_dead_pid_is_stale_not_live(self):
        """A lock left by a hard kill must not block the next sweep for ever —
        that would turn a crash into a permanent block."""
        self._write(2 ** 22)                       # implausible pid
        self.assertEqual(run_lock.live(self.dir), [])
        self.assertEqual(len(run_lock.stale(self.dir)), 1)

    def test_a_stale_lock_does_not_refuse_a_new_acquire(self):
        self._write(2 ** 22, "x")
        run_lock.acquire("x", ["A"], self.dir)     # must not raise

    def test_stale_locks_are_reported_not_silently_deleted(self):
        """A leftover lock is evidence a sweep died without cleaning up."""
        self._write(2 ** 22)
        run_lock.stale(self.dir)
        self.assertTrue((self.dir / "x.json").exists())

    def test_an_unreadable_lock_is_ignored_rather_than_fatal(self):
        (self.dir / "bad.json").write_bytes(b"\xff\xfe not json")
        self.assertEqual(run_lock.live(self.dir), [])


class TestAgainstARealProcess(unittest.TestCase):
    """The property that actually failed: found by lock, not by name."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.child = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(60)"])
        self.addCleanup(self._reap)
        (self.dir / "real.json").write_text(json.dumps({
            "pid": self.child.pid, "label_prefix": "real",
            "projects": ["A"], "started": "t"}), encoding="utf-8")

    def _reap(self):
        try:
            self.child.kill()
            self.child.wait(timeout=5)
        except Exception:                                    # noqa: BLE001
            pass

    def test_pgrep_by_name_does_not_find_it(self):
        """The premise. If this ever starts finding it, the lock is still
        correct but this test has stopped demonstrating why it exists."""
        found = subprocess.run(["pgrep", "-f", "d4d api"],
                               capture_output=True, text=True).stdout
        self.assertNotIn(str(self.child.pid), found)

    def test_the_lock_finds_it(self):
        self.assertEqual([l.pid for l in run_lock.live(self.dir)],
                         [self.child.pid])

    def test_stop_actually_stops_it(self):
        [lock] = run_lock.live(self.dir)
        self.assertTrue(run_lock.stop(lock))
        for _ in range(50):
            if not lock.alive:
                break
            time.sleep(0.1)
        self.assertFalse(lock.alive, "process survived SIGTERM")

    def test_it_becomes_stale_once_stopped(self):
        [lock] = run_lock.live(self.dir)
        run_lock.stop(lock)
        for _ in range(50):
            if not lock.alive:
                break
            time.sleep(0.1)
        self.assertEqual(run_lock.live(self.dir), [])
        self.assertEqual(len(run_lock.stale(self.dir)), 1)

"""One SchemaView per schema file (#926).

linkml_runtime's SchemaView caches its methods with `lru_cache(None)`, which
keys on `self`: a view is pinned for the life of the process by its own
caches, and `del` frees nothing. The suite's API-runner tests built ~24 views
per `execute()` and reached 14 GB in one file — the 7 GB CI runner died of it
on every run and reported a runner shutdown, never a test.
"""

import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from data_sheets_schema import schema_view
from data_sheets_schema.api_runner import FULL_SCHEMA_PATH

SRC = Path("src/data_sheets_schema")


class TestSharing(unittest.TestCase):
    def test_the_same_file_gives_the_same_view(self):
        a = schema_view.shared_view(FULL_SCHEMA_PATH)
        b = schema_view.shared_view(str(Path(FULL_SCHEMA_PATH).resolve()))
        self.assertIs(a, b)

    def test_a_rewritten_file_gives_a_new_view_and_drops_the_old_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "s.yaml"
            p.write_text("id: https://example.org/s\nname: s\nclasses:\n  A: {}\n")
            first = schema_view.shared_view(p)
            held = schema_view.views_held()
            p.write_text("id: https://example.org/s\nname: s\nclasses:\n  A: {}\n  B: {}\n")
            import os, time
            os.utime(p, ns=(time.time_ns(), time.time_ns() + 1_000_000))
            second = schema_view.shared_view(p)
            self.assertIsNot(first, second)
            self.assertIn("B", second.all_classes())
            self.assertEqual(schema_view.views_held(), held,
                             "the stale key must be dropped, not kept beside the new one")


class TestNoSiteBuildsItsOwn(unittest.TestCase):
    """The property that keeps the leak fixed: a new `SchemaView(` in the
    package is a new pinned view per call."""

    ALLOWED = {"schema_view.py", "cli/rocrate.py"}   # the factory; one-shot CLI

    def test_every_in_process_site_uses_the_shared_view(self):
        offenders = []
        for path in SRC.rglob("*.py"):
            rel = str(path.relative_to(SRC))
            if rel in self.ALLOWED:
                continue
            for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if re.search(r"\bSchemaView\(", line) and not line.lstrip().startswith("#"):
                    offenders.append(f"{rel}:{n}")
        self.assertEqual(offenders, [])


class TestTheSyncCheckDoesNotGrow(unittest.TestCase):
    """`schema_sync.check` digested a byte-identical rebuild at a fresh temp
    path every call: one pinned view and one digest-cache entry per check,
    forever. In-sync checks must leave both caches where they were."""

    def test_an_in_sync_check_adds_no_views_and_no_digest_entries(self):
        from data_sheets_schema import schema_digest, schema_sync
        if not Path(schema_sync.MERGED_SCHEMAS[0][0]).exists():
            self.skipTest("merged schema not present")
        schema_sync.check()                                   # warm
        views, builds = schema_view.views_held(), len(schema_digest._BUILD_CACHE)
        rows = schema_sync.check()
        self.assertTrue(all(r["status"] == schema_sync.IN_SYNC for r in rows))
        self.assertEqual(schema_view.views_held(), views)
        self.assertEqual(len(schema_digest._BUILD_CACHE), builds)


class TestLinkmlStillPinsViews(unittest.TestCase):
    """The premise. If a linkml upgrade stops pinning discarded views, this
    module is a harmless cache and the docstrings above are history — say so
    here rather than leave the explanation asserting something false."""

    def test_a_discarded_view_survives_collection(self):
        code = (
            "import gc\n"
            "from linkml_runtime import SchemaView\n"
            f"sv = SchemaView({str(FULL_SCHEMA_PATH)!r}); sv.class_induced_slots('Dataset'); del sv; gc.collect()\n"
            "print(sum(1 for o in gc.get_objects() if type(o).__name__ == 'SchemaView'))\n")
        out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr[-500:])
        self.assertEqual(out.stdout.strip(), "1",
                         "linkml no longer pins discarded views; revisit schema_view.py's rationale")

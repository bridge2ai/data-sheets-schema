"""One parse of a schema file per process (#1203).

The merged schema is 1.4 MB and was parsed from disk on every call by three
production paths, seven times per record write. These pin what the cache must
not get wrong: an edit in place is seen, a copy is a different entry, a caller
cannot poison the next caller's read, and a rebuild is redone when any module
the merged schema derives from changes.
"""
import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path

from data_sheets_schema import schema_cache


def _write(p: Path, text: str, mtime_ns: int | None = None) -> None:
    p.write_text(text, encoding="utf-8")
    if mtime_ns is not None:
        os.utime(p, ns=(mtime_ns, mtime_ns))


class TheParseCache(unittest.TestCase):
    def setUp(self):
        schema_cache.clear()
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.p = Path(self.tmp.name) / "s.yaml"
        _write(self.p, "prefixes:\n  doi: https://doi.org/\n", mtime_ns=1_000_000_000)

    def test_the_second_read_is_served_without_parsing(self):
        first = schema_cache.load_schema(self.p)
        info = schema_cache._parsed.cache_info()
        schema_cache.load_schema(self.p)
        self.assertEqual(schema_cache._parsed.cache_info().hits, info.hits + 1)
        self.assertEqual(first, {"prefixes": {"doi": "https://doi.org/"}})

    def test_an_edit_in_place_is_seen(self):
        schema_cache.load_schema(self.p)
        _write(self.p, "prefixes:\n  ror: https://ror.org/\n", mtime_ns=2_000_000_000)
        self.assertEqual(schema_cache.load_schema(self.p), {"prefixes": {"ror": "https://ror.org/"}})

    def test_a_same_size_edit_in_the_same_mtime_tick_is_the_one_blind_spot_and_clear_covers_it(self):
        """The key is path, mtime and size. A file rewritten with the same size
        inside one mtime tick cannot be told apart by any of them; a test that
        does that calls `clear`. Pinned so the limitation is stated, not
        discovered."""
        schema_cache.load_schema(self.p)
        _write(self.p, "prefixes:\n  dio: https://doi.org/\n", mtime_ns=1_000_000_000)   # same size, same mtime
        self.assertEqual(schema_cache.load_schema(self.p), {"prefixes": {"doi": "https://doi.org/"}})
        schema_cache.clear()
        self.assertEqual(schema_cache.load_schema(self.p), {"prefixes": {"dio": "https://doi.org/"}})

    def test_a_copy_elsewhere_is_a_different_entry(self):
        q = Path(self.tmp.name) / "copy.yaml"
        shutil.copy2(self.p, q)
        _write(q, "prefixes:\n  ror: https://ror.org/\n", mtime_ns=1_000_000_000)
        self.assertEqual(schema_cache.load_schema(self.p)["prefixes"], {"doi": "https://doi.org/"})
        self.assertEqual(schema_cache.load_schema(q)["prefixes"], {"ror": "https://ror.org/"})

    def test_a_caller_that_mutates_its_copy_does_not_poison_the_next(self):
        doc = schema_cache.load_schema(self.p)
        doc["prefixes"]["evil"] = "x"
        doc["prefixes"].clear()
        self.assertEqual(schema_cache.load_schema(self.p), {"prefixes": {"doi": "https://doi.org/"}})

    def test_a_missing_file_raises_like_a_read(self):
        with self.assertRaises(FileNotFoundError):
            schema_cache.load_schema(Path(self.tmp.name) / "absent.yaml")

    def test_the_digest_is_cached_and_invalidated_the_same_way(self):
        a = schema_cache.sha256_of(self.p)
        self.assertEqual(schema_cache.sha256_of(self.p), a)
        _write(self.p, "prefixes:\n  ror: https://ror.org/\n", mtime_ns=3_000_000_000)
        self.assertNotEqual(schema_cache.sha256_of(self.p), a)


class TheRebuildCache(unittest.TestCase):
    """`schema_sync._regenerate` spawned `poetry run gen-linkml` on every
    record write. Its bytes are a pure function of the source tree, so a
    second call inside one process with nothing changed is served from
    memory — and any change to any module invalidates it."""

    def test_the_key_is_the_whole_source_tree_not_only_the_named_source(self):
        from data_sheets_schema import schema_sync
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            src = d / "data_sheets_schema.yaml"; _write(src, "id: x\n", 1_000_000_000)
            mod = d / "D4D_Module.yaml"; _write(mod, "classes: {}\n", 1_000_000_000)
            k1 = schema_sync._source_state(src)
            _write(mod, "classes: {A: {}}\n", 2_000_000_000)          # a module changed, the source did not
            k2 = schema_sync._source_state(src)
            self.assertNotEqual(k1, k2)
            # the merged outputs beside the sources are not part of the key
            (d / "data_sheets_schema_all.yaml").write_text("generated\n")
            self.assertEqual(schema_sync._source_state(src), k2)

    def test_a_hit_writes_the_cached_bytes_and_spawns_nothing(self):
        from unittest import mock

        from data_sheets_schema import schema_sync
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            src = d / "data_sheets_schema.yaml"; _write(src, "id: x\n", 1_000_000_000)
            key = (schema_sync._source_state(src), False)
            schema_sync._REBUILT[key] = b"merged bytes\n"
            self.addCleanup(schema_sync._REBUILT.pop, key, None)
            target = d / "out.yaml"
            with mock.patch.object(schema_sync.subprocess, "run", side_effect=AssertionError("spawned")):
                ok, why = schema_sync._regenerate(src, target, marker=False)
            self.assertEqual((ok, why), (True, None))
            self.assertEqual(target.read_bytes(), b"merged bytes\n")

    def test_a_failed_rebuild_is_not_cached(self):
        from unittest import mock

        from data_sheets_schema import schema_sync
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            src = d / "data_sheets_schema.yaml"; _write(src, "id: x\n", 1_000_000_000)
            key = (schema_sync._source_state(src), False)
            schema_sync._REBUILT.pop(key, None)
            failed = mock.Mock(returncode=1, stderr="boom", stdout="")
            with mock.patch.object(schema_sync.subprocess, "run", return_value=failed):
                ok, why = schema_sync._regenerate(src, d / "out.yaml", marker=False)
            self.assertFalse(ok); self.assertIn("gen-linkml failed", why)
            self.assertNotIn(key, schema_sync._REBUILT)

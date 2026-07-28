"""Tests for manifest-driven fetch.

The value of this module is that a fresh clone can rebuild the corpus without
the input sheet. The failure that matters most is the quiet one: writing a
truncated or wrong artifact over a corpus file, so that generation runs consume
something different without anything announcing it. Most of these tests are
about refusing to do that.
"""

import unittest
import tempfile
from pathlib import Path

import yaml

import data_sheets_schema.fetch as F
from data_sheets_schema.fetch import (
    FetchResult,
    Source,
    audit,
    fetch_source,
    load_sources,
    missing,
)


def write_manifest(root: Path, entries: dict) -> Path:
    p = root / "source_manifest.yaml"
    p.write_text(yaml.safe_dump({"version": 1, "projects": entries}),
                 encoding="utf-8")
    return p


class FakeExtractor:
    """Stands in for OrganizedDatasetExtractor, with no network."""

    def __init__(self, payload=b"x" * 2000, suffix=".html", downloaded=True,
                 extra=None, raise_exc=None):
        self.payload, self.suffix = payload, suffix
        self.downloaded, self.extra, self.raise_exc = downloaded, extra, raise_exc
        self.calls = []

    def _process_url(self, url, column_dir, row):
        self.calls.append(url)
        if self.raise_exc:
            raise self.raise_exc
        column_dir.mkdir(parents=True, exist_ok=True)
        f = column_dir / f"handler_output{self.suffix}"
        f.write_bytes(self.payload)
        for name, blob in (self.extra or {}).items():
            (column_dir / name).write_bytes(blob)
        return {"downloaded": self.downloaded, "path": str(f)}


class FetchTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self._raw, self._proc = F.RAW_DIR, F.PROCESSED_DIR
        F.RAW_DIR = self.root / "raw"
        F.PROCESSED_DIR = self.root / "processed"
        self.addCleanup(self._restore)

    def _restore(self):
        F.RAW_DIR, F.PROCESSED_DIR = self._raw, self._proc

    def src(self, **kw):
        base = dict(project="CHORUS", id="s1", url="https://example.org/a",
                    raw_file="a.html", processed_file="a.txt")
        base.update(kw)
        return Source(**base)


class TestLoadAndMissing(FetchTestCase):
    def test_loads_every_project_entry(self):
        m = write_manifest(self.root, {
            "CHORUS": [{"id": "a", "url": "u", "raw_file": "a.html",
                        "processed_file": "a.txt"}],
            "VOICE": [{"id": "b", "url": "u2", "raw_file": "b.pdf",
                       "processed_file": "b.txt"}],
        })
        s = load_sources(m)
        self.assertEqual({x.id for x in s}, {"a", "b"})
        self.assertEqual({x.project for x in s}, {"CHORUS", "VOICE"})

    def test_project_filter(self):
        m = write_manifest(self.root, {
            "CHORUS": [{"id": "a", "url": "u", "raw_file": "a.html",
                        "processed_file": "a.txt"}],
            "VOICE": [{"id": "b", "url": "u2", "raw_file": "b.pdf",
                       "processed_file": "b.txt"}],
        })
        self.assertEqual([x.id for x in load_sources(m, ["VOICE"])], ["b"])

    def test_missing_reflects_disk(self):
        s = self.src()
        self.assertEqual(missing([s]), [s])
        s.raw_path.parent.mkdir(parents=True, exist_ok=True)
        s.raw_path.write_text("hi")
        self.assertEqual(missing([s]), [])


class TestFetchSource(FetchTestCase):
    def test_writes_to_the_manifest_declared_filename(self):
        """Not the handler's own name — the manifest is the authority."""
        s = self.src(raw_file="canonical_name_2026-01-01.html")
        r = fetch_source(s, extractor=FakeExtractor())
        self.assertEqual(r.status, "fetched", r.detail)
        self.assertTrue(s.raw_path.exists())
        self.assertEqual(s.raw_path.name, "canonical_name_2026-01-01.html")

    def test_existing_file_is_not_overwritten(self):
        s = self.src()
        s.raw_path.parent.mkdir(parents=True, exist_ok=True)
        s.raw_path.write_text("ORIGINAL CORPUS BYTES")
        ex = FakeExtractor()
        r = fetch_source(s, extractor=ex)
        self.assertEqual(r.status, "skipped_present")
        self.assertEqual(s.raw_path.read_text(), "ORIGINAL CORPUS BYTES")
        self.assertEqual(ex.calls, [], "must not even hit the network")

    def test_force_overwrites(self):
        s = self.src()
        s.raw_path.parent.mkdir(parents=True, exist_ok=True)
        s.raw_path.write_text("old")
        r = fetch_source(s, force=True, extractor=FakeExtractor())
        self.assertEqual(r.status, "fetched")
        self.assertNotEqual(s.raw_path.read_text(), "old")

    def test_dry_run_writes_nothing(self):
        s = self.src()
        ex = FakeExtractor()
        r = fetch_source(s, dry_run=True, extractor=ex)
        self.assertEqual(r.status, "dry_run")
        self.assertFalse(s.raw_path.exists())
        self.assertEqual(ex.calls, [])

    def test_short_artifact_is_refused(self):
        """A truncated page must never land on a corpus filename."""
        s = self.src(minimum_characters=5000)
        r = fetch_source(s, extractor=FakeExtractor(payload=b"tiny"))
        self.assertEqual(r.status, "failed")
        self.assertIn("below the 5000b floor", r.detail)
        self.assertFalse(s.raw_path.exists())

    def test_default_floor_applies_when_manifest_is_silent(self):
        s = self.src()  # no minimum_characters
        r = fetch_source(s, extractor=FakeExtractor(payload=b"z" * 10))
        self.assertEqual(r.status, "failed")
        self.assertFalse(s.raw_path.exists())

    def test_handler_failure_is_reported_not_raised(self):
        s = self.src()
        r = fetch_source(s, extractor=FakeExtractor(downloaded=False))
        self.assertEqual(r.status, "failed")
        self.assertFalse(s.raw_path.exists())

    def test_handler_exception_is_caught(self):
        s = self.src()
        r = fetch_source(s, extractor=FakeExtractor(raise_exc=RuntimeError("boom")))
        self.assertEqual(r.status, "failed")
        self.assertIn("RuntimeError", r.detail)

    def test_picks_the_artifact_matching_the_declared_extension(self):
        """Dataverse emits .html and .txt; FAIRhub emits .html and a small .json.

        Choosing by extension is what stops a 110-byte info blob being written
        over a 133 KB API record — the real failure this guards.
        """
        s = self.src(raw_file="want.json")
        ex = FakeExtractor(payload=b"{}" + b" " * 3000, suffix=".json",
                           extra={"decoy.html": b"h" * 90000})
        r = fetch_source(s, extractor=ex)
        self.assertEqual(r.status, "fetched", r.detail)
        self.assertTrue(s.raw_path.read_bytes().startswith(b"{}"))

    def test_missing_declared_extension_fails_rather_than_guessing(self):
        s = self.src(raw_file="want.json")
        r = fetch_source(s, extractor=FakeExtractor(suffix=".html"))
        self.assertEqual(r.status, "failed")
        self.assertIn("no .json artifact", r.detail)

    def test_entry_without_url_is_reported(self):
        r = fetch_source(self.src(url=""), extractor=FakeExtractor())
        self.assertEqual(r.status, "no_url")


class TestManualSources(FetchTestCase):
    """Captures no handler can reproduce must be named, not silently retried."""

    def test_manual_source_is_never_fetched(self):
        s = self.src(fetch="manual")
        ex = FakeExtractor()
        r = fetch_source(s, extractor=ex)
        self.assertEqual(r.status, "manual")
        self.assertEqual(ex.calls, [])

    def test_manual_and_absent_is_flagged_unrecoverable(self):
        r = fetch_source(self.src(fetch="manual"), extractor=FakeExtractor())
        self.assertIn("unrecoverable", r.detail.lower())

    def test_manual_and_present_is_not_alarming(self):
        s = self.src(fetch="manual")
        s.raw_path.parent.mkdir(parents=True, exist_ok=True)
        s.raw_path.write_text("captured by hand")
        r = fetch_source(s, extractor=FakeExtractor())
        self.assertIn("present", r.detail)
        self.assertNotIn("unrecoverable", r.detail.lower())

    def test_force_does_not_override_manual(self):
        """force is about overwriting, not about pretending a URL works."""
        s = self.src(fetch="manual")
        ex = FakeExtractor()
        r = fetch_source(s, force=True, extractor=ex)
        self.assertEqual(r.status, "manual")
        self.assertEqual(ex.calls, [])


class TestAudit(FetchTestCase):
    def make(self, **extra):
        entry = {"id": "a", "url": "u", "raw_file": "a.html",
                 "processed_file": "a.txt"}
        entry.update(extra)
        return write_manifest(self.root, {"CHORUS": [entry]})

    def test_reports_missing_raw(self):
        a = audit(self.make())
        self.assertEqual(a["total"], 1)
        self.assertEqual(len(a["missing_raw"]), 1)

    def test_reports_raw_present_but_unprocessed(self):
        m = self.make()
        s = load_sources(m)[0]
        s.raw_path.parent.mkdir(parents=True, exist_ok=True)
        s.raw_path.write_text("x")
        a = audit(m)
        self.assertEqual(a["missing_raw"], [])
        self.assertEqual(len(a["missing_processed"]), 1)

    def test_manual_sources_are_surfaced_even_when_present(self):
        m = self.make(fetch="manual")
        s = load_sources(m)[0]
        for p in (s.raw_path, s.processed_path):
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("x")
        a = audit(m)
        self.assertEqual(len(a["manual"]), 1)
        self.assertEqual(a["unrecoverable"], [])
        self.assertEqual(a["present"], 1)

    def test_manual_and_absent_counts_as_unrecoverable(self):
        a = audit(self.make(fetch="manual"))
        self.assertEqual(len(a["unrecoverable"]), 1)


if __name__ == "__main__":
    unittest.main()

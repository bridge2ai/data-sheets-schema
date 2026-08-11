"""Does a record's declared input still hash to what the record consumed? (#452)

The mirror of `d4d download audit-bundles` (#446) one layer up. That command
asks whether a derived bundle still matches what its inputs produce; this asks
whether a *record's* declared input still matches what the record read.

The distinction the whole check rests on: a drifted record is not wrong. It
correctly states the bytes it consumed. What it has lost is the ability to be
re-derived from the path it names, which is a caveat rather than a defect —
hence reported and never fatal, like the unobserved-values counter (#447).
"""

import hashlib
import tempfile
import unittest
from pathlib import Path

import yaml

from data_sheets_schema.runs import (
    BUNDLE_ABSENT,
    BUNDLE_CURRENT,
    BUNDLE_DRIFTED,
    BUNDLE_UNRECORDED,
    bundle_drift,
    bundle_drift_detail,
)


class TestBundleDrift(unittest.TestCase):
    LABEL, METHOD, PROJECT = "2026-08-11_drift_rep1", "claudecode_agent", "VOICE"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.concat = self.root / "data/d4d_concatenated"
        (self.concat / f"{self.METHOD}_core" / self.LABEL).mkdir(parents=True)
        self.bundle = self.root / "bundle.txt"

    def _write(self, *, content=b"the bytes the run consumed", md5=None,
               path=None, omit_hash=False, omit_record=False):
        if content is not None:
            self.bundle.write_bytes(content)
        if omit_record:
            return
        inputs = {"bundle_path": str(path if path is not None else self.bundle)}
        if not omit_hash:
            inputs["bundle_md5"] = md5 or hashlib.md5(content).hexdigest()
        record = (self.concat / f"{self.METHOD}_core" / self.LABEL
                  / f"{self.PROJECT}_provenance.yaml")
        record.write_text(yaml.safe_dump({"inputs": inputs}), encoding="utf-8")

    def _status(self):
        return bundle_drift(self.METHOD, self.LABEL, self.PROJECT, self.concat)

    def test_an_unchanged_bundle_is_current(self):
        self._write()
        status, reason = self._status()
        self.assertEqual(status, BUNDLE_CURRENT)
        self.assertIsNone(reason)

    def test_a_changed_bundle_drifts(self):
        """The case the corpus is in: #421 stripped curator notes from bundles
        55 records already pinned."""
        self._write()
        self.bundle.write_bytes(b"the bytes after a later, correct strip")
        status, reason = self._status()
        self.assertEqual(status, BUNDLE_DRIFTED)
        self.assertIn("now hashes", reason)

    def test_a_single_byte_is_enough(self):
        """Not a heuristic — the record pins an md5, so any edit drifts it."""
        self._write(content=b"aaaa")
        self.bundle.write_bytes(b"aaab")
        self.assertEqual(self._status()[0], BUNDLE_DRIFTED)

    def test_a_missing_bundle_is_absent_not_drifted(self):
        """Distinct because the remedies differ: a drifted path can still be
        read and diffed, a deleted one cannot."""
        self._write()
        self.bundle.unlink()
        status, reason = self._status()
        self.assertEqual(status, BUNDLE_ABSENT)
        self.assertIn("does not exist", reason)

    def test_no_recorded_hash_is_not_a_pass(self):
        """`unrecorded` must never be counted as `current`.

        86 records carry no bundle hash. Folding them into the matching count
        would report the corpus as far healthier than it is — the same error as
        treating an absent cache entry as a hit.
        """
        self._write(omit_hash=True)
        self.assertEqual(self._status()[0], BUNDLE_UNRECORDED)

    def test_a_missing_provenance_record_is_unrecorded(self):
        self._write(omit_record=True)
        self.assertEqual(self._status()[0], BUNDLE_UNRECORDED)

    def test_the_detail_form_returns_the_declared_path(self):
        """So a caller grouping by bundle need not parse the reason string."""
        self._write()
        status, _reason, declared = bundle_drift_detail(
            self.METHOD, self.LABEL, self.PROJECT, self.concat)
        self.assertEqual(status, BUNDLE_CURRENT)
        self.assertEqual(declared, str(self.bundle))

    def test_the_declared_path_survives_a_missing_hash(self):
        """Grouping still works for records that recorded a path but no hash."""
        self._write(omit_hash=True)
        _status, _reason, declared = bundle_drift_detail(
            self.METHOD, self.LABEL, self.PROJECT, self.concat)
        self.assertEqual(declared, str(self.bundle))

    def test_the_record_is_read_not_the_live_config(self):
        """The comparison is against the path the *record* declares.

        A check that resolved the bundle from the current project config would
        report `current` for a record whose declared path had since been
        repointed — the drift it exists to find.
        """
        other = self.root / "somewhere_else.txt"
        other.write_bytes(b"a different bundle entirely")
        self._write(content=b"original", path=other,
                    md5=hashlib.md5(b"original").hexdigest())
        self.assertEqual(self._status()[0], BUNDLE_DRIFTED)


@unittest.skipUnless(Path("data/d4d_concatenated").exists(), "corpus absent")
class TestAgainstTheRealCorpus(unittest.TestCase):
    def test_the_corpus_drift_is_what_the_issue_measured(self):
        """64 drifted / 12 current, the figures #452 was filed on.

        Pinned so the next corpus-wide input change is a visible test failure
        rather than an unreported absorption — which is the whole defect: #421
        and #445 both changed bundles correctly and neither was detected.
        """
        from data_sheets_schema.runs import discover, is_complete

        counts = {BUNDLE_CURRENT: 0, BUNDLE_DRIFTED: 0,
                  BUNDLE_ABSENT: 0, BUNDLE_UNRECORDED: 0}
        for run in discover():
            # The same filter `d4d runs check` applies. `discover` yields the
            # full and _core methods as separate runs over one provenance
            # record, so counting both doubles every figure.
            if run.is_core or run.deterministic:
                continue
            for project in run.projects:
                if not is_complete(run.method, run.label, project):
                    continue
                counts[bundle_drift(run.method, run.label, project)[0]] += 1

        self.assertEqual(counts[BUNDLE_DRIFTED] + counts[BUNDLE_ABSENT], 64)
        self.assertEqual(counts[BUNDLE_CURRENT], 12)

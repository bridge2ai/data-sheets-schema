"""`inputs.bundle_md5` recovered by proof for the records that predate it (#1121).

The 82 records without an md5 carry `inputs.bundle_sha256` of the bytes
they consumed. The md5 is taken from the committed version of the bundle
whose sha256 equals it — never from `repo.commit`, which for these runs
names a tree older than the regenerated bundles they read.
"""

import hashlib
import tempfile
import subprocess
import unittest
from unittest import mock
from pathlib import Path

import yaml

from data_sheets_schema import provenance as pv

SHA = hashlib.sha256(b"the bytes the run read").hexdigest()
MD5 = hashlib.md5(b"the bytes the run read").hexdigest()
HISTORY = [
    {"commit": "b" * 40, "date": "2026-08-10", "sha256": hashlib.sha256(b"later").hexdigest(),
     "md5": hashlib.md5(b"later").hexdigest()},
    {"commit": "a" * 40, "date": "2026-07-28", "sha256": SHA, "md5": MD5},
    {"commit": "9" * 40, "date": "2026-04-24", "sha256": hashlib.sha256(b"older").hexdigest(),
     "md5": hashlib.md5(b"older").hexdigest()},
]


def _record(tmp, inputs):
    p = Path(tmp) / "P_provenance.yaml"
    p.write_text("# Model: x\n# Temperature: not sent\n" + yaml.safe_dump({"run": {"label": "L"}, "inputs": inputs}))
    return p


class Resolve(unittest.TestCase):
    def test_the_blob_whose_sha256_matches_gives_the_md5(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = _record(tmp, {"bundle_path": "data/x.txt", "bundle_sha256": SHA})
            r = pv.resolve_bundle_md5(p, history=lambda bp: HISTORY)
            self.assertEqual((r["status"], r["md5"], r["commit"][:4], r["date"]),
                             (pv.BUNDLE_MD5_RECOVERED, MD5, "aaaa", "2026-07-28"))

    def test_the_oldest_matching_commit_is_named(self):
        """Identical bytes re-committed (merge sides under --full-history)
        must not name an arbitrary later commit (#1129 review)."""
        with tempfile.TemporaryDirectory() as tmp:
            p = _record(tmp, {"bundle_path": "data/x.txt", "bundle_sha256": SHA})
            dup = [{"commit": "c" * 40, "date": "2026-09-01", "sha256": SHA, "md5": MD5}] + HISTORY
            r = pv.resolve_bundle_md5(p, history=lambda bp: dup)
            self.assertEqual((r["commit"][:4], r["matches"]), ("aaaa", 2))
            # oldest by date even if the list is not in git's order; position breaks a tie
            shuffled = [HISTORY[1], dup[0], {"commit": "d" * 40, "date": "2026-07-28", "sha256": SHA, "md5": MD5}]
            self.assertEqual(pv.resolve_bundle_md5(p, history=lambda bp: shuffled)["commit"][:4], "dddd")

    def test_a_tool_failure_is_not_a_finding_about_the_corpus(self):
        """`git log` failing used to read as "the bytes are in no commit"
        (#1129 review, finding 3)."""
        def broken(bp):
            raise pv.GitUnavailable("fatal: not a git repository")
        with tempfile.TemporaryDirectory() as tmp:
            p = _record(tmp, {"bundle_path": "data/x.txt", "bundle_sha256": SHA})
            r = pv.resolve_bundle_md5(p, history=broken)
            self.assertEqual(r["status"], pv.BUNDLE_MD5_GIT_UNAVAILABLE)
            self.assertIsNone(pv.apply_bundle_md5(p, history=broken))
            bad = Path(tmp) / "bad_provenance.yaml"; bad.write_text("inputs: [unclosed")
            self.assertEqual(pv.resolve_bundle_md5(bad)["status"], pv.BUNDLE_MD5_UNREADABLE)

    def test_the_real_history_resolves_from_any_cwd(self):
        import os
        bp = "data/preprocessed/concatenated/CHORUS_preprocessed.txt"
        if not (pv._REPO_ROOT / bp).exists():
            self.skipTest("bundle not in this checkout")
        here = os.getcwd()
        try:
            os.chdir(tempfile.gettempdir())
            pv.bundle_blob_history.cache_clear()
            try:
                versions = pv.bundle_blob_history(bp)
            except pv.GitUnavailable as exc:
                if "shallow" in str(exc):
                    self.skipTest("shallow clone; the real history is not here")   # CI checks out one commit
                raise
        finally:
            os.chdir(here)
        self.assertGreaterEqual(len(versions), 2)

    def test_a_shallow_clone_is_refused_not_searched(self):
        """A one-commit history would report every record whose bytes an
        earlier commit holds as unrecoverable — which is what the CI clone
        did on this branch's first run."""
        calls = []
        real = pv.subprocess.run

        def fake(args, **kw):
            calls.append(args)
            if args[:2] == ["git", "rev-parse"]:
                return subprocess.CompletedProcess(args, 0, stdout="true\n", stderr="")
            return real(args, **kw)
        pv.bundle_blob_history.cache_clear()
        with mock.patch.object(pv.subprocess, "run", fake):
            with self.assertRaises(pv.GitUnavailable) as ctx:
                pv.bundle_blob_history("data/preprocessed/concatenated/CHORUS_preprocessed.txt")
        self.assertIn("shallow", str(ctx.exception))
        self.assertFalse(any(a[:2] == ["git", "log"] for a in calls))   # refused before searching
        pv.bundle_blob_history.cache_clear()

    def test_the_other_outcomes_say_why(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(pv.resolve_bundle_md5(_record(tmp, {"bundle_path": "x", "bundle_sha256": SHA, "bundle_md5": MD5}),
                                                   history=lambda bp: HISTORY)["status"], pv.BUNDLE_MD5_ALREADY)
            self.assertEqual(pv.resolve_bundle_md5(_record(tmp, {"bundle_sha256": SHA}),
                                                   history=lambda bp: HISTORY)["status"], pv.BUNDLE_MD5_NO_PATH)
            self.assertEqual(pv.resolve_bundle_md5(_record(tmp, {"bundle_path": "x"}),
                                                   history=lambda bp: HISTORY)["status"], pv.BUNDLE_MD5_NO_SHA256)
            self.assertEqual(pv.resolve_bundle_md5(_record(tmp, {"bundle_path": "x", "bundle_sha256": "0" * 64}),
                                                   history=lambda bp: HISTORY)["status"], pv.BUNDLE_MD5_NO_BLOB)


class Apply(unittest.TestCase):
    def test_the_write_keeps_the_header_and_names_its_proof(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = _record(tmp, {"bundle_path": "data/x.txt", "bundle_sha256": SHA, "bundle_bytes": 22})
            self.assertIsNotNone(pv.apply_bundle_md5(p, history=lambda bp: HISTORY))
            text = p.read_text()
            self.assertTrue(text.startswith("# Model: x\n# Temperature: not sent\n"))
            d = yaml.safe_load(text)
            self.assertEqual(d["inputs"]["bundle_md5"], MD5)
            self.assertIn("aaaaaaaaaaaa (2026-07-28)", d["inputs"]["bundle_md5_basis"])
            self.assertIn("sha256 equals this record's bundle_sha256", d["inputs"]["bundle_md5_basis"])
            self.assertEqual(d["inputs"]["bundle_bytes"], 22)                        # nothing else touched
            self.assertIsNone(pv.apply_bundle_md5(p, history=lambda bp: HISTORY))     # idempotent: already recorded

    def test_a_record_it_cannot_prove_is_not_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = _record(tmp, {"bundle_path": "data/x.txt", "bundle_sha256": "0" * 64})
            before = p.read_text()
            self.assertIsNone(pv.apply_bundle_md5(p, history=lambda bp: HISTORY))
            self.assertEqual(p.read_text(), before)


class OnTheCorpus(unittest.TestCase):
    def test_every_recovered_md5_on_disk_is_current_or_a_history_before(self):
        """The drift test's rule (#910): a drifted record must pin a hash some
        history event names as its `before`. Asserted on the md5 as WRITTEN
        to every record whose `bundle_md5_basis` says it was recovered —
        not on a re-resolution, which after the backfill returns
        `already_recorded` for all of them and made the first version of
        this test a permanent skip (#1129 review, must-fix 1). Read-only."""
        import glob
        from tests.test_cli.test_bundle_drift import _history_befores
        befores = _history_befores()
        recovered, bad = 0, []
        for path in sorted(glob.glob(str(pv._REPO_ROOT / pv.CONCAT_DIR / "*_core" / "*" / "*_provenance.yaml"))):
            d = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
            inp = d.get("inputs") or {}
            if not str(inp.get("bundle_md5_basis") or "").startswith("recovered (#1121)"):
                continue
            recovered += 1
            md5 = inp.get("bundle_md5")
            bundle = pv._REPO_ROOT / inp["bundle_path"]
            current = hashlib.md5(bundle.read_bytes()).hexdigest() if bundle.exists() else None
            if not (md5 == current or md5 in befores):
                bad.append((path, md5))
        if not list((pv._REPO_ROOT / pv.CONCAT_DIR).glob("*_core/*/*_provenance.yaml")):
            self.skipTest("no provenance records in this checkout")
        self.assertGreater(recovered, 0, "the recovered records are gone, or their basis field was dropped")
        self.assertEqual(bad, [])


if __name__ == "__main__":
    unittest.main()

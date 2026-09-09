"""`inputs.bundle_md5` recovered by proof for the records that predate it (#1121).

The 82 records without an md5 carry `inputs.bundle_sha256` of the bytes
they consumed. The md5 is taken from the committed version of the bundle
whose sha256 equals it — never from `repo.commit`, which for these runs
names a tree older than the regenerated bundles they read.
"""

import hashlib
import tempfile
import unittest
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
    def test_every_recovered_md5_is_current_or_a_history_before(self):
        """The drift test's rule (#910): a drifted record must pin a hash some
        history event names as its `before`. Every md5 this recovers is
        either the bundle as it is or such a before — so the backfill adds
        no hash the history cannot explain. Read-only."""
        from data_sheets_schema.runs import discover
        from tests.test_cli.test_bundle_drift import _history_befores
        befores = _history_befores()
        checked = 0
        for run in discover():
            if run.is_core or run.deterministic:
                continue
            for proj in run.projects:
                path = pv.record_path_for(proj, run.method, run.label)
                if not path.exists():
                    continue
                r = pv.resolve_bundle_md5(path)
                if r["status"] != pv.BUNDLE_MD5_RECOVERED:
                    continue
                checked += 1
                current = hashlib.md5(Path(r["path"]).read_bytes()).hexdigest() if Path(r["path"]).exists() else None
                self.assertTrue(r["md5"] == current or r["md5"] in befores, (path, r["md5"]))
        if checked == 0:
            self.skipTest("no record left to recover in this checkout")


if __name__ == "__main__":
    unittest.main()

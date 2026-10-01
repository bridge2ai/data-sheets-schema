"""Bytes a run recorded that only a squash-merged branch held, rebuilt from a
reachable blob by a recorded edit (#3788)."""
import hashlib
import subprocess
import unittest
from unittest import mock

from data_sheets_schema import reconstructed_bytes as rb
from data_sheets_schema.provenance import _REPO_ROOT, GitUnavailable

VOICE_V4_REP1 = "data/d4d_concatenated/claudecode_agent_core/2026-08-13_claude-opus-5-api-generic-v4_rep1/VOICE_provenance.yaml"


def _entry(base: bytes, edits, **over):
    data = rb.apply_edits(base, edits)
    return {"path": "x.yaml", "sha256": hashlib.sha256(data).hexdigest(), "md5": hashlib.md5(data).hexdigest(),
            "base_commit": "c" * 40, "edits": edits, "observed_at": "a branch commit", "issue": 1, **over}


class ApplyEdits(unittest.TestCase):
    def test_inserts_deletes_and_replaces_by_base_line(self):
        base = b"a\nb\nc\n"
        self.assertEqual(rb.apply_edits(base, [{"at": 1, "delete": 0, "insert": "x\n"}]), b"a\nx\nb\nc\n")
        self.assertEqual(rb.apply_edits(base, [{"at": 1, "delete": 1, "insert": ""}]), b"a\nc\n")
        self.assertEqual(rb.apply_edits(base, [{"at": 2, "delete": 1, "insert": "z\n"},
                                               {"at": 0, "delete": 1, "insert": "y\n"}]), b"y\nb\nz\n")
        self.assertEqual(rb.apply_edits(base, [{"at": 3, "delete": 0, "insert": "d\n"}]), b"a\nb\nc\nd\n")

    def test_an_edit_that_does_not_fit_the_base_is_refused(self):
        with self.assertRaises(ValueError):
            rb.apply_edits(b"a\n", [{"at": 1, "delete": 1, "insert": ""}])
        with self.assertRaises(ValueError):
            rb.apply_edits(b"a\nb\n", [{"at": 0, "delete": 2, "insert": ""}, {"at": 1, "delete": 0, "insert": ""}])


class ReconstructedBytesFor(unittest.TestCase):
    BASE = b"prefixes:\n  a: 1\nclasses: {}\n"
    EDITS = ({"at": 2, "delete": 0, "insert": "  b: 2\n"},)

    def test_a_recorded_rebuild_is_returned_by_either_hash_and_says_so(self):
        entry = _entry(self.BASE, self.EDITS)
        with mock.patch.object(rb, "RECONSTRUCTIONS", (entry,)), \
                mock.patch.object(rb, "_base_blob", return_value=self.BASE) as base:
            for kw, on in (({"sha256": entry["sha256"]}, ["sha256"]), ({"md5": entry["md5"]}, ["md5"]),
                           ({"md5": entry["md5"], "sha256": entry["sha256"]}, ["md5", "sha256"])):
                data, got = rb.reconstructed_bytes_for("x.yaml", **kw)
                self.assertEqual(data, b"prefixes:\n  a: 1\n  b: 2\nclasses: {}\n")
                self.assertEqual((got["matched_on"], got["base_commit"]), (on, "c" * 40))
            base.assert_called_with("c" * 40, "x.yaml")

    def test_no_entry_a_mismatched_hash_another_path_or_a_missing_base_is_none(self):
        entry = _entry(self.BASE, self.EDITS)
        with mock.patch.object(rb, "RECONSTRUCTIONS", (entry,)), \
                mock.patch.object(rb, "_base_blob", return_value=self.BASE):
            self.assertIsNone(rb.reconstructed_bytes_for("x.yaml"))
            self.assertIsNone(rb.reconstructed_bytes_for("x.yaml", sha256="0" * 64))
            # Every hash given must match, not one of them.
            self.assertIsNone(rb.reconstructed_bytes_for("x.yaml", sha256=entry["sha256"], md5="0" * 32))
            self.assertIsNone(rb.reconstructed_bytes_for("y.yaml", sha256=entry["sha256"]))
        with mock.patch.object(rb, "RECONSTRUCTIONS", (entry,)), mock.patch.object(rb, "_base_blob", return_value=None):
            self.assertIsNone(rb.reconstructed_bytes_for("x.yaml", sha256=entry["sha256"]))

    def test_a_wrong_entry_is_refused_by_its_hash_not_trusted(self):
        entry = {**_entry(self.BASE, self.EDITS), "edits": ({"at": 2, "delete": 0, "insert": "  c: 3\n"},)}
        with mock.patch.object(rb, "RECONSTRUCTIONS", (entry,)), \
                mock.patch.object(rb, "_base_blob", return_value=self.BASE):
            self.assertIsNone(rb.reconstructed_bytes_for("x.yaml", sha256=entry["sha256"]))

    def test_git_failing_other_than_by_lacking_the_base_raises(self):
        failed = subprocess.CompletedProcess([], 128, b"", b"fatal: unable to read tree (corrupt)")
        with mock.patch("subprocess.run", return_value=failed):
            with self.assertRaises(GitUnavailable):
                rb._base_blob("c" * 40, "x.yaml")
        missing = subprocess.CompletedProcess([], 128, b"", b"fatal: invalid object name 'cccc'.")
        with mock.patch("subprocess.run", return_value=missing):
            self.assertIsNone(rb._base_blob("c" * 40, "x.yaml"))


def _have(commit: str) -> bool:
    try:
        return subprocess.run(["git", "cat-file", "-e", f"{commit}^{{commit}}"], cwd=_REPO_ROOT,
                              capture_output=True, check=False).returncode == 0
    except OSError:
        return False


class TheRecordedEntry(unittest.TestCase):
    """The one entry (#3788) rebuilds the bytes the 2026-08-13 generic-v4
    rep1 VOICE record hashed, from the blob at its own repo commit."""

    def test_the_voice_v4_rep1_merged_schema_is_rebuilt_from_its_run_commit(self):
        (entry,) = rb.RECONSTRUCTIONS
        if not _have(entry["base_commit"]):
            self.skipTest("the base commit is not in this clone (a shallow checkout)")
        data, got = rb.reconstructed_bytes_for(entry["path"], sha256=entry["sha256"])
        self.assertEqual(hashlib.sha256(data).hexdigest(),
                         "fc3ca87375af6954cc47c27910574d1b67f5a2391697bf45be8097326a9e4015")
        self.assertEqual(hashlib.md5(data).hexdigest(), entry["md5"])
        # The only difference from the reachable blob is the three prefixes.
        base = rb._base_blob(entry["base_commit"], entry["path"])
        import difflib
        a, b = base.decode().splitlines(), data.decode().splitlines()
        ops = [op for op in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes() if op[0] != "equal"]
        self.assertEqual([op[0] for op in ops], ["insert"])
        added = b[ops[0][3]:ops[0][4]]
        self.assertEqual([line.split(": ")[1] for line in added if "prefix_reference" in line],
                         ["https://ror.org/", "https://orcid.org/", "https://doi.org/"])
        self.assertEqual(len(added), 9)

    def test_the_record_names_this_path_hash_and_commit(self):
        import yaml
        path = _REPO_ROOT / VOICE_V4_REP1
        if not path.exists():
            self.skipTest("the corpus record is not in this tree")
        record = yaml.safe_load(path.read_text(encoding="utf-8"))
        (entry,) = rb.RECONSTRUCTIONS
        self.assertEqual((record["schema"]["full_path"], record["schema"]["full_sha256"], record["repo"]["commit"]),
                         (entry["path"], entry["sha256"], entry["base_commit"]))


if __name__ == "__main__":
    unittest.main()

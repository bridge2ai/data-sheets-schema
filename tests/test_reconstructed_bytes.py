"""Bytes a run recorded that only a squash-merged branch held, read from a
committed, hash-checked artefact (#3788, #3953)."""
import gzip
import hashlib
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

from data_sheets_schema import reconstructed_bytes as rb
from data_sheets_schema.provenance import _REPO_ROOT, GitUnavailable

VOICE_V4_REP1 = "data/d4d_concatenated/claudecode_agent_core/2026-08-13_claude-opus-5-api-generic-v4_rep1/VOICE_provenance.yaml"


def _entry(base: bytes, edits, **over):
    data = rb.apply_edits(base, edits)
    return {"path": "x.yaml", "sha256": hashlib.sha256(data).hexdigest(), "md5": hashlib.md5(data).hexdigest(),
            "artefact": "notes/x.yaml.gz", "artefact_sha256": "0" * 64, "base_commit": "c" * 40,
            "edits": edits, "observed_at": "a branch commit", "issue": 1, **over}


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

    def test_a_recorded_version_is_returned_by_either_hash_and_says_so(self):
        entry = _entry(self.BASE, self.EDITS)
        data = rb.apply_edits(self.BASE, self.EDITS)
        with mock.patch.object(rb, "RECONSTRUCTIONS", (entry,)), \
                mock.patch.object(rb, "_artefact_bytes", return_value=data) as read:
            for kw, on in (({"sha256": entry["sha256"]}, ["sha256"]), ({"md5": entry["md5"]}, ["md5"]),
                           ({"md5": entry["md5"], "sha256": entry["sha256"]}, ["md5", "sha256"])):
                got_data, got = rb.reconstructed_bytes_for("x.yaml", **kw)
                self.assertEqual(got_data, b"prefixes:\n  a: 1\n  b: 2\nclasses: {}\n")
                self.assertEqual((got["matched_on"], got["artefact"]), (on, "notes/x.yaml.gz"))
            read.assert_called_with(entry)

    def test_no_entry_a_mismatched_hash_another_path_or_a_missing_artefact_is_none(self):
        entry = _entry(self.BASE, self.EDITS)
        data = rb.apply_edits(self.BASE, self.EDITS)
        with mock.patch.object(rb, "RECONSTRUCTIONS", (entry,)), \
                mock.patch.object(rb, "_artefact_bytes", return_value=data):
            self.assertIsNone(rb.reconstructed_bytes_for("x.yaml"))
            self.assertIsNone(rb.reconstructed_bytes_for("x.yaml", sha256="0" * 64))
            # Every hash given must match, not one of them.
            self.assertIsNone(rb.reconstructed_bytes_for("x.yaml", sha256=entry["sha256"], md5="0" * 32))
            self.assertIsNone(rb.reconstructed_bytes_for("y.yaml", sha256=entry["sha256"]))
        with mock.patch.object(rb, "RECONSTRUCTIONS", (entry,)), \
                mock.patch.object(rb, "_artefact_bytes", return_value=None):
            self.assertIsNone(rb.reconstructed_bytes_for("x.yaml", sha256=entry["sha256"]))

    def test_an_artefact_whose_bytes_are_not_the_entrys_is_refused_not_trusted(self):
        entry = _entry(self.BASE, self.EDITS)
        with mock.patch.object(rb, "RECONSTRUCTIONS", (entry,)), \
                mock.patch.object(rb, "_artefact_bytes", return_value=self.BASE + b"  c: 3\n"):
            self.assertIsNone(rb.reconstructed_bytes_for("x.yaml", sha256=entry["sha256"]))

    def test_the_artefact_is_read_only_where_its_own_sha256_and_gzip_hold(self):
        data = rb.apply_edits(self.BASE, self.EDITS)
        packed = gzip.compress(data, mtime=0)
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch("data_sheets_schema.provenance._REPO_ROOT", Path(tmp)):
            entry = _entry(self.BASE, self.EDITS, artefact_sha256=hashlib.sha256(packed).hexdigest())
            self.assertIsNone(rb._artefact_bytes(entry))            # not in this tree
            (Path(tmp) / "notes").mkdir()
            (Path(tmp) / "notes/x.yaml.gz").write_bytes(packed)
            self.assertEqual(rb._artefact_bytes(entry), data)
            self.assertIsNone(rb._artefact_bytes({**entry, "artefact_sha256": "0" * 64}))
            (Path(tmp) / "notes/x.yaml.gz").write_bytes(data)       # not gzip, sha256 named
            self.assertIsNone(rb._artefact_bytes({**entry, "artefact_sha256": hashlib.sha256(data).hexdigest()}))

    def test_git_failing_other_than_by_lacking_the_base_raises(self):
        failed = subprocess.CompletedProcess([], 128, b"", b"fatal: unable to read tree (corrupt)")
        with mock.patch("subprocess.run", return_value=failed):
            with self.assertRaises(GitUnavailable):
                rb._base_blob("c" * 40, "x.yaml")
        missing = subprocess.CompletedProcess([], 128, b"", b"fatal: invalid object name 'cccc'.")
        with mock.patch("subprocess.run", return_value=missing):
            self.assertIsNone(rb._base_blob("c" * 40, "x.yaml"))
            self.assertIsNone(rb.rebuild(_entry(self.BASE, self.EDITS)))


def _git(*args: str) -> subprocess.CompletedProcess | None:
    try:
        return subprocess.run(["git", *args], cwd=_REPO_ROOT, capture_output=True, text=True, check=False)
    except OSError:
        return None


def _full_clone() -> bool:
    got = _git("rev-parse", "--is-shallow-repository")
    return got is not None and got.returncode == 0 and got.stdout.strip() == "false"


class TheRecordedEntry(unittest.TestCase):
    """The one entry (#3788): the bytes the 2026-08-13 generic-v4 rep1 VOICE
    record hashed, committed as an artefact that every clone reads (#3953)."""

    def test_the_artefact_is_read_with_no_git_and_hashes_to_the_record(self):
        (entry,) = rb.RECONSTRUCTIONS
        with mock.patch("subprocess.run", side_effect=AssertionError("git must not be needed")):
            data, got = rb.reconstructed_bytes_for(entry["path"], sha256=entry["sha256"])
        self.assertEqual(hashlib.sha256(data).hexdigest(),
                         "fc3ca87375af6954cc47c27910574d1b67f5a2391697bf45be8097326a9e4015")
        self.assertEqual(hashlib.md5(data).hexdigest(), entry["md5"])
        self.assertEqual(got["matched_on"], ["sha256"])

    def test_the_artefact_is_tracked_so_a_fresh_clone_has_it(self):
        if not (_REPO_ROOT / ".git").exists():
            self.skipTest("not a git checkout")
        (entry,) = rb.RECONSTRUCTIONS
        for path in (entry["artefact"], entry["provenance"]):
            got = _git("ls-files", "--error-unmatch", path)
            if got is None:
                self.skipTest("git cannot be run")
            self.assertEqual(got.returncode, 0, f"{path} is not tracked")

    def test_the_provenance_sidecar_states_the_entry(self):
        (entry,) = rb.RECONSTRUCTIONS
        side = yaml.safe_load((_REPO_ROOT / entry["provenance"]).read_text(encoding="utf-8"))
        self.assertEqual({k: side[k] for k in ("path", "sha256", "md5", "artefact", "artefact_sha256", "issue")},
                         {k: entry[k] for k in ("path", "sha256", "md5", "artefact", "artefact_sha256", "issue")})
        self.assertEqual(side["base"]["commit"], entry["base_commit"])
        self.assertEqual(tuple(side["edits"]), entry["edits"])
        self.assertEqual(side["bytes"], len(rb.reconstructed_bytes_for(entry["path"], sha256=entry["sha256"])[0]))

    def test_the_artefact_is_the_recorded_edit_of_a_commit_on_main(self):
        """The base commit is an ancestor of HEAD (main's history, not a
        local branch), its blob is the one the sidecar names, and the
        recorded edit of it is the artefact byte for byte: three prefixes
        inserted, nothing else."""
        if not _full_clone():
            self.skipTest("needs a clone with history")
        (entry,) = rb.RECONSTRUCTIONS
        self.assertEqual(_git("merge-base", "--is-ancestor", entry["base_commit"], "HEAD").returncode, 0,
                         "the base commit is not reachable from HEAD")
        side = yaml.safe_load((_REPO_ROOT / entry["provenance"]).read_text(encoding="utf-8"))
        self.assertEqual(_git("rev-parse", f"{entry['base_commit']}:{entry['path']}").stdout.strip(),
                         side["base"]["blob"])
        base = rb._base_blob(entry["base_commit"], entry["path"])
        self.assertEqual(hashlib.sha256(base).hexdigest(), side["base"]["sha256"])
        data, _ = rb.reconstructed_bytes_for(entry["path"], sha256=entry["sha256"])
        self.assertEqual(rb.rebuild(entry), data)
        import difflib
        a, b = base.decode().splitlines(), data.decode().splitlines()
        ops = [op for op in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes() if op[0] != "equal"]
        self.assertEqual([op[0] for op in ops], ["insert"])
        added = b[ops[0][3]:ops[0][4]]
        self.assertEqual([line.split(": ")[1] for line in added if "prefix_reference" in line],
                         ["https://ror.org/", "https://orcid.org/", "https://doi.org/"])
        self.assertEqual(len(added), 9)

    def test_the_record_names_this_path_and_hash(self):
        path = _REPO_ROOT / VOICE_V4_REP1
        if not path.exists():
            self.skipTest("the corpus record is not in this tree")
        record = yaml.safe_load(path.read_text(encoding="utf-8"))
        (entry,) = rb.RECONSTRUCTIONS
        self.assertEqual((record["schema"]["full_path"], record["schema"]["full_sha256"]),
                         (entry["path"], entry["sha256"]))
        # The run's own commit, on the #543 branch, held the base blob; the
        # entry names main's commit with that blob instead (#3953).
        self.assertEqual(record["repo"]["commit"], "4892fcd3a5e7d805653bf6426c0ac8b8ad173822")


if __name__ == "__main__":
    unittest.main()

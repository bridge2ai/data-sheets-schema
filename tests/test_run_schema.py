"""A schema-dependent recompute reads the merged schema the run recorded (#3931).

`removals.run_enum_aliases` was the one recompute that read the schema a run
recorded (#3702). The form block's undeclared-prefix count and the grounding
block's identifier walk and resolver-URL findings read today's schema and
said nothing about it. #3788 is the case that matters: the 2026-08-13 v4 rep1
VOICE run read a schema declaring `ROR`, `ORCID` and `doi`, and its commit's
blob declares none of the three. These pin the one resolution
(`run_schema.run_schema_bytes`) that removals now reads through.
"""
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

from data_sheets_schema import run_schema as rs
from data_sheets_schema.provenance import GitUnavailable

#: A small merged schema: it declares `foo` and no `doi`, ranges `id` and
#: `publisher` on `uriorcurie` (today's schema does too) and `lead` on Person.
RUN_SCHEMA = {
    "id": "https://example.org/run-schema", "name": "run-schema", "default_range": "string",
    "prefixes": {"foo": {"prefix_prefix": "foo", "prefix_reference": "https://foo.example.org/"},
                 "linkml": {"prefix_prefix": "linkml", "prefix_reference": "https://w3id.org/linkml/"}},
    "types": {"string": {"uri": "xsd:string", "base": "str"},
              "uriorcurie": {"uri": "xsd:anyURI", "base": "URIorCURIE"}},
    "classes": {
        "Dataset": {"attributes": {"id": {"range": "uriorcurie", "identifier": True},
                                   "publisher": {"range": "uriorcurie"},
                                   "lead": {"range": "Person"}}},
        "Person": {"attributes": {"id": {"range": "uriorcurie", "identifier": True}, "name": {}}},
    },
}

GIT = "data_sheets_schema.provenance.committed_bytes_for"
REBUILT = "data_sheets_schema.reconstructed_bytes.reconstructed_bytes_for"


def _schema_file(tmp: str, schema: dict = RUN_SCHEMA) -> tuple[Path, str, str]:
    path = Path(tmp) / "schema_all.yaml"
    path.write_text(yaml.safe_dump(schema), encoding="utf-8")
    data = path.read_bytes()
    return path, hashlib.sha256(data).hexdigest(), hashlib.md5(data).hexdigest()


class Resolution(unittest.TestCase):
    """`run_schema_bytes`: disk, reconstruction, git, else a stated fallback."""

    def test_a_record_naming_no_schema_by_path_and_hash_reads_today(self):
        for record in (None, {}, {"schema": "x"}, {"schema": {"full_path": "x.yaml"}},
                       {"schema": {"full_sha256": "a" * 64}}, {"schema": {"full_path": "", "full_md5": "m"}}):
            self.assertEqual(rs.run_schema_bytes(record),
                             (None, {"source": rs.TODAY,
                                     "reason": "the record names no merged schema by path and hash"}))

    def test_the_file_on_disk_is_read_where_every_recorded_hash_matches(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, sha, md5 = _schema_file(tmp)
            for given in ({"full_sha256": sha}, {"full_md5": md5}, {"full_sha256": sha, "full_md5": md5}):
                data, basis = rs.run_schema_bytes({"schema": {"full_path": str(path), **given}})
                self.assertEqual(data, path.read_bytes())
                self.assertEqual(basis["source"], "the run's schema, on disk")
            # One recorded hash that does not match is not the run's file: git is asked.
            with mock.patch(REBUILT, return_value=None), mock.patch(GIT, return_value=None) as git:
                data, basis = rs.run_schema_bytes({"schema": {"full_path": str(path), "full_sha256": sha,
                                                              "full_md5": "0" * 32}})
            git.assert_called_once_with(str(path), md5="0" * 32, sha256=sha)
            self.assertIsNone(data)
            self.assertIn("no committed version", basis["reason"])

    def test_a_reconstruction_is_read_before_git_is_asked(self):
        """#3953: a shallow clone cannot answer git, so the committed artefact comes first."""
        record = {"schema": {"full_path": "src/x_all.yaml", "full_sha256": "a" * 64}}
        entry = {"artefact": "notes/x.yaml.gz", "base_commit": "b" * 40, "matched_on": ["sha256"],
                 "observed_at": "a branch commit", "issue": 3788}
        with mock.patch(REBUILT, return_value=(b"bytes", entry)) as rebuilt, \
                mock.patch(GIT, side_effect=AssertionError("git must not be asked")):
            data, basis = rs.run_schema_bytes(record)
        rebuilt.assert_called_once_with("src/x_all.yaml", md5=None, sha256="a" * 64)
        self.assertEqual(data, b"bytes")
        self.assertEqual(basis, {"source": "the run's schema, reconstructed", "path": "src/x_all.yaml",
                                 "sha256": "a" * 64, "artefact": "notes/x.yaml.gz", "base_commit": "b" * 40,
                                 "matched_on": ["sha256"], "observed_at": "a branch commit",
                                 "reconstruction": "reconstructed_bytes.RECONSTRUCTIONS (#3788)"})

    def test_a_committed_version_is_read_with_its_commit(self):
        record = {"schema": {"full_path": "src/x_all.yaml", "full_md5": "m" * 32}}
        with mock.patch(REBUILT, return_value=None), \
                mock.patch(GIT, return_value=(b"bytes", {"commit": "c" * 40, "matched_on": ["md5"]})) as git:
            data, basis = rs.run_schema_bytes(record)
        git.assert_called_once_with("src/x_all.yaml", md5="m" * 32, sha256=None)
        self.assertEqual(data, b"bytes")
        self.assertEqual(basis, {"source": "the run's schema, a git blob", "path": "src/x_all.yaml",
                                 "md5": "m" * 32, "commit": "c" * 40, "matched_on": ["md5"]})

    def test_every_failure_is_the_stated_fallback_never_a_traceback(self):
        """A shallow clone, git that cannot be started (#3851), git refusing
        to run, no matching version, an unreadable reconstruction: each is
        today's schema with its reason, the recorded hash kept."""
        record = {"schema": {"full_path": "src/x_all.yaml", "full_sha256": "a" * 64}}
        cases = (
            (None, GitUnavailable("shallow clone"), "git cannot answer (shallow clone)"),
            (None, FileNotFoundError(2, "No such file or directory", "git"),
             "git could not be run (FileNotFoundError"),
            (None, PermissionError(13, "Permission denied", "git"), "git could not be run (PermissionError"),
            (None, None, "no committed version of the path hashes to what the record recorded"),
            (PermissionError(13, "Permission denied", "x.yaml.gz"), AssertionError("not reached"),
             "its recorded reconstruction could not be read (PermissionError"),
        )
        for rebuilt, git, reason in cases:
            with self.subTest(reason=reason), \
                    mock.patch(REBUILT, **({"side_effect": rebuilt} if isinstance(rebuilt, Exception)
                                          else {"return_value": rebuilt})), \
                    mock.patch(GIT, **({"side_effect": git} if isinstance(git, Exception)
                                      else {"return_value": git})):
                data, basis = rs.run_schema_bytes(record)
            self.assertIsNone(data)
            self.assertEqual((basis["source"], basis["path"], basis["sha256"]),
                             (rs.TODAY, "src/x_all.yaml", "a" * 64))
            self.assertIn(reason, basis["reason"])

    def test_removals_reads_its_enum_tables_through_the_helper(self):
        """The extraction: `run_enum_aliases` is the helper's bytes and basis,
        tabled, or None with the helper's fallback basis."""
        from data_sheets_schema import removals as rm
        data = yaml.safe_dump({"enums": {"E": {"permissible_values": {"bar": {"aliases": ["Foo"]}}}},
                               "classes": {"C": {"attributes": {"kind": {"range": "E"}}}}}).encode()
        basis = {"source": "the run's schema, a git blob", "path": "p", "sha256": "s"}
        with mock.patch("data_sheets_schema.run_schema.run_schema_bytes", return_value=(data, basis)) as got:
            tables, said = rm.run_enum_aliases({"schema": {}})
        got.assert_called_once_with({"schema": {}})
        self.assertEqual((tables, said), ({"kind": {"Foo": "bar", "foo": "bar", "bar": "bar"}}, basis))
        fallback = {"source": rs.TODAY, "reason": "why"}
        with mock.patch("data_sheets_schema.run_schema.run_schema_bytes", return_value=(None, fallback)):
            self.assertEqual(rm.run_enum_aliases(None), (None, fallback))


if __name__ == "__main__":
    unittest.main()

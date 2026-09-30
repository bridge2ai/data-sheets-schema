"""Deterministic-arm records are judged against today's schema (#2970).

`rocrate_mapped` and `rocrate_static_map` write no `<method>_core`
provenance record, so `validation_status` calls them UNVERIFIED and `d4d runs
check` skipped them outright: #2916 found committed records the schema
rejected with nothing reporting it. `runs.deterministic_validity` judges each
one against the merged schema on disk, and `runs check` reports the answer —
never fatally, and never by rewriting a record, because the published labels
are kept as published (#426/#520).
"""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pytest
import yaml
from click.testing import CliRunner

from data_sheets_schema.cli import cli
from data_sheets_schema.runs import (CONCAT_DIR, INVALID, UNVERIFIED, VALID,
                                     _validate_deterministic, deterministic_validity)

ROOT = Path(__file__).resolve().parents[1]

VALID_RECORD = "id: https://example.org/ds\ntitle: A dataset\ndoi: 10.1234/abc\n"
#: The committed arms' defect: the crate's resolver URL in `doi` (#646, #2916).
RESOLVER_DOI = "id: https://example.org/ds\ntitle: A dataset\ndoi: https://doi.org/10.1234/abc\n"


def _tree(root: Path, records: dict[str, str]) -> Path:
    """`records` maps ``method/label/PROJECT_d4d.yaml`` to its text."""
    concat = root / "data" / "d4d_concatenated"
    for rel, text in records.items():
        path = concat / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return concat


class TestSelection(unittest.TestCase):
    """Which records are judged, and how a verdict becomes a status — with the
    validator replaced, so these run in milliseconds."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.concat = _tree(Path(self.tmp.name), {
            "rocrate_static_map/v1/A_d4d.yaml": "a",
            "rocrate_static_map/v1/B_d4d.yaml": "b",
            "rocrate_mapped/det-v1/A_d4d.yaml": "c",
            # A generated arm: `runs check`'s own loop covers it; this does not.
            "claudecode_agent/x_rep1/A_d4d.yaml": "d",
        })
        self.seen: list[str] = []

    def _fake(self, verdicts):
        def validate(path):
            self.seen.append(str(Path(path).relative_to(self.concat)))
            return verdicts[Path(path).read_text(encoding="utf-8")]
        return validate

    def test_only_deterministic_arms_are_judged_and_each_verdict_is_kept(self):
        rows = deterministic_validity(self.concat, validate=self._fake({
            "a": ([], None), "b": (["[ERROR] [x/0] bad in /doi"], None),
            "c": (None, "linkml-validate did not run: boom")}))
        self.assertNotIn("claudecode_agent/x_rep1/A_d4d.yaml", self.seen)
        got = {(r["method"], r["label"], r["project"]): r for r in rows}
        self.assertEqual(set(got), {("rocrate_static_map", "v1", "A"),
                                    ("rocrate_static_map", "v1", "B"),
                                    ("rocrate_mapped", "det-v1", "A")})
        self.assertEqual(got["rocrate_static_map", "v1", "A"]["status"], VALID)
        self.assertEqual(got["rocrate_static_map", "v1", "B"]["status"], INVALID)
        self.assertEqual(got["rocrate_static_map", "v1", "B"]["findings"],
                         ["[ERROR] [x/0] bad in /doi"])

    def test_a_validator_that_did_not_run_is_never_read_as_valid(self):
        """#613: "found nothing because nothing ran" is not a conforming record."""
        rows = deterministic_validity(self.concat, method="rocrate_mapped",
                                      validate=self._fake({"c": (None, "did not run")}))
        self.assertEqual([r["status"] for r in rows], [UNVERIFIED])
        self.assertEqual(rows[0]["failure"], "did not run")

    def test_the_filters_narrow_what_is_judged(self):
        ok = self._fake({"a": ([], None), "b": ([], None), "c": ([], None)})
        rows = deterministic_validity(self.concat, method="rocrate_static_map",
                                      project="B", validate=ok)
        self.assertEqual([(r["label"], r["project"]) for r in rows], [("v1", "B")])
        self.assertEqual(deterministic_validity(self.concat, label="nope", validate=ok), [])

    def test_nothing_is_written(self):
        before = {p: p.read_bytes() for p in self.concat.rglob("*") if p.is_file()}
        deterministic_validity(self.concat, validate=self._fake({
            "a": (["x"], None), "b": ([], None), "c": ([], None)}))
        after = {p: p.read_bytes() for p in self.concat.rglob("*") if p.is_file()}
        self.assertEqual(before, after)


class TestTheInstrument(unittest.TestCase):
    """The real validator, on a record built here. The CLI test below runs it
    on a resolver-URL `doi` and on a valid record."""

    def test_a_duplicate_key_is_a_finding_the_loader_cannot_see(self):
        """#1029: `safe_load` keeps the last `title`, and validates that."""
        with tempfile.TemporaryDirectory() as tmp:
            dup = Path(tmp) / "dup.yaml"
            dup.write_text(VALID_RECORD + "title: Another\n", encoding="utf-8")
            findings, failure = _validate_deterministic(dup)
            self.assertIsNone(failure)
            self.assertEqual(len(findings), 1)
            self.assertIn("duplicate mapping key", findings[0])


class TestRunsCheckReportsIt(unittest.TestCase):
    """`d4d runs check` on a caller's own tree (outside the checkout, no
    manifest selected, so the corpus root is the working directory)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        _tree(self.root, {
            "rocrate_static_map/ourmap-v1/CHORUS_d4d.yaml": RESOLVER_DOI,
            "rocrate_static_map/ourmap-v1/VOICE_d4d.yaml": VALID_RECORD,
        })
        cwd = Path.cwd()
        import os
        os.chdir(self.root)
        self.addCleanup(os.chdir, cwd)

    def test_an_invalid_record_is_named_and_strict_still_exits_zero(self):
        result = CliRunner().invoke(cli, ["runs", "check", "--strict"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("2 deterministic-arm record(s) judged against the current schema", result.output)
        self.assertIn("1 valid, 1 invalid, 0 could not be checked", result.output)
        line = [l for l in result.output.splitlines() if "ourmap-v1" in l]
        self.assertEqual(len(line), 1, result.output)
        self.assertIn("CHORUS", line[0])
        self.assertIn("in /doi", line[0])
        self.assertIn("Reported, never fatal", result.output)
        # and the record is as it was
        self.assertEqual((self.root / "data/d4d_concatenated/rocrate_static_map/ourmap-v1/"
                          "CHORUS_d4d.yaml").read_text(encoding="utf-8"), RESOLVER_DOI)

    def test_the_filters_given_are_the_filters_used(self):
        """`check` rebinds `project` and `label` in its report loops; the
        section must see the options as given, not a loop's last value."""
        with mock.patch("data_sheets_schema.runs.deterministic_validity",
                        return_value=[]) as dv:
            result = CliRunner().invoke(cli, ["runs", "check", "--project", "VOICE",
                                              "--label", "ourmap-v1"])
        self.assertEqual(result.exit_code, 0, result.output)
        dv.assert_called_once_with(method=None, label="ourmap-v1", project="VOICE")


@pytest.mark.corpus   # walks the committed deterministic arms (#1203)
class TestTheCommittedArms(unittest.TestCase):
    def test_every_committed_record_gets_a_verdict_the_record_explains(self):
        """Each committed deterministic-arm record is judged (none left
        unchecked), and a record is invalid exactly where its `doi` still
        carries the resolver URL #646 made invalid — the verdict follows the
        bytes, not a count pinned here."""
        concat = ROOT / CONCAT_DIR
        rows = deterministic_validity(concat)
        self.assertTrue(rows)
        self.assertEqual([], [r for r in rows if r["status"] == UNVERIFIED])
        for r in rows:
            with self.subTest(record=r["path"]):
                doi = (yaml.safe_load(Path(r["path"]).read_text(encoding="utf-8")) or {}).get("doi")
                resolver = isinstance(doi, str) and doi.startswith("https://doi.org/")
                if resolver:
                    self.assertEqual(r["status"], INVALID)
                    self.assertTrue(any("in /doi" in f for f in r["findings"]), r["findings"])
                else:
                    self.assertFalse(any("in /doi" in f for f in r["findings"]), r["findings"])


if __name__ == "__main__":
    unittest.main()

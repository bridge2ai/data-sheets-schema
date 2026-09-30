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


def _assert_verdict_explained(case: unittest.TestCase, row: dict) -> None:
    """A record is INVALID, with a finding at `/doi`, if its `doi` carries the
    resolver URL #646 made invalid, and VALID if it does not — both
    directions, so a bare-`doi` record invalid for any other reason fails
    here rather than passing unexplained (#3597)."""
    doi = (yaml.safe_load(Path(row["path"]).read_text(encoding="utf-8")) or {}).get("doi")
    if isinstance(doi, str) and doi.startswith("https://doi.org/"):
        case.assertEqual(row["status"], INVALID, row["findings"])
        case.assertTrue(any("in /doi" in f for f in row["findings"]), row["findings"])
    else:
        case.assertEqual(row["status"], VALID, row["findings"])


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

    def test_a_duplicate_key_survives_a_validator_that_did_not_run(self):
        """#1032, review #3610: the duplicate is read off the text, which
        needs no validator, so a record known to be invalid is reported
        INVALID — with the failure kept, since the schema was not checked —
        and not as "could not be checked". A record with no duplicate stays
        UNVERIFIED (#613)."""
        down = (None, "linkml-validate did not run: x")
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch("data_sheets_schema.api_runner._validator_lines",
                           return_value=down):
            concat = _tree(Path(tmp), {
                "rocrate_static_map/v1/DUP_d4d.yaml": VALID_RECORD + "title: Another\n",
                "rocrate_static_map/v1/OK_d4d.yaml": VALID_RECORD,
            })
            findings, failure = _validate_deterministic(
                concat / "rocrate_static_map/v1/DUP_d4d.yaml")
            self.assertEqual(failure, down[1])
            self.assertEqual(len(findings), 1)
            self.assertIn("duplicate mapping key", findings[0])
            rows = {r["project"]: r for r in deterministic_validity(concat)}
            self.assertEqual(rows["DUP"]["status"], INVALID)
            self.assertEqual(rows["DUP"]["failure"], down[1])
            self.assertEqual(rows["OK"]["status"], UNVERIFIED)
            self.assertEqual(rows["OK"]["findings"], [])

    def test_an_unreadable_record_is_not_checked_and_does_not_crash(self):
        """Review #3616: a `*_d4d.yaml` that cannot be read — a directory
        with that name, or a file with no read permission — is UNVERIFIED
        with the reason kept, not an OSError that aborts the whole check.
        The validator is never asked about bytes nobody could read."""
        import os
        with tempfile.TemporaryDirectory() as tmp:
            concat = _tree(Path(tmp), {"rocrate_static_map/v1/OK_d4d.yaml": VALID_RECORD})
            (concat / "rocrate_static_map/v1/DIR_d4d.yaml").mkdir()
            locked = concat / "rocrate_static_map/v1/LOCK_d4d.yaml"
            locked.write_text(VALID_RECORD, encoding="utf-8")
            locked.chmod(0)
            try:
                readable = os.access(locked, os.R_OK)   # True when run as root
                with mock.patch("data_sheets_schema.api_runner._validator_lines",
                                return_value=([], None)) as validator:
                    rows = {r["project"]: r for r in deterministic_validity(concat)}
            finally:
                locked.chmod(0o644)
            self.assertEqual(rows["OK"]["status"], VALID)
            unreadable = ["DIR"] + ([] if readable else ["LOCK"])
            for proj in unreadable:
                with self.subTest(project=proj):
                    self.assertEqual(rows[proj]["status"], UNVERIFIED)
                    self.assertEqual(rows[proj]["findings"], [])
                    self.assertIn("record could not be read", rows[proj]["failure"])
            called = {Path(c.args[0]).name for c in validator.call_args_list}
            self.assertEqual(called & {f"{p}_d4d.yaml" for p in unreadable}, set())

    def test_the_verdict_check_holds_in_both_directions(self):
        """The helper the corpus test applies, on the real validator: it
        accepts a resolver-URL `doi` judged invalid and a bare one judged
        valid, and rejects a bare-`doi` record that is invalid for another
        reason. Today's committed records all carry the resolver URL, so
        only this test exercises the bare-`doi` direction (#3597)."""
        with tempfile.TemporaryDirectory() as tmp:
            concat = _tree(Path(tmp), {
                "rocrate_static_map/v1/BAD_d4d.yaml": RESOLVER_DOI,
                "rocrate_static_map/v1/GOOD_d4d.yaml": VALID_RECORD,
                "rocrate_static_map/v1/DUP_d4d.yaml": VALID_RECORD + "title: Another\n",
            })
            rows = {r["project"]: r for r in deterministic_validity(concat)}
            self.assertEqual(set(rows), {"BAD", "GOOD", "DUP"})
            _assert_verdict_explained(self, rows["BAD"])
            _assert_verdict_explained(self, rows["GOOD"])
            self.assertEqual(rows["DUP"]["status"], INVALID)
            with self.assertRaises(AssertionError):
                _assert_verdict_explained(self, rows["DUP"])


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

    def test_an_invalid_row_whose_schema_was_not_checked_says_so(self):
        """A duplicate key found while the validator could not run is printed
        as invalid, with a line saying the schema was not checked (#3610)."""
        rows = [{"method": "rocrate_static_map", "label": "ourmap-v1",
                 "project": "CHORUS", "path": "x", "status": INVALID,
                 "findings": ["duplicate mapping key 'title'"],
                 "failure": "linkml-validate did not run: x"}]
        with mock.patch("data_sheets_schema.runs.deterministic_validity",
                        return_value=rows):
            result = CliRunner().invoke(cli, ["runs", "check"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("0 valid, 1 invalid, 0 could not be checked", result.output)
        out = result.output.splitlines()
        i = next(i for i, l in enumerate(out) if "duplicate mapping key" in l)
        self.assertIn("CHORUS", out[i])
        self.assertIn("schema not checked: linkml-validate did not run: x", out[i + 1])

    def test_an_unreadable_record_is_reported_and_strict_still_exits_zero(self):
        """Review #3616: an unreadable record is a "not checked" row, and the
        command reaches its own verdict rather than a traceback."""
        (self.root / "data/d4d_concatenated/rocrate_static_map/ourmap-v1/"
         "DIR_d4d.yaml").mkdir()
        result = CliRunner().invoke(cli, ["runs", "check", "--strict"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIsNone(result.exception, result.output)
        self.assertIn("3 deterministic-arm record(s) judged", result.output)
        self.assertIn("1 valid, 1 invalid, 1 could not be checked", result.output)
        line = [l for l in result.output.splitlines() if "DIR" in l and "ourmap-v1" in l]
        self.assertEqual(len(line), 1, result.output)
        self.assertIn("not checked: record could not be read", line[0])
        self.assertIn("Reported, never fatal", result.output)

    def test_the_filters_given_are_passed_through(self):
        """`--method/--label/--project` reach the section. This tree holds no
        generated run, so no report loop rebinds a name here: the rebinding
        case is the next test."""
        with mock.patch("data_sheets_schema.runs.deterministic_validity",
                        return_value=[]) as dv:
            result = CliRunner().invoke(cli, ["runs", "check", "--project", "VOICE",
                                              "--label", "ourmap-v1"])
        self.assertEqual(result.exit_code, 0, result.output)
        dv.assert_called_once_with(method=None, label="ourmap-v1", project="VOICE")

    def test_a_report_loop_that_rebinds_the_names_does_not_narrow_the_section(self):
        """`check`'s report loops rebind `project` and `label` (`for project,
        label, n in sorted(ungrounded)`) — but only when a generated run has a
        finding to list. The first version passed the names after those loops,
        so an unfiltered check asked the section for a generated run's label
        and printed nothing (#2970; review #3567). Here a complete generated
        run with an ungrounded identifier makes that loop run, in the fast
        lane, and the section must still see no filter."""
        _tree(self.root, {
            "claudecode_agent/gen_rep1/OTHER_d4d.yaml": VALID_RECORD,
            "claudecode_agent_core/gen_rep1/OTHER_d4d_core.yaml": VALID_RECORD,
            "claudecode_agent_core/gen_rep1/OTHER_reconciliation.md": "report\n",
        })
        from data_sheets_schema.runs import (CLAIMS_CONTRADICTED, GROUNDED_GAPS,
                                             PAIR_DIVERGENT)
        # All three listing loops run (#3521), not only the grounding one.
        with mock.patch("data_sheets_schema.runs.grounding_status",
                        return_value=(GROUNDED_GAPS, 1)), \
                mock.patch("data_sheets_schema.runs.report_claim_status",
                           return_value=(CLAIMS_CONTRADICTED, 2)), \
                mock.patch("data_sheets_schema.runs.pair_status",
                           return_value=(PAIR_DIVERGENT, 3)):
            result = CliRunner().invoke(cli, ["runs", "check"])
        # The loops ran over the generated run's names …
        for what in ("1 identifier(s)", "2 claim(s)", "3 error(s)"):
            self.assertTrue(any("OTHER" in l and "gen_rep1" in l and what in l
                                for l in result.output.splitlines()),
                            (what, result.output))
        # … and the section still judged both deterministic records.
        self.assertIn("2 deterministic-arm record(s) judged", result.output)
        self.assertIn("1 valid, 1 invalid, 0 could not be checked", result.output)


@pytest.mark.corpus   # walks the committed deterministic arms (#1203)
class TestTheCommittedArms(unittest.TestCase):
    def test_every_committed_record_gets_a_verdict_the_record_explains(self):
        """Each committed deterministic-arm record is judged (none left
        unchecked), and a record is invalid exactly where its `doi` still
        carries the resolver URL #646 made invalid: invalid with a `/doi`
        finding where it does, valid where it does not — the verdict follows
        the bytes, not a count pinned here. All 8 records committed today
        carry the resolver URL, so the valid direction does not run on this
        corpus; `test_the_verdict_check_holds_in_both_directions` exercises it
        on a fixture (#3597)."""
        concat = ROOT / CONCAT_DIR
        rows = deterministic_validity(concat)
        self.assertTrue(rows)
        self.assertEqual([], [r for r in rows if r["status"] == UNVERIFIED])
        for r in rows:
            with self.subTest(record=r["path"]):
                _assert_verdict_explained(self, r)

    def test_an_unfiltered_check_reports_every_committed_record(self):
        """The first version passed `label` and `project` after the report
        loops had rebound them to a generated run's, so on the real corpus
        the section asked for a label no deterministic arm has and printed
        nothing. Only a corpus with generated rows exercises that."""
        import os
        committed = deterministic_validity(ROOT / CONCAT_DIR,
                                           validate=lambda path: ([], None))
        cwd = Path.cwd()
        os.chdir(ROOT)
        self.addCleanup(os.chdir, cwd)
        result = CliRunner().invoke(cli, ["runs", "check"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn(f"{len(committed)} deterministic-arm record(s) judged", result.output)


if __name__ == "__main__":
    unittest.main()

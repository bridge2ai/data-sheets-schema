"""`d4d provenance recheck-validation --all` (#1033): every record is brought
under the duplicate-key instrument on one condition — the recomputed
verdict and the artifacts' md5s equal the recorded ones, so the write adds
the `duplicate_keys` field and nothing else. A record whose verdict or
artifacts would move is held and named; one already carrying the field is
skipped. Validation itself is stubbed: the gate is what is under test."""
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

from data_sheets_schema.cli import provenance as cli


def _record(tmp, passed=True, md5="m1", with_field=False):
    d = Path(tmp) / "claudecode_api_core" / "L_rep1"; d.mkdir(parents=True, exist_ok=True)
    (Path(tmp) / "claudecode_api" / "L_rep1").mkdir(parents=True, exist_ok=True)
    (Path(tmp) / "claudecode_api" / "L_rep1" / "P_d4d.yaml").write_text("id: x\n")
    (d / "P_d4d_core.yaml").write_text("id: x\n")
    block = {"passed": passed, "artifacts": {"full": {"md5": md5}, "core": {"md5": md5}}}
    if with_field:
        block["duplicate_keys"] = {"full": [], "core": []}
    (d / "P_provenance.yaml").write_text("# header\n" + yaml.safe_dump({"validation": block}))
    return d / "P_provenance.yaml"


class TestTheGate(unittest.TestCase):
    def _run(self, tmp, new_passed=True, new_md5="m1", execute=True, problems=(), schema=None):
        from data_sheets_schema.cli import provenance as cli
        block = {"passed": new_passed, "artifacts": {"full": {"md5": new_md5}, "core": {"md5": new_md5}},
                 "duplicate_keys": {"full": [], "core": []}, "problems": list(problems)}
        if schema is not None:
            block["schema"] = dict(schema)
        with mock.patch("data_sheets_schema.api_runner.validate_outputs", lambda spec: []), \
             mock.patch("data_sheets_schema.api_runner.validation_block", lambda spec, problems, recorded_by: dict(block)), \
             mock.patch("data_sheets_schema.provenance.record_path_for",
                        lambda project, method, label, concat_dir=None: Path(tmp) / "claudecode_api_core" / label / f"{project}_provenance.yaml"), \
             mock.patch("data_sheets_schema.api_runner.RunSpec") as spec_cls:
            spec = spec_cls.return_value
            spec.full_path = Path(tmp) / "claudecode_api" / "L_rep1" / "P_d4d.yaml"
            spec.core_path = Path(tmp) / "claudecode_api_core" / "L_rep1" / "P_d4d_core.yaml"
            return cli._recheck_one("claudecode_api", "L_rep1", "P", execute=execute, gated=True)

    def test_an_unchanged_verdict_is_written_with_the_field_added(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _record(tmp)
            self.assertEqual(self._run(tmp), "written")
            v = yaml.safe_load(path.read_text().split("\n", 1)[1])["validation"]
            self.assertIn("duplicate_keys", v); self.assertTrue(v["passed"])

    def test_a_moved_verdict_or_artifact_is_held_and_left_alone(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _record(tmp)
            before = path.read_text()
            self.assertEqual(self._run(tmp, new_passed=False), "held")
            self.assertEqual(self._run(tmp, new_md5="m2"), "held")
            self.assertEqual(path.read_text(), before)

    def test_problems_that_name_another_artifact_class_or_path_are_held_but_a_reworded_message_is_not(self):
        """A validator message carries today's enum list and moves with the
        schema while the failure it names does not; a failure on another
        artifact, class or JSON-pointer path is a different verdict (#1190
        review, M3: two written records had swapped one failure set for
        another under the same artifact and class)."""
        same = [{"artifact": "a", "class": "Dataset", "error": "'x' is not one of [a, b] in /related_datasets/0/relationship_type"}]
        with tempfile.TemporaryDirectory() as tmp:
            path = _record(tmp, passed=False)
            d = yaml.safe_load(path.read_text().split("\n", 1)[1]); d["validation"]["problems"] = same
            path.write_text("# header\n" + yaml.safe_dump(d))
            reworded = [{"artifact": "a", "class": "Dataset", "error": "'x' is not one of [a, b, c, d] in /related_datasets/0/relationship_type"}]
            self.assertEqual(self._run(tmp, new_passed=False, problems=reworded), "written")
            path = _record(tmp, passed=False)
            path.write_text("# header\n" + yaml.safe_dump(d))
            other_path = [{"artifact": "a", "class": "Dataset", "error": "True is not valid in /creators/0/principal_investigator"}]
            self.assertEqual(self._run(tmp, new_passed=False, problems=other_path), "held")
            path = _record(tmp, passed=False)
            path.write_text("# header\n" + yaml.safe_dump(d))
            elsewhere = [{"artifact": "a", "class": "Person", "error": "old wording"}]
            self.assertEqual(self._run(tmp, new_passed=False, problems=elsewhere), "held")
            self.assertNotIn("duplicate_keys", yaml.safe_load(path.read_text().split("\n", 1)[1])["validation"])

    def test_a_record_already_under_the_instrument_is_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _record(tmp, with_field=True)
            before = path.read_text()
            self.assertEqual(self._run(tmp), "already")
            self.assertEqual(path.read_text(), before)

    def test_all_visits_each_record_once_and_names_a_method_that_matches_nothing(self):
        """#1190 review, M1/S3/S5: `discover` yields a base directory and its
        _core twin as two runs over one record; the walk is keyed on the
        record path, the summary counts records, and a --method that
        reaches no directory is an error rather than a silent all-zero."""
        import click.testing
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as tmp:
            path = _record(tmp)
            runs = [SimpleNamespace(method="claudecode_api", label="L_rep1", projects=["P"]),
                    SimpleNamespace(method="claudecode_api_core", label="L_rep1", projects=["P"])]
            calls = []
            def one(method, label, project, execute, gated):
                calls.append(method); return "written"
            with mock.patch("data_sheets_schema.runs.discover", lambda: runs), \
                 mock.patch("data_sheets_schema.provenance.record_path_for",
                            lambda project, method, label, concat_dir=None: path), \
                 mock.patch.object(cli, "_recheck_one", one), \
                 mock.patch.object(cli, "_require_repo_root_cwd", lambda *a, **k: None):
                r = click.testing.CliRunner().invoke(cli.provenance, ["recheck-validation", "--all", "--execute"])
                self.assertEqual(r.exit_code, 0, r.output); self.assertEqual(len(calls), 1)
                self.assertIn("summary over 1 record(s): written 1, would write 0, already 0", r.output)
                r = click.testing.CliRunner().invoke(cli.provenance, ["recheck-validation", "--all", "--method", "claudecode_api_core"])
                self.assertEqual(len(calls), 2)
                r = click.testing.CliRunner().invoke(cli.provenance, ["recheck-validation", "--all", "--method", "nosuch"])
                self.assertNotEqual(r.exit_code, 0); self.assertIn("matched no run directory", r.output)

    def test_a_gated_dry_run_counts_what_it_would_write_and_says_when_the_schema_digest_moves(self):
        """#1190 review, S2/M4; round 2, S2: the message is asserted on a
        populated new digest, not on the empty rendering."""
        import contextlib, io
        with tempfile.TemporaryDirectory() as tmp:
            path = _record(tmp)
            d = yaml.safe_load(path.read_text().split("\n", 1)[1]); d["validation"]["schema"] = {"full_sha256": "oldoldoldold"}
            path.write_text("# header\n" + yaml.safe_dump(d))
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                self.assertEqual(self._run(tmp, execute=False, schema={"full_sha256": "newnewnewnew"}), "would write")
            self.assertIn("schema digest restamped", buf.getvalue())
            self.assertIn("full_sha256 oldoldol→newnewne", buf.getvalue())
            self.assertNotIn("duplicate_keys", yaml.safe_load(path.read_text().split("\n", 1)[1])["validation"])

    def test_a_record_already_under_the_instrument_is_rechecked_when_its_schema_pin_moved(self):
        """#1190 round 2, M1: a corpus pass taken before the branch merged a
        schema change left records pinning the older digest, which
        `validation_status` reads as STALE, and the `already` short circuit
        made it unrepairable."""
        with tempfile.TemporaryDirectory() as tmp:
            path = _record(tmp, with_field=True)
            d = yaml.safe_load(path.read_text().split("\n", 1)[1]); d["validation"]["schema"] = {"full_sha256": "stale"}
            path.write_text("# header\n" + yaml.safe_dump(d))
            with mock.patch.object(cli, "_schema_pin_moved", lambda block: True):
                self.assertEqual(self._run(tmp, schema={"full_sha256": "fresh"}), "written")
            self.assertEqual(yaml.safe_load(path.read_text().split("\n", 1)[1])["validation"]["schema"],
                             {"full_sha256": "fresh"})
            with mock.patch.object(cli, "_schema_pin_moved", lambda block: False):
                self.assertEqual(self._run(tmp, schema={"full_sha256": "fresh"}), "already")

    def test_report_mode_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _record(tmp)
            before = path.read_text()
            self.assertEqual(self._run(tmp, execute=False), "would write")               # gated: what --execute would do
            self.assertEqual(path.read_text(), before)


if __name__ == "__main__":
    unittest.main()

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
    def _run(self, tmp, new_passed=True, new_md5="m1", execute=True, problems=()):
        from data_sheets_schema.cli import provenance as cli
        block = {"passed": new_passed, "artifacts": {"full": {"md5": new_md5}, "core": {"md5": new_md5}},
                 "duplicate_keys": {"full": [], "core": []}, "problems": list(problems)}
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

    def test_problems_that_name_another_artifact_or_class_are_held_but_a_reworded_message_is_not(self):
        """The eight failing records the corpus run wrote carry the same
        failures under a longer enum list in the message; a record whose
        failures move to another artifact or class is a different verdict."""
        same = [{"artifact": "a", "class": "Dataset", "error": "old wording"}]
        with tempfile.TemporaryDirectory() as tmp:
            path = _record(tmp, passed=False)
            d = yaml.safe_load(path.read_text().split("\n", 1)[1]); d["validation"]["problems"] = same
            path.write_text("# header\n" + yaml.safe_dump(d))
            reworded = [{"artifact": "a", "class": "Dataset", "error": "new wording with a longer list"}]
            self.assertEqual(self._run(tmp, new_passed=False, problems=reworded), "written")
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

    def test_report_mode_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _record(tmp)
            before = path.read_text()
            self.assertEqual(self._run(tmp, execute=False), "reported")
            self.assertEqual(path.read_text(), before)


if __name__ == "__main__":
    unittest.main()

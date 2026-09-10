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


def _record(tmp, passed=True, md5=None, with_field=False, algo="md5"):
    """The artifacts carry a path and a hash of that path's bytes, as the
    corpus does — 82 corpus records pin `sha256` only and 118 `md5` only
    (#1190 round 3, M1), so `algo` selects which."""
    import hashlib
    d = Path(tmp) / "claudecode_api_core" / "L_rep1"; d.mkdir(parents=True, exist_ok=True)
    (Path(tmp) / "claudecode_api" / "L_rep1").mkdir(parents=True, exist_ok=True)
    full = Path(tmp) / "claudecode_api" / "L_rep1" / "P_d4d.yaml"; full.write_text("id: x\n")
    core = d / "P_d4d_core.yaml"; core.write_text("id: x\n")
    def h(p):
        return md5 if md5 else getattr(hashlib, algo)(p.read_bytes()).hexdigest()
    block = {"passed": passed, "artifacts": {"full": {"path": str(full), algo: h(full)},
                                             "core": {"path": str(core), algo: h(core)}}}
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
            self.assertEqual(path.read_text(), before)
        # an artifact whose bytes moved since the verdict is held, under
        # either hash algorithm the corpus uses (#1190 round 3, M1)
        for algo in ("md5", "sha256"):
            with tempfile.TemporaryDirectory() as tmp:
                path = _record(tmp, algo=algo); before = path.read_text()
                self.assertEqual(self._run(tmp), "written", algo)      # unmoved: written
            with tempfile.TemporaryDirectory() as tmp:
                path = _record(tmp, algo=algo); before = path.read_text()
                (Path(tmp) / "claudecode_api" / "L_rep1" / "P_d4d.yaml").write_text("id: edited\n")
                self.assertEqual(self._run(tmp), "held", algo)
                self.assertEqual(path.read_text(), before, algo)

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


class TestTheRecordedAlgorithmSurvives(unittest.TestCase):
    """#1190 round 4, M1: `validation_block` hashes with md5 and was never
    brought under #204, which unified provenance hashing on sha256 and
    deprecated md5. A recheck that wrote its output as it stood moved a
    record back to the deprecated algorithm and destroyed the sha256 values
    it had attested, while both documents said the write changed nothing but
    the duplicate-key field, the schema digest and the recorder."""

    def _entry(self, tmp, text="a: 1\n"):
        import hashlib
        p = Path(tmp) / "art.yaml"; p.write_text(text)
        return p, hashlib.sha256(p.read_bytes()).hexdigest(), hashlib.md5(p.read_bytes()).hexdigest()

    def test_a_sha256_only_entry_is_rewritten_in_sha256(self):
        with tempfile.TemporaryDirectory() as tmp:
            p, sha, md5 = self._entry(tmp)
            out = cli._keep_recorded_algorithms(
                {"full": {"path": str(p), "md5": md5}},
                {"full": {"path": str(p), "sha256": "an old value"}})
            self.assertEqual(out["full"], {"path": str(p), "sha256": sha})
            self.assertNotIn("md5", out["full"])

    def test_an_md5_only_entry_stays_md5_and_both_stay_both(self):
        with tempfile.TemporaryDirectory() as tmp:
            p, sha, md5 = self._entry(tmp)
            self.assertEqual(cli._keep_recorded_algorithms({"full": {"path": str(p), "md5": md5}},
                                                           {"full": {"path": str(p), "md5": "old"}}),
                             {"full": {"path": str(p), "md5": md5}})
            both = cli._keep_recorded_algorithms({"full": {"path": str(p), "md5": md5}},
                                                 {"full": {"path": str(p), "md5": "old", "sha256": "old"}})
            self.assertEqual(both["full"], {"path": str(p), "md5": md5, "sha256": sha})

    def test_a_hash_is_recomputed_not_copied(self):
        with tempfile.TemporaryDirectory() as tmp:
            p, sha, md5 = self._entry(tmp)
            p.write_text("a: 2\n")
            import hashlib
            out = cli._keep_recorded_algorithms({"full": {"path": str(p), "md5": "x"}},
                                                {"full": {"path": str(p), "sha256": sha}})
            self.assertEqual(out["full"]["sha256"], hashlib.sha256(p.read_bytes()).hexdigest())
            self.assertNotEqual(out["full"]["sha256"], sha)

    def test_a_missing_file_an_empty_path_and_an_unknown_algorithm_are_left_alone(self):
        for prior in ({"path": "/no/such/file", "sha256": "x"}, {"path": "", "sha256": "x"},
                      {"path": "/no/such/file", "crc32": "x"}, "not a mapping"):
            with self.subTest(prior=prior):
                new = {"full": {"path": str(prior.get("path", "")) if isinstance(prior, dict) else "", "md5": "m"}}
                self.assertEqual(cli._keep_recorded_algorithms(new, {"full": prior}), new)


class TestSchemaPinMoved(unittest.TestCase):
    """#1190 round 4, S1: the predicate was reached only through a test that
    patched it out, so its own semantics were unpinned — and a `schema` that
    is not a mapping raised and aborted the whole `--all` walk."""

    def test_an_absent_empty_or_null_pin_is_not_moved(self):
        for block in ({}, {"schema": {}}, {"schema": {"full_sha256": None}},
                      {"schema": {"full_sha256": ""}}):
            with self.subTest(block=block):
                self.assertFalse(cli._schema_pin_moved(block))

    def test_a_schema_that_is_not_a_mapping_is_not_a_pin_and_does_not_raise(self):
        for block in ({"schema": "b9b31aca"}, {"schema": ["b9b31aca"]}, {"schema": 7}):
            with self.subTest(block=block):
                self.assertFalse(cli._schema_pin_moved(block))

    def test_a_live_key_the_pin_lacks_is_not_moved_and_a_pin_that_differs_is(self):
        from data_sheets_schema.provenance import CORE_SCHEMA, FULL_SCHEMA, _sha256
        live_full, live_core = _sha256(FULL_SCHEMA), _sha256(CORE_SCHEMA)
        self.assertFalse(cli._schema_pin_moved({"schema": {"full_sha256": live_full}}))
        self.assertFalse(cli._schema_pin_moved({"schema": {"full_sha256": live_full, "core_sha256": live_core}}))
        self.assertTrue(cli._schema_pin_moved({"schema": {"full_sha256": "something else"}}))
        self.assertTrue(cli._schema_pin_moved({"schema": {"full_sha256": live_full, "core_sha256": "moved"}}))

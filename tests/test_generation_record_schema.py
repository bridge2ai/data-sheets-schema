"""The generation record has a schema of its own.

This repository schematises metadata about datasets. Its own generation
metadata was a hand-built Python dictionary written as YAML — 25 top-level
keys, `record_version: 1`, and nothing that could validate it. The one artifact
that *did* carry a LinkML schema, `d4d_run_telemetry.yaml`, is the derived
report rather than the authoritative record.

The schema describes today's record rather than a tidier one. Across 195
records the shape genuinely varies by `record_mode`, and requiring a field an
honest record cannot have would make the schema a fiction.
"""

import re
import subprocess
import unittest
from pathlib import Path

import yaml

SCHEMA = Path("src/data_sheets_schema/schema/d4d_generation_record.yaml")
CORPUS = Path("data/d4d_concatenated")


class SchemaShapeTest(unittest.TestCase):

    def setUp(self):
        if not SCHEMA.exists():
            self.skipTest("schema not present in this checkout")
        self.schema = yaml.safe_load(SCHEMA.read_text(encoding="utf-8"))

    def test_it_is_not_imported_by_the_dataset_schema(self):
        """Importing it would move the `Dataset` digest an arm is frozen
        against, and it describes the pipeline rather than a dataset."""
        main = yaml.safe_load(
            Path("src/data_sheets_schema/schema/data_sheets_schema.yaml")
            .read_text(encoding="utf-8"))
        self.assertNotIn("d4d_generation_record", main.get("imports") or [])

    def test_only_universal_fields_are_required(self):
        """A `derived` record has no `inputs`, `model` or `system`; requiring
        them would make the schema describe a record that does not exist."""
        attrs = self.schema["classes"]["GenerationRecord"]["attributes"]
        required = {k for k, v in attrs.items() if v.get("required")}
        for optional in ("inputs", "model", "system", "api_usage",
                         "playbooks", "prompts", "derivation", "sources"):
            with self.subTest(field=optional):
                self.assertNotIn(optional, required)
        for universal in ("record_type", "record_version", "record_mode",
                          "run", "schema", "outputs"):
            with self.subTest(field=universal):
                self.assertIn(universal, required)

    def test_the_three_record_modes_are_enumerated(self):
        values = self.schema["enums"]["RecordMode"]["permissible_values"]
        self.assertEqual(set(values), {"live", "reconstructed", "derived"})

    def test_variable_blocks_are_declared_as_such(self):
        """`AnyBlock` says a block exists and what it is for without freezing
        an interior that is still being added to — `grounding` gained a finding
        kind this week. A schema needing an edit before an additive change can
        be recorded would be a brake rather than a contract."""
        self.assertEqual(
            self.schema["classes"]["AnyBlock"]["class_uri"], "linkml:Any")


class CompanionReferenceTest(unittest.TestCase):
    """Everything else a reader needs, by reference (#596 and this thread)."""

    def test_the_record_points_at_its_companions(self):
        from data_sheets_schema.provenance import companion_facts
        c = companion_facts("CHORUS", "claudecode_agent",
                            "2026-08-13_claude-opus-5-api-generic-v4_rep1")
        self.assertEqual(set(c), {"reasoning_log", "telemetry_report",
                                  "prompt_registry", "digest_inventory"})

    def test_absence_is_recorded_rather_than_omitted(self):
        """An absent reasoning log is a fact about the runtime (#400), not a
        gap in the record — so the reference exists and says `present: false`.
        """
        from data_sheets_schema.provenance import companion_facts
        c = companion_facts("NO_SUCH_PROJECT", "claudecode_agent", "nope")
        self.assertFalse(c["reasoning_log"]["present"])
        self.assertTrue(c["reasoning_log"]["path"])

    def test_registries_are_referenced_by_hash_not_copied(self):
        """A registry is shared and appended to over time: copying it into
        every record would multiply it and still not say which version was in
        force. A hash does say."""
        from data_sheets_schema.provenance import companion_facts
        c = companion_facts("CHORUS", "claudecode_agent",
                            "2026-08-13_claude-opus-5-api-generic-v4_rep1")
        if not c["prompt_registry"]["present"]:
            self.skipTest("registry not present in this checkout")
        self.assertTrue(c["prompt_registry"]["md5"])


class CorpusValidatesTest(unittest.TestCase):

    def test_a_real_record_validates(self):
        """One record, run through the real validator. The corpus-wide pass is
        `d4d provenance validate-records --strict`, too slow for a unit test at
        one linkml-validate invocation per record."""
        p = (CORPUS / "claudecode_agent_core"
             / "2026-08-13_claude-opus-5-api-generic-v4_rep1"
             / "CHORUS_provenance.yaml")
        if not (p.exists() and SCHEMA.exists()):
            self.skipTest("record or schema not present in this checkout")
        r = subprocess.run(
            ["poetry", "run", "linkml-validate", "-s", str(SCHEMA),
             "-C", "GenerationRecord", str(p)],
            capture_output=True, text=True, timeout=300)
        self.assertEqual(r.returncode, 0, (r.stdout + r.stderr)[-500:])

    def test_a_record_missing_a_required_field_is_rejected(self):
        """Otherwise the schema is decorative."""
        import tempfile
        if not SCHEMA.exists():
            self.skipTest("schema not present in this checkout")
        with tempfile.TemporaryDirectory() as d:
            bad = Path(d) / "bad.yaml"
            bad.write_text(yaml.safe_dump(
                {"record_type": "d4d_generation_provenance",
                 "record_version": 1, "record_mode": "live"}),
                encoding="utf-8")
            r = subprocess.run(
                ["poetry", "run", "linkml-validate", "-s", str(SCHEMA),
                 "-C", "GenerationRecord", str(bad)],
                capture_output=True, text=True, timeout=300)
            self.assertNotEqual(r.returncode, 0)


class ValidatorControl(unittest.TestCase):
    """Base class: prove the validator works before trusting a clean result.

    `check_record` returns no violations both when a record conforms and when it
    could not be checked (#613). Three tests below assert "no violations", so
    with a dead validator they would all pass having verified nothing — the
    vacuous-pass shape of #617. Every one of them goes through `_control`
    first, which fails rather than skips if a known-bad record comes back clean.
    """

    BASELINE = (Path("data/d4d_concatenated/claudecode_agent_core")
                / "2026-08-13_claude-opus-5-api-generic-v4_rep1"
                / "CHORUS_provenance.yaml")

    def _control(self):
        """A conforming record, having first proved the validator discriminates."""
        from data_sheets_schema.provenance import check_record
        if not (self.BASELINE.exists() and SCHEMA.exists()):
            self.skipTest("record or schema not present in this checkout")
        record = yaml.safe_load(self.BASELINE.read_text(encoding="utf-8"))

        # Positive control, and specifically a control on the **rules**.
        #
        # The first version deleted `record_mode`, which is `required: true` at
        # the attribute level — so it still produced findings with every rule
        # stripped from the schema, and proved only that the validator was
        # alive (#620). Since the regression this class exists to catch is a
        # rule that stops being enforced, a control that survives the rules'
        # removal guards nothing.
        #
        # A live record missing `model` is rejected *only* by the live rule.
        # Verified by deleting the rules block: this comes back clean.
        findings, failure = check_record(
            {k: v for k, v in record.items() if k != "model"})
        self.assertIsNone(failure, f"the validator could not run: {failure}")
        self.assertTrue(findings,
                        "a live record with no `model` was reported clean, so "
                        "the mode rules are not being enforced and every 'no "
                        "violations' assertion below would pass vacuously")

        findings, failure = check_record(record)
        self.assertIsNone(failure, f"the validator could not run: {failure}")
        self.assertEqual(findings, [],
                         "the baseline record does not conform, so it cannot "
                         "serve as the starting point for these mutations")
        return record


class ModeSpecificRequirements(ValidatorControl):
    """#605: the schema was mode-blind, so it asserted almost nothing.

    The required fields are **derived from `build_record`**, the single writer
    both runtimes go through, rather than listed here. The first version listed
    them from the archive and so required `validation`, which no writer emits —
    it is filled in later by `d4d runs validate`. That rejected every freshly
    written agentic record (#612). Deriving them means the schema and the writer
    cannot drift apart without this test noticing.
    """

    def _writer_fields(self, mode):
        """What the real writer emits for a mode, at write time.

        `derived` goes through `build_derived_record`, a different function —
        covering it here rather than fabricating a derived record by mutating a
        live one, since a fabrication proves nothing about what the writer
        emits and `derived` has the most required fields of the three (#620).
        """
        import tempfile

        from data_sheets_schema.provenance import (Contribution, build_record,
                                                   build_derived_record)
        if mode == "derived":
            with tempfile.TemporaryDirectory() as d:
                out = Path(d) / "X_d4d.yaml"
                out.write_text("id: x\n", encoding="utf-8")
                return build_derived_record(
                    "AI_READI", "claudecode_agent", "test",
                    sources=[Contribution(label="l", project="AI_READI",
                                          method="claudecode_agent",
                                          path=str(out), sha256="deadbeef")],
                    derivation="a test record", outputs={"full": out}).data
        bundle = Path("data/preprocessed/concatenated/AI_READI_preprocessed.txt")
        if not bundle.exists():
            self.skipTest("no bundle in this checkout to build a record from")
        return build_record("AI_READI", "claudecode_agent", "test_rep1",
                            mode=mode, input_bundle=bundle,
                            input_verified=True).data

    def _rule_requirements(self, mode):
        """What the schema requires of a mode, read from the rules."""
        schema = yaml.safe_load(SCHEMA.read_text(encoding="utf-8"))
        out = set()
        for rule in schema["classes"]["GenerationRecord"].get("rules") or []:
            pre = ((rule.get("preconditions") or {}).get("slot_conditions")
                   or {}).get("record_mode") or {}
            if pre.get("equals_string") != mode:
                continue
            post = ((rule.get("postconditions") or {}).get("slot_conditions")
                    or {})
            out |= {k for k, v in post.items() if v.get("required")}
        return out

    def test_no_rule_requires_a_field_no_writer_writes(self):
        """The #612 defect, in its general form.

        A rule requiring something the writer does not emit rejects records the
        pipeline produces correctly — and the justification for these rules is
        that they describe the writers.
        """
        if not SCHEMA.exists():
            self.skipTest("schema not present in this checkout")
        for mode in ("live", "reconstructed", "derived"):
            with self.subTest(mode=mode):
                written = set(self._writer_fields(mode))
                missing = sorted(self._rule_requirements(mode) - written)
                self.assertEqual(
                    missing, [],
                    f"the schema requires {missing} of a {mode} record, but "
                    "build_record does not emit them, so every fresh record "
                    "fails the gate")

    def test_a_freshly_written_record_conforms(self):
        """The same thing end to end, through the real builder."""
        self._control()
        from data_sheets_schema.provenance import check_record
        for mode in ("live", "reconstructed", "derived"):
            with self.subTest(mode=mode):
                findings, failure = check_record(self._writer_fields(mode))
                self.assertIsNone(failure)
                self.assertEqual(findings, [])

    def test_a_live_record_must_carry_what_a_live_run_observed(self):
        from data_sheets_schema.provenance import record_conformance
        record = self._control()
        required = self._rule_requirements("live")
        self.assertTrue(required, "the live rule requires nothing at all")
        for field in sorted(required):
            with self.subTest(field=field):
                short = {k: v for k, v in record.items() if k != field}
                self.assertTrue(
                    record_conformance(short),
                    f"a live record with no {field!r} validated; before #605 "
                    "all of these did")

    def test_a_derived_record_may_omit_them(self):
        """The requirements must be conditional, not a blanket tightening.

        A derived record consumes records rather than a bundle and has no model
        at all. If dropping the mode made no difference to the verdict, the
        rules would be requiring these of everything, and four honest records
        on disk would be reclassified as defective.
        """
        from data_sheets_schema.provenance import check_record
        record = self._control()
        derived = {k: v for k, v in record.items()
                   if k not in self._rule_requirements("live")}
        derived.update(record_mode="derived",
                       record_type="d4d_derived_provenance",
                       derivation={"method": "test"},
                       sources=[{"path": "x", "sha256": "y"}],
                       not_applicable=[{"field": "model", "reason": "test"}])
        findings, failure = check_record(derived)
        self.assertIsNone(failure)
        self.assertEqual(findings, [])

    def test_the_two_discriminators_cannot_disagree(self):
        from data_sheets_schema.provenance import record_conformance
        record = self._control()
        confused = {**record, "record_mode": "derived"}
        self.assertTrue(record_conformance(confused),
                        "a record calling itself derived while typed as a "
                        "generation record validated")

    def test_every_record_the_checkers_look_at_conforms(self):
        """The requirements describe the writers; they do not fail the corpus.

        A rule that is right in principle and rejects records nobody can
        regenerate is not an improvement — it is a schema that has to be
        ignored, which is where this started.

        Scoped to the `*_core/` glob that `d4d provenance validate-records`
        uses, and *named* for that scope rather than "every record on disk":
        three `curated/` records sit outside it and do not conform, three of
        those violations predating this schema (#616). Claiming disk-wide
        conformance while checking a glob is the kind of overreach this corpus
        keeps having to correct.
        """
        self._control()
        from data_sheets_schema.provenance import check_record
        records = sorted(Path("data/d4d_concatenated").glob(
            "*_core/*/*_provenance.yaml"))
        if not records:
            self.skipTest("no records in this checkout")
        failures = []
        for path in records:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            findings, failure = check_record(data)
            self.assertIsNone(failure, f"{path}: {failure}")
            failures += [f"{path}: {m}" for m in findings]
        self.assertEqual(failures[:5], [], f"{len(failures)} violations")


class ConformanceIsOnTheGenerationPath(ValidatorControl):
    """A check that exists but does not run on the path it guards is #582.

    Validation used to be reachable only through `d4d provenance
    validate-records`, so a run could finish, report success, and leave a
    non-conforming record behind.
    """

    def test_write_reports_conformance_of_what_it_wrote(self):
        import tempfile

        from data_sheets_schema.provenance import ProvenanceRecord
        path = (Path("data/d4d_concatenated/claudecode_agent_core")
                / "2026-08-13_claude-opus-5-api-generic-v4_rep1"
                / "CHORUS_provenance.yaml")
        if not (path.exists() and SCHEMA.exists()):
            self.skipTest("record or schema not present in this checkout")
        good = yaml.safe_load(path.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as d:
            rec = ProvenanceRecord(data=good)
            rec.write(Path(d) / "ok.yaml")
            # Fails rather than skips on a truthy result. Calling a genuinely
            # non-conforming record an environment problem is how a real defect
            # gets skipped past in CI (#617).
            self.assertIsNone(rec.conformance_failure,
                              f"the validator could not run: "
                              f"{rec.conformance_failure}")
            self.assertEqual(rec.conformance, [],
                             "the baseline record does not conform")

            # `validation` is preserved from a prior file by `write`, so drop a
            # field that is not carried forward.
            bad = {k: v for k, v in good.items() if k != "model"}
            rec = ProvenanceRecord(data=bad)
            out = rec.write(Path(d) / "bad.yaml")
            self.assertTrue(rec.conformance,
                            "write() did not notice a live record with no model")
            self.assertTrue(out.exists(),
                            "the record must still be written: it is the run's "
                            "only account of itself")

    def test_a_record_that_could_not_be_checked_is_not_reported_as_clean(self):
        """The distinction the gate turns on (#613).

        `check_record` returns no violations in both cases, so if the failure
        were not reported separately a broken validator would pass an entire
        sweep with every run printing a tick.
        """
        import tempfile
        import unittest.mock as mock

        from data_sheets_schema import provenance
        from data_sheets_schema.provenance import ProvenanceRecord
        if not self.BASELINE.exists():
            self.skipTest("record not present in this checkout")
        good = yaml.safe_load(self.BASELINE.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as d:
            with mock.patch.object(provenance, "record_schema_path",
                                   lambda: Path(d) / "absent.yaml"):
                rec = ProvenanceRecord(data=good)
                rec.write(Path(d) / "r.yaml")
            self.assertEqual(rec.conformance, [],
                             "an unrunnable validator must not invent findings")
            self.assertTrue(rec.conformance_failure,
                            "a record that could not be checked was reported "
                            "as conforming")

    def test_the_gate_still_works_away_from_the_repo_root(self):
        """Otherwise the gate silently passes everything a sweep writes.

        `RECORD_SCHEMA` is repo-relative, matching its siblings, but those are
        read by commands run from the repo root and this one runs during
        generation.

        Asserts the gate *discriminates* from another directory, not merely
        that a file exists there. A schema that resolves but is stale, or a
        validator that fails from that cwd for any other reason, would satisfy
        an existence check while reporting every record clean (#618).
        """
        import os
        import tempfile

        from data_sheets_schema.provenance import check_record
        if not self.BASELINE.exists():
            self.skipTest("record not present in this checkout")
        good = yaml.safe_load(self.BASELINE.read_text(encoding="utf-8"))
        bad = {k: v for k, v in good.items() if k != "model"}
        cwd = os.getcwd()
        try:
            # os.chdir is process-global, so this cannot run under pytest -n
            # without corrupting siblings. Restored in `finally`.
            with tempfile.TemporaryDirectory() as d:
                os.chdir(d)
                findings, failure = check_record(bad)
                self.assertIsNone(
                    failure, f"the gate could not run from {d}: {failure}")
                self.assertTrue(
                    findings,
                    "a live record with no model was reported clean from a "
                    "directory that is not the repo root")
                self.assertEqual(check_record(good), ([], None))
        finally:
            os.chdir(cwd)


class TheSchemaKnowsEveryFieldTheWritersWrite(unittest.TestCase):
    """The general form of the gap the conformance gate found first.

    `report_regenerated_after_repair` is written by `execute()` only when
    repair rewrites a record after the report was rendered. No record on disk
    carries it, so validating the corpus could not reach it, and the schema
    forbade it — meaning the first real repair-with-report-regeneration run
    would have failed at the new gate.

    This reads the writers instead of the archive, so a field added to a rarely
    taken branch is caught when it is added rather than when it first fires.
    """

    #: Where record fields are set, and under which local name. The first
    #: version scanned only for `rec.data["x"]` with a regex and so saw 14 of
    #: 34 fields — missing both builders entirely, because each assembles its
    #: record as a **dict literal** that no assignment regex can see (#615).
    #: An AST scan reads the literals, so the two writers that produce the whole
    #: agentic and derived records are covered.
    #:
    #: Scoped to the **functions** that build a record, not whole files. A
    #: file-wide scan of `api_runner.py` picks up every unrelated dict called
    #: `data` — progress files, phase payloads — and reports them as forbidden
    #: record fields. `src/renderer` and `src/validation` have one too, and
    #: neither writes provenance.
    #: Round 2 (#620) found five more record-mutating functions absent from the
    #: first version of this list, and three idioms the scan could not see.
    #: None violated the schema, but the docstring claimed "every record field
    #: any writer sets" — so the guard was narrower than the promise, which is
    #: the failure mode it exists to prevent one level up.
    WRITERS = {
        "src/data_sheets_schema/provenance.py": {
            "build_record": ("data",),
            "build_derived_record": ("data",),
            "apply_observed_effort": ("data",),
            "apply_effort_basis": ("data",),
            "apply_historical_prompt": ("data",),
        },
        "src/data_sheets_schema/cli/runs.py": {
            "validate_cmd": ("data",),
            "select_cmd": ("data", "prior"),
        },
        "src/data_sheets_schema/cli/provenance.py": {
            "backfill_context": ("rec",),
        },
        "src/data_sheets_schema/backfill_checks.py": {
            "apply": ("record",),
        },
    }

    #: Attribute-style record mutation, `rec.data["x"] = …`, which `execute()`
    #: uses and which is a subscript on an attribute rather than on a name.
    ATTRIBUTE_WRITE = re.compile(r"""(?:rec|record)\.data\[["']([a-z_]+)["']\]""")

    #: Where `execute()` sets record fields. Scanned across the whole file
    #: because `rec.data[...]` is unambiguous — it names the record object.
    ATTRIBUTE_WRITE_FILE = "src/data_sheets_schema/api_runner.py"

    def _written_fields(self):
        """Every record field any writer sets, by the file that sets it."""
        import ast
        found = {}
        runner = Path(self.ATTRIBUTE_WRITE_FILE)
        if runner.exists():
            for field in self.ATTRIBUTE_WRITE.findall(
                    runner.read_text(encoding="utf-8")):
                found.setdefault(field, self.ATTRIBUTE_WRITE_FILE)
        for name, functions in self.WRITERS.items():
            path = Path(name)
            if not path.exists():
                continue
            for fn in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                locals_ = functions.get(fn.name)
                if not locals_:
                    continue
                for node in ast.walk(fn):
                    # `data.update({...})` / `data.setdefault("x", …)`. Both are
                    # in use on record dicts today (`api_runner:2417`,
                    # `provenance:542`) and the first version of this scan saw
                    # neither, so a field introduced by either was unguarded
                    # while the docstring claimed full coverage (#620).
                    if (isinstance(node, ast.Call)
                            and isinstance(node.func, ast.Attribute)
                            and isinstance(node.func.value, ast.Name)
                            and node.func.value.id in locals_):
                        if node.func.attr == "setdefault" and node.args and \
                                isinstance(node.args[0], ast.Constant) and \
                                isinstance(node.args[0].value, str):
                            found.setdefault(node.args[0].value, name)
                        if node.func.attr == "update":
                            for arg in node.args:
                                if isinstance(arg, ast.Dict):
                                    for key in arg.keys:
                                        if isinstance(key, ast.Constant) and \
                                                isinstance(key.value, str):
                                            found.setdefault(key.value, name)
                            for kw in node.keywords:
                                if kw.arg:
                                    found.setdefault(kw.arg, name)

                    targets = []
                    if isinstance(node, ast.Assign):
                        targets = list(node.targets)
                    elif isinstance(node, ast.AnnAssign):
                        targets = [node.target]
                    for target in targets:
                        # `data = {...}` — the builders' dict literals. Also
                        # covers `data = {**other, "x": …}`: an unpacking has a
                        # None key, which the isinstance check skips, while the
                        # literal keys beside it are still collected.
                        if (isinstance(target, ast.Name)
                                and target.id in locals_
                                and isinstance(node.value, ast.Dict)):
                            for key in node.value.keys:
                                if isinstance(key, ast.Constant) and \
                                        isinstance(key.value, str):
                                    found.setdefault(key.value, name)
                        # `data["x"] = …` — cli/runs.py's idiom.
                        if (isinstance(target, ast.Subscript)
                                and isinstance(target.value, ast.Name)
                                and target.value.id in locals_
                                and isinstance(target.slice, ast.Constant)
                                and isinstance(target.slice.value, str)):
                            found.setdefault(target.slice.value, name)
        return found

    def test_the_blocks_a_backfill_writes_are_all_declared(self):
        """`backfill_checks.apply` writes `record[name] for name in BLOCKS`.

        The key is a loop variable, so no AST scan of the assignment can name
        it — the field list lives in a module constant instead. Adding a fifth
        entry to `BLOCKS` would make all 195 records non-conforming, and
        nothing else would notice (#620).
        """
        if not SCHEMA.exists():
            self.skipTest("schema not present in this checkout")
        from data_sheets_schema.backfill_checks import BLOCKS
        schema = yaml.safe_load(SCHEMA.read_text(encoding="utf-8"))
        known = set(schema["classes"]["GenerationRecord"]["attributes"])
        self.assertEqual(sorted(set(BLOCKS) - known), [],
                         "backfill_checks.BLOCKS names a field the schema does "
                         "not declare; applying it would break every record")

    def test_every_named_writer_function_still_exists(self):
        """A renamed function would silently drop out of the scan."""
        import ast
        for name, functions in self.WRITERS.items():
            path = Path(name)
            if not path.exists():
                continue
            present = {fn.name for fn in ast.walk(
                ast.parse(path.read_text(encoding="utf-8")))
                if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef))}
            for fn_name in functions:
                with self.subTest(function=f"{name}:{fn_name}"):
                    self.assertIn(fn_name, present,
                                  "the scan names a function that no longer "
                                  "exists, so its fields are unguarded")

    def test_no_writer_sets_a_field_the_schema_forbids(self):
        if not SCHEMA.exists():
            self.skipTest("schema not present in this checkout")
        schema = yaml.safe_load(SCHEMA.read_text(encoding="utf-8"))
        known = set(schema["classes"]["GenerationRecord"]["attributes"])
        unknown = {f: w for f, w in self._written_fields().items()
                   if f not in known}
        self.assertEqual(
            unknown, {},
            "these fields are written into a generation record but the schema "
            "does not declare them, so — `additionalProperties` being false — "
            f"a run taking that branch fails the conformance gate: {unknown}")

    def test_the_scan_sees_both_builders_and_not_just_one_idiom(self):
        """Otherwise the test above passes by finding nothing to check.

        The previous version asserted only that `"validation"` was found, which
        a single `rec.data["validation"]` match satisfied while 20 fields stayed
        invisible. These three come from three different writers and three
        different idioms, so losing any one of them empties part of the scan
        and fails here rather than silently narrowing the guard.
        """
        if not any(Path(w).exists() for w in self.WRITERS):
            self.skipTest("writers not present in this checkout")
        found = self._written_fields()
        for field, why in (
                ("validation", "rec.data[...] in api_runner.execute"),
                ("companions", "the build_record dict literal"),
                ("derivation", "the build_derived_record dict literal"),
                ("canonical", "a data[...] assignment in cli/runs.py")):
            with self.subTest(field=field):
                self.assertIn(field, found,
                              f"the scan no longer sees {why}; the guard has "
                              f"narrowed. Found: {sorted(found)}")


if __name__ == "__main__":
    unittest.main()

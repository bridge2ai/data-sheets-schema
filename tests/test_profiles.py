"""Study text and vocabularies sit behind a profile (#628, #1302).

The study profile renders the vocabulary its runs have always seen; the
neutral profile renders only what the schema itself declares; and what the
model is *sent* — the assembled full-phase request — is what is asserted,
not a helper.
"""
from __future__ import annotations

import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

ROOT = Path(__file__).resolve().parents[1]
STUDY_MANIFEST = ROOT / "data/preprocessed/source_manifest.yaml"


class _Clean(unittest.TestCase):
    def setUp(self):
        from data_sheets_schema import schema_digest
        self._cwd = os.getcwd(); os.chdir(ROOT)
        schema_digest._TEXT_CACHE.clear()
        self._env = mock.patch.dict(os.environ, {}, clear=False)
        self._env.start()
        os.environ.pop("D4D_PROFILE", None)

    def tearDown(self):
        from data_sheets_schema import schema_digest
        schema_digest._TEXT_CACHE.clear()
        self._env.stop(); os.chdir(self._cwd)


class TestSelection(_Clean):
    def test_the_study_manifest_declares_its_profile(self):
        from data_sheets_schema.profiles import active_profile, declared_profile
        self.assertEqual(declared_profile(STUDY_MANIFEST), "bridge2ai")
        self.assertEqual(active_profile().name, "bridge2ai")          # the default registry
        self.assertEqual(active_profile(STUDY_MANIFEST).name, "bridge2ai")

    def test_a_manifest_without_a_profile_is_neutral_and_so_is_none(self):
        from data_sheets_schema.profiles import active_profile
        with tempfile.TemporaryDirectory() as d:
            m = Path(d) / "m.yaml"
            m.write_text(yaml.safe_dump({"projects": {"X": []}}), encoding="utf-8")
            self.assertEqual(active_profile(m).name, "neutral")
        self.assertEqual(active_profile(None).name, "neutral")

    def test_the_environment_overrides(self):
        from data_sheets_schema.profiles import active_profile
        os.environ["D4D_PROFILE"] = "neutral"
        self.assertEqual(active_profile(STUDY_MANIFEST).name, "neutral")
        os.environ["D4D_PROFILE"] = "nope"
        with self.assertRaises(ValueError):
            active_profile()

    def test_the_study_facts_are_the_profiles_read_when_asked(self):
        """The agreement default, the healthsheet input and the arm scope are
        the *active* profile's, resolved at call time (#1444): the study's
        under `bridge2ai`, none under `neutral`."""
        from data_sheets_schema import agreement, healthsheet
        from data_sheets_schema.constants.methods import GENERATION_ARMS
        from data_sheets_schema.profiles import BRIDGE2AI, NEUTRAL, arm_projects_for
        self.assertEqual(agreement.default_projects(), ("AI_READI", "CHORUS", "CM4AI", "VOICE"))
        self.assertEqual(healthsheet.bundle_name(), "AI_READI_healthsheet_only.txt")
        self.assertEqual(healthsheet.default_record(), BRIDGE2AI.healthsheet_record)
        os.environ["D4D_PROFILE"] = "neutral"
        self.assertEqual(agreement.default_projects(), ())
        self.assertIsNone(healthsheet.bundle_name())
        self.assertIsNone(healthsheet.default_record())
        with self.assertRaises(FileNotFoundError):
            healthsheet.load_healthsheet(None)
        with self.assertRaises(ValueError):
            agreement.build_matrix(projects=None, offline=True)
        # The arm table declares the arms; the profile says which datasets.
        self.assertFalse(any("projects" in arm for arm in GENERATION_ARMS.values()))
        self.assertTrue(set(BRIDGE2AI.arm_projects) <= set(GENERATION_ARMS))
        self.assertEqual(arm_projects_for("crate_only", BRIDGE2AI), ["CHORUS", "CM4AI", "VOICE"])
        self.assertIsNone(arm_projects_for("crate_only", NEUTRAL))

    def test_a_manifest_declaring_neutral_or_an_unknown_profile(self):
        """The manifest's own `profile:` key, not only the environment (#1447)."""
        from data_sheets_schema.profiles import active_profile, select_profile
        with tempfile.TemporaryDirectory() as d:
            m = Path(d) / "m.yaml"
            m.write_text(yaml.safe_dump({"profile": "neutral", "projects": {"X": []}}), encoding="utf-8")
            sel = select_profile(m)
            self.assertEqual(sel.name, "neutral")
            self.assertRegex(sel.basis, rf"^manifest:{re.escape(m.as_posix())}@[0-9a-f]{{12}}$")
            m.write_text(yaml.safe_dump({"profile": "acme", "projects": {"X": []}}), encoding="utf-8")
            from data_sheets_schema import schema_cache
            schema_cache.clear()
            with self.assertRaises(ValueError) as caught:
                active_profile(m)
            self.assertIn("bridge2ai", str(caught.exception))
            self.assertIn("neutral", str(caught.exception))

    def test_the_selection_says_why(self):
        """`environment`, `manifest:<path>`, `default manifest:<path>`, or
        `no manifest` — what the record states (#1443)."""
        from data_sheets_schema.profiles import select_profile
        self.assertEqual(select_profile(None).basis, "no manifest")
        # Repository-relative and content-stamped, so one string names one
        # manifest and no local path reaches a record (#1466).
        self.assertRegex(select_profile(STUDY_MANIFEST).basis,
                         r"^manifest:data/preprocessed/source_manifest\.yaml@[0-9a-f]{12}$")
        self.assertTrue(select_profile().basis.startswith("default manifest:"))
        os.environ["D4D_PROFILE"] = "neutral"
        self.assertEqual(select_profile(STUDY_MANIFEST).basis, "environment")

    def test_the_default_manifest_does_not_follow_the_working_directory(self):
        """From `tests/` in the study's checkout, and from a directory that is
        no checkout at all, a caller that selected nothing still gets the
        study's manifest — the checkout's — rather than a silent neutral
        (#1439)."""
        from data_sheets_schema import schema_digest
        from data_sheets_schema.profiles import select_profile
        here = select_profile()
        self.assertEqual(here.name, "bridge2ai")
        study = schema_digest.fingerprint(schema_digest.digest_text("Dataset"))
        for elsewhere in (ROOT / "tests", Path(tempfile.gettempdir())):
            os.chdir(elsewhere)
            sel = select_profile()
            self.assertEqual(sel.name, "bridge2ai", elsewhere)
            self.assertRegex(sel.basis, r"^default manifest:data/preprocessed/source_manifest\.yaml@[0-9a-f]{12}$")
            schema_digest._TEXT_CACHE.clear()
            self.assertEqual(schema_digest.fingerprint(schema_digest.digest_text("Dataset")), study)
        os.chdir(ROOT)

    def test_an_explicit_profile_overrides_the_ambient_one(self):
        """A run passes the profile it resolved; the digest does not consult
        the environment or the default manifest then (#1438)."""
        from data_sheets_schema import schema_digest
        from data_sheets_schema.profiles import BRIDGE2AI, NEUTRAL
        study = schema_digest.fingerprint(schema_digest.digest_text("Dataset", profile=BRIDGE2AI))
        neutral = schema_digest.fingerprint(schema_digest.digest_text("Dataset", profile=NEUTRAL))
        self.assertNotEqual(study, neutral)
        os.environ["D4D_PROFILE"] = "neutral"
        self.assertEqual(schema_digest.fingerprint(schema_digest.digest_text("Dataset", profile=BRIDGE2AI)), study)
        self.assertEqual(schema_digest.fingerprint(schema_digest.digest_text("Dataset")), neutral)


class TestTheDigest(_Clean):
    def test_the_study_digest_renders_the_schema_scope_and_the_pinned_list(self):
        from data_sheets_schema import schema_digest
        text = schema_digest.digest_text("Dataset")
        line = next(l for l in text.splitlines() if "`data_topic` draws from" in l)
        self.assertIn("GO, MeSH, EFO, NCIT", line)          # the schema's scope (#1302)
        self.assertIn("B2AI_TOPIC (use `B2AI_TOPIC:<id>`)", line)   # the study's pin (#538)
        self.assertIn("Diabetes", line)
        self.assertIn("omit the slot rather than approximate", line)

    def test_the_neutral_digest_renders_only_the_schema_scope(self):
        from data_sheets_schema import schema_digest
        os.environ["D4D_PROFILE"] = "neutral"
        text = schema_digest.digest_text("Dataset")
        line = next(l for l in text.splitlines() if "`data_topic` draws from" in l)
        self.assertIn("GO, MeSH, EFO, NCIT", line)
        self.assertNotIn("B2AI_TOPIC", line)
        self.assertNotIn("Diabetes", line)
        # And no substrate list at all: the schema declares no sources there.
        self.assertFalse(any("`data_substrate` draws from" in l for l in text.splitlines()))
        self.assertNotIn("B2AI", text)

    def test_the_two_profiles_are_different_instruments(self):
        from data_sheets_schema import schema_digest
        study = schema_digest.fingerprint(schema_digest.digest_text("Dataset"))
        schema_digest._TEXT_CACHE.clear()
        os.environ["D4D_PROFILE"] = "neutral"
        neutral = schema_digest.fingerprint(schema_digest.digest_text("Dataset"))
        self.assertNotEqual(study, neutral)

    def test_render_values_from_without_a_pin(self):
        from data_sheets_schema.schema_digest import render_values_from
        self.assertIsNone(render_values_from([], vocabulary={}, term_sources=None))
        out = render_values_from(["B2AI_TOPIC"], vocabulary={}, term_sources="GO, MeSH")
        self.assertIn("a term from GO, MeSH", out)
        self.assertNotIn("B2AI_TOPIC", out)


class TestTheAssembledRequest(_Clean):
    """#1302 acceptance 4: the instruction actually sent carries a
    non-B2AI ontology scope, under both profiles."""

    def _full_phase_text(self):
        from data_sheets_schema.api_runner import RunSpec, build_phase
        spec = RunSpec(project="CHORUS", arm="BASELINE (input documents only)",
                       method="claudecode_api",
                       bundle=Path("data/preprocessed/concatenated/CHORUS_preprocessed.txt"),
                       label="2026-09-13_x_rep1", condition="generic_v9")
        return "\n".join(b["text"] for b in build_phase(spec, "full", carry={}).cached_blocks)

    def test_a_mesh_term_is_in_range_under_the_study_profile(self):
        sent = self._full_phase_text()
        self.assertIn("GO, MeSH, EFO, NCIT", sent)
        self.assertIn("B2AI_TOPIC", sent)

    def test_the_neutral_request_carries_no_study_vocabulary(self):
        os.environ["D4D_PROFILE"] = "neutral"
        sent = self._full_phase_text()
        self.assertIn("GO, MeSH, EFO, NCIT", sent)
        self.assertNotIn("B2AI_TOPIC", sent)
        self.assertNotIn("B2AI_SUBSTRATE", sent)


class TestTheJudge(_Clean):
    """The fitness judge is told what the model was told (#1440)."""

    def test_the_judge_names_the_schema_scope_under_both_profiles(self):
        from data_sheets_schema import evidence_score, schema_digest
        study = evidence_score.slot_spec("instances")
        self.assertIn("MeSH", study)
        self.assertIn("B2AI_TOPIC", study)
        os.environ["D4D_PROFILE"] = "neutral"
        schema_digest._TEXT_CACHE.clear()
        neutral = evidence_score.slot_spec("instances")
        self.assertIn("MeSH", neutral)
        self.assertIn("data_topic", neutral)
        self.assertNotIn("B2AI_TOPIC", neutral)
        self.assertNotIn("B2AI", neutral)


class TestTheLedger(_Clean):
    def test_both_digests_are_in_the_inventory(self):
        """A neutral run's `slot_existed_at` lookup must answer, not return
        None (#1441)."""
        from data_sheets_schema import schema_digest
        from data_sheets_schema.profiles import BRIDGE2AI, NEUTRAL
        for prof in (BRIDGE2AI, NEUTRAL):
            md5 = schema_digest.fingerprint(schema_digest.digest_text("Dataset", profile=prof))
            self.assertIs(schema_digest.slot_existed_at(md5, "Dataset", "instances"), True, prof.name)
            self.assertIs(schema_digest.slot_existed_at(md5, "CoreDataset", "title"), True, prof.name)


class TestTheRecord(_Clean):
    """A run resolves its profile once from the manifest it selected and the
    record states the profile and why (#1438, #1443)."""

    def test_a_study_run_and_an_external_run_resolve_differently(self):
        from data_sheets_schema.api_runner import RunSpec
        study = RunSpec(project="CHORUS", arm="x", method="claudecode_api", label="L",
                        bundle=ROOT / "data/preprocessed/concatenated/CHORUS_preprocessed.txt",
                        condition="generic_v9")
        self.assertEqual(study.profile, "bridge2ai")
        self.assertRegex(study.profile_basis, r"^manifest:data/preprocessed/source_manifest\.yaml@[0-9a-f]{12}$")
        with tempfile.TemporaryDirectory() as d:
            ext = Path(d) / "clinic_preprocessed.txt"; ext.write_text("FILE: a\nhi\n", encoding="utf-8")
            external = RunSpec(project="CLINIC", arm="x", method="claudecode_api", label="L",
                               bundle=ext, condition="generic_v9")
        self.assertEqual((external.profile, external.profile_basis), ("neutral", "no manifest"))
        os.environ["D4D_PROFILE"] = "neutral"
        forced = RunSpec(project="CHORUS", arm="x", method="claudecode_api", label="L",
                         bundle=ROOT / "data/preprocessed/concatenated/CHORUS_preprocessed.txt",
                         condition="generic_v9")
        self.assertEqual((forced.profile, forced.profile_basis), ("neutral", "environment"))

    def test_the_record_carries_the_profile_and_validates(self):
        from data_sheets_schema import schema_digest
        from data_sheets_schema.provenance import build_record, check_record
        from data_sheets_schema.profiles import NEUTRAL, Selection
        with tempfile.TemporaryDirectory() as d:
            full = Path(d) / "P_d4d.yaml"
            full.write_text("# Generated: 2026-09-13\nid: https://example.org/p\ntitle: P\n", encoding="utf-8")
            sel = Selection(NEUTRAL, "no manifest")
            rec = build_record("P", "claudecode_api", "L", mode="live", input_bundle=full,
                               input_verified=True, outputs={"full": full},
                               schema_digest_md5=schema_digest.fingerprint(
                                   schema_digest.digest_text("Dataset", profile=NEUTRAL)),
                               profile=sel)
            block = rec.data["schema"]
            self.assertEqual(block["profile"], "neutral")
            self.assertEqual(block["profile_basis"], "no manifest")
            self.assertEqual(block["digest_md5"], "029c2abcda26e45c4465fd0a8455893d")
            violations, why = check_record(rec.data)
            self.assertIsNone(why, why)
            self.assertEqual([v for v in violations if "profile" in v], [])

    def test_the_plan_says_which_profile(self):
        """`d4d api plan` names the profile, so a neutral fallback is visible
        before any spend (#1439)."""
        from data_sheets_schema.api_runner import RunSpec, plan
        spec = RunSpec(project="CHORUS", arm="x", method="claudecode_api", label="L",
                       bundle=ROOT / "data/preprocessed/concatenated/CHORUS_preprocessed.txt",
                       condition="generic_v9")
        out = plan(spec)
        self.assertEqual(out["profile"], "bridge2ai")
        self.assertEqual(out["schema_digest_md5"], "cd3c79f2c62f11675d5ce2c1df96b88e")


class TestTheThreadingHolds(_Clean):
    """The round-2 review showed the round-1 tests passed with the profile
    argument discarded (#1470): every case here resolves one profile on the
    spec and changes the environment before looking."""

    STUDY = "cd3c79f2c62f11675d5ce2c1df96b88e"
    NEUTRAL = "029c2abcda26e45c4465fd0a8455893d"

    def _study_spec(self, **kw):
        from data_sheets_schema.api_runner import RunSpec
        return RunSpec(project="CHORUS", arm="BASELINE (input documents only)", method="claudecode_api",
                       label="2026-09-13_x-api-generic-v9_rep1", condition="generic_v9", run_date="2026-09-13",
                       bundle=ROOT / "data/preprocessed/concatenated/CHORUS_preprocessed.txt", **kw)

    def test_every_request_of_a_run_follows_the_spec_not_the_environment(self):
        from data_sheets_schema import api_runner, schema_digest
        spec = self._study_spec()
        self.assertEqual(spec.profile, "bridge2ai")
        os.environ["D4D_PROFILE"] = "neutral"
        schema_digest._TEXT_CACHE.clear()
        full = api_runner.build_phase(spec, "full", carry={})
        self.assertEqual(schema_digest.fingerprint(full.cached_blocks[0]["text"]), self.STUDY)
        repair = api_runner.build_repair("full", "id: https://example.org/x\n", ["e"], profile=spec.profile_obj)
        self.assertEqual(schema_digest.fingerprint(repair.cached_blocks[0]["text"]), self.STUDY)
        self.assertEqual(api_runner.plan(spec)["schema_digest_md5"], self.STUDY)
        self.assertEqual(spec.input_identity()["profile"], {"name": "bridge2ai", "digest_md5": self.STUDY})
        # And the ambient one really is the other instrument now.
        self.assertEqual(schema_digest.fingerprint(schema_digest.digest_text("Dataset")), self.NEUTRAL)

    def test_a_resume_under_another_profile_is_refused(self):
        """#1460: the instrument is an input; a record made under one profile
        is not continued under another."""
        from data_sheets_schema import api_runner, schema_digest, usage_ledger
        first = self._study_spec()
        identity = first.input_identity()
        record = {"inputs": {"bundle_path": identity["bundle"]["path"], "bundle_sha256": identity["bundle"]["sha256"],
                             "source_manifest": identity["source_manifest"], "chunks": identity["chunks"]},
                  "schema": {"digest_md5": self.STUDY, "profile": "bridge2ai"},
                  "prompts": {"request": {"sha256": identity["instruction"]["sha256"]}}}
        api_runner._require_recorded_inputs(first, record)          # same instrument: allowed
        os.environ["D4D_PROFILE"] = "neutral"
        schema_digest._TEXT_CACHE.clear()
        resumed = self._study_spec()
        self.assertEqual(resumed.profile, "neutral")
        with self.assertRaises(usage_ledger.UsageLedgerError) as caught:
            api_runner._require_recorded_inputs(resumed, record)
        self.assertIn("instrument", str(caught.exception))
        self.assertTrue(usage_ledger._identity_differs(identity, resumed.input_identity()))
        # A pin made before the key existed says nothing about it.
        older = {k: v for k, v in identity.items() if k != "profile"}
        self.assertFalse(usage_ledger._identity_differs(older, first.input_identity()))

    def test_the_rendered_recording_command_names_the_selected_manifest(self):
        """#1461: an arm whose header declares the manifest's context unused
        still selected it, and the recorder selects the profile from it."""
        from data_sheets_schema.api_runner import RunSpec, resolve_prompt
        from data_sheets_schema.cli.api import ARMS
        crate = RunSpec(project="CHORUS", arm=ARMS["crate_only"][0], method=ARMS["crate_only"][1],
                        label="2026-09-13_x-claudecode-generic-v9_rep1", condition="generic_v9",
                        runtime="Claude Code", run_date="2026-09-13",
                        bundle=ROOT / "data/preprocessed/concatenated/CHORUS_crate_only.txt",
                        manifest=STUDY_MANIFEST, manifest_line=ARMS["crate_only"][3])
        self.assertEqual((crate.profile, crate.manifest_used), ("bridge2ai", False))
        line = next(l for l in resolve_prompt(crate).splitlines() if "d4d provenance record" in l)
        self.assertIn(f"--manifest {STUDY_MANIFEST}", line)
        self.assertNotIn("--manifest none", line)
        with tempfile.TemporaryDirectory() as d:
            ext = Path(d) / "clinic_preprocessed.txt"; ext.write_text("FILE: a\nhi\n", encoding="utf-8")
            external = RunSpec(project="CLINIC", arm=ARMS["baseline"][0], method=ARMS["baseline"][1],
                               label="2026-09-13_x-claudecode-generic-v9_rep1", condition="generic_v9",
                               runtime="Claude Code", run_date="2026-09-13", bundle=ext)
            line = next(l for l in resolve_prompt(external).splitlines() if "d4d provenance record" in l)
        self.assertIn("--manifest none", line)

    def test_replay_never_consults_the_environment(self):
        """#1468: verifying a historical instruction must not fail on an
        irrelevant current setting."""
        from data_sheets_schema.api_runner import RunSpec
        os.environ["D4D_PROFILE"] = "invalid-profile"
        replay = RunSpec.from_render_spec({"condition": "generic"}, project="P", method="claudecode_api", label="L")
        self.assertIsNone(replay.profile)
        self.assertIsNone(replay.profile_obj)

    def test_readers_of_a_record_use_the_records_profile(self):
        """#1462: the judge, the review pack's labels and the pair backfill
        read the profile the record states, not the environment."""
        from data_sheets_schema import evidence_score, schema_digest
        from data_sheets_schema.d4d_pair_consistency import pair_predates_current_schema
        from data_sheets_schema.profiles import BRIDGE2AI, NEUTRAL, for_record
        self.assertIs(for_record({"schema": {"profile": "neutral"}}), NEUTRAL)
        self.assertIs(for_record({"schema": {"digest_md5": "x"}}), BRIDGE2AI)      # pre-profile: the ambient one
        self.assertNotIn("B2AI_TOPIC", evidence_score.slot_spec("instances", profile=NEUTRAL))
        self.assertIn("MeSH", evidence_score.slot_spec("instances", profile=NEUTRAL))
        judge = evidence_score.LLMSlotFitnessScorer(client=object(), model="offline-test", profile=NEUTRAL)
        self.assertEqual(judge._context("offline-test").schema, self.NEUTRAL)
        with tempfile.TemporaryDirectory() as d:
            core = Path(d) / "P_d4d_core.yaml"; core.write_text("id: x\n", encoding="utf-8")
            (Path(d) / "P_provenance.yaml").write_text(
                yaml.safe_dump({"schema": {"digest_md5": self.NEUTRAL, "profile": "neutral"}}), encoding="utf-8")
            self.assertFalse(pair_predates_current_schema(core))         # ambient is bridge2ai; the record is not
            (Path(d) / "P_provenance.yaml").write_text(
                yaml.safe_dump({"schema": {"digest_md5": self.STUDY, "profile": "bridge2ai"}}), encoding="utf-8")
            self.assertFalse(pair_predates_current_schema(core))

    def test_the_sync_gate_is_keyed_on_the_profile(self):
        """#1463: the rebuilt digest is cached per profile, so a profile
        switch cannot classify an unchanged schema as stale."""
        from data_sheets_schema import schema_sync
        from data_sheets_schema.profiles import BRIDGE2AI, NEUTRAL
        study = {r["class"]: r for r in schema_sync.check(profile=BRIDGE2AI)}
        neutral = {r["class"]: r for r in schema_sync.check(profile=NEUTRAL)}
        for cls in ("Dataset", "CoreDataset"):
            self.assertEqual(study[cls]["status"], schema_sync.IN_SYNC, study[cls])
            self.assertEqual(neutral[cls]["status"], schema_sync.IN_SYNC, neutral[cls])
        self.assertEqual(study["Dataset"]["digest"], self.STUDY)
        self.assertEqual(neutral["Dataset"]["digest"], self.NEUTRAL)

    def test_the_healthsheet_bundle_names_its_own_dataset(self):
        """#1464: no literal project identity in the model's source bundle."""
        from data_sheets_schema.healthsheet import render
        text, _ = render({"cohort": [{"question": "Population?", "response": "Clinic participants"}]},
                         {"title": "Independent Clinic"}, Path("CLINIC.json"), project="CLINIC")
        self.assertIn("Project: CLINIC", text)
        self.assertIn("It is NOT the\nCLINIC baseline", text)
        self.assertNotIn("AI_READI", text); self.assertNotIn("AI-READI", text)
        text, _ = render({}, {"title": "t"}, Path("x.json"))                     # study default
        self.assertIn("Project: AI_READI", text)
        os.environ["D4D_PROFILE"] = "neutral"
        with self.assertRaises(ValueError):
            render({}, {"title": "t"}, Path("x.json"))

    def test_the_ledger_carries_the_whole_inventory_for_both_profiles(self):
        from data_sheets_schema import schema_digest
        from data_sheets_schema.profiles import BRIDGE2AI, NEUTRAL
        for prof in (BRIDGE2AI, NEUTRAL):
            md5 = schema_digest.fingerprint(schema_digest.digest_text("Dataset", profile=prof))
            for cls in ("Dataset", "CoreDataset"):
                for slot in schema_digest.slot_names(cls):
                    self.assertIs(schema_digest.slot_existed_at(md5, cls, slot), True, (prof.name, cls, slot))


class TestRoundThree(_Clean):
    """The Claude round-2 residuals (#1491–#1498)."""

    def test_one_default_manifest_rule(self):
        """#1491: the profile's default is the registry's default."""
        from data_sheets_schema import profiles, registry
        self.assertEqual(profiles.default_manifest(), registry.default_manifest_path())
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); man = root / "data/preprocessed/source_manifest.yaml"; man.parent.mkdir(parents=True)
            man.write_text(yaml.safe_dump({"profile": "neutral", "projects": {"X": [{"id": "s", "source": "s"}]}}), encoding="utf-8")
            sub = root / "work" / "deeper"; sub.mkdir(parents=True)
            os.chdir(sub)
            self.assertEqual(registry.default_manifest_path().resolve(), man.resolve())
            self.assertEqual(profiles.default_manifest().resolve(), man.resolve())
            self.assertEqual(profiles.select_profile().name, "neutral")
            os.chdir(ROOT)

    def test_the_basis_says_undeclared_and_missing(self):
        """#1494"""
        from data_sheets_schema.profiles import select_profile
        with tempfile.TemporaryDirectory() as d:
            m = Path(d) / "m.yaml"
            m.write_text(yaml.safe_dump({"projects": {"X": []}}), encoding="utf-8")
            sel = select_profile(m)
            self.assertEqual(sel.name, "neutral")
            self.assertRegex(sel.basis, r"@[0-9a-f]{12} \(undeclared\)$")
            m.write_text(yaml.safe_dump({"profile": "neutral", "projects": {"X": []}}), encoding="utf-8")
            from data_sheets_schema import schema_cache
            schema_cache.clear()
            self.assertRegex(select_profile(m).basis, r"@[0-9a-f]{12}$")
            gone = select_profile(Path(d) / "nope.yaml")
            self.assertEqual(gone.name, "neutral")
            self.assertTrue(gone.basis.endswith("nope.yaml (missing)"), gone.basis)

    def test_the_plan_prints_the_profile_in_text_mode(self):
        """#1492"""
        from click.testing import CliRunner
        from data_sheets_schema.cli import cli
        r = CliRunner().invoke(cli, ["api", "plan", "--project", "CHORUS", "--label", "2026-09-13_x-api-generic-v9_rep1",
                                     "--condition", "generic_v9"])
        self.assertEqual(r.exit_code, 0, r.output)
        self.assertRegex(r.output, r"profile  bridge2ai  \(manifest:data/preprocessed/source_manifest\.yaml@[0-9a-f]{12}\)")

    def test_agreement_main_reports_a_missing_default_instead_of_a_traceback(self):
        """#1495"""
        import contextlib, io
        from data_sheets_schema import agreement
        os.environ["D4D_PROFILE"] = "neutral"
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = agreement.main(["--offline"])
        self.assertEqual(code, 2)
        self.assertIn("names none", err.getvalue())

    def test_form_defects_takes_the_records_profile(self):
        """#1496"""
        from data_sheets_schema.form_defects import FormSubtypeClassifier
        from data_sheets_schema.profiles import NEUTRAL
        self.assertEqual(FormSubtypeClassifier(profile=NEUTRAL)._default_schema(), "029c2abcda26e45c4465fd0a8455893d")
        self.assertEqual(FormSubtypeClassifier()._default_schema(), "cd3c79f2c62f11675d5ce2c1df96b88e")

    def test_the_recorder_selects_the_profile_from_a_manifest_the_header_declares_unused(self):
        """#1461 at the recorder itself (#1497): the crate-only arm's header
        says the manifest's context was not used; the manifest was still
        selected and its profile decides the digest."""
        import click.testing
        from data_sheets_schema.cli import provenance as prov_cli
        method, label = "claudecode_agent_crate_only", "2026-09-13_test-crate_rep1"
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "src/data_sheets_schema").mkdir(parents=True)          # the recorder's root marker
            full_dir = root / "data/d4d_concatenated" / method / label
            core_dir = root / "data/d4d_concatenated" / f"{method}_core" / label
            full_dir.mkdir(parents=True); core_dir.mkdir(parents=True)
            man = root / "data/preprocessed/source_manifest.yaml"; man.parent.mkdir(parents=True)
            man.write_text(yaml.safe_dump({"profile": "bridge2ai",
                                           "projects": {"CHORUS": [{"id": "s", "source": "s", "title": "s"}]}}), encoding="utf-8")
            bundle = root / "data/preprocessed/concatenated/CHORUS_crate_only.txt"
            bundle.parent.mkdir(parents=True, exist_ok=True); bundle.write_text("crate\n", encoding="utf-8")
            body = ("# Generated: 2026-09-13\n# Source manifest: not used (crate-only arm; single declared source bundle)\n"
                    "id: https://example.org/x\nname: x\n")
            (full_dir / "CHORUS_d4d.yaml").write_text(body, encoding="utf-8")
            (core_dir / "CHORUS_d4d_core.yaml").write_text(body, encoding="utf-8")
            (core_dir / "CHORUS_reconciliation.md").write_text("# r\n", encoding="utf-8")
            os.chdir(root)
            try:
                r = click.testing.CliRunner().invoke(prov_cli.provenance, [
                    "record", "--project", "CHORUS", "--method", method, "--label", label, "--arm", "crate_only",
                    "--input-bundle", str(bundle), "--manifest", "data/preprocessed/source_manifest.yaml",
                    "--phase", "generate_full"])
            finally:
                os.chdir(ROOT)
            self.assertEqual(r.exit_code, 0, r.output)
            rec = yaml.safe_load((core_dir / "CHORUS_provenance.yaml").read_text(encoding="utf-8"))
        self.assertEqual(rec["schema"]["profile"], "bridge2ai")
        self.assertRegex(rec["schema"]["profile_basis"], r"^manifest:data/preprocessed/source_manifest\.yaml@[0-9a-f]{12}$")
        self.assertEqual(rec["schema"]["digest_md5"], "cd3c79f2c62f11675d5ce2c1df96b88e")
        attested = (rec.get("inputs") or {}).get("source_manifest") or {}
        self.assertIsNone(attested.get("path"))                      # not consumed as context …
        self.assertIn("unused", attested.get("basis", ""))           # … and the record says why

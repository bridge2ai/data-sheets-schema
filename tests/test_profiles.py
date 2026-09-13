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
        older = {k: v for k, v in identity.items() if k != "profile"}      # the subset rule, not a real pre-profile pin (#1628)
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
            os.chdir(root)
            self.assertEqual(registry.default_manifest_path().resolve(), man.resolve())
            self.assertEqual(profiles.default_manifest().resolve(), man.resolve())
            self.assertEqual(profiles.select_profile().name, "neutral")
            # Not from a subdirectory: the corpus root is anchored to the
            # checkout, so an ancestor's manifest is not discovered until the
            # corpus root follows the manifest (#1515, #1523).
            sub = root / "work" / "deeper"; sub.mkdir(parents=True)
            os.chdir(sub)
            self.assertEqual(registry.default_manifest_path().resolve(), STUDY_MANIFEST.resolve())
            self.assertEqual(profiles.select_profile().name, "bridge2ai")
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
            # A scratch tree cannot exercise the automatic rule: the conventional
            # bundles are anchored to the checkout (#1523), so only an explicit
            # manifest selects here; the automatic case is the next test.
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

    def test_the_recorder_with_no_manifest_option_follows_the_runners_rule(self):
        """#1512: from the checkout, on a tracked crate-only output whose
        header declares the manifest unused, no `--manifest` at all selects
        the study manifest as the runner would — the write is captured, not
        made."""
        import click.testing
        from unittest import mock
        from data_sheets_schema import provenance as pv
        from data_sheets_schema.cli import provenance as prov_cli
        label = "2026-07-31_claude-opus-5-api-generic_rep2"
        full = ROOT / "data/d4d_concatenated/claudecode_agent_crate_only" / label / "CHORUS_d4d.yaml"
        if not full.exists():
            self.skipTest("the tracked crate-only output is not in this checkout")
        self.assertIn("not used", full.read_text(encoding="utf-8")[:2000].lower())
        captured = {}

        def capture(self_, path):
            captured["data"] = self_.data
            return path
        with mock.patch.object(pv.ProvenanceRecord, "write", capture), \
                mock.patch.object(prov_cli, "_inline_checks", lambda *a, **k: None):
            r = click.testing.CliRunner().invoke(prov_cli.provenance, [
                "record", "--project", "CHORUS", "--method", "claudecode_agent_crate_only", "--label", label,
                "--arm", "crate_only", "--input-bundle", "data/preprocessed/concatenated/CHORUS_crate_only.txt",
                "--phase", "generate_full"])
        self.assertEqual(r.exit_code, 0, r.output)
        rec = captured["data"]
        self.assertEqual(rec["schema"]["profile"], "bridge2ai")
        self.assertRegex(rec["schema"]["profile_basis"], r"^manifest:data/preprocessed/source_manifest\.yaml@[0-9a-f]{12}$")
        attested = (rec.get("inputs") or {}).get("source_manifest") or {}
        self.assertIsNone(attested.get("path"))
        self.assertIn("unused", attested.get("basis", ""))


class TestRoundFour(_Clean):
    """The Codex round-3 findings (#1512–#1522)."""

    STUDY = "cd3c79f2c62f11675d5ce2c1df96b88e"

    def _fake_client(self):
        import sys
        sys.path.insert(0, str(ROOT / "tests" / "test_download"))
        try:
            from test_api_runner import FakeClient
        finally:
            sys.path.pop(0)
        return FakeClient()

    def test_a_repair_round_sends_the_specs_digest(self):
        """#1521: through `_repair_invalid` itself, not `build_repair`."""
        from data_sheets_schema import api_runner, schema_digest
        from data_sheets_schema.api_runner import RunSpec
        with tempfile.TemporaryDirectory() as d:
            spec = RunSpec(project="CHORUS", arm="BASELINE (input documents only)", method="claudecode_api",
                           label="2026-09-13_x-api-generic_rep1", run_date="2026-09-13", out_dir=Path(d),
                           bundle=ROOT / "data/preprocessed/concatenated/CHORUS_preprocessed.txt")
            self.assertEqual(spec.profile, "bridge2ai")
            spec.full_path.parent.mkdir(parents=True, exist_ok=True)
            spec.full_path.write_text("# Generated: 2026-09-13\nid: 123\ntitle: T\n", encoding="utf-8")   # id is not a uriorcurie
            os.environ["D4D_PROFILE"] = "neutral"
            schema_digest._TEXT_CACHE.clear()
            client = self._fake_client()
            api_runner._prepare_usage(spec, resume=False)
            api_runner._repair_invalid(spec, client, api_runner._model_settings(), [])
            repairs = [kw for kw in client.messages.calls if api_runner.REPAIR_INSTRUCTION in
                       " ".join(p.get("text", "") for p in kw["messages"][0]["content"])]
            self.assertTrue(repairs, "no repair request was sent")
            first_block = repairs[0]["messages"][0]["content"][0]["text"]
            self.assertEqual(schema_digest.fingerprint(first_block), self.STUDY)

    def test_the_sync_gate_and_the_record_follow_the_spec_through_execute(self):
        """#1521: through `execute()` itself, with a spy on the gate."""
        from unittest import mock
        from data_sheets_schema import api_runner, schema_digest, schema_sync
        from data_sheets_schema.api_runner import RunSpec
        with tempfile.TemporaryDirectory() as d:
            spec = RunSpec(project="CHORUS", arm="BASELINE (input documents only)", method="claudecode_api",
                           label="2026-09-13_x-api-generic_rep1", run_date="2026-09-13", out_dir=Path(d),
                           bundle=ROOT / "data/preprocessed/concatenated/CHORUS_preprocessed.txt")
            os.environ["D4D_PROFILE"] = "neutral"
            schema_digest._TEXT_CACHE.clear()
            seen = []
            real = schema_sync.check

            def spy(*a, **kw):
                seen.append(kw.get("profile"))
                return real(*a, **kw)
            with mock.patch.object(schema_sync, "check", spy):
                api_runner.execute(spec, client=self._fake_client())
            self.assertEqual([p.name for p in seen if p is not None], ["bridge2ai"])
            rec = yaml.safe_load((Path(d) / "CHORUS_provenance.yaml").read_text(encoding="utf-8"))
            self.assertEqual(rec["schema"]["profile"], "bridge2ai")
            self.assertEqual(rec["schema"]["digest_md5"], self.STUDY)
            self.assertEqual(rec["pair_consistency"].get("schema_moved"), False)

    def test_the_form_classifier_snapshot_is_its_own_instrument(self):
        """#1513: a fresh classifier under the opposite environment does not
        raise on its own snapshot."""
        from data_sheets_schema.form_defects import FormFailure, FormSubtypeClassifier
        from data_sheets_schema.profiles import BRIDGE2AI, NEUTRAL
        os.environ["D4D_PROFILE"] = "bridge2ai"
        c = FormSubtypeClassifier(client=object(), model="offline-test", profile=NEUTRAL)
        self.assertEqual(c.schema, c._live_snapshot()[0])
        os.environ["D4D_PROFILE"] = "neutral"
        c = FormSubtypeClassifier(client=object(), model="offline-test", profile=BRIDGE2AI)
        self.assertEqual(c.schema, c._live_snapshot()[0])
        # #1514: a failure judged under another instrument is refused, not pooled.
        other = FormFailure(project="P", slot="instances", value="[]", reason="wrong kind", fitness=0.0,
                            schema="029c2abcda26e45c4465fd0a8455893d")
        with self.assertRaises(ValueError):
            c(other)

    def test_loading_refuses_failures_from_two_instruments(self):
        """#1514"""
        import json
        from data_sheets_schema.form_defects import load_form_failures
        with tempfile.TemporaryDirectory() as d:
            rows = [{"failure": "form", "rubric": "r", "model": "m", "slot": "instances", "value": "[]",
                     "reason": "x", "fitness": 0.0, "schema": s} for s in (self.STUDY, "029c2abcda26e45c4465fd0a8455893d")]
            (Path(d) / "P_fitness.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
            with self.assertRaises(ValueError) as caught:
                load_form_failures(Path(d))
            self.assertIn("schema", str(caught.exception))
            (Path(d) / "P_fitness.jsonl").write_text(json.dumps(rows[0]) + "\n", encoding="utf-8")
            self.assertEqual(load_form_failures(Path(d))[0].schema, self.STUDY)

    def test_a_pre_profile_record_is_the_studys_whatever_the_environment(self):
        """#1518"""
        from data_sheets_schema.profiles import BRIDGE2AI, NEUTRAL, for_record
        os.environ["D4D_PROFILE"] = "neutral"
        self.assertIs(for_record({"schema": {"digest_md5": "34d24ff30fb6ad0f10d82af09ddc1fba"}}), BRIDGE2AI)
        self.assertIs(for_record({"schema": {}}), BRIDGE2AI)               # no profile at all: before profiles, the study's (#1583)
        self.assertIs(for_record({"schema": "not a mapping"}), BRIDGE2AI)
        import warnings
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            self.assertIs(for_record({"schema": {"profile": "acme"}}), BRIDGE2AI)
        self.assertTrue(any("does not know" in str(w.message) for w in caught))

    def test_own_record_under_another_project_gets_its_own_file(self):
        """#1516"""
        from unittest import mock
        from data_sheets_schema import healthsheet
        from data_sheets_schema.profiles import BRIDGE2AI
        rec = BRIDGE2AI.healthsheet_record
        if not (ROOT / rec).exists():
            self.skipTest("the study's healthsheet record is not in this checkout")
        with tempfile.TemporaryDirectory() as d:
            target, _ = healthsheet.build_bundle(ROOT / rec, Path(d), project="CLINIC")
            self.assertEqual(target.name, "CLINIC_healthsheet_only.txt")
            target, _ = healthsheet.build_bundle(ROOT / rec, Path(d))
            self.assertEqual(target.name, "AI_READI_healthsheet_only.txt")

    def test_legacy_progress_and_continuation(self):
        """#1517: a saved identity without the profile key matches when the
        rest does; #1519: a record with no digest cannot be resumed."""
        from data_sheets_schema import api_runner, usage_ledger
        spec = self._spec()
        identity = spec.input_identity()
        legacy = {k: v for k, v in identity.items() if k != "profile"}     # the subset rule, not a real pre-profile pin (#1628)
        self.assertFalse(usage_ledger._identity_differs(legacy, identity))
        record = {"inputs": {"bundle_path": identity["bundle"]["path"], "bundle_sha256": identity["bundle"]["sha256"],
                             "source_manifest": identity["source_manifest"], "chunks": identity["chunks"]},
                  "schema": {}, "prompts": {"request": {"sha256": identity["instruction"]["sha256"]}}}
        api_runner._require_recorded_inputs(spec, record)             # no digest: no evidence here, no refusal here
        # … the refusal is at continuation: finished phases, no digest in the
        # record, no profile in the pin.
        from unittest import mock
        with tempfile.TemporaryDirectory() as d:
            spec = self._spec(out_dir=Path(d))
            api_runner._prepare_usage(spec, resume=False)
            with mock.patch.object(api_runner, "_load_progress", return_value={"completed": ["full"], "input_identity": legacy,
                                                                                 "generation_id": api_runner._usage_generation(spec)}), \
                    mock.patch.object(usage_ledger, "recorded_inputs", return_value=legacy):
                with self.assertRaises(usage_ledger.UsageLedgerError) as caught:
                    api_runner.execute(spec, resume=True, client=self._fake_client())
            self.assertIn("no instrument identity", str(caught.exception))

    def _spec(self, **kw):
        from data_sheets_schema.api_runner import RunSpec
        return RunSpec(project="CHORUS", arm="BASELINE (input documents only)", method="claudecode_api",
                       label="2026-09-13_x-api-generic-v9_rep1", condition="generic_v9", run_date="2026-09-13",
                       bundle=ROOT / "data/preprocessed/concatenated/CHORUS_preprocessed.txt", **kw)

    def test_neutral_sync_needs_no_pin(self):
        """#1520"""
        from unittest import mock
        from data_sheets_schema import schema_digest, schema_sync
        from data_sheets_schema.profiles import NEUTRAL
        with mock.patch.object(schema_digest, "VOCABULARY_PIN", Path("/nonexistent-round4-vocabulary.yaml")):
            rows = schema_sync.check(profile=NEUTRAL)
        self.assertTrue(all(r["status"] == schema_sync.IN_SYNC for r in rows), rows)


class TestRoundFive(_Clean):
    """The Claude round-3 residuals (#1540–#1549)."""

    def test_the_studys_own_bundle_reproduces_the_tracked_bytes(self):
        """#1542: the profile's record renders what the chunk manifest and 12
        records hash — the display name in prose, the key in the header."""
        from data_sheets_schema import healthsheet
        from data_sheets_schema.profiles import BRIDGE2AI
        rec = ROOT / BRIDGE2AI.healthsheet_record
        tracked = ROOT / "data/preprocessed/concatenated" / BRIDGE2AI.healthsheet_bundle
        if not (rec.exists() and tracked.exists()):
            self.skipTest("the study's healthsheet record or bundle is not in this checkout")
        with tempfile.TemporaryDirectory() as d:
            target, _ = healthsheet.build_bundle(rec, Path(d))
            self.assertEqual(target.name, BRIDGE2AI.healthsheet_bundle)
            got = [l for l in target.read_text(encoding="utf-8").splitlines() if not l.startswith("Source: ")]
        want = [l for l in tracked.read_text(encoding="utf-8").splitlines() if not l.startswith("Source: ")]
        self.assertEqual(got, want)
        # #1544: from another directory, by absolute path, it is still the profile's record.
        os.chdir(ROOT / "tests")
        with tempfile.TemporaryDirectory() as d:
            target, _ = healthsheet.build_bundle(rec, Path(d))
            self.assertEqual(target.name, BRIDGE2AI.healthsheet_bundle)
        os.chdir(ROOT)

    def test_a_foreign_record_cannot_take_the_studys_bundle_name(self):
        """#1543"""
        import json
        from data_sheets_schema import healthsheet
        with tempfile.TemporaryDirectory() as d:
            rec = Path(d) / "other.json"
            rec.write_text(json.dumps({"title": "Other", "metadata": {"healthsheet": {"cohort": [
                {"question": "Q?", "response": "A."}]}}}), encoding="utf-8")
            with self.assertRaises(ValueError) as caught:
                healthsheet.build_bundle(rec, Path(d), project="AI_READI")
            self.assertIn("pass --name", str(caught.exception))
            target, _ = healthsheet.build_bundle(rec, Path(d), project="AI_READI", name="other.txt")
            self.assertEqual(target.name, "other.txt")
            self.assertIn("AI_READI baseline", target.read_text(encoding="utf-8"))   # a foreign record: the key, not the study's prose

    def test_a_nested_manifest_copy_inside_the_checkout_is_not_the_registry(self):
        """#1545"""
        from data_sheets_schema import profiles, registry
        nested = ROOT / "notes/reference_rescore_2026-09-12_cborg_runtime/registrations/measured_inputs_1381/files"
        if not (nested / "data/preprocessed/source_manifest.yaml").exists():
            self.skipTest("no nested manifest copy in this checkout")
        os.chdir(nested)
        self.assertEqual(registry.default_manifest_path().resolve(), STUDY_MANIFEST.resolve())
        self.assertEqual(profiles.select_profile().name, "bridge2ai")
        os.chdir(ROOT)

    def test_a_caller_stated_profile_has_a_basis(self):
        """#1549"""
        spec = self._spec(profile="neutral")
        self.assertEqual((spec.profile, spec.profile_basis), ("neutral", "stated by the caller"))

    def test_the_snapshot_store_accepts_a_pre_profile_identity(self):
        """#1540, #1560, #1566: an index written before the `profile` key
        existed is still this generation's — read, not superseded — and one
        under another instrument is not."""
        import json
        from data_sheets_schema import api_runner, snapshot_store, usage_ledger
        with tempfile.TemporaryDirectory() as d:
            spec = self._spec(out_dir=Path(d))
            api_runner._prepare_usage(spec, resume=False)
            snapshot_store.activate(spec, fresh=True, completed=False, prior_record={})
            artifact = Path(d) / "intermediate" / "CHORUS_full.yaml"
            artifact.parent.mkdir(parents=True, exist_ok=True)
            artifact.write_text("id: https://example.org/x\n", encoding="utf-8")
            snapshot_store.record(spec, "full", artifact)
            index = snapshot_store.index_path(Path(d), "CHORUS")
            data = json.loads(index.read_text(encoding="utf-8"))
            self.assertIn("profile", data["input_identity"])
            data["input_identity"].pop("profile")                        # the pre-profile shape
            index.write_text(json.dumps(data), encoding="utf-8")
            loaded = snapshot_store._load(Path(d), "CHORUS")
            self.assertFalse(loaded.get("superseded"), loaded)
            found, entry = snapshot_store.read_latest(Path(d), "CHORUS", "full", spec=spec)
            self.assertTrue(found); self.assertIsNotNone(entry)
            # The same index under another instrument is not this generation's.
            data["input_identity"]["profile"] = {"name": "neutral", "digest_md5": "029c2abcda26e45c4465fd0a8455893d"}
            index.write_text(json.dumps(data), encoding="utf-8")
            self.assertTrue(snapshot_store._load(Path(d), "CHORUS").get("superseded"))
            with self.assertRaises(usage_ledger.UsageLedgerError):
                snapshot_store.read_latest(Path(d), "CHORUS", "full", spec=spec)

    def _spec(self, **kw):
        from data_sheets_schema.api_runner import RunSpec
        return RunSpec(project="CHORUS", arm="BASELINE (input documents only)", method="claudecode_api",
                       label="2026-09-13_x-api-generic-v9_rep1", condition="generic_v9", run_date="2026-09-13",
                       bundle=ROOT / "data/preprocessed/concatenated/CHORUS_preprocessed.txt", **kw)


class TestRoundSix(_Clean):
    """The Codex round-4 findings (#1558–#1568)."""

    STUDY = "cd3c79f2c62f11675d5ce2c1df96b88e"

    def _fake_client(self):
        import sys
        sys.path.insert(0, str(ROOT / "tests" / "test_download"))
        try:
            from test_api_runner import FakeClient
        finally:
            sys.path.pop(0)
        return FakeClient()

    def _spec(self, **kw):
        from data_sheets_schema.api_runner import RunSpec
        return RunSpec(project="CHORUS", arm="BASELINE (input documents only)", method="claudecode_api",
                       label="2026-09-13_x-api-generic-v9_rep1", condition="generic_v9", run_date="2026-09-13",
                       bundle=ROOT / "data/preprocessed/concatenated/CHORUS_preprocessed.txt", **kw)

    def test_the_recorder_honours_a_no_manifest_selected_header(self):
        """#1558, #1627: from the checkout, on the tracked study bundle the
        automatic rule would select the study manifest — and the runner's
        own "not used (no manifest selected …)" header must still record
        neutral / no manifest. A scratch tree cannot exercise the automatic
        rule, so the header is supplied by a patched parser and the write
        is captured, not made."""
        import click.testing
        from unittest import mock
        from data_sheets_schema import provenance as pv
        from data_sheets_schema.cli import provenance as prov_cli
        label = "2026-07-31_claude-opus-5-api-generic_rep2"
        full = ROOT / "data/d4d_concatenated/claudecode_agent_crate_only" / label / "CHORUS_d4d.yaml"
        if not full.exists():
            self.skipTest("the tracked crate-only output is not in this checkout")
        captured = {}

        def capture(self_, path):
            captured["data"] = self_.data
            return path
        header = {"Source bundle": "data/preprocessed/concatenated/CHORUS_preprocessed.txt",
                  "Source manifest": "not used (no manifest selected; the bundle was passed explicitly)"}
        with mock.patch.object(pv.ProvenanceRecord, "write", capture), \
                mock.patch.object(pv, "parse_header", lambda *a, **k: dict(header)), \
                mock.patch.object(prov_cli, "_inline_checks", lambda *a, **k: None):
            r = click.testing.CliRunner().invoke(prov_cli.provenance, [
                "record", "--project", "CHORUS", "--method", "claudecode_agent_crate_only", "--label", label,
                "--input-bundle", "data/preprocessed/concatenated/CHORUS_preprocessed.txt", "--phase", "generate_full"])
        self.assertEqual(r.exit_code, 0, r.output)
        rec = captured["data"]
        self.assertEqual((rec["schema"]["profile"], rec["schema"]["profile_basis"]), ("neutral", "no manifest"))
        self.assertIsNone(((rec.get("inputs") or {}).get("source_manifest") or {}).get("path"))

    def test_the_recorder_with_no_manifest_option_follows_the_runners_rule(self):
        """#1512: from the checkout, on a tracked crate-only output whose
        header declares the manifest unused, no `--manifest` at all selects
        the study manifest as the runner would — the write is captured, not
        made."""
        import click.testing
        from unittest import mock
        from data_sheets_schema import provenance as pv
        from data_sheets_schema.cli import provenance as prov_cli
        label = "2026-07-31_claude-opus-5-api-generic_rep2"
        full = ROOT / "data/d4d_concatenated/claudecode_agent_crate_only" / label / "CHORUS_d4d.yaml"
        if not full.exists():
            self.skipTest("the tracked crate-only output is not in this checkout")
        self.assertIn("not used", full.read_text(encoding="utf-8")[:2000].lower())
        captured = {}

        def capture(self_, path):
            captured["data"] = self_.data
            return path
        with mock.patch.object(pv.ProvenanceRecord, "write", capture), \
                mock.patch.object(prov_cli, "_inline_checks", lambda *a, **k: None):
            r = click.testing.CliRunner().invoke(prov_cli.provenance, [
                "record", "--project", "CHORUS", "--method", "claudecode_agent_crate_only", "--label", label,
                "--arm", "crate_only", "--input-bundle", "data/preprocessed/concatenated/CHORUS_crate_only.txt",
                "--phase", "generate_full"])
        self.assertEqual(r.exit_code, 0, r.output)
        rec = captured["data"]
        self.assertEqual(rec["schema"]["profile"], "bridge2ai")
        self.assertRegex(rec["schema"]["profile_basis"], r"^manifest:data/preprocessed/source_manifest\.yaml@[0-9a-f]{12}$")
        attested = (rec.get("inputs") or {}).get("source_manifest") or {}
        self.assertIsNone(attested.get("path"))
        self.assertIn("unused", attested.get("basis", ""))

    def test_a_modern_ledger_pin_is_evidence_even_with_legacy_progress(self):
        """#1559"""
        from unittest import mock
        from data_sheets_schema import api_runner, usage_ledger
        from data_sheets_schema.api_runner import RunSpec
        with tempfile.TemporaryDirectory() as d:
            # The plain condition: the fake client writes no coverage receipt.
            spec = RunSpec(project="CHORUS", arm="BASELINE (input documents only)", method="claudecode_api",
                           label="2026-09-13_x-api-generic_rep1", run_date="2026-09-13", out_dir=Path(d),
                           bundle=ROOT / "data/preprocessed/concatenated/CHORUS_preprocessed.txt")
            api_runner._prepare_usage(spec, resume=False)                           # a modern pin, with the profile
            identity = spec.input_identity()
            legacy = {k: v for k, v in identity.items() if k != "profile"}  # the subset rule, not a real pre-profile pin (#1628)
            with mock.patch.object(api_runner, "_load_progress", return_value={"completed": ["full"], "input_identity": legacy,
                                                                                 "generation_id": api_runner._usage_generation(spec)}):
                api_runner.execute(spec, resume=True, client=self._fake_client())   # continues: the ledger attests the instrument
            self.assertTrue((Path(d) / "CHORUS_provenance.yaml").exists())

    def test_the_classifier_refuses_a_foreign_instrument_before_its_cache(self):
        """#1561, #1562"""
        from data_sheets_schema.form_defects import FormFailure, FormSubtypeClassifier
        from data_sheets_schema.profiles import BRIDGE2AI
        c = FormSubtypeClassifier(client=object(), model="offline-test", profile=BRIDGE2AI)
        own = FormFailure(project="P", slot="instances", value="[]", reason="wrong kind", fitness=0.0, schema=c.schema)
        c._memo[own.key + (":" + __import__("hashlib").sha256(b"wrong kind").hexdigest() if c.specification else "")] = ("other", "cached")
        self.assertEqual(c(own), ("other", "cached"))
        foreign = FormFailure(project="P", slot="instances", value="[]", reason="wrong kind", fitness=0.0,
                              schema="029c2abcda26e45c4465fd0a8455893d")
        with self.assertRaises(ValueError):
            c(foreign)                                                          # cached for its key, refused before the memo
        if c.specification:
            other_spec = FormFailure(project="P", slot="instances", value="[]", reason="wrong kind", fitness=0.0,
                                     schema=c.schema, specification="0" * 64)
            with self.assertRaises(ValueError):
                c(other_spec)

    def test_loading_refuses_two_specifications(self):
        """#1562"""
        import json
        from data_sheets_schema.form_defects import load_form_failures
        with tempfile.TemporaryDirectory() as d:
            rows = [{"failure": "form", "rubric": "r", "model": "m", "slot": "instances", "value": "[]", "reason": "x",
                     "fitness": 0.0, "schema": self.STUDY, "specification": s} for s in ("a" * 64, "b" * 64)]
            (Path(d) / "P_fitness.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
            with self.assertRaises(ValueError) as caught:
                load_form_failures(Path(d))
            self.assertIn("specification", str(caught.exception))

    def test_load_registry_follows_the_one_default_rule(self):
        """#1563"""
        from data_sheets_schema import registry
        nested = ROOT / "notes/reference_rescore_2026-09-12_cborg_runtime/registrations/measured_inputs_1381/files"
        if not (nested / "data/preprocessed/source_manifest.yaml").exists():
            self.skipTest("no nested manifest copy in this checkout")
        os.chdir(nested)
        self.assertEqual(Path(registry.load_registry().path).resolve(), STUDY_MANIFEST.resolve())
        os.chdir(ROOT)

    def test_the_tracked_bundle_name_is_reserved_under_every_profile(self):
        """#1565"""
        from data_sheets_schema import healthsheet
        from data_sheets_schema.profiles import BRIDGE2AI
        rec = ROOT / BRIDGE2AI.healthsheet_record
        if not rec.exists():
            self.skipTest("the study's healthsheet record is not in this checkout")
        os.environ["D4D_PROFILE"] = "neutral"
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError) as caught:
                healthsheet.build_bundle(rec, Path(d), project="AI_READI")
            self.assertIn("pass --name", str(caught.exception))

    def test_the_default_healthsheet_invocation_works_from_a_subdirectory(self):
        """#1567"""
        from data_sheets_schema import healthsheet
        from data_sheets_schema.profiles import BRIDGE2AI
        if not (ROOT / BRIDGE2AI.healthsheet_record).exists():
            self.skipTest("the study's healthsheet record is not in this checkout")
        os.chdir(ROOT / "tests")
        with tempfile.TemporaryDirectory() as d:
            target, _ = healthsheet.build_bundle(None, Path(d))
            self.assertEqual(target.name, BRIDGE2AI.healthsheet_bundle)
        os.chdir(ROOT)

    def test_the_ledger_refuses_a_replay_spec(self):
        """#1568"""
        from data_sheets_schema import usage_ledger
        from data_sheets_schema.api_runner import RunSpec
        replay = RunSpec.from_render_spec({"condition": "generic"}, project="P", method="claudecode_api", label="L")
        with self.assertRaises(usage_ledger.UsageLedgerError):
            usage_ledger.prepare_usage(replay, resume=True)



class TestRoundSeven(_Clean):
    """The Claude round-4 findings (#1581–#1586)."""

    def test_the_environment_selected_profile_reaches_the_recorder(self):
        """#1581: the rendered recording command carries the profile; the
        recorder records it over what its own process would select; the
        render gate's spec carries it; a record whose digest is the other
        profile's is a finding."""
        import click.testing
        from data_sheets_schema.api_runner import RunSpec, resolve_prompt
        from data_sheets_schema.cli import provenance as prov_cli
        from data_sheets_schema.cli.api import ARMS
        from data_sheets_schema.provenance import check_record
        os.environ["D4D_PROFILE"] = "neutral"
        spec = RunSpec(project="CHORUS", arm=ARMS["baseline"][0], method=ARMS["baseline"][1],
                       label="2026-09-13_x-claudecode-generic-v9_rep1", condition="generic_v9",
                       runtime="Claude Code", run_date="2026-09-13",
                       bundle=ROOT / "data/preprocessed/concatenated/CHORUS_preprocessed.txt")
        self.assertEqual((spec.profile, spec.profile_basis), ("neutral", "environment"))
        line = next(l for l in resolve_prompt(spec).splitlines() if "d4d provenance record" in l)
        self.assertIn("--profile neutral", line)
        self.assertEqual(spec.render_spec()["profile"], "neutral")
        replay = RunSpec.from_render_spec(spec.render_spec(), project="CHORUS", method=spec.method, label=spec.label)
        self.assertEqual((replay.profile, replay.profile_basis), ("neutral", "environment"))
        self.assertEqual(resolve_prompt(replay), resolve_prompt(spec))            # the gate re-renders the same line
        os.environ.pop("D4D_PROFILE")
        # The recorder in a process without the environment, told the profile.
        method, label = "claudecode_api", "2026-09-13_test-env_rep1"
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "src/data_sheets_schema").mkdir(parents=True)
            full_dir = root / "data/d4d_concatenated" / method / label
            core_dir = root / "data/d4d_concatenated" / f"{method}_core" / label
            full_dir.mkdir(parents=True); core_dir.mkdir(parents=True)
            man = root / "data/preprocessed/source_manifest.yaml"; man.parent.mkdir(parents=True)
            man.write_text(yaml.safe_dump({"profile": "bridge2ai",
                                           "projects": {"CHORUS": [{"id": "s", "source": "s", "title": "s"}]}}), encoding="utf-8")
            bundle = root / "data/preprocessed/concatenated/CHORUS_preprocessed.txt"
            bundle.parent.mkdir(parents=True, exist_ok=True); bundle.write_text("docs\n", encoding="utf-8")
            body = "# Generated: 2026-09-13\n# Source manifest: data/preprocessed/source_manifest.yaml\nid: https://example.org/x\nname: x\n"
            (full_dir / "CHORUS_d4d.yaml").write_text(body, encoding="utf-8")
            (core_dir / "CHORUS_d4d_core.yaml").write_text(body, encoding="utf-8")
            (core_dir / "CHORUS_reconciliation.md").write_text("# r\n", encoding="utf-8")
            os.chdir(root)
            try:
                r = click.testing.CliRunner().invoke(prov_cli.provenance, [
                    "record", "--project", "CHORUS", "--method", method, "--label", label,
                    "--input-bundle", str(bundle), "--manifest", "data/preprocessed/source_manifest.yaml",
                    "--profile", "neutral", "--phase", "generate_full"])
            finally:
                os.chdir(ROOT)
            self.assertEqual(r.exit_code, 0, r.output)
            rec = yaml.safe_load((core_dir / "CHORUS_provenance.yaml").read_text(encoding="utf-8"))
        self.assertEqual(rec["schema"]["profile"], "neutral")
        self.assertTrue(rec["schema"]["profile_basis"].startswith("rendered instruction (this process would select bridge2ai"))
        self.assertEqual(rec["schema"]["digest_md5"], "029c2abcda26e45c4465fd0a8455893d")
        # A profile whose digest is the other profile's current digest is a finding.
        bad = dict(rec); bad["schema"] = dict(rec["schema"], digest_md5="cd3c79f2c62f11675d5ce2c1df96b88e")
        violations, why = check_record(bad)
        self.assertIsNone(why)
        self.assertTrue(any("bridge2ai profile's current digest" in v for v in violations), violations)

    def test_an_unknown_stated_profile_fails_at_construction(self):
        """#1585"""
        from data_sheets_schema.api_runner import RunSpec
        with self.assertRaises(ValueError) as caught:
            RunSpec(project="CHORUS", arm="x", method="claudecode_api", label="L", profile="bogus",
                    bundle=ROOT / "data/preprocessed/concatenated/CHORUS_preprocessed.txt")
        self.assertIn("bridge2ai", str(caught.exception))

    def test_an_unreadable_manifest_names_the_file(self):
        """#1586"""
        from data_sheets_schema.profiles import select_profile
        with tempfile.TemporaryDirectory() as d:
            m = Path(d) / "m.yaml"; m.write_text("[broken", encoding="utf-8")
            with self.assertRaises(ValueError) as caught:
                select_profile(m)
            self.assertIn("m.yaml", str(caught.exception))


class TestRoundEight(_Clean):
    """The Codex round-5 findings (#1606–#1611)."""

    def _recorder(self, args, env):
        """The recorder from the checkout root with its writes captured —
        the record's `build_record` keywords and nothing on disk."""
        import click.testing
        from data_sheets_schema import provenance as pv
        from data_sheets_schema.cli import provenance as prov_cli
        with mock.patch.dict(os.environ, env, clear=False):
            for k in ("D4D_PROFILE",):
                if k not in env:
                    os.environ.pop(k, None)
            rec = mock.Mock(data={}, validation_carried=None)
            with mock.patch.object(pv, "build_record", return_value=rec) as build, \
                    mock.patch.object(prov_cli, "_inline_checks"):
                r = click.testing.CliRunner().invoke(prov_cli.provenance, ["record", *args])
        return r, (build.call_args.kwargs if build.call_args else None)

    def test_the_saved_spec_carries_the_stated_profile(self):
        """#1606: under `--condition` the saved render spec re-renders the
        instruction that was sent, under the profile the record states — and
        a recorder whose own environment is invalid still records it."""
        from data_sheets_schema.api_runner import RunSpec, resolve_prompt
        from data_sheets_schema.cli.api import ARMS
        bundle = ROOT / "data/preprocessed/concatenated/CHORUS_preprocessed.txt"
        label = "2026-09-13_x-claudecode-generic-v9_rep1"
        os.environ["D4D_PROFILE"] = "neutral"
        spec = RunSpec(project="CHORUS", method=ARMS["baseline"][1], arm=ARMS["baseline"][0], bundle=bundle,
                       label=label, condition="generic_v9", runtime="Claude Code", provider="Anthropic")
        sent = resolve_prompt(spec)
        os.environ.pop("D4D_PROFILE")
        args = ["--project", "CHORUS", "--method", spec.method, "--label", label, "--input-bundle", str(bundle),
                "--manifest", str(spec.manifest), "--profile", "neutral", "--condition", "generic_v9",
                "--runtime", "Claude Code", "--provider", "Anthropic", "--phase", "generate_full"]
        r, kw = self._recorder(args, {})
        self.assertEqual(r.exit_code, 0, r.output)
        self.assertEqual(kw["profile"].name, "neutral")
        self.assertTrue(kw["profile"].basis.startswith("rendered instruction (this process would select bridge2ai"))
        saved = kw["prompt_request_spec"]
        self.assertEqual((saved["profile"], saved["profile_basis"]), ("neutral", kw["profile"].basis))
        replay = RunSpec.from_render_spec(saved, project="CHORUS", method=spec.method, label=label)
        self.assertEqual(resolve_prompt(replay), sent)                    # the gate would read `match`
        r, kw = self._recorder(args, {"D4D_PROFILE": "typo"})           # an invalid ambient selection
        self.assertEqual(r.exit_code, 0, r.output)
        self.assertEqual(kw["profile"].name, "neutral")
        self.assertIn("could not select one", kw["profile"].basis)

    def test_backfill_spec_reconstructs_the_single_source_arms(self):
        """#1607: an arm with its own "not used" header, whose record names no
        manifest as consumed, still re-renders — the selected manifest is tried."""
        import hashlib
        import click.testing
        import yaml
        from data_sheets_schema import provenance as pv
        from data_sheets_schema.api_runner import RunSpec, resolve_prompt
        from data_sheets_schema.cli import provenance as prov_cli
        from data_sheets_schema.cli.api import ARMS
        label = "2026-09-13_x-claudecode-generic-v9_rep1"
        for arm, project in (("crate_only", "CHORUS"), ("healthsheet", "AI_READI")):
            display, method, pattern, header = ARMS[arm]
            bundle = ROOT / "data/preprocessed/concatenated" / pattern.format(p=project)
            if not bundle.exists():
                self.skipTest(f"no {bundle.name} bundle")
            spec = RunSpec(project=project, arm=display, method=method, bundle=bundle, label=label,
                           condition="generic_v9", runtime="Claude Code", provider="Anthropic",
                           run_date="2026-09-13", manifest_line=header)
            self.assertFalse(spec.manifest_used); self.assertIsNotNone(spec.manifest)   # selected, not consumed
            record = {"record_generated_at": "2026-09-13T12:00:00Z", "model": {"provider": "Anthropic"},
                      "schema": {"profile": spec.profile, "profile_basis": spec.profile_basis},
                      "inputs": {"bundle_path": str(bundle), "source_manifest": {"path": None},
                                 **({"chunks": {"path": str(spec.chunk_manifest)}} if spec.chunk_manifest else {})},
                      "prompts": {"request": {"sha256": hashlib.sha256(resolve_prompt(spec).encode()).hexdigest()}}}
            with tempfile.TemporaryDirectory() as d:
                path = Path(d) / f"{project}_provenance.yaml"
                path.write_text(yaml.safe_dump(record), encoding="utf-8")
                with mock.patch.object(pv, "record_path_for", return_value=path):
                    r = click.testing.CliRunner().invoke(prov_cli.provenance, [
                        "backfill-spec", "--project", project, "--method", method, "--label", label,
                        "--condition", "generic_v9", "--runtime", "Claude Code", "--arm", arm])
            self.assertEqual(r.exit_code, 0, f"{arm}: {r.output}")
            self.assertIn("re-renders to the recorded hash", r.output)

    def test_a_missing_attestation_is_an_instrument_boundary(self):
        """#1608: a failure with a complete-specification hash never takes a
        label cached without one, and the loader refuses a mixed population."""
        import json
        from data_sheets_schema.form_defects import FormFailure, FormSubtypeClassifier, load_form_failures
        from data_sheets_schema.profiles import BRIDGE2AI
        study = "cd3c79f2c62f11675d5ce2c1df96b88e"
        fresh = FormFailure(project="P", slot="instances", value="[]", reason="wrong kind", fitness=0.0,
                            schema=study, specification="b" * 64)
        legacy = FormSubtypeClassifier(client=object(), model="offline-test", schema=study, specification="",
                                       profile=BRIDGE2AI, offline=True)
        legacy._memo[fresh.key] = ("other", "cached before the specification was recorded")
        with self.assertRaises(ValueError):
            legacy(fresh)
        # A failure with no attestation at all is legacy — read like one with
        # no schema, stamped rather than refused — so the attested classifier
        # serves it (its key carries the reason hash).
        old = FormFailure(project="P", slot="instances", value="[]", reason="wrong kind", fitness=0.0,
                          schema=study, specification="")
        attested = FormSubtypeClassifier(client=object(), model="offline-test", schema=study,
                                         specification="b" * 64, profile=BRIDGE2AI, offline=True)
        attested._memo[old.key + ":" + __import__("hashlib").sha256(b"wrong kind").hexdigest()] = ("other", "x")
        self.assertEqual(attested(old), ("other", "x"))
        with tempfile.TemporaryDirectory() as d:
            rows = [{"failure": "form", "rubric": "r", "model": "m", "slot": "instances", "value": "[]",
                     "reason": "wrong kind", "fitness": 0.0, "schema": study, **({"specification": "b" * 64} if s else {})}
                    for s in (False, True)]
            (Path(d) / "P_fitness.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_form_failures(Path(d))
            (Path(d) / "P_fitness.jsonl").write_text(json.dumps(rows[0]) + "\n", encoding="utf-8")
            self.assertEqual(len(load_form_failures(Path(d))), 1)       # one population loads

    def test_a_profiles_own_digest_is_never_a_disagreement(self):
        """#1609"""
        from data_sheets_schema import schema_digest
        from data_sheets_schema.provenance import _profile_digest_disagreement
        with mock.patch.object(schema_digest, "digest_text", return_value="the same bytes"):
            same = schema_digest.fingerprint("the same bytes")
            self.assertIsNone(_profile_digest_disagreement({"schema": {"profile": "bridge2ai", "digest_md5": same}}))
            self.assertIsNone(_profile_digest_disagreement({"schema": {"profile": "neutral", "digest_md5": same}}))

    def test_a_malformed_manifest_is_refused_not_read_as_neutral(self):
        """#1610"""
        from data_sheets_schema.profiles import declared_profile, select_profile
        with tempfile.TemporaryDirectory() as d:
            m = Path(d) / "m.yaml"
            m.write_text("- a\n- b\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "not a mapping"):
                declared_profile(m)
            with self.assertRaises(ValueError):
                select_profile(m)
            m.write_text("profile: []\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "not a profile name"):
                declared_profile(m)
            m.write_text("", encoding="utf-8")
            self.assertIsNone(declared_profile(m))                       # an empty document declares nothing
            m.write_text("projects: {}\n", encoding="utf-8")
            self.assertIsNone(declared_profile(m))

    def test_the_utility_agents_name_no_study_project(self):
        """#1611: the executable examples a user copies name no study project."""
        import re
        for rel in (".claude/agents/d4d-rocrate.md", ".claude/agents/d4d-mapper.md", ".claude/agents/d4d-validator.md"):
            text = (ROOT / rel).read_text(encoding="utf-8")
            self.assertIsNone(re.search(r"\b(AI_READI|CHORUS|CM4AI|VOICE)\b", text), rel)
        self.assertNotIn("b2ai-voice", (ROOT / ".claude/commands/d4d-uniform-rules.md").read_text(encoding="utf-8"))


class TestRoundNine(_Clean):
    """The Claude round-5 findings (#1626–#1632)."""

    def _spec(self, **over):
        from data_sheets_schema.api_runner import RunSpec
        from data_sheets_schema.cli.api import ARMS
        return RunSpec(project="CHORUS", method=ARMS["baseline"][1], arm=ARMS["baseline"][0],
                       bundle=ROOT / "data/preprocessed/concatenated/CHORUS_preprocessed.txt",
                       label="2026-09-13_x-claudecode-generic-v9_rep1", condition="generic_v9",
                       runtime="Claude Code", provider="Anthropic", run_date="2026-09-13", **over)

    def test_the_basis_is_recorded_but_is_not_the_resume_identity(self):
        """#1626"""
        from data_sheets_schema.api_runner import RunSpec
        from data_sheets_schema.usage_ledger import _identity_differs
        a = self._spec(profile="bridge2ai", profile_basis="manifest:data/preprocessed/source_manifest.yaml@000000000000")
        b = self._spec(profile="bridge2ai", profile_basis="environment")
        self.assertNotEqual(a.render_spec()["profile_basis"], b.render_spec()["profile_basis"])   # the record keeps it
        self.assertFalse(_identity_differs(a.input_identity(), b.input_identity()))
        self.assertNotIn("profile_basis", a.input_identity()["instruction"]["spec"])
        self.assertEqual(a.input_identity()["profile"]["name"], "bridge2ai")
        replay = RunSpec.from_render_spec(a.render_spec(), project="CHORUS", method=a.method, label=a.label)
        self.assertEqual(replay.profile_basis, a.profile_basis)

    def test_a_real_pre_profile_pin_is_refused_and_the_refusal_says_why(self):
        """#1628: a pin whose instruction predates `--profile` never matches."""
        import hashlib
        from data_sheets_schema.api_runner import RunSpec, resolve_prompt
        from data_sheets_schema.usage_ledger import UsageLedgerError, _identity_differs, require_resolved
        current = self._spec()
        old_dict = {k: v for k, v in current.render_spec().items() if k not in ("profile", "profile_basis")}
        old = RunSpec.from_render_spec(old_dict, project="CHORUS", method=current.method, label=current.label)
        old_identity = {k: v for k, v in current.input_identity().items() if k != "profile"}
        old_identity["instruction"] = {"render_version": old.render_version, "spec": old_dict,
                                       "sha256": hashlib.sha256(resolve_prompt(old).encode()).hexdigest()}
        self.assertNotIn("--profile", resolve_prompt(old))
        self.assertTrue(_identity_differs(old_identity, current.input_identity()))
        with mock.patch("data_sheets_schema.usage_ledger._read", return_value={"input_identity": old_identity}):
            with self.assertRaises(UsageLedgerError) as caught:
                require_resolved(current)
        self.assertIn("cannot be resumed", str(caught.exception))          # the cause is named (#1628, #1712)

    def test_an_unknown_profile_is_a_usage_error_not_a_traceback(self):
        """#1630"""
        import click.testing
        from data_sheets_schema.cli import provenance as prov_cli
        from data_sheets_schema.cli.api import _spec
        r = click.testing.CliRunner().invoke(prov_cli.provenance, [
            "record", "--project", "CHORUS", "--method", "claudecode_api", "--label", "x", "--profile", "bogus"])
        self.assertEqual(r.exit_code, 2, r.output)
        self.assertIn("Invalid value for '--profile'", r.output)
        with tempfile.TemporaryDirectory() as d:
            man = Path(d) / "m.yaml"
            man.write_text("profile: Bridge2AI\nprojects:\n  CHORUS:\n    - {id: s, source: s, title: s}\n", encoding="utf-8")
            with self.assertRaises(click.ClickException) as caught:
                _spec("CHORUS", "baseline", "2026-09-13_x_rep1", "generic_v9",
                      bundle=str(ROOT / "data/preprocessed/concatenated/CHORUS_preprocessed.txt"), manifest=man)
            self.assertIn("unknown profile", str(caught.exception))

    def test_the_profile_is_an_arm_procedure_field(self):
        """#1631"""
        from data_sheets_schema.runs import ARM_PROCEDURE_FIELDS
        self.assertIn(("profile", ("schema", "profile")), ARM_PROCEDURE_FIELDS)

    def test_the_basis_vocabulary_is_documented_everywhere(self):
        """#1632"""
        from data_sheets_schema.profiles import Selection
        import inspect
        for text, where in ((inspect.getsource(Selection), "Selection"),
                            ((ROOT / "src/data_sheets_schema/schema/d4d_generation_record.yaml").read_text(encoding="utf-8"), "record schema"),
                            ((ROOT / "CLAUDE.md").read_text(encoding="utf-8"), "CLAUDE.md")):
            self.assertIn("rendered instruction", text, where)
            self.assertIn("stated by the caller", text, where)
            self.assertIn("could not select one", text, where)                # #1660
            self.assertIn("backfill-spec", text, where)


class TestRoundTen(_Clean):
    """The Codex round-6 findings (#1654–#1661)."""

    def test_backfill_spec_takes_the_selected_manifest_as_a_candidate(self):
        """#1654: a single-source run that selected the study manifest under
        another spelling re-renders when the caller names it."""
        import hashlib
        import click.testing
        import yaml
        from data_sheets_schema import provenance as pv
        from data_sheets_schema.api_runner import RunSpec, resolve_prompt
        from data_sheets_schema.cli import provenance as prov_cli
        from data_sheets_schema.cli.api import ARMS
        display, method, pattern, header = ARMS["crate_only"]
        bundle = ROOT / "data/preprocessed/concatenated" / pattern.format(p="CHORUS")
        if not bundle.exists():
            self.skipTest("no crate-only bundle")
        selected = Path("data/preprocessed/../preprocessed/source_manifest.yaml")
        spec = RunSpec(project="CHORUS", arm=display, method=method, bundle=bundle, condition="generic_v9",
                       label="2026-09-13_x-claudecode-generic-v9_rep1", manifest=selected, manifest_line=header,
                       runtime="Claude Code", provider="Anthropic", run_date="2026-09-13")
        record = {"record_generated_at": "2026-09-13T12:00:00Z", "model": {"provider": "Anthropic"},
                  "schema": {"profile": spec.profile, "profile_basis": spec.profile_basis},
                  "inputs": {"bundle_path": str(bundle), "source_manifest": {"path": None},
                             **({"chunks": {"path": str(spec.chunk_manifest)}} if spec.chunk_manifest else {})},
                  "prompts": {"request": {"sha256": hashlib.sha256(resolve_prompt(spec).encode()).hexdigest()}}}
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "CHORUS_provenance.yaml"; path.write_text(yaml.safe_dump(record), encoding="utf-8")
            with mock.patch.object(pv, "record_path_for", return_value=path):
                base = ["backfill-spec", "--project", "CHORUS", "--method", method, "--label", spec.label,
                        "--condition", "generic_v9", "--runtime", "Claude Code", "--arm", "crate_only"]
                without = click.testing.CliRunner().invoke(prov_cli.provenance, base)
                with_it = click.testing.CliRunner().invoke(prov_cli.provenance, base + ["--manifest", str(selected)])
        self.assertNotEqual(without.exit_code, 0)                              # not a default spelling
        self.assertEqual(with_it.exit_code, 0, with_it.output)
        self.assertIn("re-renders to the recorded hash", with_it.output)

    def test_a_malformed_profile_is_a_finding_not_a_crash(self):
        """#1655"""
        from data_sheets_schema.provenance import _profile_digest_disagreement, check_record
        for value in (["neutral"], {"name": "neutral"}, 3):
            self.assertIsNone(_profile_digest_disagreement({"schema": {"profile": value, "digest_md5": "029c2abcda26e45c4465fd0a8455893d"}}))
            problems, why = check_record({"schema": {"profile": value, "digest_md5": "029c2abcda26e45c4465fd0a8455893d"}})
            self.assertTrue(problems or why)

    def test_a_pin_that_carried_the_basis_still_resumes(self):
        """#1657"""
        from data_sheets_schema.api_runner import RunSpec
        from data_sheets_schema.cli.api import ARMS
        from data_sheets_schema.usage_ledger import _identity_differs
        spec = RunSpec(project="CHORUS", method=ARMS["baseline"][1], arm=ARMS["baseline"][0],
                       bundle=ROOT / "data/preprocessed/concatenated/CHORUS_preprocessed.txt",
                       label="2026-09-13_x-claudecode-generic-v9_rep1", condition="generic_v9",
                       runtime="Claude Code", provider="Anthropic", run_date="2026-09-13", profile="bridge2ai")
        current = spec.input_identity()
        older = dict(current); older["instruction"] = {**current["instruction"],
                                                       "spec": {**current["instruction"]["spec"], "profile_basis": "environment"}}
        self.assertNotEqual(older, current)
        self.assertFalse(_identity_differs(older, current))
        self.assertFalse(_identity_differs(current, older))
        changed = dict(older); changed["bundle"] = {"path": "x", "sha256": "y"}
        self.assertTrue(_identity_differs(changed, current))

    def test_a_falsey_non_mapping_manifest_is_refused_by_the_registry(self):
        """#1658"""
        import click
        from data_sheets_schema import schema_cache
        from data_sheets_schema.registry import load_registry
        with tempfile.TemporaryDirectory() as d:
            m = Path(d) / "m.yaml"
            for text in ("[]\n", "0\n", "false\n"):
                m.write_text(text, encoding="utf-8"); schema_cache.clear()
                with self.assertRaises(click.ClickException):
                    load_registry(m)
            m.write_text("", encoding="utf-8"); schema_cache.clear()
            self.assertIsNotNone(load_registry(m))                              # an empty document is an empty registry

    def test_the_healthsheet_cli_default_works_from_a_subdirectory(self):
        """#1659"""
        import click.testing
        from data_sheets_schema.cli.healthsheet import healthsheet as cli
        from data_sheets_schema.profiles import BRIDGE2AI
        if not (ROOT / BRIDGE2AI.healthsheet_record).exists():
            self.skipTest("the study's healthsheet record is not in this checkout")
        os.chdir(ROOT / "tests")
        with tempfile.TemporaryDirectory() as d:
            r = click.testing.CliRunner().invoke(cli, ["bundle", "--output-dir", d])
            self.assertEqual(r.exit_code, 0, r.output)
            self.assertTrue((Path(d) / BRIDGE2AI.healthsheet_bundle).exists())


class TestRoundEleven(_Clean):
    """The Claude round-6 findings (#1676–#1679)."""

    def _spec(self, **over):
        from data_sheets_schema.api_runner import RunSpec
        from data_sheets_schema.cli.api import ARMS
        return RunSpec(project="CHORUS", method=ARMS["baseline"][1], arm=ARMS["baseline"][0],
                       bundle=ROOT / "data/preprocessed/concatenated/CHORUS_preprocessed.txt",
                       label="2026-09-13_x-claudecode-generic-v9_rep1", condition="generic_v9",
                       runtime="Claude Code", provider="Anthropic", run_date="2026-09-13", **over)

    def test_the_reconstructed_prior_rule_binds_under_the_subset_rule(self):
        """#1676, #1629: a saved identity lacking the profile key still binds the
        generation; one whose bundle moved does not."""
        from data_sheets_schema import api_runner as a
        spec = self._spec(profile="bridge2ai")
        current = spec.input_identity()
        subset = {k: v for k, v in current.items() if k != "profile"}
        progress = {"generation_id": "g1", "run_identity": None, "input_identity": subset}
        with mock.patch.object(a, "_usage_record_matches", return_value=True):
            self.assertTrue(a._generation_bound_inputs_observed(spec, progress, "g1", None, current))
            moved = dict(subset, bundle={"path": "x", "sha256": "y"})
            self.assertFalse(a._generation_bound_inputs_observed(spec, dict(progress, input_identity=moved), "g1", None, current))
            self.assertTrue(a._generation_bound_inputs_observed(spec, {}, "g1", subset, current))     # the ledger's pin
            self.assertFalse(a._generation_bound_inputs_observed(spec, {}, "g1", moved, current))

    def test_the_subset_rule_holds_at_every_depth_and_the_refusal_names_its_cause(self):
        """#1677"""
        import hashlib
        from data_sheets_schema.api_runner import RunSpec, resolve_prompt
        from data_sheets_schema.usage_ledger import _identity_differs, identity_refusal, pre_profile_pin
        current = self._spec(profile="bridge2ai").input_identity()
        nested_subset = dict(current, instruction={**current["instruction"],
                                                   "spec": {k: v for k, v in current["instruction"]["spec"].items() if k != "chunk_manifest"}})
        self.assertFalse(_identity_differs(nested_subset, current))
        with_basis = dict(current, instruction={**current["instruction"], "spec": {**current["instruction"]["spec"], "profile_basis": "environment"}})
        self.assertFalse(_identity_differs(with_basis, current))
        self.assertNotIn("before profiles existed", identity_refusal(with_basis, "x"))     # not the cause
        old_dict = {k: v for k, v in self._spec().render_spec().items() if k not in ("profile", "profile_basis")}
        old = RunSpec.from_render_spec(old_dict, project="CHORUS", method=self._spec().method, label=self._spec().label)
        pre = {k: v for k, v in current.items() if k != "profile"}
        pre["instruction"] = {"render_version": old.render_version, "spec": old_dict,
                              "sha256": hashlib.sha256(resolve_prompt(old).encode()).hexdigest()}
        self.assertTrue(pre_profile_pin(pre)); self.assertTrue(_identity_differs(pre, current))
        self.assertIn("cannot be resumed", identity_refusal(pre, "x"))

    def test_a_backfilled_profile_is_the_records_and_a_disagreement_is_a_finding(self):
        """#1678"""
        import hashlib
        import click.testing
        import yaml
        from data_sheets_schema import provenance as pv
        from data_sheets_schema.api_runner import resolve_prompt
        from data_sheets_schema.cli import provenance as prov_cli
        from data_sheets_schema.profiles import for_record
        from data_sheets_schema.provenance import _spec_profile_disagreement, check_record
        os.environ["D4D_PROFILE"] = "neutral"
        spec = self._spec()
        os.environ.pop("D4D_PROFILE")
        self.assertEqual(spec.profile, "neutral")
        record = {"record_generated_at": "2026-09-13T12:00:00Z", "model": {"provider": "Anthropic"},
                  "inputs": {"bundle_path": str(spec.bundle), "source_manifest": {"path": str(spec.manifest)},
                             **({"chunks": {"path": str(spec.chunk_manifest)}} if spec.chunk_manifest else {})},
                  "prompts": {"request": {"sha256": hashlib.sha256(resolve_prompt(spec).encode()).hexdigest()}}}
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "CHORUS_provenance.yaml"; path.write_text(yaml.safe_dump(record), encoding="utf-8")
            with mock.patch.object(pv, "record_path_for", return_value=path):
                r = click.testing.CliRunner().invoke(prov_cli.provenance, [
                    "backfill-spec", "--project", "CHORUS", "--method", spec.method, "--label", spec.label,
                    "--condition", "generic_v9", "--runtime", "Claude Code", "--execute"])
            self.assertEqual(r.exit_code, 0, r.output)
            written = yaml.safe_load(path.read_text(encoding="utf-8"))
        self.assertEqual(written["prompts"]["request"]["spec"]["profile"], "neutral")
        self.assertEqual(written["schema"]["profile"], "neutral")               # the readers see it too
        self.assertEqual(for_record(written).name, "neutral")
        self.assertIsNone(_spec_profile_disagreement(written))
        split = {"schema": {"profile": "bridge2ai", "digest_md5": "x"}, "prompts": {"request": {"spec": {"profile": "neutral"}}}}
        self.assertIn("different instruments", _spec_profile_disagreement(split))
        problems, _ = check_record(split)
        self.assertTrue(any("different instruments" in p for p in problems))

    def test_an_unknown_ambient_profile_is_a_usage_error_everywhere(self):
        """#1679"""
        import click.testing
        from data_sheets_schema.cli.healthsheet import healthsheet as hs
        from data_sheets_schema.cli import provenance as prov_cli
        os.environ["D4D_PROFILE"] = "typo"
        r = click.testing.CliRunner().invoke(hs, ["bundle", "--output-dir", tempfile.mkdtemp()])
        self.assertNotEqual(r.exit_code, 0)
        self.assertNotIsInstance(r.exception, ValueError, r.output)
        label = "2026-07-31_claude-opus-5-api-generic_rep2"                  # a tracked record (#1705)
        if (ROOT / "data/d4d_concatenated/claudecode_agent_crate_only_core" / label / "CHORUS_provenance.yaml").exists():
            os.chdir(ROOT)
            r = click.testing.CliRunner().invoke(prov_cli.provenance, [
                "recheck-validation", "--method", "claudecode_agent_crate_only", "--label", label, "--project", "CHORUS"])
            self.assertNotIsInstance(r.exception, ValueError, r.output)
            self.assertIn("unknown profile", r.output)
        import subprocess, sys
        r2 = subprocess.run([sys.executable, "-m", "data_sheets_schema.form_defects", "--offline", "--profile", "bogus"],
                            capture_output=True, text=True, cwd=ROOT, env={**os.environ, "PYTHONPATH": str(ROOT / "src")})
        self.assertNotEqual(r2.returncode, 0); self.assertIn("invalid choice", r2.stderr)


class TestRoundTwelve(_Clean):
    """The Codex round-7 findings (#1698–#1708)."""

    def test_a_pin_without_its_inputs_is_no_pin(self):
        """#1698"""
        from data_sheets_schema.api_runner import RunSpec
        from data_sheets_schema.cli.api import ARMS
        from data_sheets_schema.usage_ledger import _identity_differs
        spec = RunSpec(project="CHORUS", method=ARMS["baseline"][1], arm=ARMS["baseline"][0],
                       bundle=ROOT / "data/preprocessed/concatenated/CHORUS_preprocessed.txt",
                       label="2026-09-13_x-claudecode-generic-v9_rep1", condition="generic_v9",
                       runtime="Claude Code", provider="Anthropic", run_date="2026-09-13", profile="bridge2ai")
        current = spec.input_identity()
        self.assertTrue(_identity_differs({"profile": current["profile"], "instruction": {"render_version": 4}}, current))
        self.assertTrue(_identity_differs({k: v for k, v in current.items() if k != "bundle"}, current))
        no_hash = dict(current, instruction={k: v for k, v in current["instruction"].items() if k != "sha256"})
        self.assertTrue(_identity_differs(no_hash, current))
        self.assertFalse(_identity_differs({k: v for k, v in current.items() if k != "profile"}, current))
        self.assertTrue(_identity_differs("not a pin", current)); self.assertTrue(_identity_differs(current, None))

    def test_malformed_records_and_pins_never_crash_the_helpers(self):
        """#1700, #1701"""
        from data_sheets_schema.provenance import _spec_profile_disagreement, check_record, profile_problems
        from data_sheets_schema.usage_ledger import identity_refusal, pre_profile_pin
        for prompts in ("text", 3, ["x"], {"request": "text"}, {"request": {"spec": ["x"]}}, {"request": {"spec": {"profile": 5}}}):
            data = {"schema": {"profile": "bridge2ai", "digest_md5": "x"}, "prompts": prompts}
            self.assertIsNone(_spec_profile_disagreement(data)); self.assertIsInstance(profile_problems(data), list)
            problems, why = check_record(data); self.assertTrue(problems or why)
        for pin in ("text", None, {"instruction": "text"}, {"instruction": {"spec": "x"}}, {"instruction": {"spec": ["x"]}}, {"instruction": None}):
            pre_profile_pin(pin); self.assertIn("generation input identity changed", identity_refusal(pin, "x"))
        self.assertFalse(pre_profile_pin({"instruction": {"spec": {"bundle": "b"}}}))
        self.assertFalse(pre_profile_pin({"profile": {"name": "neutral"}, "instruction": {"spec": {}}}))    # incomplete evidence, not an attested historical instruction (#1744)
        self.assertFalse(pre_profile_pin({"profile": {"name": "neutral"}, "instruction": {"spec": {"profile": "neutral"}}}))

    def test_runs_check_fails_strict_on_a_profile_disagreement(self):
        """#1699"""
        import click.testing
        from data_sheets_schema.cli import runs as runs_cli
        label = "2026-07-31_claude-opus-5-api-generic_rep2"
        if not (ROOT / "data/d4d_concatenated/claudecode_agent_crate_only_core" / label / "CHORUS_provenance.yaml").exists():
            self.skipTest("the tracked record is not in this checkout")
        os.chdir(ROOT)
        from data_sheets_schema import runs as runs_lib
        real = runs_lib._prov
        def disagreeing(method, lab, proj, *a, **kw):
            data = real(method, lab, proj, *a, **kw) or {}
            return dict(data, schema=dict(data.get("schema") or {}, profile="bridge2ai"),
                        prompts={"request": {"spec": {"profile": "neutral"}}})
        with mock.patch.object(runs_lib, "_prov", disagreeing):        # the command imports it at call time
            r = click.testing.CliRunner().invoke(runs_cli.runs, ["check", "--strict", "--method", "claudecode_agent_crate_only",
                                                                 "--label", label, "--project", "CHORUS"])
        self.assertNotEqual(r.exit_code, 0); self.assertIn("two instruments", r.output)

    def test_backfill_spec_refuses_a_malformed_recorded_profile(self):
        """#1702"""
        import click.testing
        import yaml
        from data_sheets_schema import provenance as pv
        from data_sheets_schema.cli import provenance as prov_cli
        record = {"record_generated_at": "2026-09-13T12:00:00Z", "model": {"provider": "Anthropic"},
                  "schema": {"profile": ["neutral"]},
                  "inputs": {"bundle_path": "data/preprocessed/concatenated/CHORUS_preprocessed.txt", "source_manifest": {"path": None}},
                  "prompts": {"request": {"sha256": "0" * 64}}}
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "CHORUS_provenance.yaml"; path.write_text(yaml.safe_dump(record), encoding="utf-8")
            with mock.patch.object(pv, "record_path_for", return_value=path):
                r = click.testing.CliRunner().invoke(prov_cli.provenance, [
                    "backfill-spec", "--project", "CHORUS", "--method", "claudecode_api", "--label", "x",
                    "--condition", "generic_v9", "--runtime", "Claude Code"])
        self.assertEqual(r.exit_code, 1, r.output); self.assertIn("schema.profile", r.output)
        self.assertNotIsInstance(r.exception, (ValueError, TypeError))

    def test_form_defects_names_an_unknown_ambient_profile_with_a_fresh_cache(self):
        """#1703"""
        import subprocess, sys
        with tempfile.TemporaryDirectory() as d:
            r = subprocess.run([sys.executable, "-m", "data_sheets_schema.form_defects", "--offline", "--cache", str(Path(d) / "fresh.jsonl"), "--limit", "1"],
                               capture_output=True, text=True, cwd=ROOT,
                               env={**os.environ, "PYTHONPATH": str(ROOT / "src"), "D4D_PROFILE": "typo"})
        self.assertEqual(r.returncode, 2, r.stderr[-500:]); self.assertIn("unknown profile", r.stderr)
        self.assertNotIn("Traceback", r.stderr)

    def test_the_playbooks_send_the_model_to_no_prior_output(self):
        """#1706, #1707"""
        import re
        for rel in (".github/workflows/d4d_assistant_create.md", ".github/workflows/d4d_assistant_edit.md",
                    ".claude/commands/d4d-assistant.md", ".claude/commands/d4d-webfetch.md"):
            text = (ROOT / rel).read_text(encoding="utf-8")
            self.assertNotIn("data/d4d_concatenated/claudecode_agent/2026-04-10", text, rel)
            self.assertIsNone(re.search(r"\bprogramme\b", text, re.I), rel)

    def test_a_non_utf8_manifest_is_a_click_error_from_the_registry(self):
        """#1708"""
        import click
        from data_sheets_schema import schema_cache
        from data_sheets_schema.registry import load_registry
        with tempfile.TemporaryDirectory() as d:
            m = Path(d) / "m.yaml"; m.write_bytes(b"projects: {}\nnote: J\xf6rg\n"); schema_cache.clear()
            with self.assertRaises(click.ClickException):
                load_registry(m)


class TestRoundThirteen(_Clean):
    """The Claude round-7 findings (#1709–#1712)."""

    def test_a_missing_schema_block_with_a_spec_profile_is_the_split(self):
        """#1709"""
        from data_sheets_schema.provenance import _spec_profile_disagreement
        for schema in ({}, None, "x", ["x"]):
            data = {"prompts": {"request": {"spec": {"profile": "neutral"}}}}
            if schema != {}:
                data["schema"] = schema
            finding = _spec_profile_disagreement(data)
            self.assertIsNotNone(finding, repr(schema)); self.assertIn("different instruments", finding)
        self.assertIsNone(_spec_profile_disagreement({"prompts": {"request": {"spec": {}}}}))

    def test_backfill_spec_writes_into_a_null_schema_block_and_restates_a_version_one_profile(self):
        """#1710, #1711"""
        import hashlib
        import click.testing
        import yaml
        from data_sheets_schema import provenance as pv
        from data_sheets_schema.api_runner import RunSpec, resolve_prompt
        from data_sheets_schema.cli import provenance as prov_cli
        from data_sheets_schema.cli.api import ARMS
        os.environ["D4D_PROFILE"] = "neutral"
        spec = RunSpec(project="CHORUS", method=ARMS["baseline"][1], arm=ARMS["baseline"][0],
                       bundle=ROOT / "data/preprocessed/concatenated/CHORUS_preprocessed.txt",
                       label="2026-09-13_x-claudecode-generic-v9_rep1", condition="generic_v9",
                       runtime="Claude Code", provider="Anthropic", run_date="2026-09-13")
        os.environ.pop("D4D_PROFILE")
        base = {"record_generated_at": "2026-09-13T12:00:00Z", "model": {"provider": "Anthropic"},
                "inputs": {"bundle_path": str(spec.bundle), "source_manifest": {"path": str(spec.manifest)},
                           **({"chunks": {"path": str(spec.chunk_manifest)}} if spec.chunk_manifest else {})}}
        args = ["backfill-spec", "--project", "CHORUS", "--method", spec.method, "--label", spec.label,
                "--condition", "generic_v9", "--runtime", "Claude Code", "--execute"]
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "CHORUS_provenance.yaml"
            # schema: null, a version-4 instruction rendered under neutral (#1710)
            path.write_text(yaml.safe_dump(dict(base, schema=None, prompts={"request": {"sha256": hashlib.sha256(resolve_prompt(spec).encode()).hexdigest()}})), encoding="utf-8")
            with mock.patch.object(pv, "record_path_for", return_value=path):
                r = click.testing.CliRunner().invoke(prov_cli.provenance, args)
            self.assertEqual(r.exit_code, 0, r.output); self.assertNotIsInstance(r.exception, TypeError)
            written = yaml.safe_load(path.read_text(encoding="utf-8"))
            self.assertEqual(written["schema"]["profile"], "neutral")
            # a version-1 record that states a profile: restated, not verified (#1711)
            v1 = RunSpec.from_render_spec({**spec.render_spec(), "render_version": 1}, project="CHORUS", method=spec.method, label=spec.label)
            path.write_text(yaml.safe_dump(dict(base, schema={"profile": "neutral", "profile_basis": "environment"},
                                                prompts={"request": {"sha256": hashlib.sha256(resolve_prompt(v1).encode()).hexdigest()}})), encoding="utf-8")
            with mock.patch.object(pv, "record_path_for", return_value=path):
                r = click.testing.CliRunner().invoke(prov_cli.provenance, args)
            self.assertEqual(r.exit_code, 0, r.output)
            written = yaml.safe_load(path.read_text(encoding="utf-8"))
            self.assertEqual(written["prompts"]["request"]["spec"]["render_version"], 1)
            self.assertIn("render version 1 does not hash the profile", written["prompts"]["request"]["spec_basis"])

    def test_runs_validate_names_an_unknown_ambient_profile(self):
        """#1711 (the `runs validate` wrap)"""
        import click.testing
        from data_sheets_schema.cli import runs as runs_cli
        label = "2026-07-31_claude-opus-5-api-generic_rep2"
        if not (ROOT / "data/d4d_concatenated/claudecode_agent_crate_only_core" / label / "CHORUS_provenance.yaml").exists():
            self.skipTest("the tracked record is not in this checkout")
        os.chdir(ROOT); os.environ["D4D_PROFILE"] = "typo"
        r = click.testing.CliRunner().invoke(runs_cli.runs, ["validate", "--recheck", "--method", "claudecode_agent_crate_only", "--label", label, "--project", "CHORUS"])
        self.assertNotIsInstance(r.exception, ValueError, r.output)
        self.assertIn("unknown profile", r.output)

    def test_a_window_pin_is_refused_with_the_cause(self):
        """#1712: a pin with the profile key beside an instruction hashed without `--profile`."""
        import hashlib
        from data_sheets_schema.api_runner import RunSpec, resolve_prompt
        from data_sheets_schema.cli.api import ARMS
        from data_sheets_schema.usage_ledger import _identity_differs, identity_refusal, pre_profile_pin
        spec = RunSpec(project="CHORUS", method=ARMS["baseline"][1], arm=ARMS["baseline"][0],
                       bundle=ROOT / "data/preprocessed/concatenated/CHORUS_preprocessed.txt",
                       label="2026-09-13_x-claudecode-generic-v9_rep1", condition="generic_v9",
                       runtime="Claude Code", provider="Anthropic", run_date="2026-09-13", profile="bridge2ai")
        current = spec.input_identity()
        old_dict = {k: v for k, v in spec.render_spec().items() if k not in ("profile", "profile_basis")}
        old = RunSpec.from_render_spec(old_dict, project="CHORUS", method=spec.method, label=spec.label)
        window = dict(current, instruction={"render_version": old.render_version, "spec": old_dict,
                                            "sha256": hashlib.sha256(resolve_prompt(old).encode()).hexdigest()})
        self.assertIn("profile", window)
        self.assertTrue(_identity_differs(window, current)); self.assertTrue(pre_profile_pin(window))
        self.assertIn("cannot be resumed", identity_refusal(window, "x"))
        self.assertFalse(pre_profile_pin(current))

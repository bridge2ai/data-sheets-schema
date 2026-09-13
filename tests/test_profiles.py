"""Study text and vocabularies sit behind a profile (#628, #1302).

The study profile renders the vocabulary its runs have always seen; the
neutral profile renders only what the schema itself declares; and what the
model is *sent* — the assembled full-phase request — is what is asserted,
not a helper.
"""
from __future__ import annotations

import os
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
            self.assertEqual(sel.basis, f"manifest:{m.as_posix()}")
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
        self.assertEqual(select_profile(STUDY_MANIFEST).basis, f"manifest:{STUDY_MANIFEST.as_posix()}")
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
            self.assertEqual(sel.basis, f"default manifest:{STUDY_MANIFEST.as_posix()}")
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
        self.assertEqual(study.profile_basis, "manifest:data/preprocessed/source_manifest.yaml")
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

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

    def test_the_study_facts_are_the_profiles(self):
        from data_sheets_schema import agreement, healthsheet
        from data_sheets_schema.profiles import BRIDGE2AI
        self.assertEqual(agreement.DEFAULT_PROJECTS, ("AI_READI", "CHORUS", "CM4AI", "VOICE"))
        self.assertEqual(healthsheet.BUNDLE_NAME, "AI_READI_healthsheet_only.txt")
        self.assertIs(agreement.DEFAULT_PROJECTS, BRIDGE2AI.agreement_projects)


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

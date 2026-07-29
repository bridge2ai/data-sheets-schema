"""Tests for the API generation path.

Everything here runs without an API key. The point of `plan()` is that the
whole assembly — prompt resolution, cache layout, cost — is inspectable before
anything is billed, so the tests exercise exactly what a real run would send.
"""

import unittest
from pathlib import Path

from data_sheets_schema import schema_digest
from data_sheets_schema.api_runner import (
    GENERIC_PROMPT,
    PHASES,
    RUNTIME,
    RunSpec,
    build_phase,
    plan,
    resolve_prompt,
)

BUNDLE = Path("data/preprocessed/concatenated/CHORUS_preprocessed.txt")


def spec(**kw):
    base = dict(project="CHORUS", arm="BASELINE (input documents only)",
                method="claudecode_agent", bundle=BUNDLE,
                label="2026-07-29_claude-opus-5-api-generic_rep1")
    base.update(kw)
    return RunSpec(**base)


class TestSchemaDigest(unittest.TestCase):
    def test_digest_is_far_smaller_than_the_schema(self):
        s = schema_digest.stats("Dataset")
        self.assertGreater(s["reduction"], 0.9,
                           "digest must be a large reduction to be worth using")
        self.assertGreater(s["slots"], 50)

    def test_core_class_resolves_to_the_core_schema(self):
        """CoreDataset does not exist in the full merged schema."""
        d = schema_digest.build("CoreDataset")
        self.assertIn("core", d.schema_path)
        self.assertTrue(d.slots)

    def test_unknown_class_is_an_error_not_a_guess(self):
        with self.assertRaises(ValueError):
            schema_digest.build("NoSuchClass")

    def test_digest_carries_no_dataset_facts(self):
        """It states structure. Content would breach the provenance boundary."""
        text = schema_digest.digest_text("Dataset").lower()
        for leak in ("chorus", "cm4ai", "ai-readi", "physionet", "b2ai"):
            self.assertNotIn(leak, text)

    def test_fingerprint_is_stable_and_content_sensitive(self):
        a = schema_digest.digest_text("Dataset")
        self.assertEqual(schema_digest.fingerprint(a),
                         schema_digest.fingerprint(a))
        self.assertNotEqual(schema_digest.fingerprint(a),
                            schema_digest.fingerprint(a + " "))


class TestPromptResolution(unittest.TestCase):
    def test_no_placeholders_survive(self):
        text = resolve_prompt(spec())
        for token in ("{PROJECT}", "{ARM}", "{METHOD}", "{BUNDLE}",
                      "{LABEL}", "{MANIFEST_LINE}"):
            self.assertNotIn(token, text)

    def test_generic_prompt_differs_between_projects_only_mechanically(self):
        a = resolve_prompt(spec(project="CHORUS")).splitlines()
        b = resolve_prompt(spec(
            project="VOICE",
            bundle=Path("data/preprocessed/concatenated/VOICE_preprocessed.txt")
        )).splitlines()
        self.assertEqual(len(a), len(b))
        differing = [(x, y) for x, y in zip(a, b) if x != y]
        for x, y in differing:
            self.assertTrue(
                "CHORUS" in x and "VOICE" in y,
                f"non-mechanical difference between projects: {x!r} vs {y!r}")

    def test_tuned_adds_the_component_block_and_nothing_else(self):
        g = resolve_prompt(spec(project="VOICE", condition="generic",
                                bundle=Path("data/preprocessed/concatenated/VOICE_preprocessed.txt")))
        t = resolve_prompt(spec(project="VOICE", condition="tuned",
                                bundle=Path("data/preprocessed/concatenated/VOICE_preprocessed.txt")))
        self.assertGreater(len(t), len(g))
        self.assertIn("pediatric", t)
        self.assertNotIn("pediatric", g)

    def test_tuned_declares_its_components_in_the_header(self):
        t = resolve_prompt(spec(project="VOICE", condition="tuned",
                                bundle=Path("data/preprocessed/concatenated/VOICE_preprocessed.txt")))
        self.assertIn("tuned prompt", t)
        self.assertIn("components/VOICE.md", t)

    def test_prompt_files_reflect_the_condition(self):
        self.assertEqual(spec().prompt_files, [GENERIC_PROMPT])
        self.assertEqual(len(spec(condition="tuned").prompt_files), 3)


class TestPhaseAssembly(unittest.TestCase):
    def test_every_phase_caches_the_bundle_and_digest(self):
        for ph in PHASES:
            req = build_phase(spec(), ph, carry={})
            self.assertEqual(len(req.cached_blocks), 2, ph)
            for b in req.cached_blocks:
                self.assertEqual(b["cache_control"]["type"], "ephemeral")

    def test_core_phase_uses_the_core_class_digest(self):
        req = build_phase(spec(), "core", carry={})
        self.assertIn("CoreDataset", req.cached_blocks[0]["text"])

    def test_other_phases_use_the_full_class_digest(self):
        for ph in ("full", "audit", "reconcile"):
            req = build_phase(spec(), ph, carry={})
            self.assertIn("`Dataset`", req.cached_blocks[0]["text"], ph)

    def test_system_prompt_states_the_evidence_boundary(self):
        req = build_phase(spec(), "full", carry={})
        self.assertIn("only source of dataset facts", req.system)
        self.assertIn("never consult a previously generated", req.system.lower())

    def test_carry_forward_is_included_when_supplied(self):
        req = build_phase(spec(), "core", carry={"Completed full record": "id: x"})
        blob = " ".join(p["text"] for p in req.messages[0]["content"])
        self.assertIn("Completed full record", blob)

    def test_unknown_phase_rejected(self):
        with self.assertRaises(ValueError):
            build_phase(spec(), "nonsense", carry={})


class TestPlan(unittest.TestCase):
    def test_plan_needs_no_api_key(self):
        p = plan(spec())
        self.assertEqual(p["runtime"], RUNTIME)
        self.assertEqual(len(p["phases"]), len(PHASES))

    def test_plan_reports_the_shared_config_model(self):
        p = plan(spec())
        self.assertEqual(p["model"]["name"], "claude-opus-5")
        self.assertEqual(p["model"]["temperature"], 0.0)

    def test_plan_output_paths_follow_the_run_layout(self):
        p = plan(spec())
        self.assertTrue(p["outputs"]["full"].endswith("CHORUS_d4d.yaml"))
        self.assertIn("claudecode_agent_core", p["outputs"]["core"])
        self.assertIn(spec().label, p["outputs"]["report"])

    def test_token_estimate_scales_with_the_bundle(self):
        small = plan(spec())["approx_total_input_tokens"]
        big = plan(spec(
            project="VOICE",
            bundle=Path("data/preprocessed/concatenated/VOICE_preprocessed.txt")
        ))["approx_total_input_tokens"]
        self.assertGreater(big, small * 2)


if __name__ == "__main__":
    unittest.main()

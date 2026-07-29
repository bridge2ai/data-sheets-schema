"""Tests for the API generation path.

Everything here runs without an API key. The point of `plan()` is that the
whole assembly — prompt resolution, cache layout, cost — is inspectable before
anything is billed, so the tests exercise exactly what a real run would send.
"""

import json
import unittest
from pathlib import Path

from data_sheets_schema import schema_digest
from data_sheets_schema.api_runner import (
    GENERIC_PROMPT,
    PHASE_INSTRUCTIONS,
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
        for ph in ("full", "audit", "reconcile_full", "report"):
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


class FakeUsage:
    input_tokens = 100
    output_tokens = 50
    cache_read_input_tokens = 0
    cache_creation_input_tokens = 100


class FakeBlock:
    type = "text"

    def __init__(self, text):
        self.text = text


class FakeResponse:
    def __init__(self, text):
        self.content = [FakeBlock(text)]
        self.usage = FakeUsage()


class FakeMessages:
    """Returns a plausible payload per phase, keyed by the instruction sent."""

    def __init__(self, fail_on=None, exc=None):
        self.calls = []
        self.fail_on, self.exc = fail_on, exc

    def create(self, **kw):
        self.calls.append(kw)
        blob = " ".join(p.get("text", "") for p in kw["messages"][0]["content"])
        # Match the actual instruction text. Substring-matching "Phase 3" fails:
        # the prompt body itself enumerates all four playbook phases, so every
        # request contains every phase number.
        phase = next((ph for ph, instr in PHASE_INSTRUCTIONS.items()
                      if instr in blob), None)
        if phase is None:
            raise AssertionError("could not identify the phase from the request")
        if self.fail_on == phase:
            raise self.exc or RuntimeError("boom")
        if phase == "audit":
            return FakeResponse('{"findings": [], "summary": "none"}')
        if phase == "report":
            return FakeResponse("# Reconciliation\nNo discrepancies.\n")
        return FakeResponse(f"```yaml\n# {phase}\nid: x\nname: X\n```")


class FakeClient:
    def __init__(self):
        self.messages = FakeMessages()


class TestExecuteOffline(unittest.TestCase):
    """Exercise execute() without the API.

    plan() alone cannot catch this class of bug: execute() imports inside the
    function body, so a wrong import name survives every plan-based test and
    only surfaces on a live run. That is exactly what happened — `record_path`
    was imported from `provenance`, where it does not exist.
    """

    def setUp(self):
        import tempfile
        from data_sheets_schema import api_runner
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = Path(self.tmp.name) / "out"
        self.api = api_runner
        self._client = api_runner._client
        api_runner._client = lambda: FakeClient()
        self.addCleanup(lambda: setattr(api_runner, "_client", self._client))

    def test_execute_writes_every_artifact(self):
        s = spec(out_dir=self.out)
        res = self.api.execute(s)
        for p in (s.full_path, s.core_path, s.report_path):
            self.assertTrue(p.exists(), f"missing {p}")
        self.assertTrue((self.out / "CHORUS_d4d_metadata.yaml").exists(),
                        "provenance record not written")
        self.assertEqual(len(res["usage"]), 6)

    def test_progress_file_is_removed_on_success(self):
        s = spec(out_dir=self.out)
        self.api.execute(s)
        self.assertFalse(self.api._progress_path(s).exists(),
                         "a completed run must not leave resume state behind")

    def test_provenance_record_is_live_and_names_the_prompt(self):
        import yaml as _yaml
        s = spec(out_dir=self.out)
        self.api.execute(s)
        d = _yaml.safe_load((self.out / "CHORUS_d4d_metadata.yaml").read_text())
        self.assertEqual(d["record_mode"], "live")
        self.assertEqual(d["model"]["agent_runtime"], RUNTIME)
        # claude-opus-5 rejects `temperature`, so the record must say the
        # parameter does not apply rather than restate an inert config value.
        self.assertEqual(d["model"]["temperature_basis"],
                         "not applicable to this model")
        self.assertIsNone(d["model"]["temperature"])
        self.assertTrue(any(u["field"] == "model.temperature"
                            for u in (d.get("unverified") or [])))
        self.assertEqual(len(d["prompts"]["files"]), 1)
        self.assertEqual(len(d["prompts"]["files"][0]["sha256"]), 64)
        self.assertEqual(len(d["api_usage"]), 6)

    def test_every_phase_sends_the_cached_prefix(self):
        s = spec(out_dir=self.out)
        client = FakeClient()
        self.api._client = lambda: client
        self.api.execute(s)
        self.assertEqual(len(client.messages.calls), 6)
        for kw in client.messages.calls:
            parts = kw["messages"][0]["content"]
            cached = [p for p in parts if p.get("cache_control")]
            self.assertEqual(len(cached), 2)
            # temperature must be absent for models that reject it
            self.assertNotIn("temperature", kw)
            self.assertEqual(kw["model"], "claude-opus-5")
            # every phase must be given a limit large enough for its artifact
            self.assertGreaterEqual(kw["max_tokens"], 12000)


class TestResumeAndRetry(unittest.TestCase):
    """A six-phase run costs real money; a failure must not discard the rest."""

    def setUp(self):
        import tempfile
        from data_sheets_schema import api_runner
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = Path(self.tmp.name) / "out"
        self.api = api_runner

    def test_failure_midway_keeps_completed_artifacts(self):
        s = spec(out_dir=self.out)
        client = FakeClient()
        client.messages = FakeMessages(fail_on="reconcile_core")
        with self.assertRaises(RuntimeError):
            self.api.execute(s, client=client)
        self.assertTrue(s.full_path.exists(), "phase 1 output was discarded")
        self.assertTrue(s.core_path.exists(), "phase 2 output was discarded")
        self.assertTrue(self.api._progress_path(s).exists(),
                        "no resume state written")

    def test_resume_skips_completed_phases(self):
        s = spec(out_dir=self.out)
        first = FakeClient(); first.messages = FakeMessages(fail_on="report")
        with self.assertRaises(RuntimeError):
            self.api.execute(s, client=first)
        done_first = len(first.messages.calls)

        second = FakeClient()
        res = self.api.execute(s, client=second)
        self.assertLess(len(second.messages.calls), done_first,
                        "resume re-ran work that was already paid for")
        self.assertTrue(res["skipped"], "nothing reported as skipped")
        self.assertTrue(s.report_path.exists())

    def test_resume_false_redoes_everything(self):
        s = spec(out_dir=self.out)
        self.api.execute(s, client=FakeClient())
        again = FakeClient()
        self.api.execute(s, client=again, resume=False)
        self.assertEqual(len(again.messages.calls), 6)

    def test_corrupt_progress_file_is_ignored_not_fatal(self):
        s = spec(out_dir=self.out)
        p = self.api._progress_path(s)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("{not json", encoding="utf-8")
        res = self.api.execute(s, client=FakeClient())
        self.assertEqual(len(res["usage"]), 6)

    def test_truncated_output_raises_rather_than_writing(self):
        """A truncated record can validate while being silently incomplete."""
        class Truncated(FakeResponse):
            def __init__(self, text):
                super().__init__(text)
                self.stop_reason = "max_tokens"

        class TruncMessages(FakeMessages):
            def create(self, **kw):
                super().create(**kw)
                return Truncated("```yaml\nid: x\n```")

        s = spec(out_dir=self.out)
        client = FakeClient(); client.messages = TruncMessages()
        with self.assertRaises(RuntimeError) as ctx:
            self.api.execute(s, client=client)
        self.assertIn("max_tokens", str(ctx.exception))
        self.assertFalse(s.full_path.exists(), "truncated record was written")

    def test_transient_errors_are_retried(self):
        import anthropic
        calls = {"n": 0}

        def flaky(**kw):
            calls["n"] += 1
            if calls["n"] < 3:
                raise anthropic.APIConnectionError(request=None)
            return FakeResponse("```yaml\nid: x\n```")

        client = FakeClient()
        client.messages.create = flaky
        out = self.api._call_with_retry(
            client, model="m", max_tokens=100, temperature=0.0,
            system="s", messages=[{"role": "user", "content": []}],
            sleep=lambda _: None)
        self.assertEqual(calls["n"], 3)
        self.assertIsNotNone(out)

    def test_auth_errors_are_not_retried(self):
        """An invalid key fails identically every time; retrying just delays it."""
        calls = {"n": 0}

        def bad_key(**kw):
            calls["n"] += 1
            err = Exception("invalid x-api-key")
            err.status_code = 401
            raise err

        client = FakeClient()
        client.messages.create = bad_key
        with self.assertRaises(Exception):
            self.api._call_with_retry(
                client, model="m", max_tokens=100, temperature=0.0,
                system="s", messages=[{"role": "user", "content": []}],
                sleep=lambda _: None)
        self.assertEqual(calls["n"], 1)

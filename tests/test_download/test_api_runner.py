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
                      "{LABEL}", "{MANIFEST_LINE}", "{RUNTIME}",
                      "{PROVIDER}", "{MODEL}"):
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

    def test_header_states_the_real_runtime_not_a_hardcoded_one(self):
        """The first live API run emitted "Agent runtime: Claude Code"."""
        from data_sheets_schema.api_runner import RUNTIME
        t = resolve_prompt(spec())
        self.assertIn(f"# Agent runtime: {RUNTIME}", t)
        self.assertNotIn("# Agent runtime: Claude Code", t)
        self.assertNotIn("claude-opus-5[1m]", t)

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
        """Whatever the config pins is what a run will use."""
        from data_sheets_schema.provenance import load_generation_config
        pinned = (load_generation_config().get("model") or {}).get("name")
        p = plan(spec())
        self.assertEqual(p["model"]["name"], pinned)

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

    def stream(self, **kw):
        """Mirror the SDK's streaming context manager.

        The runner streams because the SDK refuses a non-streaming request whose
        max_tokens implies a >10-minute response. Errors must surface on
        __enter__ so retry and failure paths behave as they do live.
        """
        outer = self

        class _Stream:
            def __enter__(self):
                self._msg = outer.create(**kw)
                return self

            def __exit__(self, *exc):
                return False

            def get_final_message(self):
                return self._msg

        return _Stream()


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
        self.assertTrue((self.out / "CHORUS_provenance.yaml").exists(),
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
        d = _yaml.safe_load((self.out / "CHORUS_provenance.yaml").read_text())
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
            from data_sheets_schema.api_runner import output_limit
            self.assertLessEqual(kw["max_tokens"], output_limit(kw["model"]),
                                 "a phase must not request more output than "
                                 "the route allows")
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


class TestMetadataPlacementIsUnified(unittest.TestCase):
    """One filename and one placement rule for a run's metadata.

    There used to be three: provenance named `_provenance.yaml` in the study
    layout but `_d4d_metadata.yaml` in the assistant layout, and the progress
    file landing beside the *full* record while provenance landed in the
    `_core` directory. That cost real time — run state was misread twice while
    watching the first live run.
    """

    def test_provenance_sits_with_the_report_in_study_layout(self):
        s = spec()
        self.assertEqual(s.provenance_path.parent, s.report_path.parent)
        self.assertTrue(s.provenance_path.name.endswith("_provenance.yaml"))

    def test_provenance_sits_with_the_report_in_assistant_layout(self):
        s = spec(out_dir=Path("data/sheets_d4dassistant"))
        self.assertEqual(s.provenance_path.parent, s.report_path.parent)
        self.assertTrue(s.provenance_path.name.endswith("_provenance.yaml"))

    def test_filename_is_identical_across_layouts(self):
        self.assertEqual(spec().provenance_path.name,
                         spec(out_dir=Path("x")).provenance_path.name)

    def test_progress_shares_the_metadata_directory(self):
        from data_sheets_schema.api_runner import _progress_path
        for s in (spec(), spec(out_dir=Path("data/sheets_d4dassistant"))):
            self.assertEqual(_progress_path(s).parent, s.metadata_dir)

    def test_old_assistant_filename_is_gone(self):
        for s in (spec(), spec(out_dir=Path("x"))):
            self.assertNotIn("_d4d_metadata", str(s.provenance_path))

    def test_assistant_config_declares_the_aligned_name(self):
        from data_sheets_schema.provenance import load_generation_config
        pat = ((load_generation_config().get("output") or {})
               .get("metadata_filename_pattern", ""))
        self.assertIn("_provenance.yaml", pat)


class TestOutputValidation(unittest.TestCase):
    """A run must not report success on a record that fails validation.

    The first live run completed six phases, exited 0 and printed a tick while
    emitting a full record whose five DataSubsets lacked required ids and a core
    record carrying slots CoreDataset does not accept.
    """

    def test_reconcile_core_is_shown_the_core_schema(self):
        """The bug that produced the invalid core record."""
        req = build_phase(spec(), "reconcile_core", carry={})
        self.assertIn("CoreDataset", req.cached_blocks[0]["text"])
        self.assertNotIn("`Dataset` — slot inventory",
                         req.cached_blocks[0]["text"])

    def test_digest_states_required_keys_of_object_ranges(self):
        """DataSubset requires `id`; the digest must say so."""
        d = schema_digest.build("Dataset")
        by_name = {n.name: n for n in d.nested}
        self.assertIn("DataSubset", by_name)
        self.assertIn("id", by_name["DataSubset"].required)
        self.assertIn("Object ranges — required keys",
                      schema_digest.digest_text("Dataset"))

    def test_missing_artifact_is_reported_as_a_problem(self):
        import tempfile
        from data_sheets_schema.api_runner import validate_outputs
        with tempfile.TemporaryDirectory() as td:
            problems = validate_outputs(spec(out_dir=Path(td)))
        self.assertTrue(problems)
        self.assertTrue(any(p["error"] == "missing" for p in problems))


class TestTransportErrorsAreRetried(unittest.TestCase):
    """Mid-stream connection drops must retry, not abort the run.

    The second live CHORUS run died in phase 1 on
    `httpx.RemoteProtocolError: peer closed connection without sending complete
    message body`. It was never retried: the classifier only recognised
    anthropic's own exception classes, and a raw httpx transport error is not
    wrapped in one when it surfaces mid-stream. Streaming a 64k-token response
    through a proxy is a long-lived connection, so this is an expected failure
    mode rather than a fluke.
    """

    def _flaky(self, exc, fail_times):
        calls = {"n": 0}

        class C:
            class messages:
                @staticmethod
                def create(**kw):
                    calls["n"] += 1
                    if calls["n"] <= fail_times:
                        raise exc
                    return FakeResponse("ok")

                @classmethod
                def stream(cls, **kw):
                    outer = cls

                    class _S:
                        def __enter__(self):
                            self._m = outer.create(**kw)
                            return self

                        def __exit__(self, *e):
                            return False

                        def get_final_message(self):
                            return self._m
                    return _S()
        return C(), calls

    def test_remote_protocol_error_is_retried(self):
        import httpx
        from data_sheets_schema.api_runner import _call_with_retry
        exc = httpx.RemoteProtocolError(
            "peer closed connection without sending complete message body")
        client, calls = self._flaky(exc, fail_times=2)
        out = _call_with_retry(client, model="claude-opus-5", max_tokens=10,
                               temperature=None, system="s", messages=[],
                               sleep=lambda _: None)
        self.assertEqual(calls["n"], 3)
        self.assertIsNotNone(out)

    def test_read_timeout_is_retried(self):
        import httpx
        from data_sheets_schema.api_runner import _call_with_retry
        client, calls = self._flaky(httpx.ReadTimeout("slow"), fail_times=1)
        _call_with_retry(client, model="claude-opus-5", max_tokens=10,
                         temperature=None, system="s", messages=[],
                         sleep=lambda _: None)
        self.assertEqual(calls["n"], 2)

    def test_a_persistent_transport_error_still_gives_up(self):
        import httpx
        from data_sheets_schema.api_runner import _call_with_retry, MAX_ATTEMPTS
        client, calls = self._flaky(httpx.ConnectError("down"), fail_times=99)
        with self.assertRaises(httpx.ConnectError):
            _call_with_retry(client, model="claude-opus-5", max_tokens=10,
                             temperature=None, system="s", messages=[],
                             sleep=lambda _: None)
        self.assertEqual(calls["n"], MAX_ATTEMPTS)

    def test_a_bad_request_is_not_retried(self):
        """400s are deterministic; retrying only delays the real error."""
        from data_sheets_schema.api_runner import _call_with_retry
        err = Exception("`temperature` is deprecated for this model")
        err.status_code = 400
        client, calls = self._flaky(err, fail_times=99)
        with self.assertRaises(Exception):
            _call_with_retry(client, model="claude-opus-5", max_tokens=10,
                             temperature=None, system="s", messages=[],
                             sleep=lambda _: None)
        self.assertEqual(calls["n"], 1)


class TestMidStreamErrorClassification(unittest.TestCase):
    """Errors that arrive inside a 200 stream, not as an HTTP status.

    The SDK opens the stream, gets a 200, then receives an SSE `error` event and
    raises APIStatusError carrying the *stream's* status — 200. So the 5xx check
    never fires and an obviously transient `overloaded_error` was killing runs
    on the first attempt. Classification has to read the error body.
    """

    def _err(self, body, status=200):
        class MidStream(Exception):
            def __init__(self):
                self.body = body
                self.status_code = status

            def __str__(self):
                return str(body)
        return MidStream()

    def test_overloaded_error_nested_in_body_is_transient(self):
        from data_sheets_schema.api_runner import _transient_error_type
        exc = self._err({"type": "error",
                         "error": {"type": "overloaded_error",
                                   "message": "Overloaded"}})
        self.assertEqual(_transient_error_type(exc), "overloaded_error")

    def test_overloaded_error_flat_in_body_is_transient(self):
        from data_sheets_schema.api_runner import _transient_error_type
        self.assertEqual(
            _transient_error_type(self._err({"type": "overloaded_error"})),
            "overloaded_error")

    def test_message_text_is_the_fallback(self):
        """Covers SDK versions that attach no parsed body to a stream error."""
        from data_sheets_schema.api_runner import _transient_error_type
        self.assertEqual(
            _transient_error_type(Exception("{'type': 'overloaded_error'}")),
            "overloaded_error")

    def test_client_errors_stay_non_transient(self):
        from data_sheets_schema.api_runner import _transient_error_type
        for kind in ("invalid_request_error", "authentication_error",
                     "permission_error", "not_found_error"):
            with self.subTest(kind=kind):
                exc = self._err({"error": {"type": kind}}, status=400)
                self.assertIsNone(_transient_error_type(exc))

    def test_overloaded_stream_error_is_actually_retried(self):
        from data_sheets_schema.api_runner import _call_with_retry
        exc = self._err({"type": "error",
                         "error": {"type": "overloaded_error"}})
        calls = {"n": 0}

        class C:
            class messages:
                @staticmethod
                def stream(**kw):
                    calls["n"] += 1
                    if calls["n"] <= 2:
                        raise exc

                    class S:
                        def __enter__(s):
                            return s

                        def __exit__(s, *e):
                            return False

                        def get_final_message(s):
                            class M:
                                content = []
                                stop_reason = "end_turn"
                                usage = None
                            return M()
                    return S()

        out = _call_with_retry(C(), model="claude-opus-5", max_tokens=10,
                               temperature=None, system="s", messages=[],
                               sleep=lambda _: None)
        self.assertEqual(calls["n"], 3)
        self.assertIsNotNone(out)


class TestErrorBodyIsAuthoritative(unittest.TestCase):
    """A stated non-transient type must not be overridden by message text (#182).

    D4D requests carry dataset prose, so an error echoing back offending content
    can contain almost any token. Falling through to substring matching let a
    deterministic 400 be retried MAX_ATTEMPTS times.
    """

    def _exc(self, inner_type, message="", status=400):
        class E(Exception):
            def __init__(s):
                s.body = {"type": "error",
                          "error": {"type": inner_type, "message": message}}
                s.status_code = status

            def __str__(s):
                return str(s.body)
        return E()

    def test_text_cannot_promote_a_declared_client_error(self):
        from data_sheets_schema.api_runner import _transient_error_type
        exc = self._exc("invalid_request_error",
                        "field 'notes' contains: retry on overloaded_error")
        self.assertIsNone(_transient_error_type(exc))

    def test_declared_transient_type_still_retries(self):
        from data_sheets_schema.api_runner import _transient_error_type
        self.assertEqual(_transient_error_type(self._exc("overloaded_error")),
                         "overloaded_error")

    def test_text_fallback_survives_for_bodyless_errors(self):
        from data_sheets_schema.api_runner import _transient_error_type
        self.assertEqual(
            _transient_error_type(Exception("{'type': 'overloaded_error'}")),
            "overloaded_error")

    def test_bare_error_envelope_falls_through_to_text(self):
        """{"type": "error"} names no condition, so it must not short-circuit."""
        from data_sheets_schema.api_runner import _transient_error_type

        class E(Exception):
            body = {"type": "error"}

            def __str__(self):
                return "overloaded_error happened"
        self.assertEqual(_transient_error_type(E()), "overloaded_error")

    def test_a_declared_400_is_not_retried_end_to_end(self):
        from data_sheets_schema.api_runner import _call_with_retry
        exc = self._exc("invalid_request_error", "quotes overloaded_error")
        calls = {"n": 0}

        class C:
            class messages:
                @staticmethod
                def stream(**kw):
                    calls["n"] += 1
                    raise exc

        with self.assertRaises(Exception):
            _call_with_retry(C(), model="claude-opus-5", max_tokens=10,
                             temperature=None, system="s", messages=[],
                             sleep=lambda _: None)
        self.assertEqual(calls["n"], 1, "must fail fast, not retry five times")

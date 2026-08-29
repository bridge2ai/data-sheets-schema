"""Tests for the API generation path.

Everything here runs without an API key. The point of `plan()` is that the
whole assembly — prompt resolution, cache layout, cost — is inspectable before
anything is billed, so the tests exercise exactly what a real run would send.
"""

import json
import re
import time
import unittest

import yaml
import unittest.mock
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
        """It states structure. Content would breach the provenance boundary.

        `b2ai` was narrowed to `b2ai-voice` on 2026-08-13. The bare token was a
        proxy for dataset-specific leakage and now also matches
        `B2AI_SUBSTRATE` / `B2AI_TOPIC`, the registry *vocabulary* names that
        #538 renders. A controlled vocabulary is structure — it says what kinds
        of value a slot admits, never what any dataset contains — so matching
        it here would fail the test for doing the right thing.

        The dataset-specific forms are still forbidden, and the companion test
        below asserts the vocabulary names *are* present, so this exemption
        cannot widen silently into one that lets a real fact through.
        """
        text = schema_digest.digest_text("Dataset").lower()
        for leak in ("chorus", "cm4ai", "ai-readi", "physionet", "b2ai-voice",
                     "aireadi", "fairhub"):
            with self.subTest(leak=leak):
                self.assertNotIn(leak, text)

    def test_the_registry_vocabulary_names_are_structure_not_facts(self):
        """The exemption above, stated positively so it is visible.

        `B2AI_SUBSTRATE:11 = DICOM` names a kind of data any dataset might
        hold. It is the same category of statement as an enum's permitted
        values, which the digest has always carried.
        """
        text = schema_digest.digest_text("Dataset")
        self.assertIn("B2AI_SUBSTRATE", text)
        self.assertIn("B2AI_TOPIC", text)
        # And no dataset is named alongside them.
        for line in text.splitlines():
            if "B2AI_" in line:
                with self.subTest(line=line[:60]):
                    self.assertNotIn("AI-READI", line)
                    self.assertNotIn("CHORUS", line)

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
    def test_every_phase_caches_the_bundle_digest_and_ranking(self):
        """Asserted by content, not by count.

        A literal `2` broke when #596 added the source ranking — a test about
        *what* is cached failing because of *how many*. What matters is that
        each block is per-project input that does not change between phases,
        and that all of them are marked ephemeral.
        """
        for ph in PHASES:
            req = build_phase(spec(), ph, carry={})
            texts = [b["text"] for b in req.cached_blocks]
            with self.subTest(phase=ph):
                self.assertTrue(any("Declared input bundle" in t for t in texts))
                self.assertTrue(any("Declared source ranking" in t
                                    for t in texts))
                # the digest block leads, and names the class it describes
                self.assertTrue(texts[0].strip())
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
        req = build_phase(spec(), "core", carry={"Completed full record": "id: x\ntitle: T\nname: n\ndescription: d\nkeywords: [a]"})
        blob = " ".join(p["text"] for p in req.messages[0]["content"])
        self.assertIn("Completed full record", blob)

    def test_instruction_is_the_last_part_so_carry_never_trails(self):
        # #346: when the carried full record was the final content block, the
        # message ended with a large YAML document and the model continued it
        # instead of answering — ten consecutive core attempts on AI-READI
        # returned a mid-record fragment. The instruction must come last.
        for ph, carry in (
                ("core", {"Completed full record": "id: x\n"}),
                ("reconcile_core", {"Reconciled full record": "id: x\n",
                                    "Completed core record": "id: y\n",
                                    "Audit findings": "{}"}),
                ("report", {"Audit findings": "{}"})):
            req = build_phase(spec(), ph, carry=carry)
            self.assertEqual(req.messages[0]["content"][-1]["text"],
                             PHASE_INSTRUCTIONS[ph], ph)

    def test_audit_and_reconcile_demand_schema_shape_conformance(self):
        # #356: the AI-READI v3 audit saw evidence problems but no phase saw
        # shape problems, and reconciliation introduced one while repairing an
        # audited omission. The audit must ask for shape findings, and both
        # reconcile phases must be told a repair may not break shape.
        self.assertIn("shape", PHASE_INSTRUCTIONS["audit"])
        self.assertIn("schema digest", PHASE_INSTRUCTIONS["audit"])
        for ph in ("reconcile_full", "reconcile_core"):
            self.assertIn("conform to the schema digest",
                          PHASE_INSTRUCTIONS[ph], ph)

    def test_carry_instructions_say_above_not_below(self):
        # The instruction follows the carry, so any instruction describing a
        # carried artifact's position must say "above". "Below" would point at
        # nothing and invite exactly the confusion #346 documents.
        for ph, instr in PHASE_INSTRUCTIONS.items():
            self.assertNotIn("supplied below", instr, ph)

    def test_unknown_phase_rejected(self):
        with self.assertRaises(ValueError):
            build_phase(spec(), "nonsense", carry={})


class TestPlan(unittest.TestCase):
    def test_plan_needs_no_api_key(self):
        p = plan(spec())
        self.assertEqual(p["runtime"], RUNTIME)
        from data_sheets_schema.api_runner import DERIVED_PHASES
        # Only phases that make a call are costed (#694).
        self.assertEqual(len(p["phases"]), len(PHASES) - len(DERIVED_PHASES))

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

    def test_plan_does_not_cost_the_derived_phases(self):
        """#704 review F4: a phase that makes no call must not be estimated."""
        from data_sheets_schema.api_runner import DERIVED_PHASES, plan
        p = plan(spec())
        costed = {row["phase"] for row in p.get("phases", [])} if isinstance(p.get("phases"), list) else set(p.get("phases", {}))
        self.assertFalse(costed & DERIVED_PHASES, costed)

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



def _rate_limit_error(message: str):
    """A real `anthropic.RateLimitError`; the SDK needs an httpx response."""
    import anthropic
    import httpx
    req = httpx.Request("POST", "https://example.invalid/v1/messages")
    resp = httpx.Response(429, request=req, json={"error": {"message": message}})
    return anthropic.RateLimitError(message, response=resp, body=None)


class TestTemporalValuesAreNormalisedOnWrite(unittest.TestCase):
    """#215. Two failures were showing up as one.

    `issued: 2026-05-01T00:00:00Z` is a *correct* RFC 3339 value that the
    validator rejects, because unquoted YAML hands it a `datetime` object where
    a string is required — the generator was right and the serialisation lost
    it. `issued: '2026-06-30'` is genuinely wrong. Quoting plus shaping to the
    slot's declared range fixes both.
    """

    def _n(self, text):
        from data_sheets_schema.api_runner import normalise_temporal
        return normalise_temporal(text)

    def test_a_correct_but_unquoted_value_is_quoted(self):
        self.assertEqual(self._n("issued: 2026-05-01T00:00:00Z"),
                         "issued: '2026-05-01T00:00:00Z'")

    def test_a_naive_datetime_gains_a_zone(self):
        self.assertEqual(self._n("issued: '2026-05-01T00:00:00'"),
                         "issued: '2026-05-01T00:00:00Z'")

    def test_a_date_in_a_datetime_slot_is_widened(self):
        self.assertEqual(self._n("issued: '2026-06-30'"),
                         "issued: '2026-06-30T00:00:00Z'")

    def test_an_explicit_offset_is_kept_not_rewritten(self):
        self.assertEqual(self._n("issued: 2026-05-01T00:00:00+00:00"),
                         "issued: '2026-05-01T00:00:00+00:00'")

    def test_a_datetime_in_a_date_slot_is_narrowed(self):
        self.assertEqual(self._n("    end_date: '2026-05-01T00:00:00Z'"),
                         "    end_date: '2026-05-01'")

    def test_indentation_and_list_markers_survive(self):
        self.assertEqual(self._n("  - start_date: 2026-05-01"),
                         "  - start_date: '2026-05-01'")

    def test_values_it_cannot_read_are_left_alone(self):
        """Guessing at an unrecognised value would corrupt a record to make a
        validator happy."""
        for line in ("issued: null", "issued: ~", "issued: *anchor",
                     "issued: not-a-date", "issued: [2026-05-01]",
                     "description: issued: something"):
            with self.subTest(line=line):
                self.assertEqual(self._n(line), line)

    def test_the_header_comment_block_survives(self):
        """A YAML re-dump would drop the `#` header every record carries — the
        provenance a reader sees first. Hence text-level."""
        doc = "# Generated: 2026-08-01\n# Arm: baseline\nid: x\nissued: 2026-05-01T00:00:00Z\n"
        out = self._n(doc)
        self.assertIn("# Generated: 2026-08-01", out)
        self.assertIn("# Arm: baseline", out)

    def test_normalisation_is_idempotent(self):
        """A resumed run re-normalises a record already on disk, so a second
        pass must be a no-op."""
        for line in ("issued: 2026-05-01",
                     "  - start_date: 2026-05-01T00:00:00Z",
                     "issued: '2026-05-01T00:00:00+00:00'",
                     'issued: "2026-05-01"'):
            with self.subTest(line=line):
                once = self._n(line)
                self.assertEqual(once, self._n(once))

    def test_line_endings_and_indent_styles_survive(self):
        self.assertEqual(self._n("issued: 2026-05-01\r\n"),
                         "issued: '2026-05-01T00:00:00Z'\r\n")
        self.assertEqual(self._n("\tissued: 2026-05-01"),
                         "\tissued: '2026-05-01T00:00:00Z'")
        self.assertEqual(self._n("issued: 2026-05-01"),
                         "issued: '2026-05-01T00:00:00Z'")

    def test_prose_in_a_block_scalar_is_never_rewritten(self):
        """A description is free prose, and prose quoting a field name matches
        the pattern exactly. Rewriting it edits a record's *content* rather
        than its serialisation — the one thing this must never do."""
        import yaml as _yaml
        doc = ("id: x\ndescription: |\n  Fields present in the manifest:\n"
               "  issued: 2026-05-01\n  end_date: 2026-06-30\n"
               "issued: 2026-05-01\n")
        out = self._n(doc)
        before, after = _yaml.safe_load(doc), _yaml.safe_load(out)
        self.assertEqual(before["description"], after["description"],
                         "prose inside a block scalar was rewritten")
        self.assertEqual(after["issued"], "2026-05-01T00:00:00Z",
                         "the real field should still be normalised")

    def test_folded_scalars_are_also_protected(self):
        import yaml as _yaml
        doc = ("id: x\nnotes: >-\n  A folded note mentioning\n"
               "  start_date: 2026-01-01\nstart_date: 2026-01-01\n")
        out = self._n(doc)
        before, after = _yaml.safe_load(doc), _yaml.safe_load(out)
        self.assertEqual(before["notes"], after["notes"])
        self.assertEqual(after["start_date"], "2026-01-01")

    def test_a_block_scalar_ends_at_a_dedent(self):
        """Fields after a block must still be normalised."""
        import yaml as _yaml
        doc = ("id: x\ndescription: |\n  some prose\nissued: 2026-05-01\n")
        after = _yaml.safe_load(self._n(doc))
        self.assertEqual(after["issued"], "2026-05-01T00:00:00Z")

    def test_nested_records_keep_their_structure(self):
        import yaml as _yaml
        doc = ("id: x\ncollection_timeframes:\n  - start_date: 2026-05-01\n"
               "    end_date: 2026-06-30\n    description: a window\n")
        loaded = _yaml.safe_load(self._n(doc))
        self.assertEqual(set(loaded["collection_timeframes"][0]),
                         {"start_date", "end_date", "description"})
        self.assertEqual(loaded["collection_timeframes"][0]["start_date"],
                         "2026-05-01")


class TestGeneratedDateIsTheRunDate(unittest.TestCase):
    """#214: both prompts stamped a wrong date, in opposite directions."""

    def _resolved(self, condition):
        from data_sheets_schema.api_runner import resolve_prompt
        from data_sheets_schema.cli.api import _spec
        return resolve_prompt(_spec("CHORUS", "baseline",
                                    "2026-08-01_x_rep1", condition, None, None))

    def _today(self):
        from data_sheets_schema.cli.api import _spec
        return _spec("CHORUS", "baseline", "2026-08-01_x_rep1",
                     "generic", None, None).run_date

    def test_v2_no_longer_leaks_a_literal_placeholder(self):
        """`{DATE}` was never in the substitution table, so the literal string
        reached the model; its records read correctly only because the model
        inferred the date from `{LABEL}`."""
        body = self._resolved("generic_v2")
        self.assertNotIn("{DATE}", body)
        self.assertIn(f"# Generated: {self._today()}", body)

    def test_v1_hardcoded_date_is_normalised_not_emitted(self):
        """v1 hardcodes 2026-07-28 where every neighbouring header line takes a
        placeholder, so every run since carried a false date."""
        body = self._resolved("generic")
        self.assertNotIn("2026-07-28", body)
        self.assertIn(f"# Generated: {self._today()}", body)

    def test_v1_file_bytes_are_untouched(self):
        """The fix must not edit v1: its bytes are the pinned baseline for the
        2026-07-28 series, and editing them redefines what v2 is measured
        against."""
        from data_sheets_schema.api_runner import GENERIC_PROMPT
        self.assertIn("# Generated: 2026-07-28",
                      GENERIC_PROMPT.read_text(encoding="utf-8"),
                      "v1 was edited; normalisation should happen on the "
                      "resolved text instead")


class TestTheRunDateIsFrozenPerRun(unittest.TestCase):
    """A six-phase run takes tens of minutes; this study's sweep ran past
    midnight UTC. Reading the clock on each use is therefore not a hypothetical
    problem."""

    def _spec_for(self, **kw):
        from data_sheets_schema.api_runner import RunSpec
        from pathlib import Path
        return RunSpec(project="CHORUS", arm="baseline",
                       method="claudecode_agent",
                       bundle=Path("data/preprocessed/concatenated/"
                                   "CHORUS_preprocessed.txt"),
                       label="2026-08-01_x_rep1", **kw)

    def test_every_phase_of_a_run_sees_the_same_date(self):
        from data_sheets_schema.api_runner import resolve_prompt
        spec = self._spec_for()
        self.assertEqual(resolve_prompt(spec), resolve_prompt(spec))

    def test_the_recorded_digest_matches_the_text_actually_sent(self):
        """The digest is computed after the last phase. If the date moved, it
        would attest a prompt that was never sent — defeating the point of
        recording it at all."""
        import hashlib
        from data_sheets_schema.api_runner import (
            resolve_prompt, resolved_prompt_digest)
        spec = self._spec_for()
        sent = hashlib.sha256(resolve_prompt(spec).encode("utf-8")).hexdigest()
        self.assertEqual(sent, resolved_prompt_digest(spec)["sha256"])

    def test_assembly_digest_moves_when_an_instruction_moves(self):
        """#353: the prompt hashes witness the arm prompt only; #352 changed
        every request without moving them. The assembly digest must move with
        the instruction texts, and be stable when nothing changed."""
        from data_sheets_schema.api_runner import (
            PHASE_INSTRUCTIONS, assembly_digest)
        before = assembly_digest()
        self.assertEqual(before, assembly_digest())
        with unittest.mock.patch.dict(PHASE_INSTRUCTIONS,
                                      {"core": "reworded"}):
            self.assertNotEqual(before["sha256"], assembly_digest()["sha256"])
        self.assertEqual(before, assembly_digest())

    def test_the_date_can_be_pinned_explicitly(self):
        """Frozen on the spec, so a rerun can reproduce an earlier run's text."""
        from data_sheets_schema.api_runner import resolve_prompt
        body = resolve_prompt(self._spec_for(run_date="2026-07-04"))
        self.assertIn("# Generated: 2026-07-04", body)

    def test_the_default_is_today_in_utc(self):
        from datetime import datetime, timezone
        self.assertEqual(self._spec_for().run_date,
                         datetime.now(timezone.utc).date().isoformat())


class TestResolvedPromptIsHashed(unittest.TestCase):
    """The module docstring claimed the resolved text's hash was recorded. Only
    the file was hashed, so runs differing by substitution were
    indistinguishable by their prompt evidence."""

    def _digest(self, project, condition="generic"):
        from data_sheets_schema.api_runner import resolved_prompt_digest
        from data_sheets_schema.cli.api import _spec
        return resolved_prompt_digest(
            _spec(project, "baseline", "2026-08-01_x_rep1", condition, None, None))

    def test_substitution_changes_the_resolved_hash(self):
        self.assertNotEqual(self._digest("CHORUS")["sha256"],
                            self._digest("CM4AI")["sha256"],
                            "same file, different request, same hash")

    def test_the_same_request_hashes_the_same(self):
        self.assertEqual(self._digest("CHORUS"), self._digest("CHORUS"))

    def test_the_digest_states_its_algorithm_and_size(self):
        d = self._digest("CHORUS")
        self.assertEqual(len(d["sha256"]), 64)
        self.assertGreater(d["bytes"], 0)


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
            from data_sheets_schema.api_runner import REPAIR_INSTRUCTION
            if REPAIR_INSTRUCTION in blob:
                return FakeResponse(
                    "```yaml\nid: x\ntitle: T\nname: n\ndescription: d\n"
                    "keywords: [repaired]\n```")
            raise AssertionError("could not identify the phase from the request")
        if self.fail_on == phase:
            raise self.exc or RuntimeError("boom")
        if phase == "audit":
            return FakeResponse('{"findings": [], "summary": "none"}')
        if phase == "report":
            return FakeResponse("# Reconciliation\nNo discrepancies.\n")
        return FakeResponse(f"```yaml\n# {phase}\nid: x\ntitle: T\nname: n\ndescription: d\nkeywords: [a]\n```")

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
        # Four model phases: the core is derived, not generated (#694).
        self.assertEqual(len(res["usage"]), 4)
        self.assertEqual([u["phase"] for u in res["usage"]],
                         ["full", "audit", "reconcile_full", "report"])

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
        self.assertEqual(len(d["api_usage"]), 4)
        self.assertTrue(d["core_derivation"]["derived"])
        self.assertEqual(d["core_derivation"]["phase"], "reconcile_core")
        self.assertIn("derived from the full record", d["model"]["generation_method"])

    def test_every_phase_sends_the_cached_prefix(self):
        s = spec(out_dir=self.out)
        client = FakeClient()
        self.api._client = lambda: client
        self.api.execute(s)
        self.assertEqual(len(client.messages.calls), 4)
        for kw in client.messages.calls:
            parts = kw["messages"][0]["content"]
            cached = [p for p in parts if p.get("cache_control")]
            # By content: the count changed when the source ranking joined the
            # cached prefix (#596), and the property under test is that the
            # prefix is sent on every call, not its length.
            self.assertTrue(any("Declared input bundle" in p["text"]
                                for p in cached))
            self.assertTrue(any("Declared source ranking" in p["text"]
                                for p in cached))
            # temperature must be absent for models that reject it
            self.assertNotIn("temperature", kw)
            from data_sheets_schema.api_runner import output_limit
            self.assertLessEqual(kw["max_tokens"], output_limit(kw["model"]),
                                 "a phase must not request more output than "
                                 "the route allows")
            # every phase must be given a limit large enough for its artifact
            self.assertGreaterEqual(kw["max_tokens"], 12000)


class TestValidatorDrivenRepair(unittest.TestCase):
    """#356 option 1: the validator's findings drive a bounded shape repair.

    The shape-instructed audit still missed every type violation on the #347
    canary (#360), so the only reliable shape check is the validator — and a
    fully billed run should get a cheap repair before being declared invalid.
    """

    def setUp(self):
        import tempfile
        from data_sheets_schema import api_runner
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = Path(self.tmp.name) / "out"
        self.api = api_runner
        self.settings = {"name": "claude-opus-5", "temperature": 0.0}

    def _spec_with_artifacts(self):
        s = spec(out_dir=self.out)
        self.out.mkdir(parents=True, exist_ok=True)
        for p in (s.full_path, s.core_path):
            p.write_text("id: x\ntitle: T\nname: n\ndescription: d\n"
                         "keywords: [original]\n", encoding="utf-8")
        return s

    def test_build_repair_puts_instruction_last_and_omits_bundle(self):
        from data_sheets_schema.api_runner import (
            REPAIR_INSTRUCTION, build_repair)
        req = build_repair("full", "id: x\n", ["[ERROR] bad shape"])
        texts = [p["text"] for p in req.messages[0]["content"]]
        self.assertEqual(texts[-1], REPAIR_INSTRUCTION)
        # No bundle: the validator names shapes, not facts, and the evidence
        # boundary belongs to the six generation phases.
        self.assertFalse(any("Declared input bundle" in t for t in texts))
        self.assertEqual(len(req.cached_blocks), 1)
        self.assertIn("[ERROR] bad shape", texts[-2])
        core = build_repair("core", "id: x\n", ["e"])
        self.assertIn("CoreDataset", core.cached_blocks[0]["text"])

    def test_repair_rewrites_the_failing_artifact_and_stops_when_clean(self):
        s = self._spec_with_artifacts()
        # full fails round 1, is clean after the rewrite; core is clean.
        verdicts = iter([(["[ERROR] x"], None), ([], None), ([], None)])
        with unittest.mock.patch.object(
                self.api, "_validator_lines", lambda *a: next(verdicts)):
            usage = []
            log = self.api._repair_invalid(s, FakeClient(), self.settings,
                                           usage)
        self.assertIn("repaired", s.full_path.read_text())
        # The core is re-derived from the repaired full, never repaired itself.
        self.assertIn("repaired", s.core_path.read_text())
        self.assertEqual([x["outcome"] for x in log if x["phase"] == "repair_full"], ["applied"])
        self.assertTrue(log[-1]["phase"] == "repair_core"
                        and log[-1]["outcome"].startswith("re-derived"))
        self.assertEqual([u["phase"] for u in usage], ["repair_full"])

    def test_unusable_repair_leaves_the_record_untouched(self):
        s = self._spec_with_artifacts()

        class ProseClient:
            class messages:
                @staticmethod
                def stream(**kw):
                    class _S:
                        def __enter__(self):
                            return self

                        def __exit__(self, *a):
                            return False

                        def get_final_message(self):
                            return FakeResponse("I cannot repair this record.")
                    return _S()

        with unittest.mock.patch.object(
                self.api, "_validator_lines",
                lambda path, schema, cls: (["[ERROR] x"], None)
                if "core" not in str(path) else ([], None)):
            log = self.api._repair_invalid(s, ProseClient(), self.settings, [])
        self.assertIn("original", s.full_path.read_text(),
                      "a failed repair must never overwrite the record")
        full_log = [x for x in log if x["phase"] == "repair_full"]
        self.assertEqual(len(full_log), self.api.REPAIR_ROUNDS)
        self.assertTrue(all(x["outcome"].startswith("unusable") for x in full_log))

    def test_repair_stops_when_an_applied_round_makes_no_progress(self):
        """#364: strict decrease is the convergence test, but only across
        APPLIED rounds — a dud round rewrote nothing and must not cancel the
        retry the ceiling allows."""
        s = self._spec_with_artifacts()
        with unittest.mock.patch.object(
                self.api, "_validator_lines",
                lambda path, schema, cls: (["[ERROR] a", "[ERROR] b"], None)
                if "core" not in str(path) else ([], None)):
            log = self.api._repair_invalid(s, FakeClient(), self.settings, [])
        full_log = [x for x in log if x["phase"] == "repair_full"]
        self.assertEqual([x["outcome"] for x in full_log][:1], ["applied"])
        self.assertEqual(len(full_log), 2, log)
        self.assertIn("not converging", full_log[1]["outcome"])

    def test_execute_repairs_through_the_real_call_path(self):
        """The repair branch in execute() must be exercised end to end: it
        names client/settings/usage from enclosing scope, and a wrong name
        there survives every test that validates cleanly — the exact failure
        class the TestExecuteOffline docstring records."""
        import yaml as _yaml
        from data_sheets_schema import api_runner
        s = spec(out_dir=self.out)
        keep = api_runner._client
        api_runner._client = lambda: FakeClient()
        self.addCleanup(lambda: setattr(api_runner, "_client", keep))
        # Seven validator calls: validate#1 (full fails, core clean); repair
        # full round 1 (fails, rewrite) and round 2 (clean); repair checks
        # core (clean); validate#2 (both clean).
        verdicts = iter([(["[ERROR] x"], None), ([], None),
                         (["[ERROR] x"], None), ([], None), ([], None),
                         ([], None), ([], None)])
        with unittest.mock.patch.object(
                self.api, "_validator_lines", lambda *a: next(verdicts)):
            res = self.api.execute(s)
        self.assertEqual(res["validation_problems"], [])
        self.assertIn("repaired", s.full_path.read_text())
        d = _yaml.safe_load((self.out / "CHORUS_provenance.yaml").read_text())
        self.assertEqual([x["outcome"] for x in d["repair"] if x["phase"] == "repair_full"], ["applied"])
        self.assertTrue(d["repair"][-1]["outcome"].startswith("re-derived"))
        # Repair rewrote the full record *after* the report was written in
        # phase 6, so the report is regenerated against the repaired bytes and
        # is the last call (#604). Before that, `report_claims` checked a stale
        # report against records it no longer described.
        phases = [u["phase"] for u in d["api_usage"]]
        self.assertEqual(phases[-2:], ["repair_full", "report_after_repair"])
        self.assertEqual(len(phases), 6)
        # The core is re-derived from the repaired full, so both changed.
        self.assertEqual(
            d["report_regenerated_after_repair"]["changed"], ["core", "full"])

    def test_resume_of_a_completed_run_keeps_the_prior_accounting(self):
        """#362: re-running an invalid-but-complete run is how repair is
        triggered (#361), and that invocation rebuilds provenance. The six
        phases' real token accounting must survive into the new record, not
        be replaced by only the resumed calls."""
        import yaml as _yaml
        from data_sheets_schema import api_runner
        s = spec(out_dir=self.out)
        keep = api_runner._client
        api_runner._client = lambda: FakeClient()
        self.addCleanup(lambda: setattr(api_runner, "_client", keep))
        self.api.execute(s)                      # full pass: 4 usage rows
        prov = self.out / "CHORUS_provenance.yaml"
        first = _yaml.safe_load(prov.read_text())
        self.assertEqual(len(first["api_usage"]), 4)
        # Keep resume state, as a validation failure would have.
        self.api._save_progress(s, list(self.api.PHASES), None)
        # Re-run: all phases skip, repair runs once on the full record.
        verdicts = iter([(["[ERROR] x"], None), ([], None),
                         (["[ERROR] x"], None), ([], None), ([], None),
                         ([], None), ([], None)])
        with unittest.mock.patch.object(
                self.api, "_validator_lines", lambda *a: next(verdicts)):
            res = self.api.execute(s)
        self.assertEqual(len(res["skipped"]), 6)
        second = _yaml.safe_load(prov.read_text())
        phases = [u["phase"] for u in second["api_usage"]]
        self.assertEqual(len(phases), 5, phases)
        self.assertEqual(phases[:4], [u["phase"] for u in first["api_usage"]])
        self.assertEqual(phases[-1], "repair_full")
        # #366: a third invocation must keep the second's repair rounds in
        # the record, exactly as api_usage keeps every billed call.
        self.api._save_progress(s, list(self.api.PHASES), None)
        verdicts2 = iter([(["[ERROR] y"], None), ([], None),
                          (["[ERROR] y"], None), ([], None), ([], None),
                          ([], None), ([], None)])
        with unittest.mock.patch.object(
                self.api, "_validator_lines", lambda *a: next(verdicts2)):
            self.api.execute(s)
        third = _yaml.safe_load(prov.read_text())
        self.assertEqual([r["outcome"] for r in third["repair"] if r["phase"] == "repair_full"],
                         ["applied", "applied"],
                         "prior invocation's repair rounds must survive")
        self.assertEqual(len(third["api_usage"]), 6)

    def test_a_resumed_model_written_core_is_not_stamped_derived(self):
        """#704 review F3: a completed run resumed with a pre-#694 core on
        disk must not claim derivation the pair check would contradict."""
        import yaml as _yaml
        from data_sheets_schema import api_runner
        s = spec(out_dir=self.out)
        keep = api_runner._client
        api_runner._client = lambda: FakeClient()
        self.addCleanup(lambda: setattr(api_runner, "_client", keep))
        self.api.execute(s)
        # A core that a model wrote: not the projection of the full on disk.
        s.core_path.write_text(s.core_path.read_text() + "notes:\n- model-written core-only note\n")
        self.api._save_progress(s, list(self.api.PHASES), None)
        with unittest.mock.patch.object(self.api, "_validator_lines", lambda *a: ([], None)):
            self.api.execute(s)
        d = _yaml.safe_load((self.out / "CHORUS_provenance.yaml").read_text())
        self.assertFalse(d["core_derivation"]["derived"])
        self.assertIn("not the projection", d["core_derivation"]["reason"])

    def test_execute_snapshots_every_intermediate(self):
        """#369: reconcile and repair overwrite artifacts in place, and the
        audit findings die with the progress file on success. The snapshots
        are the only phase-evolution record the manuscript can analyze."""
        import yaml as _yaml
        from data_sheets_schema import api_runner
        s = spec(out_dir=self.out)
        keep = api_runner._client
        api_runner._client = lambda: FakeClient()
        self.addCleanup(lambda: setattr(api_runner, "_client", keep))
        self.api.execute(s)
        inter = s.provenance_path.parent / "intermediate"
        names = sorted(p.name for p in inter.iterdir())
        for expected in ("CHORUS_full.yaml", "CHORUS_core.yaml",
                         "CHORUS_audit.json", "CHORUS_reconcile_full.yaml",
                         "CHORUS_reconcile_core.yaml", "CHORUS_report.md"):
            self.assertIn(expected, names)
        d = _yaml.safe_load((self.out / "CHORUS_provenance.yaml").read_text())
        listed = {Path(i["path"]).name for i in d["intermediates"]}
        self.assertEqual(listed, set(names))
        for i in d["intermediates"]:
            self.assertEqual(len(i["sha256"]), 64)

    def test_snapshot_never_overwrites_a_colliding_name(self):
        s = spec(out_dir=self.out)
        self.out.mkdir(parents=True, exist_ok=True)
        first = self.api._snapshot(s, "CHORUS_repair_full_r1.yaml", "one\n")
        second = self.api._snapshot(s, "CHORUS_repair_full_r1.yaml", "two\n")
        self.assertNotEqual(first, second)
        self.assertEqual(first.read_text(), "one\n")
        self.assertEqual(second.read_text(), "two\n")
        self.assertEqual(second.name, "CHORUS_repair_full_r1_2.yaml")

    def test_intermediates_do_not_claim_a_prefix_sibling_project(self):
        s = spec(out_dir=self.out)
        self.out.mkdir(parents=True, exist_ok=True)
        self.api._snapshot(s, "CHORUS_full.yaml", "id: x\n")
        self.api._snapshot(s, "CHORUS_EXTENDED_full.yaml", "id: y\n")
        block = self.api._intermediates_block(s)
        self.assertEqual([Path(i["path"]).name for i in block],
                         ["CHORUS_full.yaml"])

    def test_execute_records_no_repair_when_records_validate(self):
        import yaml as _yaml
        from data_sheets_schema import api_runner
        s = spec(out_dir=self.out)
        keep = api_runner._client
        api_runner._client = lambda: FakeClient()
        self.addCleanup(lambda: setattr(api_runner, "_client", keep))
        self.api.execute(s)
        d = _yaml.safe_load((self.out / "CHORUS_provenance.yaml").read_text())
        self.assertIn("repair", d)
        self.assertIsNone(d["repair"])
        self.assertEqual(len(d["api_usage"]), 4)


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
        # reconcile_core is derived now (#694); the last model phase is report.
        client.messages = FakeMessages(fail_on="report")
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
        self.assertEqual(len(again.messages.calls), 4)

    def test_corrupt_progress_file_is_ignored_not_fatal(self):
        s = spec(out_dir=self.out)
        p = self.api._progress_path(s)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("{not json", encoding="utf-8")
        res = self.api.execute(s, client=FakeClient())
        self.assertEqual(len(res["usage"]), 4)

    def test_truncated_output_raises_rather_than_writing(self):
        """A truncated record can validate while being silently incomplete."""
        class Truncated(FakeResponse):
            def __init__(self, text):
                super().__init__(text)
                self.stop_reason = "max_tokens"

        class TruncMessages(FakeMessages):
            def create(self, **kw):
                super().create(**kw)
                return Truncated("```yaml\nid: x\ntitle: T\nname: n\ndescription: d\nkeywords: [a]\n```")

        import unittest.mock as _mock
        s = spec(out_dir=self.out)
        client = FakeClient(); client.messages = TruncMessages()
        with _mock.patch("data_sheets_schema.api_runner.time.sleep"):
            with self.assertRaises(RuntimeError) as ctx:
                self.api.execute(s, client=client)
        # Retried first — a ceiling one attempt overran is not a fact about the
        # phase — but never written, which is the property that matters.
        self.assertIn("max_tokens", str(ctx.exception))
        self.assertFalse(s.full_path.exists(), "truncated record was written")

    def test_an_unusable_body_is_retried_not_fatal(self):
        """A 200 whose body is unusable is not a permanent failure.

        A live CHORUS run returned the whole of `**Phase 2 - Core record.**`
        for phase 2 - `end_turn`, nine tokens of reasoning, no record - and
        killed a run whose phase 1 had already been billed. The transport-level
        retry cannot see this, because at that layer the call succeeded.
        """
        import unittest.mock as _mock

        duds = {"n": 0}

        class OneDud(FakeMessages):
            def create(self, **kw):
                resp = super().create(**kw)
                blob = " ".join(p.get("text", "")
                                for p in kw["messages"][0]["content"])
                # Exactly one dud, on the core phase, then behave.
                if "core record" in blob.lower() and duds["n"] == 0:
                    duds["n"] += 1
                    return FakeResponse("**Phase 2 - Core record.**")
                return resp

        s = spec(out_dir=self.out)
        client = FakeClient()
        client.messages = OneDud()
        with _mock.patch("data_sheets_schema.api_runner.time.sleep"):
            self.api.execute(s, client=client)

        self.assertEqual(duds["n"], 1, "the dud never landed")
        self.assertTrue(s.core_path.exists(),
                        "the retry did not recover the core record")

    def test_a_rate_limit_waits_for_the_stated_reset(self):
        """The backoff ladder is 30s; a CBORG window can be 10 minutes.

        23 runs of one sweep died because every attempt was spent inside a
        single window. The error says when it resets — honour that.
        """
        from datetime import datetime, timezone
        from data_sheets_schema.api_runner import _rate_limit_pause

        now = datetime(2026, 7, 31, 20, 20, 0, tzinfo=timezone.utc)
        exc = _rate_limit_error(
            "Error code: 429 - Rate limit exceeded. Limit type: requests. "
            "Current limit: 20, Remaining: 0. "
            "Limit resets at: 2026-07-31 20:28:19 UTC")
        pause = _rate_limit_pause(exc, now=now)
        self.assertAlmostEqual(pause, 8 * 60 + 19 + 2, delta=1)

    def test_a_rate_limit_without_a_reset_time_still_pauses(self):
        from data_sheets_schema.api_runner import (
            _rate_limit_pause, RATE_LIMIT_FALLBACK)
        exc = _rate_limit_error("429 slow down")
        self.assertEqual(_rate_limit_pause(exc), RATE_LIMIT_FALLBACK)

    def test_a_rate_limit_pause_is_capped(self):
        """A malformed or far-future reset must not park a run for hours."""
        from datetime import datetime, timezone
        from data_sheets_schema.api_runner import (
            _rate_limit_pause, RATE_LIMIT_MAX_PAUSE)
        exc = _rate_limit_error("Limit resets at: 2027-01-01 00:00:00 UTC")
        self.assertEqual(
            _rate_limit_pause(exc, now=datetime(2026, 7, 31, tzinfo=timezone.utc)),
            RATE_LIMIT_MAX_PAUSE)

    def test_a_non_rate_limit_error_is_not_treated_as_one(self):
        import anthropic
        from data_sheets_schema.api_runner import _rate_limit_pause
        self.assertIsNone(_rate_limit_pause(ValueError("nope")))
        self.assertIsNone(
            _rate_limit_pause(anthropic.APIConnectionError(request=None)))

    def test_transient_errors_are_retried(self):
        import anthropic
        calls = {"n": 0}

        def flaky(**kw):
            calls["n"] += 1
            if calls["n"] < 3:
                raise anthropic.APIConnectionError(request=None)
            return FakeResponse("```yaml\nid: x\ntitle: T\nname: n\ndescription: d\nkeywords: [a]\n```")

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

    def test_a_hung_call_is_abandoned_and_retried_not_waited_on(self):
        """#664: the first watchdog closed the stream from a timer thread and
        the blocked SSL read never woke. The call now runs on a worker the
        caller abandons at the wall clock; the next attempt proceeds while
        the dead one stays blocked."""
        import threading
        from data_sheets_schema.api_runner import _call_with_retry
        release = threading.Event()
        calls = {"n": 0}

        class Stream:
            def __init__(self, hang):
                self.hang = hang
            def __enter__(self): return self
            def __exit__(self, *e): return False
            def get_final_message(self):
                if self.hang:
                    release.wait(30)            # blocks like a dead socket read
                return FakeResponse("ok")
            def close(self):
                pass

        class Messages:
            @staticmethod
            def stream(**kw):
                calls["n"] += 1
                return Stream(hang=calls["n"] == 1)

        class Client:
            messages = Messages()

        t0 = time.monotonic()
        out = _call_with_retry(Client(), model="claude-opus-5", max_tokens=10,
                               temperature=None, system="s", messages=[],
                               sleep=lambda _: None, wall_clock=0.3)
        self.assertIsNotNone(out)
        self.assertEqual(calls["n"], 2)
        self.assertLess(time.monotonic() - t0, 5, "the caller must not wait for the hung read")
        release.set()

    def test_a_late_abandoned_worker_cannot_poison_the_live_attempt(self):
        """#747: the abandoned attempt's thread completes (with an error, as a
        closed stream would) *while* the next attempt is running; the live
        attempt's good response must survive."""
        import threading
        from data_sheets_schema.api_runner import _call_with_retry
        first_started = threading.Event(); second_running = threading.Event()
        calls = {"n": 0}

        class Stream:
            def __init__(self, n): self.n = n
            def __enter__(self): return self
            def __exit__(self, *e): return False
            def get_final_message(self):
                if self.n == 1:
                    first_started.set()
                    second_running.wait(10)          # wake once attempt 2 is live…
                    raise RuntimeError("stream closed")   # …and fail into *our* box
                second_running.set()
                time.sleep(0.3)                       # give the late thread time to land
                return FakeResponse("ok")
            def close(self): pass

        class Messages:
            @staticmethod
            def stream(**kw):
                calls["n"] += 1
                return Stream(calls["n"])

        class Client:
            messages = Messages()

        out = _call_with_retry(Client(), model="claude-opus-5", max_tokens=10,
                               temperature=None, system="s", messages=[],
                               sleep=lambda _: None, wall_clock=1.0)
        self.assertEqual(calls["n"], 2)
        self.assertEqual(out.content[0].text, "ok")

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


class TestExtractionRefusesProse(unittest.TestCase):
    """A phase must not write the model's narration as a record.

    Falling back to raw text when no fence was found saved a core file beginning
    "I need to emit the corrected core record. The core schema (CoreDataset)
    does not have..." — prose, written as the artifact. Only the downstream
    validator noticed, after the run was billed in full.
    """

    def test_prose_raises_from_extract(self):
        from data_sheets_schema.api_runner import _extract
        with self.assertRaises(RuntimeError) as ctx:
            _extract("I need to emit the corrected core record. The core "
                     "schema does not have that slot.", "yaml")
        self.assertIn("no parseable yaml", str(ctx.exception))

    def test_a_bare_scalar_is_not_a_record(self):
        """Prose parses as a YAML string, so parsing alone is not enough."""
        from data_sheets_schema.api_runner import _extract
        with self.assertRaises(RuntimeError):
            _extract("just a sentence with no colon", "yaml")

    def test_a_fenced_record_is_extracted(self):
        from data_sheets_schema.api_runner import _extract
        self.assertEqual(_extract("preamble\n```yaml\nid: x\ntitle: T\nname: n\ndescription: d\nkeywords: [a]\n```", "yaml"),
                         "id: x\ntitle: T\nname: n\ndescription: d\nkeywords: [a]")

    def test_an_unfenced_record_is_accepted(self):
        from data_sheets_schema.api_runner import _extract
        self.assertEqual(_extract("id: x\ntitle: T\nname: n\ndescription: d\nkeywords: [a]", "yaml"), "id: x\ntitle: T\nname: n\ndescription: d\nkeywords: [a]")

    def test_narration_before_a_fence_is_discarded(self):
        """A model that reasons before answering puts the answer last."""
        from data_sheets_schema.api_runner import _extract
        self.assertEqual(
            _extract("Let me think about this.\n```yaml\nid: x\ntitle: T\nname: n\ndescription: d\nkeywords: [a]\n```", "yaml"),
            "id: x\ntitle: T\nname: n\ndescription: d\nkeywords: [a]")

    def test_two_candidate_records_are_ambiguous_not_last_wins(self):
        """This test previously asserted the opposite, and was wrong to.

        "The model corrects itself as it goes, so take the last fence" is a
        guess about narrative order, not evidence. Under it, a complete record
        followed by a one-line `id: x` illustration silently became that
        illustration. Where two fences each look like the requested record,
        nothing in the response says which was meant — so fail rather than
        write the wrong one into a billed run.
        """
        from data_sheets_schema.api_runner import _extract
        first = "id: first\ntitle: T\nname: n\ndescription: d\nkeywords: [a]"
        last = "id: last\ntitle: U\nname: m\ndescription: e\nkeywords: [b]"
        with self.assertRaises(RuntimeError) as ctx:
            _extract(f"```yaml\n{first}\n```\nrevised:\n```yaml\n{last}\n```",
                     "yaml")
        self.assertIn("refusing to guess", str(ctx.exception).lower())

    def test_a_record_followed_by_a_small_example_keeps_the_record(self):
        """The concrete case the last-fence rule got wrong."""
        from data_sheets_schema.api_runner import _extract
        rec = "id: x\ntitle: T\nname: n\ndescription: d\nkeywords: [a]"
        out = _extract(f"```yaml\n{rec}\n```\nfor example:\n```yaml\nid: x\n```",
                       "yaml")
        self.assertEqual(out, rec)

    def test_an_audit_must_match_the_audit_contract(self):
        """Accepting any JSON object let `{"error": "unable to audit"}` through
        and fed it into reconciliation as though an audit had happened. An
        earlier version of this test asserted `{"a": 1}` was accepted, codifying
        the gap rather than catching it."""
        from data_sheets_schema.api_runner import _extract
        ok = '{"findings": [], "summary": "clean"}'
        self.assertEqual(_extract(f"```json\n{ok}\n```", "json"), ok)
        for bad in ('{"a": 1}', '{"error": "unable to audit"}', "not json"):
            with self.subTest(body=bad):
                with self.assertRaises(RuntimeError):
                    _extract(bad, "json")

    def test_markdown_reports_are_prose_by_design(self):
        from data_sheets_schema.api_runner import _extract
        self.assertEqual(_extract("# Report\n\nAll good.", "md"),
                         "# Report\n\nAll good.")

    def test_a_report_containing_a_fenced_example_is_not_truncated(self):
        """The regression this guards was mine: trying fences first for *every*
        kind reduced a report to the snippet it quoted. Reports routinely quote
        corrected slots, so this would have destroyed reports across a sweep.
        """
        from data_sheets_schema.api_runner import _extract
        report = ("# Reconciliation\n\nCorrected block:\n\n"
                  "```yaml\nid: https://example.org/x\n```\n\nNo contradictions.")
        out = _extract(report, "md")
        self.assertTrue(out.startswith("# Reconciliation"))
        self.assertTrue(out.endswith("No contradictions."))

    def test_an_empty_report_is_refused(self):
        from data_sheets_schema.api_runner import _extract
        for empty in ("", "   ", "\n\n"):
            with self.subTest(body=repr(empty)):
                with self.assertRaises(RuntimeError):
                    _extract(empty, "md")

    def test_narration_with_a_colon_is_still_refused(self):
        """`Note: ...` parses as a mapping, so requiring a mapping was not
        enough. A record names slots the schema defines; prose does not."""
        from data_sheets_schema.api_runner import _extract
        for prose in ("Note: I need to emit the corrected core record.",
                      "Core slots available: acquisition_methods, anomalies",
                      "Summary: the schema does not have that slot."):
            with self.subTest(prose=prose[:30]):
                with self.assertRaises(RuntimeError):
                    _extract(prose, "yaml")

    def test_narration_followed_by_a_real_record_keeps_the_record(self):
        from data_sheets_schema.api_runner import _extract
        self.assertEqual(
            _extract("I will now emit it.\n```yaml\nid: x\ntitle: T\nname: n\ndescription: d\nkeywords: [a]\n```",
                     "yaml"),
            "id: x\ntitle: T\nname: n\ndescription: d\nkeywords: [a]")

    def test_a_refusal_naming_real_slots_is_refused(self):
        """A vocabulary test alone cannot see a refusal.

        `title: I cannot produce the requested record` spends every key on a
        real slot, so "names at least one known slot" accepted it and wrote the
        refusal to disk as the record.
        """
        from data_sheets_schema.api_runner import _extract
        for refusal in ("title: I cannot produce the requested record",
                        "description: The documents do not support this record."):
            with self.subTest(refusal=refusal[:30]):
                with self.assertRaises(RuntimeError):
                    _extract(f"```yaml\n{refusal}\n```", "yaml")

    def test_narration_beside_a_real_slot_is_refused(self):
        """Narration sits happily next to `id:`, which is how it got through."""
        from data_sheets_schema.api_runner import _extract
        with self.assertRaises(RuntimeError):
            _extract("```yaml\nNote: here is my narration\nid: x\n```", "yaml")

    def test_a_record_must_carry_the_root_identifier(self):
        """The fragment this catches was real output, not a hypothetical.

        One VOICE core run wrote an 8-key blob with no `id` and keys like
        `_distributions` that are not slots at all.
        """
        from data_sheets_schema.api_runner import _extract
        with self.assertRaises(RuntimeError):
            _extract("```yaml\ntitle: T\nname: n\ndescription: d\n"
                     "keywords: [a]\npurposes: []\n```", "yaml")

    def test_a_core_response_may_not_use_full_only_slots(self):
        """Checking a core response against the full schema defeats the point.

        `_known_slots` also used `all_slots()`, which for the core schema is 262
        names against the 79 `CoreDataset` actually accepts.
        """
        from linkml_runtime import SchemaView
        from data_sheets_schema.api_runner import (
            _extract, CORE_SCHEMA_PATH, FULL_SCHEMA_PATH)
        full = {s.name for s in
                SchemaView(FULL_SCHEMA_PATH).class_induced_slots("Dataset")}
        core = {s.name for s in
                SchemaView(CORE_SCHEMA_PATH).class_induced_slots("CoreDataset")}
        full_only = sorted(full - core)
        self.assertTrue(full_only, "expected some Dataset-only slots")
        body = ("id: x\ntitle: T\nname: n\ndescription: d\nkeywords: [a]\n"
                f"{full_only[0]}: []")
        _extract(f"```yaml\n{body}\n```", "yaml")          # fine as a full record
        with self.assertRaises(RuntimeError):
            _extract(f"```yaml\n{body}\n```", "yaml",
                     CORE_SCHEMA_PATH, "CoreDataset")

    def test_an_audit_must_carry_usable_findings(self):
        """`findings` present is not `findings` usable.

        `{"findings": null}` and `{"findings": "unable to audit"}` were both
        accepted and handed to both reconciliation phases — three further
        billed calls correcting a record against an audit that never ran.
        """
        from data_sheets_schema.api_runner import _extract
        for body in ('{"findings": null}',
                     '{"findings": "unable to audit"}',
                     '{"findings": [{"note": "malformed"}]}',
                     '{"summary": "no findings key at all"}'):
            with self.subTest(body=body[:34]):
                with self.assertRaises(RuntimeError):
                    _extract(f"```json\n{body}\n```", "json")

    def test_a_well_formed_audit_is_accepted(self):
        from data_sheets_schema.api_runner import _extract
        # `record` is required since #604: each reconciliation phase applies
        # "the findings that concern" its record, so a finding that does not
        # say which record it concerns cannot be applied by either.
        good = ('{"findings": [{"severity": "high", "record": "full", '
                '"slot": "id", "issue": "mismatch"}], "summary": "one finding"}')
        self.assertEqual(_extract(f"```json\n{good}\n```", "json"), good)

    def test_an_audit_with_no_findings_is_still_an_audit(self):
        """An empty list is a result; null is an absence."""
        from data_sheets_schema.api_runner import _extract
        good = '{"findings": [], "summary": "no contradictions"}'
        self.assertEqual(_extract(f"```json\n{good}\n```", "json"), good)

    def test_uppercase_fence_labels_are_recognised(self):
        from data_sheets_schema.api_runner import _extract
        self.assertEqual(_extract("```YAML\nid: x\ntitle: T\nname: n\ndescription: d\nkeywords: [a]\n```", "yaml"), "id: x\ntitle: T\nname: n\ndescription: d\nkeywords: [a]")

    def test_the_audit_ceiling_has_real_headroom(self):
        """Two AI-READI runs truncated mid-audit at 12000.

        `> 12000` would be satisfied by 12001, which would not have stopped
        them. The requirement is headroom, so the assertion states it.
        """
        from data_sheets_schema.api_runner import PHASE_MAX_TOKENS
        self.assertGreaterEqual(PHASE_MAX_TOKENS["audit"], 24000)


class TestARejectedPhaseWritesNothing(unittest.TestCase):
    """`_extract` raising must leave no artifact and no resumable progress.

    Tested through `execute()`, not `_extract`. A unit test of the extractor
    proves the string is refused; it does not prove the run refuses to write it,
    and writing a bad artifact is the failure that actually cost a billed run.
    """

    def _client(self, body):
        class Resp:
            def __init__(self):
                self.content = [type("B", (), {"type": "text", "text": body})()]
                self.stop_reason = "end_turn"
                self.usage = type("U", (), {
                    "input_tokens": 1, "output_tokens": 1,
                    "cache_read_input_tokens": 0,
                    "cache_creation_input_tokens": 0})()

        class C:
            class messages:
                @staticmethod
                def stream(**kw):
                    class S:
                        def __enter__(s):
                            return s

                        def __exit__(s, *e):
                            return False

                        def get_final_message(s):
                            return Resp()
                    return S()
        return C()

    def test_prose_in_phase_one_leaves_no_record_and_no_progress(self):
        import tempfile
        from pathlib import Path
        from data_sheets_schema.api_runner import RunSpec, execute

        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "out"
            bundle = Path(td) / "b.txt"
            bundle.write_text("some source text")
            spec = RunSpec(project="P", arm="baseline",
                           method="claudecode_agent", bundle=bundle,
                           label="2026-07-31_x_rep1", out_dir=out)
            with self.assertRaises(RuntimeError):
                execute(spec, client=self._client(
                    "I need to emit the record but the schema lacks that slot."))
            written = {p.name for p in out.rglob("*") if p.is_file()} \
                if out.exists() else set()

            # No record, no provenance, and nothing resumable.
            self.assertEqual(
                {n for n in written
                 if n.endswith((".yaml", "_progress.json", ".md"))}, set(),
                "a refused phase must not leave an artifact or progress file")

            # The reasoning log *should* survive. It is written before the
            # extraction check on purpose, so a phase that fails still records
            # what it cost — that is the one thing worth keeping from a run
            # that produced nothing usable.
            self.assertIn("P_reasoning.jsonl", written)


class TestExtractionToleratesFenceArtifacts(unittest.TestCase):
    """A valid record must not be thrown away over a formatting artifact.

    The guard rejected a response beginning `yaml\\n# D4D Datasheet...` — a
    perfectly good record whose fence backticks did not survive. Each such
    rejection costs every phase already billed for that run, so the reader has
    to be tolerant of the wrapper while still strict about the content.
    """

    def test_a_stray_language_marker_is_stripped(self):
        from data_sheets_schema.api_runner import _extract
        self.assertEqual(_extract("yaml\n# header\nid: x\ntitle: T\nname: n\ndescription: d\nkeywords: [a]", "yaml"),
                         "# header\nid: x\ntitle: T\nname: n\ndescription: d\nkeywords: [a]")

    def test_an_unclosed_fence_is_accepted(self):
        from data_sheets_schema.api_runner import _extract
        self.assertEqual(_extract("```yaml\nid: x\ntitle: T\nname: n\ndescription: d\nkeywords: [a]", "yaml"),
                         "id: x\ntitle: T\nname: n\ndescription: d\nkeywords: [a]")

    def test_tolerance_does_not_admit_prose(self):
        """The point is a looser wrapper, not a looser record."""
        from data_sheets_schema.api_runner import _extract
        for prose in ("yaml\nNote: I need to emit the record.",
                      "```yaml\nSummary: the schema lacks that slot."):
            with self.subTest(prose=prose[:28]):
                with self.assertRaises(RuntimeError):
                    _extract(prose, "yaml")


class TestResumeUsesArtifactsNotOnlyProgress(unittest.TestCase):
    """A finished run must not be redone.

    Success deletes the progress file, so resuming a *completed* run found no
    record of it and re-ran all six phases of work already paid for. The
    artifacts on disk are the durable evidence of what completed.
    """

    def _spec(self, td):
        from data_sheets_schema.api_runner import RunSpec
        out = Path(td) / "out"
        b = Path(td) / "b.txt"
        b.write_text("src")
        return RunSpec(project="P", arm="baseline", method="claudecode_agent",
                       bundle=b, label="2026-07-31_x_rep1", out_dir=out)

    REC = "id: x\ntitle: T\nname: n\ndescription: d\nkeywords: [a]\n"

    def _complete_run(self, spec, *, provenance=True, label=None):
        """Lay down a finished run: three artifacts and its provenance record."""
        import hashlib
        import yaml as _yaml
        spec.out_dir.mkdir(parents=True, exist_ok=True)
        spec.full_path.write_text(self.REC)
        spec.core_path.write_text(self.REC)
        spec.report_path.write_text("# report\n")
        if not provenance:
            return
        self._write_provenance(spec, label=label)

    def _write_provenance(self, spec, *, label=None):
        """Provenance matching whatever is on disk *now*.

        Built with `build_record`, the writer the pipeline itself uses, rather
        than hand-assembled. It used to be a stub of four keys, and the resume
        exit's conformance gate (#619) rejected it — correctly, since no writer
        produces such a record. A fixture that cannot pass the gate the code
        under test applies is testing a situation that does not arise, and
        weakening the gate to accommodate it would have been the wrong fix.

        Going through the real writer also means the fixture cannot drift away
        from the schema again: a field the writer gains, it gains.
        """
        import hashlib
        import yaml as _yaml

        from data_sheets_schema.provenance import build_record
        def sha(p):
            return hashlib.sha256(p.read_bytes()).hexdigest()
        rec = build_record(spec.project, spec.method, label or spec.label,
                           mode="live", input_bundle=spec.bundle,
                           input_verified=True, concat_dir=spec.out_dir)
        data = dict(rec.data)
        data["run"] = {**(data.get("run") or {}), "method": spec.method,
                       "label": label or spec.label, "project": spec.project}
        data["api_usage"] = [{"phase": ph, "input_tokens": 100,
                              "output_tokens": 200} for ph in
                             ("full", "core", "audit", "reconcile_full",
                              "reconcile_core", "report")]
        data["validation"] = {"artifacts": {
            "full": {"path": str(spec.full_path), "sha256": sha(spec.full_path)},
            "core": {"path": str(spec.core_path), "sha256": sha(spec.core_path)},
        }}
        spec.provenance_path.parent.mkdir(parents=True, exist_ok=True)
        spec.provenance_path.write_text(_yaml.safe_dump(data))

    def _no_api(self, called):
        class C:
            class messages:
                @staticmethod
                def stream(**kw):
                    called["n"] += 1
                    raise AssertionError("no phase should have been called")
        return C

    def test_a_completed_run_reruns_nothing(self):
        import tempfile
        from data_sheets_schema.api_runner import execute

        with tempfile.TemporaryDirectory() as td:
            spec = self._spec(td)
            self._complete_run(spec)
            called = {"n": 0}
            execute(spec, client=self._no_api(called))
            self.assertEqual(called["n"], 0,
                             "a completed run must cost nothing to resume")

    def test_resume_will_not_report_a_non_conforming_record_as_complete(self):
        """The resume exit has now been patched three times for one omission.

        It returns `already_complete: True` after `check_provenance`, which asks
        whether a *usable* record exists — never whether it conforms. So a
        record written by any other path (`d4d provenance record`, a backfill,
        a run that failed the gate) came back through here as a success and
        `d4d api batch` counted it in `ok` (#619).

        The same exit previously reported `[]` validation problems about records
        it never looked at, and `None` for all three checks (#599). This is the
        third instance, so it gets a test rather than a comment.
        """
        import tempfile

        import yaml as _yaml

        from data_sheets_schema.api_runner import execute

        with tempfile.TemporaryDirectory() as td:
            spec = self._spec(td)
            self._complete_run(spec)
            data = _yaml.safe_load(
                spec.provenance_path.read_text(encoding="utf-8"))
            # A live record with no `system`: rejected only by the mode rule,
            # and exactly the kind of record another writer could leave behind.
            data.pop("system")
            spec.provenance_path.write_text(_yaml.safe_dump(data))
            called = {"n": 0}
            with self.assertRaises(RuntimeError) as caught:
                execute(spec, client=self._no_api(called))
            self.assertIn("system", str(caught.exception))
            self.assertEqual(called["n"], 0,
                             "the gate must refuse before spending anything")

    def test_resuming_a_completed_run_preserves_its_provenance(self):
        """Resume must not restamp the record it is resuming.

        Continuing through `execute` rebuilds provenance from the *current*
        bundle and writes `api_usage: []` over six phases of real token
        accounting. For a study whose output is the measurement, a resume that
        silently erases the cost evidence is worse than one that re-runs.
        """
        import tempfile
        from data_sheets_schema.api_runner import execute

        with tempfile.TemporaryDirectory() as td:
            spec = self._spec(td)
            self._complete_run(spec)
            before = spec.provenance_path.read_text()
            result = execute(spec, client=self._no_api({"n": 0}))
            self.assertEqual(spec.provenance_path.read_text(), before,
                             "the provenance record was rewritten on resume")
            self.assertEqual(len(result["usage"]), 6)
            self.assertTrue(result.get("already_complete"))

    def test_a_resumed_run_reports_real_validation_problems(self):
        """Resuming must not hand back a clean bill nobody checked.

        The early return asserted `validation_problems: []` about records the
        call never examined, so a run that had failed validation came back clean
        the moment it was resumed — and `batch` counts its successes from that
        field, which is how a broken run reads as a passing one.
        """
        import tempfile
        from data_sheets_schema.api_runner import execute

        bad = ("id: x\ntitle: T\nname: n\ndescription: d\n"
               "keywords: [a]\ninstances: not-a-list\n")
        with tempfile.TemporaryDirectory() as td:
            spec = self._spec(td)
            spec.out_dir.mkdir(parents=True, exist_ok=True)
            # Lay the invalid records down *first*, then hash them, so the
            # provenance is internally consistent and the run resumes.
            spec.full_path.write_text(bad)
            spec.core_path.write_text(bad)
            spec.report_path.write_text("# report\n")
            self._write_provenance(spec)

            result = execute(spec, client=self._no_api({"n": 0}))
            self.assertTrue(result.get("already_complete"),
                            "expected the run to resume, not re-run")
            self.assertNotEqual(
                result["validation_problems"], [],
                "a resumed run reported clean without validating")

    def test_artifacts_without_provenance_are_not_adopted(self):
        """Three files on disk do not say who wrote them."""
        import tempfile
        from data_sheets_schema.api_runner import execute

        with tempfile.TemporaryDirectory() as td:
            spec = self._spec(td)
            self._complete_run(spec, provenance=False)
            called = {"n": 0}
            with self.assertRaises(AssertionError):
                execute(spec, client=self._no_api(called))
            self.assertEqual(called["n"], 1, "should have re-run phase 1")

    def test_a_flat_out_dir_does_not_let_a_new_label_claim_old_outputs(self):
        """With `out_dir` set, artifact paths carry no label at all.

        So a fresh label sees the previous run's files at exactly the paths it
        would write, and inferring completion from them would restamp another
        run's outputs as its own.
        """
        import tempfile
        from data_sheets_schema.api_runner import RunSpec, execute

        with tempfile.TemporaryDirectory() as td:
            old = self._spec(td)
            self._complete_run(old)
            new = RunSpec(project="P", arm="baseline", method="claudecode_agent",
                          bundle=old.bundle, label="2026-07-31_DIFFERENT_rep1",
                          out_dir=old.out_dir)
            self.assertEqual(new.full_path, old.full_path)
            called = {"n": 0}
            with self.assertRaises(AssertionError):
                execute(new, client=self._no_api(called))
            self.assertEqual(called["n"], 1,
                             "the new label claimed the old run's outputs")

    def test_a_corrupt_artifact_is_not_resumed_on_top_of(self):
        """The exact debris one VOICE run left: progress said `core` was done,
        and the core on disk was an 8-key fragment with no `id`. Resuming would
        have carried it into reconciliation and billed two more phases against
        a record that never existed."""
        import json
        import tempfile
        from data_sheets_schema.api_runner import execute, _progress_path

        with tempfile.TemporaryDirectory() as td:
            spec = self._spec(td)
            spec.out_dir.mkdir(parents=True)
            spec.full_path.write_text(self.REC)
            spec.core_path.write_text(
                "_distributions: []\ncompression: none\ndialect: x\n")
            _progress_path(spec).parent.mkdir(parents=True, exist_ok=True)
            _progress_path(spec).write_text(json.dumps(
                {"completed": ["full", "core"]}))

            ran = []

            class C:
                class messages:
                    @staticmethod
                    def stream(**kw):
                        raise AssertionError("stop")

            def record(spec_, ph, **kw):
                ran.append(ph)
                raise AssertionError("stop")

            import data_sheets_schema.api_runner as m
            original = m.build_phase
            m.build_phase = lambda s_, ph, **kw: record(s_, ph, **kw)
            try:
                with self.assertRaises(AssertionError):
                    execute(spec, client=C())
            finally:
                m.build_phase = original

            # The core is derived, not generated (#694): re-running it makes no
            # model call, so the first *model* phase reached is audit — and by
            # then the fragment must have been replaced by a derived record.
            self.assertEqual(ran[0], "audit",
                             f"expected core to re-derive then audit to run, resumed at {ran[:1]}")
            import yaml as _yaml
            core = _yaml.safe_load(spec.core_path.read_text())
            self.assertEqual(core.get("id"), "x", "corrupt core was not re-derived")

    def test_a_partial_run_is_not_inferred_from_artifacts(self):
        """`full` and `reconcile_full` write the same file.

        Inferring completion per-artifact marked reconciliation done when only
        phase 1 had run, shipping an unreconciled record as finished. Only a
        wholly complete run may be inferred; a partial one falls back to the
        progress file, which is what distinguishes the two phases.
        """
        import tempfile
        from data_sheets_schema.api_runner import execute

        with tempfile.TemporaryDirectory() as td:
            spec = self._spec(td)
            spec.out_dir.mkdir(parents=True)
            spec.full_path.write_text("id: x\ntitle: T\nname: n\ndescription: d\nkeywords: [a]\n")     # phase 1 only

            calls = {"n": 0}

            class C:
                class messages:
                    @staticmethod
                    def stream(**kw):
                        calls["n"] += 1
                        raise RuntimeError("stop after the first call")

            with self.assertRaises(RuntimeError):
                execute(spec, client=C())
            self.assertGreater(calls["n"], 0,
                               "a partial run must not be treated as complete")


class TestReceiptCondition(unittest.TestCase):
    """Under a receipt condition the bundle carries chunk markers, the full
    phase asks for the receipt, and the response's second document is the
    receipt file (#710). Under any other condition none of that happens."""

    def _spec(self, condition):
        from pathlib import Path

        from data_sheets_schema.api_runner import RunSpec
        return RunSpec(project="CHORUS", arm="baseline", method="claudecode_agent",
                       bundle=Path("data/preprocessed/concatenated/CHORUS_preprocessed.txt"),
                       label="t", condition=condition)

    def setUp(self):
        from pathlib import Path
        if not Path("data/preprocessed/chunks/CHORUS_chunks.yaml").exists():
            self.skipTest("corpus manifest absent")

    def test_markers_and_instruction_only_under_the_receipt_condition(self):
        from data_sheets_schema.api_runner import RECEIPT_MARK, build_phase
        from data_sheets_schema.chunking import load_manifest
        from pathlib import Path
        m = load_manifest(Path("data/preprocessed/chunks/CHORUS_chunks.yaml"))
        v7 = build_phase(self._spec("generic_v7"), "full", carry={})
        text = v7.cached_blocks[1]["text"]
        for c in m["chunks"]:
            self.assertIn(f"\n[{c['id']}]\n", text)
        self.assertIn(f"bundle_md5: {m['bundle_md5']}", text)
        self.assertIn(RECEIPT_MARK, v7.messages[0]["content"][-1]["text"])
        # markers are additions only: removing them gives the bundle back
        stripped = "\n".join(l for l in text.split("\n\n", 1)[1].split("\n") if not re.fullmatch(r"\[c\d+\]", l))
        self.assertEqual(stripped, Path("data/preprocessed/concatenated/CHORUS_preprocessed.txt").read_text(encoding="utf-8"))
        v6 = build_phase(self._spec("generic_v6"), "full", carry={})
        self.assertNotIn("\n[c001]\n", v6.cached_blocks[1]["text"])
        self.assertNotIn(RECEIPT_MARK, v6.messages[0]["content"][-1]["text"])
        # the receipt request rides only on the full phase
        audit = build_phase(self._spec("generic_v7"), "audit", carry={"Completed full record": "x"})
        self.assertNotIn(RECEIPT_MARK, audit.messages[0]["content"][-1]["text"])

    def test_a_stale_or_missing_manifest_refuses_before_a_token_is_spent(self):
        import tempfile
        from pathlib import Path

        from data_sheets_schema.api_runner import chunk_marked_bundle
        with tempfile.TemporaryDirectory() as tmp:
            other = Path(tmp) / "CHORUS_preprocessed.txt"
            other.write_text("not the bytes the manifest chunked\n", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "not of the bytes"):
                chunk_marked_bundle(other)
            missing = Path(tmp) / "NOPE_crate_only.txt"
            missing.write_text("x\n", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "no chunk manifest"):
                chunk_marked_bundle(missing)

    def test_the_response_is_split_into_record_and_receipt(self):
        from data_sheets_schema.api_runner import RECEIPT_MARK, _extract_receipt, split_receipt
        rec, rcpt = split_receipt(f"```yaml\nid: x\n```\n{RECEIPT_MARK}\n```yaml\nbundle_md5: m\nchunks:\n- id: c001\n  status: nothing_relevant\n  reason: r\n```\n")
        self.assertIn("id: x", rec)
        self.assertEqual(yaml.safe_load(_extract_receipt(rcpt))["chunks"][0]["id"], "c001")
        self.assertEqual(split_receipt("no marker")[1], None)
        # #740: a marker echoed inside the record does not split it; the
        # receipt follows the last marker *line*; a single fence around both
        # documents still yields the receipt
        echoed = (f"```yaml\nid: x\nnotes: the instruction said {RECEIPT_MARK} here\n```\n"
                  f"{RECEIPT_MARK}\nbundle_md5: m\nchunks:\n- id: c001\n  status: nothing_relevant\n  reason: r\n```\n")
        rec, rcpt = split_receipt(echoed)
        self.assertIn("notes: the instruction said", rec)
        self.assertEqual(yaml.safe_load(_extract_receipt(rcpt))["chunks"][0]["id"], "c001")
        with self.assertRaisesRegex(RuntimeError, "not a receipt"):
            _extract_receipt("chunks:\n- just a string\n")
        with self.assertRaisesRegex(RuntimeError, "not a receipt"):
            _extract_receipt("chunks: []\n")
        with self.assertRaisesRegex(RuntimeError, "not a receipt"):
            _extract_receipt("- a list\n")

    def test_the_full_phase_budget_is_raised_only_under_a_receipt_condition(self):
        """#768: record plus receipt was 95,342 tokens on AI_READI against a
        96,000 cap. The receipt phase gets the route's ceiling; nothing else moves."""
        import os
        from data_sheets_schema.api_runner import PHASE_MAX_TOKENS, phase_max_tokens
        saved = os.environ.pop("D4D_RECEIPT_FULL_MAX_TOKENS", None)
        self.addCleanup(lambda: os.environ.update({"D4D_RECEIPT_FULL_MAX_TOKENS": saved}) if saved is not None else None)
        self.assertEqual(phase_max_tokens(self._spec("generic_v7"), "full", 1), 128000)
        self.assertEqual(phase_max_tokens(self._spec("generic_v6"), "full", 1), PHASE_MAX_TOKENS["full"])
        self.assertEqual(phase_max_tokens(self._spec("generic_v7"), "reconcile_full", 1), PHASE_MAX_TOKENS["reconcile_full"])
        self.assertEqual(phase_max_tokens(self._spec("generic_v7"), "nope", 7), 7)
        # #777: the receipt-condition full budget is env-overridable, malformed-safe
        for raw, want in (("96000", 96000), ("junk", 128000), ("0", 128000), ("999999", 128000)):   # clamped (#779)
            os.environ["D4D_RECEIPT_FULL_MAX_TOKENS"] = raw
            try:
                self.assertEqual(phase_max_tokens(self._spec("generic_v7"), "full", 1), want, raw)
                self.assertEqual(phase_max_tokens(self._spec("generic_v6"), "full", 1), PHASE_MAX_TOKENS["full"])
            finally:
                os.environ.pop("D4D_RECEIPT_FULL_MAX_TOKENS", None)
        # the record's per-phase map says the same number api_usage does (#770)
        from data_sheets_schema.api_runner import _model_settings
        import data_sheets_schema.api_runner as api
        settings = _model_settings()
        blk = api._model_block(self._spec("generic_v7"), settings) if hasattr(api, "_model_block") else None
        if blk is not None:
            self.assertEqual(blk["max_tokens_by_phase"]["full"], 128000)

    def test_the_assembly_digest_covers_the_receipt_instruction(self):
        from data_sheets_schema.api_runner import PHASE_INSTRUCTIONS, assembly_digest
        self.assertIn("full_receipt", PHASE_INSTRUCTIONS)
        self.assertIn("#710", assembly_digest()["layout"])

"""The third generation arm's registry entries and record identity (#2202).

`claudecode_direct` is Claude Code on the maintainer's subscription, direct
to Anthropic: same runtime binary as the agentic arm, different transport.
These tests pin what tells the two apart in code, that every consumer of the
runtime key admits the third one (#2210, #2211), that a Claude Code runtime is
recognised by its key rather than its exact string (#2212, #2213), that the
provider is not compared between arms (#2214), that the render-spec gate binds
the asserted effort (#2216), and that the effort reaches the rendered recorder
line through the production renderer (#2217).
"""
from dataclasses import replace
import json
import os
import shlex
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from click.testing import CliRunner
import pytest
import yaml

from tests.test_generation_manifest_identity import external, offline  # noqa: F401  the external cohort fixture
from tests.test_native_registered_provenance import native  # noqa: F401  the registered native fixture
from tests.test_provenance_reasoning_effort import header

DIRECT = "Claude Code (direct)"
DIRECT_PROVIDER = "Anthropic (Claude subscription, direct)"


class DirectArmRegistry(unittest.TestCase):
    def test_the_method_and_its_core_twin_are_registered_as_a_baseline_agent_family(self):
        from data_sheets_schema.constants.methods import METHODS
        from data_sheets_schema.runs import AGENT_FAMILY, ARM_BY_METHOD, requires_request
        for method in ("claudecode_direct", "claudecode_direct_core"):
            self.assertIn(method, METHODS)
            self.assertEqual(ARM_BY_METHOD[method], "baseline")
        self.assertIn("claudecode_direct", AGENT_FAMILY)
        self.assertTrue(requires_request("2026-09-22_claude-opus-5-direct-generic-v9_rep1", "claudecode_direct"))
        # The existing families are unchanged and still ordered first.
        self.assertEqual(AGENT_FAMILY[:2], ("claudecode_agent", "claudecode_api"))

    def test_the_direct_runtime_string_folds_to_its_own_key_and_plain_claude_code_stays_agentic(self):
        from data_sheets_schema.runs import RUNTIME_CHOICES, RUNTIME_KEYS, runtime_of
        self.assertEqual(runtime_of({"model": {"agent_runtime": DIRECT}}), "direct")
        self.assertEqual(runtime_of({"model": {"agent_runtime": "Claude Code"}}), "agentic")
        self.assertEqual(runtime_of({"model": {"agent_runtime": "Claude API (direct)"}}), "api")
        self.assertEqual(set(RUNTIME_KEYS.values()), {"agentic", "api", "direct"})
        # Every key is offered wherever a runtime is chosen (#2211).
        self.assertEqual(set(RUNTIME_CHOICES), set(RUNTIME_KEYS.values()))
        self.assertEqual(RUNTIME_CHOICES[:2], ("api", "agentic"))       # the existing order is kept

    def test_a_claude_code_runtime_is_recognised_by_its_key_not_its_exact_string(self):
        from data_sheets_schema.runs import is_claude_code_runtime
        for runtime in ("Claude Code", " claude code ", DIRECT, "CLAUDE CODE (DIRECT)"):
            self.assertTrue(is_claude_code_runtime(runtime), runtime)
        for runtime in ("Claude API (direct)", "Codex CLI", "", None, 3, "Claude Code (proxy)"):
            self.assertFalse(is_claude_code_runtime(runtime), runtime)

    def test_the_direct_runtime_still_reads_playbooks_and_follows_the_agentic_spec(self):
        from data_sheets_schema.api_runner import RunSpec
        from data_sheets_schema.provenance import runtime_reads_playbooks
        self.assertTrue(runtime_reads_playbooks(DIRECT))
        spec = RunSpec(project="CHORUS", arm="baseline", method="claudecode_direct", bundle=Path("x"),
                       label="2026-09-22_x_rep1", condition="generic_v9", manifest=None, render_version=9,
                       run_date="2026-09-22", runtime=DIRECT, provider=DIRECT_PROVIDER, _replay_only=True)
        self.assertTrue(spec.is_agentic)

    def test_the_runtime_row_separates_the_arms_and_the_provider_is_not_compared(self):
        """#2214: on the 2026-08 agentic records `model.provider` is the literal
        the old playbook dictated while the transport was CBORG, so comparing
        it reported a transport confound between two arms that shared one."""
        from data_sheets_schema.runs import ARM_PROCEDURE_FIELDS, arm_confounds, arm_facts
        names = [n for n, _ in ARM_PROCEDURE_FIELDS]
        self.assertIn("runtime", names)
        self.assertNotIn("provider", names)
        self.assertNotIn(("model", "provider"), [f for _, f in ARM_PROCEDURE_FIELDS])
        with tempfile.TemporaryDirectory() as tmp:
            corpus = Path(tmp)
            def record(prefix, runtime, provider):
                folder = corpus / "claudecode_agent_core" / f"{prefix}_rep1"
                folder.mkdir(parents=True)
                (folder / "CHORUS_provenance.yaml").write_text(yaml.safe_dump({
                    "run": {"project": "CHORUS", "label": f"{prefix}_rep1", "method": "claudecode_agent",
                            "condition": "generic_v9"},
                    "model": {"model": "claude-opus-5", "agent_runtime": runtime, "provider": provider},
                    "schema": {"digest_md5": "d", "profile": "bridge2ai"},
                    "prompts": {"assembly": {"sha256": "a"}}}))
            record("2026-08-28_a", "Claude Code", "Anthropic")
            record("2026-09-01_b", "Claude Code", "LBL CBORG (proxy to Anthropic)")
            record("2026-09-22_c", DIRECT, DIRECT_PROVIDER)
            agentic = arm_facts("2026-08-28_a", concat_dir=corpus)
            proxied = arm_facts("2026-09-01_b", concat_dir=corpus)
            direct = arm_facts("2026-09-22_c", concat_dir=corpus)
            self.assertEqual(agentic["labels"], ["2026-08-28_a_rep1"])
            self.assertEqual(arm_confounds(agentic, proxied), [])            # provider alone is no row
            self.assertEqual([c["field"] for c in arm_confounds(agentic, direct)], ["runtime"])

    def test_method_resolution_finds_a_label_under_the_direct_family(self):
        from data_sheets_schema.runs import method_for_label
        with tempfile.TemporaryDirectory() as root:
            corpus = Path(root) / "d4d_concatenated"
            (corpus / "claudecode_direct_core" / "2026-09-22_d_rep1").mkdir(parents=True)
            (corpus / "claudecode_agent_core" / "2026-09-22_a_rep1").mkdir(parents=True)
            self.assertEqual(method_for_label("2026-09-22_d_rep1", concat_dir=corpus), "claudecode_direct")
            self.assertEqual(method_for_label("2026-09-22_a_rep1", concat_dir=corpus), "claudecode_agent")


class ThreeRuntimeCanonicals(unittest.TestCase):
    """A project marked under all three runtimes (#2210, #2211)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.corpus = Path(self.tmp.name)
        for method, label, runtime in (("claudecode_agent", "2026-08-28_a_rep1", "Claude Code"),
                                       ("claudecode_api", "2026-09-04f_b_rep1", "Claude API (direct)"),
                                       ("claudecode_direct", "2026-09-22_d_rep1", DIRECT)):
            folder = self.corpus / f"{method}_core" / label
            folder.mkdir(parents=True)
            for name in ("CHORUS_d4d.yaml", "CHORUS_d4d_core.yaml"):
                (folder / name).write_text("id: https://example.org/x\n")
            (folder / "CHORUS_provenance.yaml").write_text(yaml.safe_dump({
                "run": {"project": "CHORUS", "label": label, "method": method},
                "model": {"agent_runtime": runtime},
                "canonical": {"criterion": "validity → coverage → label", "selected_from": [label]},
                "outputs": {"full": {"path": str(folder / "CHORUS_d4d.yaml")},
                            "core": {"path": str(folder / "CHORUS_d4d_core.yaml")}}}))

    def test_canonical_sets_enumerates_every_runtime_key(self):
        from data_sheets_schema.runs import RUNTIME_CHOICES, canonical_sets
        sets = canonical_sets(concat_dir=self.corpus)
        self.assertEqual(list(sets), list(RUNTIME_CHOICES))
        self.assertEqual({rt: found["CHORUS"]["label"] for rt, found in sets.items()},
                         {"api": "2026-09-04f_b_rep1", "agentic": "2026-08-28_a_rep1", "direct": "2026-09-22_d_rep1"})

    def test_the_ambiguity_hint_names_every_runtime_and_the_direct_key_resolves_it(self):
        from data_sheets_schema.runs import AmbiguousCanonical, canonical_runs
        with self.assertRaises(AmbiguousCanonical) as caught:
            canonical_runs(concat_dir=self.corpus)
        self.assertIn("'direct'", str(caught.exception))
        self.assertIn("[direct]", str(caught.exception))
        self.assertEqual(canonical_runs(concat_dir=self.corpus, runtime="direct")["CHORUS"]["label"], "2026-09-22_d_rep1")

    def test_every_runtime_option_offers_the_direct_key(self):
        from data_sheets_schema.cli.evaluate import evaluate
        from data_sheets_schema.cli.runs import runs
        from data_sheets_schema.runs import RUNTIME_CHOICES
        commands = [runs.commands["canonical"], runs.commands["redundancy"],
                    evaluate.commands["plan"], evaluate.commands["related-datasets"]]
        for command in commands:
            option = next(p for p in command.params if p.name == "runtime")
            self.assertEqual(list(option.type.choices), list(RUNTIME_CHOICES), command.name)


class ReasoningLogStatus(unittest.TestCase):
    """#2212: the direct arm writes no log of its own and may carry the transcript's measure, like the agentic arm."""

    def test_the_direct_runtime_reads_as_the_agentic_one_does(self):
        from data_sheets_schema.reasoning import NO_LOG_MISSING, NO_LOG_RUNTIME, RECOVERED, log_status
        for runtime in ("Claude Code", DIRECT):
            with self.subTest(runtime=runtime):
                self.assertEqual(log_status(runtime, "2026-09-22_x_rep1", False), NO_LOG_RUNTIME)
                self.assertEqual(log_status(runtime, "2026-09-22_x_rep1", False, {"output_tokens": 5}), RECOVERED)
        self.assertEqual(log_status("Claude API (direct)", "2026-09-22_x_rep1", False), NO_LOG_MISSING)


class HeaderBasisForTheDirectRuntime(unittest.TestCase):
    """#2213: a header effort or temperature on the direct runtime is the agent's assertion, as on the agentic one."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cwd = os.getcwd()
        self.addCleanup(os.chdir, self.cwd)
        os.chdir(self.tmp.name)
        self.label, self.method = "2026-09-22_direct_rep1", "claudecode_direct"
        self.concat = Path("data/d4d_concatenated")
        self.full_dir = self.concat / self.method / self.label
        self.core_dir = self.concat / f"{self.method}_core" / self.label
        self.full_dir.mkdir(parents=True)
        self.core_dir.mkdir(parents=True)
        Path("src/data_sheets_schema").mkdir(parents=True, exist_ok=True)
        self.bundle = Path("bundle.txt")
        self.bundle.write_text("source documents\n")
        body = yaml.safe_dump({"id": "https://example.org/x", "name": "x"})
        for path in (self.full_dir / "TESTPROJ_d4d.yaml", self.core_dir / "TESTPROJ_d4d_core.yaml"):
            path.write_text(header("claude-opus-5", DIRECT, "max") + body)
        (self.core_dir / "TESTPROJ_reconciliation.md").write_text("# r\n")

    def _record(self, **kw):
        from data_sheets_schema import provenance
        return provenance.build_record("TESTPROJ", self.method, self.label, mode="live", input_bundle=self.bundle,
                                       input_verified=True, concat_dir=self.concat, **kw).data

    def test_a_header_effort_that_disagrees_with_the_launcher_flag_is_noted_not_erased(self):
        """#2221: the header route walked past the #2216 gate silently."""
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CLAUDE_EFFORT", None)
            data = self._record(reasoning_effort="high")
        self.assertEqual(data["model"]["reasoning_effort"], "max")            # the header stays recorded
        notes = [n for n in (data.get("notes") or []) if "Reasoning effort mismatch" in n]
        self.assertEqual(len(notes), 1)
        self.assertIn("header says 'max'", notes[0])
        self.assertIn("says 'high'", notes[0])                                   # two statements (#2256)
        self.assertIn("not observed", notes[0])
        gap = [u for u in data["unverified"] if u["field"] == "model.reasoning_effort"]
        self.assertEqual(len(gap), 1)
        self.assertIn("disagree", gap[0]["reason"])
        # The block names the standing the header has and never double-reports (#2257).
        with mock.patch.dict(os.environ, {"CLAUDE_EFFORT": "max"}):
            corroborated = self._record(reasoning_effort="high")
        self.assertTrue(corroborated["model"]["reasoning_effort_basis"].startswith("observed"))
        [note] = [n for n in (corroborated.get("notes") or []) if "Reasoning effort mismatch" in n]
        self.assertIn("corroborated by CLAUDE_EFFORT", note)
        [gap] = [u for u in corroborated["unverified"] if u["field"] == "model.reasoning_effort"]
        self.assertIn("corroborated", gap["reason"]) ; self.assertNotIn("neither observed", gap["reason"])
        with mock.patch.dict(os.environ, {"CLAUDE_EFFORT": "low"}):
            twice = self._record(reasoning_effort="high")
        [gap] = [u for u in twice["unverified"] if u["field"] == "model.reasoning_effort"]
        self.assertIn("CLAUDE_EFFORT reads 'low'", gap["reason"])
        self.assertIn("Also, the header says 'max'", gap["reason"])
        # An agreeing flag adds nothing.
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CLAUDE_EFFORT", None)
            agreeing = self._record(reasoning_effort="max")
        self.assertEqual([n for n in (agreeing.get("notes") or []) if "effort mismatch" in n.lower()], [])
        self.assertEqual([u for u in agreeing["unverified"] if u["field"] == "model.reasoning_effort"], [])

    def test_a_silent_environment_leaves_both_values_asserted_and_named_as_gaps(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CLAUDE_EFFORT", None)
            data = self._record()
        model = data["model"]
        self.assertEqual(model["agent_runtime"], DIRECT)
        self.assertEqual(model["reasoning_effort"], "max")
        self.assertEqual(model["reasoning_effort_basis"], "asserted by the generating agent, not observed")
        self.assertEqual(model["temperature_basis"], "asserted by the generating agent, not observed")
        # The same standing the agentic runtime's header values have: the
        # temperature is a named gap, the effort is asserted and corroborable.
        self.assertIn("model.temperature", {u["field"] for u in data["unverified"]})

    def test_an_agreeing_environment_corroborates_the_effort(self):
        with mock.patch.dict(os.environ, {"CLAUDE_EFFORT": "max"}):
            data = self._record()
        self.assertIn("observed", data["model"]["reasoning_effort_basis"])
        self.assertNotIn("model.reasoning_effort", {u["field"] for u in data["unverified"]})


class AssertedEffort(unittest.TestCase):
    def test_the_recorder_admits_the_session_levels_and_the_ladder_agrees(self):
        from data_sheets_schema.cli.provenance import EFFORT_CHOICES
        from data_sheets_schema.provenance import _EFFORT_LADDER
        self.assertEqual(tuple(EFFORT_CHOICES), _EFFORT_LADDER)
        self.assertEqual(_EFFORT_LADDER[-2:], ("xhigh", "max"))

    def test_a_rendered_recorder_line_carries_the_asserted_effort_and_nothing_else_moves(self):
        from data_sheets_schema.api_runner import RunSpec
        # Renderer 3: below the versions whose replay requires recorded
        # artifact paths and toolchain, which are not what this test pins.
        common = dict(project="CHORUS", arm="baseline", method="claudecode_direct", bundle=Path("x"),
                      label="2026-09-22_x_rep1", condition="generic_v9", manifest=None, render_version=3,
                      run_date="2026-09-22", runtime=DIRECT, provider=DIRECT_PROVIDER, _replay_only=True)
        without = RunSpec(**common).render_spec()
        with_effort = RunSpec(**common, reasoning_effort="max").render_spec()
        self.assertNotIn("reasoning_effort", without)
        self.assertEqual(with_effort.pop("reasoning_effort"), "max")
        self.assertEqual(with_effort, without)          # the only difference is the one key
        restored = RunSpec.from_render_spec({**without, "reasoning_effort": "max"}, project="CHORUS",
                                            method="claudecode_direct", label="2026-09-22_x_rep1")
        self.assertEqual(restored.reasoning_effort, "max")
        self.assertIsNone(RunSpec.from_render_spec(without, project="CHORUS", method="claudecode_direct",
                                                   label="2026-09-22_x_rep1").reasoning_effort)


def recorder_line(instruction):
    lines = [line.strip() for line in instruction.splitlines() if " provenance record " in line]
    assert len(lines) == 1, lines
    return lines[0]


def test_the_production_renderer_emits_the_effort_on_the_recorder_line_only_when_asserted(native):  # noqa: F811
    """#2217: through `resolve_prompt`, not a copy of it."""
    from data_sheets_schema.api_runner import resolve_prompt
    spec, _, _ = native
    direct = replace(spec, runtime=DIRECT, provider=DIRECT_PROVIDER)
    without = recorder_line(resolve_prompt(direct))
    with_effort = recorder_line(resolve_prompt(replace(direct, reasoning_effort="max")))
    assert "--reasoning-effort" not in without

    def split(line):
        tokens = shlex.split(line)
        at = tokens.index("--render-spec-json")
        payload = json.loads(tokens[at + 1])
        return tokens[:at] + tokens[at + 2:], payload
    plain, plain_spec = split(without)
    asserted, asserted_spec = split(with_effort)
    at = asserted.index("--reasoning-effort")
    assert asserted[at + 1] == "max"
    assert asserted[:at] + asserted[at + 2:] == plain                 # the flag pair is the only difference
    assert asserted_spec.pop("reasoning_effort") == "max" and asserted_spec == plain_spec
    assert "# Agent runtime: Claude Code (direct)" in resolve_prompt(direct)
    assert f"# Provider: {DIRECT_PROVIDER}" in resolve_prompt(direct)


@pytest.fixture
def direct_native(native, tmp_path):  # noqa: F811
    """The registered native fixture re-rendered for the direct arm with an asserted effort."""
    from data_sheets_schema.cli import cli
    spec, sent, command = native
    direct = replace(spec, runtime=DIRECT, provider=DIRECT_PROVIDER, reasoning_effort="max")
    instruction = direct.instruction
    sent_direct = tmp_path / "exact direct launch instruction.txt"
    sent_direct.write_text(instruction)
    header_text = (f"# Agent runtime: {DIRECT}\n# Provider: {DIRECT_PROVIDER}\n"
                   "# Model: synthetic-model\n# Temperature: not observed\n")
    for path in (direct.full_path, direct.core_path):
        path.write_text(header_text + "id: https://example.org/cohort\nname: Example\n")
    argv = shlex.split(recorder_line(instruction))
    argv[-1] = str(sent_direct)
    return direct, argv[3:], cli


def test_the_gate_takes_the_registered_effort_when_the_copied_line_dropped_the_flag(direct_native):
    """#2216: the recorder line is copied by hand; a dropped flag must not drop the asserted effort."""
    direct, command, cli = direct_native
    at = command.index("--reasoning-effort")
    assert command[at + 1] == "max"
    dropped = command[:at] + command[at + 2:]
    result = CliRunner().invoke(cli, dropped)
    assert result.exit_code == 0, (result.output, result.exception)
    record = yaml.safe_load(direct.provenance_path.read_text())
    assert record["model"]["reasoning_effort"] == "max"
    assert record["model"]["reasoning_effort_basis"].startswith("asserted by the launcher")
    assert record["model"]["agent_runtime"] == DIRECT
    assert record["prompts"]["request"]["spec"]["reasoning_effort"] == "max"


def test_the_gate_refuses_an_effort_that_disagrees_with_the_registered_specification(direct_native):
    direct, command, cli = direct_native
    at = command.index("--reasoning-effort")
    result = CliRunner().invoke(cli, command[:at + 1] + ["high"] + command[at + 2:])
    assert result.exit_code != 0
    assert "--reasoning-effort conflicts with the registered specification" in result.output   # the flag's own spelling
    assert not direct.provenance_path.exists()


def test_a_specification_asserting_an_unknown_effort_is_refused(direct_native):
    """#2255: the specification route bypassed the flag's closed choice."""
    import json
    direct, command, cli = direct_native
    at = command.index("--render-spec-json") + 1
    spec = json.loads(command[at])
    for bogus in ("bogus", "Max", ""):
        forged = command[:at] + [json.dumps({**spec, "reasoning_effort": bogus})] + command[at + 1:]
        result = CliRunner().invoke(cli, forged)
        assert result.exit_code != 0, bogus
        assert ("invalid recorded reasoning effort" in result.output) or (bogus == "" and "does not reproduce" in result.output), (bogus, result.output)
        assert not direct.provenance_path.exists()
    from data_sheets_schema.api_runner import RunSpec
    with pytest.raises(ValueError, match="invalid recorded reasoning effort"):
        RunSpec.from_render_spec({**spec, "reasoning_effort": "maximum"}, project=direct.project, method=direct.method,
                                 label=direct.label)


def test_the_renderer_3_receipt_section_renders_for_both_claude_code_runtimes(external):  # noqa: F811
    """#2259: the one exact 'Claude Code' comparison left outside AGENTIC_RUNTIMES."""
    from data_sheets_schema import api_runner as api
    marker = "<!-- D4D prompt renderer version 3 -->"
    tails = {}
    for runtime in ("Claude Code", DIRECT, "Codex CLI"):
        body = api.resolve_prompt(replace(external, runtime=runtime, render_version=3, chunk_manifest=external.chunk_manifest))
        tails[runtime] = body.split(marker, 1)[1]
    assert tails["Claude Code"] == tails[DIRECT] and tails[DIRECT].strip()
    assert tails["Codex CLI"] != tails[DIRECT]


def test_a_specification_that_asserts_no_effort_binds_none(native):  # noqa: F811
    """An existing registered launch may still state an effort, recorded as the launcher's own assertion, as before."""
    from data_sheets_schema.cli import cli
    spec, _, command = native
    result = CliRunner().invoke(cli, command + ["--reasoning-effort", "high"])
    assert result.exit_code == 0, (result.output, result.exception)
    record = yaml.safe_load(spec.provenance_path.read_text())
    assert record["model"]["reasoning_effort"] == "high"
    assert record["model"]["reasoning_effort_basis"].startswith("asserted by the launcher")
    assert "reasoning_effort" not in record["prompts"]["request"]["spec"]


@pytest.mark.parametrize("version", [1, 2, 3])
def test_backfill_spec_recovers_a_direct_runtime_record(external, monkeypatch, version):  # noqa: F811
    """The candidate loop admits the direct runtime as an agentic one instead of raising (#2226)."""
    import hashlib
    from data_sheets_schema import api_runner as api, provenance as pv
    from data_sheets_schema.cli import cli
    from data_sheets_schema.runs import verify_request
    spec = replace(external, runtime=DIRECT, provider=DIRECT_PROVIDER, render_version=version, chunk_manifest=None)
    body = api.resolve_prompt(spec)
    render = spec.render_spec()
    if version == 1:
        del render["render_version"]
    data = {"run": {"project": spec.project, "method": spec.method, "label": spec.label},
            "model": {"provider": render["provider"], "agent_runtime": DIRECT}, "record_generated_at": spec.run_date,
            "inputs": {"bundle_path": str(spec.bundle), "source_manifest": {"path": str(spec.manifest)},
                       "chunks": {"path": str(external.chunk_manifest)}},
            "prompts": {"request": {"sha256": hashlib.sha256(body.encode()).hexdigest()}}}
    monkeypatch.setattr(pv, "CONCAT_DIR", spec.out_dir)
    path = pv.record_path_for(spec.project, spec.method, spec.label, spec.out_dir)
    path.parent.mkdir(parents=True)
    path.write_text(yaml.safe_dump(data))
    result = CliRunner().invoke(cli, ["provenance", "backfill-spec", "--project", spec.project, "--method", spec.method,
                                      "--label", spec.label, "--condition", spec.condition, "--runtime", DIRECT,
                                      "--execute"])
    assert result.exit_code == 0, (result.output, result.exception)
    assert verify_request(spec.method, spec.label, spec.project, spec.out_dir)[0] == "match"
    recovered = yaml.safe_load(path.read_text())["prompts"]["request"]["spec"]
    assert recovered["render_version"] == version and recovered["runtime"] == DIRECT


class PlaybookWording(unittest.TestCase):
    def test_the_playbooks_name_the_direct_runtime_and_dictate_no_provider_string(self):
        root = Path(__file__).resolve().parents[1]
        core = (root / ".claude/commands/d4d-full-core.md").read_text(encoding="utf-8")
        agent = (root / ".claude/commands/d4d-agent.md").read_text(encoding="utf-8")
        self.assertNotIn("`Provider: Anthropic`", core)
        self.assertIn("exactly as the launch\n  instruction header states them", core)
        # The substitution table lists the direct runtime and provider beside
        # the existing values, so a model cannot normalise one to another (#2220).
        self.assertIn("`Claude Code (direct)`", core)
        self.assertIn(f"`{DIRECT_PROVIDER}`", core)
        self.assertIn("never shorten one to another", core)
        self.assertNotIn("# Provider: {Anthropic|OpenAI}", agent)
        # No `{...}` token outside the substitution vocabulary (#2220).
        self.assertIn("# Agent runtime: {RUNTIME}\n# Provider: {PROVIDER}\n", agent)
        self.assertNotIn("{as the launch", agent)
        # The agent playbook defines the two tokens itself; it is a standalone method (#2227).
        self.assertIn("`{RUNTIME}` and `{PROVIDER}` are the `Agent runtime` and `Provider` lines", agent)
        self.assertIn("`Claude Code (direct)`", agent)
        # The registered-specification rule for the effort is stated where the flag is explained (#2225).
        self.assertIn("Under a registered specification that asserts an effort", core)


if __name__ == "__main__":
    unittest.main()

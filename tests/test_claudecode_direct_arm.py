"""The third generation arm's registry entries and record identity (#2202).

`claudecode_direct` is Claude Code on the maintainer's subscription, direct
to Anthropic: same runtime as the agentic arm, different provider. These
tests pin what tells the two apart in code, and that nothing existing moved.
"""
import shlex
import unittest
from pathlib import Path


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
        from data_sheets_schema.runs import RUNTIME_KEYS, runtime_of
        self.assertEqual(runtime_of({"model": {"agent_runtime": "Claude Code (direct)"}}), "direct")
        self.assertEqual(runtime_of({"model": {"agent_runtime": "Claude Code"}}), "agentic")
        self.assertEqual(runtime_of({"model": {"agent_runtime": "Claude API (direct)"}}), "api")
        self.assertEqual(set(RUNTIME_KEYS.values()), {"agentic", "api", "direct"})

    def test_the_direct_runtime_still_reads_playbooks_and_follows_the_agentic_spec(self):
        from data_sheets_schema.api_runner import RunSpec
        from data_sheets_schema.provenance import runtime_reads_playbooks
        self.assertTrue(runtime_reads_playbooks("Claude Code (direct)"))
        spec = RunSpec(project="CHORUS", arm="baseline", method="claudecode_direct", bundle=Path("x"),
                       label="2026-09-22_x_rep1", condition="generic_v9", manifest=None, render_version=9,
                       run_date="2026-09-22", runtime="Claude Code (direct)", provider="Anthropic (direct)",
                       _replay_only=True)
        self.assertTrue(spec.is_agentic)

    def test_provider_is_an_arm_procedure_field(self):
        from data_sheets_schema.runs import ARM_PROCEDURE_FIELDS
        self.assertIn(("provider", ("model", "provider")), ARM_PROCEDURE_FIELDS)

    def test_method_resolution_finds_a_label_under_the_direct_family(self):
        import tempfile
        from data_sheets_schema.runs import method_for_label
        with tempfile.TemporaryDirectory() as root:
            corpus = Path(root) / "d4d_concatenated"
            (corpus / "claudecode_direct_core" / "2026-09-22_d_rep1").mkdir(parents=True)
            (corpus / "claudecode_agent_core" / "2026-09-22_a_rep1").mkdir(parents=True)
            self.assertEqual(method_for_label("2026-09-22_d_rep1", concat_dir=corpus), "claudecode_direct")
            self.assertEqual(method_for_label("2026-09-22_a_rep1", concat_dir=corpus), "claudecode_agent")


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
                      run_date="2026-09-22", runtime="Claude Code (direct)", provider="Anthropic (direct)",
                      _replay_only=True)
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

    def test_the_recorder_line_substitution_appends_the_flag_only_when_asserted(self):
        import re
        from data_sheets_schema import api_runner
        from data_sheets_schema.api_runner import RunSpec
        body = "    poetry run d4d provenance record --project {PROJECT}\n"
        common = dict(project="CHORUS", arm="baseline", method="claudecode_direct", bundle=Path("x"),
                      label="2026-09-22_x_rep1", condition="generic_v9", manifest=None, render_version=9,
                      run_date="2026-09-22", runtime="Claude Code (direct)", provider="Anthropic (direct)",
                      _replay_only=True)
        for effort, expected in ((None, ""), ("max", " --reasoning-effort max")):
            spec = RunSpec(**common, reasoning_effort=effort)
            def recording_command(match, spec=spec):
                command = match.group(1)
                command += " --manifest none"
                if spec.reasoning_effort:
                    command += " --reasoning-effort " + shlex.quote(spec.reasoning_effort)
                return command
            rendered = re.sub(r"(?m)^([ \t]*(?:poetry run )?d4d provenance record[^\n]*)$", recording_command, body)
            self.assertTrue(rendered.rstrip().endswith("--manifest none" + expected))


class PlaybookWording(unittest.TestCase):
    def test_the_playbooks_no_longer_dictate_a_provider_string(self):
        root = Path(__file__).resolve().parents[1]
        core = (root / ".claude/commands/d4d-full-core.md").read_text(encoding="utf-8")
        agent = (root / ".claude/commands/d4d-agent.md").read_text(encoding="utf-8")
        self.assertNotIn("`Provider: Anthropic`", core)
        self.assertIn("exactly as the launch\n  instruction header states them", core)
        self.assertNotIn("# Provider: {Anthropic|OpenAI}", agent)


if __name__ == "__main__":
    unittest.main()

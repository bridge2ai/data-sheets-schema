"""Render the agentic instruction instead of typing it (#419, #422).

The API path never types an instruction: `resolve_prompt()` builds it from a
`RunSpec`, so the condition, the substitutions and any per-project content are
functions of declared inputs. The agentic path had no way to obtain that text,
so its launch prompts were hand-composed — and the VOICE run of 2026-08-07 was
sent a project-specific scope paragraph that appears in no prompt file, while
its provenance recorded the base file and the record header said "identical for
all projects".

Rendering closes that by construction rather than by discipline: per-project
content can only enter through `--condition tuned`, which is a declared door
the record names.
"""

import hashlib
import unittest
from pathlib import Path

from click.testing import CliRunner

from data_sheets_schema.api_runner import RunSpec, resolve_prompt
from data_sheets_schema.cli.api import ARMS, api

BUNDLE = Path("data/preprocessed/concatenated/VOICE_preprocessed.txt")


def _spec(**kw):
    # The method follows the arm, as the command's own spec does (#690, D6):
    # `{METHOD}` is substituted into the text, so a hand-pinned method here
    # would hash a different request from the one the command renders.
    base = dict(project="VOICE", arm="BASELINE (input documents only)",
                method=ARMS["baseline"][1], bundle=BUNDLE,
                label="2026-08-10_test_rep1", condition="generic_v3")
    base.update(kw)
    return RunSpec(**base)


class TestTheRuntimeIsAParameter(unittest.TestCase):
    """It was a module constant, so the rendered header always said
    "Claude API (direct)" — useless for rendering an instruction another
    runtime will execute."""

    def test_the_runtime_appears_in_the_rendered_header(self):
        text = resolve_prompt(_spec(runtime="Claude Code"))
        self.assertIn("# Agent runtime: Claude Code", text)

    def test_the_default_is_unchanged_for_the_api_path(self):
        from data_sheets_schema.api_runner import RUNTIME
        self.assertEqual(RUNTIME, _spec().runtime)

    def test_the_provider_is_a_parameter_too(self):
        """`provider_identity()` reports the endpoint *this process* is
        configured against, which rendered "LBL CBORG (proxy to Anthropic)"
        into a Claude Code header — a provider that run never touches."""
        text = resolve_prompt(_spec(runtime="Claude Code", provider="Anthropic"))
        self.assertIn("# Provider: Anthropic", text)
        self.assertNotIn("CBORG", text)


@unittest.skipUnless(BUNDLE.exists(), "bundles not present")
class TestRenderedInstructionsAreComplete(unittest.TestCase):

    def test_nothing_is_left_unsubstituted(self):
        """v2 introduced `{DATE}` and nothing substituted it, so the literal
        string reached the model."""
        import re
        for condition in ("generic", "generic_v2", "generic_v3", "generic_v4"):
            with self.subTest(condition=condition):
                text = resolve_prompt(_spec(condition=condition,
                                            runtime="Claude Code"))
                self.assertEqual([], re.findall(r"\{[A-Z_]+\}", text))

    def test_the_generic_conditions_name_no_project_they_were_not_given(self):
        """The project appears only where it was substituted in. Any other GC
        name would mean per-project content in a generic condition."""
        text = resolve_prompt(_spec(condition="generic_v3", runtime="Claude Code"))
        for other in ("AI_READI", "CHORUS", "CM4AI"):
            with self.subTest(other=other):
                self.assertNotIn(other, text)


@unittest.skipUnless(BUNDLE.exists(), "bundles not present")
class TestTheCommand(unittest.TestCase):

    def _run(self, *args):
        return CliRunner(mix_stderr=False).invoke(
            api, ["render-prompt", "--project", "VOICE",
                  "--label", "2026-08-10_test_rep1", *args])

    def test_it_prints_the_instruction_on_stdout(self):
        r = self._run("--condition", "generic_v3")
        self.assertEqual(r.exit_code, 0, r.stderr)
        self.assertIn("Generate paired full and core D4D records", r.stdout)

    def test_stdout_is_the_instruction_alone_so_it_can_be_piped(self):
        """Commentary goes to stderr; a caller redirecting stdout to a file
        must get the instruction and nothing else."""
        r = self._run("--condition", "generic_v3")
        self.assertNotIn("sha256", r.stdout)
        self.assertIn("sha256", r.stderr)

    def test_the_digest_is_of_the_resolved_text_not_the_file(self):
        """Substitution is what makes the file and the request different
        objects, which is why the request needs its own hash."""
        r = self._run("--condition", "generic_v3", "--runtime", "Claude Code")
        # Claude Code writes under claudecode_agent, the default for that runtime (#5063).
        expected = hashlib.sha256(
            resolve_prompt(_spec(condition="generic_v3", method="claudecode_agent",
                                 runtime="Claude Code",
                                 provider="Anthropic")).encode()).hexdigest()
        self.assertIn(expected, r.stderr)

    def test_an_unknown_condition_is_refused(self):
        r = self._run("--condition", "no-such-condition")
        self.assertNotEqual(r.exit_code, 0)

    def test_method_overrides_the_baseline_directory_for_agentic_runs(self):
        """#690 moved `ARMS["baseline"][1]` to `claudecode_api`, leaving
        `d4d prompt render` unable to render the `claudecode_agent` paths that
        an agentic baseline run actually writes (#5046)."""
        from data_sheets_schema import runs
        label = "2026-10-14_claude-opus-5-generic-v8_rep1"
        r = CliRunner(mix_stderr=False).invoke(
            api, ["render-prompt", "--project", "VOICE",
                  "--label", label, "--condition", "generic_v8",
                  "--method", "claudecode_agent"])
        self.assertEqual(r.exit_code, 0, r.stderr)
        self.assertIn(f"data/d4d_concatenated/claudecode_agent/{label}/VOICE_d4d.yaml", r.stdout)
        self.assertIn(f"data/d4d_concatenated/claudecode_agent_core/{label}/VOICE_d4d_core.yaml", r.stdout)
        self.assertNotIn("claudecode_api", r.stdout)

        expected_spec = _spec(
            label=label, condition="generic_v8",
            method="claudecode_agent", runtime="Claude Code", provider="Anthropic",
            manifest_line=ARMS["baseline"][3],
        )
        reconstructed = RunSpec.from_render_spec(
            expected_spec.render_spec(),
            project="VOICE", method="claudecode_agent", label=label,
        )
        expected_digest = hashlib.sha256(resolve_prompt(reconstructed).encode("utf-8")).hexdigest()
        self.assertIn(expected_digest, r.stderr)

    def test_method_conflicting_with_explicit_arm_is_refused(self):
        r = self._run("--condition", "generic_v3", "--arm", "de_novo", "--method", "claudecode_agent")
        self.assertNotEqual(r.exit_code, 0)
        self.assertIn("conflicts with --arm", r.stderr)

    def test_a_runtime_contradicting_the_method_is_warned(self):
        """#5046 review: a method that contradicts the runtime is said where
        the instruction is obtained. Since #5063 an omitted --method follows the
        runtime, so only an explicit contradiction warns."""
        label = "2026-10-14_claude-opus-5-generic-v8_rep1"
        base = ["render-prompt", "--project", "VOICE", "--label", label, "--condition", "generic_v8"]
        for extra, warned in ((["--runtime", "Claude Code", "--method", "claudecode_api"],
                               "an agentic run writes under claudecode_agent/"),
                              (["--runtime", "Claude Code", "--method", "claudecode_direct"],
                               "pass --method claudecode_agent"),
                              (["--runtime", "Claude Code (direct)", "--method", "claudecode_agent"],
                               "pass --method claudecode_direct"),
                              (["--runtime", "Claude API (direct)", "--method", "claudecode_direct"], "(#5046)")):
            with self.subTest(extra=extra):
                r = CliRunner(mix_stderr=False).invoke(api, base + extra)
                self.assertEqual(r.exit_code, 0, r.stderr)
                self.assertIn(warned, r.stderr)
        for extra in (["--runtime", "Claude Code", "--method", "claudecode_agent"],
                      ["--runtime", "Claude Code"], [],
                      ["--runtime", "Claude API (direct)"],
                      ["--runtime", "Claude Code (direct)"],
                      ["--runtime", "Claude Code (direct)", "--method", "claudecode_direct"]):
            with self.subTest(extra=extra):
                r = CliRunner(mix_stderr=False).invoke(api, base + extra)
                self.assertEqual(r.exit_code, 0, r.stderr)
                self.assertNotIn("#5046", r.stderr)

    def test_the_api_runtime_with_the_agent_directory_is_warned_from_v8(self):
        """#5068: from generic_v8 the API baseline writes under claudecode_api
        (#690); through v7 both runtimes wrote under claudecode_agent."""
        api_rt = ["--runtime", "Claude API (direct)", "--method", "claudecode_agent"]
        for condition, label, warned in (
                ("generic_v8", "2026-10-14_claude-opus-5-api-generic-v8_rep1", True),
                ("generic_v9", "2026-10-14_claude-opus-5-api-generic-v9_rep1", True),
                ("generic_v7", "2026-08-28c_claude-opus-5-api-generic-v7_rep1", False)):
            with self.subTest(condition=condition):
                r = CliRunner(mix_stderr=False).invoke(api, [
                    "render-prompt", "--project", "VOICE", "--label", label,
                    "--condition", condition, *api_rt])
                self.assertEqual(r.exit_code, 0, r.stderr)
                if warned:
                    self.assertIn("pass --method claudecode_api", r.stderr)
                else:
                    self.assertNotIn("#5046", r.stderr)

    def test_an_omitted_method_follows_the_runtime(self):
        """#5063 F1/F2 (owner, 2026-10-19): the playbook renders without
        --method, so the default is the directory the runtime writes under.
        The rendered text is the same as with that method passed explicitly."""
        cases = (  # (condition, runtime args, label, method the run writes under)
            ("generic_v8", [], "2026-10-14_claude-opus-5-generic-v8_rep1", "claudecode_agent"),
            ("generic_v8", ["--runtime", "Claude Code"], "2026-10-14_claude-opus-5-generic-v8_rep1", "claudecode_agent"),
            ("generic_v6", ["--runtime", "Claude Code"], "2026-08-28_claude-opus-5-claudecode-generic-v6_rep9", "claudecode_agent"),
            ("generic_v8", ["--runtime", "Claude Code (direct)"], "2026-10-14_claude-opus-5-direct-generic-v8_rep1", "claudecode_direct"),
            ("generic_v8", ["--runtime", "Claude API (direct)"], "2026-10-14_claude-opus-5-api-generic-v8_rep1", "claudecode_api"),
            ("generic_v9", ["--runtime", "Claude API (direct)"], "2026-10-14_claude-opus-5-api-generic-v9_rep1", "claudecode_api"),
            ("generic_v7", ["--runtime", "Claude API (direct)"], "2026-08-28c_claude-opus-5-api-generic-v7_rep1", "claudecode_agent"),
            ("generic_v8", ["--runtime", "Some Other Runtime"], "2026-10-14_claude-opus-5-generic-v8_rep1", "claudecode_api"),
        )
        for condition, runtime, label, method in cases:
            with self.subTest(condition=condition, runtime=runtime):
                base = ["render-prompt", "--project", "VOICE", "--label", label, "--condition", condition, *runtime]
                omitted = CliRunner(mix_stderr=False).invoke(api, base)
                explicit = CliRunner(mix_stderr=False).invoke(api, base + ["--method", method])
                self.assertEqual(omitted.exit_code, 0, omitted.stderr)
                self.assertIn(f"data/d4d_concatenated/{method}/{label}/VOICE_d4d.yaml", omitted.stdout)
                self.assertEqual(omitted.stdout, explicit.stdout)

    def test_another_arm_keeps_its_own_method(self):
        r = CliRunner(mix_stderr=False).invoke(api, [
            "render-prompt", "--project", "VOICE", "--label", "2026-10-14_claude-opus-5-generic-v8_rep1",
            "--condition", "generic_v8", "--arm", "de_novo", "--runtime", "Claude Code"])
        if r.exit_code == 0:
            self.assertIn("claudecode_agent_crate/", r.stdout)
            self.assertNotIn("claudecode_agent/", r.stdout.replace("claudecode_agent_crate/", ""))
        else:   # no crate bundle in this checkout: refused before any method is used
            self.assertNotIn("conflicts with --arm", r.stderr)


if __name__ == "__main__":
    unittest.main()


class TestTheInstructionIsResolvedOnce(unittest.TestCase):
    """Raised reviewing #425.

    `resolve_prompt` was called at send time and again when the provenance
    record was built after the last phase. It reads `provider_identity()` and
    `_model_settings()`, so anything moving in between would have the record
    attest a prompt that was never sent — the same failure `run_date` is frozen
    to avoid, on a six-phase run that takes tens of minutes.
    """

    def test_the_same_spec_returns_the_same_object(self):
        s = _spec(runtime="Claude Code")
        self.assertIs(s.instruction, s.instruction)

    def test_it_does_not_re_read_the_environment(self):
        """The record is built after the phases; if settings moved in between,
        re-rendering would attest something else."""
        import data_sheets_schema.api_runner as ar
        s = _spec(runtime="Claude Code")
        first = s.instruction
        original = ar._model_settings
        ar._model_settings = lambda condition=None: {"name": "SOME-OTHER-MODEL",
                                                     "temperature": 0.0}
        try:
            self.assertEqual(first, s.instruction)
            self.assertNotIn("SOME-OTHER-MODEL", s.instruction)
        finally:
            ar._model_settings = original

    def test_a_different_spec_resolves_separately(self):
        a = _spec(runtime="Claude Code")
        b = _spec(runtime="Codex CLI")
        self.assertNotEqual(a.instruction, b.instruction)
        self.assertIn("Codex CLI", b.instruction)

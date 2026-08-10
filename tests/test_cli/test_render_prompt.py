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
from data_sheets_schema.cli.api import api

BUNDLE = Path("data/preprocessed/concatenated/VOICE_preprocessed.txt")


def _spec(**kw):
    base = dict(project="VOICE", arm="BASELINE (input documents only)",
                method="claudecode_agent", bundle=BUNDLE,
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
        expected = hashlib.sha256(
            resolve_prompt(_spec(condition="generic_v3",
                                 runtime="Claude Code",
                                 provider="Anthropic")).encode()).hexdigest()
        self.assertIn(expected, r.stderr)

    def test_an_unknown_condition_is_refused(self):
        r = self._run("--condition", "no-such-condition")
        self.assertNotEqual(r.exit_code, 0)


if __name__ == "__main__":
    unittest.main()

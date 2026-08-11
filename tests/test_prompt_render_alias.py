"""`d4d prompt render` — the rendering command, where its audience will look.

`d4d api render-prompt` exists so the *agentic* path can obtain its instruction
rather than compose one by hand, and it lived under the group for generating
records through the API. The command an agentic run needs was filed under the
path it is not taking (#428).

Aliased rather than reimplemented. Two renderers free to disagree is exactly the
failure #425 was built to remove.
"""

import unittest

from click.testing import CliRunner

from data_sheets_schema.cli import cli


class TestPromptRenderAlias(unittest.TestCase):
    ARGS = ["--project", "CHORUS", "--label", "2026-08-11_alias_rep1",
            "--condition", "generic"]

    def _run(self, *argv):
        return CliRunner().invoke(cli, list(argv))

    def test_the_group_is_discoverable_from_the_top_level(self):
        result = self._run("--help")
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("prompt", result.output)

    def test_render_produces_an_instruction(self):
        result = self._run("prompt", "render", *self.ARGS)
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("rendered generic for CHORUS", result.output)

    def test_both_spellings_produce_identical_output(self):
        """One implementation. A copy would be free to drift, and two
        renderers that disagree is the failure #425 removed."""
        alias = self._run("prompt", "render", *self.ARGS)
        original = self._run("api", "render-prompt", *self.ARGS)
        self.assertEqual(alias.exit_code, 0, alias.output)
        self.assertEqual(original.exit_code, 0, original.output)
        self.assertEqual(alias.output, original.output)

    def test_it_is_the_same_command_object(self):
        """Not merely equal today — the same object, so it cannot diverge."""
        from data_sheets_schema.cli.api import api, render_prompt_cmd
        from data_sheets_schema.cli.prompt import prompt

        self.assertIs(prompt.commands["render"], render_prompt_cmd)
        self.assertIs(api.commands["render-prompt"], render_prompt_cmd)

    def test_the_original_still_works(self):
        """Aliasing must not move it: labels, scripts and the API playbook
        already name the original."""
        result = self._run("api", "render-prompt", *self.ARGS)
        self.assertEqual(result.exit_code, 0, result.output)

    def test_the_agentic_playbook_names_the_discoverable_spelling(self):
        """The playbook is what an agentic run reads, so it is where the
        command has to be named for the fix to reach its audience."""
        from pathlib import Path

        playbook = Path(".claude/commands/d4d-full-core.md")
        if not playbook.exists():
            self.skipTest("playbook absent")
        self.assertIn("d4d prompt render", playbook.read_text(encoding="utf-8"))

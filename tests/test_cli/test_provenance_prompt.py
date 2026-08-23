"""`d4d provenance record --prompt` — hash the prompt into the record.

The recorder builds its `prompts` block from `prompt_paths`, and `d4d api run`
has always passed it (`api_runner.py`, `prompt_paths=spec.prompt_files`). The
CLI — the only route the Claude Code agentic path has — did not expose it, so
every agentic record in the corpus carried `prompts: null` while every API
record carried hashes. The same procedure was reproducible from one and not the
other.

That gap bites hardest here specifically: the study these records feed compares
a generic prompt condition against a tuned one, and the generic prompt file's
own editing rule says a change to it re-baselines the arm for every project at
once. A record that names its prompt but does not hash it cannot detect that.
"""

import os
import tempfile
import unittest
from pathlib import Path

import yaml
from click.testing import CliRunner


HEADER = """\
# D4D Datasheet for TESTPROJ Dataset
# Agent runtime: Claude Code
# Provider: Anthropic
# Model: claude-opus-5
# Reasoning effort: high
# Temperature: 0.0
"""


class TestProvenancePromptFlag(unittest.TestCase):
    def setUp(self):
        from data_sheets_schema.cli import provenance as prov_cli

        self.cli = prov_cli.provenance
        self.runner = CliRunner()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

        self.label = "2026-08-07_test_rep1"
        self.method = "claudecode_agent"
        concat = self.root / "data" / "d4d_concatenated"
        full_dir = concat / self.method / self.label
        core_dir = concat / f"{self.method}_core" / self.label
        full_dir.mkdir(parents=True)
        core_dir.mkdir(parents=True)
        # marker the repo-root guard (#672) requires; the scratch root
        # stands in for the repo by design in these tests
        (self.root / "src" / "data_sheets_schema").mkdir(parents=True, exist_ok=True)

        body = yaml.safe_dump({"id": "https://example.org/x", "name": "x"})
        (full_dir / "TESTPROJ_d4d.yaml").write_text(HEADER + body)
        (core_dir / "TESTPROJ_d4d_core.yaml").write_text(HEADER + body)
        (core_dir / "TESTPROJ_reconciliation.md").write_text("# report\n")

        self.bundle = self.root / "bundle.txt"
        self.bundle.write_text("source documents\n")
        self.prompt = self.root / "arm_prompt.md"
        self.prompt.write_text("# generic arm prompt\n")

        self.concat = concat

    def tearDown(self):
        self.tmp.cleanup()

    def _record(self, *extra):
        args = ["record", "--project", "TESTPROJ", "--method", self.method,
                "--label", self.label, "--input-bundle", str(self.bundle),
                *extra]
        # The recorder's paths are repo-relative module constants bound as
        # default arguments, so they follow the working directory rather than
        # a patched attribute.
        cwd = os.getcwd()
        os.chdir(self.root)
        try:
            return self.runner.invoke(self.cli, args)
        finally:
            os.chdir(cwd)

    def _written(self):
        p = (self.concat / f"{self.method}_core" / self.label
             / "TESTPROJ_provenance.yaml")
        return yaml.safe_load(p.read_text())

    def test_prompt_is_hashed_into_the_record(self):
        result = self._record("--prompt", str(self.prompt))
        self.assertEqual(result.exit_code, 0, result.output)

        prompts = self._written()["prompts"]
        self.assertEqual(prompts["hash_algorithm"], "sha256")
        self.assertEqual(len(prompts["files"]), 1)
        entry = prompts["files"][0]
        # Normalised, not verbatim (#398). These fixtures live outside the
        # repository, so the recorded path stays absolute — but it is resolved,
        # which on macOS turns /var/... into /private/var/... . One file must
        # not be recordable under two strings, inside the repo or out.
        self.assertEqual(entry["path"], str(self.prompt.resolve()))
        self.assertTrue(entry["exists"])
        self.assertEqual(entry["bytes"], self.prompt.stat().st_size)
        self.assertEqual(len(entry["sha256"]), 64)

    def test_repeated_prompt_flags_are_all_recorded(self):
        second = self.root / "component.md"
        second.write_text("# per-project component\n")

        result = self._record("--prompt", str(self.prompt),
                              "--prompt", str(second))
        self.assertEqual(result.exit_code, 0, result.output)

        files = self._written()["prompts"]["files"]
        self.assertEqual([f["path"] for f in files],
                         [str(self.prompt.resolve()), str(second.resolve())])
        # The tuned condition is prompt + component; two files that hash the
        # same would mean the component never made it into the record.
        self.assertNotEqual(files[0]["sha256"], files[1]["sha256"])

    def test_without_the_flag_the_block_says_so_rather_than_going_missing(self):
        result = self._record()
        self.assertEqual(result.exit_code, 0, result.output)

        prompts = self._written()["prompts"]
        self.assertIsNone(prompts["paths"])
        self.assertIn("not recoverable", prompts["note"])

    def test_a_missing_prompt_file_fails_instead_of_recording_a_false_path(self):
        result = self._record("--prompt", str(self.root / "nope.md"))
        self.assertNotEqual(result.exit_code, 0)
        # A live record asserting a prompt path that does not exist is the
        # same class of false claim the module refuses for input bundles.
        self.assertNotIn("nope.md", str(self._probe_written()))

    def _probe_written(self):
        p = (self.concat / f"{self.method}_core" / self.label
             / "TESTPROJ_provenance.yaml")
        return p.read_text() if p.exists() else ""


if __name__ == "__main__":
    unittest.main()


class TestTheRequestIsRecordedNotJustTheFile(unittest.TestCase):
    """#419. The file is not the instruction — substitution turns one into the
    other, and on the agentic path a human turned it into something else again.

    The VOICE run of 2026-08-07 was sent a project-specific scope paragraph
    that appears in no prompt file, while the record hashed the file and its
    header said "identical for all projects". Recording the resolved text is
    what makes that difference detectable instead of merely discouraged.
    """

    def setUp(self):
        from data_sheets_schema.cli import provenance as prov_cli
        self.cli = prov_cli.provenance
        self.runner = CliRunner()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.label, self.method = "2026-08-10_test_rep1", "claudecode_agent"
        concat = self.root / "data" / "d4d_concatenated"
        (concat / self.method / self.label).mkdir(parents=True)
        (concat / f"{self.method}_core" / self.label).mkdir(parents=True)
        # marker the repo-root guard (#672) requires; the scratch root
        # stands in for the repo by design in these tests
        (self.root / "src" / "data_sheets_schema").mkdir(parents=True, exist_ok=True)
        body = yaml.safe_dump({"id": "https://example.org/x", "name": "x"})
        (concat / self.method / self.label / "P_d4d.yaml").write_text(body)
        (concat / f"{self.method}_core" / self.label / "P_d4d_core.yaml").write_text(body)
        (concat / f"{self.method}_core" / self.label
         / "P_reconciliation.md").write_text("# r\n")
        self.bundle = self.root / "b.txt"; self.bundle.write_text("docs\n")
        self.base = self.root / "base.md"; self.base.write_text("# base\n")
        self.sent = self.root / "sent.txt"
        self.sent.write_text("Generate paired records for the P project.\n")
        self.concat = concat

    def tearDown(self):
        self.tmp.cleanup()

    def _record(self, *extra):
        args = ["record", "--project", "P", "--method", self.method,
                "--label", self.label, "--input-bundle", str(self.bundle), *extra]
        cwd = os.getcwd(); os.chdir(self.root)
        try:
            return self.runner.invoke(self.cli, args)
        finally:
            os.chdir(cwd)

    def _prompts(self):
        p = (self.concat / f"{self.method}_core" / self.label
             / "P_provenance.yaml")
        return yaml.safe_load(p.read_text())["prompts"]

    def test_the_sent_instruction_is_hashed_alongside_the_file(self):
        import hashlib
        r = self._record("--prompt", str(self.base),
                         "--prompt-text", str(self.sent))
        self.assertEqual(r.exit_code, 0, r.output)
        pr = self._prompts()
        self.assertEqual(1, len(pr["files"]), "the base file is still recorded")
        self.assertEqual(
            hashlib.sha256(self.sent.read_bytes()).hexdigest(),
            pr["request"]["sha256"])
        self.assertEqual(self.sent.stat().st_size, pr["request"]["bytes"])

    def test_the_two_hashes_differ_which_is_the_whole_point(self):
        r = self._record("--prompt", str(self.base),
                         "--prompt-text", str(self.sent))
        self.assertEqual(r.exit_code, 0, r.output)
        pr = self._prompts()
        self.assertNotEqual(pr["files"][0]["sha256"], pr["request"]["sha256"])

    def test_without_the_flag_no_request_is_claimed(self):
        """Absent is honest; an absent block must not be filled with the file's
        hash, which would assert the two were the same."""
        self._record("--prompt", str(self.base))
        self.assertNotIn("request", self._prompts())

    def test_the_request_can_be_recorded_without_a_base_file(self):
        """An agentic run may know what it was sent and not which file it came
        from — that is still strictly more than recording nothing."""
        self._record("--prompt-text", str(self.sent))
        pr = self._prompts()
        self.assertIsNone(pr["paths"])
        self.assertIn("request", pr)

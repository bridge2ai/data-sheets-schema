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
        # marker the old repo-root guard (#672) required; kept since #1301
        # narrowed the guard, so the scratch root
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
        # marker the old repo-root guard (#672) required; kept since #1301
        # narrowed the guard, so the scratch root
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


class TestMidnightCrossingRunDate(unittest.TestCase):
    """#5049: An agentic run rendered before UTC midnight (`# Generated: 2026-10-14`)
    and recorded after midnight (`2026-10-15`) must record the launch `run_date`
    rather than the recorder process's `date.today()`, so the render gate verifies
    `match` instead of failing with a 1-day `mismatch`."""

    def test_prompt_text_header_and_window_recover_midnight_run_date(self):
        from unittest import mock
        from data_sheets_schema.api_runner import RunSpec, resolve_prompt
        from data_sheets_schema.cli import provenance as prov_cli
        from data_sheets_schema.cli.api import ARMS

        repo_root = Path(__file__).resolve().parents[2]
        bundle = repo_root / "data/preprocessed/concatenated/VOICE_preprocessed.txt"
        if not bundle.exists():
            self.skipTest("VOICE bundle absent")

        label = "2026-10-14_claude-opus-5-generic-v8_rep1"
        spec_prev_day = RunSpec(
            project="VOICE",
            arm=ARMS["baseline"][0],
            method="claudecode_agent",
            bundle=bundle,
            label=label,
            condition="generic_v8",
            runtime="Claude Code",
            provider="Anthropic",
            run_date="2026-10-14",
            manifest_line=ARMS["baseline"][3],
        )
        sent = resolve_prompt(spec_prev_day)
        self.assertIn("# Generated: 2026-10-14", sent)

        with tempfile.TemporaryDirectory() as tmp:
            prompt_file = Path(tmp) / "rendered_prompt.txt"
            prompt_file.write_text(sent, encoding="utf-8")
            fake_rec = mock.MagicMock(validation_carried=None)
            fake_rec.write.return_value = repo_root / "VOICE_provenance.yaml"

            with mock.patch("data_sheets_schema.provenance.build_record", return_value=fake_rec) as build, \
                 mock.patch.object(prov_cli, "_recorded_receipt_origin", return_value=None), \
                 mock.patch.object(prov_cli, "_inline_checks"):
                r = CliRunner().invoke(
                    prov_cli.provenance,
                    [
                        "record",
                        "--project", "VOICE",
                        "--method", "claudecode_agent",
                        "--label", label,
                        "--input-bundle", str(bundle),
                        "--condition", "generic_v8",
                        "--runtime", "Claude Code",
                        "--provider", "Anthropic",
                        "--prompt-text", str(prompt_file),
                    ],
                )
            self.assertEqual(r.exit_code, 0, r.output)
            saved_spec = build.call_args.kwargs["prompt_request_spec"]
            self.assertEqual(saved_spec["run_date"], "2026-10-14")
            reconstructed = RunSpec.from_render_spec(
                saved_spec, project="VOICE", method="claudecode_agent", label=label
            )
            self.assertEqual(resolve_prompt(reconstructed), sent)

    def test_explicit_run_date_flag_sets_spec_run_date_and_rejects_bad_dates(self):
        from unittest import mock
        from data_sheets_schema.cli import provenance as prov_cli

        repo_root = Path(__file__).resolve().parents[2]
        bundle = repo_root / "data/preprocessed/concatenated/VOICE_preprocessed.txt"
        if not bundle.exists():
            self.skipTest("VOICE bundle absent")

        label = "2026-10-14_claude-opus-5-generic-v8_rep1"
        fake_rec = mock.MagicMock(validation_carried=None)
        fake_rec.write.return_value = repo_root / "VOICE_provenance.yaml"
        with mock.patch("data_sheets_schema.provenance.build_record", return_value=fake_rec) as build, \
             mock.patch.object(prov_cli, "_recorded_receipt_origin", return_value=None), \
             mock.patch.object(prov_cli, "_inline_checks"):
            r = CliRunner().invoke(
                prov_cli.provenance,
                [
                    "record",
                    "--project", "VOICE",
                    "--method", "claudecode_agent",
                    "--label", label,
                    "--input-bundle", str(bundle),
                    "--condition", "generic_v8",
                    "--runtime", "Claude Code",
                    "--provider", "Anthropic",
                    "--run-date", "2026-10-14",
                ],
            )
        self.assertEqual(r.exit_code, 0, r.output)
        self.assertEqual(build.call_args.kwargs["prompt_request_spec"]["run_date"], "2026-10-14")

        bad = CliRunner().invoke(
            prov_cli.provenance,
            [
                "record",
                "--project", "VOICE",
                "--method", "claudecode_agent",
                "--label", label,
                "--input-bundle", str(bundle),
                "--condition", "generic_v8",
                "--run-date", "not-a-date",
            ],
        )
        self.assertNotEqual(bad.exit_code, 0)
        self.assertIn("--run-date", bad.output)



class TestRunDateRecoveryPaths(unittest.TestCase):
    """#5049 review: each recovery path isolated, with the recorder's clock
    frozen so the label date or today's date cannot rescue a broken path."""

    LABEL = "2026-10-14_claude-opus-5-generic-v8_rep1"

    def setUp(self):
        self.repo_root = Path(__file__).resolve().parents[2]
        self.bundle = self.repo_root / "data/preprocessed/concatenated/VOICE_preprocessed.txt"
        if not self.bundle.exists():
            self.skipTest("VOICE bundle absent")
        self.sent = self._render(self.LABEL)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.prompt_file = Path(tmp.name) / "rendered_prompt.txt"

    def _render(self, label):
        # Rendered under the label it is recorded under, on 2026-10-14.
        from data_sheets_schema.api_runner import RunSpec, resolve_prompt
        from data_sheets_schema.cli.api import ARMS
        return resolve_prompt(RunSpec(
            project="VOICE", arm=ARMS["baseline"][0], method="claudecode_agent",
            bundle=self.bundle, label=label, condition="generic_v8",
            runtime="Claude Code", provider="Anthropic", run_date="2026-10-14",
            manifest_line=ARMS["baseline"][3]))

    def _record(self, label, text=None, today="2026-10-20", extra=(), runtime="Claude Code"):
        import datetime as _dt
        from unittest import mock
        from data_sheets_schema.cli import provenance as prov_cli

        class FrozenDate(_dt.date):
            @classmethod
            def today(cls):
                return _dt.date.fromisoformat(today)

        self.prompt_file.write_text(self._render(label) if text is None else text, encoding="utf-8")
        fake_rec = mock.MagicMock(validation_carried=None)
        fake_rec.write.return_value = self.repo_root / "VOICE_provenance.yaml"
        with mock.patch("datetime.date", FrozenDate), \
             mock.patch("data_sheets_schema.provenance.build_record", return_value=fake_rec) as build, \
             mock.patch.object(prov_cli, "_recorded_receipt_origin", return_value=None), \
             mock.patch.object(prov_cli, "_inline_checks"):
            r = CliRunner().invoke(prov_cli.provenance, [
                "record", "--project", "VOICE", "--method", "claudecode_agent",
                "--label", label, "--input-bundle", str(self.bundle),
                "--condition", "generic_v8", "--runtime", runtime,
                "--provider", "Anthropic", "--prompt-text", str(self.prompt_file), *extra])
        return r, build

    def test_a_non_canonical_runtime_records_the_spec_render_prompt_used(self):
        """#5091 R1: render-prompt reads `--runtime 'claude code'` as 'Claude Code'.
        The recorder must too, or a pair given the same spelling records a spec
        that re-renders to other text and the gate reports a false mismatch."""
        import datetime as _dt
        import hashlib
        from data_sheets_schema.api_runner import RunSpec, resolve_prompt
        from data_sheets_schema.cli.api import api as api_cli

        canonical = None
        for spelling in ("Claude Code", "claude code", " Claude Code ", "CLAUDE CODE"):
            with self.subTest(runtime=spelling):
                rendered = CliRunner(mix_stderr=False).invoke(api_cli, [
                    "render-prompt", "--project", "VOICE", "--label", self.LABEL,
                    "--condition", "generic_v8", "--runtime", spelling, "--method", "claudecode_agent",
                    "--provider", "Anthropic", "--bundle", str(self.bundle), "--out", str(self.prompt_file)])
                self.assertEqual(rendered.exit_code, 0, rendered.stderr)
                sent = self.prompt_file.read_text(encoding="utf-8")
                canonical = canonical or sent
                self.assertEqual(sent, canonical)   # the 'Claude Code' instruction
                # Recorded the day it was rendered, with the same spelling.
                r, build = self._record(self.LABEL, text=sent, today=_dt.date.today().isoformat(),
                                        runtime=spelling)
                self.assertEqual(r.exit_code, 0, r.output)
                spec = build.call_args.kwargs["prompt_request_spec"]
                self.assertIsNotNone(spec, r.output)
                self.assertEqual(spec["runtime"], "Claude Code")
                replay = RunSpec.from_render_spec(spec, project="VOICE", method="claudecode_agent", label=self.LABEL)
                self.assertEqual(hashlib.sha256(resolve_prompt(replay).encode()).hexdigest(),
                                 hashlib.sha256(sent.encode()).hexdigest())

    def test_indented_generated_header_alone_recovers_the_date(self):
        # Neither today (10-20) nor the label (none) is within ±2 days of the
        # render date, so only the `# Generated:` line can supply it.
        self.assertIn("    # Generated: 2026-10-14", self.sent)
        r, build = self._record("nodate_claude-opus-5-generic-v8_rep1")
        self.assertEqual(r.exit_code, 0, r.output)
        self.assertEqual(build.call_args.kwargs["prompt_request_spec"]["run_date"], "2026-10-14")

    def test_utc_midnight_crossing_with_a_far_label_date(self):
        # Recorded the next day, under a label dated four days earlier.
        r, build = self._record("2026-10-10_claude-opus-5-generic-v8_rep1", today="2026-10-15")
        self.assertEqual(r.exit_code, 0, r.output)
        self.assertEqual(build.call_args.kwargs["prompt_request_spec"]["run_date"], "2026-10-14")

    def test_an_edited_text_records_its_claimed_date_so_the_gate_sees_it(self):
        # #5068: with no spec the gate says `unverifiable`, which --strict
        # passes; the text's own # Generated: date makes the edit a mismatch.
        r, build = self._record(self.LABEL, text=self.sent + "\n")
        self.assertEqual(r.exit_code, 0, r.output)
        self.assertEqual(build.call_args.kwargs["prompt_request_spec"]["run_date"], "2026-10-14")
        self.assertIn("render gate will report a mismatch", r.output)

    def _blind_header(self):
        """The recorder's # Generated: extractor misses the header (as the
        unindented pattern did, #5049 review F6), so only the ±day search can
        find the date (#5068 F7). The rendered text itself is untouched."""
        from unittest import mock
        from data_sheets_schema.cli import provenance as prov_cli
        return mock.patch.object(prov_cli, "_generated_date", return_value=None)

    def test_the_day_search_alone_recovers_a_missed_header_date(self):
        with self._blind_header():
            # Neither the label (none) nor the header (missed) gives the date;
            # only today's ±2-day window reaches it.
            r, build = self._record("nodate_claude-opus-5-generic-v8_rep1", today="2026-10-16")
        self.assertEqual(r.exit_code, 0, r.output)
        self.assertEqual(build.call_args.kwargs["prompt_request_spec"]["run_date"], "2026-10-14")

    def test_no_claimed_and_no_reproducing_date_records_no_spec_and_says_so(self):
        with self._blind_header():
            r, build = self._record(self.LABEL, text=self.sent + "\n")
        self.assertEqual(r.exit_code, 0, r.output)
        self.assertIsNone(build.call_args.kwargs["prompt_request_spec"])
        self.assertIn("no request spec recorded", r.output)

    def test_explicit_run_date_must_reproduce_the_prompt_text(self):
        r, build = self._record(self.LABEL, extra=("--run-date", "2026-10-12"))
        self.assertNotEqual(r.exit_code, 0)
        self.assertIn("does not reproduce --prompt-text", r.output)
        build.assert_not_called()
        ok, build = self._record(self.LABEL, extra=("--run-date", "2026-10-14"))
        self.assertEqual(ok.exit_code, 0, ok.output)
        self.assertEqual(build.call_args.kwargs["prompt_request_spec"]["run_date"], "2026-10-14")

    def test_non_canonical_and_unused_run_dates_are_refused(self):
        from data_sheets_schema.cli import provenance as prov_cli
        for value in ("20261014", "2026-W42-3"):
            r, _ = self._record(self.LABEL, extra=("--run-date", value))
            self.assertNotEqual(r.exit_code, 0, value)
            self.assertIn("--run-date", r.output)
        r = CliRunner().invoke(prov_cli.provenance, [
            "record", "--project", "VOICE", "--method", "claudecode_agent",
            "--label", self.LABEL, "--run-date", "2026-10-14"])
        self.assertNotEqual(r.exit_code, 0)
        self.assertIn("--condition", r.output)

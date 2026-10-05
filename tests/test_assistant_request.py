"""src/github/assistant_request.py, and the d4d-agent.yml steps around it:
the GitHub assistant workflow acts only on an explicit request line, never on
its handle quoted in prose or code (#4108)."""
import importlib.util
import io
import os
import re
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

import yaml

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "src" / "github" / "assistant_request.py"
_spec = importlib.util.spec_from_file_location("assistant_request", SCRIPT)
ar = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ar)

H = ar.HANDLE
#: The input directories #4108 names.
DATASETS = ("CHORUS", "CM4AI", "testdataset")
FIXTURES = ROOT / "tests" / "fixtures" / "assistant_request"
WORKFLOW = ROOT / ".github" / "workflows" / "d4d-agent.yml"
NOTHING = (None, None, ())


def _ask(text):
    return ar.find_request(text, DATASETS)


def _issue_4093():
    """The body of issue #4093 as GitHub returned it on 2026-10-05: a review
    issue quoting the handle twice in code spans. The workflow ran on it
    (run 36902377148), and only the backtick after the handle kept its old
    regex from reading a request."""
    return (FIXTURES / "issue_4093_body.md").read_bytes().decode("utf-8")


class TestARequestIsOneExplicitLine(unittest.TestCase):

    def test_the_handle_then_one_input_directory_is_a_request(self):
        for text, dataset, line in ((f"{H} CM4AI", "CM4AI", 1),
                                    (f"{H} CM4AI \t ", "CM4AI", 1),
                                    (f"{H}\tCHORUS", "CHORUS", 1),
                                    (f"{H.upper()} CM4AI", "CM4AI", 1),
                                    (f"Context for the run.\n\n{H} CM4AI\n\nMore context.", "CM4AI", 3),
                                    (f"Context.\r\n\r\n{H} testdataset\r\n", "testdataset", 3),
                                    (f"Context.\r\r{H} CM4AI", "CM4AI", 3)):
            with self.subTest(text=text):
                self.assertEqual(_ask(text), (dataset, line, ()))

    def test_the_issue_4093_body_is_not_a_request(self):
        body = _issue_4093()
        self.assertEqual(body.count(f"`{H}`"), 2)
        self.assertEqual(_ask(body), NOTHING)
        # Without the backticks the old detect regex matched and read the
        # rest of the line as the request; the handle is still mid-sentence.
        near = body.replace(f"`{H}`", H)
        self.assertRegex(near, re.compile(re.escape(H) + r"\s+(.*)", re.I))
        self.assertEqual(_ask(near), NOTHING)

    def test_a_handle_in_a_code_span_is_not_a_request(self):
        for text in (f"Run `{H} CM4AI` to generate it.", f"`{H} CM4AI`", f"``{H} CM4AI``",
                     f"The `{H}` workflow\n\nreads `CM4AI`."):
            with self.subTest(text=text):
                self.assertEqual(_ask(text), NOTHING)
        # a code span carried onto the next line of its paragraph
        self.assertEqual(_ask(f"Write `\n{H} CM4AI\n` to ask."),
                         (None, None, ("line 2: does not start a paragraph (the line before it is not blank)",)))

    def test_a_handle_in_a_fenced_block_is_not_a_request(self):
        for text, opened, at in ((f"```\n{H} CM4AI\n```", 1, 2),
                                 (f"```text\nAsk like this:\n\n{H} CM4AI\n```", 1, 4),
                                 (f"~~~\n\n{H} CM4AI\n~~~", 1, 3),
                                 (f"````\n```\n\n{H} CM4AI\n```\n````", 1, 4),   # a shorter run does not close it
                                 (f"```\n\n{H} CM4AI\n~~~", 1, 3),               # nor does the other character
                                 (f"```\ncode\n    ```\n\n{H} CM4AI\n```", 1, 5),  # nor one indented four spaces
                                 (f"```\n\n{H} CM4AI", 1, 3),                    # an unclosed fence runs to the end
                                 (f"Intro.\n```\n\n{H} CM4AI\n```", 2, 4)):      # a fence interrupts a paragraph
            with self.subTest(text=text):
                self.assertEqual(_ask(text),
                                 (None, None, (f"line {at}: inside the fenced code block opened on line {opened}",)))
        # once the fence closes, a request after it is read
        self.assertEqual(_ask(f"```\n{H} CHORUS\n```\n\n{H} CM4AI"),
                         ("CM4AI", 5, ("line 2: inside the fenced code block opened on line 1",)))
        # three backticks with a backtick after them are a code span, not a fence
        self.assertEqual(_ask(f"```x`y```\n\n{H} CM4AI"), ("CM4AI", 3, ()))

    def test_a_quoted_line_is_not_a_request(self):
        for text in (f"> {H} CM4AI", f">{H} CM4AI", f"> Quoted:\n>\n> {H} CM4AI", f"> > {H} CM4AI"):
            with self.subTest(text=text):
                self.assertEqual(_ask(text), NOTHING)
        # a line run on after a quote continues the quote
        self.assertFalse(_ask(f"> quoted\n{H} CM4AI").request)

    def test_a_handle_mid_sentence_is_not_a_request(self):
        # The second started a billed run before #4108: the old regex read
        # "CHORUS run failed." as the request, and CHORUS is an input directory.
        for text in (f"Please ask {H} CM4AI for a sheet.", f"The {H} CHORUS run failed.",
                     f"- {H} CM4AI", f"1. {H} CM4AI", f"| {H} CM4AI |", f"**{H} CM4AI**",
                     f"# {H} CM4AI"):
            with self.subTest(text=text):
                self.assertEqual(_ask(text), NOTHING)

    def test_an_unknown_dataset_is_not_a_request(self):
        self.assertEqual(_ask(f"{H} VOICE"), (None, None, (
            "line 1: names 'VOICE', which is not an input directory "
            "(input directories: CHORUS, CM4AI, testdataset)",)))
        # the name exactly as the directory is: no other case, quoting, path or punctuation
        for name in ("cm4ai", "CM4AI.", "`CM4AI`", "**CM4AI**", "../CM4AI", "CM4AI/", "inputs/CM4AI"):
            with self.subTest(name=name):
                self.assertFalse(_ask(f"{H} {name}").request)
        # nor a directory whose name the workflow's shell could misread
        self.assertFalse(ar.find_request(f"{H} a;b", ("a;b",)).request)

    def test_only_one_word_follows_the_handle(self):
        for text, why in ((f"{H} CM4AI please", "has more than one word after the handle ('CM4AI please')"),
                          (f"{H} generate CM4AI", "has more than one word after the handle ('generate CM4AI')"),
                          (f"{H}", "names no input directory after the handle"),
                          (f"{H}   ", "names no input directory after the handle"),
                          (f"{H}: CM4AI", "the handle is followed by ':', not a space and an input directory name"),
                          (f"{H}, CM4AI", "the handle is followed by ',', not a space and an input directory name")):
            with self.subTest(text=text):
                self.assertEqual(_ask(text), (None, None, (f"line 1: {why}",)))
        # a longer login is another account
        for text in (f"{H}bot CM4AI", f"{H}-bot CM4AI", f"{H}2 CM4AI"):
            with self.subTest(text=text):
                self.assertEqual(_ask(text), NOTHING)

    def test_a_request_starts_a_paragraph(self):
        for text in (f"Context.\n{H} CM4AI", f"- item\n{H} CM4AI", f"# Heading\n{H} CM4AI",
                     f"```\nx\n```\n{H} CM4AI"):
            with self.subTest(text=text):
                d = _ask(text)
                self.assertFalse(d.request)
                self.assertEqual(d.notes[-1][-len("does not start a paragraph (the line before it is not blank)"):],
                                 "does not start a paragraph (the line before it is not blank)")

    def test_an_indented_line_is_not_a_request(self):
        for text in (f" {H} CM4AI", f"   {H} CM4AI", f"    {H} CM4AI", f"\t{H} CM4AI", f"Text.\n\n    {H} CM4AI"):
            with self.subTest(text=text):
                self.assertEqual(_ask(text), NOTHING)

    def test_an_html_block_that_spans_blank_lines_holds_no_request(self):
        for text in (f"<!--\n\n{H} CM4AI\n\n-->", f"<!-- Ask like this:\n\n{H} CM4AI\n-->",
                     f"<pre>\n\n{H} CM4AI\n\n</pre>", f"<SCRIPT>\n\n{H} CM4AI\n</script>"):
            with self.subTest(text=text):
                self.assertEqual(_ask(text), (None, None, ("line 3: inside the HTML block opened on line 1",)))
        # one closed on its own line hides nothing after it
        self.assertEqual(_ask(f"<!-- a note -->\n\n{H} CM4AI"), ("CM4AI", 3, ()))
        self.assertEqual(_ask(f"<!--\nnote\n-->\n\n{H} CM4AI"), ("CM4AI", 5, ()))

    def test_a_text_requests_at_most_one_dataset(self):
        self.assertEqual(_ask(f"{H} CM4AI\n\n{H} CHORUS"), (None, None, (
            "line 1 (CM4AI), line 3 (CHORUS) ask for different datasets: a text may request one",)))
        self.assertEqual(_ask(f"{H} CM4AI\n\nAgain:\n\n{H} CM4AI"), ("CM4AI", 1, ()))

    def test_only_a_markdown_line_break_starts_a_line(self):
        """str.splitlines() also breaks at these; Markdown does not, so the
        handle after one is still inside the code span."""
        for sep in (" ", " ", "\x0b", "\x0c", "\x1c", "\x85"):
            with self.subTest(sep=repr(sep)):
                self.assertEqual(_ask(f"Write `x{sep}{sep}{H} CM4AI{sep}` to ask."), NOTHING)

    def test_unsure_where_a_fence_ends_it_reads_no_later_request(self):
        """Where only a list or HTML parse would place a block's end, no line
        after that point is a request (it fails closed)."""
        for text, lost in ((f"- ```\n  code\n  ```\n\n{H} CM4AI", 1),                   # opened on a list marker
                           (f"1. Run:\n   ```\nlog\n   ```\n\n{H} CM4AI", 3),            # content left of its opener
                           (f"  ```\n  code\n      ```\n\n{H} CM4AI", 3),                # closed past three spaces
                           (f"<details>\n```\ncode\n```\n</details>\n\n{H} CM4AI", 2),   # in what may be HTML
                           (f"- <!--\n  note\n  -->\n\n{H} CM4AI", 1)):                  # HTML on a list marker
            with self.subTest(text=text):
                at = text.split("\n").index(f"{H} CM4AI") + 1
                self.assertEqual(_ask(text), (None, None, (
                    f"line {at}: from line {lost} on, this reader cannot tell where a code fence or HTML "
                    "block ends",)))
        # a list item's fence that closes where it opened is followed exactly
        self.assertEqual(_ask(f"1. Run:\n\n   ```bash\n   make\n   ```\n\n{H} CM4AI"), ("CM4AI", 7, ()))
        self.assertEqual(_ask(f"<details>\n<summary>Log</summary>\n\n```\nx\n```\n\n</details>\n\n{H} CM4AI"),
                         ("CM4AI", 10, ()))


class TestTheWorkflow(unittest.TestCase):
    """d4d-agent.yml: `contains()` is only a pre-filter; the request step
    decides, and the run takes its dataset from that step alone."""

    @classmethod
    def setUpClass(cls):
        cls.text = WORKFLOW.read_text(encoding="utf-8")
        wf = yaml.safe_load(cls.text)
        cls.check, cls.respond = wf["jobs"]["check-mention"], wf["jobs"]["respond-to-mention"]
        cls.step = {s.get("id") or s["name"]: s for s in cls.check["steps"]}
        cls.respond_step = {s.get("id") or s["name"]: s for s in cls.respond["steps"]}

    def test_the_pre_filter_looks_for_the_handle_the_script_reads(self):
        literals = re.findall(r"contains\([^,]+,\s*'([^']*)'\)", self.check["if"])
        self.assertEqual(len(literals), 3)
        self.assertEqual({x.lower() for x in literals}, {H.lower()})

    def test_only_the_request_step_qualifies_a_run_and_names_its_dataset(self):
        self.assertEqual(self.check["outputs"]["qualified-mention"], "${{ steps.request.outputs.request }}")
        self.assertEqual(self.check["outputs"]["dataset"], "${{ steps.request.outputs.dataset }}")
        self.assertEqual(self.step["request"]["if"], "steps.detect.outputs.allowed == 'true'")
        self.assertEqual(self.respond["if"], "needs.check-mention.outputs.qualified-mention == 'true'")
        self.assertEqual(self.respond_step["resolve"]["env"], {"DATASET": "${{ needs.check-mention.outputs.dataset }}"})
        self.assertIn('--project "${{ steps.resolve.outputs.dataset }}"',
                      self.respond_step["Generate datasheet"]["run"])
        # nothing reads a dataset out of the request's free text any more
        self.assertNotIn("outputs.prompt", self.text)
        self.assertNotIn("mentionRegex", self.text)

    def test_the_detect_step_hands_its_text_to_the_request_step(self):
        written = re.search(r"writeFileSync\(`\$\{process\.env\.RUNNER_TEMP\}/([^`]+)`, content\)",
                            self.step["detect"]["with"]["script"])
        read = re.search(r'--body "\$RUNNER_TEMP/([^"]+)"', self.step["request"]["run"])
        self.assertIsNotNone(written)
        self.assertIsNotNone(read)
        self.assertEqual(written.group(1), read.group(1))

    def test_the_request_step_as_written(self):
        """Run the step's command as the runner does, on this checkout's input
        directories, and read the outputs it appends."""
        names = ar.declared_datasets(ROOT / "data" / "sheets_d4dassistant" / "inputs")
        self.assertTrue(names)
        body_name = re.search(r'--body "\$RUNNER_TEMP/([^"]+)"', self.step["request"]["run"]).group(1)
        cases = (("the #4093 body", _issue_4093(), "false", "", "no request"),
                 ("a request", f"Please regenerate.\n\n{H} {names[0]}\n", "true", names[0], "request: line 3"),
                 ("an unknown dataset", f"{H} not-an-input-directory\n", "false", "", "no request"))
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / "bin").mkdir()
            # this interpreter, whatever python3 is on PATH; -S leaves out
            # site-packages, as on the runner, where nothing is installed yet
            python3 = tmp / "bin" / "python3"
            python3.write_text(f'#!/bin/sh\nexec "{sys.executable}" -S "$@"\n')
            python3.chmod(0o755)
            for i, (label, text, request, dataset, logged) in enumerate(cases):
                with self.subTest(label):
                    runner_temp = tmp / f"runner{i}"
                    runner_temp.mkdir()
                    (runner_temp / body_name).write_bytes(text.encode("utf-8"))
                    out = runner_temp / "github_output"
                    env = {**os.environ, "PATH": f"{tmp / 'bin'}{os.pathsep}{os.environ.get('PATH', '')}",
                           "RUNNER_TEMP": str(runner_temp), "GITHUB_OUTPUT": str(out)}
                    run = subprocess.run(["bash", "-c", self.step["request"]["run"]], cwd=ROOT, env=env,
                                         capture_output=True, text=True)
                    self.assertEqual(run.returncode, 0, run.stderr)
                    self.assertTrue(run.stdout.startswith(logged), run.stdout)
                    self.assertEqual(out.read_text(encoding="utf-8"), f"request={request}\ndataset={dataset}\n")


class TestTheCommandLine(unittest.TestCase):

    @staticmethod
    def _main(argv, stdin):
        """(exit status, standard output, standard error) of main() reading `stdin`."""
        out, err = io.StringIO(), io.StringIO()
        with mock.patch("sys.stdin", io.StringIO(stdin)), redirect_stdout(out), redirect_stderr(err):
            try:
                status = ar.main(argv)
            except SystemExit as exc:
                status = exc.code
        return status, out.getvalue(), err.getvalue()

    def test_input_directories_are_subdirectories_with_safe_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            inputs = Path(tmp)
            for d in ("mydataset", "other.set", "has space", ".hidden", "-dash"):
                (inputs / d).mkdir()
            (inputs / "notes.txt").write_text("x")
            self.assertEqual(ar.declared_datasets(inputs), ["mydataset", "other.set"])
            self.assertEqual(self._main(["--inputs", str(inputs)], f"{H} mydataset\n"),
                             (0, "request: line 1 asks for mydataset\n", ""))
            self.assertEqual(self._main(["--inputs", str(inputs)], f"See `{H}`.\n\n{H} has\n"), (0, (
                "no request\n  line 3: names 'has', which is not an input directory "
                "(input directories: mydataset, other.set)\n"), ""))
            self.assertEqual(self._main(["--inputs", str(inputs)], "No handle here.\n"),
                             (0, "no request: no line starts with the assistant's handle\n", ""))

    def test_a_missing_inputs_directory_is_a_usage_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            status, out, err = self._main(["--inputs", str(Path(tmp) / "absent")], "")
        self.assertEqual((status, out), (2, ""))
        self.assertIn("is not a directory", err)


if __name__ == "__main__":
    unittest.main()

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
#: The rule a line that starts with the handle and does not stand alone is refused under.
STANDS_ALONE = "(a request line stands alone between blank lines, or at the start or end of the text)"


def _ask(text):
    return ar.find_request(text, DATASETS)


def _issue_4093():
    """The body of issue #4093 as GitHub returned it on 2026-10-05: a review
    issue quoting the handle twice in code spans. The workflow ran on it
    (run 36902377148), and only the backtick after the handle kept its old
    regex from reading a request."""
    return (FIXTURES / "issue_4093_body.md").read_bytes().decode("utf-8")


def _unsure(at, lost):
    """The note for line `at` once the reader has lost track at line `lost`."""
    return f"line {at}: from line {lost} on, this reader cannot tell where a code fence or HTML block ends"


def _left_open(at, first, last=None):
    """The note for line `at` after raw HTML on lines `first`-`last` that may hide it."""
    where = f"line {first} holds" if last in (None, first) else f"lines {first}-{last} hold"
    return (f"line {at}: {where} HTML whose end this reader cannot see, which may hide every later line: "
            "an unclosed comment or tag, or <textarea>, <svg>, <? or the like")


def _conflict(*asking, unread=()):
    """The note for lines that ask for different datasets, as (line, dataset)."""
    note = ", ".join(f"line {n} ({d})" for n, d in asking) + " ask for different datasets: a text may request one"
    return note + (f", and this reader cannot rule out {', '.join(f'line {n}' for n in unread)}" if unread else "")


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
                         (None, None, (f"line 2: the line before it is not blank {STANDS_ALONE}",)))

    def test_a_handle_in_a_fenced_block_is_not_a_request(self):
        for text, opened, at in ((f"```\n{H} CM4AI\n```", 1, 2),
                                 (f"```text\nAsk like this:\n\n{H} CM4AI\n```", 1, 4),
                                 (f"~~~\n\n{H} CM4AI\n~~~", 1, 3),
                                 (f"````\n```\n\n{H} CM4AI\n```\n````", 1, 4),   # a shorter run does not close it
                                 (f"```\n\n{H} CM4AI\n~~~", 1, 3),               # nor does the other character
                                 (f"```\ncode\n    ```\n\n{H} CM4AI\n```", 1, 5),  # nor one indented four spaces
                                 (f"```\n\n{H} CM4AI", 1, 3),                    # an unclosed fence runs to the end
                                 (f"Intro.\n```\n\n{H} CM4AI\n```", 2, 4),       # a fence interrupts a paragraph
                                 # nor a fence line carrying more than spaces: a closing
                                 # fence has no info string (#4426)
                                 (f"```\n```python\n\n{H} CM4AI\n\n```", 1, 4),
                                 (f"~~~\n~~~ text\n\n{H} CM4AI\n\n~~~", 1, 4),
                                 (f"```\n````x\n\n{H} CM4AI\n\n```", 1, 4),
                                 # only a backtick fence's info string may not hold a
                                 # backtick; a tilde fence's may (#4426)
                                 (f"~~~ `md`\n\n{H} CM4AI\n\n~~~", 1, 3),
                                 (f"~~~ x`y\n\n{H} CM4AI", 1, 3)):
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

    def test_the_handle_is_matched_in_ascii_letters_only(self):
        """Under IGNORECASE alone, Python's re would also take U+017F for "s"
        and U+0130 or U+0131 for "i": spellings that are not the handle, and
        that this reader does not even note (#4428)."""
        for wrong in (H.replace("s", "ſ"), H.replace("i", "ı"), H.replace("i", "İ")):
            with self.subTest(handle=ascii(wrong)):
                self.assertNotEqual(wrong, H)
                self.assertEqual(_ask(f"{wrong} CM4AI"), NOTHING)

    def test_a_request_line_stands_alone(self):
        """A blank line, or the start or end of the text, on each side. The
        note states that rule rather than a claim about Markdown: after a
        heading, a closing fence or a one-line comment, Markdown does start a
        new paragraph, and the line is still refused (#4430)."""
        for text, at in ((f"Context.\n{H} CM4AI", 2), (f"- item\n{H} CM4AI", 2), (f"> quoted\n{H} CM4AI", 2),
                         (f"# Heading\n{H} CM4AI", 2), (f"```\nx\n```\n{H} CM4AI", 4),
                         (f"<!-- note -->\n{H} CM4AI", 2),
                         # a table row needs no leading pipe (#4429)
                         (f"| a | b |\n|---|---|\n| x | y |\n{H} CM4AI", 4)):
            with self.subTest(text=text):
                self.assertEqual(_ask(text),
                                 (None, None, (f"line {at}: the line before it is not blank {STANDS_ALONE}",)))
        # Nor may its paragraph go on: with the line under it, Markdown makes
        # it a heading, a table header or the start of a sentence (#4429, #4430).
        for text, at in ((f"{H} CHORUS\n---", 1), (f"{H} CHORUS\n===", 1), (f"{H} CM4AI\n|---|", 1),
                         (f"{H} CHORUS\nruns failed again today; see the log.", 1),
                         (f"Context.\n\n{H} CM4AI\nThanks.", 3)):
            with self.subTest(text=text):
                self.assertEqual(_ask(text),
                                 (None, None, (f"line {at}: the line after it is not blank {STANDS_ALONE}",)))
        self.assertEqual(_ask(f"Context.\n\n{H} CM4AI\n\nThanks."), ("CM4AI", 3, ()))

    def test_only_spaces_and_tabs_make_a_line_blank(self):
        """CommonMark's blank line, not str.strip()'s. After a line of U+00A0,
        a form feed or other white space, the paragraph and the code span in
        it go on, so the handle is inside the code span; nor does a fence
        line ending in such a character close a fence (#4427)."""
        for space in (" ", "\f", "\v", "　", " "):
            with self.subTest(space=ascii(space)):
                self.assertEqual(_ask(f"Write `x\n{space}\n{H} CM4AI\n` to ask."),
                                 (None, None, (f"line 3: the line before it is not blank {STANDS_ALONE}",)))
                self.assertEqual(_ask(f"```\n```{space}\n\n{H} CM4AI\n\n```"),
                                 (None, None, ("line 4: inside the fenced code block opened on line 1",)))
        for space in (" ", "\t", " \t "):
            with self.subTest(space=ascii(space)):
                self.assertEqual(_ask(f"Write `x\n{space}\n{H} CM4AI"), ("CM4AI", 3, ()))

    def test_an_indented_line_is_not_a_request(self):
        for text in (f" {H} CM4AI", f"   {H} CM4AI", f"    {H} CM4AI", f"\t{H} CM4AI", f"Text.\n\n    {H} CM4AI"):
            with self.subTest(text=text):
                self.assertEqual(_ask(text), NOTHING)

    def test_an_html_block_that_spans_blank_lines_holds_no_request(self):
        """Every kind of CommonMark HTML block that ends at a marker rather
        than at a blank line (#4425): a comment; <pre>, <script>, <style> and
        <textarea> in any letter case, opened also at the end of a line; a
        processing instruction; a declaration; CDATA. A blank line follows the
        request line, so only the block keeps it from being read."""
        for text, at in ((f"<!--\n\n{H} CM4AI\n\n-->", 3), (f"<!-- Ask like this:\n\n{H} CM4AI\n-->", 3),
                         (f"<!-- e.g. <b>\n\n{H} CM4AI\n\n-->", 3),     # a ">" does not end a comment
                         (f"<pre>\n\n{H} CM4AI\n\n</pre>", 3), (f"<pre\n\n{H} CM4AI\n\n</pre>", 3),
                         (f"<pre>\n</b>\n\n{H} CM4AI\n\n</pre>", 4),    # nor does another end tag end <pre>
                         (f"<SCRIPT>\n\n{H} CM4AI\n\n</script>", 3), (f"<style>\n\n{H} CM4AI\n\n</style>", 3),
                         (f"<textarea>\n\n{H} CM4AI\n\n</textarea>", 3),
                         (f"<?\n\n{H} CM4AI\n\n?>", 3), (f"<!DOCTYPE\n\n{H} CM4AI\n\n>", 3),
                         (f"<![CDATA[\n\n{H} CM4AI\n\n]]>", 3)):
            with self.subTest(text=text):
                self.assertEqual(_ask(text), (None, None, (f"line {at}: inside the HTML block opened on line 1",)))
        # opened one to three spaces in: a list item holding it may end at the request line
        for text in (f"  <pre>\n\n{H} CM4AI\n\n</pre>", f"   <!--\n\n{H} CM4AI\n\n-->"):
            with self.subTest(text=text):
                self.assertEqual(_ask(text), (None, None, (_unsure(3, 3),)))
        # one closed on its own line hides nothing after it
        self.assertEqual(_ask(f"<!-- a note -->\n\n{H} CM4AI"), ("CM4AI", 3, ()))
        self.assertEqual(_ask(f"<!--\nnote\n-->\n\n{H} CM4AI"), ("CM4AI", 5, ()))
        self.assertEqual(_ask(f"<pre>\nx\n</pre>\n\n{H} CM4AI"), ("CM4AI", 5, ()))

    def test_raw_html_left_open_hides_every_later_line(self):
        """A comment, a tag or a quoted attribute value that raw HTML leaves
        open runs past the Markdown block holding it, and the page hides
        everything after it; so does an element such as <textarea> or <svg>,
        and a processing instruction, CDATA or "--!>" even inside a paragraph
        (#4422). No later line is a request."""
        for text, at, first, last in (
                (f"<details>\n<summary>Generation request</summary> <!-- uncomment the line below to run\n\n"
                 f"{H} CM4AI\n\n-->\n</details>", 4, 2, 2),                           # in a tag's HTML block
                (f"> <!--\n\n{H} CM4AI\n\n-->", 3, 1, 1),                             # in a block quote
                (f"- > <!--\n\n{H} CM4AI\n\n-->", 3, 1, 1),                           # in one in a list item
                (f"<!-- a --> <!-- b\n\n{H} CM4AI\n\n-->", 3, 1, 1),                 # after a closed one
                (f"<!--\nnote\n--> <!-- b\n\n{H} CM4AI\n\n-->", 5, 1, 3),             # on a comment's last line
                (f"- item\n  - nested\n\n      <!--\n\n{H} CM4AI\n\n-->", 6, 4, 4),   # in a nested list item
                (f"1.  item\n\n    <!--\n\n{H} CM4AI\n\n-->", 5, 3, 3),
                (f"10. item\n\n    <!--\n\n{H} CM4AI\n\n-->", 5, 3, 3),
                (f"<p>see</p> <!--\n\n{H} CM4AI\n\n-->", 3, 1, 1),
                (f"<pre>\n<!--\n</pre>\n\n{H} CM4AI\n\n-->", 5, 1, 3),                # it swallows the </pre>
                (f'<div title="\n\n{H} CM4AI\n\n">', 3, 1, 1),                        # an attribute value
                (f'<div title = "x>y\n\n{H} CM4AI\n\n">', 3, 1, 1),                   # one after "=" and spaces
                (f'<p>a</p> <!x <a b="> <!-- ">\n\n{H} CM4AI', 3, 1, 1),              # a bogus comment ends at ">"
                (f"<div><textarea>\n\n{H} CM4AI\n\n</textarea></div>", 3, 1, 1),
                (f"<svg>\n\n{H} CM4AI", 3, 1, 1),
                (f"Text <textarea> more\n\n{H} CM4AI", 3, 1, 1),                     # inline, in a paragraph
                (f"`<!--` <textarea> `-->`\n\n{H} CM4AI", 3, 1, 1),                  # between code spans
                (f"a <? b > <!-- ?>\n\n{H} CM4AI", 3, 1, 1),                         # ends at the first ">"
                (f"x <![CDATA[ a > <!-- ]]>\n\n{H} CM4AI", 3, 1, 1),                 # so does CDATA
                (f'<!-- a --!> <a title=" -->\n\n{H} CM4AI', 3, 1, 1),               # a comment ends at "--!>",
                (f'Text <!-- a --!> <a title=" -->\n\n{H} CM4AI', 3, 1, 1)):         # also inline
            with self.subTest(text=text):
                self.assertEqual(_ask(text), (None, None, (_left_open(at, first, last),)))

    def test_raw_html_that_closes_hides_nothing(self):
        """Raw HTML that closes by the HTML tokenizer's rules leaves later
        lines readable (#4422)."""
        for text, line in ((f"<!-- a --> <!-- b -->\n\n{H} CM4AI", 3),
                           (f"<details>\n<summary>Log</summary> <!-- c -->\n\n{H} CM4AI", 4),
                           (f"> <!-- quoted note -->\n\n{H} CM4AI", 3),
                           (f"<!-->\n\n{H} CM4AI", 3), (f"<!--->\n\n{H} CM4AI", 3),   # comments that end at once
                           (f"<!DOCTYPE html>\n\n{H} CM4AI", 3),
                           (f'<img width="500" alt="a > b" src="x.png">\n\n{H} CM4AI', 3),  # ">" in a quoted value
                           (f'<a "b>\n\n{H} CM4AI', 3),         # a quote in an attribute name opens nothing
                           (f"<a b=c\"d>\n\n{H} CM4AI", 3),     # nor one in an unquoted value
                           (f"<a b='x\"y'>\n\n{H} CM4AI", 3),
                           # a paragraph shows an unclosed comment, or a "<" before a letter, as text
                           (f"Use <!-- to open a comment.\n\n{H} CM4AI", 3),
                           (f"Compare a<b and List<String>.\n\n{H} CM4AI", 3)):
            with self.subTest(text=text):
                self.assertEqual(_ask(text), ("CM4AI", line, ()))

    def test_a_text_requests_at_most_one_dataset(self):
        self.assertEqual(_ask(f"{H} CM4AI\n\n{H} CHORUS"), (None, None, (_conflict((1, "CM4AI"), (3, "CHORUS")),)))
        # every line that asks is named, also one repeating a dataset (#4431)
        self.assertEqual(_ask(f"{H} CM4AI\n\n{H} CHORUS\n\n{H} CM4AI"),
                         (None, None, (_conflict((1, "CM4AI"), (3, "CHORUS"), (5, "CM4AI")),)))
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
                self.assertEqual(_ask(text), (None, None, (_unsure(at, lost),)))
        # a list item's fence that closes where it opened is followed exactly
        self.assertEqual(_ask(f"1. Run:\n\n   ```bash\n   make\n   ```\n\n{H} CM4AI"), ("CM4AI", 7, ()))
        self.assertEqual(_ask(f"<details>\n<summary>Log</summary>\n\n```\nx\n```\n\n</details>\n\n{H} CM4AI"),
                         ("CM4AI", 10, ()))

    def test_a_line_past_where_the_reader_loses_track_still_cancels(self):
        """It is not a request, but a line there that would ask for another
        dataset still cancels a request before it: a text whose requests
        conflict holds none, wherever they are (#4423)."""
        for text, lost, at in ((f"{H} CM4AI\n\n- ```\n  log\n  ```\n\n{H} CHORUS", 3, 7),   # a fence on a list marker
                               (f"{H} CM4AI\n\n- <!--\n  log\n  -->\n\n{H} CHORUS", 3, 7),  # a comment on one
                               (f"{H} CM4AI\n\n<details>\n```\nlog\n```\n</details>\n\n{H} CHORUS", 4, 9)):
            with self.subTest(text=text):
                self.assertEqual(_ask(text), (None, None, (
                    _unsure(at, lost), _conflict((1, "CM4AI"), (at, "CHORUS"), unread=(at,)))))
        # also after raw HTML that may hide it
        self.assertEqual(_ask(f"{H} CM4AI\n\n<!-- a --> <!-- b\n\n{H} CHORUS"), (None, None, (
            _left_open(5, 3), _conflict((1, "CM4AI"), (5, "CHORUS"), unread=(5,)))))
        # nothing cancels it that could not ask for another dataset under any reading
        for text in (f"{H} CM4AI\n\n- ```\n  log\n  ```\n\n{H} CM4AI",          # the same dataset
                     f"{H} CM4AI\n\n- ```\n  log\n  ```\n\n{H} CHORUS\nmore",   # a line that does not stand alone
                     f"{H} CM4AI\n\n- ```\n  log\n  ```\nText.\n{H} CHORUS",
                     f"{H} CM4AI\n\n- ```\n  log\n  ```\n\n{H} VOICE"):         # no input directory
            with self.subTest(text=text):
                self.assertEqual(_ask(text), ("CM4AI", 1, (_unsure(7, 3),)))


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
        inputs = ROOT / "data" / "sheets_d4dassistant" / "inputs"
        names = [n for n in ar.input_directories(inputs) if ar.NAME.fullmatch(n)]
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

    def test_input_directories_are_the_subdirectories(self):
        with tempfile.TemporaryDirectory() as tmp:
            inputs = Path(tmp)
            for d in ("mydataset", "other.set", "has space", ".hidden", "-dash", "_private"):
                (inputs / d).mkdir()
            (inputs / "notes.txt").write_text("x")
            self.assertEqual(ar.input_directories(inputs),
                             ["-dash", ".hidden", "_private", "has space", "mydataset", "other.set"])
            self.assertEqual(self._main(["--inputs", str(inputs)], f"{H} mydataset\n"),
                             (0, "request: line 1 asks for mydataset\n", ""))
            self.assertEqual(self._main(["--inputs", str(inputs)], f"See `{H}`.\n\n{H} has\n"), (0, (
                "no request\n  line 3: names 'has', which is not an input directory "
                "(input directories: mydataset, other.set)\n"), ""))
            # a directory whose name the workflow's shell commands could misread
            # is still named as one, with the rule its name breaks (#4433)
            for name in (".hidden", "-dash", "_private"):
                with self.subTest(name=name):
                    self.assertEqual(self._main(["--inputs", str(inputs)], f"{H} {name}\n"), (0, (
                        f"no request\n  line 1: names {name!r}, an input directory a request cannot name: the "
                        "workflow passes the name to shell commands, so it must match "
                        "[A-Za-z0-9][A-Za-z0-9_.-]*\n"), ""))
            self.assertEqual(self._main(["--inputs", str(inputs)], "No handle here.\n"),
                             (0, "no request: no line starts with the assistant's handle\n", ""))

    def test_a_missing_inputs_directory_is_a_usage_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            status, out, err = self._main(["--inputs", str(Path(tmp) / "absent")], "")
        self.assertEqual((status, out), (2, ""))
        self.assertIn("is not a directory", err)


if __name__ == "__main__":
    unittest.main()

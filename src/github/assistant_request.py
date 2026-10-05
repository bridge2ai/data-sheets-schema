#!/usr/bin/env python3
"""Decide whether an issue, pull request or comment text asks the D4D
assistant workflow (`.github/workflows/d4d-agent.yml`) for a datasheet (#4108).

The workflow used to act on any text holding the assistant's handle followed
by whitespace, and read the rest of that line as the request: a review issue
that quoted the handle could start a billed `d4d api run` and open a pull
request. On #4093 only the backtick right after the handle prevented it. A
request is now one explicit line, and nothing else is one:

- the line reads exactly: the assistant's handle at its very start (any
  letter case), spaces or tabs, then the name of one directory under the
  inputs directory, spelled as the directory is; only spaces or tabs follow;
- it starts a paragraph: it is the first line of the text or follows a blank
  line. No code span, inline HTML comment or quotation continues across a
  blank line, and after one a list item continues only on indented lines,
  so such a line cannot sit inside any of them;
- it lies outside fenced code blocks, and outside the HTML blocks that run
  past a blank line (a comment, <pre>, <script>, <style>, <textarea>, a
  processing instruction, a declaration, CDATA).

A quoted (`>`) line, a list item, an indented code block or a table row does
not start with the handle, so none of them is a request. A text whose
request lines name different datasets holds no request.

This reads lines, not a Markdown tree. Where it cannot tell where a fence or
an HTML block ends without parsing lists or HTML (one opened on a list
marker; one whose content runs left of its indented opening line; an
indented fence closed by a line indented past three spaces; a fence or HTML
block opened in a paragraph that may itself be an HTML block), it reads no
later line as a request. It fails closed: a missed request costs a re-post,
a false one a billed run.

Run by the workflow's "Read the request" step:

    python3 src/github/assistant_request.py \\
        --inputs data/sheets_d4dassistant/inputs \\
        --body "$RUNNER_TEMP/assistant-request-text.md" \\
        --github-output "$GITHUB_OUTPUT"

It logs `request: ...`, or `no request` with the reason each line that starts
with the handle is not one, and, with --github-output, appends
`request=true|false` and `dataset=<name>` (empty without a request).
Standard library only, Python 3.9 or later: the workflow runs it on the
runner's own python3 before anything is installed.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Iterable, NamedTuple, Optional

#: The assistant's account name; its handle is an at sign and this name.
ASSISTANT = "d4dassistant"
HANDLE = "@" + ASSISTANT

#: The line endings Markdown recognises, and no others: str.splitlines()
#: would also break at U+2028 and the like, which can sit inside one line.
LINE_BREAK = re.compile(r"\r\n|\r|\n")
#: A line that starts with the handle: the handle, then no character a
#: GitHub login can continue with.
STARTS_WITH_HANDLE = re.compile(re.escape(HANDLE) + r"(?![A-Za-z0-9-])", re.IGNORECASE | re.ASCII)
#: A dataset name a request may carry. The workflow puts it into shell
#: commands, so a directory named otherwise can never be requested.
NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*")
#: A list item marker and the spaces after it (repeated for a nested list).
LIST_MARKER = re.compile(r" {0,3}(?:[-+*]|\d{1,9}[.)])[ \t]+")
#: A fence's opening line, indented at most three spaces.
FENCE = re.compile(r"(?P<indent> {0,3})(?P<run>`{3,}|~{3,})(?P<info>.*)")
#: CommonMark's HTML blocks 1-5, which end at a marker rather than at a
#: blank line: (start, end). The end may be on the start line.
HTML_BLOCKS = (
    (re.compile(r" {0,3}<(?:pre|script|style|textarea)(?:[ \t>]|$)", re.I),
     re.compile(r"</(?:pre|script|style|textarea)>", re.I)),
    (re.compile(r" {0,3}<!--"), re.compile(r"-->")),
    (re.compile(r" {0,3}<\?"), re.compile(r"\?>")),
    (re.compile(r" {0,3}<![A-Za-z]"), re.compile(r">")),
    (re.compile(r" {0,3}<!\[CDATA\["), re.compile(r"\]\]>")),
)
#: A line that may start an HTML block of kind 6 or 7 (a tag), which runs
#: to the next blank line and makes a fence line inside it plain text.
TAG = re.compile(r" {0,3}</?[A-Za-z]")


class Decision(NamedTuple):
    """The input directory a text requests, the line asking for it, and why
    each other line that starts with the handle is not a request (or why
    the text's requests conflict)."""
    dataset: Optional[str]
    line: Optional[int]
    notes: tuple

    @property
    def request(self) -> bool:
        return self.dataset is not None


class _Block(NamedTuple):
    what: str               # "fenced code block" or "HTML block"
    line: int               # the line that opened it
    indent: int             # that line's indentation
    fence: Optional[tuple]  # (character, length) for a fence
    end: Optional[re.Pattern]  # for an HTML block


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _fence(line: str) -> Optional[tuple]:
    """(character, length, indentation) when `line` opens a fence."""
    m = FENCE.fullmatch(line)
    if m is None or (m["run"][0] == "`" and "`" in m["info"]):
        return None     # a backtick in the info string makes it a code span
    return m["run"][0], len(m["run"]), len(m["indent"])


def _html(line: str) -> Optional[re.Pattern]:
    """The end marker when `line` starts an HTML block of kind 1-5."""
    return next((end for start, end in HTML_BLOCKS if start.match(line)), None)


def _closes(block: _Block, line: str) -> bool:
    """Whether `line` ends `block` (a closing fence of any indentation)."""
    if block.end is not None:
        return block.end.search(line) is not None
    char, length = block.fence
    body = line.lstrip(" ")
    run = len(body) - len(body.lstrip(char))
    return run >= length and not body[run:].strip(" ")


def _requested(line: str, datasets: frozenset) -> tuple:
    """(dataset, "") when a line starting with the handle names exactly one
    input directory, else (None, why not)."""
    rest = line[len(HANDLE):]
    words = [w for w in rest.split(" ") if w]
    if not words:
        return None, "names no input directory after the handle"
    if not rest.startswith(" "):
        return None, f"the handle is followed by {rest[:1]!r}, not a space and an input directory name"
    if len(words) > 1:
        return None, f"has more than one word after the handle ({' '.join(words)!r})"
    name = words[0]
    if name not in datasets or not NAME.fullmatch(name):
        listed = ", ".join(sorted(datasets)) or "none"
        return None, f"names {name!r}, which is not an input directory (input directories: {listed})"
    return name, ""


def find_request(text: Optional[str], datasets: Iterable[str]) -> Decision:
    """Read `text` for a request naming one of `datasets` (module docstring)."""
    datasets = frozenset(datasets)
    found: dict = {}        # dataset -> the first line asking for it
    notes: list = []
    block: Optional[_Block] = None
    lost: Optional[int] = None     # the line where block ends became uncertain
    maybe_html = False             # this run of lines may be an HTML block 6-7
    after_blank = True
    for number, raw in enumerate(LINE_BREAK.split(text or ""), 1):
        line = raw.expandtabs(4)
        blank = not line.strip(" ")
        starts = STARTS_WITH_HANDLE.match(line) is not None
        if lost is None and block is not None and block.indent and not blank \
                and _indent(line) < block.indent:
            lost = number   # left of an indented opener: a list item holding it may end here
        if lost is not None:
            if starts:
                notes.append(f"line {number}: from line {lost} on, this reader cannot tell where "
                             "a code fence or HTML block ends")
            continue
        if block is not None:
            if starts:
                notes.append(f"line {number}: inside the {block.what} opened on line {block.line}")
            if _closes(block, line):
                if block.fence is None or _indent(line) <= 3:
                    block = None
                elif block.indent:
                    lost = number   # closes it in a list item, is content at the top level
            after_blank = blank
            continue
        rest, nested = line, False
        while (marker := LIST_MARKER.match(rest)) is not None:
            rest, nested = rest[marker.end():], True
        fence, end = _fence(rest), _html(rest)
        stays = end is not None and not end.search(rest)   # an HTML block past this line
        if (fence or stays) and (nested or maybe_html):
            lost = number   # in a list item, or plain text if this paragraph is an HTML block
            continue
        if fence:
            block = _Block("fenced code block", number, fence[2], fence[:2], None)
        elif stays:
            block = _Block("HTML block", number, _indent(line), None, end)
        elif end is None and TAG.match(rest):
            maybe_html = True
        elif starts:
            if not after_blank:
                notes.append(f"line {number}: does not start a paragraph (the line before it is not blank)")
            else:
                name, why = _requested(line, datasets)
                if name is None:
                    notes.append(f"line {number}: {why}")
                else:
                    found.setdefault(name, number)
        if blank:
            maybe_html = False
        after_blank = blank
    if len(found) > 1:
        lines = ", ".join(f"line {n} ({d})" for d, n in sorted(found.items(), key=lambda x: x[1]))
        notes.append(f"{lines} ask for different datasets: a text may request one")
        return Decision(None, None, tuple(notes))
    if found:
        (dataset, number), = found.items()
        return Decision(dataset, number, tuple(notes))
    return Decision(None, None, tuple(notes))


def declared_datasets(inputs: Path) -> list:
    """The input directories a request may name: the subdirectories of
    `inputs` whose names are safe in the workflow's shell commands."""
    return sorted(p.name for p in inputs.iterdir() if p.is_dir() and NAME.fullmatch(p.name))


def report(decision: Decision) -> str:
    """The log lines for a decision."""
    if decision.request:
        head = f"request: line {decision.line} asks for {decision.dataset}"
    elif decision.notes:
        head = "no request"
    else:
        head = "no request: no line starts with the assistant's handle"
    return "\n".join([head] + [f"  {note}" for note in decision.notes])


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--inputs", required=True, type=Path,
                        help="directory whose subdirectories are the datasets a request may name")
    parser.add_argument("--body", type=Path, help="file holding the text (default: standard input)")
    parser.add_argument("--github-output", type=Path,
                        help="append request=true|false and dataset=<name> to this file")
    args = parser.parse_args(argv)
    if not args.inputs.is_dir():
        parser.error(f"--inputs {args.inputs} is not a directory")
    text = (args.body.read_bytes().decode("utf-8", errors="replace") if args.body
            else sys.stdin.read())
    decision = find_request(text, declared_datasets(args.inputs))
    print(report(decision))
    if args.github_output:
        with args.github_output.open("a", encoding="utf-8") as out:
            out.write(f"request={'true' if decision.request else 'false'}\n")
            out.write(f"dataset={decision.dataset or ''}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

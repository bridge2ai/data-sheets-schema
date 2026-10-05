#!/usr/bin/env python3
"""Decide whether an issue, pull request or comment text asks the D4D
assistant workflow (`.github/workflows/d4d-agent.yml`) for a datasheet (#4108).

The workflow used to act on any text holding the assistant's handle followed
by whitespace, and read the rest of that line as the request: a review issue
that quoted the handle could start a billed `d4d api run` and open a pull
request. On #4093 only the backtick right after the handle prevented it. A
request is now one explicit line, and nothing else is one:

- the line reads exactly: the assistant's handle at its very start (in any
  ASCII letter case), spaces or tabs, then the name of one directory under
  the inputs directory, spelled as the directory is; only spaces or tabs
  follow;
- it stands alone: the line before it is blank or it is the first line, and
  the line after it is blank or it is the last line. A blank line holds
  nothing but spaces and tabs, as in CommonMark; a line of U+00A0, a form
  feed or any other white space is not blank;
- it lies outside fenced code blocks, and outside the HTML blocks that run
  past a blank line (a comment, <pre>, <script>, <style>, <textarea>, a
  processing instruction, a declaration, CDATA);
- no line before it leaves raw HTML open (see below).

Standing alone keeps the line out of code spans, quotes, lists, tables and
headings. No code span, inline HTML comment or quotation continues across a
blank line. After one, a block quote has ended and a list item continues
only on indented lines. A table row follows its table with no blank line
between. A line with a blank line after it is neither a heading's text nor
a table's header. So a quoted line, a list item, an indented code block or
a table row either does not start with the handle or does not stand alone.
A text whose request lines name different datasets holds no request.

Raw HTML: a browser reads an HTML comment, a tag with its quoted attribute
values, and the content of elements such as <textarea>, <script>, <title>,
<plaintext> or <svg> until they end, not where the Markdown block holding
them ends; one left open hides every later line. So a line that may be raw
HTML (one in or opening an HTML block, a quoted line, a list item line or
an indented line) must close each comment and tag it opens, by the HTML
tokenizer's rules; an HTML block of the kinds listed above must do so by
its last line. And no line outside a fenced code block may hold a start
tag of one of those elements, a processing instruction, CDATA or "--!>":
CommonMark passes them through as raw HTML even inside a paragraph, and
the tokenizer ends the last three sooner than CommonMark does. Otherwise
no later line is read as a request. (An element that hides content it
does hold, such as <template> or one with a `hidden` attribute, is not
covered: that is a question of rendering, not of where markup ends.)

This reads lines, not a Markdown tree. Where it cannot tell where a fence or
an HTML block ends without parsing lists or HTML (one opened on a list
marker; one whose content runs left of its indented opening line; an
indented fence closed by a line indented past three spaces; a fence or HTML
block opened in a paragraph that may itself be an HTML block), or where raw
HTML may be left open, it reads no later line as a request, and a later
line that would ask for another dataset still cancels a request before it.
It fails closed: a missed request costs a re-post, a false one a billed run.

Run by the workflow's "Read the request" step:

    python3 src/github/assistant_request.py \\
        --inputs data/sheets_d4dassistant/inputs \\
        --body "$RUNNER_TEMP/assistant-request-text.md" \\
        --github-output "$GITHUB_OUTPUT"

It logs `request: ...`, or `no request` with the reason each line that starts
with the handle is not one (where requests conflict, one note names every
line that asks), and, with --github-output, appends `request=true|false` and
`dataset=<name>` (empty without a request).
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
#: GitHub login can continue with. re.ASCII matters: without it, IGNORECASE
#: also lets U+017F stand for "s" and U+0130 or U+0131 for "i", spellings
#: that are not the handle.
STARTS_WITH_HANDLE = re.compile(re.escape(HANDLE) + r"(?![A-Za-z0-9-])", re.IGNORECASE | re.ASCII)
#: A dataset name a request may carry. The workflow puts it into shell
#: commands, so a directory named otherwise can never be requested.
NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*")
#: A list item marker and the spaces after it (repeated for a nested list).
LIST_MARKER = re.compile(r" {0,3}(?:[-+*]|\d{1,9}[.)])[ \t]+")
#: A block quote marker.
QUOTE_MARKER = re.compile(r" {0,3}>")
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

#: Where the HTML tokenizer opens a start or an end tag.
TAG_OPEN = re.compile(r"</?[A-Za-z]")
#: Raw HTML that may run past the paragraph or block holding it even where
#: CommonMark reads it as complete, so it counts as left open wherever it
#: appears, also in a code span or a comment. A start tag of an element
#: after which the HTML tokenizer stops reading markup as it does elsewhere
#: (raw text, RCDATA, PLAINTEXT), or of <svg> or <math>, in whose content
#: CDATA runs to "]]>"; and constructs the tokenizer ends before CommonMark
#: does: a processing instruction or CDATA at its first ">", a comment at
#: "--!>".
OPAQUE = re.compile(r"<(?:iframe|math|noembed|noframes|noscript|plaintext|script|style|svg|textarea|title|xmp)"
                    r"(?=[\t\n\f />]|\Z)|<\?|<!\[CDATA\[|--!>", re.IGNORECASE | re.ASCII)
#: The HTML tokenizer's white space.
HTML_SPACE = "\t\n\f "

#: Why a line that starts with the handle does not stand alone.
BEFORE_NOT_BLANK = ("the line before it is not blank (a request line stands alone between blank lines, "
                    "or at the start or end of the text)")
AFTER_NOT_BLANK = ("the line after it is not blank (a request line stands alone between blank lines, "
                   "or at the start or end of the text)")


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
        return None     # a backtick fence's info string holds no backtick: this is a code span
    return m["run"][0], len(m["run"]), len(m["indent"])


def _html(line: str) -> Optional[re.Pattern]:
    """The end marker when `line` starts an HTML block of kind 1-5."""
    return next((end for start, end in HTML_BLOCKS if start.match(line)), None)


def _closes(block: _Block, line: str) -> bool:
    """Whether `line` ends `block` (a closing fence of any indentation).
    A closing fence carries nothing but spaces after its run: not an info
    string, and not other white space such as U+00A0."""
    if block.end is not None:
        return block.end.search(line) is not None
    char, length = block.fence
    body = line.lstrip(" ")
    run = len(body) - len(body.lstrip(char))
    return run >= length and not body[run:].strip(" ")


def _comment_end(text: str, start: int) -> Optional[int]:
    """Just past the end of the HTML comment opened at text[start] ("<!--"),
    or None when the text ends inside it. By the HTML tokenizer's rules,
    "<!-->" and "<!--->" end at once; otherwise the first "-->" or "--!>"
    after the opening ends it."""
    body = start + 4
    if text.startswith(">", body):
        return body + 1
    if text.startswith("->", body):
        return body + 2
    ends = [(text.find(mark, body), len(mark)) for mark in ("-->", "--!>")]
    ends = [(at, size) for at, size in ends if at >= 0]
    if not ends:
        return None
    at, size = min(ends)
    return at + size


def _tag_end(text: str, start: int) -> Optional[int]:
    """Just past the ">" that ends the start or end tag opened at text[start],
    read by the HTML tokenizer's tag states, or None when the text ends
    inside it. A quote opens an attribute value only after "=" (and white
    space); anywhere else it is part of a name or of an unquoted value."""
    i = start + (2 if text.startswith("</", start) else 1)
    state = "name"
    while i < len(text):
        c = text[i]
        i += 1
        if state == "value" and c in "\"'":     # a quoted value runs to its closing quote
            close = text.find(c, i)
            if close < 0:
                return None
            i, state = close + 1, "before"
        elif c == ">":
            return i
        elif state == "name":                   # the tag name
            if c in HTML_SPACE or c == "/":
                state = "before"
        elif state in ("before", "attribute"):  # before, in or after an attribute name
            if c == "/":
                state = "before"
            elif c == "=" and state == "attribute":
                state = "value"
            elif c not in HTML_SPACE:
                state = "attribute"             # here "=" starts a name
        elif state == "value":                  # before an attribute value
            if c not in HTML_SPACE:
                state = "unquoted"
        elif c in HTML_SPACE:                   # an unquoted value ends at white space
            state = "before"
    return None


def _leaves_html_open(text: str) -> bool:
    """Whether `text`, read as raw HTML, may leave something open that hides
    what the page shows after it: anything OPAQUE matches, or an HTML
    tokenizer that, reading `text` from its data state, stops in a comment,
    a tag or a quoted attribute value, or in a bogus comment or DOCTYPE
    short of its ">". OPAQUE already refuses "<?" and "--!>"; the tokenizer
    below still reads them by its own rules, so it stays right on its own."""
    if OPAQUE.search(text):
        return True
    i = text.find("<")
    while i >= 0:
        if text.startswith("<!--", i):
            end = _comment_end(text, i)
        elif TAG_OPEN.match(text, i):
            end = _tag_end(text, i)
        elif text.startswith("</>", i):
            end = i + 3
        elif text.startswith(("<!", "<?", "</"), i):    # a bogus comment or a DOCTYPE runs to the next ">"
            close = text.find(">", i + 2)
            end = None if close < 0 else close + 1
        else:                                            # "<" before anything else is text
            end = i + 1
        if end is None:
            return True
        i = text.find("<", end)
    return False


def _unsure(line: int) -> str:
    return f"from line {line} on, this reader cannot tell where a code fence or HTML block ends"


def _left_open(first: int, last: int) -> str:
    where = f"line {first} holds" if first == last else f"lines {first}-{last} hold"
    return (f"{where} HTML whose end this reader cannot see, which may hide every later line: "
            "an unclosed comment or tag, or <textarea>, <svg>, <? or the like")


def _requested(line: str, datasets: frozenset) -> tuple:
    """(dataset, "") when a line starting with the handle names exactly one
    input directory that a request can name, else (None, why not)."""
    rest = line[len(HANDLE):]
    words = [w for w in rest.split(" ") if w]
    if not words:
        return None, "names no input directory after the handle"
    if not rest.startswith(" "):
        return None, f"the handle is followed by {rest[:1]!r}, not a space and an input directory name"
    if len(words) > 1:
        return None, f"has more than one word after the handle ({' '.join(words)!r})"
    name = words[0]
    if name not in datasets:
        listed = ", ".join(sorted(d for d in datasets if NAME.fullmatch(d))) or "none"
        return None, f"names {name!r}, which is not an input directory (input directories: {listed})"
    if not NAME.fullmatch(name):
        return None, (f"names {name!r}, an input directory a request cannot name: the workflow passes the "
                      f"name to shell commands, so it must match {NAME.pattern}")
    return name, ""


def find_request(text: Optional[str], datasets: Iterable[str]) -> Decision:
    """Read `text` for a request naming one of `datasets` (module docstring)."""
    datasets = frozenset(datasets)
    lines = [raw.expandtabs(4) for raw in LINE_BREAK.split(text or "")]
    asked: dict = {}        # dataset -> [(line, read)]; read is False for a line past `lost`
    notes: list = []
    block: Optional[_Block] = None
    lost: Optional[str] = None      # why no line from here on can be read
    maybe_html = False              # this run of lines may be an HTML block 6-7
    previous_blank = True
    pending: Optional[tuple] = None   # (line, dataset, read): a request line until the line after it is seen
    for number, line in enumerate(lines, 1):
        # Blank as in CommonMark: spaces and tabs only (expanded above). Not
        # str.strip(), which also strips U+00A0, form feeds and the like.
        blank = not line.strip(" ")
        follows_blank, previous_blank = previous_blank, blank
        if pending is not None:
            asking, name, read = pending
            pending = None
            if blank:
                asked.setdefault(name, []).append((asking, read))
            elif read:
                notes.append(f"line {asking}: {AFTER_NOT_BLANK}")
        starts = STARTS_WITH_HANDLE.match(line) is not None
        if lost is None and block is not None and block.indent and not blank \
                and _indent(line) < block.indent:
            lost = _unsure(number)   # left of an indented opener: a list item holding it may end here
        if lost is not None:
            if starts:
                notes.append(f"line {number}: {lost}")
                name = _requested(line, datasets)[0] if follows_blank else None
                if name is not None:
                    pending = (number, name, False)   # unreadable, yet it may ask: it can still cancel
            continue
        if block is not None:
            if starts:
                notes.append(f"line {number}: inside the {block.what} opened on line {block.line}")
            if _closes(block, line):
                if block.fence is None:
                    if _leaves_html_open("\n".join(lines[block.line - 1:number])):
                        lost = _left_open(block.line, number)
                    block = None
                elif _indent(line) <= 3:
                    block = None
                elif block.indent:
                    lost = _unsure(number)   # closes it in a list item, is content at the top level
            continue
        rest, nested = line, False
        while (marker := LIST_MARKER.match(rest)) is not None:
            rest, nested = rest[marker.end():], True
        fence, end = _fence(rest), _html(rest)
        stays = end is not None and not end.search(rest)   # an HTML block past this line
        if (fence or stays) and (nested or maybe_html):
            lost = _unsure(number)   # in a list item, or plain text if this paragraph is an HTML block
            continue
        if fence:
            block = _Block("fenced code block", number, fence[2], fence[:2], None)
        elif stays:
            block = _Block("HTML block", number, _indent(line), None, end)
        else:
            if end is None and TAG.match(rest):
                maybe_html = True
            elif starts:
                if not follows_blank:
                    notes.append(f"line {number}: {BEFORE_NOT_BLANK}")
                else:
                    name, why = _requested(line, datasets)
                    if name is None:
                        notes.append(f"line {number}: {why}")
                    else:
                        pending = (number, name, True)
            # A line that may be raw HTML must close what it opens; any other
            # line, read as a paragraph, may still hold OPAQUE (module docstring).
            if maybe_html or end is not None or nested or _indent(line) or QUOTE_MARKER.match(line):
                left_open = _leaves_html_open(line)
            else:
                left_open = OPAQUE.search(line) is not None
            if left_open:
                lost = _left_open(number, number)
        if blank:
            maybe_html = False
    if pending is not None:     # the last line
        asking, name, read = pending
        asked.setdefault(name, []).append((asking, read))
    read_names = sorted(d for d, lines_asking in asked.items() if any(read for _, read in lines_asking))
    if len(read_names) > 1 or (read_names and set(asked) - set(read_names)):
        every = sorted((n, d, read) for d, lines_asking in asked.items() for n, read in lines_asking)
        note = ", ".join(f"line {n} ({d})" for n, d, _ in every) + \
            " ask for different datasets: a text may request one"
        unread = [f"line {n}" for n, _, read in every if not read]
        if unread:
            note += f", and this reader cannot rule out {', '.join(unread)}"
        notes.append(note)
        return Decision(None, None, tuple(notes))
    if read_names:
        dataset, = read_names
        return Decision(dataset, min(n for n, read in asked[dataset] if read), tuple(notes))
    return Decision(None, None, tuple(notes))


def input_directories(inputs: Path) -> list:
    """The names of the subdirectories of `inputs`. A request can name one
    whose name also matches NAME, since the workflow passes it to shell
    commands; any other is reported as one a request cannot name."""
    return sorted(p.name for p in inputs.iterdir() if p.is_dir())


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
    decision = find_request(text, input_directories(args.inputs))
    print(report(decision))
    if args.github_output:
        with args.github_output.open("a", encoding="utf-8") as out:
            out.write(f"request={'true' if decision.request else 'false'}\n")
            out.write(f"dataset={decision.dataset or ''}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Duplicate mapping keys are a validation failure and a gated floor (#1029).

The AI_READI 2026-09-04f full record carries a top-level `source_caveats`
three times; `yaml.safe_load` keeps the last, and until #1030 its
`validation.passed` read true. It is the one such record in the corpus,
kept as declared evidence (`passed: false`, the key named) and not retained.
"""

import pytest
import glob
import tempfile
import unittest
import unittest.mock
from pathlib import Path

import yaml

from data_sheets_schema.canary import OK, REGRESSED, UNMEASURABLE, duplicate_key_count, verdict
from data_sheets_schema.duplicate_keys import describe, find_duplicate_keys

ROOT = Path(__file__).resolve().parents[1]

DUPED = """# header
id: doi:10.1/x
source_caveats: >-
  first
variables:
- variable_name: a
  unit: mm
  unit: cm
source_caveats: >-
  second
funders:
- name: NIH
- name: NIH
"""


class TestDetection(unittest.TestCase):
    def test_top_level_and_nested_duplicates_are_found_with_lines(self):
        dups = find_duplicate_keys(DUPED)
        self.assertEqual([(d["path"], d["key"], d["lines"], d["count"]) for d in dups],
                         [("$", "source_caveats", [3, 9], 2), ("variables[0]", "unit", [7, 8], 2)])
        self.assertIn("`source_caveats` at $ on lines 3, 9", describe(dups))
        self.assertIn("keeps only the last", describe(dups))

    def test_a_clean_record_and_unparsable_text_yield_nothing(self):
        self.assertEqual(find_duplicate_keys("id: x\nnotes: y\nfunders:\n- name: a\n- name: a\n"), [])
        self.assertEqual(find_duplicate_keys("id: [unterminated\n"), [])
        self.assertEqual(find_duplicate_keys(""), [])

    def test_the_loader_would_have_kept_the_last(self):
        self.assertEqual(yaml.safe_load(DUPED)["source_caveats"], "second")


PARITY = [
    DUPED, "id: x\nnotes: y\n", "id: [unterminated\n", "", "a: \0", "loop: &loop {self: *loop}\n",
    "a: &x {k: 1, k: 2}\nb: *x\nc: *x\n", "true: a\nTrue: b\n", "1: a\n\"1\": b\n", "true: a\n1: b\n1.0: c\n",
    "base: &b {x: 1}\nother: &o {y: 2}\nm:\n  <<: *b\n  <<: *o\n  z: 3\n",
    "x: &x {k: 1}\nz:\n  <<: *x\n  k: 2\n", "x: &x {k: 1}\ny: &y {k: 2}\nz:\n  <<: [*x, *y]\n  z: 1\n  z: 2\n",
    "a: 1\n---\nb: 2\n", "a:\n- b: 1\n  b: 2\n",
]


class TestTheLoader(unittest.TestCase):
    """#3704: the node tree may be composed by libyaml; the rule does not move."""

    def test_the_default_is_the_pure_python_safe_loader(self):
        import inspect
        from data_sheets_schema import duplicate_keys
        self.assertIs(inspect.signature(find_duplicate_keys).parameters["loader"].default, yaml.SafeLoader)
        self.assertIn(duplicate_keys.FAST_LOADER, (getattr(yaml, "CSafeLoader", None), yaml.SafeLoader))

    def test_the_given_loader_composes_the_tree(self):
        made = []

        class Recording(yaml.SafeLoader):
            def __init__(self, stream):
                made.append(stream)
                super().__init__(stream)

        self.assertEqual([d["key"] for d in find_duplicate_keys("a: 1\na: 2\n", loader=Recording)], ["a"])
        self.assertEqual(made, ["a: 1\na: 2\n"])

    def test_libyaml_and_the_pure_python_loader_give_the_same_findings(self):
        from data_sheets_schema.duplicate_keys import FAST_LOADER
        if not hasattr(yaml, "CSafeLoader"):
            self.skipTest("PyYAML built without libyaml")
        self.assertIs(FAST_LOADER, yaml.CSafeLoader)
        for text in PARITY:
            with self.subTest(text=text):
                self.assertEqual(find_duplicate_keys(text, loader=yaml.CSafeLoader),
                                 find_duplicate_keys(text, loader=yaml.SafeLoader))
                self.assertEqual(find_duplicate_keys(text), find_duplicate_keys(text, loader=yaml.SafeLoader))
        # The cases are not all empty: the parity is over findings, merges included.
        self.assertEqual([d["key"] for d in find_duplicate_keys(PARITY[-3], loader=yaml.CSafeLoader)], ["z"])

    def test_strict_raises_what_the_default_reports_as_nothing(self):
        """#3799: a text the scan cannot check is `[]` by default and raised
        under `strict=True`, under either loader."""
        import inspect
        from data_sheets_schema.duplicate_keys import FAST_LOADER
        self.assertIs(inspect.signature(find_duplicate_keys).parameters["strict"].default, False)
        deep = "a: 1\na: 2\nb: " + "{x: " * 1200 + "1" + "}" * 1200 + "\n"
        for loader in {yaml.SafeLoader, FAST_LOADER}:
            with self.subTest(loader=loader.__name__):
                self.assertEqual(find_duplicate_keys(deep, loader=loader), [])
                with self.assertRaises(RecursionError):
                    find_duplicate_keys(deep, loader=loader, strict=True)
                for bad in ("id: [unterminated\n", "a: \0"):   # the composer; the reader
                    self.assertEqual(find_duplicate_keys(bad, loader=loader), [])
                    with self.assertRaises(yaml.YAMLError):
                        find_duplicate_keys(bad, loader=loader, strict=True)
                self.assertEqual([d["key"] for d in find_duplicate_keys("a: 1\na: 2\n", loader=loader, strict=True)],
                                 ["a"])


class TestUnencodableText(unittest.TestCase):
    """#3834: a lone surrogate is unscannable under either loader, alike."""

    SURROGATE = "a: 1\na: 2\nb: \udcff\n"

    def _scan(self, text, loader, strict):
        try:
            return ("found", find_duplicate_keys(text, loader=loader, strict=strict))
        except Exception as exc:                                  # noqa: BLE001
            return ("raised", type(exc), getattr(exc, "position", None), getattr(exc, "character", None))

    def test_a_lone_surrogate_is_nothing_by_default_and_a_reader_error_under_strict(self):
        from data_sheets_schema.duplicate_keys import FAST_LOADER
        for loader in {yaml.SafeLoader, FAST_LOADER}:
            for text in (self.SURROGATE, "\ud800a: 1\na: 2\n", "a: 1\na: 2\nb: \"x\udfffy\"\n",
                         "a: 1\na: 2\n# \udcff\n", "a: \0\nb: \udcff\n"):
                with self.subTest(loader=loader.__name__, text=text.encode("utf-8", "backslashreplace")):
                    self.assertEqual(find_duplicate_keys(text, loader=loader), [])
                    with self.assertRaises(yaml.reader.ReaderError):
                        find_duplicate_keys(text, loader=loader, strict=True)

    def test_both_loaders_raise_the_same_reader_error(self):
        """The same class, position and character: the pure-Python reader's
        error, naming the first character it rejects (the NUL before the
        surrogate in the second text)."""
        if not hasattr(yaml, "CSafeLoader"):
            self.skipTest("PyYAML built without libyaml")
        for text, position in ((self.SURROGATE, 13), ("a: \0\nb: \udcff\n", 3)):
            with self.subTest(position=position):
                pure = self._scan(text, yaml.SafeLoader, True)
                self.assertEqual(pure[:3], ("raised", yaml.reader.ReaderError, position))
                self.assertEqual(self._scan(text, yaml.CSafeLoader, True), pure)

    def test_code_points_at_every_reader_boundary_are_accepted_or_rejected_alike(self):
        """In a double-quoted scalar, strict and not, over the code points
        around each boundary of the readers' printable set (C0 and C1
        controls, NEL, NBSP, the surrogates, U+FEFF, U+FFFE/U+FFFF, the astral
        planes): before #3834 the surrogates raised UnicodeEncodeError under
        libyaml. Outcomes compare by class — each reader words its own
        `ReaderError`. All 1,114,112 code points were compared once, outside
        the suite: the surrogates were the only difference."""
        if not hasattr(yaml, "CSafeLoader"):
            self.skipTest("PyYAML built without libyaml")
        differ = []
        for cp in list(range(0x0, 0x200)) + list(range(0x2020, 0x2030)) + list(range(0xD7F0, 0xE010)) + list(range(0xFFF0, 0x10010)) \
                + [0x10FFFF]:
            text = 'a: 1\na: 2\nb: "x' + chr(cp) + 'y"\n'
            for strict in (False, True):
                pure = self._scan(text, yaml.SafeLoader, strict)
                fast = self._scan(text, yaml.CSafeLoader, strict)
                if pure[:2] != fast[:2]:
                    differ.append((hex(cp), strict, pure[:2], fast[:2]))
        self.assertEqual(differ, [])

    def test_the_depth_guard_does_not_raise_on_an_unencodable_text(self):
        from data_sheets_schema.duplicate_keys import nesting_exceeds
        if not hasattr(yaml, "CSafeLoader"):
            self.skipTest("PyYAML built without libyaml")
        self.assertIs(nesting_exceeds(self.SURROGATE, yaml.CSafeLoader, 10), False)

    def test_the_scanners_differ_on_a_tab_in_a_plain_scalar(self):
        """Pinned as documented, not as desired: PyYAML's pure-Python scanner
        rejects a tab inside a plain scalar and a byte-order mark after the last
        token; libyaml accepts both and loads the text, so the
        libyaml scan reports what that load would drop."""
        if not hasattr(yaml, "CSafeLoader"):
            self.skipTest("PyYAML built without libyaml")
        for text in ("a: 1\na: 2\nb: x\ty\n", "a: 1\na: 2\n\ufeff"):
            with self.subTest(text=text):
                self.assertEqual(find_duplicate_keys(text, loader=yaml.SafeLoader), [])
                with self.assertRaises(yaml.YAMLError):
                    yaml.load(text, Loader=yaml.SafeLoader)   # noqa: S506
                self.assertEqual([d["key"] for d in find_duplicate_keys(text, loader=yaml.CSafeLoader,
                                                                         strict=True)], ["a"])
                self.assertEqual(yaml.load(text, Loader=yaml.CSafeLoader)["a"], 2)   # noqa: S506

    def test_the_scanners_differ_the_other_way_on_a_byte_order_mark(self):
        """The reverse direction (#3855): a byte-order mark directly before a
        plain key at column 0 on a later line is a ParserError to libyaml,
        which drops the mark but counts it as a column, while the pure-Python
        loader reads the mark into the key, so the default scan reports what
        libyaml refuses. This is not a general rule for a mark opening a later
        line: before a comment, alone on a line or before indentation libyaml
        accepts it (#3956, #3987; the next two tests pin the comment and
        indentation cases)."""
        if not hasattr(yaml, "CSafeLoader"):
            self.skipTest("PyYAML built without libyaml")
        text = "a: 1\na: 2\n﻿b: 3\n"
        self.assertEqual(yaml.load(text, Loader=yaml.SafeLoader), {"a": 2, "﻿b": 3})   # noqa: S506
        self.assertEqual([d["key"] for d in find_duplicate_keys(text, loader=yaml.SafeLoader,
                                                                 strict=True)], ["a"])
        with self.assertRaises(yaml.YAMLError):
            yaml.load(text, Loader=yaml.CSafeLoader)   # noqa: S506
        self.assertEqual(find_duplicate_keys(text, loader=yaml.CSafeLoader), [])
        with self.assertRaises(yaml.YAMLError):
            find_duplicate_keys(text, loader=yaml.CSafeLoader, strict=True)

    def test_libyaml_accepts_a_line_start_mark_the_default_refuses(self):
        """A mark opening a later line is not refused by libyaml in general
        (#3956): libyaml drops it, so before a comment the text loads and the
        libyaml scan reports the duplicate. The pure-Python scanner reads the
        mark as an ordinary character there and refuses the text."""
        if not hasattr(yaml, "CSafeLoader"):
            self.skipTest("PyYAML built without libyaml")
        text = "a: 1\n\ufeff# c\na: 2\n"
        self.assertEqual(yaml.load(text, Loader=yaml.CSafeLoader), {"a": 2})   # noqa: S506
        self.assertEqual([d["key"] for d in find_duplicate_keys(text, loader=yaml.CSafeLoader,
                                                                 strict=True)], ["a"])
        with self.assertRaises(yaml.scanner.ScannerError):
            yaml.load(text, Loader=yaml.SafeLoader)   # noqa: S506
        self.assertEqual(find_duplicate_keys(text, loader=yaml.SafeLoader), [])
        with self.assertRaises(yaml.YAMLError):
            find_duplicate_keys(text, loader=yaml.SafeLoader, strict=True)

    def test_one_line_start_mark_gives_different_structures(self):
        """One mark that does not lead the stream is read by both loaders, to
        different structures (#3956). libyaml drops it but counts it as a
        column, which nests `b` under `x`. The pure-Python loader reads the
        mark into a key."""
        if not hasattr(yaml, "CSafeLoader"):
            self.skipTest("PyYAML built without libyaml")
        bom = "\ufeff"
        text = "b: 0\nx:\n" + bom + "  b: 1\n"
        self.assertEqual(yaml.load(text, Loader=yaml.SafeLoader),   # noqa: S506
                         {"b": 0, "x": None, bom + "  b": 1})
        self.assertEqual(yaml.load(text, Loader=yaml.CSafeLoader), {"b": 0, "x": {"b": 1}})   # noqa: S506
        for loader in (yaml.SafeLoader, yaml.CSafeLoader):
            with self.subTest(loader=loader.__name__):
                self.assertEqual(find_duplicate_keys(text, loader=loader, strict=True), [])
        # The mark counts as a column: the key after it is at column 3, so a
        # duplicate there must be indented three spaces for libyaml to nest it
        # beside the first (two spaces is a ParserError).
        text = "x:\n" + bom + "  b: 1\n   b: 2\n"
        self.assertEqual([(d["path"], d["key"]) for d in find_duplicate_keys(
            text, loader=yaml.CSafeLoader, strict=True)], [("x", "b")])
        with self.assertRaises(yaml.YAMLError):
            find_duplicate_keys("x:\n" + bom + "  b: 1\n  b: 2\n", loader=yaml.CSafeLoader, strict=True)

    def test_two_leading_byte_order_marks_give_different_keys(self):
        """Both loaders scan `<BOM><BOM>a: 1`, to different keys: libyaml
        drops both marks, the pure-Python reader only the first (#3855). Each
        scan names the key its own loader constructs. Not every stream opening
        with two marks scans under both: the last case below is one libyaml
        refuses (#3987)."""
        if not hasattr(yaml, "CSafeLoader"):
            self.skipTest("PyYAML built without libyaml")
        bom = "﻿"
        self.assertEqual(yaml.load(bom * 2 + "a: 1\n", Loader=yaml.SafeLoader), {bom + "a": 1})   # noqa: S506
        self.assertEqual(yaml.load(bom * 2 + "a: 1\n", Loader=yaml.CSafeLoader), {"a": 1})   # noqa: S506
        text = bom * 2 + "a: 1\n" + bom + "a: 2\n"
        self.assertEqual([d["key"] for d in find_duplicate_keys(text, loader=yaml.SafeLoader, strict=True)],
                         [bom + "a"])
        self.assertEqual([d["key"] for d in find_duplicate_keys(text, loader=yaml.CSafeLoader, strict=True)],
                         ["a"])
        # Without the second line's mark the default reads two distinct keys
        # and libyaml refuses the text: neither scan reports a duplicate.
        text = bom * 2 + "a: 1\na: 2\n"
        self.assertEqual(yaml.load(text, Loader=yaml.SafeLoader), {bom + "a": 1, "a": 2})   # noqa: S506
        self.assertEqual(find_duplicate_keys(text, loader=yaml.SafeLoader, strict=True), [])
        with self.assertRaises(yaml.YAMLError):
            find_duplicate_keys(text, loader=yaml.CSafeLoader, strict=True)


    def test_an_answer_matches_the_load_only_where_the_loader_scans(self):
        """The docstring's claim that each answer is what `yaml.load` with the
        same loader would load holds only where that loader scans the text
        (#4006). On every example text of the #3855 paragraph, under each
        loader: where `yaml.load` raises, the scan gives `[]` and under
        `strict` raises the same error class; where it loads, the strict scan
        succeeds and every duplicate it reports is a key of that load."""
        if not hasattr(yaml, "CSafeLoader"):
            self.skipTest("PyYAML built without libyaml")
        bom = "﻿"
        texts = ["b: x\ty\n", "a: 1\n" + bom + "b: 2\n", "a: 1\n" + bom + "# c\na: 2\n",
                 "a: 1\n" + bom + "\na: 2\n", "a: 1\n" + bom, "b: 0\nx:\n" + bom + "  b: 1\n",
                 bom * 2 + "a: 1\n", "a: x" + bom + "y\n", bom * 2 + "a: 1\na: 2\n",
                 bom * 2 + "a: 1\n" + bom + "a: 2\n"]
        unscannable, reported = set(), set()
        for text in texts:
            for loader in (yaml.SafeLoader, yaml.CSafeLoader):
                with self.subTest(text=text, loader=loader.__name__):
                    try:
                        loaded = yaml.load(text, Loader=loader)   # noqa: S506
                    except yaml.YAMLError as exc:
                        unscannable.add(loader.__name__)
                        self.assertEqual(find_duplicate_keys(text, loader=loader), [])
                        with self.assertRaises(type(exc)):
                            find_duplicate_keys(text, loader=loader, strict=True)
                        continue
                    for d in find_duplicate_keys(text, loader=loader, strict=True):
                        reported.add(loader.__name__)
                        self.assertIn(d["key"], loaded if d["path"] == "$" else loaded[d["path"]])
        # The examples exercise both branches under each loader.
        self.assertEqual(unscannable, {"SafeLoader", "CSafeLoader"})
        self.assertEqual(reported, {"SafeLoader", "CSafeLoader"})


#: A child process that scans texts nested 50,000 deep with libyaml. Before
#: #3817 the flow case killed the interpreter with SIGSEGV (exit 139), which
#: is why it runs in a subprocess and not in pytest's own process.
_DEEP_CHILD = """
import sys, yaml
from data_sheets_schema.duplicate_keys import FAST_LOADER, find_duplicate_keys
n = 50_000
bom = "\\ufeff"
texts = {
    "flow": "a: 1\\na: 2\\nb: " + "{x: " * n + "1" + "}" * n + "\\n",
    "block sequence": "- " * n + "x\\n",
    "key position": "? " * n + "x\\n",
    # #3826: libyaml skips a byte-order mark; a column count did not.
    "BOM, block sequence": bom + "- " * n + "x\\n",
    "BOM, flow mappings": bom + "a: 1\\na: 2\\nb: " + "{x: " * n + "1" + "}" * n + "\\n",
    "BOM, flow sequences": bom + "[" * n + "]" * n + "\\n",
    "flow single-pair mappings": "[a: " * n + "1" + "]" * n + "\\n",
    "mixed block and flow": "- " * (n // 2) + "[" * (n // 2) + "]" * (n // 2) + "\\n",
    "BOM, mixed with properties": bom + "- &a !!seq\\n  " + "- " * n + "[{k: " * 10 + "x" + "}]" * 10 + "\\n",
}
for name, text in texts.items():
    assert find_duplicate_keys(text, loader=FAST_LOADER) == [], name
    try:
        find_duplicate_keys(text, loader=FAST_LOADER, strict=True)
    except RecursionError as exc:
        assert "#3817" in str(exc), (name, str(exc))
    else:
        raise SystemExit(f"{name}: strict scan returned instead of raising")
print("refused", len(texts))
"""


#: The same texts where PyYAML has no libyaml (`yaml._yaml` cannot be
#: imported): `FAST_LOADER` is then the pure-Python `SafeLoader`, the guard is
#: not consulted, and the composer raises RecursionError itself.
_NO_LIBYAML_CHILD = "import sys\nsys.modules['yaml._yaml'] = None\n" + _DEEP_CHILD.replace(
    "import sys, yaml\n",
    "import sys, yaml\nfrom data_sheets_schema import duplicate_keys\n"
    "assert duplicate_keys.FAST_LOADER is yaml.SafeLoader and duplicate_keys._CParser is None\n", 1).replace(
    "assert \"#3817\" in str(exc)", "assert \"#3817\" not in str(exc)", 1)

def _event_depth(text: str) -> int:
    """The nesting depth, from the pure-Python parser's event stream."""
    depth = deepest = 0
    for event in yaml.parse(text, Loader=yaml.SafeLoader):
        if isinstance(event, (yaml.MappingStartEvent, yaml.SequenceStartEvent)):
            depth += 1
            deepest = max(deepest, depth)
        elif isinstance(event, (yaml.MappingEndEvent, yaml.SequenceEndEvent)):
            depth -= 1
    return deepest


def _block(depth: int) -> str:
    """Block mappings nested `depth` deep, a duplicate key in the innermost."""
    pad = "  " * (depth - 1)
    return "".join("  " * i + "k:\n" for i in range(depth - 1)) + pad + "a: 1\n" + pad + "a: 2\n"


def _flow(depth: int) -> str:
    """Flow mappings under a top-level mapping with a duplicate key: `depth` deep."""
    return "a: 1\na: 2\nb: " + "{x: " * (depth - 1) + "1" + "}" * (depth - 1) + "\n"


class TestTheLibyamlDepthGuard(unittest.TestCase):
    """#3817: libyaml's composer recurses on the C stack, so a deep enough
    tree crashed the process instead of raising. It is never handed one."""

    def setUp(self):
        if not hasattr(yaml, "CSafeLoader"):
            self.skipTest("PyYAML built without libyaml")

    def test_a_scan_of_a_tree_nested_fifty_thousand_deep_raises_and_does_not_crash(self):
        import os
        import subprocess
        import sys
        env = dict(os.environ)
        env["PYTHONPATH"] = os.pathsep.join([str(ROOT / "src"), str(ROOT), env.get("PYTHONPATH", "")])
        proc = subprocess.run([sys.executable, "-c", _DEEP_CHILD], capture_output=True, text=True,
                              env=env, timeout=300)
        self.assertEqual(proc.returncode, 0, proc.stderr[-2000:])
        self.assertEqual(proc.stdout.strip(), "refused 9")

    def test_without_libyaml_the_fallback_raises_cleanly_on_the_same_texts(self):
        """The pure-Python fallback: no guard, and a RecursionError from the
        composer rather than a crash, byte-order marks included (#3826)."""
        import os
        import subprocess
        import sys
        env = dict(os.environ)
        env["PYTHONPATH"] = os.pathsep.join([str(ROOT / "src"), str(ROOT), env.get("PYTHONPATH", "")])
        proc = subprocess.run([sys.executable, "-c", _NO_LIBYAML_CHILD], capture_output=True, text=True,
                              env=env, timeout=600)
        self.assertEqual(proc.returncode, 0, proc.stderr[-2000:])
        self.assertEqual(proc.stdout.strip(), "refused 9")

    def test_the_guard_refuses_one_level_past_the_limit_and_scans_at_it(self):
        """With the limit lowered, the boundary is testable without deep text:
        the refusal is the guard's (its message), not the walk's."""
        from data_sheets_schema import duplicate_keys
        with unittest.mock.patch.object(duplicate_keys, "LIBYAML_MAX_DEPTH", 6):
            for make in (_flow, _block):
                with self.subTest(form=make.__name__):
                    self.assertEqual(_event_depth(make(6)), 6)
                    self.assertEqual(len(find_duplicate_keys(make(6), loader=yaml.CSafeLoader, strict=True)), 1)
                    self.assertEqual(find_duplicate_keys(make(7), loader=yaml.CSafeLoader), [])
                    with self.assertRaisesRegex(RecursionError, "more than 6 deep.*#3817"):
                        find_duplicate_keys(make(7), loader=yaml.CSafeLoader, strict=True)
                    # The pure-Python loader is not guarded: the default path is unchanged.
                    self.assertEqual(len(find_duplicate_keys(make(7), strict=True)), 1)

    def test_the_default_loader_never_consults_the_guard(self):
        from data_sheets_schema import duplicate_keys
        with unittest.mock.patch.object(duplicate_keys, "nesting_exceeds", side_effect=AssertionError):
            self.assertEqual([d["key"] for d in find_duplicate_keys("a: 1\na: 2\n")], ["a"])
            self.assertEqual([d["key"] for d in find_duplicate_keys("a: 1\na: 2\n", loader=yaml.SafeLoader)], ["a"])

    def test_the_guard_counts_the_depth_the_composer_reaches(self):
        """#3826: the guard's depth is libyaml's own event stream, so no
        spelling of the nesting (a byte-order mark, flow or block style,
        properties, aliases) moves it off the depth the composer reaches. Each
        text is refused exactly one level below its depth and passed at it."""
        from data_sheets_schema.duplicate_keys import nesting_exceeds
        bom = "\ufeff"
        skipped = ("id: [unterminated\n", "a: \0", "a: 1\n---\nb: 2\n", "")   # unparseable, or no collection
        texts = [t for t in PARITY if t not in skipped] + [
            _block(40), _flow(40), "- - - - - x\n", "? - - a\n: - - b\n", "- a:\n  - b:\n    - c: 1\n",
            "a:\n- b:\n  - c\n", "[a: [b: [c: [d: 1]]]]\n", "{a: [{b: [x]}]}\n", "- &x !!map\n  k: [1, [2]]\n- *x\n",
            "k: |\n  [[[[\n", "a:\r\n  b:\r\n    - [c]\r\n", "a:\u2028  b: 1\n",
            "".join(" " * i + "a:\n" + " " * i + "-\n" for i in range(20)) + " " * 20 + "x: 1\n",
            bom + "- - - - - - x\n", bom + _flow(12), bom + "[" * 9 + "]" * 9 + "\n", bom + "? - - a\n: - - b\n",
            bom + "- [a: [{b: [c]}]]\n", bom + _block(8), "- " * 5 + "[" * 5 + "{k: v}" + "]" * 5 + "\n",
        ]
        for text in texts:
            depth = _event_depth(text)
            with self.subTest(text=text[:60], depth=depth):
                self.assertGreater(depth, 0)
                self.assertTrue(nesting_exceeds(text, yaml.CSafeLoader, depth - 1))
                self.assertFalse(nesting_exceeds(text, yaml.CSafeLoader, depth))
        self.assertFalse(nesting_exceeds("", yaml.CSafeLoader, 0))
        # A stream the parser rejects is too deep only if it passed the limit
        # first; otherwise the composer reports the error at the same place.
        self.assertTrue(nesting_exceeds("id: [unterminated\n", yaml.CSafeLoader, 1))
        self.assertFalse(nesting_exceeds("id: [unterminated\n", yaml.CSafeLoader, 2))
        self.assertFalse(nesting_exceeds("a: \0", yaml.CSafeLoader, 0))

    def test_a_leading_byte_order_mark_is_refused_at_the_limit_like_any_other_text(self):
        """#3826: the case the column count missed, at a lowered limit."""
        from data_sheets_schema import duplicate_keys
        bom = "\ufeff"
        with unittest.mock.patch.object(duplicate_keys, "LIBYAML_MAX_DEPTH", 6):
            for text in (bom + "- " * 7 + "x\n", bom + _flow(7), bom + "[" * 7 + "]" * 7 + "\n"):
                with self.subTest(text=text[:30]):
                    with self.assertRaisesRegex(RecursionError, "more than 6 deep.*#3817"):
                        find_duplicate_keys(text, loader=yaml.CSafeLoader, strict=True)
            self.assertEqual(len(find_duplicate_keys(bom + _flow(6), loader=yaml.CSafeLoader, strict=True)), 1)

    def test_every_libyaml_scan_parses_its_text_for_depth_first(self):
        """No text is cleared without the event pass: a libyaml scan opens the
        loader twice, the pass and the composer."""
        opened = []

        class Counting(yaml.CSafeLoader):
            def __init__(self, stream):
                opened.append(1)
                super().__init__(stream)

        self.assertEqual(len(find_duplicate_keys("a: 1\na: 2\nb: [[1]]\n", loader=Counting)), 1)
        self.assertEqual(len(opened), 2)


GOOD = {"pair": {"ran": True, "errors": 0}, "report": {"checked": True, "findings": [], "claims_checked": 3},
        "grounding": {"ran": True, "distinct": {"absent": 0}, "findings": []},
        "form": {"ran": True, "organisational_fragments": 0, "undeclared_prefix_occurrences": 0, "british_spellings": 0}}
BAR = {"pair errors": 0, "report findings": 0, "ungrounded identifiers": 0, "resolver URLs in identifier slots": 0,
       "organisational fragments": 0, "undeclared prefixes": 0, "British spellings": 0}


class TestTheGate(unittest.TestCase):
    def test_a_record_with_duplicate_keys_regresses_against_a_floor_of_zero(self):
        checks = {**GOOD, "validation": {"passed": True, "duplicate_keys": {
            "full": [{"path": "$", "key": "source_caveats", "lines": [812, 1019, 1565], "count": 3}], "core": []}}}
        v = verdict(checks, BAR)
        self.assertEqual(v["status"], REGRESSED)
        self.assertEqual(v["regressions"], ["duplicate keys: 1 against a floor of 0"])
        self.assertIn({"metric": "duplicate keys", "run": 1, "baseline_worst": 0, "regressed": True}, v["rows"])

    def test_a_measured_zero_is_a_row_and_an_unmeasured_block_is_none(self):
        v = verdict({**GOOD, "validation": {"passed": True, "duplicate_keys": {"full": [], "core": []}}}, BAR)
        self.assertEqual(v["status"], OK)
        self.assertIn({"metric": "duplicate keys", "run": 0, "baseline_worst": 0}, v["rows"])
        v = verdict({**GOOD, "validation": {"passed": True}}, BAR)      # predates the instrument
        self.assertEqual(v["status"], OK)
        self.assertNotIn("duplicate keys", [r["metric"] for r in v["rows"]])
        self.assertIsNone(duplicate_key_count({"passed": True}))

    def test_an_unreadable_artifact_is_not_a_measured_zero(self):
        for counts in ({"full": None, "core": []}, {"full": [], "core": None},
                       {"full": [{}], "core": None}, {}, None, {"full": "invalid"},
                       {"full": []}, {"core": []}):
            with self.subTest(counts=counts):
                block = {"passed": False, "duplicate_keys": counts}
                self.assertIsNone(duplicate_key_count(block))
                v = verdict({**GOOD, "validation": block}, BAR)
                self.assertEqual(v["status"], UNMEASURABLE)
                self.assertIn("duplicate keys", v["blind"])
                row = next(r for r in v["rows"] if r["metric"] == "duplicate keys")
                self.assertIsNone(row["run"])
                self.assertIn("unmeasured", row["note"])
                self.assertNotIn("regressed", row)


class TestValidateOutputs(unittest.TestCase):
    def test_a_duplicate_key_is_a_validation_problem_and_is_recorded(self):
        from data_sheets_schema import api_runner
        from data_sheets_schema.api_runner import RunSpec, validate_outputs, validation_block
        with tempfile.TemporaryDirectory() as tmp:
            spec = RunSpec(project="P", arm="", method="m", bundle=Path(tmp) / "b.txt", label="L")
            full = Path(tmp) / "full.yaml"; core = Path(tmp) / "core.yaml"
            full.write_text("id: doi:10.1/x\ntitle: T\nsource_caveats: a\nsource_caveats: b\n")
            core.write_text("id: doi:10.1/x\ntitle: T\n")
            with unittest.mock.patch.object(RunSpec, "full_path", property(lambda self: full)), \
                 unittest.mock.patch.object(RunSpec, "core_path", property(lambda self: core)), \
                 unittest.mock.patch.object(api_runner, "_validator_lines", lambda *a, **k: ([], None)):
                problems = validate_outputs(spec)
                block = validation_block(spec, problems)
        self.assertEqual(len(problems), 1)
        self.assertEqual(problems[0]["class"], "Dataset")
        self.assertIn("`source_caveats` at $ on lines 3, 4", problems[0]["error"])
        self.assertFalse(block["passed"])
        self.assertEqual(block["duplicate_keys"]["full"][0]["key"], "source_caveats")
        self.assertEqual(block["duplicate_keys"]["core"], [])


def _declared_duplicates(artifact: Path) -> list[tuple[str, str, list[int]]]:
    """What the record's own provenance says about this artifact's duplicate
    keys: nothing for a record that predates the instrument, else the
    entries under `validation.duplicate_keys.{full|core}`."""
    label_dir = artifact.parent
    project = artifact.name.split("_d4d")[0]
    kind = "core" if artifact.name.endswith("_d4d_core.yaml") else "full"
    core_dir = label_dir if label_dir.parent.name.endswith("_core") else \
        label_dir.parent.parent / f"{label_dir.parent.name}_core" / label_dir.name
    prov = core_dir / f"{project}_provenance.yaml"
    if not prov.exists():
        return []
    v = (yaml.safe_load(prov.read_text(encoding="utf-8")) or {}).get("validation") or {}
    if v.get("passed") is not False:
        return []
    return [(d["path"], d["key"], d["lines"]) for d in ((v.get("duplicate_keys") or {}).get(kind) or [])]


@pytest.mark.corpus   # walks the committed corpus; the main-branch lane (#1203)
class TestTheCorpus(unittest.TestCase):
    def test_no_committed_record_hides_a_duplicate_key(self):
        """The floor is a fact about the corpus, and a record with a duplicate
        may sit in it only as declared evidence: its own validation block
        says `passed: false` and names the key (#1029; the AI_READI
        2026-09-04f record is the one). An undeclared one fails here as
        well as at the gate."""
        records = sorted(glob.glob(str(ROOT / "data/d4d_concatenated/claudecode_a*/*/*_d4d*.yaml")))
        if not records:
            self.skipTest("no records on disk")
        undeclared = {}
        for f in records:
            found = [(x["path"], x["key"], x["lines"]) for x in
                     find_duplicate_keys(Path(f).read_text(encoding="utf-8", errors="replace"))]
            if found and found != _declared_duplicates(Path(f)):
                undeclared[str(Path(f).relative_to(ROOT))] = found
        self.assertEqual(undeclared, {}, "records with duplicate mapping keys their provenance does not declare (#1029)")



class TestReviewRound(unittest.TestCase):
    """#1032: what the first cut of the instrument missed."""

    def test_aliases_and_cycles_are_walked_once(self):
        self.assertEqual(find_duplicate_keys("loop: &loop {self: *loop}\n"), [])
        shared = "a: &x {k: 1, k: 2}\nb: *x\nc: *x\n"
        self.assertEqual([(d["path"], d["key"]) for d in find_duplicate_keys(shared)], [("a", "k")])

    def test_keys_collide_as_the_loader_constructs_them(self):
        self.assertEqual([d["key"] for d in find_duplicate_keys("true: a\nTrue: b\n")], ["true"])
        self.assertEqual(find_duplicate_keys("1: a\n\"1\": b\n"), [])
        self.assertEqual([d["lines"] for d in find_duplicate_keys("true: a\n1: b\n1.0: c\n")], [[1, 2, 3]])
        self.assertEqual(yaml.safe_load("true: a\n1: b\n1.0: c\n"), {True: "c"})

    def test_unscannable_text_claims_nothing(self):
        self.assertEqual(find_duplicate_keys("a: \0"), [])
        self.assertEqual(find_duplicate_keys("x: " + "[" * 600 + "0" + "]" * 600), [])

    def test_one_finding_per_extra_occurrence_so_a_partial_merge_is_progress(self):
        from data_sheets_schema.duplicate_keys import findings
        three = find_duplicate_keys("a: 1\na: 2\na: 3\n")
        two = find_duplicate_keys("a: 1\na: 2\n")
        self.assertEqual((len(findings(three)), len(findings(two))), (2, 1))
        self.assertEqual(find_duplicate_keys("base: &b {x: 1}\nother: &o {y: 2}\nm:\n  <<: *b\n  <<: *o\n  z: 3\n"), [])
        self.assertEqual(yaml.safe_load("m:\n  <<: [{x: 1}, {y: 2}]\n")["m"], {"x": 1, "y": 2})

    def test_the_repair_round_is_told_about_a_duplicate_and_checks_it_again(self):
        from types import SimpleNamespace
        from unittest import mock

        from data_sheets_schema import api_runner
        from data_sheets_schema.api_runner import RunSpec, _repair_invalid
        prompts = []

        class _Client:
            class messages:
                @staticmethod
                def stream(**kw):
                    prompts.append(kw)
                    body = ("```yaml\n# repaired\nid: doi:10.1/x\ntitle: T\nname: n\ndescription: d\n"
                            "keywords: [a]\nsource_caveats: a; b\n```")

                    class _S:
                        def __enter__(self): return self
                        def __exit__(self, *a): return False
                        def __iter__(self): return iter([SimpleNamespace(type="message_stop")])
                        def get_final_message(self):
                            return SimpleNamespace(content=[SimpleNamespace(type="text", text=body)],
                                                   usage=SimpleNamespace(input_tokens=1, output_tokens=1,
                                                                         cache_read_input_tokens=0,
                                                                         cache_creation_input_tokens=0),
                                                   stop_reason="end_turn")
                    return _S()
        with tempfile.TemporaryDirectory() as tmp:
            spec = RunSpec(project="P", arm="", method="m", bundle=Path(tmp) / "b.txt", label="L",
                           out_dir=Path(tmp))
            spec.full_path.write_text("id: doi:10.1/x\ntitle: T\nname: n\ndescription: d\nkeywords: [a]\n"
                                      "source_caveats: a\nsource_caveats: b\n")
            spec.core_path.write_text("id: doi:10.1/x\ntitle: T\nname: n\ndescription: d\nkeywords: [a]\n")
            usage = []
            with mock.patch.object(api_runner, "_validator_lines", lambda *a, **k: ([], None)), \
                 mock.patch.object(api_runner, "CORE_DERIVED", False), \
                 mock.patch.object(api_runner, "_reasoning_path", lambda s: Path(tmp) / "r.jsonl"), \
                 mock.patch.object(api_runner, "_snapshot", lambda *a, **k: None), \
                 mock.patch.object(api_runner.time, "sleep", lambda *_: None):
                log = _repair_invalid(spec, _Client(), {"name": "m", "temperature": None}, usage)
            self.assertEqual(len(prompts), 1, log)
            sent = str(prompts[0]["messages"])
            self.assertIn("duplicate mapping key", sent)
            self.assertIn("`source_caveats` at $ on lines 6, 7", sent)
            self.assertEqual(find_duplicate_keys(spec.full_path.read_text()), [])
            self.assertTrue(any("validates" in str(e.get("outcome", "")) or e.get("findings") for e in log), log)

    def test_the_method_base_strips_a_core_suffix(self):
        from data_sheets_schema.provenance import record_path_for
        self.assertEqual(record_path_for("P", "claudecode_api_core", "L").parts[-3:],
                         record_path_for("P", "claudecode_api", "L").parts[-3:])

    def test_the_offline_verdict_reads_the_record_and_keeps_the_prior_block(self):
        from data_sheets_schema.canary import offline_verdict
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "claudecode_agent_core" / "v7_rep1"
            base.mkdir(parents=True)
            (base / "P_provenance.yaml").write_text(yaml.safe_dump({
                "pair_consistency": {"ran": True, "errors": 0},
                "report_claims": {"checked": True, "claims_checked": 2, "findings": []},
                "grounding": {"ran": True, "distinct": {"absent": 0}, "findings": []},
                "form": {"ran": True, "organisational_fragments": 0, "undeclared_prefix_occurrences": 0,
                         "british_spellings": 3}}))
            record = {**{k: v for k, v in yaml.safe_load((base / "P_provenance.yaml").read_text()).items()},
                      "validation": {"passed": False, "duplicate_keys": {"full": [{"path": "$", "key": "x",
                                                                                   "lines": [1, 2], "count": 2}],
                                                                         "core": []}},
                      "canary": {"status": "ok", "regressions": [], "recorded_at": "t", "recorded_by": "r"}}
            v = offline_verdict(record, "P", "v7", None, Path(tmp))          # every family searched, as the batch does
            same = offline_verdict(record, "P", "v7", "claudecode_agent", Path(tmp))
            wrong = offline_verdict(record, "P", "v7", "claudecode_api", Path(tmp))
        self.assertEqual(v["status"], REGRESSED)
        self.assertEqual(same["rows"], v["rows"])
        self.assertEqual(wrong["status"], "unmeasurable")                    # the record's own family is not the baseline's
        self.assertEqual(v["regressions"], ["duplicate keys: 1 against a floor of 0"])
        self.assertEqual(v["prior_verdict"], record["canary"])                   # the whole prior block
        self.assertIn("'v7'", v["basis"])
        self.assertTrue(v["recorded_by"].endswith("(offline)"))


if __name__ == "__main__":
    unittest.main()

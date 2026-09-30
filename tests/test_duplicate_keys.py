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


#: A child process that scans texts nested 50,000 deep with libyaml. Before
#: #3817 the flow case killed the interpreter with SIGSEGV (exit 139), which
#: is why it runs in a subprocess and not in pytest's own process.
_DEEP_CHILD = """
import sys, yaml
from data_sheets_schema.duplicate_keys import FAST_LOADER, find_duplicate_keys
n = 50_000
texts = {
    "flow": "a: 1\\na: 2\\nb: " + "{x: " * n + "1" + "}" * n + "\\n",
    "block sequence": "- " * n + "x\\n",
    "key position": "? " * n + "x\\n",
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
        self.assertEqual(proc.stdout.strip(), "refused 3")

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

    def test_the_textual_bound_is_never_below_the_nesting(self):
        from data_sheets_schema.duplicate_keys import depth_bound
        unparseable = ("id: [unterminated\n", "a: \0", "a: 1\n---\nb: 2\n")
        texts = [t for t in PARITY if t not in unparseable] + [
            _block(40), _flow(40), "- - - - - x\n", "? - - a\n: - - b\n", "- a:\n  - b:\n    - c: 1\n",
            "a:\n- b:\n  - c\n", "[a: [b: [c: [d: 1]]]]\n", "{a: [{b: [x]}]}\n", "- &x !!map\n  k: [1, [2]]\n",
            "k: |\n  [[[[\n", "a:\r\n  b:\r\n    - [c]\r\n", "a:\u2028  b: 1\n", "",
        ]
        for text in texts:
            with self.subTest(text=text[:60]):
                self.assertGreaterEqual(depth_bound(text), _event_depth(text))

    def test_the_event_pass_runs_only_where_the_bound_cannot_clear_the_text(self):
        """A text whose bound is within the limit is parsed once, not twice."""
        from data_sheets_schema import duplicate_keys
        opened = []

        class Counting(yaml.CSafeLoader):
            def __init__(self, stream):
                opened.append(1)
                super().__init__(stream)

        self.assertEqual(len(find_duplicate_keys("a: 1\na: 2\nb: [[1]]\n", loader=Counting)), 1)
        self.assertEqual(len(opened), 1)
        with unittest.mock.patch.object(duplicate_keys, "LIBYAML_MAX_DEPTH", 3):
            opened.clear()
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

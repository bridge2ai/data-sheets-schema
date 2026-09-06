"""Duplicate mapping keys are a validation failure and a gated floor (#1029).

The AI_READI 2026-09-04f full record carried a top-level `source_caveats`
three times; `yaml.safe_load` kept the last and `validation.passed` read
true. None of the corpus records on main had a duplicate key.
"""

import glob
import tempfile
import unittest
import unittest.mock
from pathlib import Path

import yaml

from data_sheets_schema.canary import OK, REGRESSED, duplicate_key_count, verdict
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
        self.assertEqual(duplicate_key_count({"passed": True}), 0)


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
        self.assertIn("#1020", v["basis"])


if __name__ == "__main__":
    unittest.main()

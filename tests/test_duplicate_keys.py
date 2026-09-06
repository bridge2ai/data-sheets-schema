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


class TestTheCorpus(unittest.TestCase):
    def test_no_committed_record_has_a_duplicate_key(self):
        """The floor of 0 is a fact about the corpus; a new record with one fails here as well as at the gate."""
        records = sorted(glob.glob(str(ROOT / "data/d4d_concatenated/claudecode_a*/*/*_d4d*.yaml")))
        if not records:
            self.skipTest("no records on disk")
        offenders = {}
        for f in records:
            d = find_duplicate_keys(Path(f).read_text(encoding="utf-8", errors="replace"))
            if d:
                offenders[str(Path(f).relative_to(ROOT))] = [(x["path"], x["key"], x["lines"]) for x in d]
        self.assertEqual(offenders, {}, "records with duplicate mapping keys (#1029)")



if __name__ == "__main__":
    unittest.main()

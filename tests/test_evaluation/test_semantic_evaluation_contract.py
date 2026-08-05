"""The semantic schemas must describe what the agents instruct (#323).

`scripts/validate_evaluation_schema.py` reported `Valid: 0, Invalid: 28` — not
one recorded semantic evaluation conformed to its own JSON schema. Nothing ran
the validator, so nothing said so.

Six independent drifts, all the same shape: the schemas described the 2025-12
output and the agents moved on.

    rubric20  overall_score required `percentage`; the agent emits the N/A
              vocabulary (`normalized_percentage`, `adjusted_max_points`, …)
    rubric10  required `summary_scores` / `element_scores`; the agent has
              instructed `overall_score` / `elements` since 2026-07
    both      `score` typed `number`, so `score: null` — the N/A convention's
              way of saying "not assessed", already on disk 6 times — failed
    rubric10  `semantic_insights` typed `string` against an array
    rubric10  `severity` enumerated critical|warning|info against the agent's
              low|medium|high, `consistency_checks` typed as arrays against
              three counters, `grant_format` against `grant_number_format`
    rubric10  `method` enumerated a hand-written subset that rejected
              `claudecode_agent_core`, a method the pipeline has produced for
              months
    rubric10  `element_max` fixed at `const: 5`, which the N/A convention
              contradicts — records already carry `element_max: 3`

The tests below assert the *contract*, not that historical records pass. Twenty
still fail and should: 12 predate the contract, and 8 report `max_points: 84`,
a maximum the rubric has never had (#314). Weakening the schema to admit those
would be the opposite of the fix.

The load-bearing test is `TestTheContractIsSatisfiable`: a record built to what
the agent documents must validate. That is what the rerun will produce, and it
is the only test here that would have failed for every one of the six drifts at
once.
"""

import importlib.util
import json
import unittest
from pathlib import Path

import yaml

from data_sheets_schema.constants import METHODS
from data_sheets_schema.constants.evaluation import RUBRIC10_PATH, RUBRIC20_PATH

REPO = Path(__file__).resolve().parents[2]
PROMPTS = REPO / "src" / "download" / "prompts"
SCHEMAS = {
    "rubric10-semantic": PROMPTS / "rubric10_semantic_schema.json",
    "rubric20-semantic": PROMPTS / "rubric20_semantic_schema.json",
}
VALIDATOR = REPO / "scripts" / "validate_evaluation_schema.py"


def _schema(name):
    return json.loads(SCHEMAS[name].read_text())


def _validator():
    spec = importlib.util.spec_from_file_location("validate_evaluation_schema", VALIDATOR)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _rubric20_maximum():
    questions = yaml.safe_load(Path(RUBRIC20_PATH).read_text())[
        "d4d_evaluation_rubric"]["rubric"]
    return sum(1 if q.get("score_type") == "pass_fail" else 5 for q in questions)


def _rubric10_maximum():
    elements = yaml.safe_load(Path(RUBRIC10_PATH).read_text())[
        "d4d_complex_proxy_rubric"]["rubric"]
    return sum(len(e.get("sub_elements") or []) for e in elements)


def _semantic_analysis():
    """The block both agents instruct, identically."""
    return {
        "issues_detected": [{
            "type": "consistency",
            "severity": "medium",
            "description": "human_subject_research is true with no ethical_reviews",
            "fields_involved": ["human_subject_research", "ethical_reviews"],
            "recommendation": "Populate ethical_reviews",
        }],
        "semantic_insights": ["PhysioNet DOI prefix (10.13026) correctly used"],
        "consistency_checks": {"passed": 15, "failed": 2, "warnings": 3},
        "correctness_validations": {
            "doi_format": "valid",
            "grant_number_format": "valid",
            "rrid_format": "not_present",
            "url_validity": "all_valid",
        },
    }


def _rubric20_record(**overrides):
    """A rubric20-semantic evaluation shaped as the agent documents it.

    Built from `rubric20.txt` rather than hand-written, so it carries all 20
    questions in the four categories the schema requires, with each question's
    real name and score type. A one-category stub passed the checks that matter
    here while failing `minItems: 4`, which is the schema being right.
    """
    questions = yaml.safe_load(Path(RUBRIC20_PATH).read_text())[
        "d4d_evaluation_rubric"]["rubric"]
    names = ["Structural Completeness", "Metadata Quality & Content",
             "Technical Documentation", "FAIRness & Accessibility"]
    categories = []
    for index, name in enumerate(names):
        block = questions[index * 5:(index + 1) * 5]
        rendered, earned, available = [], 0, 0
        for q in block:
            pass_fail = q.get("score_type") == "pass_fail"
            top = 1 if pass_fail else 5
            entry = {
                "id": q["id"], "name": q["name"],
                "description": (q.get("description") or "")[:120],
                "score_type": q.get("score_type"), "score": top,
                "max_score": top, "score_label": "top band",
                "evidence": "quoted from the record",
                "quality_note": "assessed against the named fields",
            }
            if q["id"] == 11:
                # The N/A convention, which `score: {type: number}` rejected.
                entry.update({"score": None, "applicable": "false",
                              "applicability_status": "not_applicable",
                              "applicability_evidence":
                                  "no code repository in external_resources",
                              "score_label": "Not applicable",
                              "quality_note": "Excluded from the denominator"})
            else:
                earned += top
            available += top
            rendered.append(entry)
        categories.append({"name": name, "questions": rendered,
                           "category_score": earned, "category_max": available})

    top = _rubric20_maximum()
    record = {
        "rubric": "rubric20-semantic",
        "version": "1.0",
        "d4d_file": "AI_READI_d4d.yaml",
        "project": "AI_READI",
        "method": "claudecode_agent_core",
        "evaluation_timestamp": "2026-08-05T00:00:00Z",
        "model": {"name": "claude-fable-5", "temperature": 0.0,
                  "evaluation_type": "semantic_llm_judge"},
        "overall_score": {
            "total_points": top - 5, "max_points": top,
            "excluded_max_points": 5, "adjusted_max_points": top - 5,
            "normalized_percentage": 100.0, "questions_not_applicable": 1,
        },
        "categories": categories,
        "semantic_analysis": _semantic_analysis(),
    }
    record.update(overrides)
    return record


def _rubric10_record(**overrides):
    """A rubric10-semantic evaluation shaped as the agent documents it."""
    record = {
        "rubric": "rubric10-semantic",
        "version": "1.0",
        "d4d_file": "AI_READI_d4d.yaml",
        "project": "AI_READI",
        "method": "claudecode_agent_core",
        "evaluation_timestamp": "2026-08-05T00:00:00Z",
        "model": {"name": "claude-fable-5", "temperature": 0.0,
                  "evaluation_type": "semantic_llm_judge"},
        "overall_score": {
            "total_points": 38, "max_points": _rubric10_maximum(),
            "excluded_max_points": 2, "adjusted_max_points": _rubric10_maximum() - 2,
            "normalized_percentage": 79.2, "sub_elements_not_applicable": 2,
        },
        "elements": [
            {"id": i, "name": f"Element {i}", "description": "…",
             "sub_elements": [
                 {"name": f"sub {j}", "score": 1, "evidence": "…",
                  "quality_note": "…"} for j in range(1, 6)],
             "element_score": 5, "element_max": 5}
            for i in range(1, 11)
        ],
        "semantic_analysis": _semantic_analysis(),
    }
    # Element 8 carries the N/A convention: two sub-elements excluded, so its
    # maximum is 3 rather than 5. `const: 5` forbade exactly this.
    record["elements"][7]["sub_elements"][0]["score"] = None
    record["elements"][7]["sub_elements"][1]["score"] = None
    record["elements"][7]["element_score"] = 3
    record["elements"][7]["element_max"] = 3
    record.update(overrides)
    return record


class TestTheContractIsSatisfiable(unittest.TestCase):
    """A record shaped as the agent documents must validate.

    Every one of the six drifts would fail this, which is why it is here rather
    than a test per drift. If the agents change again, this is what breaks.
    """

    def _assert_valid(self, record, schema_name):
        import jsonschema
        errors = sorted(jsonschema.Draft7Validator(_schema(schema_name)).iter_errors(record),
                        key=lambda e: list(e.absolute_path))
        self.assertEqual(
            [], [f"{list(e.absolute_path)}: {e.message}" for e in errors])

    def test_a_rubric20_record_as_the_agent_documents_it_validates(self):
        self._assert_valid(_rubric20_record(), "rubric20-semantic")

    def test_a_rubric10_record_as_the_agent_documents_it_validates(self):
        self._assert_valid(_rubric10_record(), "rubric10-semantic")

    def test_a_record_with_no_exclusions_validates(self):
        """The N/A vocabulary is required, not conditional on anything being
        excluded — a record that excludes nothing still reports zeros."""
        top = _rubric20_maximum()
        self._assert_valid(_rubric20_record(overall_score={
            "total_points": 80, "max_points": top, "excluded_max_points": 0,
            "adjusted_max_points": top, "normalized_percentage": 90.9,
            "questions_not_applicable": 0}), "rubric20-semantic")


class TestTheSchemasStillReject(unittest.TestCase):
    """The contract has to be able to say no, or the tests above are vacuous."""

    def _errors(self, record, schema_name):
        import jsonschema
        return list(jsonschema.Draft7Validator(_schema(schema_name)).iter_errors(record))

    def test_the_superseded_maximum_is_rejected(self):
        """The 8 recorded rubric20 evaluations report 84 and should fail."""
        bad = _rubric20_record()
        bad["overall_score"]["max_points"] = 84
        self.assertTrue(self._errors(bad, "rubric20-semantic"))

    def test_an_unknown_method_is_rejected(self):
        bad = _rubric20_record(method="claudecode_agent_corex")
        self.assertTrue(self._errors(bad, "rubric20-semantic"))

    def test_a_missing_normalized_percentage_is_rejected(self):
        bad = _rubric20_record()
        del bad["overall_score"]["normalized_percentage"]
        self.assertTrue(self._errors(bad, "rubric20-semantic"))

    def test_a_sub_element_score_outside_the_vocabulary_is_rejected(self):
        bad = _rubric10_record()
        bad["elements"][0]["sub_elements"][0]["score"] = 3
        self.assertTrue(self._errors(bad, "rubric10-semantic"))


class TestTheDenominators(unittest.TestCase):
    """Pinned to the rubrics, not restated."""

    def test_rubric20_max_points_matches_the_questions(self):
        node = _schema("rubric20-semantic")["properties"]["overall_score"] \
            ["properties"]["max_points"]
        self.assertEqual(node.get("const"), _rubric20_maximum())

    def test_rubric10_max_points_matches_the_sub_elements(self):
        node = _schema("rubric10-semantic")["properties"]["overall_score"] \
            ["properties"]["max_points"]
        self.assertEqual(node.get("const"), _rubric10_maximum())


class TestTheMethodVocabulary(unittest.TestCase):
    """A hand-written subset rejected `claudecode_agent_core` for months."""

    def test_both_schemas_enumerate_the_canonical_methods(self):
        for name in SCHEMAS:
            with self.subTest(schema=name):
                self.assertEqual(_schema(name)["properties"]["method"].get("enum"),
                                 list(METHODS))


class TestTheValidatorClassifies(unittest.TestCase):
    """`Invalid: 28` said nothing about which records were merely old."""

    @classmethod
    def setUpClass(cls):
        cls.module = _validator()

    def test_a_conformant_record_is_valid(self):
        status, _ = self.module.classify(_rubric20_record(), _schema("rubric20-semantic"))
        self.assertEqual(status, "valid")

    def test_a_pre_contract_shape_is_superseded_not_invalid(self):
        old = _rubric10_record()
        old["summary_scores"] = old.pop("overall_score")
        old["element_scores"] = old.pop("elements")
        status, _ = self.module.classify(old, _schema("rubric10-semantic"))
        self.assertEqual(status, "superseded")

    def test_a_wrong_value_in_the_current_shape_is_invalid(self):
        """The distinction that matters: an 84-denominator record has the right
        shape and the wrong number, and must not be excused as old."""
        bad = _rubric20_record()
        bad["overall_score"]["max_points"] = 84
        status, _ = self.module.classify(bad, _schema("rubric20-semantic"))
        self.assertEqual(status, "invalid")


if __name__ == "__main__":
    unittest.main()

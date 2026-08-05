"""The hybrid rubric20 scorer must score the rubric the repository publishes (#314).

`scripts/batch_evaluate_rubric20_hybrid.py` carries its own copy of the 20
questions and writes the records under `data/evaluation_llm/rubric20/`. Its copy
had drifted from `data/rubric/rubric20.txt` on five questions, and Q20 was not a
rename: the script scored a retired "Interlinking Across Platforms and Datasets"
as pass/fail worth 1 where the rubric defines "Bias Documentation and
Responsible AI Alignment" as numeric worth 5.

That produced a worse failure than the agents'. #275 corrected
`RUBRIC20_MAX_SCORE` to 88 and the script's `max_total = RUBRIC20_MAX_SCORE`
went with it, but the question table still summed to **84** — so a record that
scored every available point was reported as 95.5%, and no percentage the script
emitted could reach 100. A denominator imported from a constant cannot notice
that its own numerator has a different ceiling.

Hence `TestTheDenominator`: the fix is not "set it to
88", it is deriving the maximum from the table and refusing to run when the two
disagree.
"""

import importlib.util
import re
import tempfile
import unittest
from pathlib import Path

import yaml

from data_sheets_schema.constants import RUBRIC20_MAX_SCORE
from data_sheets_schema.constants.evaluation import RUBRIC20_PATH

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "batch_evaluate_rubric20_hybrid.py"


def _load():
    spec = importlib.util.spec_from_file_location("rubric20_hybrid", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _questions():
    return yaml.safe_load(Path(RUBRIC20_PATH).read_text())[
        "d4d_evaluation_rubric"]["rubric"]


@unittest.skipUnless(SCRIPT.exists(), "hybrid scorer not present")
class TestQuestionTableParity(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.table = _load().RUBRIC20_QUESTIONS
        cls.canon = _questions()

    def test_every_rubric_question_is_scored(self):
        self.assertEqual(sorted(self.table), list(range(1, len(self.canon) + 1)))

    def test_names_match(self):
        for i, q in enumerate(self.canon, 1):
            with self.subTest(question=i):
                self.assertEqual(self.table[i]["name"].strip().lower(),
                                 q["name"].strip().lower())

    def test_score_types_and_maxima_match(self):
        """Q20 as pass/fail worth 1 against numeric worth 5 is the whole 84."""
        for i, q in enumerate(self.canon, 1):
            want_type = q.get("score_type")
            want_max = 1 if want_type == "pass_fail" else 5
            with self.subTest(question=i):
                self.assertEqual(self.table[i]["score_type"], want_type)
                self.assertEqual(self.table[i]["max_score"], want_max)

    def test_the_retired_question_is_gone(self):
        names = {spec["name"] for spec in self.table.values()}
        self.assertNotIn("Interlinking Across Platforms and Datasets", names)

    def test_the_table_reaches_the_published_maximum(self):
        self.assertEqual(sum(s["max_score"] for s in self.table.values()),
                         RUBRIC20_MAX_SCORE)


@unittest.skipUnless(SCRIPT.exists(), "hybrid scorer not present")
class TestTheDenominator(unittest.TestCase):

    def test_the_intact_table_yields_the_published_maximum(self):
        """`84/88` was not visible as an error anywhere — every percentage
        simply stopped short of 100."""
        self.assertEqual(_load().derived_maximum(), RUBRIC20_MAX_SCORE)

    def test_a_drifted_table_stops_the_run(self):
        """Shrinking one question's maximum is exactly the shape the defect
        had: the table can no longer reach `RUBRIC20_MAX_SCORE`, and before the
        fix that produced percentages with an unreachable ceiling rather than
        an error."""
        module = _load()
        module.RUBRIC20_QUESTIONS[20]["max_score"] = 1  # re-open the 84
        with self.assertRaises(ValueError) as caught:
            module.derived_maximum()
        self.assertIn("drifted", str(caught.exception))

    def test_the_scorer_itself_refuses_a_drifted_table(self):
        """Not just the helper — the call site has to reach it.

        Asserted by scoring a real file, because the previous version of this
        test asserted on the script's source text and would have passed against
        a `derived_maximum()` that nothing called.
        """
        module = _load()
        with tempfile.TemporaryDirectory(dir=REPO) as tmp:
            record = Path(tmp) / "VOICE_d4d.yaml"
            record.write_text("id: https://example.org/d4d/voice\ntitle: VOICE\n")

            scored = module.evaluate_d4d_file(record, "VOICE", "m", "concatenated")
            self.assertEqual(scored["overall_score"]["max_points"],
                             RUBRIC20_MAX_SCORE)

            module.RUBRIC20_QUESTIONS[20]["max_score"] = 1  # re-open the 84
            with self.assertRaises(ValueError) as caught:
                module.evaluate_d4d_file(record, "VOICE", "m", "concatenated")
            self.assertIn("drifted", str(caught.exception))

    def test_the_guard_runs_at_import(self):
        """Partway through a batch is too late to discover it.

        Q20 is shrunk in the *source* and the module executed from scratch, so
        the only thing that can raise is module-scope execution — a guard that
        only ran from `evaluate_d4d_file` would let the import succeed.
        """
        source = SCRIPT.read_text()
        tampered = re.sub(r'("fields": \["known_biases", "future_use_impacts"\],\n\s+'
                          r'"score_type": "numeric",\n\s+"max_score": )5',
                          r"\g<1>1", source)
        self.assertNotEqual(tampered, source, "could not shrink Q20 in the source")
        namespace = {"__name__": "tampered_rubric20_hybrid", "__file__": str(SCRIPT)}
        with self.assertRaises(ValueError) as caught:
            exec(compile(tampered, str(SCRIPT), "exec"), namespace)
        self.assertIn("drifted", str(caught.exception))


@unittest.skipUnless(SCRIPT.exists(), "hybrid scorer not present")
class TestBiasDocumentationScoring(unittest.TestCase):
    """Q20's bands, which no longer exist anywhere else to compare against.

    The taxonomy check reads `bias_type` structurally rather than grepping for
    the word "bias", so prose that says "selection bias" scores 3 and a
    populated `bias_type` scores 5. That distinction is the rubric's, and it is
    the only thing separating the two bands.
    """

    @classmethod
    def setUpClass(cls):
        cls.module = _load()

    def _score(self, data):
        return self.module.evaluate_question(data, 20)[0]

    def test_absent_scores_zero(self):
        self.assertEqual(self._score({}), 0)

    def test_prose_without_a_taxonomy_scores_three(self):
        self.assertEqual(self._score(
            {"known_biases": [{"bias_description": "Recruitment favoured urban clinics"}]}), 3)

    def test_a_taxonomy_without_fairness_analysis_scores_three(self):
        """Both halves are required for 5 — categorisation alone is not enough."""
        self.assertEqual(self._score(
            {"known_biases": [{"bias_type": "selection_bias",
                               "bias_description": "urban clinics"}]}), 3)

    def test_taxonomy_plus_mitigation_scores_five(self):
        self.assertEqual(self._score(
            {"known_biases": [{"bias_type": "selection_bias",
                               "bias_description": "urban clinics",
                               "mitigation_strategy": "oversample rural sites"}]}), 5)

    def test_a_single_mapping_is_accepted_as_well_as_a_list(self):
        """`known_biases` is multivalued, but records emit a bare mapping."""
        self.assertEqual(self._score(
            {"known_biases": {"bias_type": "sampling_bias",
                              "affected_subsets": ["female participants"]}}), 5)

    def test_a_value_outside_the_enum_is_not_a_taxonomy(self):
        """Otherwise any string in `bias_type` buys the 5."""
        self.assertEqual(self._score(
            {"known_biases": [{"bias_type": "vibes_bias",
                               "mitigation_strategy": "none"}]}), 3)

    def test_one_typed_bias_among_many_is_not_comprehensive(self):
        """#318. Band 5 is "Comprehensive bias categorization"; nine untyped
        biases beside one typed one is the 3 band by any reading."""
        self.assertEqual(self._score({"known_biases":
            [{"bias_type": "selection_bias", "mitigation_strategy": "x"}]
            + [{"bias_description": f"bias {i}"} for i in range(9)]}), 3)

    def test_the_taxonomy_and_the_fairness_analysis_must_meet(self):
        """#318. Computing the two lists independently let one bias supply the
        `bias_type` and an entirely different one supply the mitigation."""
        self.assertEqual(self._score({"known_biases": [
            {"bias_type": "selection_bias", "bias_description": "urban clinics"},
            {"bias_description": "unrelated", "mitigation_strategy": "something"}]}), 3)

    def test_every_bias_typed_with_one_analysed_scores_five(self):
        """The complement: the rule must remain satisfiable."""
        self.assertEqual(self._score({"known_biases": [
            {"bias_type": "selection_bias", "mitigation_strategy": "oversample rural"},
            {"bias_type": "measurement_bias", "bias_description": "device variance"}]}), 5)

    def test_the_taxonomy_matches_the_schema(self):
        """#317. The script restates `BiasTypeEnum` rather than loading the
        merged schema in a batch script's import path, so this is what keeps the
        two in step.

        Drift is silent otherwise: a record categorising a bias with a value the
        schema added scores 3 where the rubric says 5, and is penalised for
        using the vocabulary the schema told it to use.
        """
        from linkml_runtime.utils.schemaview import SchemaView
        schema = REPO / "src" / "data_sheets_schema" / "schema" / "data_sheets_schema_all.yaml"
        declared = {str(v) for v in
                    SchemaView(str(schema)).get_enum("BiasTypeEnum").permissible_values}
        self.assertEqual(set(self.module.BIAS_TYPE_ENUM), declared)


if __name__ == "__main__":
    unittest.main()

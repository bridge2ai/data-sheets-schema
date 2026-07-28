"""Tests for the healthsheet-only generation input."""

import json
import tempfile
import unittest
from pathlib import Path

from data_sheets_schema.healthsheet import build_bundle, load_healthsheet, render

RECORD = {
    "title": "Test Dataset",
    "doi": "10.60775/test",
    "metadata": {
        "healthsheet": {
            "motivation": [
                {"id": 1, "question": "Why was it made?", "response": "To test."},
                {"id": 2, "question": "Unanswered one?", "response": ""},
            ],
            "collection": [
                {"id": 1, "question": "How collected?", "response": "Carefully."},
            ],
        }
    },
}


class TestRender(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.record_path = Path(self.tmp.name) / "record.json"
        self.record_path.write_text(json.dumps(RECORD))

    def tearDown(self):
        self.tmp.cleanup()

    def test_every_question_and_answer_appears(self):
        text, stats = render(RECORD["metadata"]["healthsheet"], RECORD,
                             self.record_path)
        self.assertIn("Why was it made?", text)
        self.assertIn("To test.", text)
        self.assertIn("How collected?", text)
        self.assertIn("Carefully.", text)
        self.assertEqual(stats.questions, 3)
        self.assertEqual(stats.answered, 2)

    def test_unanswered_questions_are_shown_not_dropped(self):
        text, stats = render(RECORD["metadata"]["healthsheet"], RECORD,
                             self.record_path)
        self.assertIn("Unanswered one?", text)
        self.assertIn("(no response provided)", text)
        self.assertEqual(stats.unanswered, ["motivation:2"])

    def test_sections_are_labelled(self):
        text, _ = render(RECORD["metadata"]["healthsheet"], RECORD, self.record_path)
        self.assertIn("SECTION: MOTIVATION", text)
        self.assertIn("SECTION: COLLECTION", text)

    def test_bundle_states_it_is_not_the_baseline(self):
        """The header must not let anyone mistake this for the AI-READI corpus."""
        text, _ = render(RECORD["metadata"]["healthsheet"], RECORD, self.record_path)
        self.assertIn("NOT the", text)
        self.assertIn("baseline", text)

    def test_build_writes_the_bundle(self):
        out_dir = Path(self.tmp.name) / "out"
        target, stats = build_bundle(self.record_path, out_dir)
        self.assertTrue(target.exists())
        self.assertEqual(stats.sections, 2)
        self.assertIn("Test Dataset", target.read_text())

    def test_missing_healthsheet_is_an_error(self):
        bad = Path(self.tmp.name) / "bad.json"
        bad.write_text(json.dumps({"metadata": {}}))
        with self.assertRaises(KeyError):
            load_healthsheet(bad)


class TestArmRegistration(unittest.TestCase):
    def test_arm_is_restricted_to_ai_readi(self):
        from data_sheets_schema.constants.methods import GENERATION_ARMS
        arm = GENERATION_ARMS["healthsheet_only"]
        self.assertEqual(arm["projects"], ["AI_READI"])
        self.assertTrue(arm["model_involved"])

    def test_arm_is_counted_as_stochastic(self):
        from data_sheets_schema.constants.methods import STOCHASTIC_ARMS
        self.assertIn("healthsheet_only", STOCHASTIC_ARMS)


if __name__ == "__main__":
    unittest.main()

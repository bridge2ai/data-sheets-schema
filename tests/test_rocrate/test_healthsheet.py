"""Tests for the healthsheet-only generation input."""

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from data_sheets_schema.healthsheet import build_bundle, load_healthsheet, render

ROOT = Path(__file__).resolve().parents[2]

_SAVED_PROFILE = None


def setUpModule():
    """The renderer's default project is the active profile's; these tests
    render the study's shape, whatever `D4D_PROFILE` says outside (#1582)."""
    global _SAVED_PROFILE
    import os
    _SAVED_PROFILE = os.environ.pop("D4D_PROFILE", None)


def tearDownModule():
    import os
    if _SAVED_PROFILE is not None:
        os.environ["D4D_PROFILE"] = _SAVED_PROFILE

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
        """A record that is not the profile's names its project and gets its
        own file — never the study's tracked bundle name (#1493)."""
        out_dir = Path(self.tmp.name) / "out"
        with self.assertRaises(ValueError):
            build_bundle(self.record_path, out_dir)
        target, stats = build_bundle(self.record_path, out_dir, project="TESTPROJ")
        self.assertEqual(target.name, "TESTPROJ_healthsheet_only.txt")
        self.assertIn("Project: TESTPROJ", target.read_text())
        self.assertTrue(target.exists())
        self.assertEqual(stats.sections, 2)
        self.assertIn("Test Dataset", target.read_text())

    def test_missing_healthsheet_is_an_error(self):
        bad = Path(self.tmp.name) / "bad.json"
        bad.write_text(json.dumps({"metadata": {}}))
        with self.assertRaises(KeyError):
            load_healthsheet(bad)


#: A record that is no profile's and names no platform anywhere, so a
#: platform in its bundle could only come from the renderer (#4009).
FOREIGN = {
    "title": "Independent Clinic Cohort",
    "doi": "10.1234/clinic",
    "metadata": {"healthsheet": {"cohort": [{"id": 1, "question": "Who took part?", "response": "Adults."}]}},
}


class TestOrigin(unittest.TestCase):
    """The `Origin:` line says where a record came from, which only its
    profile knows: the study's text for the study's own record under
    `bridge2ai`, and no line for any other record or under `neutral` (#4009)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name)
        self.foreign = self.out / "clinic_record.json"
        self.foreign.write_text(json.dumps(FOREIGN), encoding="utf-8")
        self._cwd = os.getcwd()
        os.chdir(ROOT)                     # `Source:` is shown relative to the checkout in use
        self._env = mock.patch.dict(os.environ, {"D4D_PROFILE": "bridge2ai"})
        self._env.start()

    def tearDown(self):
        self._env.stop()
        os.chdir(self._cwd)
        self.tmp.cleanup()

    def _study(self):
        from data_sheets_schema.profiles import BRIDGE2AI
        record = ROOT / BRIDGE2AI.healthsheet_record
        tracked = ROOT / "data/preprocessed/concatenated" / BRIDGE2AI.healthsheet_bundle
        if not (record.exists() and tracked.exists()):
            self.skipTest("the study's healthsheet record or bundle is not in this checkout")
        return record, tracked

    @staticmethod
    def _origin_lines(text):
        return [line for line in text.splitlines() if line.startswith("Origin:")]

    def test_the_study_bundle_keeps_its_bytes(self):
        """The profile now states the line; the tracked bundle, which its
        chunk manifest and the arm's records pin, does not move a byte."""
        from data_sheets_schema.profiles import BRIDGE2AI
        record, tracked = self._study()
        target, _ = build_bundle(record, self.out)
        self.assertEqual(target.name, BRIDGE2AI.healthsheet_bundle)
        self.assertEqual(hashlib.sha256(target.read_bytes()).hexdigest(),
                         hashlib.sha256(tracked.read_bytes()).hexdigest())
        self.assertEqual(self._origin_lines(target.read_text(encoding="utf-8")),
                         [f"Origin: {BRIDGE2AI.healthsheet_origin}"])

    def test_the_origin_follows_the_record_not_the_project(self):
        """The study's record filed under another project is still that record."""
        from data_sheets_schema.profiles import BRIDGE2AI
        record, _ = self._study()
        target, _ = build_bundle(record, self.out, project="CLINIC")
        self.assertEqual(target.name, "CLINIC_healthsheet_only.txt")
        self.assertEqual(self._origin_lines(target.read_text(encoding="utf-8")),
                         [f"Origin: {BRIDGE2AI.healthsheet_origin}"])

    def test_another_record_states_no_origin(self):
        """Under `bridge2ai`, a record passed with --project, with --name, or
        claiming the study's project gets no `Origin:` line, least of all
        the study's."""
        for kw in ({"project": "CLINIC"}, {"project": "CLINIC", "name": "clinic.txt"},
                   {"project": "AI_READI", "name": "other.txt"}):
            with self.subTest(**kw):
                target, _ = build_bundle(self.foreign, self.out, **kw)
                text = target.read_text(encoding="utf-8")
                self.assertIn(f"Project: {kw['project']}", text)
                self.assertEqual(self._origin_lines(text), [])
                self.assertNotIn("fairhub", text.lower())

    def test_neutral_states_no_origin_for_any_record(self):
        """`neutral` states no origin, so no record gets one: the study's
        capture included, which is no profile's record there."""
        from data_sheets_schema.profiles import NEUTRAL
        self.assertIsNone(NEUTRAL.healthsheet_origin)
        os.environ["D4D_PROFILE"] = "neutral"
        target, _ = build_bundle(self.foreign, self.out, project="CLINIC")
        text = target.read_text(encoding="utf-8")
        self.assertEqual(self._origin_lines(text), [])
        self.assertNotIn("fairhub", text.lower())
        record, _ = self._study()
        target, _ = build_bundle(record, self.out, project="AI_READI", name="study_under_neutral.txt")
        self.assertEqual(self._origin_lines(target.read_text(encoding="utf-8")), [])

    def test_render_writes_the_origin_it_is_given_after_the_source(self):
        """Only a given origin is written, directly after `Source:`, where
        the tracked bundle has it."""
        healthsheet = FOREIGN["metadata"]["healthsheet"]
        text, _ = render(healthsheet, FOREIGN, self.foreign, project="CLINIC")
        self.assertEqual(self._origin_lines(text), [])
        text, _ = render(healthsheet, FOREIGN, self.foreign, project="CLINIC", origin="Clinic portal export")
        lines = text.splitlines()
        source = next(i for i, line in enumerate(lines) if line.startswith("Source: "))
        self.assertEqual(lines[source + 1:source + 3], ["Origin: Clinic portal export", ""])


class TestArmRegistration(unittest.TestCase):
    def test_arm_is_restricted_to_ai_readi_by_the_study_profile(self):
        """The arm table declares the arm; which datasets it applies to is
        the profile's fact (#628, #1444) — the table carries no list."""
        from data_sheets_schema.constants.methods import GENERATION_ARMS
        from data_sheets_schema.profiles import BRIDGE2AI, NEUTRAL, arm_projects_for
        arm = GENERATION_ARMS["healthsheet_only"]
        self.assertNotIn("projects", arm)
        self.assertTrue(arm["model_involved"])
        self.assertEqual(arm_projects_for("healthsheet_only", BRIDGE2AI), ["AI_READI"])
        self.assertIsNone(arm_projects_for("healthsheet_only", NEUTRAL))

    def test_arm_is_counted_as_stochastic(self):
        from data_sheets_schema.constants.methods import STOCHASTIC_ARMS
        self.assertIn("healthsheet_only", STOCHASTIC_ARMS)


if __name__ == "__main__":
    unittest.main()

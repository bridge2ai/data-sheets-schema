"""Structural guards on the prompt-condition design.

The generic-vs-tuned comparison only means anything if two properties hold:
the generic prompt carries no project-specific content, and the tuned prompt
differs from it by exactly the component block. Both are easy to break with a
well-meaning edit — adding one clarifying sentence to the generic prompt for one
project silently converts it into a third condition, which is what happened to
the 2026-07-28 `-deprimed` series.

These tests are cheap and catch that.
"""

import re
import unittest
from pathlib import Path
from data_sheets_schema.constants import PROJECTS

PROMPTS = Path("src/download/prompts")
GENERIC = PROMPTS / "d4d_generic_arm_prompt.md"
TUNED = PROMPTS / "d4d_tuned_arm_prompt.md"
COMPONENTS = PROMPTS / "components"
# PROJECTS is imported, not restated. A four-project literal here made
# the per-project assertions below exclude VOICE_PEDIATRIC from the day
# #298 made it a project, so a guard that reads as covering every
# project covered four of five (#467).
#
# Widening it immediately found the gap the narrowing had hidden:
# VOICE_PEDIATRIC has no component file, so the `tuned` condition cannot be run
# for it (#478). Authoring one is content and a judgement call — it must state
# what distinguishes the pediatric cohort without importing adult-cohort facts —
# so the gap is pinned by name rather than papered over. The other four projects
# stay guarded, and this list may only shrink.
WITHOUT_COMPONENT = {"VOICE_PEDIATRIC"}
COMPONENT_PROJECTS = tuple(p for p in PROJECTS if p not in WITHOUT_COMPONENT)

ALLOWED_TYPES = {"fact", "decision-rule", "referent-pin"}
HEADING = re.compile(r"^##\s+([a-z-]+)\s*$", re.MULTILINE)


def body(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    return text.split("## Prompt body", 1)[1] if "## Prompt body" in text else text


def flat(text: str) -> str:
    """Collapse whitespace so assertions survive line wrapping.

    These files are hand-wrapped prose; a phrase can straddle a newline and two
    spaces of indent. Matching raw text would make the tests fail on reflowing
    rather than on meaning.
    """
    return re.sub(r"\s+", " ", text).lower()


class TestGenericPromptIsGeneric(unittest.TestCase):
    def test_exists(self):
        self.assertTrue(GENERIC.exists())

    def test_names_no_project_in_its_body(self):
        """Project names may appear only via the {PROJECT} placeholder."""
        text = body(GENERIC)
        for p in PROJECTS:
            self.assertNotIn(p, text,
                             f"{p} named directly in the generic prompt body")

    def test_mentions_no_project_specific_dataset_facts(self):
        """A dataset identifier in the generic prompt means it is not generic."""
        text = body(GENERIC).lower()
        for token in ("physionet", "fairhub", "dataverse", "b2ai-voice",
                      "cm4ai.org", "healthsheet", "pediatric", "quarterly"):
            self.assertNotIn(token, text,
                             f"generic prompt references {token!r}")

    def test_declares_its_substitution_fields(self):
        text = GENERIC.read_text(encoding="utf-8")
        for field in ("{PROJECT}", "{ARM}", "{METHOD}", "{BUNDLE}",
                      "{LABEL}", "{MANIFEST_LINE}", "{RUNTIME}",
                      "{PROVIDER}", "{MODEL}"):
            self.assertIn(field, text)

    def test_carries_the_uniform_decision_rules(self):
        """The rule that was CHORUS-only must live here, applying to all."""
        text = flat(body(GENERIC))
        self.assertIn("uniform decision rules", text)
        self.assertIn("prefer omission over inference", text)


class TestComponentFiles(unittest.TestCase):
    def test_every_project_has_a_component_file(self):
        missing = [p for p in PROJECTS
                   if not (COMPONENTS / f"{p}.md").exists()]
        self.assertEqual(
            set(missing), WITHOUT_COMPONENT,
            "the set of projects without a component file has changed; a new "
            "gap must be filed like #478, and a filled one removed from "
            "WITHOUT_COMPONENT")

    def test_only_permitted_component_types_are_declared(self):
        for p in COMPONENT_PROJECTS:
            for kind in HEADING.findall((COMPONENTS / f"{p}.md").read_text("utf-8")):
                self.assertIn(kind, ALLOWED_TYPES,
                              f"{p}.md declares disallowed component {kind!r}")

    def test_expectation_components_are_absent(self):
        """The one category with measured harm must not reappear."""
        for p in COMPONENT_PROJECTS:
            text = (COMPONENTS / f"{p}.md").read_text("utf-8")
            self.assertNotIn("## expectation", text,
                             f"{p}.md declares an expectation component")

    def test_no_component_states_an_expected_output(self):
        """Catches expectation language smuggled inside a fact section."""
        banned = ("expected to be", "should be largely", "sparse output",
                  "do not manufacture", "is the correct result",
                  "target slot", "aim for")
        for p in COMPONENT_PROJECTS:
            text = (COMPONENTS / f"{p}.md").read_text("utf-8").lower()
            for phrase in banned:
                self.assertNotIn(phrase, text,
                                 f"{p}.md contains expectation language: {phrase!r}")

    def test_readme_documents_the_excluded_type(self):
        text = (COMPONENTS / "README.md").read_text("utf-8").lower()
        self.assertIn("expectation", text)
        self.assertIn("excluded", text)


class TestTunedPromptIsGenericPlusBlock(unittest.TestCase):
    def test_exists(self):
        self.assertTrue(TUNED.exists())

    def test_does_not_duplicate_the_generic_body(self):
        """It must reference the generic prompt, not copy it.

        A copy is the drift risk this design exists to avoid.
        """
        tuned = TUNED.read_text(encoding="utf-8")
        self.assertIn("d4d_generic_arm_prompt.md", tuned)
        # the generic body's distinctive instruction must NOT be restated here
        self.assertNotIn("ABSOLUTE CONSTRAINT", tuned)

    def test_declares_the_components_substitution(self):
        self.assertIn("{COMPONENTS}", TUNED.read_text(encoding="utf-8"))

    def test_header_distinguishes_the_condition(self):
        text = TUNED.read_text(encoding="utf-8")
        self.assertIn("tuned prompt", text)
        self.assertIn("Prompt components:", text)

    def test_frames_components_as_input_claims_not_output_targets(self):
        text = flat(TUNED.read_text(encoding="utf-8"))
        self.assertIn("nothing about what the output should contain", text)


if __name__ == "__main__":
    unittest.main()

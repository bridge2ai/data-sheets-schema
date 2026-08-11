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
# Widening it immediately found the gap the narrowing had hidden: VOICE_PEDIATRIC
# had no component file, so the `tuned` condition could not be run for it (#478).
# Filled — the set is now empty and every project is guarded. Kept as a named set
# rather than deleted, because the README makes "no legitimate component" a valid
# outcome: such a project would get an *empty block*, which is a different state
# from a missing file and belongs here rather than as a silent absence.
WITHOUT_COMPONENT: set[str] = set()
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


class TestTunedRendersForEveryProject(unittest.TestCase):
    """The tuned condition must be runnable for every project (#478).

    File existence is not the property that matters — reaching the instruction
    is. VOICE_PEDIATRIC had no component, so `--condition tuned` could not be
    rendered for it at all, and nothing said so because the only check declared
    its own project list.
    """

    def _render(self, project):
        from data_sheets_schema.api_runner import RunSpec, resolve_prompt
        bundle = Path(f"data/preprocessed/concatenated/{project}_preprocessed.txt")
        if not bundle.exists():
            self.skipTest(f"{project} bundle not present")
        return resolve_prompt(RunSpec(
            project=project, arm="BASELINE (input documents only)",
            method="claudecode_agent", bundle=bundle, label="L",
            condition="tuned", runtime="Claude API (direct)",
            provider="Anthropic"))

    def test_every_project_renders_under_tuned(self):
        for project in PROJECTS:
            with self.subTest(project=project):
                self.assertTrue(self._render(project).strip())

    def test_the_component_body_reaches_the_instruction(self):
        """Substituted in, not merely present on disk."""
        for project in COMPONENT_PROJECTS:
            with self.subTest(project=project):
                rendered = flat(self._render(project))
                component = flat(body(COMPONENTS / f"{project}.md"))
                probe = next((ln for ln in component.split(".")
                              if len(ln.strip()) > 40), None)
                self.assertIsNotNone(probe, f"{project}.md has no prose to probe")
                self.assertIn(probe.strip()[:60], rendered)

    def test_tuned_is_longer_than_generic_where_a_component_exists(self):
        """A component that renders to nothing would pass every other check."""
        from data_sheets_schema.api_runner import RunSpec, resolve_prompt
        for project in COMPONENT_PROJECTS:
            with self.subTest(project=project):
                bundle = Path(f"data/preprocessed/concatenated/"
                              f"{project}_preprocessed.txt")
                if not bundle.exists():
                    self.skipTest(f"{project} bundle not present")
                generic = resolve_prompt(RunSpec(
                    project=project, arm="BASELINE (input documents only)",
                    method="claudecode_agent", bundle=bundle, label="L",
                    condition="generic", runtime="Claude API (direct)",
                    provider="Anthropic"))
                self.assertGreater(len(self._render(project)), len(generic))


if __name__ == "__main__":
    unittest.main()

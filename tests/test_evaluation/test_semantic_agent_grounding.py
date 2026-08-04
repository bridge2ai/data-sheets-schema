"""The semantic agents must score only what the datasheet contains (#162).

Both agents promise temperature 0.0 and "same file → same score". PR #154 added
a check asking whether a description suits "the claimed dataset type **and
program of origin**" — and there is no `program` or `project` field anywhere in
the D4D schema to read that from. With no field to ground on, an evaluator
infers program from the filename, the invocation context, or prior knowledge,
and the same datasheet scores differently depending on who asks.

The prompts were corrected on 2026-07-22 to name the exact fields the inference
may use. Nothing pins that correction, and it is one careless edit from
returning — so this does.

These tests read the agent definitions rather than running them. That is the
right level here: the defect is a sentence in a prompt, and what must not
regress is the sentence.
"""

import re
import unittest
from pathlib import Path

AGENTS = Path(__file__).resolve().parents[2] / ".claude" / "agents"
SEMANTIC = ("d4d-rubric10-semantic.md", "d4d-rubric20-semantic.md")

#: The only datasheet fields a program inference may rest on. Named here rather
#: than in prose so the test and the prompts cannot drift apart quietly.
GROUNDING_FIELDS = ("keywords", "publisher", "funders")


class TestSemanticAgentsGroundProgramInference(unittest.TestCase):

    def _text(self, name):
        path = AGENTS / name
        self.assertTrue(path.exists(), f"{name} is missing")
        return path.read_text(encoding="utf-8")

    def test_both_agents_exist(self):
        for name in SEMANTIC:
            with self.subTest(agent=name):
                self.assertTrue((AGENTS / name).exists())

    def test_program_inference_is_restricted_to_named_fields(self):
        for name in SEMANTIC:
            with self.subTest(agent=name):
                text = self._text(name)
                if "program" not in text.lower():
                    continue  # dropped entirely — also an acceptable fix
                for field in GROUNDING_FIELDS:
                    self.assertIn(
                        field, text,
                        f"{name} mentions program context but does not name "
                        f"`{field}` as a permitted source")

    def test_the_ungrounded_sources_are_explicitly_forbidden(self):
        """Naming what may be used is not enough on its own.

        A model told "infer from keywords" and left free to consult a filename
        will still consult the filename. The prompt has to rule it out.
        """
        for name in SEMANTIC:
            with self.subTest(agent=name):
                text = self._text(name).lower()
                if "program" not in text:
                    continue
                self.assertIn("never from the filename", text,
                              f"{name} must forbid filename inference")
                for forbidden in ("invocation context", "prior knowledge"):
                    self.assertIn(forbidden, text,
                                  f"{name} must forbid {forbidden}")

    def test_the_original_ungrounded_phrasing_is_gone(self):
        """`dataset type and program of origin` is the exact wording of #162."""
        pattern = re.compile(r"dataset type\s+and\s+program of origin", re.I)
        for name in SEMANTIC:
            with self.subTest(agent=name):
                self.assertIsNone(pattern.search(self._text(name)))

    def test_no_program_or_project_slot_exists_to_ground_on(self):
        """The premise. If the schema ever gains one, this test should fail and
        the prompts can stop working around its absence."""
        schema = (Path(__file__).resolve().parents[2] / "src"
                  / "data_sheets_schema" / "schema" / "D4D_Core.yaml")
        if not schema.exists():
            self.skipTest("D4D_Core.yaml not present")
        text = schema.read_text(encoding="utf-8")
        for slot in ("\n  program:", "\n  project:"):
            self.assertNotIn(
                slot, text,
                "D4D_Core now declares a program/project slot — the semantic "
                "agents can ground on it directly and this workaround should go")


if __name__ == "__main__":
    unittest.main()

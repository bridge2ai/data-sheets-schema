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

class TestThePremise(unittest.TestCase):
    """Both halves of it, from the schema rather than from a file path.

    An earlier version read `D4D_Core.yaml` for the absence of `program`. That
    is the wrong scope — records are evaluated as `Dataset`, which draws from
    the whole schema, and the fields the prompt *may* use are declared
    elsewhere: `publisher` and `keywords` in `D4D_Base_import.yaml`, `funders`
    as an attribute rather than a top-level slot. A `program` slot added to any
    other module would have left it green (#285).
    """

    @classmethod
    def setUpClass(cls):
        from data_sheets_schema import schema_digest
        cls.slots = {s.name for s in schema_digest.build("Dataset").slots}

    def test_no_program_or_project_slot_exists_to_ground_on(self):
        """If the schema gains one, this fails and the workaround can go."""
        for name in ("program", "project", "program_of_origin"):
            with self.subTest(slot=name):
                self.assertNotIn(
                    name, self.slots,
                    f"Dataset now declares `{name}` — the semantic agents can "
                    "ground on it directly and this workaround should go")

    def test_the_fields_the_prompt_may_use_actually_exist(self):
        """The other half, and #162 in miniature.

        A test that stops a prompt grounding on nothing should check that what
        it grounds on is something. `funders` is an attribute, so a naive grep
        for a top-level slot reports it missing when it is not.
        """
        for name in GROUNDING_FIELDS:
            with self.subTest(slot=name):
                self.assertIn(
                    name, self.slots,
                    f"the prompts tell the agent to infer from `{name}`, which "
                    "is not a Dataset slot — the same defect as #162")


if __name__ == "__main__":
    unittest.main()

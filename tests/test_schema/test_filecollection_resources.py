"""`FileCollection.resources` — a slot that could not be populated (#226).

The schema declared `any_of: [File, FileCollection]` alongside a concrete
`range`. LinkML ANDs the two when generating JSON Schema, so the effective
constraint was `range AND (File OR FileCollection)`:

* with the inherited `range: Dataset` it was unsatisfiable for *every* value;
* with `range: File` it admitted a File and rejected the nested FileCollection
  the union existed to allow.

Either way the recursive shape it documented was unreachable, and the corpus
agrees — zero of 658 `file_collections` entries populate `resources`.
"""

import subprocess
import tempfile
import unittest
from pathlib import Path

from linkml_runtime import SchemaView

FULL = "src/data_sheets_schema/schema/data_sheets_schema_all.yaml"


def _validate(record: str) -> subprocess.CompletedProcess:
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "r.yaml"
        p.write_text(record, encoding="utf-8")
        return subprocess.run(
            ["poetry", "run", "linkml-validate", "-s", FULL, "-C", "Dataset",
             str(p)], capture_output=True, text=True, timeout=300)


HEAD = ("id: https://example.org/x\nname: x\ntitle: T\ndescription: d\n"
        "file_collections:\n  - id: https://example.org/fc\n    path: /d/fc\n")


class TestTheSlotCanActuallyBePopulated(unittest.TestCase):
    def test_a_collection_may_list_its_files(self):
        """The point of the fix: this record failed before it."""
        r = _validate(HEAD + "    resources:\n"
                             "      - id: https://example.org/f1\n"
                             "        path: /d/fc/a.csv\n")
        self.assertEqual(r.returncode, 0, (r.stdout + r.stderr)[:400])

    def test_several_files_are_fine(self):
        r = _validate(HEAD + "    resources:\n"
                             "      - id: https://example.org/f1\n"
                             "        path: /d/fc/a.csv\n"
                             "      - id: https://example.org/f2\n"
                             "        path: /d/fc/b.csv\n")
        self.assertEqual(r.returncode, 0, (r.stdout + r.stderr)[:400])

    def test_a_collection_with_no_resources_is_still_fine(self):
        """658 of 658 corpus entries look like this; narrowing the range must
        not make the ordinary case harder."""
        self.assertEqual(_validate(HEAD).returncode, 0)


class TestTheUnsatisfiableUnionIsGone(unittest.TestCase):
    def setUp(self):
        self.slot = SchemaView(FULL).induced_slot("resources", "FileCollection")

    def test_no_any_of_remains(self):
        """`any_of` beside a concrete `range` is ANDed, not ORed — declaring
        both is how the slot became unusable."""
        self.assertFalse(self.slot.any_of,
                         "any_of is back; check it is satisfiable this time")

    def test_the_range_is_file(self):
        self.assertEqual(self.slot.range, "File")

    def test_it_is_a_list(self):
        self.assertTrue(self.slot.multivalued)

    def test_the_description_does_not_promise_nesting(self):
        """It described "nested FileCollection objects" while rejecting them.
        A description that documents an impossible shape is worse than a
        narrower one, because it sends a generator after it."""
        text = (self.slot.description or "").lower()
        self.assertNotIn("nested file collection", text)


class TestTheSchemaStillHasNoAbstractClasses(unittest.TestCase):
    """Expressing the union properly would need an abstract parent over File
    and FileCollection. This schema has no abstract or mixin class among its
    78, so that would be a new idiom introduced for a capability nothing uses.
    Recorded so the choice is visible if someone later adds one."""

    def test_no_abstract_or_mixin_classes(self):
        sv = SchemaView(FULL)
        abstract = [n for n, c in sv.all_classes().items() if c.abstract]
        mixins = [n for n, c in sv.all_classes().items() if c.mixin]
        self.assertEqual(abstract, [])
        self.assertEqual(mixins, [])


if __name__ == "__main__":
    unittest.main()

"""The dataset-relationship vocabulary, and whether a generator can see it.

Twelve of the 23 artifacts that failed validation in the 2026-07-31 sweep did so
on `related_datasets.relationship_type`, filled with DataCite spellings
(`IsNewVersionOf`, `Continues`, `References`) and inventions (`related_to`,
`is a later release in the same series as`).

Two separate causes, and both are covered here:

* the schema modelled only 14 of DataCite's 36 relation types, so `Continues`
  had no home to go to; and
* the schema digest sent with every generation request named
  `relationship_type` as a required key but never showed the vocabulary, so the
  model was choosing from a list it had never been shown.
"""

import subprocess
import tempfile
import unittest
from pathlib import Path

from linkml_runtime import SchemaView

FULL = "src/data_sheets_schema/schema/data_sheets_schema_all.yaml"
CORE = "src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml"
ENUM = "DatasetRelationshipTypeEnum"

# DataCite Metadata Schema 4.x relationType, in full.
DATACITE = {
    "IsCitedBy", "Cites", "IsSupplementTo", "IsSupplementedBy", "IsContinuedBy",
    "Continues", "IsDescribedBy", "Describes", "HasMetadata", "IsMetadataFor",
    "HasVersion", "IsVersionOf", "IsNewVersionOf", "IsPreviousVersionOf",
    "IsPartOf", "HasPart", "IsPublishedIn", "IsReferencedBy", "References",
    "IsDocumentedBy", "Documents", "IsCompiledBy", "Compiles",
    "IsVariantFormOf", "IsOriginalFormOf", "IsIdenticalTo", "IsReviewedBy",
    "Reviews", "IsDerivedFrom", "IsSourceOf", "IsRequiredBy", "Requires",
    "IsObsoletedBy", "Obsoletes", "IsCollectedBy", "Collects",
}


class TestDataCiteAlignment(unittest.TestCase):
    def setUp(self):
        self.pvs = SchemaView(FULL).get_enum(ENUM).permissible_values

    def test_every_datacite_relation_type_is_represented(self):
        covered = {a for pv in self.pvs.values() for a in (pv.aliases or [])}
        self.assertEqual(DATACITE - covered, set(),
                         "DataCite relation types with nowhere to go")

    def test_no_alias_is_invented(self):
        """An alias that is not a DataCite term claims an alignment that does
        not exist."""
        aliases = {a for pv in self.pvs.values() for a in (pv.aliases or [])}
        self.assertEqual(aliases - DATACITE, set())

    def test_each_datacite_term_maps_to_exactly_one_value(self):
        for term in DATACITE:
            hits = [k for k, v in self.pvs.items() if term in (v.aliases or [])]
            with self.subTest(term=term):
                self.assertEqual(len(hits), 1, f"{term} -> {hits}")

    def test_every_value_carries_its_datacite_term(self):
        missing = [k for k, v in self.pvs.items() if not v.aliases]
        self.assertEqual(missing, [], "values with no DataCite alignment")

    def test_names_stay_snake_case(self):
        """The alias records the DataCite spelling; it is not a second way to
        write the value."""
        for name in self.pvs:
            with self.subTest(name=name):
                self.assertEqual(name, name.lower())
                self.assertNotIn(" ", name)

    def test_the_core_schema_agrees(self):
        core = SchemaView(CORE).get_enum(ENUM)
        self.assertIsNotNone(core, "core schema lost the enum")
        self.assertEqual(set(core.permissible_values), set(self.pvs),
                         "full and core schemas disagree on the vocabulary")


class TestTheValuesThatFailedNowValidate(unittest.TestCase):
    """The three DataCite spellings seen in real output, by their schema name."""

    def _validate(self, value: str) -> bool:
        record = (
            "id: https://example.org/x\nname: x\ntitle: T\ndescription: d\n"
            "related_datasets:\n  - target_dataset: https://example.org/y\n"
            f"    relationship_type: {value}\n")
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "r.yaml"
            p.write_text(record, encoding="utf-8")
            r = subprocess.run(
                ["poetry", "run", "linkml-validate", "-s", FULL,
                 "-C", "Dataset", str(p)],
                capture_output=True, text=True, timeout=300)
            return r.returncode == 0

    def test_the_previously_failing_relations_validate(self):
        for value in ("is_new_version_of", "continues", "references"):
            with self.subTest(value=value):
                self.assertTrue(self._validate(value))

    def test_newly_added_relations_validate(self):
        for value in ("cites", "is_published_in", "is_source_of", "collects"):
            with self.subTest(value=value):
                self.assertTrue(self._validate(value))

    def test_the_datacite_spelling_is_still_rejected(self):
        """Canonical is snake_case. Accepting both would give one concept two
        spellings and make records disagree with each other."""
        self.assertFalse(self._validate("IsNewVersionOf"))

    def test_an_invented_relation_is_still_rejected(self):
        self.assertFalse(self._validate("related_to"))


class TestTheDigestShowsNestedVocabularies(unittest.TestCase):
    """A model cannot choose from a list it has never been shown."""

    def setUp(self):
        from data_sheets_schema import schema_digest
        schema_digest._BUILD_CACHE.clear()
        self.sd = schema_digest

    def test_a_nested_enum_slot_lists_its_values(self):
        text = self.sd.digest_text("Dataset")
        self.assertIn("`relationship_type` accepts only:", text)
        for value in ("is_new_version_of", "continues", "references"):
            with self.subTest(value=value):
                self.assertIn(f"`{value}`", text)

    def test_this_was_the_gap(self):
        """Naming the required key was never enough on its own."""
        digest = self.sd.build("Dataset")
        nested = {n.name: n for n in digest.nested}
        rel = nested.get("DatasetRelationship")
        self.assertIsNotNone(rel)
        self.assertIn("relationship_type", rel.required)
        self.assertIn("relationship_type", rel.enums)

    def test_it_covers_more_than_one_slot(self):
        """13 nested enum slots, not a special case for one."""
        digest = self.sd.build("Dataset")
        with_enums = [n for n in digest.nested if n.enums]
        self.assertGreater(len(with_enums), 5)

    def test_the_core_digest_gets_them_too(self):
        digest = self.sd.build("CoreDataset")
        self.assertTrue(any(n.enums for n in digest.nested))

    def test_long_vocabularies_are_truncated_and_say_so(self):
        """A digest that silently drops values is worse than one that admits
        it: the model would treat the short list as complete."""
        from data_sheets_schema.schema_digest import MAX_ENUM_VALUES
        digest = self.sd.build("Dataset")
        for n in digest.nested:
            for slot, values in n.enums.items():
                with self.subTest(cls=n.name, slot=slot):
                    self.assertLessEqual(len(values), MAX_ENUM_VALUES)
                    if n.enums_truncated.get(slot):
                        self.assertIn(f"+{n.enums_truncated[slot]} more",
                                      self.sd.digest_text("Dataset"))


if __name__ == "__main__":
    unittest.main()

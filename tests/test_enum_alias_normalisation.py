"""Records may name an enum value the way the schema says it may (#292).

`linkml-validate` matches permissible values on `text` alone. The relationship
enum aligned with DataCite (#223) declares DataCite's own CamelCase spellings as
`aliases` — `IsNewVersionOf`, `HasPart`, `References` — and those are exactly
what generation emits, because they are what the vocabulary is called
everywhere else. So the schema declared a name valid and validation rejected it.

Measured across the 24 generic and generic-v2 records, 14 enum values fell
outside their vocabulary:

    IsNewVersionOf                              x6   declared alias
    is a later release in the same series as    x4   prose, no equivalent
    HasPart                                     x2   declared alias
    related_to                                  x1   no equivalent
    References                                  x1   casing only

Case-insensitive matching alone would have fixed **one** of the fourteen.
Honouring the declared aliases fixes **nine**. The remaining five are real
generation failures and are deliberately left to fail.
"""

import unittest

from data_sheets_schema.api_runner import _enum_aliases, normalise_enum_aliases


class TestAliasTable(unittest.TestCase):

    def test_datacite_spellings_are_declared_aliases(self):
        aliases = _enum_aliases()
        for camel, snake in (("IsNewVersionOf", "is_new_version_of"),
                             ("HasPart", "has_part"),
                             ("References", "references")):
            with self.subTest(alias=camel):
                self.assertEqual(aliases.get(camel), snake)

    def test_it_is_read_from_the_schema_not_hardcoded(self):
        """A second copy of the vocabulary is one to keep in step."""
        self.assertGreater(len(_enum_aliases()), 100)

    def test_a_permissible_value_maps_to_itself(self):
        self.assertEqual(_enum_aliases().get("references"), "references")


class TestNormalisation(unittest.TestCase):

    def test_a_declared_alias_is_rewritten(self):
        out = normalise_enum_aliases("    relationship_type: IsNewVersionOf")
        self.assertEqual(out, "    relationship_type: is_new_version_of")

    def test_a_casing_difference_is_rewritten(self):
        out = normalise_enum_aliases("  - relationship_type: References")
        self.assertEqual(out, "  - relationship_type: references")

    def test_an_already_valid_value_is_untouched(self):
        line = "    relationship_type: is_new_version_of"
        self.assertEqual(normalise_enum_aliases(line), line)

    def test_prose_is_left_to_fail(self):
        """`is a later release in the same series as` is a generation failure.

        Normalising it into something valid would hide the failure, which is
        the opposite of what this is for — four of the fourteen bad values are
        this shape and they should stay visible.
        """
        line = "    relationship_type: is a later release in the same series as"
        self.assertEqual(normalise_enum_aliases(line), line)

    def test_a_value_with_no_equivalent_is_left_to_fail(self):
        line = "    relationship_type: related_to"
        self.assertEqual(normalise_enum_aliases(line), line)

    def test_the_provenance_header_survives(self):
        """Text-level for the same reason as `normalise_temporal`: re-dumping
        the YAML would drop the `#` block the reader sees first."""
        doc = ("# Generated: 2026-08-04\n"
               "# Model: claude-opus-5\n"
               "related_datasets:\n"
               "  - relationship_type: HasPart\n")
        out = normalise_enum_aliases(doc)
        self.assertTrue(out.startswith("# Generated: 2026-08-04\n# Model:"))
        self.assertIn("relationship_type: has_part", out)

    def test_only_the_value_position_is_rewritten(self):
        """A key that happens to share an alias's spelling is not a value."""
        line = "    HasPart: something"
        self.assertEqual(normalise_enum_aliases(line), line)

    def test_quoted_and_flow_values_are_left_alone(self):
        for line in ("    relationship_type: 'HasPart'",
                     "    relationship_type: [HasPart]",
                     "    relationship_type: {a: HasPart}"):
            with self.subTest(line=line):
                self.assertEqual(normalise_enum_aliases(line), line)


if __name__ == "__main__":
    unittest.main()

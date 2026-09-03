"""The fitness judge is told the ranges of nested attributes (#486).

`FORM_SUBTYPE_SYSTEM` asks the judge to separate two defects. `hollow_object`
— content in prose while structured keys sit empty — is judgeable from names
alone. The other is not:

    other — a bare string where a list of objects is declared, **a wrong
    range**, a scalar where a structure belongs.

`slot_spec` rendered nested attributes as names only, so below the top level
"a wrong range" could not be assessed at all. The form axis was measuring
hollowness reliably and range conformance only at the top level — a narrower
claim than "form failures", and one the v1-vs-v3 comparison rests on.

**This is a deliberate re-measurement, not a bug fix.** The judge now answers a
better-informed question, so cached labels from before it are not comparable and
must not be reused. The last class here is what makes that safe.
"""

import unittest

from data_sheets_schema import schema_digest
from data_sheets_schema.evidence_score import slot_spec


class TestTheDigestCarriesNestedRanges(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.digest = schema_digest.build("Dataset")
        cls.by_name = {n.name: n for n in cls.digest.nested}

    def test_nested_classes_record_their_attribute_ranges(self):
        nested = self.by_name.get("VariableMetadata")
        self.assertIsNotNone(nested, "VariableMetadata not a nested range")
        self.assertEqual(nested.ranges.get("minimum_value"), "float")
        self.assertEqual(nested.ranges.get("is_sensitive"), "boolean")

    def test_multivalued_ranges_are_marked(self):
        """`Person` and `Person[]` are different obligations, and a judge told
        the first about the second cannot assess cardinality."""
        nested = self.by_name.get("DataGovernance")
        if nested is None:
            self.skipTest("DataGovernance not a nested range")
        self.assertEqual(nested.ranges.get("committee_members"), "Person[]")
        self.assertEqual(nested.ranges.get("committee_contact"), "Person")

    def test_uriorcurie_attributes_are_covered(self):
        """The case that motivated this. A bare token in a nested `id`
        validates exactly as cleanly as a ROR IRI (#402/#457), and the judge
        could not see the declaration that makes it wrong."""
        with_uri = [n for n in self.digest.nested
                    if any(v.startswith("uriorcurie") for v in n.ranges.values())]
        self.assertGreater(len(with_uri), 10)


class TestTheJudgeSeesThem(unittest.TestCase):
    """`slot_spec` is what reaches the judge; the digest alone would not."""

    def test_slot_spec_names_the_nested_ranges(self):
        spec = slot_spec("variables")
        self.assertIn("attribute ranges", spec)
        self.assertIn("minimum_value → float", spec)

    def test_the_universal_ranges_are_stated_once(self):
        """`id` is `uriorcurie` on all 67 nested classes, so a per-class line
        is bloat an existing guard already forbids. Stated once instead —
        same information, and the #402/#457 signal still reaches the judge."""
        spec = slot_spec("variables")
        self.assertIn("uriorcurie", spec)
        self.assertNotIn("id → uriorcurie", spec)

    def test_it_says_a_wrong_range_is_a_form_failure(self):
        """Naming the range without saying what to do with it leaves the judge
        to infer the rule, which is what produced the gap."""
        self.assertIn("wrong kind for its declared range", slot_spec("variables"))

    def test_string_ranges_are_omitted(self):
        """`string` is the schema default: naming it costs prompt length and
        tells a reader nothing. `unit` is `string` since #456, so it must not
        appear even though it is the attribute the issue was filed about."""
        spec = slot_spec("variables")
        self.assertNotIn("→ string", spec)
        self.assertNotIn("unit →", spec)

    def test_a_slot_with_no_class_range_is_unaffected(self):
        spec = slot_spec("title")
        self.assertNotIn("attribute ranges", spec)


class TestCachedJudgementsCannotSurviveThis(unittest.TestCase):
    """The property that makes the re-measurement safe.

    The fitness cache keys on the schema digest fingerprint. Had `slot_spec`
    changed without the digest render changing, the key would have held while
    the question moved, and every cached label would have answered a
    worse-informed question with nothing to say so — the #465 failure exactly.
    """

    def test_nested_ranges_reach_the_rendered_digest(self):
        """So the fingerprint moves when they do."""
        text = schema_digest.digest_text("Dataset")
        self.assertIn("- ranges:", text)

    def test_the_fingerprint_responds_to_the_nested_ranges(self):
        """Render the same digest with the ranges stripped and confirm the
        fingerprint differs. If it did not, the cache key would be blind to
        exactly the information the judge gained."""
        # No longer deep-copied: `build` returns a copy since #528, so
        # stripping ranges here cannot reach the cache. Left mutating in place
        # deliberately — if that isolation ever regresses, the two tests below
        # fail, which is how this one was found in the first place.
        digest = schema_digest.build("Dataset")
        before = schema_digest.fingerprint(schema_digest.render(digest))
        for nested in digest.nested:
            nested.ranges = {}
        after = schema_digest.fingerprint(schema_digest.render(digest))
        self.assertNotEqual(before, after)

    def test_the_judge_and_the_key_show_the_same_set(self):
        """The guarantee the test above only appears to give.

        Stripping *every* range moves the fingerprint whatever the filters are,
        so that test passes even when the two disagree — and they did. The
        first version of this change showed `id`, `data_type` and
        `used_software` in `slot_spec` and omitted them from the digest as
        universal attributes, so a change to any of those three would have
        moved the judge's question while the cache key held.

        Asserted as set equality per nested class, which is the property that
        actually prevents it.
        """
        digest = schema_digest.build("Dataset")
        top_level = {s.name: s for s in digest.slots}
        checked = 0
        for nested in digest.nested:
            expected = set(schema_digest.shown_ranges(nested))
            if not expected:
                continue
            slot = next((n for n, s in top_level.items()
                         if s.range == nested.name), None)
            if slot is None:
                continue
            spec = slot_spec(slot)
            for attribute in expected:
                with self.subTest(nested=nested.name, attribute=attribute):
                    self.assertIn(f"{attribute} \u2192", spec)
            checked += 1
        self.assertGreater(checked, 20, "too few nested classes exercised")

    def test_the_universal_ranges_reach_both_renderings(self):
        """Stated once each, from one constant, so they cannot drift apart."""
        self.assertIn(schema_digest.UNIVERSAL_RANGES,
                      schema_digest.digest_text("Dataset"))
        self.assertIn(schema_digest.UNIVERSAL_RANGES, slot_spec("variables"))

    def test_universal_attributes_are_not_repeated_per_class(self):
        """The existing guard this change first violated: repeating `id` on 67
        classes pushed the digest past its 40k budget for no new information."""
        digest = schema_digest.build("Dataset")
        for nested in digest.nested:
            with self.subTest(nested=nested.name):
                self.assertNotIn("id", schema_digest.shown_ranges(nested))


class DepthTwo(unittest.TestCase):
    """#900 / v8 plan A: the classes a first-level attribute ranges over are
    rendered too — a run told `principal_investigator: Person` must also be
    told what a Person carries — but not through the universal attributes,
    and not deeper."""

    def test_person_and_grant_are_rendered_with_their_keys(self):
        digest = schema_digest.build("Dataset")
        names = {n.name for n in digest.nested}
        self.assertIn("Person", names); self.assertIn("Grant", names); self.assertIn("Organization", names)
        person = next(n for n in digest.nested if n.name == "Person")
        self.assertIn("orcid", person.optional); self.assertIn("email", person.optional)
        grant = next(n for n in digest.nested if n.name == "Grant")
        self.assertIn("grant_number", grant.optional)
        text = schema_digest.digest_text("Dataset")
        self.assertIn("**Person**", text); self.assertIn("**Grant**", text)

    def test_software_is_reached_only_through_a_universal_attribute_and_stays_out(self):
        digest = schema_digest.build("Dataset")
        self.assertNotIn("Software", {n.name for n in digest.nested})

    def test_the_second_level_stays_within_budget(self):
        self.assertLess(len(schema_digest.digest_text("Dataset")), 44_000)
        self.assertEqual(schema_digest.NESTING_DEPTH, 2)

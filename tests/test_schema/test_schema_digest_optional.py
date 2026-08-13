"""The digest must name the nested keys a record may use, not only the required ones (#325).

`NestedClass` has carried an `optional` list since the first version. `build()`
populated it. `render()` never emitted it. So the digest told a run which nested
keys were *mandatory* and never which were *available*: 54 of 66 nested classes
rendered as a bare `required: none`, and 367 attributes were named nowhere in
the text the model receives.

The measurement that made this concrete. Across the 25 current records, not one
populates `regulatory_restrictions.confidentiality_level`, `.hipaa_compliant`,
`.other_compliance` or `.governance_committee_contact` — all four real slots.
Every record instead writes prose into that object's `description`, and the
prose *contains the answers*: "FDA Regulated: No", "De-identified Samples: Yes",
a license clause about data security and privacy standards. The model had the
facts and no structured place it had been told about.

Downstream, rubric20's Q9 asks for confidentiality classification and a
governance contact at band 5, so it scores exactly 3/5 on every record —
constant, and not because the datasheets are uniform.

Two of the four were already visible, because enum-ranged nested slots have
always been rendered with their vocabularies. That is why this file asserts the
*listing*, not the outcome: making a field addressable is what the digest can
do. Whether a run then fills it is a question for the next generation, and one
these tests deliberately do not pretend to answer.
"""

import unittest

from data_sheets_schema import schema_digest
from data_sheets_schema.schema_digest import (CLASS_SCHEMA, MAX_OPTIONAL_SHOWN,
                                              MIRRORS_TOP_LEVEL,
                                              UNIVERSAL_ATTRIBUTES,
                                              ClassDigest, NestedClass)

#: Both targets, not just `Dataset` (#331). `CoreDataset` lives in its own
#: merged artifact, is the `*_core` arm of every run, and takes a *different
#: branch*: its top-level listing is smaller, so one nested class mirrors it
#: against three for `Dataset`.
TARGETS = sorted(CLASS_SCHEMA)


def _rendered(target):
    digest = schema_digest.build(target)
    return digest, schema_digest.render(digest)


def _block(text, name):
    """A class's rendered line plus its indented continuations."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.startswith(f"- **{name}** — required:"):
            out = [line]
            for follow in lines[i + 1:]:
                if not follow.startswith("    "):
                    break
                out.append(follow)
            return "\n".join(out)
    return ""


class TestOptionalAttributesAreRendered(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.digest = schema_digest.build("Dataset")
        cls.text = schema_digest.render(cls.digest)
        cls.nested = {n.name: n for n in cls.digest.nested}

    def test_the_premise_the_class_has_no_required_attributes(self):
        """If it ever gains one, `required: none` stops being the whole story
        and this file's motivating example needs rewriting rather than passing
        by accident."""
        self.assertEqual(self.nested["ExportControlRegulatoryRestrictions"].required,
                         [])

    def test_the_governance_fields_are_named(self):
        """The four that no record populates. Two were visible via their enums;
        `other_compliance` and `governance_committee_contact` were not named
        anywhere at all."""
        for attribute in ("confidentiality_level", "hipaa_compliant",
                          "other_compliance", "governance_committee_contact"):
            with self.subTest(attribute=attribute):
                self.assertIn(f"`{attribute}`", self.text)

    def test_no_class_is_rendered_with_nothing_but_required_none(self):
        """54 of 66 were. A class described only by what it does not require
        tells a run nothing it can act on. Both targets (#331)."""
        for target in TARGETS:
            digest, text = _rendered(target)
            blind = [n.name for n in digest.nested
                     if not n.required and not n.enums
                     and [k for k in n.optional if k not in UNIVERSAL_ATTRIBUTES]
                     and _block(text, n.name) == f"- **{n.name}** — required: none"]
            with self.subTest(target=target):
                self.assertEqual(blind, [])

    def test_the_governance_fields_are_named_for_both_targets(self):
        """The `*_core` arm scores the same Q9 (#331)."""
        for target in TARGETS:
            text = schema_digest.digest_text(target)
            for attribute in ("confidentiality_level", "hipaa_compliant",
                              "other_compliance", "governance_committee_contact"):
                with self.subTest(target=target, attribute=attribute):
                    self.assertIn(f"`{attribute}`", text)

    def _block(self, name):
        """The rendered line for a class plus its indented continuations."""
        lines = self.text.splitlines()
        for i, line in enumerate(lines):
            if line.startswith(f"- **{name}** — required:"):
                out = [line[2:] + "\n"]
                for follow in lines[i + 1:]:
                    if not follow.startswith("    "):
                        break
                    out.append(follow + "\n")
                return "".join(out)
        return ""

    def test_universal_attributes_are_not_repeated_on_every_class(self):
        """`id`, `name`, `description` and `used_software` are on all 66. Naming
        them each time is tokens spent saying nothing — and `description` is the
        slot runs already over-use, which is the problem, not the fix."""
        for target in TARGETS:
            _, text = _rendered(target)
            for name in ("ExportControlRegulatoryRestrictions", "ParticipantPrivacy"):
                block = _block(text, name)
                if not block:
                    continue
                for attribute in sorted(UNIVERSAL_ATTRIBUTES):
                    with self.subTest(target=target, nested=name, attribute=attribute):
                        self.assertNotIn(f"`{attribute}`", block)


class TestTheByReferenceShortcut(unittest.TestCase):
    """Three classes mostly repeat the top-level slot listing.

    Enumerating 24 alphabetically-first names for them would be redundant and
    arbitrary, so they are described by reference. The risk of that shortcut is
    swallowing the attributes that make the class *different* — which is the
    only reason to read its entry.
    """

    @classmethod
    def setUpClass(cls):
        cls.digest = schema_digest.build("Dataset")
        cls.text = schema_digest.render(cls.digest)
        cls.top_level = {s.name for s in cls.digest.slots}
        cls.nested = {n.name: n for n in cls.digest.nested}

    def _own(self, name):
        return [k for k in self.nested[name].optional
                if k not in self.top_level and k not in UNIVERSAL_ATTRIBUTES]

    def test_a_mirroring_class_is_described_by_reference(self):
        self.assertIn("also accepts the same slots as the top-level listing above",
                      self.text)

    def test_the_distinguishing_attributes_survive_the_shortcut(self):
        """`DataSubset` is 98% the top-level listing; the 2% is the whole point
        of it being a separate class."""
        for name in ("DataSubset", "FileCollection"):
            own = self._own(name)
            with self.subTest(nested=name):
                self.assertTrue(own, f"{name} has no distinguishing attributes")
                for attribute in own:
                    self.assertIn(f"`{attribute}`", self._block(name),
                                  f"{name}.{attribute} is named nowhere")

    def test_data_subset_keeps_its_two_discriminators(self):
        """Named explicitly because rubric20 Q5 and Q19 score them."""
        block = self._block("DataSubset")
        self.assertIn("`is_data_split`", block)
        self.assertIn("`is_subpopulation`", block)

    def test_only_classes_that_really_mirror_take_the_shortcut(self):
        """Both targets: `CoreDataset` has a smaller top-level listing, so one
        class mirrors it against three for `Dataset` (#331)."""
        for target in TARGETS:
            digest, text = _rendered(target)
            top_level = {s.name for s in digest.slots}
            for n in digest.nested:
                optional = [k for k in n.optional if k not in UNIVERSAL_ATTRIBUTES]
                if not optional:
                    continue
                own = [k for k in optional if k not in top_level]
                overlap = 1 - len(own) / len(optional)
                shortcut = "also accepts the same slots" in _block(text, n.name)
                with self.subTest(target=target, nested=n.name,
                                  overlap=round(overlap, 2)):
                    self.assertEqual(shortcut, overlap >= MIRRORS_TOP_LEVEL)

    def test_no_distinguishing_attribute_is_lost_on_either_target(self):
        """The by-reference shortcut's whole risk, checked everywhere it runs."""
        for target in TARGETS:
            digest, text = _rendered(target)
            top_level = {s.name for s in digest.slots}
            for n in digest.nested:
                block = _block(text, n.name)
                if "also accepts the same slots" not in block:
                    continue
                own = [k for k in n.optional
                       if k not in top_level and k not in UNIVERSAL_ATTRIBUTES]
                for attribute in own:
                    with self.subTest(target=target, nested=n.name,
                                      attribute=attribute):
                        self.assertIn(f"`{attribute}`", block)

    def _block(self, name):
        lines = self.text.splitlines()
        for i, line in enumerate(lines):
            if line.startswith(f"- **{name}** — required:"):
                out = [line]
                for follow in lines[i + 1:]:
                    if not follow.startswith("    "):
                        break
                    out.append(follow)
                return "\n".join(out)
        return ""


class TestTheDigestStaysCompact(unittest.TestCase):
    """The digest exists because the merged schema is 254 KB and most of it says
    nothing about how to fill a record. Naming 367 more attributes has to stay
    worth its tokens."""

    def test_each_digest_is_far_smaller_than_the_schema_it_replaces(self):
        for target in TARGETS:
            with self.subTest(target=target):
                text = schema_digest.digest_text(target)
                merged = CLASS_SCHEMA[target].read_text()
                self.assertLess(len(text), len(merged) / 5)

    def test_the_listing_did_not_double_the_digest(self):
        """It grew ~20%. A regression that enumerated the mirroring classes in
        full would roughly double it, and this is the cheapest way to notice.

        Ceiling raised 40k -> 44k on 2026-08-13, deliberately. #538 renders the
        B2AI_SUBSTRATE (81 terms) and B2AI_TOPIC (56) vocabularies that
        `data_topic` and `data_substrate` have always declared and no run had
        ever been shown — 2,550 characters, 6.8%. The guard exists to catch a
        regression that *doubles* the digest, which this is not, and the cost
        buys the thing whose absence let 23 of 34 `data_substrate` values name
        cell lines and assay techniques instead of data types.

        The prefix is stated once and terms listed `id=name`, which halves what
        repeating `B2AI_SUBSTRATE:` 81 times would have cost.
        """
        for target in TARGETS:
            with self.subTest(target=target):
                self.assertLess(len(schema_digest.digest_text(target)), 44_000)


class TestTheTruncationSafeguard(unittest.TestCase):
    """The cap has never run against a real schema (#330).

    Both targets' large nested classes mirror the top-level listing and take
    that branch instead, so `MAX_OPTIONAL_SHOWN`, the slice and the `(+N more)`
    tail were dead code — a safeguard that reads as verified and is not. If the
    schema later gains a large class that does *not* mirror, the first run of
    that branch would be in a paid generation run.

    Exercised here against a synthetic digest, which is the only way to reach
    it without waiting for the schema to grow one.
    """

    def _render(self, count):
        nested = NestedClass(
            name="Sprawling", required=[],
            optional=sorted(f"attribute_{i:03d}" for i in range(count)))
        return schema_digest.render(
            ClassDigest(class_name="Dataset",
                        schema_path=schema_digest.FULL_SCHEMA,
                        slots=[], nested=[nested]))

    def test_a_large_non_mirroring_class_is_truncated(self):
        text = self._render(MAX_OPTIONAL_SHOWN + 9)
        self.assertIn("(+9 more)", text)
        self.assertIn("`attribute_000`", text)
        self.assertNotIn(f"`attribute_{MAX_OPTIONAL_SHOWN:03d}`", text)

    def test_it_does_not_take_the_by_reference_path(self):
        """With no top-level slots to overlap, nothing mirrors — which is what
        makes this the branch the real schema never reaches."""
        self.assertNotIn("also accepts the same slots",
                         self._render(MAX_OPTIONAL_SHOWN + 9))

    def test_a_class_at_the_cap_is_not_truncated(self):
        text = self._render(MAX_OPTIONAL_SHOWN)
        self.assertNotIn("more)", text)
        self.assertIn(f"`attribute_{MAX_OPTIONAL_SHOWN - 1:03d}`", text)


if __name__ == "__main__":
    unittest.main()

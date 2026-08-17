"""Which source wins when two of them state different things.

The uniform rules have always said to represent a disagreement rather than
select a side. A v4 CHORUS record followed that and named what was missing:

    No instance count is asserted because the two sources give different
    figures (over 45,000 and 50,000) for the same released dataset and the
    bundle offers no basis for preferring one.

The rule was right. `source_priority` supplies the basis, declared in the
manifest rather than a prompt for the reason #422 records — a constraint in the
launch text is per-run adaptation nothing inherits and no test can see.
"""

import unittest

from data_sheets_schema.source_priority import (
    UNRANKED,
    decide,
    priority_of,
    ranked,
    tiers,
    unranked_types,
)

MANIFEST = {
    "source_priority": {1: ["RO-Crate"], 2: ["documentation"], 4: ["tutorial"]},
    "projects": {
        "P": [
            {"id": "crate", "source_type": "RO-Crate"},
            {"id": "site", "source_type": "documentation"},
            {"id": "deck", "source_type": "tutorial"},
            {"id": "odd", "source_type": "something new"},
            {"id": "boosted", "source_type": "tutorial", "priority": 1},
        ],
    },
}


class TierTest(unittest.TestCase):

    def test_the_table_flattens_to_type_then_tier(self):
        self.assertEqual(tiers(MANIFEST),
                         {"RO-Crate": 1, "documentation": 2, "tutorial": 4})

    def test_an_explicit_priority_beats_the_type(self):
        """An override is a line someone deliberately wrote."""
        tier, why = priority_of({"source_type": "tutorial", "priority": 1},
                                tiers(MANIFEST))
        self.assertEqual(tier, 1)
        self.assertIn("declared on the source", why)

    def test_an_unranked_type_sorts_below_everything(self):
        """It cannot win by accident — but it stays distinguishable from
        tier 5, which somebody chose."""
        tier, why = priority_of({"source_type": "something new"},
                                tiers(MANIFEST))
        self.assertEqual(tier, UNRANKED)
        self.assertIn("no tier", why)

    def test_a_source_with_no_type_says_so(self):
        tier, why = priority_of({}, tiers(MANIFEST))
        self.assertEqual(tier, UNRANKED)
        self.assertIn("declares no source_type", why)


class DecideTest(unittest.TestCase):

    def test_the_stronger_source_wins(self):
        d = decide("P", ["site", "deck"], MANIFEST)
        self.assertEqual(d["winner"], "site")

    def test_an_equal_tier_does_not_decide(self):
        """Priority resolves a disagreement; it does not manufacture a winner
        where it has nothing to say. The record represents the disagreement, as
        it did before this existed."""
        d = decide("P", ["crate", "boosted"], MANIFEST)
        self.assertIsNone(d["winner"])
        self.assertIn("share the strongest tier", d["reason"])

    def test_an_undeclared_source_is_named_not_ignored(self):
        d = decide("P", ["site", "ghost"], MANIFEST)
        self.assertEqual(d["winner"], "site")
        self.assertEqual(d["unknown"], ["ghost"])

    def test_no_declared_source_yields_no_winner(self):
        d = decide("P", ["ghost"], MANIFEST)
        self.assertIsNone(d["winner"])

    def test_ranked_is_strongest_first_and_stable(self):
        order = [s["id"] for s in ranked("P", MANIFEST)]
        self.assertEqual(order[0], "crate")
        self.assertEqual(order[-1], "odd")
        # `boosted` overrides to tier 1 and ties with `crate`; manifest order
        # breaks the tie so the listing is reproducible.
        self.assertLess(order.index("crate"), order.index("boosted"))


class RealManifestTest(unittest.TestCase):
    """Against the manifest actually shipped."""

    def test_every_source_type_in_use_is_ranked(self):
        """An unranked source cannot win a disagreement, which is safe — but it
        also cannot lose on the record."""
        self.assertEqual(unranked_types(), {})

    def test_the_chorus_disagreement_now_resolves(self):
        """The case Harry raised: chorus4ai.org says 50,000 released admissions,
        a September 2025 webinar says over 45,000 as of August 2025."""
        d = decide("CHORUS", ["project_documentation", "cohort_2_webinar"])
        self.assertEqual(d["winner"], "project_documentation")
        self.assertIn("tier 2", d["reason"])

    def test_documentation_outranks_a_tutorial(self):
        table = tiers()
        self.assertLess(table["documentation"], table["tutorial"])

    def test_a_release_describing_itself_outranks_the_literature(self):
        """Tier is proximity to the release, not trust: peer-reviewed work is
        authoritative on method and routinely behind the current release on
        counts."""
        table = tiers()
        self.assertLess(table["RO-Crate"], table["publication"])
        self.assertLess(table["documentation"], table["publication"])

    def test_historical_material_ranks_last(self):
        table = tiers()
        self.assertGreater(table["historical documentation"],
                           table["documentation"])


if __name__ == "__main__":
    unittest.main()

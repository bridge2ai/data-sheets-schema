"""A URI without `://` is still a URI (#530).

The classifier tested for `://` and called everything else a CURIE. Schemes
with no authority component — `urn:`, `ark:`, `doi:` — have no `//`, so 1,067
corpus values were filed as "CURIE on an undeclared prefix" and counted toward
the unresolvable headline #457 sizes its migration against.

They are not CURIEs. `urn` is a scheme, not a namespace the schema could bind
to a base IRI, so "declare the prefix" — the cheap remedy #457's step 2 looks
for — does not apply and would produce a meaningless expansion.

Nor are they resolvable. `urn:cm4ai:org:ucsd` is a well-formed URN on an
unregistered NID. Hence a third category rather than a move into `uri`.
"""

import unittest

from data_sheets_schema.identifiers import (BARE, CURIE_DECLARED,
                                            CURIE_UNDECLARED,
                                            NO_AUTHORITY_SCHEMES, URI,
                                            URI_UNVERIFIED, classify)

PREFIXES = {"d4d", "schema", "ror"}


class TestSchemesAreNotCuries(unittest.TestCase):
    def test_the_three_the_corpus_actually_uses(self):
        for value in ("urn:cm4ai:org:ucsd",
                      "ark:59853/b2ai-voice-dataset-feature-ppgs",
                      "doi:10.18130/V3/HIGT4C"):
            with self.subTest(value=value):
                self.assertEqual(classify(value, PREFIXES), URI_UNVERIFIED)

    def test_every_declared_scheme_classifies(self):
        for scheme in NO_AUTHORITY_SCHEMES:
            with self.subTest(scheme=scheme):
                self.assertEqual(classify(f"{scheme}:something", PREFIXES),
                                 URI_UNVERIFIED)

    def test_a_declared_prefix_wins_over_a_scheme_of_the_same_name(self):
        """Reversed on 2026-08-14, deliberately.

        This asserted the opposite — that a scheme name beat a declared prefix,
        so ordering could not flip a value's classification. That was right
        while nothing bound `doi` to a namespace: the reading had to be stable
        and "well-formed scheme, resolution not established" was all that could
        honestly be said.

        The CURIE rule then declared `doi: https://doi.org/`. Now the CURIE
        reading expands to a resolvable IRI, which is strictly more informative
        than the scheme reading, so a declared prefix takes precedence.

        `urn` and `ark` are unaffected and still fall through — they are
        schemes this schema does not and should not bind to a namespace.
        """
        self.assertEqual(classify("doi:10.1/x", PREFIXES | {"doi"}),
                         CURIE_DECLARED)
        self.assertEqual(classify("doi:10.1/x", PREFIXES), URI_UNVERIFIED)
        self.assertEqual(classify("urn:x:y", PREFIXES), URI_UNVERIFIED)

    def test_case_is_not_significant_in_a_scheme(self):
        """RFC 3986 says schemes are case-insensitive."""
        self.assertEqual(classify("URN:x:y", PREFIXES), URI_UNVERIFIED)


class TestItIsNeitherNeighbour(unittest.TestCase):
    """Folding it either way would misstate these values."""

    def test_it_is_not_reported_as_a_resolvable_uri(self):
        """`urn:cm4ai:org:ucsd` alongside `https://ror.org/…` would claim a
        standing it does not have: the NID is not registered."""
        self.assertNotEqual(classify("urn:cm4ai:org:ucsd", PREFIXES), URI)

    def test_it_is_not_counted_unresolvable(self):
        from data_sheets_schema.identifiers import UNRESOLVABLE
        self.assertNotIn(URI_UNVERIFIED, UNRESOLVABLE)

    def test_the_genuine_failures_still_fail(self):
        """The exemption must not leak. A bare token and an undeclared prefix
        are still the two things this audit exists to find."""
        self.assertEqual(classify("funder_nih", PREFIXES), BARE)
        self.assertEqual(classify("aireadi:public-dataset", PREFIXES),
                         CURIE_UNDECLARED)
        self.assertEqual(classify("d4d:x", PREFIXES), CURIE_DECLARED)

    def test_a_real_url_is_still_a_uri(self):
        self.assertEqual(classify("https://ror.org/01an7q238", PREFIXES), URI)


class TestAgainstTheCorpus(unittest.TestCase):
    def test_the_reclassification_moves_the_headline(self):
        """1,067 values move out of unresolvable — 28% of the undeclared-CURIE
        bucket — which is why #457 must be re-sized before a pattern is chosen
        rather than after."""
        from pathlib import Path

        from data_sheets_schema import identifiers as ident
        from data_sheets_schema.runs import CONCAT_DIR

        if not Path(CONCAT_DIR).exists():
            self.skipTest("corpus absent")
        report = ident.audit(root=CONCAT_DIR)
        counts = report["counts"]
        self.assertGreater(counts[URI_UNVERIFIED], 500)
        # Every one of them would previously have been called unresolvable.
        self.assertLess(report["unresolvable_share"], 0.30)


class TestTheSchemeListIsNarrow(unittest.TestCase):
    """Every name in `NO_AUTHORITY_SCHEMES` exempts values from the audit, so
    a name that is not really a scheme silently excuses a real defect. This is
    the direction that fails quietly, and the only one worth guarding hard."""

    def test_file_is_not_exempted(self):
        """The sharpest case. `file` *is* a registered scheme, but its 22
        corpus occurrences are `file:torchaudio_spectrograms_parquet` — a
        minted type-prefix in the same family as `org:` and `creator:` (#531),
        not `file:///path`. Exempting it would erase 22 genuine findings to
        accommodate a name collision."""
        self.assertNotIn("file", NO_AUTHORITY_SCHEMES)
        self.assertEqual(
            classify("file:torchaudio_spectrograms_parquet", PREFIXES),
            CURIE_UNDECLARED)

    def test_urn_namespaces_are_not_listed_as_schemes(self):
        """`isbn`, `issn` and `uuid` are URN namespaces — `urn:isbn:…` — not
        schemes. A record writing `uuid:abc` is minting a prefix, not citing
        one, and must still be reported."""
        for name in ("isbn", "issn", "uuid"):
            with self.subTest(name=name):
                self.assertNotIn(name, NO_AUTHORITY_SCHEMES)
                self.assertEqual(classify(f"{name}:abc", PREFIXES),
                                 CURIE_UNDECLARED)

    def test_the_list_stays_small(self):
        """A growing exemption list is how an audit stops auditing. Anything
        added should be a registered scheme with corpus evidence behind it."""
        self.assertLessEqual(len(NO_AUTHORITY_SCHEMES), 8)

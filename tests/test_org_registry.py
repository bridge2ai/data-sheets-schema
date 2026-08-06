"""Tests for B2AI organization-registry resolution and enrichment (#378)."""

import unittest

from data_sheets_schema.org_registry import (
    OrgResolver,
    enrich_record,
    enrichment_block,
)


class TestOrgResolver(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = OrgResolver()

    def test_resolves_acronym_full_name_and_ror(self):
        by_acronym = self.r.resolve("AHRQ")
        self.assertEqual(by_acronym["id"], "B2AI_ORG:2")
        by_full = self.r.resolve("US Agency for Healthcare Research and Quality")
        self.assertEqual(by_full["id"], "B2AI_ORG:2")
        by_ror = self.r.resolve("see https://ror.org/03jmfdf59 for details")
        self.assertEqual(by_ror["id"], "B2AI_ORG:2")

    def test_no_fuzzy_matching(self):
        # A wrong identifier asserted confidently is worse than none.
        self.assertIsNone(self.r.resolve("Agency for Healthcare Research"))
        self.assertIsNone(self.r.resolve("University of Nowhere"))
        self.assertIsNone(self.r.resolve(""))

    def test_snapshot_is_pinned(self):
        self.assertEqual(len(self.r.snapshot_sha256), 64)


class TestEnrichRecord(unittest.TestCase):
    def test_fills_only_nameonly_org_objects_and_logs_paths(self):
        record = {
            "creators": [{"name": "Team", "affiliations": [
                {"name": "AHRQ"},
                {"name": "University of Nowhere"},
                {"id": "existing:1", "name": "AMA"},
            ]}],
            "name": "AHRQ",   # a plain string slot, must not become an object
        }
        _, log = enrich_record(record, OrgResolver())
        affs = record["creators"][0]["affiliations"]
        self.assertEqual(affs[0]["id"], "B2AI_ORG:2")
        self.assertNotIn("id", affs[1], "unresolved names stay name-only")
        self.assertEqual(affs[2]["id"], "existing:1",
                         "existing ids are never overwritten")
        self.assertEqual(record["name"], "AHRQ")
        self.assertEqual([e["path"] for e in log],
                         ["/creators/0/affiliations/0"])

    def test_enrichment_block_carries_the_claim_context(self):
        r = OrgResolver()
        record = {"creators": [{"name": "T",
                                "affiliations": [{"name": "AMA"}]}]}
        _, log = enrich_record(record, r)
        block = enrichment_block(log, r)
        self.assertEqual(block["kind"], "organization_identifiers")
        self.assertEqual(block["snapshot_sha256"], r.snapshot_sha256)
        self.assertIn("enrichment, not extraction", block["note"])
        self.assertEqual(block["resolved"], log)


if __name__ == "__main__":
    unittest.main()

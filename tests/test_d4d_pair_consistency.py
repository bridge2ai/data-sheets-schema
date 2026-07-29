"""Tests for schema-derived full/core D4D consistency validation."""

import unittest
from pathlib import Path

from data_sheets_schema.d4d_pair_consistency import (
    load_pair_schema,
    synchronize_core_data,
    validate_pair_data,
)


ROOT = Path(__file__).resolve().parents[1]
FULL_SCHEMA = (
    ROOT
    / "src"
    / "data_sheets_schema"
    / "schema"
    / "data_sheets_schema_all.yaml"
)
CORE_SCHEMA = (
    ROOT
    / "src"
    / "data_sheets_schema"
    / "schema"
    / "data_sheets_schema_core_all.yaml"
)


class TestD4DPairConsistency(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pair_schema = load_pair_schema(FULL_SCHEMA, CORE_SCHEMA)

    def test_schema_derives_identity_and_projected_slots(self):
        self.assertEqual(76, len(self.pair_schema.identity_slots))
        self.assertIn("description", self.pair_schema.identity_slots)
        self.assertEqual(("resources",), self.pair_schema.projected_slots)

    def test_identical_shared_content_passes(self):
        full = {
            "id": "https://example.org/dataset",
            "description": "Canonical description.",
            "keywords": ["one", "two"],
        }
        core = {
            "id": "https://example.org/dataset",
            "description": "Canonical description.",
            "keywords": ["one", "two"],
        }
        report = validate_pair_data(full, core, self.pair_schema)
        self.assertTrue(report.passed, report.errors)

    def test_condensed_narrative_fails(self):
        full = {
            "id": "https://example.org/dataset",
            "description": "Canonical detailed description.",
        }
        core = {
            "id": "https://example.org/dataset",
            "description": "Condensed description.",
        }
        report = validate_pair_data(full, core, self.pair_schema)
        self.assertFalse(report.passed)
        self.assertIn(
            "shared-slot-content", {issue.code for issue in report.errors}
        )

    def test_one_sided_shared_slot_fails(self):
        full = {
            "id": "https://example.org/dataset",
            "description": "Present only in full.",
        }
        core = {"id": "https://example.org/dataset"}
        report = validate_pair_data(full, core, self.pair_schema)
        self.assertFalse(report.passed)
        self.assertIn(
            "shared-slot-presence", {issue.code for issue in report.errors}
        )

    def test_resources_are_compared_as_core_projections(self):
        full = {
            "id": "https://example.org/dataset",
            "resources": [
                {
                    "id": "https://example.org/resource",
                    "description": "Shared resource description.",
                    "file_collections": [
                        {
                            "id": "https://example.org/resource/files",
                            "name": "Full-only files",
                        }
                    ],
                }
            ],
        }
        core = {
            "id": "https://example.org/dataset",
            "resources": [
                {
                    "id": "https://example.org/resource",
                    "description": "Shared resource description.",
                }
            ],
        }
        report = validate_pair_data(full, core, self.pair_schema)
        self.assertTrue(report.passed, report.errors)

    def test_related_distribution_conflict_fails(self):
        full = {
            "id": "https://example.org/dataset",
            "file_collections": [
                {
                    "id": "https://example.org/files",
                    "name": "Files",
                    "path": "data/",
                    "total_bytes": 100,
                }
            ],
        }
        core = {
            "id": "https://example.org/dataset",
            "distributions": [
                {
                    "id": "https://example.org/files",
                    "name": "Files",
                    "path": "other/",
                    "bytes": 99,
                }
            ],
        }
        report = validate_pair_data(full, core, self.pair_schema)
        self.assertFalse(report.passed)
        self.assertIn(
            "distribution-related-content",
            {issue.code for issue in report.errors},
        )

    def test_synchronize_core_uses_full_as_canonical_content(self):
        full = {
            "id": "https://example.org/dataset",
            "description": "Canonical detailed description.",
            "anomalies": [
                {
                    "id": "https://example.org/anomaly",
                    "name": "Known anomaly",
                }
            ],
        }
        core = {
            "id": "https://example.org/dataset",
            "description": "Condensed description.",
            "distributions": [
                {
                    "id": "https://example.org/distribution",
                    "name": "Core-only distribution",
                }
            ],
        }
        synchronized = synchronize_core_data(
            full, core, self.pair_schema
        )
        self.assertEqual(full["description"], synchronized["description"])
        self.assertEqual(full["anomalies"], synchronized["anomalies"])
        self.assertEqual(core["distributions"], synchronized["distributions"])


if __name__ == "__main__":
    unittest.main()

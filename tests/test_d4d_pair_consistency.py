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

    #: Every slot `Dataset` and `CoreDataset` share with an identical value
    #: signature. Named rather than counted (#407): the assertion used to be
    #: `assertEqual(76, len(...))`, which said nothing about *which* slots, so
    #: a change that removed one and added another would have passed. It also
    #: gave no clue what had happened when it did fail.
    #:
    #: Went 76 -> 78 when `notes` and `source_caveats` were added to the base
    #: class in f192c34f (#385). Both are genuinely shared and genuinely
    #: identical, so the count was stale rather than the schema wrong.
    EXPECTED_IDENTITY_SLOTS = (
    'acquisition_methods', 'addressing_gaps', 'annotation_analyses',
    'anomalies', 'at_risk_populations', 'cleaning_strategies',
    'collection_mechanisms', 'collection_timeframes', 'compression',
    'confidential_elements', 'conforms_to', 'conforms_to_class',
    'conforms_to_schema', 'content_warnings', 'created_by',
    'created_on', 'creators', 'data_collectors',
    'data_protection_impacts', 'description', 'discouraged_uses',
    'distribution_dates', 'distribution_formats', 'doi',
    'download_url', 'errata', 'ethical_reviews', 'existing_uses',
    'extension_mechanism', 'external_resources', 'funders',
    'future_use_impacts', 'human_subject_research', 'id',
    'imputation_protocols', 'informed_consent', 'instances',
    'intended_uses', 'ip_restrictions', 'is_deidentified',
    'is_tabular', 'issued', 'keywords', 'known_biases',
    'known_limitations', 'labeling_strategies', 'language',
    'last_updated_on', 'license', 'license_and_use_terms',
    'machine_annotation_tools', 'maintainers',
    'missing_data_documentation', 'modified_by', 'name', 'notes',
    'other_tasks', 'page', 'preprocessing_strategies',
    'prohibited_uses', 'publisher', 'purposes', 'raw_data_sources',
    'raw_sources', 'regulatory_restrictions', 'retention_limit',
    'sampling_strategies', 'sensitive_elements', 'source_caveats',
    'status', 'subpopulations', 'tasks', 'title', 'updates',
    'use_repository', 'version', 'version_access',
    'was_derived_from'
    )

    def test_schema_derives_identity_and_projected_slots(self):
        self.assertEqual(self.EXPECTED_IDENTITY_SLOTS,
                         tuple(sorted(self.pair_schema.identity_slots)))
        self.assertEqual(("resources",), self.pair_schema.projected_slots)

    def test_the_evidence_channel_slots_are_shared(self):
        """#385 added `notes` and `source_caveats` to the base class, which is
        what moved the count. Pinned separately so that if they are ever
        removed from one class only, the failure names the cause."""
        for slot in ("notes", "source_caveats", "description"):
            with self.subTest(slot=slot):
                self.assertIn(slot, self.pair_schema.identity_slots)

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

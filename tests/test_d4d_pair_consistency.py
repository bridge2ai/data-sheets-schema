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
    #:
    #: Went 78 -> 80 when `data_governance` and `related_datasets` reached
    #: `CoreDataset` (#510). Identity is the right relation for both: they
    #: state the same fact in either record, so a full/core pair disagreeing
    #: about who runs the access committee is a defect and not a projection.
    #:
    #: Went 80 -> 78 when `conforms_to_class` and `conforms_to_schema` became
    #: per-record slots (#499). They describe the record rather than the
    #: dataset, so their correct values *differ* between a pair — identity
    #: made them unrepresentable. `conforms_to` stays here: a standard the
    #: data follows is a fact about the data and is the same in both.
    EXPECTED_IDENTITY_SLOTS = (
    'acquisition_methods', 'addressing_gaps', 'annotation_analyses',
    'anomalies', 'at_risk_populations', 'cleaning_strategies',
    'collection_mechanisms', 'collection_timeframes', 'compression',
    'confidential_elements', 'conforms_to',
    'content_warnings', 'created_by',
    'created_on', 'creators', 'data_collectors', 'data_governance',
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
    'raw_sources', 'regulatory_restrictions', 'related_datasets',
    'retention_limit',
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

    # --- nested resource matching (#401) -------------------------------
    #
    # `FileCollection` is collection-level (total_bytes, file_count,
    # collection_type, nested resources); `CoreDistribution` is file-level
    # (bytes, hash, md5, sha256, path, media_type). A core record that
    # enumerates one distribution per file is therefore doing the correct
    # thing, and matching only at the top level reported all 12 of
    # VOICE_PEDIATRIC's as unmatched while every one matched a nested File.

    def _nested_pair(self, *, core_bytes=10, core_path="data/a.csv"):
        full = {
            "id": "https://example.org/dataset",
            "file_collections": [
                {
                    "id": "https://example.org/collection",
                    "name": "Collection",
                    "total_bytes": 100,
                    "resources": [
                        {
                            "id": "https://example.org/file-a",
                            "name": "a.csv",
                            "path": "data/a.csv",
                            "bytes": 10,
                        }
                    ],
                }
            ],
        }
        core = {
            "id": "https://example.org/dataset",
            "distributions": [
                {
                    "id": "https://example.org/file-a",
                    "name": "a.csv",
                    "path": core_path,
                    "bytes": core_bytes,
                }
            ],
        }
        return full, core

    def _relation_warning(self, report):
        for issue in report.warnings:
            if issue.path == "$.file_collections <-> $.distributions":
                return issue.message
        self.fail("no distribution relation warning emitted")

    def test_a_file_level_distribution_matches_a_nested_resource(self):
        full, core = self._nested_pair()
        report = validate_pair_data(full, core, self.pair_schema)
        message = self._relation_warning(report)
        self.assertIn("unmatched core distributions=[]", message)
        self.assertIn("1 at nested resource level", message)
        self.assertIn("0 at collection level", message)

    def test_a_nested_match_is_not_an_error(self):
        """The record was correct; only the instrument disagreed."""
        full, core = self._nested_pair()
        report = validate_pair_data(full, core, self.pair_schema)
        self.assertEqual(
            [i for i in report.errors
             if i.code == "distribution-related-content"], [])

    def test_bytes_is_compared_against_the_nested_file_not_the_total(self):
        """A file size against a collection total is a category error.

        The nested File is 10 bytes and its collection is 100. Comparing the
        core distribution's 10 against 100 would report a conflict on a record
        that agrees exactly.
        """
        full, core = self._nested_pair(core_bytes=10)
        report = validate_pair_data(full, core, self.pair_schema)
        self.assertEqual(
            [i for i in report.errors
             if i.code == "distribution-related-content"], [])

    def test_a_real_conflict_against_a_nested_file_is_still_caught(self):
        """Descending must not turn the check off."""
        full, core = self._nested_pair(core_bytes=999, core_path="wrong/")
        report = validate_pair_data(full, core, self.pair_schema)
        codes = {i.code for i in report.errors}
        self.assertIn("distribution-related-content", codes)

    def test_collection_level_matching_still_wins_and_is_reported_as_such(self):
        """The pre-existing behaviour, unchanged and now labelled."""
        full = {
            "id": "https://example.org/dataset",
            "file_collections": [
                {"id": "https://example.org/files", "name": "Files",
                 "total_bytes": 100},
            ],
        }
        core = {
            "id": "https://example.org/dataset",
            "distributions": [
                {"id": "https://example.org/files", "name": "Files",
                 "bytes": 100},
            ],
        }
        report = validate_pair_data(full, core, self.pair_schema)
        message = self._relation_warning(report)
        self.assertIn("1 at collection level", message)
        self.assertIn("0 at nested resource level", message)

    def test_a_genuinely_absent_distribution_is_still_unmatched(self):
        """The signal the fix exists to make meaningful.

        Before #401 this warning looked identical to the benign nested case,
        so the alarming reading was routine. It must survive.
        """
        full = {
            "id": "https://example.org/dataset",
            "file_collections": [
                {"id": "https://example.org/collection", "name": "C",
                 "resources": [{"id": "https://example.org/file-a",
                                "name": "a.csv"}]},
            ],
        }
        core = {
            "id": "https://example.org/dataset",
            "distributions": [
                {"id": "https://example.org/nowhere", "name": "ghost.csv"},
            ],
        }
        report = validate_pair_data(full, core, self.pair_schema)
        self.assertIn("unmatched core distributions=[0]",
                      self._relation_warning(report))

    def test_an_id_duplicated_across_collections_is_not_resolved_silently(self):
        """Ambiguity is reported, not settled by iteration order."""
        full = {
            "id": "https://example.org/dataset",
            "file_collections": [
                {"id": "https://example.org/c1", "name": "C1",
                 "resources": [{"id": "https://example.org/dup", "name": "x"}]},
                {"id": "https://example.org/c2", "name": "C2",
                 "resources": [{"id": "https://example.org/dup", "name": "y"}]},
            ],
        }
        core = {
            "id": "https://example.org/dataset",
            "distributions": [
                {"id": "https://example.org/dup", "name": "z"},
            ],
        }
        report = validate_pair_data(full, core, self.pair_schema)
        self.assertIn("unmatched core distributions=[0]",
                      self._relation_warning(report))

    def test_an_ambiguous_collection_match_is_not_rescued_by_descending(self):
        """Two collections sharing an id is a defect; descending would hide it.

        `_related_match` reports ambiguity distinctly from absence. If the
        descent treated them alike, this record would report a tidy
        `1 at nested resource level` match and the duplicate collection id
        would vanish from the output — less visible than before #401, which
        exists to make `unmatched` mean what it says (#474).
        """
        full = {
            "id": "https://example.org/dataset",
            "file_collections": [
                {"id": "https://example.org/dup", "name": "C1",
                 "resources": [{"id": "https://example.org/dup",
                                "name": "nested"}]},
                {"id": "https://example.org/dup", "name": "C2"},
            ],
        }
        core = {
            "id": "https://example.org/dataset",
            "distributions": [
                {"id": "https://example.org/dup", "name": "d"},
            ],
        }
        report = validate_pair_data(full, core, self.pair_schema)
        message = self._relation_warning(report)
        self.assertIn("unmatched core distributions=[0]", message)
        self.assertIn("0 at nested resource level", message)

    def test_a_collection_without_resources_is_handled(self):
        full = {
            "id": "https://example.org/dataset",
            "file_collections": [
                {"id": "https://example.org/c", "name": "C"},
                {"id": "https://example.org/c2", "name": "C2",
                 "resources": "not a list"},
            ],
        }
        core = {
            "id": "https://example.org/dataset",
            "distributions": [{"id": "https://example.org/x", "name": "x"}],
        }
        report = validate_pair_data(full, core, self.pair_schema)
        self.assertIn("unmatched core distributions=[0]",
                      self._relation_warning(report))

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

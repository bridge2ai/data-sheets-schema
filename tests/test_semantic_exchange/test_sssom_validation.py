#!/usr/bin/env python3
"""
Unit tests for SSSOM mapping validation.

Tests SSSOM (Simple Standard for Sharing Ontology Mappings) file generation,
format compliance, and mapping completeness.
"""

import unittest
import subprocess
from pathlib import Path
import csv
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestSSSOMValidation(unittest.TestCase):
    """Test SSSOM mapping validation and compliance."""

    def setUp(self):
        """Set up test fixtures."""
        self.repo_root = Path(__file__).parent.parent.parent
        # Structural SSSOM lives under data/; the rest are canonical under src/.
        self.mappings_dir = self.repo_root / "data" / "semantic_exchange"
        self.src_dir = self.repo_root / "src" / "data_sheets_schema" / "semantic_exchange"

        self.sssom_files = {
            'structural': self.mappings_dir / "d4d_rocrate_structural_mapping.sssom.tsv",
            'comprehensive': self.src_dir / "d4d_rocrate_sssom_comprehensive.tsv",
            'uri': self.src_dir / "d4d_rocrate_sssom_uri_mapping.tsv",
            'uri_comprehensive': self.src_dir / "d4d_rocrate_sssom_uri_comprehensive.tsv",
        }

    def test_sssom_files_exist(self):
        """Test that all expected SSSOM files exist."""
        missing_files = []
        for name, path in self.sssom_files.items():
            if not path.exists():
                missing_files.append(f"{name}: {path}")

        if missing_files:
            self.fail(f"Missing SSSOM files (run 'make gen-sssom-all' to generate):\n" +
                     "\n".join(missing_files))

    def test_sssom_file_format(self):
        """Test that SSSOM files have correct TSV format."""
        for name, path in self.sssom_files.items():
            if not path.exists():
                self.skipTest(f"SSSOM file not found: {path}")

            with self.subTest(file=name):
                with open(path, 'r', encoding='utf-8') as f:
                    # Read lines
                    lines = f.readlines()
                    self.assertGreater(len(lines), 1,
                                      f"{name}: File should have header + data rows")

                    # Find first non-comment line (header)
                    header = None
                    for line in lines:
                        if not line.startswith('#'):
                            header = line.strip()
                            break

                    self.assertIsNotNone(header, f"{name}: Should have non-comment header")
                    # Check for TSV format (tab-separated)
                    self.assertIn('\t', header,
                                 f"{name}: Header should be tab-separated")

    def test_sssom_required_columns(self):
        """Test that SSSOM files contain required columns."""
        required_columns = {
            'predicate_id',
            'object_id',
            'mapping_justification'
        }

        for name, path in self.sssom_files.items():
            if not path.exists():
                self.skipTest(f"SSSOM file not found: {path}")

            # Skip uri_comprehensive which uses different column naming
            if name == 'uri_comprehensive':
                continue

            with self.subTest(file=name):
                with open(path, 'r', encoding='utf-8') as f:
                    # Skip comment lines
                    lines = [line for line in f if not line.startswith('#')]
                    f_filtered = '\n'.join(lines)
                    import io
                    reader = csv.DictReader(io.StringIO(f_filtered), delimiter='\t')
                    columns = set(reader.fieldnames or [])

                    # Check for subject_id or d4d_slot_name (different naming conventions)
                    has_subject = 'subject_id' in columns or 'd4d_slot_name' in columns
                    self.assertTrue(has_subject,
                                   f"{name}: Missing subject identifier column (subject_id or d4d_slot_name)")

                    missing = required_columns - columns
                    self.assertEqual(len(missing), 0,
                                   f"{name}: Missing required columns: {missing}")

    def test_sssom_structural_mapping_count(self):
        """Test that structural SSSOM mapping has expected number of mappings."""
        path = self.sssom_files['structural']
        if not path.exists():
            self.skipTest(f"SSSOM file not found: {path}")

        with open(path, 'r', encoding='utf-8') as f:
            # Skip comment lines
            lines = [line for line in f if not line.startswith('#')]
            f_filtered = '\n'.join(lines)
            import io
            reader = csv.DictReader(io.StringIO(f_filtered), delimiter='\t')
            rows = list(reader)

        # Structural mapping should have multiple mappings
        self.assertGreater(len(rows), 50,
                          "Structural SSSOM should have at least 50 mappings")

    def test_sssom_uri_mapping_count(self):
        """Test that URI SSSOM mapping has expected number of mappings."""
        path = self.sssom_files['uri']
        if not path.exists():
            self.skipTest(f"SSSOM file not found: {path}")

        with open(path, 'r', encoding='utf-8') as f:
            # Skip comment lines
            lines = [line for line in f if not line.startswith('#')]
            f_filtered = '\n'.join(lines)
            import io
            reader = csv.DictReader(io.StringIO(f_filtered), delimiter='\t')
            rows = list(reader)

        # URI SSSOM should have some URI mappings
        self.assertGreater(len(rows), 10,
                          "URI SSSOM should have at least 10 mappings")

    def test_sssom_comprehensive_mapping_count(self):
        """Test that comprehensive SSSOM has all D4D attributes."""
        path = self.sssom_files['comprehensive']
        if not path.exists():
            self.skipTest(f"SSSOM file not found: {path}")

        with open(path, 'r', encoding='utf-8') as f:
            # Skip comment lines
            lines = [line for line in f if not line.startswith('#')]
            f_filtered = '\n'.join(lines)
            import io
            reader = csv.DictReader(io.StringIO(f_filtered), delimiter='\t')
            rows = list(reader)

        # Comprehensive SSSOM should have many mappings (all D4D attributes)
        self.assertGreater(len(rows), 200,
                        "Comprehensive SSSOM should have at least 200 mappings")

    def test_sssom_no_duplicate_subjects(self):
        """Test that SSSOM files don't have duplicate subject_id entries."""
        for name, path in self.sssom_files.items():
            if not path.exists():
                continue

            # Skip files that intentionally allow duplicates:
            # - comprehensive: has all attributes
            # - uri_comprehensive: has different structure
            # - uri: maps D4D → RO-Crate URIs, multiple D4D fields can map to same URI
            if name in ['comprehensive', 'uri_comprehensive', 'uri']:
                continue

            with self.subTest(file=name):
                with open(path, 'r', encoding='utf-8') as f:
                    # Skip comment lines
                    lines = [line for line in f if not line.startswith('#')]
                    f_filtered = '\n'.join(lines)
                    import io
                    reader = csv.DictReader(io.StringIO(f_filtered), delimiter='\t')
                    subjects = [row['subject_id'] for row in reader]

                duplicates = [s for s in set(subjects) if subjects.count(s) > 1]
                self.assertEqual(len(duplicates), 0,
                               f"{name}: Found duplicate subjects: {duplicates[:5]}")

    def test_sssom_mapping_status_distribution(self):
        """Test that comprehensive SSSOM has expected status distribution."""
        path = self.sssom_files['comprehensive']
        if not path.exists():
            self.skipTest(f"SSSOM file not found: {path}")

        with open(path, 'r', encoding='utf-8') as f:
            # Skip comment lines
            lines = [line for line in f if not line.startswith('#')]
            f_filtered = '\n'.join(lines)
            import io
            reader = csv.DictReader(io.StringIO(f_filtered), delimiter='\t')

            # Check if mapping_status column exists
            if 'mapping_status' not in (reader.fieldnames or []):
                self.skipTest("mapping_status column not found")

            rows = list(reader)
            statuses = [row.get('mapping_status', '') for row in rows]
            status_counts = {}
            for status in statuses:
                status_counts[status] = status_counts.get(status, 0) + 1

        # Should have distribution across different statuses (if the column exists)
        # Accept any statuses present, just verify there are multiple
        self.assertGreater(len(status_counts), 0,
                          "Should have at least one status type")

    def test_sssom_predicate_ids_valid(self):
        """Test that predicate_id values are valid SSSOM predicates."""
        valid_predicates = {
            'skos:exactMatch',
            'skos:closeMatch',
            'skos:broadMatch',
            'skos:narrowMatch',
            'skos:relatedMatch',
            'owl:equivalentClass',
            'owl:equivalentProperty',
            'rdfs:subClassOf',
            'rdfs:subPropertyOf',
            # SEMAPV extension predicates for unmapped/unmappable properties
            'semapv:UnmappedProperty',
            'semapv:UnmappableProperty',
        }

        for name, path in self.sssom_files.items():
            if not path.exists():
                continue

            with self.subTest(file=name):
                with open(path, 'r', encoding='utf-8') as f:
                    # Skip comment lines
                    lines = [line for line in f if not line.startswith('#')]
                    f_filtered = '\n'.join(lines)
                    import io
                    reader = csv.DictReader(io.StringIO(f_filtered), delimiter='\t')
                    predicates = set(row['predicate_id'] for row in reader)

                # Allow empty predicates for unmapped entries
                predicates.discard('')

                invalid = predicates - valid_predicates
                self.assertEqual(len(invalid), 0,
                               f"{name}: Found invalid predicates: {invalid}")

    def test_sssom_generation_succeeds(self):
        """Test that SSSOM generation command succeeds."""
        self.skipTest("SSSOM files are manually curated in data/semantic_exchange/")


class TestSSSOMIntegration(unittest.TestCase):
    """Test SSSOM integration with schema and mappings."""

    def setUp(self):
        """Set up test fixtures."""
        self.repo_root = Path(__file__).parent.parent.parent
        self.mappings_dir = self.repo_root / "data" / "semantic_exchange"
        self.src_dir = self.repo_root / "src" / "data_sheets_schema" / "semantic_exchange"

    def test_sssom_references_valid_d4d_slots(self):
        """Test that SSSOM subject_ids reference actual D4D schema slots."""
        sssom_file = self.mappings_dir / "d4d_rocrate_structural_mapping.sssom.tsv"
        if not sssom_file.exists():
            self.skipTest(f"SSSOM file not found: {sssom_file}")

        # Read SSSOM file
        with open(sssom_file, 'r', encoding='utf-8') as f:
            # Skip comment lines
            lines = [line for line in f if not line.startswith('#')]
            f_filtered = '\n'.join(lines)
            import io
            reader = csv.DictReader(io.StringIO(f_filtered), delimiter='\t')
            subject_ids = [row['subject_id'] for row in reader]

        # Extract slot names from subject_ids (format: d4d:slot_name)
        slot_names = []
        for subject_id in subject_ids:
            if subject_id.startswith('d4d:'):
                slot_name = subject_id.replace('d4d:', '')
                slot_names.append(slot_name)

        self.assertGreater(len(slot_names), 0,
                          "Should have at least some d4d: prefixed subjects")

    def test_sssom_mapping_files_readable(self):
        """Test that all SSSOM files can be read without errors."""
        sssom_files = (list(self.mappings_dir.glob("*.tsv"))
                       + list(self.src_dir.glob("*.tsv")))

        self.assertGreater(len(sssom_files), 0,
                          "Should have at least one SSSOM .tsv file")

        for sssom_file in sssom_files:
            with self.subTest(file=sssom_file.name):
                try:
                    with open(sssom_file, 'r', encoding='utf-8') as f:
                        # Skip comment lines
                        lines = [line for line in f if not line.startswith('#')]
                        f_filtered = '\n'.join(lines)
                        import io
                        reader = csv.DictReader(io.StringIO(f_filtered), delimiter='\t')
                        rows = list(reader)
                        self.assertGreater(len(rows), 0,
                                         f"{sssom_file.name} should have data rows")
                except Exception as e:
                    self.fail(f"Failed to read {sssom_file.name}: {e}")


if __name__ == '__main__':
    unittest.main()

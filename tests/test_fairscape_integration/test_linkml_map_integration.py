#!/usr/bin/env python3
"""
Tests for LinkML-Map Integration utility.

Tests integration with standard linkml-map package.
"""

import unittest
import sys
import tempfile
from pathlib import Path

# Add src to path for imports
repo_root = Path(__file__).parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from src.fairscape_integration.utils.linkml_map_integration import (
    LinkMLMapIntegration,
    LINKML_MAP_AVAILABLE,
    create_sssom_from_tsv_mapping
)


class TestLinkMLMapIntegration(unittest.TestCase):
    """Test LinkML-Map integration."""

    def test_is_available(self):
        """Test checking if linkml-map is available."""
        result = LinkMLMapIntegration.is_available()
        self.assertIsInstance(result, bool)
        self.assertEqual(result, LINKML_MAP_AVAILABLE)

    def test_get_version(self):
        """Test getting linkml-map version."""
        version = LinkMLMapIntegration.get_version()

        if LINKML_MAP_AVAILABLE:
            self.assertIsNotNone(version)
            self.assertIsInstance(version, str)
        else:
            self.assertIsNone(version)

    def test_initialization_without_schemas(self):
        """Test initialization without providing schemas."""
        integration = LinkMLMapIntegration(verbose=False)

        self.assertIsNone(integration.source_schema)
        self.assertIsNone(integration.target_schema)
        self.assertIsNone(integration.sssom_mappings)
        self.assertFalse(integration.verbose)

    @unittest.skipIf(not LINKML_MAP_AVAILABLE, "linkml-map not available")
    def test_initialization_with_schemas(self):
        """Test initialization with schemas (when linkml-map available)."""
        # Use actual schema files if they exist
        d4d_schema = repo_root / "src/data_sheets_schema/schema/data_sheets_schema_all.yaml"

        if d4d_schema.exists():
            integration = LinkMLMapIntegration(
                target_schema=str(d4d_schema),
                verbose=False
            )

            self.assertEqual(integration.target_schema, d4d_schema)
            self.assertTrue(integration.use_standard)

    def test_mapping_report(self):
        """Test getting mapping report."""
        integration = LinkMLMapIntegration(verbose=False)
        report = integration.get_mapping_report()

        self.assertIsInstance(report, dict)

        if LINKML_MAP_AVAILABLE:
            self.assertIn('implementation', report)
            self.assertEqual(report['implementation'], 'linkml-map')
        else:
            self.assertIn('error', report)


class TestSSSOMConversion(unittest.TestCase):
    """Test TSV to SSSOM conversion utility."""

    def setUp(self):
        """Set up test fixtures."""
        # Create test TSV mapping
        self.tsv_content = """Class\tD4D Property\tType\tDef\tD4D description\tFAIRSCAPE RO-Crate Property\tCovered by FAIRSCAPE? Yes =1; No = 0\tDirect mapping? Yes =1; No = 0
D4D: Dataset\t\t\t\t\t\t\t
RO-Crate: Root Dataset\ttitle\tstr\t\tThe title\tname\t1\t1
RO-Crate: Root Dataset\tdescription\tstr\t\tThe description\tdescription\t1\t1
RO-Crate: Root Dataset\tkeywords\tlist[str]\t\tKeywords\tkeywords\t1\t1
RO-Crate: Root Dataset\tuncovered_field\tstr\t\tNot covered\t\t0\t0
"""
        self.temp_tsv = tempfile.NamedTemporaryFile(mode='w', suffix='.tsv', delete=False, encoding='utf-8')
        self.temp_tsv.write(self.tsv_content)
        self.temp_tsv.close()

        self.temp_sssom = tempfile.NamedTemporaryFile(mode='w', suffix='.sssom.tsv', delete=False, encoding='utf-8')
        self.temp_sssom.close()

    def tearDown(self):
        """Clean up temporary files."""
        Path(self.temp_tsv.name).unlink()
        if Path(self.temp_sssom.name).exists():
            Path(self.temp_sssom.name).unlink()

    def test_create_sssom_from_tsv(self):
        """Test converting TSV mapping to SSSOM format."""
        create_sssom_from_tsv_mapping(
            self.temp_tsv.name,
            self.temp_sssom.name
        )

        # Check output file was created
        self.assertTrue(Path(self.temp_sssom.name).exists())

        # Read and verify content
        with open(self.temp_sssom.name, 'r') as f:
            content = f.read()

        # Check for header comments
        self.assertIn('# SSSOM Mapping', content)
        self.assertIn('# Total mappings:', content)

        # Check for data rows
        self.assertIn('d4d:title', content)
        self.assertIn('d4d:description', content)
        self.assertIn('d4d:keywords', content)

        # Should NOT include uncovered field
        self.assertNotIn('d4d:uncovered_field', content)

        # Count non-comment lines
        lines = [line for line in content.split('\n') if not line.startswith('#') and line.strip()]
        # Header + 3 mappings
        self.assertEqual(len(lines), 4)

    def test_create_sssom_custom_prefixes(self):
        """Test creating SSSOM with custom prefixes."""
        create_sssom_from_tsv_mapping(
            self.temp_tsv.name,
            self.temp_sssom.name,
            subject_prefix='custom_d4d',
            object_prefix='custom_rocrate'
        )

        with open(self.temp_sssom.name, 'r') as f:
            content = f.read()

        # Check custom prefixes are used
        self.assertIn('custom_d4d:title', content)
        self.assertIn('custom_rocrate:name', content)


if __name__ == '__main__':
    unittest.main()

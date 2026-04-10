#!/usr/bin/env python3
"""
LinkML-Map Integration - Use linkml-map for schema transformations.

This module provides integration with linkml-map for transforming data
between D4D and RO-Crate schemas using SSSOM mappings.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
import warnings
import yaml

# Try to import linkml-map
LINKML_MAP_AVAILABLE = False
_linkml_map_import_error = None

try:
    from linkml_map.transformer.transformer import Transformer
    from linkml_map.transformer.session import Session
    LINKML_MAP_AVAILABLE = True
except ImportError as e:
    _linkml_map_import_error = str(e)
except Exception as e:
    # Catch other errors like KeyError during linkml-map initialization
    _linkml_map_import_error = f"linkml-map import error: {type(e).__name__}: {e}"


class LinkMLMapIntegration:
    """
    Integration layer for LinkML-Map transformations.

    Provides schema-based transformations using SSSOM mappings with the
    standard linkml-map package when available.
    """

    def __init__(
        self,
        source_schema: Optional[str] = None,
        target_schema: Optional[str] = None,
        sssom_mappings: Optional[str] = None,
        verbose: bool = False
    ):
        """
        Initialize LinkML-Map integration.

        Args:
            source_schema: Path to source LinkML schema (e.g., RO-Crate schema)
            target_schema: Path to target LinkML schema (e.g., D4D schema)
            sssom_mappings: Path to SSSOM mapping file
            verbose: Print transformation details
        """
        self.source_schema = Path(source_schema) if source_schema else None
        self.target_schema = Path(target_schema) if target_schema else None
        self.sssom_mappings = Path(sssom_mappings) if sssom_mappings else None
        self.verbose = verbose
        self.use_standard = LINKML_MAP_AVAILABLE

        if self.use_standard and source_schema and target_schema:
            self._init_transformer()

    def _init_transformer(self):
        """Initialize the linkml-map transformer."""
        if not self.use_standard:
            raise RuntimeError("linkml-map package not available")

        # Create session
        self.session = Session()

        # Load schemas
        if self.source_schema and self.source_schema.exists():
            self.session.set_source_schema(str(self.source_schema))

        if self.target_schema and self.target_schema.exists():
            self.session.set_target_schema(str(self.target_schema))

        # Load SSSOM mappings if provided
        if self.sssom_mappings and self.sssom_mappings.exists():
            self.session.set_mapping_file(str(self.sssom_mappings))

        # Create transformer
        self.transformer = Transformer(self.session)

        if self.verbose:
            print("LinkML-Map transformer initialized")
            print(f"  Source schema: {self.source_schema}")
            print(f"  Target schema: {self.target_schema}")
            print(f"  SSSOM mappings: {self.sssom_mappings}")

    def transform(
        self,
        source_data: Dict[str, Any],
        target_class: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Transform data from source schema to target schema.

        Args:
            source_data: Source data dictionary
            target_class: Target class name (optional)

        Returns:
            Transformed data in target schema format
        """
        if not self.use_standard:
            raise RuntimeError(
                "linkml-map package not available. "
                "Install with: poetry install --with dev"
            )

        if self.verbose:
            print(f"Transforming data to target class: {target_class}")

        # Transform using linkml-map
        result = self.transformer.transform(
            source_data,
            target_class=target_class
        )

        return result

    def transform_file(
        self,
        input_file: str,
        output_file: str,
        target_class: Optional[str] = None,
        input_format: str = 'yaml',
        output_format: str = 'yaml'
    ):
        """
        Transform data from file to file.

        Args:
            input_file: Input file path
            output_file: Output file path
            target_class: Target class name
            input_format: Input format ('yaml', 'json')
            output_format: Output format ('yaml', 'json')
        """
        if not self.use_standard:
            raise RuntimeError(
                "linkml-map package not available. "
                "Install with: poetry install --with dev"
            )

        # Read input
        with open(input_file, 'r') as f:
            if input_format == 'yaml':
                source_data = yaml.safe_load(f)
            elif input_format == 'json':
                import json
                source_data = json.load(f)
            else:
                raise ValueError(f"Unsupported input format: {input_format}")

        # Transform
        result = self.transform(source_data, target_class)

        # Write output
        with open(output_file, 'w') as f:
            if output_format == 'yaml':
                yaml.dump(result, f, default_flow_style=False, sort_keys=False)
            elif output_format == 'json':
                import json
                json.dump(result, f, indent=2)
            else:
                raise ValueError(f"Unsupported output format: {output_format}")

        if self.verbose:
            print(f"Transformed data written to: {output_file}")

    def get_mapping_report(self) -> Dict[str, Any]:
        """
        Get report on mappings used in transformation.

        Returns:
            Dictionary with mapping statistics
        """
        if not self.use_standard:
            return {
                'error': 'linkml-map package not available'
            }

        # Get mapping information from session
        report = {
            'source_schema': str(self.source_schema) if self.source_schema else None,
            'target_schema': str(self.target_schema) if self.target_schema else None,
            'sssom_mappings': str(self.sssom_mappings) if self.sssom_mappings else None,
            'implementation': 'linkml-map'
        }

        return report

    @staticmethod
    def is_available() -> bool:
        """
        Check if linkml-map package is available.

        Returns:
            True if linkml-map is installed, False otherwise
        """
        return LINKML_MAP_AVAILABLE

    @staticmethod
    def get_version() -> Optional[str]:
        """
        Get linkml-map version.

        Returns:
            Version string if available, None otherwise
        """
        if not LINKML_MAP_AVAILABLE:
            return None

        try:
            import linkml_map
            return linkml_map.__version__
        except AttributeError:
            return "unknown"


def create_sssom_from_tsv_mapping(
    tsv_mapping_path: str,
    output_sssom_path: str,
    subject_prefix: str = "d4d",
    object_prefix: str = "rocrate"
):
    """
    Convert legacy TSV mapping file to SSSOM format.

    Args:
        tsv_mapping_path: Path to TSV mapping file
        output_sssom_path: Path for output SSSOM file
        subject_prefix: Prefix for subject IDs (default: d4d)
        object_prefix: Prefix for object IDs (default: rocrate)
    """
    import csv

    with open(tsv_mapping_path, 'r', encoding='utf-8') as f_in:
        reader = csv.DictReader(f_in, delimiter='\t')

        mappings = []
        for row in reader:
            # Skip header rows
            if row.get('D4D Property', '').startswith('D4D:'):
                continue

            d4d_field = row.get('D4D Property', '').strip()
            rocrate_field = row.get('FAIRSCAPE RO-Crate Property', '').strip()
            covered = row.get('Covered by FAIRSCAPE? Yes =1; No = 0', '0').strip()

            if d4d_field and rocrate_field and covered == '1':
                # Handle multiple RO-Crate properties
                for rc_field in rocrate_field.split(','):
                    rc_field = rc_field.strip()
                    if rc_field:
                        mappings.append({
                            'subject_id': f"{subject_prefix}:{d4d_field}",
                            'subject_label': d4d_field,
                            'predicate_id': 'skos:exactMatch',
                            'object_id': f"{object_prefix}:{rc_field}",
                            'object_label': rc_field,
                            'mapping_justification': 'semapv:ManualMappingCuration',
                            'confidence': '1.0',
                            'subject_source': f"{subject_prefix}:schema",
                            'object_source': f"{object_prefix}:schema"
                        })

    # Write SSSOM TSV
    if mappings:
        fieldnames = list(mappings[0].keys())

        with open(output_sssom_path, 'w', newline='', encoding='utf-8') as f_out:
            # Write SSSOM header comments
            f_out.write(f"# SSSOM Mapping: {subject_prefix} -> {object_prefix}\n")
            f_out.write(f"# Generated from: {tsv_mapping_path}\n")
            f_out.write(f"# Total mappings: {len(mappings)}\n")
            f_out.write("#\n")

            # Write mappings
            writer = csv.DictWriter(f_out, fieldnames=fieldnames, delimiter='\t')
            writer.writeheader()
            writer.writerows(mappings)

        print(f"Created SSSOM file with {len(mappings)} mappings: {output_sssom_path}")
    else:
        print("No mappings found in TSV file")

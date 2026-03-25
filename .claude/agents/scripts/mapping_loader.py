#!/usr/bin/env python3
"""
Mapping Loader - Parse and load D4D to RO-Crate field mappings from TSV file.

This module loads the authoritative TSV mapping file and provides lookup functions
for transforming RO-Crate metadata to D4D YAML format.
"""

import csv
from pathlib import Path
from typing import Dict, List, Optional, Set


class MappingLoader:
    """Load and manage D4D to RO-Crate field mappings from TSV file."""

    def __init__(self, tsv_path: str):
        """
        Initialize mapping loader with TSV file.

        Args:
            tsv_path: Path to the mapping TSV file
        """
        self.tsv_path = Path(tsv_path)
        self.mappings: List[Dict[str, str]] = []
        self.covered_mappings: List[Dict[str, str]] = []
        self.d4d_to_rocrate: Dict[str, str] = {}
        self.rocrate_to_d4d: Dict[str, str] = {}
        self.direct_mappings: Set[str] = set()

        if not self.tsv_path.exists():
            raise FileNotFoundError(f"Mapping TSV not found: {tsv_path}")

        self._load_mappings()

    def _load_mappings(self):
        """Load and parse the TSV mapping file."""
        with open(self.tsv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter='\t')

            for row in reader:
                # Skip header rows and empty rows
                if not row.get('D4D Property') or row['D4D Property'].startswith('D4D:'):
                    continue

                self.mappings.append(row)

                # Filter to covered fields only (FAIRSCAPE coverage = 1)
                covered = row.get('Covered by FAIRSCAPE? Yes =1; No = 0', '0').strip()
                if covered == '1':
                    self.covered_mappings.append(row)

                    d4d_field = row['D4D Property'].strip()
                    rocrate_field = row.get('FAIRSCAPE RO-Crate Property', '').strip()

                    if d4d_field and rocrate_field:
                        self.d4d_to_rocrate[d4d_field] = rocrate_field

                        # Handle multiple RO-Crate properties mapping to same D4D field
                        # Split on comma for properties like "rai:dataCollection,rai:dataCollectionType"
                        for rc_prop in rocrate_field.split(','):
                            rc_prop = rc_prop.strip()
                            if rc_prop:
                                self.rocrate_to_d4d[rc_prop] = d4d_field

                        # Track direct mappings (1:1 relationships)
                        direct = row.get('Direct mapping? Yes =1; No = 0', '0').strip()
                        if direct == '1':
                            self.direct_mappings.add(d4d_field)

        print(f"Loaded {len(self.mappings)} total mappings")
        print(f"Found {len(self.covered_mappings)} FAIRSCAPE-covered mappings")
        print(f"Created {len(self.d4d_to_rocrate)} D4D→RO-Crate lookups")
        print(f"Created {len(self.rocrate_to_d4d)} RO-Crate→D4D lookups")

    def get_covered_fields(self) -> List[str]:
        """
        Get list of D4D fields covered by FAIRSCAPE RO-Crate.

        Returns:
            List of D4D property names with FAIRSCAPE coverage
        """
        return [m['D4D Property'].strip() for m in self.covered_mappings
                if m.get('D4D Property')]

    def get_rocrate_to_d4d_mapping(self) -> Dict[str, str]:
        """
        Get dictionary mapping RO-Crate properties to D4D fields.

        Returns:
            Dict with RO-Crate property names as keys, D4D field names as values
        """
        return self.rocrate_to_d4d.copy()

    def get_d4d_to_rocrate_mapping(self) -> Dict[str, str]:
        """
        Get dictionary mapping D4D fields to RO-Crate properties.

        Returns:
            Dict with D4D field names as keys, RO-Crate property names as values
        """
        return self.d4d_to_rocrate.copy()

    def get_rocrate_property(self, d4d_field: str) -> Optional[str]:
        """
        Get the RO-Crate property name for a given D4D field.

        Args:
            d4d_field: D4D property name

        Returns:
            RO-Crate property name, or None if no mapping exists
        """
        return self.d4d_to_rocrate.get(d4d_field)

    def get_d4d_field(self, rocrate_property: str) -> Optional[str]:
        """
        Get the D4D field name for a given RO-Crate property.

        Args:
            rocrate_property: RO-Crate property name

        Returns:
            D4D field name, or None if no mapping exists
        """
        return self.rocrate_to_d4d.get(rocrate_property)

    def is_direct_mapping(self, d4d_field: str) -> bool:
        """
        Check if a D4D field has a direct (1:1) mapping to RO-Crate.

        Args:
            d4d_field: D4D property name

        Returns:
            True if direct mapping, False otherwise
        """
        return d4d_field in self.direct_mappings

    def get_mapping_info(self, d4d_field: str) -> Optional[Dict[str, str]]:
        """
        Get complete mapping information for a D4D field.

        Args:
            d4d_field: D4D property name

        Returns:
            Dict with mapping details, or None if not found
        """
        for mapping in self.covered_mappings:
            if mapping.get('D4D Property', '').strip() == d4d_field:
                return mapping
        return None

    def get_all_mapped_rocrate_properties(self) -> Set[str]:
        """
        Get set of all RO-Crate properties that have D4D mappings.

        Returns:
            Set of RO-Crate property names
        """
        return set(self.rocrate_to_d4d.keys())


if __name__ == "__main__":
    # Test the mapping loader
    import sys

    if len(sys.argv) < 2:
        print("Usage: python mapping_loader.py <path_to_tsv>")
        sys.exit(1)

    loader = MappingLoader(sys.argv[1])

    print("\n=== Covered D4D Fields ===")
    covered = loader.get_covered_fields()
    print(f"Total: {len(covered)}")
    print("Sample fields:", covered[:10])

    print("\n=== Direct Mappings ===")
    print(f"Total: {len(loader.direct_mappings)}")
    print("Sample:", list(loader.direct_mappings)[:10])

    print("\n=== Sample Mapping Info ===")
    sample_field = covered[0] if covered else None
    if sample_field:
        info = loader.get_mapping_info(sample_field)
        print(f"Field: {sample_field}")
        print(f"  RO-Crate Property: {info.get('FAIRSCAPE RO-Crate Property')}")
        print(f"  Type: {info.get('Type')}")
        print(f"  Direct: {loader.is_direct_mapping(sample_field)}")

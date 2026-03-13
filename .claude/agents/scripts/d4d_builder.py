#!/usr/bin/env python3
"""
D4D Builder - Construct D4D YAML structure from RO-Crate metadata.

This module builds the D4D datasheet structure by mapping RO-Crate properties
to D4D classes and fields according to the TSV mapping specification.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union


class D4DBuilder:
    """Build D4D YAML structure from mapped RO-Crate data."""

    def __init__(self, mapping_loader):
        """
        Initialize D4D builder with mapping loader.

        Args:
            mapping_loader: MappingLoader instance with field mappings
        """
        self.mapping = mapping_loader
        self.d4d_data: Dict[str, Any] = {}

    def build_dataset(self, rocrate_parser) -> Dict[str, Any]:
        """
        Build complete D4D Dataset from RO-Crate parser.

        Args:
            rocrate_parser: ROCrateParser instance with loaded RO-Crate data

        Returns:
            Dict with D4D Dataset structure
        """
        self.d4d_data = {}

        # Get all covered D4D fields
        covered_fields = self.mapping.get_covered_fields()

        print(f"\nBuilding D4D dataset from {len(covered_fields)} mapped fields...")

        # Map each covered field
        mapped_count = 0
        for d4d_field in covered_fields:
            rocrate_property = self.mapping.get_rocrate_property(d4d_field)
            if not rocrate_property:
                continue

            # Handle multiple RO-Crate properties (comma-separated)
            rocrate_props = [p.strip() for p in rocrate_property.split(',')]

            # Try to extract value from RO-Crate
            value = None
            for rc_prop in rocrate_props:
                value = rocrate_parser.get_property(rc_prop)
                if value is not None:
                    break

            if value is not None:
                # Apply transformations based on field type
                transformed_value = self.apply_field_transformation(d4d_field, value)
                self.d4d_data[d4d_field] = transformed_value
                mapped_count += 1

        print(f"Successfully mapped {mapped_count}/{len(covered_fields)} fields")

        return self.d4d_data

    def apply_field_transformation(self, field_name: str, value: Any) -> Any:
        """
        Apply field-specific transformations to values.

        Args:
            field_name: D4D field name
            value: Raw value from RO-Crate

        Returns:
            Transformed value appropriate for D4D field
        """
        # Get mapping info for this field
        mapping_info = self.mapping.get_mapping_info(field_name)
        if not mapping_info:
            return value

        field_type = mapping_info.get('Type', '').lower()

        # Date transformations
        if 'date' in field_type or field_name in ['created_on', 'last_updated_on', 'issued', 'distribution_dates']:
            return self._transform_date(value)

        # Integer transformations
        if field_type in ['int', 'integer']:
            return self._transform_int(value)

        # List transformations
        if 'list' in field_type or isinstance(value, list):
            return self._transform_list(value, field_name)

        # Enum transformations
        if 'enum' in field_type:
            return self._transform_enum(value, field_name)

        # URI transformations
        if field_type == 'uri' or field_name in ['doi', 'download_url', 'publisher', 'status', 'conforms_to']:
            return self._transform_uri(value)

        # Person/Organization transformations
        if field_name in ['creators', 'created_by', 'modified_by', 'funders']:
            return self._transform_person_org(value)

        # Boolean transformations
        if field_type in ['bool', 'boolean']:
            return self._transform_bool(value)

        # String is default - handle None
        if value is None:
            return None

        # Return as string
        return str(value)

    def _transform_date(self, value: Any) -> Optional[str]:
        """Transform date values to D4D Date format (YYYY-MM-DD)."""
        if value is None:
            return None

        value_str = str(value)

        # Handle ISO 8601 datetime strings
        if 'T' in value_str:
            try:
                dt = datetime.fromisoformat(value_str.replace('Z', '+00:00'))
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                pass

        # Handle YYYY-MM-DD format (already correct)
        if len(value_str) >= 10 and value_str[4] == '-' and value_str[7] == '-':
            return value_str[:10]

        # Return as-is if can't parse
        return value_str

    def _transform_int(self, value: Any) -> Optional[int]:
        """Transform values to integer."""
        if value is None:
            return None

        try:
            return int(value)
        except (ValueError, TypeError):
            return None

    def _transform_list(self, value: Any, field_name: str) -> Optional[Union[List, str]]:
        """Transform list values."""
        if value is None:
            return None

        if not isinstance(value, list):
            return [value]

        # For keywords, return list of strings
        if field_name == 'keywords':
            return [str(item) for item in value]

        # For complex objects, extract relevant info
        if all(isinstance(item, dict) for item in value):
            # Person/Organization lists
            if field_name in ['creators', 'created_by', 'funders']:
                return [self._extract_name_from_entity(item) for item in value]

        return value

    def _transform_enum(self, value: Any, field_name: str) -> Optional[str]:
        """Transform enum values."""
        if value is None:
            return None

        # CompressionEnum values
        if field_name == 'compression':
            compression_map = {
                'gzip': 'GZIP',
                'tar': 'TAR',
                'zip': 'ZIP',
                'bzip2': 'BZIP2',
                'application/gzip': 'GZIP',
                'application/zip': 'ZIP',
                'application/x-tar': 'TAR',
            }
            value_lower = str(value).lower()
            for key, enum_value in compression_map.items():
                if key in value_lower:
                    return enum_value

        return str(value)

    def _transform_uri(self, value: Any) -> Optional[str]:
        """Transform URI values."""
        if value is None:
            return None

        value_str = str(value)

        # Ensure proper URI format
        if not value_str.startswith(('http://', 'https://', 'doi:', 'urn:')):
            # DOI special case
            if value_str.startswith('10.'):
                return f"https://doi.org/{value_str}"

        return value_str

    def _transform_person_org(self, value: Any) -> Optional[str]:
        """Transform Person/Organization entities to string representation."""
        if value is None:
            return None

        if isinstance(value, dict):
            return self._extract_name_from_entity(value)

        if isinstance(value, list):
            names = [self._extract_name_from_entity(item) for item in value if isinstance(item, dict)]
            return ', '.join(filter(None, names)) if names else None

        return str(value)

    def _transform_bool(self, value: Any) -> Optional[bool]:
        """Transform boolean values."""
        if value is None:
            return None

        if isinstance(value, bool):
            return value

        value_str = str(value).lower()
        if value_str in ['true', 'yes', '1']:
            return True
        elif value_str in ['false', 'no', '0']:
            return False

        return None

    def _extract_name_from_entity(self, entity: Dict[str, Any]) -> Optional[str]:
        """Extract name from Person or Organization entity."""
        if not isinstance(entity, dict):
            return None

        # Try common name fields
        for field in ['name', 'givenName', 'familyName', '@id']:
            if field in entity:
                if field == '@id' and entity['@id'].startswith(('http://', 'https://')):
                    continue  # Skip URLs
                return str(entity[field])

        # Combine givenName and familyName if both present
        given = entity.get('givenName')
        family = entity.get('familyName')
        if given and family:
            return f"{given} {family}"

        return None

    def set_field(self, field_name: str, value: Any):
        """
        Manually set a D4D field value.

        Args:
            field_name: D4D field name
            value: Value to set
        """
        self.d4d_data[field_name] = value

    def get_field(self, field_name: str) -> Optional[Any]:
        """
        Get a D4D field value.

        Args:
            field_name: D4D field name

        Returns:
            Field value, or None if not set
        """
        return self.d4d_data.get(field_name)

    def get_dataset(self) -> Dict[str, Any]:
        """
        Get the complete D4D dataset structure.

        Returns:
            Dict with D4D Dataset data
        """
        return self.d4d_data.copy()


if __name__ == "__main__":
    # Test the D4D builder
    import sys
    from mapping_loader import MappingLoader
    from rocrate_parser import ROCrateParser

    if len(sys.argv) < 3:
        print("Usage: python d4d_builder.py <mapping_tsv> <rocrate_json>")
        sys.exit(1)

    mapping = MappingLoader(sys.argv[1])
    parser = ROCrateParser(sys.argv[2])

    builder = D4DBuilder(mapping)
    dataset = builder.build_dataset(parser)

    print("\n=== Built D4D Dataset ===")
    print(f"Total fields: {len(dataset)}")
    print("\nSample fields:")
    for key in list(dataset.keys())[:10]:
        value = dataset[key]
        value_str = str(value)[:60]
        if len(str(value)) > 60:
            value_str += "..."
        print(f"  {key}: {value_str}")

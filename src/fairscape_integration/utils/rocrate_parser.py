#!/usr/bin/env python3
"""
RO-Crate Parser - Extract metadata from RO-Crate JSON-LD files.

This module parses RO-Crate JSON-LD structure and provides methods to extract
properties for transformation to D4D YAML format.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class ROCrateParser:
    """Parse and extract metadata from RO-Crate JSON-LD files."""

    def __init__(self, rocrate_path: str, verbose: bool = False):
        """
        Initialize RO-Crate parser with JSON-LD file.

        Args:
            rocrate_path: Path to RO-Crate JSON-LD file
            verbose: Print parsing information
        """
        self.rocrate_path = Path(rocrate_path)
        self.rocrate_data: Dict[str, Any] = {}
        self.context: Dict[str, Any] = {}
        self.graph: List[Dict[str, Any]] = []
        self.root_dataset: Optional[Dict[str, Any]] = None
        self.all_properties: Dict[str, Any] = {}
        self.verbose = verbose

        if not self.rocrate_path.exists():
            raise FileNotFoundError(f"RO-Crate file not found: {rocrate_path}")

        self._load_rocrate()

    def _load_rocrate(self):
        """Load and parse the RO-Crate JSON-LD file."""
        with open(self.rocrate_path, 'r', encoding='utf-8') as f:
            self.rocrate_data = json.load(f)

        # Extract @context
        self.context = self.rocrate_data.get('@context', {})

        # Extract @graph (array of entities)
        self.graph = self.rocrate_data.get('@graph', [])

        # Find root Dataset entity
        self.root_dataset = self._find_root_dataset()

        if self.root_dataset:
            # Flatten all properties with dot notation
            self.all_properties = self._flatten_properties(self.root_dataset)
            if self.verbose:
                print(f"Loaded RO-Crate with {len(self.all_properties)} flattened properties")
        else:
            if self.verbose:
                print("Warning: No root Dataset entity found in RO-Crate")

    def _find_root_dataset(self) -> Optional[Dict[str, Any]]:
        """
        Find the root Dataset entity in the @graph.

        Returns:
            Root Dataset dict, or None if not found
        """
        # First, check if there's a metadata descriptor that points to the root
        root_id = None
        for entity in self.graph:
            if entity.get('@id') == 'ro-crate-metadata.json':
                about = entity.get('about', {})
                if isinstance(about, dict) and '@id' in about:
                    root_id = about['@id']
                    break

        # Find the Dataset entity
        for entity in self.graph:
            entity_type = entity.get('@type', '')
            entity_id = entity.get('@id', '')

            # Root dataset typically has @type "Dataset" and @id "./" or similar
            if isinstance(entity_type, str):
                entity_types = [entity_type]
            else:
                entity_types = entity_type

            if 'Dataset' in entity_types or any('Dataset' in str(t) for t in entity_types):
                # Prefer entity pointed to by metadata descriptor
                if root_id and entity_id == root_id:
                    return entity
                # Prefer entity with @id "./" (root descriptor)
                if entity_id == './':
                    return entity
                # Fallback to first Dataset found
                if not self.root_dataset:
                    self.root_dataset = entity

        return self.root_dataset

    def _flatten_properties(self, obj: Any, prefix: str = "") -> Dict[str, Any]:
        """
        Recursively flatten nested properties to dot-notation paths.

        Args:
            obj: Object to flatten (dict, list, or primitive)
            prefix: Current property path prefix

        Returns:
            Dict with flattened property paths as keys
        """
        properties = {}

        if isinstance(obj, dict):
            for key, value in obj.items():
                # Skip @type and @id metadata
                if key in ['@type', '@id', '@context']:
                    continue

                new_key = f"{prefix}.{key}" if prefix else key

                # Store the direct value
                properties[new_key] = value

                # If value is complex, also flatten it
                if isinstance(value, (dict, list)):
                    nested = self._flatten_properties(value, new_key)
                    properties.update(nested)

        elif isinstance(obj, list):
            # For arrays, store the array itself and also each item
            properties[prefix] = obj
            for i, item in enumerate(obj):
                if isinstance(item, (dict, list)):
                    nested = self._flatten_properties(item, f"{prefix}[{i}]")
                    properties.update(nested)

        else:
            # Primitive value
            properties[prefix] = obj

        return properties

    def get_root_dataset(self) -> Optional[Dict[str, Any]]:
        """
        Get the root Dataset entity from the RO-Crate.

        Returns:
            Root Dataset dict, or None if not found
        """
        return self.root_dataset

    def get_property(self, property_path: str) -> Optional[Any]:
        """
        Get a property value using dot-notation path.

        Args:
            property_path: Property path (e.g., 'name', 'author[0].name', 'rai:dataCollection')

        Returns:
            Property value, or None if not found
        """
        # Try direct lookup first
        if property_path in self.all_properties:
            return self.all_properties[property_path]

        # Try navigating through nested structure
        current = self.root_dataset
        if not current:
            return None

        parts = property_path.split('.')
        for part in parts:
            if not isinstance(current, dict):
                return None

            # Handle array indexing (e.g., "author[0]")
            if '[' in part and ']' in part:
                key = part[:part.index('[')]
                index = int(part[part.index('[')+1:part.index(']')])
                current = current.get(key, [])
                if isinstance(current, list) and len(current) > index:
                    current = current[index]
                else:
                    return None
            else:
                current = current.get(part)

            if current is None:
                return None

        return current

    def extract_all_properties(self) -> Dict[str, Any]:
        """
        Get all flattened properties as a dictionary.

        Returns:
            Dict with dot-notation paths as keys, values as values
        """
        return self.all_properties.copy()

    def get_unmapped_properties(self, mapped_properties: set) -> Dict[str, Any]:
        """
        Get properties that exist in RO-Crate but are not in the mapping.

        Args:
            mapped_properties: Set of RO-Crate property names that have mappings

        Returns:
            Dict of unmapped properties with sample values
        """
        unmapped = {}

        for prop_path, value in self.all_properties.items():
            # Extract base property name (before any dots or brackets)
            base_prop = prop_path.split('.')[0].split('[')[0]

            if base_prop not in mapped_properties:
                # Store sample value (truncate if too long)
                sample_value = str(value)[:100]
                if len(str(value)) > 100:
                    sample_value += "..."
                unmapped[prop_path] = sample_value

        return unmapped

    def get_entity_by_id(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """
        Get an entity from @graph by its @id.

        Args:
            entity_id: The @id of the entity to find

        Returns:
            Entity dict, or None if not found
        """
        for entity in self.graph:
            if entity.get('@id') == entity_id:
                return entity
        return None

    def get_entities_by_type(self, entity_type: str) -> List[Dict[str, Any]]:
        """
        Get all entities of a specific @type from @graph.

        Args:
            entity_type: The @type to search for (e.g., 'Person', 'Organization')

        Returns:
            List of matching entities
        """
        matching = []
        for entity in self.graph:
            types = entity.get('@type', [])
            if isinstance(types, str):
                types = [types]
            if entity_type in types:
                matching.append(entity)
        return matching

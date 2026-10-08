#!/usr/bin/env python3
"""
RO-Crate Parser - Extract metadata from RO-Crate JSON-LD files.

This module parses RO-Crate JSON-LD structure and provides methods to extract
properties for transformation to D4D YAML format.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from data_sheets_schema.rocrate_map import TRANSCODE_HINT, read_crate_json
from data_sheets_schema.rocrate_sources import select_root


def graph_entities(graph: Any) -> Any:
    """The entities of a crate's `@graph`, as a list where it holds one.

    JSON-LD lets `@graph` be one node object as well as an array of them,
    and reads the object as an array that holds it. RO-Crate requires the
    array, but `ROCrateParser` and `fairscape-cli info` read any JSON-LD
    file they are given, and
    data/ro-crate_packages/VOICE/raw/ro-crate-prov-graph.json writes the
    object. Iterated as it stood, the object gave its keys, and both ended
    with `'str' object has no attribute 'get'` (#4187). Any other value is
    returned as it is.
    """
    return [graph] if isinstance(graph, dict) else graph


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
        self.context: Union[str, Dict[str, Any]] = {}
        self.graph: List[Dict[str, Any]] = []
        self.root_dataset: Optional[Dict[str, Any]] = None
        self.root_selection_reason = "RO-Crate has not been loaded"
        self.all_properties: Dict[str, Any] = {}
        self.verbose = verbose

        if not self.rocrate_path.exists():
            raise FileNotFoundError(f"RO-Crate file not found: {rocrate_path}")

        self._load_rocrate()

    def _load_rocrate(self):
        """Load and parse the RO-Crate JSON-LD file.

        Read as the static-map arm reads a crate (`read_crate_json`): JSON
        that is not UTF-8, as RFC 8259 requires, is refused with a
        CrateEncodingError naming the first byte that does not decode, and
        is not decoded under a guessed encoding. Opened as UTF-8 here,
        AI_READI's windows-1252 release crate ended `fairscape-cli parse`,
        `merge`, `rank` and `transform` with a bare UnicodeDecodeError
        (#4186). The parser takes any path, so the refusal ends by saying
        to transcode the file, as `fairscape-cli rocrate-to-d4d` and `info`
        end theirs, not by pointing to crate_manifest.yaml's
        `encoding_note` (#4192).
        """
        self.rocrate_data = read_crate_json(self.rocrate_path, hint=TRANSCODE_HINT)

        # Extract @context
        self.context = self.rocrate_data.get('@context', {})

        # Extract @graph: an array of entities, or one entity written as a
        # node object, read as an array that holds it (#4187)
        self.graph = graph_entities(self.rocrate_data.get('@graph', []))

        # Find root Dataset entity
        self.root_dataset = self._find_root_dataset()

        if self.root_dataset:
            # Flatten all properties with dot notation
            self.all_properties = self._flatten_properties(self.root_dataset)
            if self.verbose:
                print(f"Loaded RO-Crate with {len(self.all_properties)} flattened properties")
        else:
            if self.verbose:
                print(f"Warning: No unambiguous root Dataset entity: {self.root_selection_reason}")

    def _find_root_dataset(self) -> Optional[Dict[str, Any]]:
        """
        Find the root Dataset entity in the @graph.

        Returns:
            Root Dataset dict, or None if not found
        """
        # Keep the original entities, including duplicate IDs, until the
        # shared selector has checked them. Filtering or indexing first can
        # conceal a descriptor conflict or make a member look like the root.
        root, self.root_selection_reason = select_root(self.graph)
        return root

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

    def require_root_dataset(self) -> Dict[str, Any]:
        """Return the authoritative root, or refuse a production operation.

        Construction and ``get_root_dataset`` remain useful for inspection
        of empty or ambiguous graphs. Building, merging and ranking datasets
        must call this method before producing output.
        """
        if self.root_dataset is None:
            raise ValueError(
                f"{self.rocrate_path}: No unambiguous root data entity in the "
                f"RO-Crate `@graph`: {self.root_selection_reason}"
            )
        return self.root_dataset

    def get_all_entities(self) -> Dict[str, Dict[str, Any]]:
        """Inspect entities with usable IDs, without overwriting duplicates.

        Anonymous or malformed entries remain available in ``graph`` but
        cannot be represented in this ID-keyed view. Duplicate string IDs
        are refused, even for identical objects, to preserve their evidence.
        """
        entities = {}
        for entity in self.graph if isinstance(self.graph, list) else []:
            if not isinstance(entity, dict):
                continue
            identifier = entity.get('@id')
            if not isinstance(identifier, str) or not identifier.strip():
                continue
            if identifier in entities:
                raise ValueError(
                    f"{self.rocrate_path}: Duplicate entity @id {identifier!r} "
                    "cannot be represented in an ID-keyed entity view"
                )
            entities[identifier] = entity
        return entities

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
        for entity in self.graph if isinstance(self.graph, list) else []:
            if not isinstance(entity, dict):
                continue
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
        for entity in self.graph if isinstance(self.graph, list) else []:
            if not isinstance(entity, dict):
                continue
            types = entity.get('@type', [])
            if isinstance(types, str):
                types = [types]
            if not isinstance(types, list):
                continue
            if entity_type in types:
                matching.append(entity)
        return matching

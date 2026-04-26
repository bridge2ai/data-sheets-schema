#!/usr/bin/env python3
"""
Generate schema-structure-aware mappings between D4D and RO-Crate.

This script:
1. Parses D4D schema structure (inheritance, composition, modules)
2. Parses RO-Crate schema structure (properties, nesting, types)
3. Generates mappings that respect structural relationships
4. Validates type compatibility
5. Outputs SSSOM-compatible mappings
"""

import json
import yaml
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


class MappingPredicate(Enum):
    """SSSOM mapping predicates."""
    EXACT_MATCH = "skos:exactMatch"
    CLOSE_MATCH = "skos:closeMatch"
    BROAD_MATCH = "skos:broadMatch"
    NARROW_MATCH = "skos:narrowMatch"
    RELATED_MATCH = "skos:relatedMatch"


class MappingJustification(Enum):
    """SSSOM mapping justification categories."""
    STRUCTURAL = "semapv:StructuralMapping"  # Based on schema structure
    SEMANTIC = "semapv:SemanticSimilarity"   # Based on meaning
    LEXICAL = "semapv:LexicalSimilarity"     # Based on name similarity
    MANUAL = "semapv:ManualMappingCuration"  # Human curated


@dataclass
class SchemaClass:
    """Represents a class in a schema."""
    name: str
    description: str = ""
    is_a: Optional[str] = None  # Parent class
    module: Optional[str] = None
    attributes: Dict[str, 'SchemaSlot'] = field(default_factory=dict)
    class_uri: Optional[str] = None

    def get_ancestors(self, all_classes: Dict[str, 'SchemaClass']) -> List[str]:
        """Get all ancestor classes via is_a."""
        ancestors = []
        current = self.is_a
        while current and current in all_classes:
            ancestors.append(current)
            current = all_classes[current].is_a
        return ancestors


@dataclass
class SchemaSlot:
    """Represents a slot/attribute in a schema."""
    name: str
    description: str = ""
    range: Optional[str] = None  # Type or class reference
    slot_uri: Optional[str] = None
    multivalued: bool = False
    required: bool = False
    parent_class: Optional[str] = None

    def is_composition(self, all_classes: Dict[str, SchemaClass]) -> bool:
        """Check if this slot represents composition (range is a class)."""
        return self.range in all_classes

    def get_composition_path(self, all_classes: Dict[str, SchemaClass]) -> List[str]:
        """Get the composition path if this is a composed type."""
        if not self.is_composition(all_classes):
            return []
        path = [self.name]
        if self.range in all_classes:
            for attr in all_classes[self.range].attributes.values():
                path.append(f"{self.name}.{attr.name}")
        return path


@dataclass
class ROCrateProperty:
    """Represents a property in RO-Crate metadata."""
    name: str
    path: str  # Full JSON path
    value_type: str  # string, array, object, etc.
    namespace: Optional[str] = None  # evi, rai, d4d, schema, etc.
    sample_value: Optional[str] = None

    def get_namespace_prefix(self) -> Optional[str]:
        """Extract namespace prefix from property name."""
        if ':' in self.name:
            return self.name.split(':')[0]
        return None


@dataclass
class StructuralMapping:
    """Represents a schema-structure-aware mapping."""
    d4d_class: str
    d4d_slot: str
    d4d_slot_uri: Optional[str]
    d4d_range: Optional[str]
    d4d_multivalued: bool
    rocrate_property: str
    rocrate_path: str
    rocrate_type: str
    predicate: MappingPredicate
    justification: MappingJustification
    confidence: float  # 0.0 to 1.0
    structural_notes: str = ""
    composition_path: Optional[str] = None
    type_compatible: bool = True
    warnings: List[str] = field(default_factory=list)

    def to_sssom_row(self) -> Dict[str, str]:
        """Convert to SSSOM TSV row."""
        return {
            "subject_id": f"d4d:{self.d4d_class}/{self.d4d_slot}",
            "subject_label": self.d4d_slot,
            "subject_category": self.d4d_class,
            "predicate_id": self.predicate.value,
            "object_id": self.rocrate_property,
            "object_label": self.rocrate_path,
            "mapping_justification": self.justification.value,
            "confidence": str(self.confidence),
            "subject_source": "d4d:data_sheets_schema",
            "object_source": "rocrate:fairscape",
            "d4d_subject_range": self.d4d_range or "string",
            "subject_multivalued": str(self.d4d_multivalued),
            "rocrate_value_type": self.rocrate_type,
            "type_compatible": str(self.type_compatible),
            "composition_path": self.composition_path or "",
            "structural_notes": self.structural_notes,
            "warnings": "; ".join(self.warnings) if self.warnings else "",
        }


class D4DSchemaParser:
    """Parse D4D LinkML schema structure."""

    def __init__(self, schema_path: Path):
        self.schema_path = schema_path
        with open(schema_path) as f:
            self.schema = yaml.safe_load(f)

        self.classes: Dict[str, SchemaClass] = {}
        self.slots: Dict[str, SchemaSlot] = {}
        self.modules: Dict[str, List[str]] = {}  # module -> class names

        self._parse_schema()

    def _parse_schema(self):
        """Parse schema structure."""
        # Parse classes
        for class_name, class_def in self.schema.get("classes", {}).items():
            schema_class = SchemaClass(
                name=class_name,
                description=class_def.get("description", ""),
                is_a=class_def.get("is_a"),
                class_uri=class_def.get("class_uri"),
            )

            # Parse attributes
            for attr_name, attr_def in class_def.get("attributes", {}).items():
                slot = SchemaSlot(
                    name=attr_name,
                    description=attr_def.get("description", ""),
                    range=attr_def.get("range"),
                    slot_uri=attr_def.get("slot_uri"),
                    multivalued=attr_def.get("multivalued", False),
                    required=attr_def.get("required", False),
                    parent_class=class_name,
                )
                schema_class.attributes[attr_name] = slot
                self.slots[f"{class_name}.{attr_name}"] = slot

            self.classes[class_name] = schema_class

        # Parse module organization from imports and id
        schema_id = self.schema.get("id", "")
        if "motivation" in schema_id:
            module = "Motivation"
        elif "composition" in schema_id:
            module = "Composition"
        elif "collection" in schema_id:
            module = "Collection"
        elif "preprocessing" in schema_id:
            module = "Preprocessing"
        elif "uses" in schema_id:
            module = "Uses"
        elif "distribution" in schema_id:
            module = "Distribution"
        elif "maintenance" in schema_id:
            module = "Maintenance"
        else:
            module = "Core"

        for class_name in self.classes.keys():
            if module not in self.modules:
                self.modules[module] = []
            self.modules[module].append(class_name)

    def get_dataset_property_subclasses(self) -> List[SchemaClass]:
        """Get all classes that inherit from DatasetProperty."""
        subclasses = []
        for cls in self.classes.values():
            if cls.is_a == "DatasetProperty" or "DatasetProperty" in cls.get_ancestors(self.classes):
                subclasses.append(cls)
        return subclasses

    def get_composition_paths(self, class_name: str) -> Dict[str, List[str]]:
        """Get all composition paths from a class."""
        paths = {}
        if class_name not in self.classes:
            return paths

        cls = self.classes[class_name]
        for attr_name, attr in cls.attributes.items():
            if attr.is_composition(self.classes):
                paths[attr_name] = attr.get_composition_path(self.classes)
        return paths


class ROCrateSchemaParser:
    """Parse RO-Crate schema structure from FAIRSCAPE example."""

    def __init__(self, rocrate_path: Path):
        self.rocrate_path = rocrate_path
        with open(rocrate_path) as f:
            self.rocrate = json.load(f)

        self.properties: Dict[str, ROCrateProperty] = {}
        self._parse_structure()

    def _parse_structure(self):
        """Parse RO-Crate structure."""
        # Get the Dataset entity (second entity in @graph)
        graph = self.rocrate.get("@graph", [])
        if len(graph) < 2:
            return

        dataset = graph[1]
        self._extract_properties(dataset, "")

    def _extract_properties(self, obj: dict, path_prefix: str):
        """Recursively extract properties from JSON structure."""
        for key, value in obj.items():
            if key.startswith("@"):
                continue  # Skip @id, @type, etc.

            full_path = f"{path_prefix}.{key}" if path_prefix else key
            value_type = type(value).__name__

            # Extract namespace
            namespace = None
            if ':' in key:
                namespace = key.split(':')[0]

            # Get sample value
            sample_value = None
            if isinstance(value, str):
                sample_value = value[:100] if len(value) > 100 else value
            elif isinstance(value, list) and value:
                sample_value = str(value[0])[:100]

            prop = ROCrateProperty(
                name=key,
                path=full_path,
                value_type=value_type,
                namespace=namespace,
                sample_value=sample_value,
            )
            self.properties[full_path] = prop

            # Recurse into nested objects
            if isinstance(value, dict):
                self._extract_properties(value, full_path)
            elif isinstance(value, list) and value and isinstance(value[0], dict):
                self._extract_properties(value[0], f"{full_path}[]")

    def get_properties_by_namespace(self, namespace: str) -> List[ROCrateProperty]:
        """Get all properties in a namespace."""
        return [p for p in self.properties.values() if p.namespace == namespace]


class StructuralMappingGenerator:
    """Generate structure-aware mappings between D4D and RO-Crate."""

    def __init__(self, d4d_parser: D4DSchemaParser, rocrate_parser: ROCrateSchemaParser):
        self.d4d = d4d_parser
        self.rocrate = rocrate_parser
        self.mappings: List[StructuralMapping] = []

    def generate_mappings(self) -> List[StructuralMapping]:
        """Generate all structure-aware mappings."""
        # 1. Map based on slot_uri annotations (highest confidence)
        self._map_slot_uris()

        # 2. Map based on inheritance hierarchies
        self._map_dataset_property_hierarchy()

        # 3. Map based on composition paths
        self._map_composition_paths()

        # 4. Map based on module semantics
        self._map_module_semantics()

        # 5. Deduplicate mappings (keep highest confidence)
        self._deduplicate_mappings()

        return self.mappings

    def _deduplicate_mappings(self):
        """Remove duplicate mappings, keeping highest confidence."""
        seen = {}  # (d4d_class, d4d_slot, rocrate_property) -> mapping

        for mapping in self.mappings:
            key = (mapping.d4d_class, mapping.d4d_slot, mapping.rocrate_property)

            if key not in seen or mapping.confidence > seen[key].confidence:
                seen[key] = mapping

        self.mappings = list(seen.values())
        print(f"  Deduplicated to {len(self.mappings)} unique mappings")

    def _map_dataset_property_hierarchy(self):
        """Map classes that inherit from DatasetProperty."""
        dataset_props = self.d4d.get_dataset_property_subclasses()

        for cls in dataset_props:
            # DatasetProperty subclasses map to top-level RO-Crate properties
            for attr_name, attr in cls.attributes.items():
                # Look for matching RO-Crate properties
                self._create_hierarchical_mapping(cls, attr)

    def _create_hierarchical_mapping(self, cls: SchemaClass, slot: SchemaSlot):
        """Create mapping considering class hierarchy."""
        # Find RO-Crate properties that might match
        candidates = self._find_rocrate_candidates(slot.name, slot.slot_uri)

        for rocrate_prop in candidates:
            # Calculate semantic similarity
            similarity = self._semantic_similarity(slot.name, rocrate_prop.name)

            # Only create mapping if similarity is high enough
            if similarity < 0.85:
                continue

            # Validate type compatibility
            type_compat, warnings = self._validate_type_compatibility(slot, rocrate_prop)

            # Skip if types are incompatible
            if not type_compat:
                continue

            mapping = StructuralMapping(
                d4d_class=cls.name,
                d4d_slot=slot.name,
                d4d_slot_uri=slot.slot_uri,
                d4d_range=slot.range,
                d4d_multivalued=slot.multivalued,
                rocrate_property=rocrate_prop.name,
                rocrate_path=rocrate_prop.path,
                rocrate_type=rocrate_prop.value_type,
                predicate=MappingPredicate.EXACT_MATCH if similarity >= 0.95 else MappingPredicate.CLOSE_MATCH,
                justification=MappingJustification.STRUCTURAL,
                confidence=similarity,
                structural_notes=f"Mapped via DatasetProperty hierarchy from {cls.name}",
                type_compatible=type_compat,
                warnings=warnings,
            )
            self.mappings.append(mapping)

    def _map_composition_paths(self):
        """Map nested composition structures."""
        # Example: Creator.principal_investigator (Person) -> principalInvestigator
        for class_name, cls in self.d4d.classes.items():
            comp_paths = self.d4d.get_composition_paths(class_name)

            for attr_name, paths in comp_paths.items():
                # Find matching RO-Crate nested structures
                for path in paths:
                    rocrate_candidates = [
                        p for p in self.rocrate.properties.values()
                        if attr_name.lower() in p.path.lower()
                    ]

                    for rocrate_prop in rocrate_candidates:
                        mapping = StructuralMapping(
                            d4d_class=class_name,
                            d4d_slot=path.split('.')[-1],
                            d4d_slot_uri=None,
                            d4d_range=None,
                            d4d_multivalued=False,
                            rocrate_property=rocrate_prop.name,
                            rocrate_path=rocrate_prop.path,
                            rocrate_type=rocrate_prop.value_type,
                            predicate=MappingPredicate.CLOSE_MATCH,
                            justification=MappingJustification.STRUCTURAL,
                            confidence=0.7,
                            composition_path=path,
                            structural_notes=f"Composition path: {path}",
                            type_compatible=True,
                        )
                        self.mappings.append(mapping)

    def _map_module_semantics(self):
        """Map entire D4D modules to RO-Crate sections."""
        module_to_namespace = {
            "Motivation": ["d4d", "schema"],
            "Composition": ["d4d", "schema"],
            "Collection": ["rai", "schema"],
            "Preprocessing": ["rai"],
            "Uses": ["d4d", "schema"],
        }

        for module, namespaces in module_to_namespace.items():
            if module not in self.d4d.modules:
                continue

            for namespace in namespaces:
                rocrate_props = self.rocrate.get_properties_by_namespace(namespace)

                # Create module-level mappings
                for class_name in self.d4d.modules[module]:
                    if class_name not in self.d4d.classes:
                        continue

                    cls = self.d4d.classes[class_name]
                    for attr in cls.attributes.values():
                        # Try to match with namespace properties
                        for rocrate_prop in rocrate_props:
                            similarity = self._semantic_similarity(attr.name, rocrate_prop.name)

                            # Require high similarity for module-based mappings
                            if similarity < 0.85:
                                continue

                            type_compat, warnings = self._validate_type_compatibility(attr, rocrate_prop)

                            # Skip if types incompatible
                            if not type_compat:
                                continue

                            mapping = StructuralMapping(
                                d4d_class=class_name,
                                d4d_slot=attr.name,
                                d4d_slot_uri=attr.slot_uri,
                                d4d_range=attr.range,
                                d4d_multivalued=attr.multivalued,
                                rocrate_property=rocrate_prop.name,
                                rocrate_path=rocrate_prop.path,
                                rocrate_type=rocrate_prop.value_type,
                                predicate=MappingPredicate.EXACT_MATCH if similarity >= 0.95 else MappingPredicate.CLOSE_MATCH,
                                justification=MappingJustification.STRUCTURAL,
                                confidence=similarity,
                                structural_notes=f"Module mapping: {module} -> {namespace} namespace",
                                type_compatible=type_compat,
                                warnings=warnings,
                            )
                            self.mappings.append(mapping)

    def _map_slot_uris(self):
        """Map based on existing slot_uri annotations."""
        for slot_key, slot in self.d4d.slots.items():
            if not slot.slot_uri:
                continue

            # Find RO-Crate properties with matching namespace
            namespace = slot.slot_uri.split(':')[0] if ':' in slot.slot_uri else None

            if namespace:
                rocrate_props = self.rocrate.get_properties_by_namespace(namespace)
                for rocrate_prop in rocrate_props:
                    if slot.slot_uri in rocrate_prop.name or slot.name in rocrate_prop.name:
                        type_compat, warnings = self._validate_type_compatibility(slot, rocrate_prop)

                        mapping = StructuralMapping(
                            d4d_class=slot.parent_class or "Unknown",
                            d4d_slot=slot.name,
                            d4d_slot_uri=slot.slot_uri,
                            d4d_range=slot.range,
                            d4d_multivalued=slot.multivalued,
                            rocrate_property=rocrate_prop.name,
                            rocrate_path=rocrate_prop.path,
                            rocrate_type=rocrate_prop.value_type,
                            predicate=MappingPredicate.EXACT_MATCH if type_compat else MappingPredicate.CLOSE_MATCH,
                            justification=MappingJustification.SEMANTIC,
                            confidence=0.9 if type_compat else 0.6,
                            structural_notes=f"slot_uri mapping: {slot.slot_uri}",
                            type_compatible=type_compat,
                            warnings=warnings,
                        )
                        self.mappings.append(mapping)

    def _find_rocrate_candidates(self, slot_name: str, slot_uri: Optional[str]) -> List[ROCrateProperty]:
        """Find RO-Crate properties that might match this slot."""
        candidates = []
        seen = set()  # Deduplicate

        # Match by name similarity (only high confidence)
        for prop in self.rocrate.properties.values():
            similarity = self._semantic_similarity(slot_name, prop.name)
            if similarity > 0.85 and prop.path not in seen:
                candidates.append(prop)
                seen.add(prop.path)

        # Match by URI namespace (if URI provided and no name matches found)
        if slot_uri and ':' in slot_uri and not candidates:
            namespace = slot_uri.split(':')[0]
            namespace_props = self.rocrate.get_properties_by_namespace(namespace)
            for prop in namespace_props:
                if prop.path not in seen:
                    # Still require some semantic similarity even for namespace match
                    if self._semantic_similarity(slot_name, prop.name) > 0.6:
                        candidates.append(prop)
                        seen.add(prop.path)

        return candidates

    def _semantic_similarity(self, name1: str, name2: str) -> float:
        """Calculate semantic similarity between names (simplified)."""
        name1_lower = name1.lower().replace('_', '').replace('-', '')
        name2_lower = name2.lower().replace('_', '').replace('-', '').replace(':', '')

        # Exact match
        if name1_lower == name2_lower:
            return 1.0

        # Substring match
        if name1_lower in name2_lower or name2_lower in name1_lower:
            return 0.8

        # Word overlap
        words1 = set(name1_lower.split())
        words2 = set(name2_lower.split())
        if words1 and words2:
            overlap = len(words1 & words2) / max(len(words1), len(words2))
            return overlap

        return 0.0

    def _validate_type_compatibility(self, d4d_slot: SchemaSlot, rocrate_prop: ROCrateProperty) -> Tuple[bool, List[str]]:
        """Validate that D4D and RO-Crate types are compatible."""
        warnings = []

        # Check for known incompatibilities
        if d4d_slot.range == "boolean" and rocrate_prop.value_type == "dict":
            warnings.append("Type mismatch: boolean cannot map to object/relationship")
            return False, warnings

        if d4d_slot.range == "boolean" and "date" in rocrate_prop.name.lower():
            warnings.append("Type mismatch: boolean cannot map to date property")
            return False, warnings

        if d4d_slot.multivalued and rocrate_prop.value_type != "list":
            warnings.append("Cardinality mismatch: multivalued slot mapping to single value")
            return False, warnings

        # Check semantic domain mismatches
        relationship_keywords = ["derived", "related", "references", "requires"]
        if d4d_slot.range in ["string", "boolean", "integer", "float"]:
            if any(kw in rocrate_prop.name.lower() for kw in relationship_keywords):
                warnings.append(f"Semantic mismatch: literal value mapping to relationship property")
                return False, warnings

        return True, warnings

    def export_sssom(self, output_path: Path):
        """Export mappings to SSSOM TSV format."""
        if not self.mappings:
            print("No mappings to export")
            return

        # Get all column names from first mapping
        columns = list(self.mappings[0].to_sssom_row().keys())

        with open(output_path, 'w') as f:
            # Write header
            f.write('\t'.join(columns) + '\n')

            # Write mappings
            for mapping in self.mappings:
                row = mapping.to_sssom_row()
                f.write('\t'.join(row.get(col, '') for col in columns) + '\n')

        print(f"Exported {len(self.mappings)} mappings to {output_path}")

    def export_summary(self, output_path: Path):
        """Export human-readable summary."""
        with open(output_path, 'w') as f:
            f.write("# D4D to RO-Crate Schema-Structure-Aware Mapping Summary\n\n")

            # Group by justification
            by_justification = {}
            for mapping in self.mappings:
                just = mapping.justification.name
                if just not in by_justification:
                    by_justification[just] = []
                by_justification[just].append(mapping)

            for just, maps in by_justification.items():
                f.write(f"\n## {just} Mappings ({len(maps)})\n\n")

                for mapping in maps[:10]:  # Show first 10
                    f.write(f"- **{mapping.d4d_class}.{mapping.d4d_slot}** → **{mapping.rocrate_property}**\n")
                    f.write(f"  - Confidence: {mapping.confidence}\n")
                    f.write(f"  - Type compatible: {mapping.type_compatible}\n")
                    f.write(f"  - Notes: {mapping.structural_notes}\n")
                    if mapping.warnings:
                        f.write(f"  - ⚠️ Warnings: {'; '.join(mapping.warnings)}\n")
                    f.write("\n")

                if len(maps) > 10:
                    f.write(f"... and {len(maps) - 10} more\n\n")

        print(f"Exported summary to {output_path}")


def main():
    """Generate schema-structure-aware mappings."""
    # Paths
    base_dir = Path(__file__).parent.parent.parent
    d4d_schema = base_dir / "src/data_sheets_schema/schema/data_sheets_schema_all.yaml"
    rocrate_example = base_dir / "data/ro-crate/profiles/fairscape/full-ro-crate-metadata.json"
    output_dir = base_dir / "data/semantic_exchange"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Parse schemas
    print("Parsing D4D schema structure...")
    d4d_parser = D4DSchemaParser(d4d_schema)
    print(f"  Found {len(d4d_parser.classes)} classes")
    print(f"  Found {len(d4d_parser.slots)} slots")
    print(f"  Found {len(d4d_parser.modules)} modules")

    print("\nParsing RO-Crate schema structure...")
    rocrate_parser = ROCrateSchemaParser(rocrate_example)
    print(f"  Found {len(rocrate_parser.properties)} properties")

    # Generate mappings
    print("\nGenerating structure-aware mappings...")
    generator = StructuralMappingGenerator(d4d_parser, rocrate_parser)
    mappings = generator.generate_mappings()
    print(f"  Generated {len(mappings)} mappings")

    # Export
    print("\nExporting mappings...")
    generator.export_sssom(output_dir / "d4d_rocrate_structural_mapping.sssom.tsv")
    generator.export_summary(output_dir / "d4d_rocrate_structural_mapping_summary.md")

    print("\n✓ Schema-structure-aware mapping complete")


if __name__ == "__main__":
    main()

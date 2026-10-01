#!/usr/bin/env python3
"""
Generate schema-structure-aware mappings between D4D and RO-Crate.

This script:
1. Parses D4D schema structure (inheritance, composition)
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
            # An unknown range is left empty, never written as "string": that
            # placeholder read as schema data on every composition row (#2936).
            "d4d_subject_range": self.d4d_range or "",
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

    def resolve_path(self, class_name: str, path: str) -> SchemaSlot:
        """The slot a dotted composition path reaches from `class_name`, as one slot.

        Range and slot_uri are the last segment's, so the bare root path
        `anomalies` is `DataAnomaly` and `anomalies.id` is `uriorcurie`.
        Multivalued is True when *any* segment is: `anomalies.name` is a
        single string per anomaly, but there is one per entry of a list, so
        the value the path reaches from a `Dataset` is a list (#2936).
        """
        segments = []
        owner = class_name
        for name in path.split("."):
            cls = self.classes.get(owner)
            if cls is None or name not in cls.attributes:
                raise ValueError(
                    f"{class_name}.{path}: {name!r} is not an attribute of "
                    f"{owner!r} in {self.schema_path}")
            segments.append(cls.attributes[name])
            owner = segments[-1].range
        leaf = segments[-1]
        return SchemaSlot(
            name=path,
            description=leaf.description,
            range=leaf.range,
            slot_uri=leaf.slot_uri,
            multivalued=any(s.multivalued for s in segments),
            required=all(s.required for s in segments),
            parent_class=class_name,
        )


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

        # There is no module strategy (#3363). One mapped every attribute of
        # the classes in a D4D module to the properties of that module's
        # RO-Crate namespaces, and never emitted a row: the merged schema gave
        # every class one module, and with each class given its own module it
        # still emits none, because its 0.85 name-similarity cut admits only
        # an exact match and every candidate's name keeps its namespace
        # prefix (`rai:dataBiases` compares as `raidatabiases`).

        # 4. Deduplicate mappings (keep highest confidence)
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
        # A property is kept only where its path contains the slot name, so
        # e.g. Creator.principal_investigator comes from the hierarchy
        # strategy, not from here (#2976).
        for class_name, cls in self.d4d.classes.items():
            comp_paths = self.d4d.get_composition_paths(class_name)

            for attr_name, paths in comp_paths.items():
                # Find matching RO-Crate nested structures
                for path in paths:
                    # What the schema says the path reaches. These rows were
                    # written with range None (emitted as "string"),
                    # multivalued False and type_compatible True, whatever
                    # the path was (#2936).
                    slot = self.d4d.resolve_path(class_name, path)
                    rocrate_candidates = [
                        p for p in self.rocrate.properties.values()
                        if attr_name.lower() in p.path.lower()
                    ]

                    for rocrate_prop in rocrate_candidates:
                        type_compat, warnings = self._validate_type_compatibility(slot, rocrate_prop)
                        # Kept and flagged when incompatible, as `_map_slot_uris`
                        # does, rather than skipped as the hierarchy strategy
                        # does: skipping would silently delete rows the
                        # committed file carries.
                        mapping = StructuralMapping(
                            d4d_class=class_name,
                            # The whole path, not its last segment (#410).
                            # `anomalies.id` reached through composition became
                            # subject `d4d:Dataset/id`, which is also the id of
                            # `Dataset`'s *own* `id` slot — so the row read as
                            # "the Dataset's id closely matches an anomaly",
                            # which is false. What distinguished them survived
                            # only in the free-text `structural_notes` column,
                            # which nothing reads.
                            d4d_slot=path,
                            d4d_slot_uri=slot.slot_uri,
                            d4d_range=slot.range,
                            d4d_multivalued=slot.multivalued,
                            rocrate_property=rocrate_prop.name,
                            rocrate_path=rocrate_prop.path,
                            rocrate_type=rocrate_prop.value_type,
                            predicate=MappingPredicate.CLOSE_MATCH,
                            justification=MappingJustification.STRUCTURAL,
                            confidence=0.7,
                            composition_path=path,
                            structural_notes=f"Composition path: {path}",
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


TRIPLE = ("subject_id", "predicate_id", "object_id")

#: Columns that state what the schema says about a subject, or whether the
#: mapping was checked. Unlike confidence or notes, a wrong value here is a
#: wrong claim: composition rows carried the generator's placeholders in all
#: three and a triple-only check could not see it (#2936).
STRUCTURAL_COLUMNS = ("d4d_subject_range", "subject_multivalued",
                      "type_compatible")

#: Rows the committed mapping asserts that regeneration does not produce
#: (#234), each under what is wrong with it; #294 is the work that would
#: derive them. `--check` (`make check-sssom-structural`) accepts exactly
#: these and tests/test_semantic_exchange/test_structural_mapping_drift.py
#: pins exactly these, both from this one set (#3968). The check compares
#: none of their columns, since regeneration has no row to compare them
#: with (#4050). Regeneration cannot produce them, so rewriting the table
#: drops them, which is why `make gen-sssom-all` does not run the
#: structural target (#3967). Shrinking the set is progress. Growing it
#: without a reason is the drift both exist to catch.
KNOWN_UNDERIVABLE = frozenset({
    # No class-level strategy exists — `class_uri` is parsed and never used.
    ("d4d:CoreDataset", "skos:exactMatch", "schema:Dataset"),
    ("d4d:CoreDatasetCollection", "skos:exactMatch", "schema:Dataset"),
    ("d4d:CoreDistribution", "skos:exactMatch", "schema:DataDownload"),
    ("d4d:DataSubset", "skos:exactMatch", "schema:Dataset"),
    # No `schema:` targets are produced.
    ("d4d:DatasetCollection/resources", "skos:exactMatch", "schema:hasPart"),
    ("d4d:FileCollection/resources", "skos:exactMatch", "schema:hasPart"),
    # Target absent from the RO-Crate input, so `_map_slot_uris` cannot match.
    ("d4d:File/file_type", "skos:exactMatch", "d4d:fileType"),
    ("d4d:FileCollection/collection_type", "skos:exactMatch", "d4d:collectionType"),
    ("d4d:FileCollection/file_count", "skos:exactMatch", "d4d:fileCount"),
    # Also disagrees with the schema, which declares `slot_uri: d4d:total_bytes`.
    ("d4d:FileCollection/total_bytes", "skos:exactMatch", "dcat:byteSize"),
})


def _read_sssom(path: Path, required: tuple) -> list:
    import csv
    with path.open(encoding="utf-8") as fh:
        lines = [l for l in fh if not l.startswith("#")]
    reader = csv.DictReader(lines, delimiter="\t")
    missing = [c for c in required if c not in (reader.fieldnames or [])]
    if missing:
        # Naming the file and the column, because the alternative is a bare
        # KeyError from inside csv and a reader who concludes the code is
        # broken rather than the input (#296).
        raise ValueError(
            f"{path} is not a readable SSSOM mapping: no "
            f"{', '.join(missing)} column"
            + (" (no header row at all?)" if not reader.fieldnames else ""))
    return list(reader)


def read_sssom_rows(path: Path) -> set:
    """(subject_id, predicate_id, object_id) for every data row.

    Identity is the triple, not the whole line: confidence and structural notes
    move for reasons that are not a change of meaning, and a drift check that
    fires on those is one nobody keeps running.
    """
    return {tuple(r[c] for c in TRIPLE) for r in _read_sssom(path, TRIPLE)}


def check_drift(committed: Path, regenerated: Path) -> tuple:
    """Rows the committed file has that regeneration does not, and vice versa."""
    have, made = read_sssom_rows(committed), read_sssom_rows(regenerated)
    return sorted(have - made), sorted(made - have)


def check_column_drift(committed: Path, regenerated: Path,
                       columns: tuple = STRUCTURAL_COLUMNS) -> tuple:
    """How many rows both files carry, and where their `columns` disagree.

    Compared per triple, so a row only one file has is `check_drift`'s to
    report, not this. Each difference is (triple, column, committed value,
    regenerated value).
    """
    def by_triple(path):
        return {tuple(r[c] for c in TRIPLE): r
                for r in _read_sssom(path, TRIPLE + tuple(columns))}
    have, made = by_triple(committed), by_triple(regenerated)
    shared = sorted(have.keys() & made.keys())
    differ = [(t, c, have[t][c], made[t][c])
              for t in shared for c in columns if have[t][c] != made[t][c]]
    return len(shared), differ


def check_known_gap(committed: Path, regenerated: Path, known) -> tuple:
    """The committed rows regeneration does not produce, held to `known`.

    Four sorted lists of triples. `gap`: the rows `known` lists that the
    committed file carries and regeneration does not produce, which is the
    part accepted. `unlisted`: the rows the committed file carries and
    regeneration does not produce that `known` does not list. `missing`: the
    rows `known` lists that neither the committed file nor regeneration has.
    `derivable`: the rows `known` lists that regeneration produces.

    The rows regeneration does not produce are exactly `known` only when the
    last three are empty (#3968). `missing` is how a table the generator
    rewrote shows: it regenerates exactly, and it has lost every curated
    row (#3967).
    """
    have, made = read_sssom_rows(committed), read_sssom_rows(regenerated)
    lost = have - made
    return (sorted(lost & known), sorted(lost - known),
            sorted(known - have - made), sorted(known & made))


def run_check(generator, committed: Path, summary: Path, known) -> int:
    """`--check`: compare `committed` and `summary` with what `generator`
    regenerates, print what differs, and return the exit status.

    Three things are compared, and nothing else (#4050):

    - the rows, as a set of (subject, predicate, object) triples, so
      neither their order nor a repeated triple is seen;
    - STRUCTURAL_COLUMNS (`d4d_subject_range`, `subject_multivalued`,
      `type_compatible`) on the rows both files carry, reading the last row
      of a repeated triple; a change to any other column, such as
      `confidence`, `warnings` or `rocrate_value_type`, passes;
    - the summary's whole text, read in text mode, so its line endings are
      not compared.

    A difference in any of them fails, except that the rows the committed
    mapping carries and regeneration does not produce must be exactly
    `known`, which `main` passes as KNOWN_UNDERIVABLE (#3968): those are
    named and accepted, and no column of an accepted row is compared, since
    regeneration has no row to compare it with.

    Writes nothing beside them: regeneration goes to a temporary directory.
    """
    # Never write over the committed file while checking it. Regenerating
    # in place to compare is how a check becomes the thing it was meant to
    # detect.
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        scratch = Path(tmp) / "regenerated.sssom.tsv"
        generator.export_sssom(scratch)
        if not committed.exists():
            print(f"\n✗ No committed mapping at {committed}")
            return 1
        _, gained = check_drift(committed, scratch)
        gap, unlisted, missing, derivable = check_known_gap(
            committed, scratch, known)
        compared, column_drift = check_column_drift(committed, scratch)

        # The target writes two artifacts from the same mappings list, so
        # check both. Today the summary is fresh and the mapping is stale
        # (#295) — the confusing direction, because the artifact that is
        # right is the one nobody thinks to distrust.
        scratch_summary = Path(tmp) / "regenerated_summary.md"
        generator.export_summary(scratch_summary)
        summary_missing = not summary.exists()
        summary_drifted = (
            summary_missing
            or summary.read_text(encoding="utf-8")
            != scratch_summary.read_text(encoding="utf-8"))
    # Said on a pass as well as a failure. Before #2936 a pass printed
    # only the line below, from a check that compared triples alone, so
    # without this a column check that found nothing reads exactly like
    # one that never ran (#3057).
    agree = (f"\n  The {compared} row(s) both files carry agree on "
             f"{', '.join(STRUCTURAL_COLUMNS)}.")
    # The known gap is accepted, not hidden: it is listed on a pass too, so
    # a check that is green still says what regeneration cannot rebuild.
    # Before #3968 the check failed on it, so it was red on main by design
    # and only the drift test, which allowed exactly these rows, could tell
    # new drift from the gap.
    apart = f"apart from the {len(gap)} row(s) KNOWN_UNDERIVABLE lists"

    def print_gap():
        if gap:
            print(f"\n  {len(gap)} row(s) in the committed file that "
                  "regeneration does not produce, listed with their reasons "
                  "in KNOWN_UNDERIVABLE in generate_structural_mapping.py "
                  "(#294):")
            for s, p_, o in gap:
                print(f"      {s}  --{p_}->  {o}")

    # Drift from regeneration and a gap that is not the declared one are
    # told apart: a table the generator rewrote regenerates exactly, and
    # fails only for the curated rows it dropped (#3967).
    mapping_drifted = bool(unlisted or gained or column_drift)
    gap_drifted = bool(missing or derivable)
    if not mapping_drifted and not gap_drifted and not summary_drifted:
        if gap:
            print(f"\n✓ The committed mapping regenerates {apart}, and the "
                  "summary regenerates exactly.")
            print_gap()
            print(agree)
            print("\n  The summary describes the generator's output, so not "
                  f"those {len(gap)} row(s) (#295).")
        else:
            print("\n✓ The committed mapping and summary regenerate exactly.")
            print(agree)
        return 0
    # The headline names what drifted. It used to blame the mapping
    # whatever failed, so a stale summary beside a mapping that
    # regenerates exactly read as a mapping failure (#3125).
    if mapping_drifted:
        print("\n✗ The committed mapping does not regenerate from its inputs.")
    elif gap_drifted:
        print("\n✗ The rows regeneration does not produce are not exactly "
              "the ones KNOWN_UNDERIVABLE lists.")
    elif summary_missing:
        print(f"\n✗ No committed summary at {summary}.")
    else:
        print("\n✗ The committed summary does not regenerate from the "
              "mapping's inputs.")
    if unlisted:
        print(f"\n  {len(unlisted)} row(s) in the committed file that "
              "regeneration does not produce and KNOWN_UNDERIVABLE does not "
              "list:")
        for s, p_, o in unlisted:
            print(f"      {s}  --{p_}->  {o}")
    if gained:
        print(f"\n  {len(gained)} row(s) regeneration produces that the "
              "committed file lacks:")
        for s, p_, o in gained:
            print(f"      {s}  --{p_}->  {o}")
    if missing:
        print(f"\n  {len(missing)} row(s) KNOWN_UNDERIVABLE lists that the "
              "committed file does not carry:")
        for s, p_, o in missing:
            print(f"      {s}  --{p_}->  {o}")
        print("  Regeneration cannot produce them, so a table the generator "
              "rewrote lacks them (#3967). Restore their lines from git; if "
              "one is wrong, take it out of KNOWN_UNDERIVABLE and say why.")
    if derivable:
        print(f"\n  {len(derivable)} row(s) KNOWN_UNDERIVABLE lists that "
              "regeneration now produces:")
        for s, p_, o in derivable:
            print(f"      {s}  --{p_}->  {o}")
        print("  They are no longer a gap: take them out of "
              "KNOWN_UNDERIVABLE (#294).")
    print_gap()
    if column_drift:
        print(f"\n  {len(column_drift)} value(s) differ on the {compared} "
              "row(s) both files carry:")
        for (s, p_, o), col, was, now in column_drift:
            print(f"      {s}  --{p_}->  {o}  {col}: "
                  f"committed {was!r}, regenerated {now!r}")
    else:
        print(agree)
    drifted = mapping_drifted or gap_drifted
    if not drifted and summary_missing:
        regenerates = f"regenerates {apart}" if gap else "regenerates exactly"
        print(f"\n  The mapping {regenerates}; the summary beside it is "
              "missing.")
    elif not drifted:
        # Reached only with the summary stale: the pass returned above.
        does = f"regenerates {apart}" if gap else "does"
        print("\n  The summary does not regenerate. The mapping beside it "
              f"{does}, so only the summary is stale.")
    elif summary_missing:
        print(f"\n  There is no committed summary either, at {summary}.")
    elif summary_drifted:
        print("\n  The summary does not regenerate either.")
    elif mapping_drifted:
        print("\n  The summary regenerates exactly, so it describes the "
              "generator's output rather than the mapping beside it (#295).")
    else:
        # Only the gap differs, so the mapping may be the generator's own
        # output written over the curated rows (#3967), and "rather than the
        # mapping beside it" would be false.
        print("\n  The summary regenerates exactly.")
    if mapping_drifted:
        print("\n  A mapping nobody can rebuild is a mapping nobody can "
              "safely change (#234).")
    return 1


def main(argv=None):
    """Generate schema-structure-aware mappings."""
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    # The columns are read from the constant the check compares, so this
    # cannot name others (#4050).
    ap.add_argument("--check", action="store_true",
                    help="Regenerate to a temporary directory and report "
                         "drift against the committed mapping and summary. "
                         "Writes nothing. Compares the rows by subject, "
                         "predicate and object; "
                         f"{', '.join(STRUCTURAL_COLUMNS)} on the rows both "
                         "carry; and the summary's whole text. Exits non-zero "
                         "on a difference in any of them, except the rows "
                         "KNOWN_UNDERIVABLE lists, which the committed "
                         "mapping must carry and regeneration cannot "
                         "produce. Compares no other column, and no column "
                         "of a KNOWN_UNDERIVABLE row.")
    # The inputs stay fixed; only where the two artifacts live can move. That
    # is what lets a test run the check on a copy of the mapping it has
    # changed, which is the only way to see what `--check` does with a
    # difference while the committed file carries none (#2999).
    ap.add_argument("--output-dir", type=Path, default=None,
                    help="Directory the mapping and its summary are written "
                         "to, or read from with --check "
                         "(default: data/semantic_exchange).")
    args = ap.parse_args(argv)

    # Paths
    base_dir = Path(__file__).parent.parent.parent
    d4d_schema = base_dir / "src/data_sheets_schema/schema/data_sheets_schema_all.yaml"
    rocrate_example = base_dir / "data/ro-crate/profiles/fairscape/full-ro-crate-metadata.json"
    output_dir = args.output_dir or base_dir / "data/semantic_exchange"

    # Parse schemas
    print("Parsing D4D schema structure...")
    d4d_parser = D4DSchemaParser(d4d_schema)
    print(f"  Found {len(d4d_parser.classes)} classes")
    print(f"  Found {len(d4d_parser.slots)} slots")

    print("\nParsing RO-Crate schema structure...")
    rocrate_parser = ROCrateSchemaParser(rocrate_example)
    print(f"  Found {len(rocrate_parser.properties)} properties")

    # Generate mappings
    print("\nGenerating structure-aware mappings...")
    generator = StructuralMappingGenerator(d4d_parser, rocrate_parser)
    mappings = generator.generate_mappings()
    print(f"  Generated {len(mappings)} mappings")

    committed = output_dir / "d4d_rocrate_structural_mapping.sssom.tsv"
    summary = output_dir / "d4d_rocrate_structural_mapping_summary.md"

    if args.check:
        # The module's set is read when the check runs, not bound as a
        # default of `run_check`, so a test can run `main` with another
        # (#3968).
        return run_check(generator, committed, summary, KNOWN_UNDERIVABLE)

    # Export. The directory is made here rather than up front, so `--check`
    # pointed at one that does not exist creates nothing either.
    print("\nExporting mappings...")
    output_dir.mkdir(parents=True, exist_ok=True)
    generator.export_sssom(committed)
    generator.export_summary(summary)

    print("\n✓ Schema-structure-aware mapping complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

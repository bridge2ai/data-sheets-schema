#!/usr/bin/env python3
"""
Generate extended schema statistics from SchemaView.

Extracts additional SchemaView data not in the basic stats:
- Type system details
- Enum permissible values
- Class metadata (URIs, mixins, direct vs inherited slots)
- Slot metadata (URIs, mappings, aliases)
- Schema metadata

Usage:
    python .claude/agents/scripts/schema_stats_extended.py
"""

import csv
from pathlib import Path
from linkml_runtime.utils.schemaview import SchemaView


def find_full_schema() -> Path:
    """Auto-detect the full merged schema file."""
    script_dir = Path(__file__).parent.resolve()
    repo_root = script_dir.parent.parent.parent
    schema_path = repo_root / "src" / "data_sheets_schema" / "schema" / "data_sheets_schema_all.yaml"

    if not schema_path.exists():
        raise FileNotFoundError(f"Full schema not found at {schema_path}")

    return schema_path


def write_tsv(output_path: Path, headers: list, rows: list):
    """Write data to TSV file."""
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, delimiter='\t')
        writer.writerow(headers)
        writer.writerows(rows)
    print(f"  ✓ Created: {output_path.name} ({len(rows)} rows)")


def export_type_system(sv: SchemaView, output_dir: Path):
    """Export type system details."""
    rows = []
    for type_name in sorted(sv.all_types()):
        type_def = sv.get_type(type_name)
        if type_def:
            rows.append([
                type_name,
                type_def.typeof if type_def.typeof else "base type",
                type_def.uri if type_def.uri else "",
                type_def.description if type_def.description else ""
            ])

    write_tsv(
        output_dir / "extended_type_system.tsv",
        ["Type Name", "Base Type", "URI", "Description"],
        rows
    )


def export_enum_values(sv: SchemaView, output_dir: Path):
    """Export all enum permissible values."""
    rows = []
    for enum_name in sorted(sv.all_enums()):
        enum_def = sv.get_enum(enum_name)
        if enum_def and enum_def.permissible_values:
            for value_name, value_def in enum_def.permissible_values.items():
                rows.append([
                    enum_name,
                    value_name,
                    value_def.description if value_def.description else "",
                    value_def.meaning if value_def.meaning else "",
                ])

    write_tsv(
        output_dir / "extended_enum_values.tsv",
        ["Enum Name", "Value", "Description", "Meaning (Ontology Term)"],
        rows
    )


def export_enum_summary(sv: SchemaView, output_dir: Path):
    """Export enum summary statistics."""
    rows = []
    for enum_name in sorted(sv.all_enums()):
        enum_def = sv.get_enum(enum_name)
        if enum_def:
            value_count = len(enum_def.permissible_values) if enum_def.permissible_values else 0
            has_meanings = any(
                v.meaning for v in enum_def.permissible_values.values()
            ) if enum_def.permissible_values else False

            rows.append([
                enum_name,
                value_count,
                "Yes" if has_meanings else "No",
                enum_def.description if enum_def.description else ""
            ])

    write_tsv(
        output_dir / "extended_enum_summary.tsv",
        ["Enum Name", "Value Count", "Has Ontology Mappings", "Description"],
        rows
    )


def export_class_details(sv: SchemaView, output_dir: Path):
    """Export detailed class information."""
    rows = []
    for class_name in sorted(sv.all_classes()):
        cls = sv.get_class(class_name)
        if cls:
            direct_slots = len(cls.attributes) if cls.attributes else 0
            total_slots = len(sv.class_slots(class_name))
            inherited_slots = total_slots - direct_slots

            rows.append([
                class_name,
                cls.is_a if cls.is_a else "",
                ", ".join(cls.mixins) if cls.mixins else "",
                direct_slots,
                inherited_slots,
                total_slots,
                "Yes" if cls.abstract else "No",
                cls.class_uri if cls.class_uri else "",
                cls.description[:100] + "..." if cls.description and len(cls.description) > 100 else (cls.description if cls.description else "")
            ])

    write_tsv(
        output_dir / "extended_class_details.tsv",
        ["Class Name", "Parent (is_a)", "Mixins", "Direct Slots", "Inherited Slots", "Total Slots", "Abstract", "URI", "Description"],
        rows
    )


def export_slot_details(sv: SchemaView, output_dir: Path):
    """Export detailed slot information."""
    rows = []
    for slot_name in sorted(sv.all_slots()):
        slot = sv.get_slot(slot_name)
        if slot:
            # Count usage across classes
            usage_count = sum(1 for cls in sv.all_classes() if slot_name in sv.class_slots(cls))

            # Get mappings
            exact_mappings = ", ".join(slot.exact_mappings) if slot.exact_mappings else ""
            broad_mappings = ", ".join(slot.broad_mappings) if slot.broad_mappings else ""

            rows.append([
                slot_name,
                slot.range if slot.range else "string",
                "Yes" if slot.required else "No",
                "Yes" if slot.multivalued else "No",
                "Yes" if slot.identifier else "No",
                usage_count,
                slot.slot_uri if slot.slot_uri else "",
                exact_mappings,
                broad_mappings,
                slot.description[:100] + "..." if slot.description and len(slot.description) > 100 else (slot.description if slot.description else "")
            ])

    write_tsv(
        output_dir / "extended_slot_details.tsv",
        ["Slot Name", "Range", "Required", "Multivalued", "Identifier", "Used in Classes", "URI", "Exact Mappings", "Broad Mappings", "Description"],
        rows
    )


def export_schema_metadata(sv: SchemaView, output_dir: Path):
    """Export schema-level metadata."""
    schema = sv.schema

    rows = [
        ["Schema Name", schema.name],
        ["Schema ID", schema.id if schema.id else ""],
        ["Version", schema.version if schema.version else "Not specified"],
        ["License", schema.license if schema.license else ""],
        ["Title", schema.title if schema.title else ""],
        ["Description", schema.description if schema.description else ""],
        ["Total Imports", str(len(schema.imports) if schema.imports else 0)],
        ["Total Prefixes", str(len(schema.prefixes) if schema.prefixes else 0)],
        ["Total Classes", str(len(sv.all_classes()))],
        ["Total Slots", str(len(sv.all_slots()))],
        ["Total Enums", str(len(sv.all_enums()))],
        ["Total Types", str(len(sv.all_types()))],
        ["Total Subsets", str(len(sv.all_subsets()))],
    ]

    write_tsv(
        output_dir / "extended_schema_metadata.tsv",
        ["Property", "Value"],
        rows
    )


def export_prefix_mappings(sv: SchemaView, output_dir: Path):
    """Export namespace prefix mappings."""
    schema = sv.schema
    rows = []

    if schema.prefixes:
        for prefix_name, prefix_def in sorted(schema.prefixes.items()):
            rows.append([
                prefix_name,
                prefix_def.prefix_reference if hasattr(prefix_def, 'prefix_reference') else str(prefix_def)
            ])

    write_tsv(
        output_dir / "extended_prefix_mappings.tsv",
        ["Prefix", "URI"],
        rows
    )


def main():
    print("Extended D4D Schema Statistics (SchemaView)")
    print("=" * 60)

    # Load schema
    schema_path = find_full_schema()
    print(f"\nLoading schema: {schema_path.name}")
    sv = SchemaView(str(schema_path))
    print(f"✓ Loaded schema: {sv.schema.name}")

    # Output directory
    output_dir = Path("data/schema_stats")
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nGenerating extended statistics...")

    # Export all extended data
    export_type_system(sv, output_dir)
    export_enum_summary(sv, output_dir)
    export_enum_values(sv, output_dir)
    export_class_details(sv, output_dir)
    export_slot_details(sv, output_dir)
    export_schema_metadata(sv, output_dir)
    export_prefix_mappings(sv, output_dir)

    print(f"\n{'=' * 60}")
    print(f"✓ Extended statistics generated in: {output_dir}")
    print(f"{'=' * 60}")


if __name__ == '__main__':
    main()

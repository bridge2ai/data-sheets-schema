#!/usr/bin/env python3
"""
schema_stats.py

Generates comprehensive statistics about the D4D LinkML schema using SchemaView.

Usage:
    python schema_stats.py [--level LEVEL] [--format FORMAT] [--output FILE]

Options:
    --level LEVEL     Granularity level (1-4, default: 1)
    --format FORMAT   Output format (json|markdown|csv, default: markdown)
    --output FILE     Output file path (default: stdout)
    --schema PATH     Path to schema file (default: auto-detect full schema)
"""

import json
import sys
import argparse
from pathlib import Path
from typing import Dict, Any, List, Set
from collections import defaultdict, Counter

try:
    from linkml_runtime.utils.schemaview import SchemaView
except ImportError:
    print("ERROR: linkml-runtime not installed. Run: poetry install", file=sys.stderr)
    sys.exit(1)


def find_full_schema() -> Path:
    """Auto-detect the full merged schema file."""
    script_dir = Path(__file__).parent.resolve()
    # Navigate from .claude/agents/scripts to repo root
    repo_root = script_dir.parent.parent.parent  # scripts -> agents -> .claude -> repo root
    schema_path = repo_root / "src" / "data_sheets_schema" / "schema" / "data_sheets_schema_all.yaml"

    if not schema_path.exists():
        raise FileNotFoundError(
            f"Full schema not found at {schema_path}\n"
            f"Run: make full-schema"
        )

    return schema_path


def load_schema(schema_path: str = None) -> SchemaView:
    """Load full merged schema using SchemaView."""
    if schema_path is None:
        schema_path = find_full_schema()

    try:
        sv = SchemaView(str(schema_path))
        return sv
    except Exception as e:
        raise RuntimeError(f"Failed to load schema from {schema_path}: {e}")


def get_module_from_prefix(prefix: str) -> str:
    """Map namespace prefix to module name."""
    module_map = {
        'd4dmotivation': 'D4D_Motivation',
        'd4dcomposition': 'D4D_Composition',
        'd4dcollection': 'D4D_Collection',
        'd4dpreprocessing': 'D4D_Preprocessing',
        'd4duses': 'D4D_Uses',
        'd4ddistribution': 'D4D_Distribution',
        'd4dmaintenance': 'D4D_Maintenance',
        'd4dethics': 'D4D_Ethics',
        'd4dhuman': 'D4D_Human',
        'd4ddatagovernance': 'D4D_Data_Governance',
        'd4dvariables': 'D4D_Variables',
        'd4dmetadata': 'D4D_Metadata',
        'd4dminimal': 'D4D_Minimal',
        'd4dbase': 'D4D_Base_import',
        'linkml': 'LinkML_Core',
    }
    return module_map.get(prefix.lower(), 'Unknown')


def get_class_module(sv: SchemaView, class_name: str) -> str:
    """Determine which module a class belongs to based on its CURIE prefix."""
    cls = sv.get_class(class_name)
    if cls is None:
        return "Unknown"

    # Try to get from class_uri or from the class name itself
    class_uri = cls.class_uri or class_name

    # Extract prefix from CURIE
    if ':' in class_uri:
        prefix = class_uri.split(':')[0]
        return get_module_from_prefix(prefix)

    return "Main"


def get_high_level_stats(sv: SchemaView) -> Dict[str, Any]:
    """Return counts of major schema elements (Level 1)."""
    all_classes = sv.all_classes()
    all_slots = sv.all_slots()
    all_enums = sv.all_enums()
    all_subsets = sv.all_subsets()

    schema = sv.schema
    prefixes = schema.prefixes if schema.prefixes else {}

    return {
        'total_classes': len(all_classes),
        'total_slots': len(all_slots),
        'total_enums': len(all_enums),
        'total_subsets': len(all_subsets),
        'total_prefixes': len(prefixes),
    }


def get_class_breakdown(sv: SchemaView) -> Dict[str, Any]:
    """Categorize classes by module, abstract/concrete, etc. (Level 2)."""
    all_classes = sv.all_classes()

    by_module = defaultdict(list)
    abstract_classes = []
    concrete_classes = []

    for class_name in all_classes:
        cls = sv.get_class(class_name)
        if cls is None:
            continue

        # Module assignment
        module = get_class_module(sv, class_name)
        by_module[module].append(class_name)

        # Abstract vs concrete
        if cls.abstract:
            abstract_classes.append(class_name)
        else:
            concrete_classes.append(class_name)

    return {
        'by_module': {k: len(v) for k, v in sorted(by_module.items())},
        'abstract_count': len(abstract_classes),
        'concrete_count': len(concrete_classes),
    }


def get_slot_analysis(sv: SchemaView) -> Dict[str, Any]:
    """Analyze slot usage, types, requirements (Level 2)."""
    all_slots = sv.all_slots()

    by_range = defaultdict(list)
    required_slots = []
    optional_slots = []
    multivalued_slots = []
    single_valued_slots = []
    identifier_slots = []

    for slot_name in all_slots:
        slot = sv.get_slot(slot_name)
        if slot is None:
            continue

        # Range type
        range_type = slot.range or 'string'
        by_range[range_type].append(slot_name)

        # Required vs optional
        if slot.required:
            required_slots.append(slot_name)
        else:
            optional_slots.append(slot_name)

        # Multivalued
        if slot.multivalued:
            multivalued_slots.append(slot_name)
        else:
            single_valued_slots.append(slot_name)

        # Identifier
        if slot.identifier:
            identifier_slots.append(slot_name)

    return {
        'by_range': {k: len(v) for k, v in sorted(by_range.items(), key=lambda x: -len(x[1]))},
        'required_count': len(required_slots),
        'optional_count': len(optional_slots),
        'multivalued_count': len(multivalued_slots),
        'single_valued_count': len(single_valued_slots),
        'identifier_count': len(identifier_slots),
    }


def get_detailed_analysis(sv: SchemaView) -> Dict[str, Any]:
    """Detailed schema analysis (Level 3)."""
    all_classes = sv.all_classes()
    all_slots = sv.all_slots()
    all_enums = sv.all_enums()

    # Inheritance depth
    def get_depth(class_name: str, visited: Set[str] = None) -> int:
        if visited is None:
            visited = set()
        if class_name in visited:
            return 0
        visited.add(class_name)

        cls = sv.get_class(class_name)
        if cls is None or cls.is_a is None:
            return 0
        return 1 + get_depth(cls.is_a, visited)

    depth_counts = defaultdict(list)
    for class_name in all_classes:
        depth = get_depth(class_name)
        depth_counts[depth].append(class_name)

    max_depth = max(depth_counts.keys()) if depth_counts else 0

    # Slot usage across classes
    slot_usage = defaultdict(list)
    for class_name in all_classes:
        cls_slots = sv.class_slots(class_name)
        for slot_name in cls_slots:
            slot_usage[slot_name].append(class_name)

    # Top 10 most reused slots
    top_slots = sorted(
        [(slot, len(classes)) for slot, classes in slot_usage.items()],
        key=lambda x: -x[1]
    )[:10]

    # Enum value counts
    enum_value_counts = {}
    for enum_name in all_enums:
        enum = sv.get_enum(enum_name)
        if enum and enum.permissible_values:
            enum_value_counts[enum_name] = len(enum.permissible_values)

    return {
        'max_inheritance_depth': max_depth,
        'classes_by_depth': {k: len(v) for k, v in sorted(depth_counts.items())},
        'top_reused_slots': [{'slot': slot, 'usage_count': count} for slot, count in top_slots],
        'enum_value_counts': enum_value_counts,
    }


def get_quality_metrics(sv: SchemaView) -> Dict[str, Any]:
    """Schema quality metrics (Level 4)."""
    all_classes = sv.all_classes()
    all_slots = sv.all_slots()

    classes_without_description = []
    slots_without_range = []
    orphaned_classes = []
    single_use_slots = []

    # Classes without descriptions
    for class_name in all_classes:
        cls = sv.get_class(class_name)
        if cls and not cls.description:
            classes_without_description.append(class_name)

    # Slots without ranges
    for slot_name in all_slots:
        slot = sv.get_slot(slot_name)
        if slot and not slot.range:
            slots_without_range.append(slot_name)

    # Orphaned classes (not used in any slot ranges or inheritance)
    used_classes = set()
    for slot_name in all_slots:
        slot = sv.get_slot(slot_name)
        if slot and slot.range:
            used_classes.add(slot.range)

    for class_name in all_classes:
        cls = sv.get_class(class_name)
        if cls and cls.is_a:
            used_classes.add(cls.is_a)
        if cls:
            for mixin in (cls.mixins or []):
                used_classes.add(mixin)

    for class_name in all_classes:
        if class_name not in used_classes:
            # Check if it has children
            has_children = any(
                sv.get_class(c).is_a == class_name
                for c in all_classes
                if sv.get_class(c) and sv.get_class(c).is_a
            )
            if not has_children:
                orphaned_classes.append(class_name)

    # Single-use slots
    slot_usage = defaultdict(int)
    for class_name in all_classes:
        cls_slots = sv.class_slots(class_name)
        for slot_name in cls_slots:
            slot_usage[slot_name] += 1

    single_use_slots = [slot for slot, count in slot_usage.items() if count == 1]

    return {
        'classes_without_description': len(classes_without_description),
        'slots_without_range': len(slots_without_range),
        'orphaned_classes': len(orphaned_classes),
        'single_use_slots': len(single_use_slots),
        'examples': {
            'classes_without_description': classes_without_description[:5],
            'slots_without_range': slots_without_range[:5],
            'orphaned_classes': orphaned_classes[:5],
            'single_use_slots': single_use_slots[:5],
        }
    }


def generate_stats(sv: SchemaView, level: int = 1) -> Dict[str, Any]:
    """Generate schema statistics at specified granularity level."""
    stats = {
        'schema_name': sv.schema.name,
        'schema_version': sv.schema.version,
        'level': level,
    }

    # Level 1: High-level summary
    stats['summary'] = get_high_level_stats(sv)

    # Level 2: Breakdown by category
    if level >= 2:
        stats['classes'] = get_class_breakdown(sv)
        stats['slots'] = get_slot_analysis(sv)

    # Level 3: Detailed analysis
    if level >= 3:
        stats['detailed'] = get_detailed_analysis(sv)

    # Level 4: Quality metrics
    if level >= 4:
        stats['quality'] = get_quality_metrics(sv)

    return stats


def format_markdown(stats: Dict[str, Any]) -> str:
    """Format statistics as Markdown."""
    lines = []

    # Header
    lines.append(f"# D4D Schema Statistics")
    lines.append(f"")
    lines.append(f"**Schema**: {stats.get('schema_name', 'Unknown')}")
    lines.append(f"**Version**: {stats.get('schema_version', 'Unknown')}")
    lines.append(f"**Detail Level**: {stats.get('level', 1)}")
    lines.append(f"")

    # Level 1: Summary
    if 'summary' in stats:
        lines.append(f"## High-Level Summary")
        lines.append(f"")
        for key, value in stats['summary'].items():
            label = key.replace('_', ' ').title()
            lines.append(f"- **{label}**: {value:,}")
        lines.append(f"")

    # Level 2: Breakdowns
    if 'classes' in stats:
        lines.append(f"## Class Breakdown")
        lines.append(f"")
        lines.append(f"- **Abstract Classes**: {stats['classes']['abstract_count']:,}")
        lines.append(f"- **Concrete Classes**: {stats['classes']['concrete_count']:,}")
        lines.append(f"")
        lines.append(f"### Classes by Module")
        lines.append(f"")
        for module, count in stats['classes']['by_module'].items():
            lines.append(f"- {module}: {count:,}")
        lines.append(f"")

    if 'slots' in stats:
        lines.append(f"## Slot Analysis")
        lines.append(f"")
        lines.append(f"- **Required Slots**: {stats['slots']['required_count']:,}")
        lines.append(f"- **Optional Slots**: {stats['slots']['optional_count']:,}")
        lines.append(f"- **Multivalued Slots**: {stats['slots']['multivalued_count']:,}")
        lines.append(f"- **Single-valued Slots**: {stats['slots']['single_valued_count']:,}")
        lines.append(f"- **Identifier Slots**: {stats['slots']['identifier_count']:,}")
        lines.append(f"")
        lines.append(f"### Slots by Range Type")
        lines.append(f"")
        for range_type, count in list(stats['slots']['by_range'].items())[:10]:
            lines.append(f"- {range_type}: {count:,}")
        lines.append(f"")

    # Level 3: Detailed analysis
    if 'detailed' in stats:
        lines.append(f"## Detailed Analysis")
        lines.append(f"")
        lines.append(f"### Inheritance Hierarchy")
        lines.append(f"")
        lines.append(f"- **Max Depth**: {stats['detailed']['max_inheritance_depth']}")
        lines.append(f"")
        for depth, count in stats['detailed']['classes_by_depth'].items():
            lines.append(f"- Depth {depth}: {count:,} classes")
        lines.append(f"")

        lines.append(f"### Top Reused Slots")
        lines.append(f"")
        for item in stats['detailed']['top_reused_slots']:
            lines.append(f"- `{item['slot']}`: used in {item['usage_count']:,} classes")
        lines.append(f"")

    # Level 4: Quality metrics
    if 'quality' in stats:
        lines.append(f"## Schema Quality Metrics")
        lines.append(f"")

        q = stats['quality']

        # Check marks
        def status(count):
            return "✓" if count == 0 else "✗"

        lines.append(f"{status(q['classes_without_description'])} **Classes without description**: {q['classes_without_description']:,}")
        if q['examples']['classes_without_description']:
            lines.append(f"  - Examples: {', '.join(q['examples']['classes_without_description'])}")
        lines.append(f"")

        lines.append(f"{status(q['slots_without_range'])} **Slots without range**: {q['slots_without_range']:,}")
        if q['examples']['slots_without_range']:
            lines.append(f"  - Examples: {', '.join(q['examples']['slots_without_range'])}")
        lines.append(f"")

        lines.append(f"{status(q['orphaned_classes'])} **Orphaned classes**: {q['orphaned_classes']:,}")
        if q['examples']['orphaned_classes']:
            lines.append(f"  - Examples: {', '.join(q['examples']['orphaned_classes'])}")
        lines.append(f"")

        lines.append(f"⚠ **Single-use slots**: {q['single_use_slots']:,} (consider consolidation)")
        if q['examples']['single_use_slots']:
            lines.append(f"  - Examples: {', '.join(q['examples']['single_use_slots'])}")
        lines.append(f"")

    return '\n'.join(lines)


def format_csv(stats: Dict[str, Any]) -> str:
    """Format statistics as CSV."""
    lines = []

    # Header
    lines.append("category,metric,value")

    # Summary
    for key, value in stats.get('summary', {}).items():
        lines.append(f"summary,{key},{value}")

    # Classes
    if 'classes' in stats:
        lines.append(f"classes,abstract_count,{stats['classes']['abstract_count']}")
        lines.append(f"classes,concrete_count,{stats['classes']['concrete_count']}")
        for module, count in stats['classes']['by_module'].items():
            lines.append(f"classes_by_module,{module},{count}")

    # Slots
    if 'slots' in stats:
        for key, value in stats['slots'].items():
            if key != 'by_range':
                lines.append(f"slots,{key},{value}")
        for range_type, count in stats['slots'].get('by_range', {}).items():
            lines.append(f"slots_by_range,{range_type},{count}")

    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description="Generate D4D schema statistics")
    parser.add_argument(
        '--level',
        type=int,
        default=1,
        choices=[1, 2, 3, 4],
        help='Granularity level (1=summary, 2=breakdown, 3=detailed, 4=quality)'
    )
    parser.add_argument(
        '--format',
        type=str,
        default='markdown',
        choices=['json', 'markdown', 'csv'],
        help='Output format'
    )
    parser.add_argument(
        '--output',
        type=str,
        help='Output file path (default: stdout)'
    )
    parser.add_argument(
        '--schema',
        type=str,
        help='Path to schema file (default: auto-detect)'
    )

    args = parser.parse_args()

    try:
        # Load schema
        sv = load_schema(args.schema)

        # Generate statistics
        stats = generate_stats(sv, level=args.level)

        # Format output
        if args.format == 'json':
            output = json.dumps(stats, indent=2)
        elif args.format == 'markdown':
            output = format_markdown(stats)
        elif args.format == 'csv':
            output = format_csv(stats)
        else:
            output = json.dumps(stats, indent=2)

        # Write output
        if args.output:
            with open(args.output, 'w') as f:
                f.write(output)
            print(f"Statistics written to {args.output}", file=sys.stderr)
        else:
            print(output)

        return 0

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())

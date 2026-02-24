# D4D Schema Statistics Export

This directory contains exported schema statistics in TSV (tab-separated values) format.

Generated: 2026-02-19

## Files

### Basic Statistics (Levels 1-4)

**Level 1: High-Level Summary**
- `level1_summary.tsv` - Overall schema element counts (5 rows)

**Level 2: Category Breakdowns**
- `level2_class_categories.tsv` - Abstract vs concrete classes (2 rows)
- `level2_classes_by_module.tsv` - Class distribution across modules (2 rows)
- `level2_slot_categories.tsv` - Slot categorization (5 rows)
- `level2_slots_by_range_type.tsv` - Complete breakdown of slots by data type (26 rows)

**Level 3: Detailed Analysis**
- `level3_inheritance_depth.tsv` - Class inheritance hierarchy distribution (5 rows)
- `level3_top_reused_slots.tsv` - Top 10 most reused slots across classes (10 rows)

**Level 4: Quality Metrics**
- `level4_quality_metrics.tsv` - Schema quality assessment results (4 rows)
- `level4_recommendations.tsv` - Recommendations for schema improvements (3 rows)

**Combined**
- `ALL_STATS_COMBINED.tsv` - All basic statistics in one file (1.5 KB)

### Extended SchemaView Data

**Type System**
- `extended_type_system.tsv` - All 19 LinkML types with URIs and descriptions (19 rows)

**Enumerations**
- `extended_enum_summary.tsv` - All 15 enums with value counts and ontology mapping status (15 rows, 2.3 KB)
- `extended_enum_values.tsv` - All 191 permissible values across all enums with descriptions and ontology terms (191 rows, 14 KB)

**Classes**
- `extended_class_details.tsv` - All 76 classes with inheritance, slots, URIs, and descriptions (76 rows, 10 KB)

**Slots**
- `extended_slot_details.tsv` - All 272 slots with ranges, usage counts, URIs, and mappings (272 rows, 26 KB)

**Schema Metadata**
- `extended_schema_metadata.tsv` - Schema-level metadata (name, version, license, etc.) (13 rows, 345 bytes)
- `extended_prefix_mappings.tsv` - All 31 namespace prefix mappings (31 rows, 1.6 KB)

## Usage

These TSV files can be:
- Opened in Excel, Google Sheets, or any spreadsheet application
- Imported into data analysis tools (R, Python pandas, etc.)
- Used for tracking schema evolution over time
- Included in documentation or reports

## Regenerating Statistics

To regenerate these statistics:

```bash
# Generate statistics at all levels
poetry run python .claude/agents/scripts/schema_stats.py --level 4 --format markdown

# Export to different formats
poetry run python .claude/agents/scripts/schema_stats.py --level 4 --format json --output stats.json
poetry run python .claude/agents/scripts/schema_stats.py --level 4 --format csv --output stats.csv
```

## Schema Source

Statistics generated from: `src/data_sheets_schema/schema/data_sheets_schema_all.yaml`

Full merged schema with all imports resolved (791 KB, 28,829 lines).

# D4D Schema Statistics Export

Basic and extended statistics regenerated for schema **3.2.0** on 2026-11-08
from `src/data_sheets_schema/schema/data_sheets_schema_all.yaml`.

The current schema has 79 classes, 301 slots, 18 enums, 242 permissible values,
19 types and 39 namespace prefixes. Counts use the repository's schema-statistics
implementation; quality metrics are structural heuristics, not validation verdicts.

## Generated exports

- `level1_*.tsv`: summary counts.
- `level2_*.tsv`: class/module and slot/range breakdowns.
- `level3_*.tsv`: inheritance depths and the ten most reused slots.
- `level4_*.tsv`: quality metrics and recommendations.
- `ALL_STATS_COMBINED.tsv`: the basic exports in one table.
- `extended_*.tsv`: types, enum summaries/values, classes, slots, schema metadata
  and prefixes, produced by the repository's extended exporter.

## Regeneration

Run from the repository root in its installed Python environment. Keep the
intermediate JSON in an explicitly chosen scratch directory:

```bash
PYTHONPATH="$PWD/src:$PWD" python -m data_sheets_schema.cli schema stats --level 4 --format json --output /path/to/scratch/level4.json
python scripts/adhoc/d100_export_stats_20261108.py /path/to/scratch/level4.json
```

The exporter converts the repository command's statistics to TSV and invokes
`.claude/agents/scripts/schema_stats_extended.py`. It preserves recommendation
wording while refreshing measured counts by issue label. It checks the input version
against the merged schema and records that version in `extended_schema_metadata.tsv`.
All TSV outputs go to this repository's `data/schema_stats/`, even when the adapter
is invoked by absolute path from another working directory. The recommendations
file is an editorial input and must be retained.

Basic export labels now follow the statistics keys (for example, `Single use slots`
and `Depth 0`); combined sections distinguish modules, slots and ranges and omit
blank separator rows. The module breakdown currently reports `Main 70` and
`Unknown 9`: this is a limitation of attribution on the merged schema, not proof
that nine classes lack a source module.

## Retained supplementary tables

`rai_*.tsv` and `d4d_properties*.txt` are historical, selected mapping/property
lists with editorial descriptions. They are preserved unchanged, are not outputs
of the repository statistics command, and are **not a complete 3.2.0 inventory**.
Use `extended_slot_details.tsv` and `extended_class_details.tsv` for the current
complete inventory. Their regeneration requires a separately defined selection
and editorial contract.

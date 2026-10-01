# D4D ↔ RO-Crate Schema-Structure-Aware Mapping Analysis

## Overview

This document describes how the schema-structure-aware mapping between D4D
(Datasheets for Datasets) and the RO-Crate FAIRSCAPE profile is produced and
checked.

**Script**: `src/semantic_exchange/generate_structural_mapping.py`
**Mapping**: `data/semantic_exchange/d4d_rocrate_structural_mapping.sssom.tsv`
**Summary**: `data/semantic_exchange/d4d_rocrate_structural_mapping_summary.md`

## Where the numbers are

This document states no counts. An earlier version stated a total and a
type-compatibility rate that the committed file had long since stopped
matching, and nothing compared them (#2976). Read the numbers from the files
instead:

```bash
make check-sssom-structural   # committed mapping and summary against regeneration
```

The check writes nothing. It compares the committed mapping and summary with
what the generator writes, allowing for the hand-written rows described under
[Rows the generator does not produce](#rows-the-generator-does-not-produce);
`python src/semantic_exchange/generate_structural_mapping.py --help` states
exactly what it compares (#4076).

The summary is written from the generator's output, not from the committed
TSV, so its per-justification counts describe what regeneration makes and not
the file beside it (#295). For the committed file's own counts, read the TSV:

```python
import pandas as pd

df = pd.read_csv("data/semantic_exchange/d4d_rocrate_structural_mapping.sssom.tsv",
                 sep="\t", comment="#")
len(df)                                          # rows
df["predicate_id"].value_counts()                # exactMatch / closeMatch
(df["type_compatible"] == False).sum()           # rows flagged incompatible
df["composition_path"].notna().sum()             # composition rows
```

## Mapping strategies

`StructuralMappingGenerator.generate_mappings` runs three strategies, then keeps
one row per (class, slot, RO-Crate property), the one with the highest
confidence. Each row's `structural_notes` names the strategy that produced it.

### 1. `slot_uri` annotations

A slot whose `slot_uri` names a property the RO-Crate input carries in the same
namespace, for example `d4d:Dataset/at_risk_populations` → `d4d:atRiskPopulations`.
Justification `semapv:SemanticSimilarity`; confidence 0.9 when the types are
compatible and 0.6 when not. **An incompatible row is kept and flagged**, not
dropped.

### 2. `DatasetProperty` hierarchy

The attributes of every class that inherits from `DatasetProperty`, matched to
RO-Crate properties by name similarity (at least 0.85), for example
`d4d:Purpose/name` → `name` and `d4d:Creator/principal_investigator` →
`principalInvestigator`. **An incompatible candidate is skipped**, so every row
this strategy emits is type-compatible by construction; that is a property of
the filter, not evidence about the schema.

### 3. Composition paths

Every slot whose range is a class, and one level below it: each direct
attribute of that class as `slot.attribute`. The generator does not recurse,
so a path never has more than one dot, even where the attribute's own range is
a class (`anomalies.used_software` is the deepest path; nothing under it is
traced). Each path is matched to RO-Crate properties whose path contains the
slot name. The subject carries the whole
path, so `anomalies.id` is `d4d:Dataset/anomalies.id` and no longer shares a
subject with `Dataset`'s own `id` slot (#410). The range is the one the schema
gives the end of the path, but the row is multivalued when *any* segment of
the path is (#2936): `anomalies.name` is one string per anomaly, yet
`d4d:Dataset/anomalies.name` is multivalued, because `anomalies` is a list and
the path reaches one name per entry. Before
#2936 these rows were written with range `string`, multivalued `False` and
`type_compatible` `True` whatever the path reached, and none was validated.
Today the only composition rows go through `anomalies` on `Dataset` and
`DataSubset`, a multivalued slot mapped to a single value, so every one of them
is **kept and flagged** with a cardinality warning.

### No module strategy

There was a fourth strategy, meant to match the attributes of classes in the
Motivation, Composition, Collection, Preprocessing and Uses modules to
properties in each module's RO-Crate namespaces. It never emitted a row and
was removed (#3363). The parser gave every class of the merged schema one
module, and assigning modules would not have helped: every class in the merged
schema carries the root schema's `from_schema`, and with each class given the
module the source schema declares it in, the strategy still matched nothing.
Its name-similarity cut admits only an exact match, and every candidate kept
its namespace prefix in the comparison, so `LabelingStrategy`'s
`data_annotation_protocol` did not match `rai:dataAnnotationProtocol`. No
row in the committed file comes from it.

## Type-compatibility validation

`_validate_type_compatibility` applies these rules:

- a `boolean` slot cannot map to an object (`dict`) property;
- a `boolean` slot cannot map to a property whose name contains `date`;
- a multivalued slot cannot map to a property whose value is not a list;
- a literal slot (`string`, `boolean`, `integer`, `float`) cannot map to a
  property whose name suggests a relationship (`derived`, `related`,
  `references`, `requires`).

What happens on a failure depends on the strategy (above): the `slot_uri` and
composition strategies keep the row with `type_compatible` `False` and the
failed rule in `warnings`; the hierarchy strategy drops the candidate. So the
share of compatible rows is not a quality measure of the mapping. It is how
many rows came from the strategies that keep failures, and how many of those
failed.

## Rows the generator does not produce

The committed file carries rows no strategy emits: class-level rows (the
generator reads `class_uri` and never emits a row from it), `schema:hasPart`,
`dcat:byteSize`, and `d4d:` targets that are absent from the RO-Crate input.
They are listed, each with its reason, in `KNOWN_UNDERIVABLE` in
`src/semantic_exchange/generate_structural_mapping.py` (#234), which the check
and `tests/test_semantic_exchange/test_structural_mapping_drift.py` both read
(#3968).

These rows' range and cardinality columns are checked against the schema, as
every committed row's are, by `TestRowsStateTheSchema` in that test file. A
row that names a slot states that slot's range and cardinality. A class-level
row names a class, not a slot, so its range is the class itself and it is not
multivalued (#3388): `TestRowsStateTheSchema` requires the class to exist in
the merged full schema or the merged core schema, `d4d_subject_range` to name
it, and `subject_multivalued` to be `False` (#4076). `d4d:DataSubset` once
gave its parent, `Dataset`, as its range.

## Usage

### Check

```bash
make check-sssom-structural
```

### Generate

```bash
make gen-sssom-structural
```

When its inputs (the merged schema, the FAIRSCAPE RO-Crate example `data/ro-crate/profiles/fairscape/full-ro-crate-metadata.json`, or the generator) are newer than the mapping, this rewrites both the mapping and the summary from the generator; otherwise make does nothing. To force a rewrite, run `python src/semantic_exchange/generate_structural_mapping.py`. While the
rows above stand, a rewrite also drops them from the committed mapping, and
the check then fails and names each one: restore their lines from git before
committing. That is why `make gen-sssom-all` does not run this target and
`make clean-sssom` does not delete the mapping (#3967).

## References

- **SSSOM Specification**: https://mapping-commons.github.io/sssom/
- **D4D Schema**: src/data_sheets_schema/schema/
- **RO-Crate 1.2**: https://www.researchobject.org/ro-crate/1.2-DRAFT/
- **FAIRSCAPE**: data/ro-crate/profiles/fairscape/

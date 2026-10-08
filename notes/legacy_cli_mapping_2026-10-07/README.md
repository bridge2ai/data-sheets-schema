# Explicit mapping selection for `d4d rocrate transform` (#4638)

`d4d rocrate transform` now accepts optional `--mapping PATH` and forwards that
file to the existing legacy loader/builder for a single source or `--merge`.
Relative paths are interpreted from the caller's working directory. The option
requires an existing file; it does not validate or reinterpret the TSV itself.
The existing mandatory Dataset publication gate still checks the final record.

```sh
d4d rocrate transform input.json -o dataset.yaml --mapping reviewed-mapping.tsv
d4d rocrate transform --merge --inputs first.json --inputs second.json \
  --primary second.json -o dataset.yaml --mapping reviewed-mapping.tsv
```

These are caller-selected source and mapping paths, not a compatible mapping
distributed by this change. Omitting `--mapping` retains
`data/ro-crate_mapping/d4d_rocrate_mapping_v2_semantic.tsv`. Its missing required
`Dataset.id` and other schema/construction defects remain under #4594; it may
still refuse publication. This wrapper adds no ID, drops no mapped field, changes
no TSV, and does not switch to the maintained static mapper or FAIRSCAPE converter.

The underlying producer and [publication gate](../../src/data_sheets_schema/legacy_publication.py)
prepare/validate Dataset bytes and reports before final writes. Validation failure
retains existing destinations; source, mapping and schema paths remain protected
from Dataset/report replacement. Existing merge ranking, field conflict rules,
description decoration and list-union behavior are unchanged. Single-source tests
retain list order/multiplicity and exact source text; merge tests assert the
existing producer's distinct behavior rather than claiming a lossless raw merge.

## Scope and validation

The implementation is based on reviewed required-publication-gate commit
`9c8b73ee7d0be062aff2532b2a9bd64ba73702e5` from
[PR #4634](https://github.com/bridge2ai/data-sheets-schema/pull/4634).
It does not depend on the separate API result contract #4630/#4635.

New tests invoke the actual Click command, hidden producer, mapping loader,
builder/merger and packaged Dataset schema. They cover explicit single/merge
selection, relative paths with spaces, primary selection, root/member isolation,
false versus missing, default refusal, invalid selected records, and preserving
source/mapping/output/report bytes on refusal. Only import state is isolated;
the transformation boundary is not replaced by a fake implementation.

Tests have been prepared but not run; the coordinator will serialize execution
after independent review and source freeze. No real-project replay, record label,
comparison figure, provider call or scientific score is produced by this change.

This addresses only #4638. Parent #4594 still needs an explicit decision about
legacy construction versus retirement, followed by the five retained legacy
replay inputs if that producer changes. Those inputs are CHORUS raw metadata,
VOICE raw metadata, CM4AI reduced metadata, the original CM4AI ZIP metadata
member, and the one-node VOICE provenance graph; their pins and previous failure
results are in [the parser replay evidence](../parser_root_policy_2026-10-07/validation.json).
They are separate from the five already-published deterministic records.
The raw RO-Crate JSON merge defect #4593 is unchanged. #2915, scientific review
holds, and held figure branches remain open; accepted serialization is not a
claim of scientific fidelity or increased source coverage.

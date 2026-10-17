# Legacy default-route dispositions

The semantic TSV uses `root_default_route_dispositions_v1` on fourteen explicit
legacy rows. This policy selects assertions from the crate's selected root. It
does not infer scientific facts, assess mapping fidelity, or add source coverage.
Unmarked custom TSV rows retain their prior construction and result contracts.

| Historical route | Dataset output |
| --- | --- |
| `tasks` | Whole strings in `tasks[].response` |
| `discouraged_uses` | Whole strings in `discouraged_uses[].discouragement_details` |
| `future_use_impacts` | Whole strings in `future_use_impacts[].impact_details` |
| `machine_annotation_analyses` | Whole strings in `machine_annotation_tools[].tool_descriptions` |
| `external_resource` | Whole strings in `external_resources[].external_resources` |
| `bytes` | `contentSize` is retained as evidence only; a separate exact nonnegative integer `evi:totalContentSizeBytes` may produce `total_size_bytes` |
| `encoding`, `existing_uses`, `other_tasks`, `data_protection_impacts`, `confidential_elements`, `ip_restrictions`, `extension_mechanism`, `version_access` | Evidence only; the original predicates do not establish these structured assertions |

Strings stay whole. Lists preserve immediate string order, duplicates and empty
strings. Unsupported units remain recoverable in evidence; they are not converted
to prose or used to invent flags. An explicit empty list remains empty. Primary
selection takes the first non-null assertion, so a false, empty or unsupported
primary value is not replaced with a more convenient secondary value. The three
concatenated routes (`tasks`, `future_use_impacts`, `external_resource`) retain
primary-then-secondary order and duplicates. The sensitive-elements route and
prior narrative constructors remain independent.

The original TSV field/source tuples still drive ranking and its denominator.
Aliases and declined outputs do not retarget the scorer, and the supplemental
exact byte assertion adds no ranking credit. Construction counts can change when
a field is declined or renamed; these counts are not measurements of source
coverage, scientific correctness or semantic loss.

## Evidence and publication

Both builders and mergers expose `get_route_dispositions()`. Marked API single
results add `route_dispositions` outside `data`; merge and batch envelopes retain
it separately as well. It is mandatory even when optional provenance or reports
are disabled. Unmarked result shapes are unchanged.

Every supported Dataset publisher prepares `<stem>_route_dispositions.json`
with the Dataset. The sidecar binds the exact published Dataset bytes, schema and
loaded mapping, and retains all selected and unselected assertions, missing/null
presence, raw values, original source occurrences, processing/merge order and
JSON pointers. Full acquired JSON text is retained to make assertions recoverable
after temporary generated inputs disappear. Treat the sidecar with the same
access controls as the source metadata; it can contain sensitive source text.
Evidence uses deterministic ASCII-escaped JSON with nonfinite values refused.
The explicit API JSON result is likewise safe for escaped lone surrogates.

The existing Dataset validator and exact serialized readback gate remain
mandatory. A valid sidecar does not make an invalid Dataset publishable. Batch
operations prepare every Dataset and sidecar before publishing any file.
Validation, overlap and staging failures preserve existing destinations. Each
replacement is atomic; an operating-system error during later replacements can
leave a partially published set. There is no multi-file rollback guarantee.

## Direct callers and generated inputs

Marked direct builders use the exact bytes retained when their mapping and
parser were loaded. Changed source files, mapping files, effective mapping rows
or lookups require a new acquisition. Evidence is checked again before staging.
A source-free `apply_field_transformation` call cannot construct a marked route.
Low-level `save_d4d_yaml` requires explicit `route_dispositions`; report-only
wrappers require an existing accepted Dataset to bind their sidecar.

Dictionary API inputs and auto-process combined inputs are captured before their
temporary files are removed. A future concatenated-output filename is only a
label, never source evidence. Combined snapshots retain each constituent input
occurrence and original pointer and declare the adapter's `_source` addition.

A direct caller intentionally changing an in-memory graph must explicitly pass
`source_snapshot(parser, kind='declared_in_memory_graph')` to the builder. This
records derived serialization, not original file bytes. For a pure graph
reordering, capture an original snapshot first, then pass
`source_snapshot(parser, kind='declared_reordered_graph', parents=[original],
permutation=indices)`; the complete entity permutation is verified. Arbitrary
unannounced graph changes refuse instead of retaining stale source pointers.
These declarations do not change the existing selection, merging or field
semantics of unmarked routes.

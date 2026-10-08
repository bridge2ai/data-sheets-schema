# Explicit legacy maintenance narratives (#4678)

The existing default legacy `updates` row now selects
`Func=update_plan_narrative_v1`. Both legacy builders use one shared constructor:
root `rai:dataReleaseMaintenancePlan` text becomes
`{"update_details": original_text}`. All text survives, including whitespace,
newlines, Unicode and blank strings. No frequency, date, responsible person or
other unstated fact is inferred.

Both loaders validate this selector before filtering raw TSV rows: it must name
one covered `updates` route with exactly that single source property. Misplaced,
uncovered, duplicate and competing declarations refuse. Builders recheck the
route before replacing previous state. An unmarked custom table retains its
existing behavior; unrelated Func values are not executed or reinterpreted.
The established DOI and root-ID rules remain unchanged.

Dictionaries and other non-text values are copied whole. Unknown keys, arrays,
duplicates, false and zero remain available to the mandatory Dataset gate;
they are not stringified, joined, filtered or reduced to a first element.
Missing/null retains its existing absence behavior. Construction reads only
the selected root; a member value cannot fill a missing root property.

The existing merger policy is unchanged: `updates` uses a non-None primary
value, otherwise the first non-None secondary in the existing order. The
selected whole value and its source provenance survive. No nested object fields
or maintenance narratives are combined. An invalid but present primary is not
skipped in favor of a valid secondary. Detached construction prevents result
mutation from changing the parser's source evidence.

This changes an already counted field's representation. Scoring, ranking,
source order and primary-selection rules remain unchanged. Historic TSV
`Mapping_Type`, `SKOS_Relation` and `Information_Loss` values are retained as
historic declarations; this change does not reapprove `exactMatch` or `none`,
measure scientific fidelity, or increase source coverage. No rows are retired.
The mandatory final-byte publication gate and producer/result contracts remain
unchanged.

## Validation status

Implementation and focused tests are ready for independent review. No tests,
producer replay or real-record publication have run for this change yet.
The new tests cover both real loaders/builders, exact text and whole-value
preservation, invalid routes, custom compatibility, missing-root isolation,
merge selection and mutation isolation, score/rank accounting, actual CLI
publication/refusal and an API batch with a later invalid record. Independent
adversarial tests additionally cover invalid first-secondary fallback, nonzero
primary selection, reused merger state, API coverage under both result
contracts, duplicate route ordering and inert near-marker strings.

Static syntax parsing completed without importing repository code. A byte
comparison against the parent table verified that removing only the newly
inserted marker restores the complete original TSV bytes. The original CRLF
line endings are preserved: ordinary `git diff --check` reports trailing
whitespace on the modified row, while the scoped
`git -c core.whitespace=cr-at-eol diff --check` passes. Do not describe the
ordinary check as clean or normalize unrelated table lines to silence it.

After coordinator authorization, validation should run the prior fourteen
root-ID/DOI/publication/API/CLI/packaged-integration modules plus
`tests/test_rocrate/test_legacy_update_plan.py` and
`tests/test_rocrate/test_legacy_update_plan_adversarial.py` (sixteen modules).
Record the exact tested commit, source/table/schema pins, JUnit results and
warnings. Until then, the following replay outcomes are hypotheses, not results.

## Planned bounded replay

Reuse the five retained inputs and both implementations/graph orders from the
[root-ID evidence](../legacy_root_identity_2026-10-08/README.md), comparing the
root-ID predecessor with this change. Keep every historical output and source
byte; use fresh external destinations. Both arms contain the root-ID route.
The expected full-record delta is only `updates` string-to-object construction
for CHORUS, VOICE and the two CM4AI representations; VOICE provenance and all
other fields remain unchanged.

Expected per-record validation counts are CHORUS 31→30, VOICE 151→150,
CM4AI reduced 76→75, VOICE provenance 0→0 and CM4AI original 76→75, repeated
across two implementations and two graph orders. The expected gate denominator
remains twenty records per arm, with four accepted variants of one VOICE
provenance input and sixteen refused drafts. All eight mixed-roster mergers
are expected to remain refused. Preserve every actual error and denominator
if an expectation fails; never drop unrelated invalid fields to obtain a pass.

Compare complete non-updates records/provenance, actual score/rank dictionaries,
selected primary, statistics and merge reports. Preserve fixed secondary source
order and distinguish construction accounting from source coverage. The mixed
roster is a software control, not a scientific combined dataset.

Only #4678 is addressed here. Parent issues #4594/#2915 remain open for broader
mapping, validation, comparison and publication obligations. Typed PI/creator
identities, approximate sizes, per-file placement, other narrative routes and
pending human scientific decisions are outside this change.

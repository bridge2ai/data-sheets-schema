# FAIRSCAPE declared assertions

The paired converters expose a detached `route_evidence` dictionary alongside
their existing return values. This implements the seven non-annotation routes
in Part A of #4046; the four paired canonical routes and annotation grouping
remain separate work. No schema, mapping table, ranking denominator, or
scientific mapping-strength claim changes here.

| Selected root assertion | Dataset construction |
| --- | --- |
| `citation` | Whole scalar `citation` string |
| `rai:dataManipulationProtocol` | Whole strings in `cleaning_strategies[].cleaning_details` |
| `funder` | Whole strings or sole explicit reference IDs in `funders[].grantor` |
| `humanSubjects`, `humanSubjectResearch` | Shared approved human-subject rule: source-labelled description, conditional explicit boolean |
| `dataGovernanceCommittee` | Whole string in `data_governance.description` |
| `completeness` | Detached assertion evidence; no Dataset metric or slot is invented |

Immediate cleaning/funder string-list occurrences keep order, duplicates and
empty strings. Unsupported units remain raw evidence and are reported in
`dropped`; mixed lists are `partial`. References do not create grant identifiers.
Human-subject processing also records the consulted exemption, IRB and protocol
assertions and exact referenced graph candidates. It does not infer approval.
Covered `additionalProperty` assertions and `d4d:humanSubject` retain their
existing fitter behavior, with complete raw evidence. Explicit canonical
assertions precede singular legacy candidates; a superseded candidate remains
visible. The ordinary final Dataset validator still runs.

Each reverse evidence row records the selected-root source pointer, missing vs
null vs present state, exact parsed JSON value, target, decision and observed
final retention. `retained`, `partial`, `not_retained` and `not_constructed`
distinguish construction from the result after final validation. Legacy rows
join actual fitter admission, produced object identities and final settlement.
Equal competing values cannot both claim the same retained occurrence.
Failure resets the conversion state, retains this attempt's error and marks
constructed outcomes unknown. Accessors return detached copies.

For path inputs, `input.source_sha256` and `source_bytes` bind the exact bytes
acquired once and parsed, even if the path later changes. Dict inputs have no
original-file hash. Model evidence uses alias dumps with `exclude_unset=True`
and `exclude_none=False` to distinguish supplied null from defaults; it cannot
recover values before model coercion. The existing execution projection still
uses `exclude_none=True`. Unrelated root/member properties are not scanned for
new evidence. Serialize diagnostics using `ensure_ascii=True, allow_nan=False`.

Forward conversion emits a scalar citation, one text-only cleaning or funder
object, or an explicit research boolean as `Yes`/`No`. Rich or multiple scalar
candidates are preserved in outgoing diagnostics rather than concatenated or
first-picked. This is a typed projection, not literal JSON-shape equality.

`forward.convert(record, source_evidence=reverse.route_evidence)` optionally
re-emits separately supplied human, completeness and committee assertions when
they fit the declared model fields. The evidence must be complete, have the
finite known source roster, and bind the **entire** final Dataset via canonical
ASCII JSON SHA-256, including fields outside these routes. If an unrelated
schema-accepted value cannot receive that finite JSON binding, conversion still
returns it unchanged: `final_dataset_binding` is `unavailable`, its SHA is null,
and optional evidence reuse refuses. No unrelated value is sanitized or dropped.
Unsupported richer
assertions stay in diagnostics. Arbitrary governance prose does not establish
a committee name, and a research boolean does not establish `humanSubjects`.
Caller-supplied evidence is not authenticated file provenance; its input hash is
retained only under `supplied_source_evidence`, never claimed as a forward read.

This evidence is finite source-value recovery, not an archive of input files,
an all-fields round-trip guarantee, or publication/semantic-fidelity credit.

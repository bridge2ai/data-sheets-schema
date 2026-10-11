# FAIRSCAPE declared assertions

The paired converters expose a detached `route_evidence` dictionary alongside
their existing return values. The thirteen #4046 root assertions have finite
canonical constructions and explicit projection limits. No schema, mapping table, ranking denominator, or
scientific mapping-strength claim changes here.

| Selected root assertion | Dataset construction |
| --- | --- |
| `citation` | Whole scalar `citation` string |
| `rai:dataManipulationProtocol` | Whole strings in `cleaning_strategies[].cleaning_details` |
| `funder` | Whole strings or sole explicit reference IDs in `funders[].grantor` |
| `humanSubjects`, `humanSubjectResearch` | Shared approved human-subject rule: source-labelled description, conditional explicit boolean |
| `dataGovernanceCommittee` | Whole string in `data_governance.description` |
| `completeness` | Detached assertion evidence; no Dataset metric or slot is invented |
| `rai:personalSensitiveInformation` | Whole strings in `sensitive_elements[].sensitivity_details`; no confidentiality flag |
| `rai:dataCollection` | Scalar text in `collection_mechanisms[].mechanism_details`; no acquisition-method inference |
| `rai:dataSocialImpact` | Scalar text in `future_use_impacts[].impact_details`; no completed DPIA inference |
| `rai:dataAnnotationProtocol` | Whole strings in `labeling_strategies[].data_annotation_protocol` |
| `rai:dataAnnotationPlatform` | Whole strings in `labeling_strategies[].data_annotation_platform` |
| `rai:annotationsPerItem` | Exact integer or reversible ASCII decimal string in `annotations_per_item` |

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

The four independent compatibility carriers are `d4d:confidentialElements`,
`d4d:acquisitionMethods`, `d4d:dataProtectionImpacts`, and
`d4d:labelingStrategies`. Forward conversion preserves complete object/list
structure through ordinary model extras. Reverse conversion fits their explicit
objects with the ordinary final D4D validator, preserving internal
duplicates and order; malformed/unretained parts remain recoverable in evidence.
Carrier transport does not assert that its content is schema-valid.

One protocol, at most one platform, and an admitted count form an explicit
root-summary annotation group. Multi-platform or raw multi-protocol input instead
produces independent protocol-only, platform-only, and count-only records. There
is no zip, broadcast, workflow inference, or first-value selection. Matching
canonical projections of an explicit labeling carrier candidate are marked
`redundant_projection` and track its final retention. Conflicts append independent
canonical groups after the carrier. Duplicates inside a carrier are not removed.

An exact integer count projects to `str(value)`, and only ASCII `0` or
`-?[1-9][0-9]*` that survives `int` and exact string round-trip is decoded.
Booleans, floats, padded/decimal/exponential text and conversion-limit failures
are declined, with raw evidence retained. No new nonnegative bound is invented.
Sensitivity and platform use list-of-string wire fields. Multiple/richer
collection or impact objects have no scalar projection; their complete source
values remain in diagnostics. Rich annotation objects retain their full carrier
even when a finite protocol/platform/count projection is also available.

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

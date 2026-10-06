# Source-supported item reporting

`data_sheets_schema.attainability_aggregation` is an opt-in report over captured
source readings and existing semantic evaluations. It does not rescore records,
write source annotations, call a model, approve a campaign, or replace the fixed
and N/A-adjusted score bases. All declared curator/judge and scope decisions are
retained statements, not authenticated scientific judgments.

No E1.1 URI or unique-identifier policy is installed. Before interpreting that
item's alternatives, an owner must decide which URI/identifier evidence is
sufficient under the selected scoring instrument and whether the alternatives
are exhaustive. Changing the scoring interpretation needs a separately pinned
instrument/policy. A missing DOI/RRID does not establish whole-item absence.

## Running a selected report

Supply a version-1 `d4d-attainability-report-selection` JSON document with a
nonempty `rows` array. Every input is a recorded `Pin` with `path`, SHA256 and
byte count. Relative paths are resolved against the selection's directory only
at initial capture; pure replay never follows them. A bundle pin also carries
MD5, and every recorded hash must match. Inputs and existing reports are never
rewritten. Outputs must be new destinations.

```sh
python -m data_sheets_schema.attainability_aggregation \
  --selection selection.json --output new-result.json
python scripts/report_semantic_comparison.py evaluation.json \
  --attainability-selection selection.json --output new-report.md
python scripts/arm_comparison.py --no-figures \
  --attainability-selection selection.json --output new-arms.md
python scripts/reference_rescore.py report \
  --attainability-selection selection.json --report-output new-report-directory
```

The first command writes `{capture, report}`. The two Markdown consumers write
an adjacent `.attainability.json` containing the same envelope. The reference
consumer writes new `results.json`, `results.md` and a captured sidecar in the
new directory, retaining its frozen campaign/receipt checks. Its run/canary/
accept/recovery actions cannot use the reporting flags. `arm_comparison` requires
`--no-figures` and rejects `--check` with the new selection. Omitting the new
flags retains the existing reporting behavior.

The consumers join the actual evaluation bytes/paths they report to the explicit
selection. A selected evaluation outside that report refuses; a report's
unselected evaluations remain visible as unavailable in the added section.
There is no project-name, filename or percentage-based identity inference.

## Closed input contracts

All objects below are closed: unknown or duplicate keys, bool-as-integer
versions/counts, nonfinite numbers and duplicate logical identities refuse.
`Pin = {path, sha256, bytes}` and `BundlePin = {path, sha256, bytes, md5}`.
Hashes are lowercase hex. Paths are recorded identities, not approval.
`Decision = {kind, actor, reference, recorded_at, rationale}`, where kind is
`declared_curator` or `declared_judge` and the remaining values are nonempty
recorded strings. The timestamp is retained text, not a verified clock.

Each selection row has exactly:

- `evaluation`, `evaluated_input`, `generation_provenance`, `bundle`,
  `source_document`, `policy`: corresponding pins;
- `adjudication`: a pin or null; `context`: a pin or null;
- `scope_binding`: null (unavailable) or
  `{evaluation_scope_sha256, declaration, decision}`. Declaration must be
  `source_readings_cover_selected_subject_scope` and decision is a Decision.

The source document is an unchanged validated v1 attainability document. Its
bundle/rubric/chunk/evidence checks use the original validator with captured
bytes. Context uses the existing normalization and three-valued applicability
rules. Generated content is used to identify the evaluation subject scope; it
is never source support evidence. An all-resource collection scope cannot be
replaced by a decision about one sibling.

A policy has exactly `format`, `version`, `state`, `rubric`, `rubric_source`,
`scoring_contract`, `roster_sha256`, `items`, `denominator_rule`,
`partial_interpretation`, `decision`:

- Format is `d4d-attainability-item-policy`, version 1; state is `draft` or
  `declared`. Draft requires decision=null and yields unavailable aggregation.
  Declared requires a Decision, which is not a scientific approval certificate.
- Rubric is `rubric10` or `rubric20`; `rubric_source` pins its actual raw YAML.
  The complete ordered roster is reconstructed from those bytes, including
  item names, maxima and applicability expressions. Current rubric10 has
  E1.1–E10.5 (50 one-point items). Current rubric20 has Q1–Q20, with Q5/Q6/Q16
  worth one point and the others five, totaling 88.
- `scoring_contract` is `{kind, definition, output_schema, semantic_version,
  evaluator_contract_sources}`. Kind is `semantic-agent`; the definition/schema
  and every source are pins. Schema references must be local fragments; a fixed
  non-retrieving registry also guards instance and meta-schema validation across
  the supported JSON Schema dialects. This
  release reconstructs version-3 scope/applicability only when the captured
  `evaluation_context.py` and `judge_contract.py` identities match its fixed
  implementation. Other retained contracts are unavailable, never executed or
  silently reconstructed under today's source.
- Each item is `{item_id, maximum, applies_to, rule, routes,
  alternatives_complete, justification}`. Identity/maximum/applicability must
  equal the complete raw rubric roster. `whole_item_only` requires empty routes
  and false completeness; `any_sufficient` requires nonempty unique route names.
  Each declared route is sufficient for the whole item. Completeness is explicit
  and controls absence inference, never inferred from observed annotations.
- Denominator rule is `known_applicable_supported_points_v1`;
  partial interpretation is `positive_lower_bound_not_explicit_absence_v1`.
  `roster_sha256` hashes canonical `{rubric,rubric_source,items}` with each item
  `{item_id,name,maximum,applies_to}`. `roster`/`roster_digest` expose this purely
  structural construction without creating or declaring any policy.

An adjudication has exactly `{format,version,policy,source_document,
predecessor_documents,bundle,rubric,chunk_rule_sha256,resolutions}`. Its format is
`d4d-attainability-adjudication`, version 1. All pins must match the selected
policy/document/bundle/rubric. Predecessors must have the same rubric/chunk and
bundle identities; originals are retained rather than replaced.

A resolution is `{item_id,route,scope_entries,scope_sha256,resolved_status,
evidence,decision}`. Route must be null; only one resolution per item is allowed.
Status is supported/partly_supported/not_stated_in_source/unknown. Supported or
partial readings require verified source snippets. `scope_entries` is the exact
complete sorted item scope across the current and explicitly named predecessor
documents, each `{document_sha256,rubric,item_id,route,entry_sha256}`. Sort by
(document SHA, rubric, item ID, null route before named route). Entry SHA hashes
`{format:"d4d-attainability-entry-identity",version:1,entry:<complete v1 entry>}`;
scope SHA hashes the complete sorted list. A changed raw document invalidates an
old adjudication even when its parsed entries happen to be equal. The separate
old same-key writer preservation behavior is unchanged.

Canonical hashes use UTF-8 JSON, sorted string keys, compact separators,
ensure_ascii=false and finite numbers. No source text is canonicalized in place.
All original raw bytes remain in the closure. Invalid/tampered identities refuse
publication; genuine missing historical identity or incomplete readings produce
explicit unavailable/excluded rows.

## Interpretation and retained uncertainty

For registered sufficient alternatives, supported wins unknown or partial;
otherwise partial remains a positive lower bound. Complete all-absent alternatives
establish absence; missing/unknown alternatives or an incomplete set do not.
Whole-item absence conflicts with partial/full route support; complete route
absence conflicts with whole-item partial/full support. Whole-item unknown is
not a denial of positive route evidence. **Any unregistered named route blocks
the entire item before combining whole status or applying adjudication.** It
cannot yield eligibility or an absence allegation.

Eligibility requires resolved support, known applicability, a bound subject
scope and a usable original score. The numerator sums original item points; the
denominator sums their pinned maxima, not routes or item count. Partial support,
unknown/conflict, source absence and N/A remain separate exclusions. Unknown
applicability still belongs to the old adjusted denominator; only this explicitly
named new basis excludes it. Missing eligible scores make the entire new ratio
unavailable rather than shrinking the denominator. Zero eligible items show
attained=null, attainable=0, percentage=null. Missing identity/policy/scope makes
all three unavailable.

Current provenance output entries may be descriptive only. The report checks
recorded hashes in `validation.artifacts.full` and any older pinned `outputs.full`
against the evaluated input; it never creates a historical hash from a current
path. Missing evaluation metadata or provenance integrity stays unavailable.
Every contradictory recorded hash refuses. Original fixed/adjusted measurements
remain unchanged and are displayed alongside the new basis. Unsupported old
formats are not silently upgraded.

Positive scores on resolved whole-item source absence are reported as review
findings, not automatic scientific hallucination labels. No unregistered-route,
unknown or conflicting reading creates such a finding. Results retain complete
item inventory, exclusions, policy/instrument/bundle/context/scope identities,
raw entry hashes, adjudication and predecessor evidence. A curator label without
a retained predecessor does not claim retained override history. Eligible-item
signatures distinguish different denominators; this tool authorizes no pooling,
ranking, four-project annotation campaign or empirical heatmap refresh.

## Captured replay and limits

`capture(selection_path)` performs bounded initial file reads.
`recheck_captured(capture)` rederives the result after approved module imports,
using raw retained blobs only: no path lookup, Git, network, process or scoring.
It checks the exact source implementation roster and refuses unrelated/missing/
duplicate blobs. A supplied report is accepted by report consumers only if it
exactly equals rederivation. Returned dictionaries do not mutate future results.

Defaults (caller `Limits` may only lower them): 256 rows, 2,048 unique blobs,
8,192 pin references, 256 MiB decoded / 384 MiB encoded closure, 16 MiB aggregate
parsed-input plus complete derived-result metadata (repeated fields count), 8 MiB selection, 64 MiB bundle, 16 MiB input/evaluation,
4 MiB document/policy/adjudication/context/rubric and 8 MiB other source per blob;
64 metadata depth, 1,000,000 nodes, dependency depth 8, 32 policies,
8 predecessors, 4,096 entries per v1 document, 32 routes per item and
128 snippets per reading/resolution. The closed dependency graph has four levels;
a smaller permitted depth refuses it. Deep/cyclic/duplicate/nonfinite metadata
refuses before publication. Bounds describe this new opt-in contract, not a
hard CPU/RSS guarantee or new restrictions on the legacy v1 API.

Tests use fictional source readings and ratings, retain raw before/after default
outputs, and exercise the actual three reporting boundaries plus captured-only
validation. They establish engineering behavior, not scientific validity.

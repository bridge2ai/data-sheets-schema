# Registered source-heading API routing

This explicit API condition implements the delivery boundary of
[#2931](https://github.com/bridge2ai/data-sheets-schema/issues/2931). It does not
approve the draft correspondences, launch a canary, or implement native routing.
`shared_generation_v2` uses renderer **27**, API playbook **3**, and receipt
completion **3**. Renderer 26 remains reserved for the separate native shared
protocol. The existing shared v1, ordinary defaults, and offline draft compiler
keep their selections and formats.

## Capture the selected evidence

Use `source_heading_runtime.prepare_condition(...)` with exact bytes, then
`check_condition(raw)` to reconstruct the complete result. This wraps the
[existing offline draft compiler](source-heading-routing-drafts.md); it rebuilds
its actual catalog, candidates, predicates and directions. Supplying a edited
projection is not an alternative authority. Captured data paths are identities,
not files reopened by this pure check; the fixed compiler still verifies its
installed software resources.

Two distinct modes require explicit selection:

| Mode | Condition | Membership |
| --- | --- | --- |
| `captured_json_values_v1` | `generic_v10_source_heading_routing_v1` | Every matched local and external complete JSON string occurs verbatim within one selected document. |
| `declared_heading_spans_v1` | `generic_v10_source_heading_span_v1` | Exact caller-selected heading and complete passage spans, with a separately sourced, draft label-to-property declaration. |

Neither mode falls back to the other. Missing source-local URI declarations in
strict mode stay unsupported. The declared mode does not assert that the source
publisher used that URI or that two strings are semantically equivalent.

The preparation API requires `draft_files` (all seven original draft artifacts
as a bytes map), `mode`, complete selected `bundle` and canonical `manifest`
bytes, explicit `selection` JSON bytes, and `max_projection_bytes`. Declared
mode also requires `crosswalk` JSON bytes and a `source_evidence` map of control
names to bytes. Those control bytes can explain a draft declaration but cannot
contribute new factual text to the model context.

Strict selection uses `format: source_heading_value_membership_v1` and `rows`.
Each row contains `evidence_id`, `value_kind` (`local` or `external`),
`document_ordinal`, `document_sha256`, and a half-open raw UTF-8 `byte_range`.
Rows must exactly cover both values of every structurally matched record.

Declared crosswalk uses `format: source_heading_span_crosswalk_v1`,
`authority_status: draft/unreviewed`, and rows with `id`, `heading`,
`property_uri`, and `evidence`. Evidence references contain `source`,
`byte_range`, `sha256`, and a nonempty declared `basis`. Selection uses
`format: source_heading_span_selection_v1` and rows with `id`,
`crosswalk_rows`, `document_ordinal`, `document_sha256`, `heading_range`,
`passage_range`, and `closing_boundary_range` (a complete next line, or null
only at that document's EOF). The software validates the declared boundary;
it does not discover or scientifically approve the semantic scope.

Ranges address the original bundle bytes, preserving CRLF and multibyte UTF-8.
An occurrence can span adjacent canonical chunks within one document. Complete
ordered chunk coverage is checked; joining different documents is forbidden.
Document ordinals distinguish repeated occurrences, even with equal filenames
or bytes. The delivered projection includes the entire enclosing documents,
including parent qualifications, other headings and negations, plus every
catalog candidate and its original direction/predicate. It does not select one
candidate as the correct placement. A worker's original target assignment and
response-credit rules remain unchanged.

The capture and complete encoded projection are bounded at 64,000,000 bytes;
callers must also supply their smaller complete-wire limit. There are at most
512 document occurrences and 512 selected/crosswalk rows. Oversize content is
refused, never truncated. The actual original Completeness fixture retains six
spans across three enclosing documents; its strict missing-prefix result stays
matched 0 / unsupported 1. This is source-membership engineering evidence, not a
validated correspondence or evidence that a model improves.

## Register and inspect the API condition

Start with the complete explicit fields described in
[shared-generation API registration](shared-generation-api-v1.md). For this
condition the outer format is `shared_generation_registration_v2` and the
selection is obtained from
`shared_generation.descriptor(version=2, condition=...)`. It binds the selected
policy bytes and routing implementation. `receipt` uses
`receipt_completion_registration_v3`, the same selected condition, and the v3
policy identity. All existing explicit schema, context, project, profile,
provider, model, thinking, effort, receipt and audit declarations remain
required. No model or empirical threshold is chosen by the software.

The additional `routing` object has exactly:

- `mode`: one of the modes above;
- `artifact`: the ordinary `{path, sha256, bytes}` pin for the prepared capture;
- `generation_limits`: positive integer `max_request_bytes`,
  `max_input_tokens_per_call`, `max_output_tokens`, `context_limit_tokens`,
  `max_calls`, `aggregate_input_tokens`, `aggregate_output_tokens`, and a
  nonempty `context_limit_basis`.

These generation limits cover ordinary phases, independently of the receipt
and typed-audit limits. There are at most 512 ordinary calls, and each complete
request is bounded at 64,000,000 bytes. Output allowances must leave input
context. The selected capture must bind the exact full-schema closure, bundle
and chunk manifest already registered for the run. Keeping a separate source
archive does not place its facts in the selected bundle.

Inspect without a client or token-count call:

```bash
d4d api plan --project "$PROJECT" --label "$RUN_LABEL" \
  --shared-generation-version 2 \
  --shared-generation-registration /absolute/caller-inputs/registration.json

d4d api render-prompt --project "$PROJECT" --label "$RUN_LABEL" \
  --shared-generation-version 2 \
  --shared-generation-registration /absolute/caller-inputs/registration.json
```

`run` and `batch` accept the same explicit selection; batch retains the exact
per-run registration roster. Those execution commands can make paid calls and
are separate from preparing or reviewing a draft. No test or plan authorizes
scientific comparisons or a campaign.

## Actual delivery and saved recheck

Every model phase receives the exact selected projection alongside its original
complete context. Core derivation and rederivation are deterministic operations;
they make no model or token-count calls and receive no invented model phase.
The real dispatcher counts the normalized complete ordinary request before
admission. Known byte, model-setting and output-limit failures precede counting.
The SDK count endpoint intentionally omits the requested output cap; the saved
logical request and context check still bind it. Unknown or excessive counts
refuse. Selected ordinary calls use one transport attempt and SDK retries zero.
Existing separately registered receipt and typed calls retain their admission
rules.

The existing durable usage transaction binds a generated usage ID to exactly
one prepared phase/attempt/request/count row before sending. The actual wire
must equal that counted request. After a complete response, reported usage is
persisted before fallible routing reconstruction or response-snapshot writes
(#4480). Later bookkeeping enriches that same usage ID rather than charging a
second call. Missing response evidence remains an unresolved admission: saved
recheck refuses and cannot buy a replacement. Endpoint counts and reported
usage are observations, not cryptographic provider authentication or guaranteed
hard expenditure caps.

Final publication and completed resume recheck the exact ordered request,
count, response and usage associations, original authority and existing typed
assembly. They make no model or count requests. This ordinary API completed
path still requires the original registered files and their identities; it is
not a relocatable native evidence pool. Provenance uses the distinct v2 block
and retains `scientific_eligibility: false`. The original v1 block does not gain
routing fields or accept a v2 protocol with no routing evidence.

Native consumption, successful target-canary evidence, approved correspondences
and scientific arm/comparator decisions remain unfinished under #2931. An API
engineering result does not close those requirements.

## Completed selected readback

A successful selected v2 run exports a bounded completed capture in its owned
metadata directory, only after the captured-only checker reconstructs all
mandatory checks. `d4d api check-routing-completed CAPTURE` rechecks that closed
byte set without counting tokens, sending a model request, settling usage or
writing run artifacts. Ordinary `api execute` retains its live authority and
ownership checks. Export refusal does not make an incomplete capture complete.

The supported relocation moves the original corpus, configuration, schemas and
run artifacts while retaining their logical identities in the capture. The
reader requires matching installed implementation, Python major/minor, schema
validator package versions and schema-instrument resource layout. In particular,
LinkML package imports keep their original logical identities: moving an equal
package to a different virtual-environment path currently refuses rather than
rewriting those identities or reading a current schema fallback. This is not a
cross-installation or cross-platform portability claim.

The independent request comparison uses the actual `PHASE_NEEDS` roster,
deterministic core derivation and every recorded ordinary/typed/receipt stage.
Captured LinkML validation delegates to the installed generator on an owned
captured import view, preserving ordered import precedence, class/slot
inheritance and the CLI's closed validation semantics. Original captured paths
are not opened or resolved, including during error reporting. Scientific
eligibility remains false; these checks do not adjudicate the draft crosswalk.

Captured path displays retain the producer's core-source spelling and canonical
bundle name, joined to the exact logical inputs, chunk manifest and reconstructed
original/final core headers. They record a historical producer result; they do
not independently attest a filesystem that is no longer available. The live
path helpers retain their original alias behavior.

Selected v2 form measurement captures the actual default naming instrument's
bytes (or absence) at its naming lookup, together with the exact full/core bytes
consumed by that invocation. It does not substitute the selected source
manifest's naming policy. The durable generation-bound observation and original
provenance form must agree with captured reconstruction. Form analysis preserves
live universal-newline decoding, while artifact hashes still identify the raw
bytes. Legacy/default form measurement retains its original input/read behavior.

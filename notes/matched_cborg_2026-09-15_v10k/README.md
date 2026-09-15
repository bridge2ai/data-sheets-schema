# v10k matched generation canaries — first API attempt stopped

The first CHORUS API request stopped with a transport error and no delivered D4D
text. Its 12 original files are preserved. Accounting remains unresolved; the
$3.539750 reservation is retained. No agentic canary or evaluation has launched.
See the [attempt outcome](CHORUS_api_stopped.md) and [follow-up #1831](https://github.com/bridge2ai/data-sheets-schema/issues/1831).

This condition applies the reviewed evidence fixes in [PR #1819](https://github.com/bridge2ai/data-sheets-schema/pull/1819)
to both API and agentic generation. The implementation base is
`94099081c2b64cb704589ecab3812bf20bb4c0e0`. The merged tree exactly matches the
approved engineering head, `b7c20719fd5ddb140a11d3330f522b03754be5ca`, whose four
required CI shards and aggregate gate passed. The
[full review](engineering_review/round6.md) identified #1829; the
[follow-up review](engineering_review/round7.md) approved its fix with no
material findings. All 97 final targeted checks passed. Independent registration
review and required CI passed on frozen launch commit
`19a5248e4d1fd2dd8e0b28b794b1c315c7915778` before the API attempt.

Both arms explicitly select renderer 9 and the shared evidence protocol.
`evidence_assertions v1` checks declared source quotes, original-artifact
assertions and relationship removals. Remaining selected members must retain
their structured content; narrative description, notes and source_caveats may
change. Other structured changes make removal ambiguous and stop the check.
Independent source review still establishes semantic support and completeness.
Historical renderer defaults and report-claims v8 results are preserved.

The current agentic arm starts the pinned Claude Code executable and uses this
repository's CLI through CBORG. It does not require Aurelian. This registration
was prepared with the Aurelian submodule uninitialized; older generation
wrappers that import Aurelian are separate entry points.

## Exact registration

- Local registration SHA256: `5f7cf55e216c56ee0712e07b24f4442eae0a9ba4bfb893ee30d25c07f4f1ea0c`.
- Native overlay SHA256: `817f4e16a2fa119cdee8f39497d00d9ba0747d2b02c92f951cddd21d7f7807ff`.
- [Public registration](registration.public.json), [native overlay](native_overlay.public.json)
  and [launch inventory](launch_input_inventory.json) expose reviewable metadata
  and hashes. Machine-specific paths are substituted; these views cannot launch jobs.
- [Offline preflight](offline_preflight.json) verifies 463 registration pins,
  eight native pins, 3,241 historical files and 325 prior original files. All
  32 instructions and 16 initial API requests rebuild exactly. The 64 output
  directories were distinct and unused at preflight. The independent source-review
  plans
  cover each attributed clause, original qualifiers/headers, actual relationship
  removal, and observed native snapshot hashes and ordering.

The initial preflight identified an additional pyproject change since v10j.
Inspection confirmed that #1813 only corrected the pytest corpus-marker
description; dependency and build configuration are unchanged. The final
preflight records that difference explicitly.

Sources, manifests, chunks, profiles and effort policy match v10j. The
[current CBORG catalogue check](model_catalogue_check.json) confirms the same
`claude-opus-5` route, prices and capabilities. API generation uses adaptive
provider default; agentic generation uses runtime default, observed separately.
No matched realized reasoning effort or deterministic generation is claimed.
The template family remains `generic_v9`; the scientific condition is the
new `generalized_v10k` cohort with this registration hash and renderer 9.

## Sequence and budget

Run CHORUS API first. Acceptance of its unchanged originals gates CHORUS
agentic, then Kids First API, then Kids First agentic, with independent review
after each. Each pair uses identical frozen source bytes and produces a full
D4D and a mechanically derived core. Stop expansion on failure; there is no
automatic whole-attempt retry. The first API launch had a fresh preflight and
review receipt; no scientific acceptance receipt exists. The stopped attempt
does not authorize an automatic retry.

| Generation canary | Proposed whole-attempt cap |
| --- | ---: |
| CHORUS API | $6.78 |
| CHORUS agentic | $6.50 |
| Kids First API | $15.00 |
| Kids First agentic | $15.00 |

The [proposal](retry_proposal.json) totals $43.28 of new maximum exposure.
Together with $20.462732 spent in applicable earlier canary attempts, that is
$63.742732, within the existing $63.75 combined ceiling. CHORUS agentic's cap
is reduced from $10 to $6.50 to remain within that ceiling; this does not show
that the attempt will fit. Before launch, 39 settled requests totalled
$29.391638. The stopped request now holds $3.539750 unresolved,
leaving $167.068612 uncommitted from the additional $200. Its provider log reports
$0.267175, but does not establish complete billable usage. Retain the reservation.
The earlier approval of one v10j attempt was used; the v10k launch instead
recorded the current active goal directing this new condition. A fresh retry
would need its own registration, accounting review and applicable launch receipt.

[Initial sizing](api_initial_admission.json) is local only. Its conservative
byte-based scenarios reserve $4.14804375 for the first CHORUS API request and
$7.98318750 for Kids First. These are not verified tokenizer bounds, actual
token counts, live admission or whole-attempt forecasts. The actual first
CHORUS request counted 44,446 input tokens and reserved $3.539750 before sending
generation. Unknown charges retain reservations and stop execution. Fresh
model, input and accounting checks remain required for any later attempt.

## Sources and evaluation

Use existing downloads for all five Bridge2AI datasets: CHORUS, AI_READI,
CM4AI, VOICE and VOICE_PEDIATRIC. The pediatric/adult source overlap remains
disclosed. Kids First retains 55 documents, links and descriptions for 36
participating studies under the neutral profile. Its paper representation is
indexed metadata and abstract; publisher full text was unavailable. No new
downloads were made for this registration.

The [workload inventory](workload.json) retains 32 full/core pairs, 256
enumerated rubric ratings including repeats and 80 evaluator-canary ratings,
and 128 offline presence scores. It covers rubric10/rubric20 presence and
semantic styles, direct API quality and field-agent canaries. Applicable
grounding, fitness, subtype, receipt, provenance and report checks remain in
the plan; additional paid styles need explicit counts and budgets before
expansion. Register accepted input hashes, trusted applicability, instrument
definitions, output paths and budgets before evaluation. Prepend pinned agent
preambles and verify check-echo; numeric semantic ratings use CBORG.

The sum of proposed generation and enumerated rating caps is $1,463.28,
which is exposure rather than a cost forecast or a funded batch. Empirical
canary costs must determine an affordable expansion within the shared ledger.
Preserve v7/v8, historical v9, every stopped or rejected condition and old
scores. Keep disputed historical adjudication separate from the matched new
comparisons. One canary does not establish repeatability.

See the [dated continuation plan](../matched_cborg_evidence_canaries_2026-09-15.md).

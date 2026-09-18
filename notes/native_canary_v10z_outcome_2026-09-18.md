# v10z CHORUS native canary outcome, 2026-09-18

The v10z CHORUS native canary ran through CBORG with `claude-opus-5` and stopped during audit preparation after an upstream HTTP 524 response. It preserved a full D4D, derived core, corrected coverage receipt and frozen originals. No audit, reconciliation report, evaluation or accepted final D4D was completed.

The attempt ran from 07:53:31 to 08:47:13 UTC on September 18. It used the [frozen v10z registration](https://github.com/bridge2ai/data-sheets-schema/blob/8468b8f3cdb8701c246ac50c103746669706bc07/notes/matched_cborg_2026-09-18_v10z/README.md) after [successful CI on the launch commit](https://github.com/bridge2ai/data-sheets-schema/actions/runs/35320956124):

| Identity | Value |
|---|---|
| Launch commit | `8468b8f3cdb8701c246ac50c103746669706bc07` |
| Registration SHA256 | `d4810ca2d8784382ae397527ca2344637a39a807888a53252e2ca34b5eb8553f` |
| Native overlay SHA256 | `b05dcf111e74d47be7da7253f514eda7832e3ed5c247792824cf63fd711b440e` |

## Observed progress and stop

All eight source chunks were read in order, with successful receipt writes before each next initial chunk read. Full schema and term validation passed. The first strict receipt check failed on 20 stale slot references and one chunk-status entry; permitted Phase 1 correction followed. The next check passed with 8/8 chunks and 88/88 literal snippets verified, before core derivation. Core schema validation passed.

The actual freeze command then printed full/core hashes that match the preserved originals. A source-inventory command succeeded and enumerated 218 full-record scalar values; the model read its persisted output. No audit file or audit evidence-validation result followed. Reconciliation and final pair/provenance checks were never completed.

The controller recorded the stop reason as `upstream HTTP response did not confirm a completed charge`, with source `proxy`. There were zero unfinished handlers at freeze. Its control history reconciles 98 Bash and 38 file calls with 136 decisions, with no phase-order problems or disqualifying denials. Four forbidden/unprescribed command denials were recorded separately; the corrected Phase 1 receipt failure was not the terminal cause.

Of 129 admitted requests, 128 are settled and one remains pending with its reservation retained. A read-only accounting lookup found a time/model candidate, but exact attribution and the complete charge remain unconfirmed. Detailed accounting and request identifiers remain private. [#2101](https://github.com/bridge2ai/data-sheets-schema/issues/2101) addresses missing captured upstream response headers for future diagnosis; that diagnostic change cannot resolve the upstream timeout tracked in [#1849](https://github.com/bridge2ai/data-sheets-schema/issues/1849).

## Unresolved findings in the originals

Independent review recorded seven findings before the model's audit. They persist in both frozen originals because every shared scalar is unchanged. They are unresolved draft findings, not evidence of a failed or completed reconciliation:

- Typed maintainer, creator and data-collector roles exceed the cited evidence for a program contact, project leadership and consortium membership, respectively.
- Two occurrences omit the anticipated-final scope governing the 60+ member/20-institution quantity.
- A request that sites submit status updates becomes a claim of regular site adherence.
- Relative timing is asserted between the dated webinar count and an undated homepage count.
- An exclusive declaration of source slides used contradicts the record's other webinar citations.

The previous category-as-variable defect is absent, and the draft does not manufacture a numerical conflict between 45,000-plus and 50,000 admissions. These improvements do not establish final source support. [#2079](https://github.com/bridge2ai/data-sheets-schema/issues/2079), #1782, #1815, #1801 and #1816 remain acceptance follow-ups. No audit classifications, reconciliation claims or numeric evaluation scores were available to judge.

## Preservation and next stage

The private archive contains 1,021 files and 115,643,750 bytes. Independent physical traversal included hidden and ignored files; all source/archive sizes and hashes match. Terminal checks also verified 495 registration pins, 14 native pins, 3,830 prior-attempt artifacts and 3,241 historical files.

| Retained artifact | SHA256 |
|---|---|
| Full / original full | `8ecd9a7e6e887185f279f472e71cf8891f722dcaccfa54ceb2a65e590d304af3` |
| Core / original core | `e7bafeb0cd317c94f92cc887493b7c04984e021998cb9b24f48787239661a999` |
| Corrected receipt | `359d87ae2b112142512d0927adff8869b00c7712b0143bd8027ae2e9acfed391` |
| Terminal transcript | `06403319beb104edd0626a645959fdaa90d553d0a9c83d868cb94ca62a6de951` |

This condition is consumed. Its measured artifacts remain unchanged; a retry requires a fresh reviewed condition under the standing CHORUS authorization and resolution of the observed stop.

The merged [evaluation runner #2098](https://github.com/bridge2ai/data-sheets-schema/pull/2098) and [offline preparer #2100](https://github.com/bridge2ai/data-sheets-schema/pull/2100) passed [runner CI](https://github.com/bridge2ai/data-sheets-schema/actions/runs/35324031109) and [preparer CI](https://github.com/bridge2ai/data-sheets-schema/actions/runs/35325038477). These preparations support subsequent registered evaluations; execution remains conditional on an independently accepted CHORUS pair, pinned instruments/applicability, accepted input hashes, output paths and costed workload. No evaluation was launched on this unfinished pair.

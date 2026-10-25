# N2 unit4 validation and handoff — 2026-10-25

Refs #4354. Evidence cutoff: frozen unit4 source
`2db091164469401d82cb7dd10ffd425658a1351c`. The scanner repair and both positive
public-adapter acceptance fixtures are **PENDING**. This note does not claim a
green current full suite, publication/merge, actual native execution or scientific
acceptance. All work described here is offline.

## Four-unit delivery state

These are local branch heads, not freshly verified GitHub heads. Counts belong to
the specified runs; overlapping tests and different source heads are not summed.

| Unit / branch | Local delivery head | Completed verification and limit |
|---|---|---|
| 1 — `codex/n2-1-protocol-selection` | `44deb52206e4499cac93cd404970d5e753022f86` | **235 passed**, zero failures/errors/skips, one dependency warning, 227.03 s at this frozen head. Nine modules cover protocol/selection/rendering and unchanged API/schema regressions. An earlier run failed the notes-preservation guard and remains a failed run. |
| 2 — `codex/n2-2-controller-receipts` | `ec9ebf240b9b9addd8c576608eca77f13be5da15` | **310 passed** at `0d5bddbc0` in receipt/API/backfill/derive/origin regressions; **267 passed** at final code head `f719de581` in cache/permission/controller/stage regressions. The included 73 parser tests are not an additional count. Delivery head adds validation notes only. See the [unit2 evidence](native_n2_validation_2026-10-25/README.md). |
| 3 — `codex/n2-3-permission-guards` | `3098aa6d77b0c34458a91d67848512a5f047dcc6` | **354 passed** at code-identical `8d2460cd9`; **4 public-front-door tests passed** again at delivery head after the notes-only restack. The restack preserved every `src/` and `tests/` byte. These are synthetic guard/probe fixtures, not a genuine binary or subscription observation. |
| 4 — `codex/n2-4-alignment-acceptance` | `2db091164469401d82cb7dd10ffd425658a1351c` | Full offline render parity completed. First scanner/acceptance-utility group: **404 passed / 11 failed / 21 errors**, 676.50 s. Separate synthetic pre-dispatch failure/readback test: **1 passed**, 31.34 s. Scanner repair and two positive completion gates pending. |

The primary coordination record is
[STATUS.md](/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/notes/coordination/STATUS.md)
under `### codex`; its absolute local path is
`/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/notes/coordination/STATUS.md`.
The [series note](native_n2_series_2026-10-25.md) records the source cut and split.

## First frozen unit4 group: failed and retained

At `2db091164`, the six-module scanner/acceptance-utility group completed with
**404 passed, 11 failed, 21 errors, zero skips**, 676.50 s. The JUnit roster has
436 cases. Evidence:

- [Frozen group log](native_n2_validation_2026-10-25/unit4/d4d-codex-n2-4-2db091164-checks.log), SHA256
  `fee651e5e286eae14271181a565c020f6cd9e5144d0cd7430dfaabcb01811735`.
- [Frozen group JUnit](native_n2_validation_2026-10-25/unit4/d4d-codex-n2-4-2db091164-checks.xml), SHA256
  `7abd74a11d6439248bf3e260e2796b9021693bebcd3651bdda44b62e6cf3a5dd`.

Independent log/XML classification found all **32 nonpasses** end in the same
`ConfigError: shared selector call guards/order changed`, at scanner line13406.
All are within `tests/test_generation_specificity_skill.py`. The 21 errors are
`TestApiMeaning` setup failures. The 11 failures comprise exit status(1),
discovery(2), native route(2), native procedure(1), fail-loudly derivation(1) and
whole-audit(4). No independent terminal failure root appeared in this run.

The preceding `unvalidated optional gate spec.receipt_completion_version` and
`unsupported optional selector shape` exceptions each occur 32 times as attempts
within the same derivation fallback chain. They are not 64 additional failures.
The final scanner assumption expects an unconditional constructor-level API
selector, whereas the reviewed unit1 code first validates native selection at
`api_runner.py:597–598` and invokes the protected API selector only inside
`if not self.native_shared_generation_version` at696–698. The scanner fails closed.
This diagnosis does not establish that later assertions will pass after repair.

The isolated scanner repair is under adversarial review. Its development checks
are not credited as final unit4 acceptance. The final repair, source head and
complete group rerun must be recorded after integration; production selection
guards and the protected shared selector must remain intact.

## Synthetic failed publication/readback check: passed

The unchanged `2db091164` source passed
`tests/test_native_shared_execution_failure.py::test_public_pre_dispatch_failure_is_readable_and_cannot_resume`:
**1 passed, zero failures/errors/skips, 13 deprecation warnings**, 31.34 s.
The warnings are one dateutil UTC warning and twelve LinkML/Pydantic warnings.

- [Failed-publication log](native_n2_validation_2026-10-25/unit4/d4d-codex-n2-4-2db091164-failed-publication.log), SHA256
  `3a980a74e815d83b25e169a83570d1b730610feef9f67cd3e5fac793e0336afe`.
- [Failed-publication JUnit](native_n2_validation_2026-10-25/unit4/d4d-codex-n2-4-2db091164-failed-publication.xml), SHA256
  `3c1c970ed2ce05a4cc8f42937146cc37358a26bf105d34f7c4bb06ef07789626`.

All four retained evidence copies preserve the corresponding original basename
under `/private/tmp/` byte-for-byte. Later full-case acceptance archives belong
in owned `d4d-executions` evidence as well as their initial scratch location.

“Publication” here is a synthetic local failure-artifact path, not publishing a
PR, launching a real Claude binary or calling a provider. This negative-path pass
does not establish successful receipt-to-record completion.

## Render parity and remaining positive gates

The exact-head render report is
`/private/tmp/d4d-native-n2-parity-2db091164/report.json`, SHA256
`30316a935b000fd1afc83464b3babdca30685edbeb37ee730b2ddf51ee28da8d`.
It records source Git tree `25557cb3f1eb381243f5008c4a017677e44d9f91`, stable
source/inputs, a completed offline render, equal 25,589-byte uniform sections and
one exact 4,433-byte current R9 passage per arm. Scope remains
`hypothetical_current_package_render_not_registered`; scientific acceptance is
`not_assessed`. Runtime limits/identity in that fixture are not approved launch
declarations.

Earlier complete r1 text/diffs and the structured recorder comparison are retained
under [render evidence](native_n2_render_evidence_2026-10-25/), with the
[independent delta review](native_n2_parity_delta_review_2026-10-25.md).
The [declared differences](native_vs_api_generic_v10_declared_differences.md)
include the current API-only report clarification, changed R9 relative to N1b,
effective schema/policy exposure and receipt-floor differences. Shared rule
equality does not establish identical effective inputs or scientific equivalence.

Both positive default-profile fixtures remain **PENDING** at this cutoff:

- `tests/test_native_shared_execution.py::test_actual_public_correction_three_workers_and_saved_completion`
- `tests/test_native_shared_execution_variant.py::test_actual_public_merged_omissions_and_all_chunk_statuses`

Run them on the clean final integrated source with their unchanged **900-second**
runtime limit and **180-second** recorder-helper timeout. Retain exact commands,
source identities, logs/JUnit, saved results and readback evidence. A credited pass
must reach checked terminal completion, saved readback and repeat-launch refusal;
`scientific_acceptance` still remains `not_assessed`.

## Historical failures and AGY handoff

The [15-row disposition ledger](native_vs_api_generic_v10_declared_differences.md#every-n1c-3-failure-and-its-disposition)
preserves the older complete N1c run at `2a9c60d43`: **22,363 passed / 15 failed /
zero errors / 46 skipped**. It is historical failed evidence, not a current full
suite. Rows1–14 remain profile1 failures, deferred and unfixed on the preserved
owner lane. Row15 is the default neutral recorder timeout and remains unresolved
until fresh final-head positive acceptance evidence establishes completion. Its
earlier omission counterpart pass does not waive it. No failure is closed by
excluding it from the default-profile source cut.

After local repair and acceptance review, AGY owns publication/integration and
must record the exact four delivered heads, reviewed diffs, exact-head full CI,
and merged-byte/merged-head verification. The N2 base `7c1002cae` records the D32
decision but does not implement A12/A13. Their later API caps, call budgets and
`receipted_part` denominator require separate integration review and reruns; native
v1 retains its whole-final-record denominator unless explicitly revised through
its own reviewed condition. Do not infer compatibility from `generic_v10` alone.
Recheck parity and affected receipt/controller/registration routes on the actual
integrated head. No push, GitHub or merge was performed for this handoff.

Real-binary permission compatibility, fresh genuine subscription/account evidence,
owner-selected model/effort/caps, a registered native canary and explicit launch
authorization remain later gates. Human applicability and audit-recall review,
receipt scientific interpretation and native rating-route decisions remain
separate. This note grants none of those approvals.

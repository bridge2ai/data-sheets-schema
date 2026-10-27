# N2 unit4 validation and handoff — 2026-10-25

Refs #4354. Final tested unit4 source:
`01969cbed8eed93f420c640c1f1c306e5f58b033`. The local series is ready for review,
but **native acceptance is blocked**. The repaired scanner group passed; the
neutral public-adapter fixture failed at the recorder's 180-second helper timeout,
and the omission fixture was not run. This note does not claim a green current
full suite, publication/merge, actual native execution or scientific acceptance.
All work described here is offline. The final documentation/evidence delivery head and
source/test-byte verification will be recorded separately in STATUS.md.

## Four-unit delivery state

These are local branch heads, not freshly verified GitHub heads. Counts belong to
the specified runs; overlapping tests and different source heads are not summed.

| Unit / branch | Local delivery head | Completed verification and limit |
|---|---|---|
| 1 — `codex/n2-1-protocol-selection` | `44deb52206e4499cac93cd404970d5e753022f86` | **235 passed**, zero failures/errors/skips, one dependency warning, 227.03 s at this frozen head. Nine modules cover protocol/selection/rendering and unchanged API/schema regressions. An earlier run failed the notes-preservation guard and remains a failed run. |
| 2 — `codex/n2-2-controller-receipts` | `ec9ebf240b9b9addd8c576608eca77f13be5da15` | **310 passed** at `0d5bddbc0` in receipt/API/backfill/derive/origin regressions; **267 passed** at final code head `f719de581` in cache/permission/controller/stage regressions. The included 73 parser tests are not an additional count. Delivery head adds validation notes only. See the [unit2 evidence](native_n2_validation_2026-10-25/README.md). |
| 3 — `codex/n2-3-permission-guards` | `3098aa6d77b0c34458a91d67848512a5f047dcc6` | **354 passed** at code-identical `8d2460cd9`; **4 public-front-door tests passed** again at delivery head after the notes-only restack. The restack preserved every `src/` and `tests/` byte. These are synthetic guard/probe fixtures, not a genuine binary or subscription observation. |
| 4 — `codex/n2-4-alignment-acceptance` | Tested source `01969cbed8eed93f420c640c1f1c306e5f58b033`; final documentation/evidence delivery head recorded in STATUS.md | Full offline render parity completed. Repaired scanner/acceptance-utility group: **445 passed**, 500.62 s. Earlier **404 passed / 11 failed / 21 errors** run remains retained. Synthetic pre-dispatch failure/readback: **1 passed** at `2db091164`. Neutral positive fixture: **1 failed**, 732.42 s; omission counterpart **not run**. Native acceptance blocked. |

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

The scanner-only repair passed independent adversarial review and was integrated
as `01969cbed`, preserving the production selection guards and protected shared
selector. Its development checks are not added to the final group count below.

## Final frozen scanner/acceptance-utility group: passed

At `01969cbed8eed93f420c640c1f1c306e5f58b033`, the complete six-module group
passed **445 tests, zero failures/errors/skips**, one dependency deprecation
warning, in **500.62 s**, process exit0. The scanner blocker is resolved at that
source; the earlier failed run remains preserved and is not relabelled.

- `/private/tmp/d4d-codex-n2-4-01969cbed-checks.log`, SHA256
  `7a95ed7f9b543b4628d2888ab2d24fb3b383d7d1938ca54acfa7cb1f2e97dc6c`.
- `/private/tmp/d4d-codex-n2-4-01969cbed-checks.xml`, SHA256
  `36068daa43bb6c76ea38baf1e77cde68f3c2b324830060d54f28ba4481b16dfb`.

Copies are retained in `notes/native_n2_validation_2026-10-25/unit4/` with
these same basenames. This is the bounded scanner/utility roster, not the current
repository's full suite or successful public native completion.

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

## Final-source render parity

The exact-head render report is
`/private/tmp/d4d-native-n2-parity-01969cbed/report.json`, SHA256
`4860510d6dc18f112e09309c1d065059aa295c58f39c91681007d28b04cca921`.
It records source Git tree `25557cb3f1eb381243f5008c4a017677e44d9f91`, stable
source/inputs, a completed offline render, equal 25,589-byte uniform sections and
one exact 4,433-byte current R9 passage per arm. Scope remains
`hypothetical_current_package_render_not_registered`; scientific acceptance is
`not_assessed`. Runtime limits/identity in that fixture are not approved launch
declarations.

Independent review against both the retained `2db091164` render and reviewed r1
found no new scientific or procedural instruction text differences. The API
instruction is byte-identical; native differences are evidence-directory path
substitutions and the resulting registration hash. The production `src` Git tree
is the same as `2db091164`; the final scanner repair changes its own scanner and
tests. The earlier exact-head report remains at
`/private/tmp/d4d-native-n2-parity-2db091164/report.json` (SHA256
`30316a935b000fd1afc83464b3babdca30685edbeb37ee730b2ddf51ee28da8d`).

Earlier complete r1 text/diffs and the structured recorder comparison are retained
under [render evidence](native_n2_render_evidence_2026-10-25/), with the
[independent delta review](native_n2_parity_delta_review_2026-10-25.md).
The [declared differences](native_vs_api_generic_v10_declared_differences.md)
include the current API-only report clarification, changed R9 relative to N1b,
effective schema/policy exposure and receipt-floor differences. Shared rule
equality does not establish identical effective inputs or scientific equivalence.

## Positive acceptance: neutral failed; omission not run

On frozen `01969cbed`,
`tests/test_native_shared_execution.py::test_actual_public_correction_three_workers_and_saved_completion`
returned **1 failed**, zero errors/skips, **12 dependency warnings**, **732.42 s**;
the acceptance driver exited1. The retained stderr confirms the provenance
recorder subprocess timed out after **180 seconds**. The journal reached
`assembly_checked` sequence22, but successful terminal runtime acceptance was
not established. Expiry of the enclosing **900-second** runtime deadline is
**not shown** by this evidence. Host contention and the recorder's internal
blocking operation are not established causes.

The runner correctly stopped without executing
`tests/test_native_shared_execution_variant.py::test_actual_public_merged_omissions_and_all_chunk_statuses`.
The omission result is **not run**, not passed, failed or skipped by pytest.

Evidence root: `/private/tmp/d4d-native-n2-acceptance-01969cbed/`:

- `neutral.log`, SHA256
  `5fa3ae13eae7d0379c6ee861ca67b1a96c26c9deaf722c2b6433e017e383feea`.
- `neutral.xml`, SHA256
  `d74f69f8f835c24630994d5103f048b08dd02bc6d03ade64e65e5b3482dac081`.
- `outcome.json`, SHA256
  `87ba53dfd5a26fd1d2effe9de7420ea54d47ae85838a3d2a166b95a757212a9c`,
  records failed neutral and the reason omission was not run.
- `preservation.json`, SHA256
  `a2bb06760d6d05a795db4d981f426272a7e412c168f933c7f1a0426b0aaffc09`,
  records all four checks true: expected head matches, run reached, source
  inspection succeeded and source unchanged.

The separate finalizer exited0 because preservation succeeded; it does not turn
the driver failure into acceptance. The approximately **27 MiB upload package**
retains commands, environment/source inventories, log/JUnit, outcome, preservation
and case manifests plus `cases.tar.gz` (18,352,510 bytes, SHA256
`5bf6f084b8dfd4c364907373f912129fd5705577a302407204877f9cd7e905ec`).
Before/after/final source snapshots have identical SHA256
`ef000ecd8ec8c6dd11a6fd004a5029ebbe6c8f864132523bb2b0d118ee8e1840`.
Durable raw staging is complete, with byte-for-byte copy verification, under
`d4d-executions/codex-n2-2026-10-25/evidence/acceptance-01969cbed/`;
small evidence copies are retained in this branch's unit4 validation directory.
The final render directory is preserved alongside the archive at
`d4d-executions/codex-n2-2026-10-25/evidence/parity-01969cbed/`.

The acceptance fixture uses a synthetic explicitly registered **0/1** receipt
floor; the render comparison uses a **pending diagnostic** floor. These are
different fixtures, neither a production floor decision. All runtime/account
declarations in the acceptance test are synthetic, and scientific acceptance
remains `not_assessed` in the failed outcome.

N2-R3 tracks the recurring recorder failure separately. Repair must preserve the
900-second runtime limit, 180-second helper timeout and production checks, then
re-establish both complete public paths, saved readback and repeat-launch refusal
on clean final source. No such repair or passing result is claimed here.

## Historical failures and AGY handoff

The [15-row disposition ledger](native_vs_api_generic_v10_declared_differences.md#every-n1c-3-failure-and-its-disposition)
preserves the older complete N1c run at `2a9c60d43`: **22,363 passed / 15 failed /
zero errors / 46 skipped**. It is historical failed evidence, not a current full
suite. Rows1–14 remain profile1 failures, deferred and unfixed on the preserved
owner lane. Row15's default neutral recorder timeout **recurs on `01969cbed`** and
remains unresolved. Its earlier omission counterpart pass does not waive it or
supply a result for the current unrun omission fixture. No failure is closed by
excluding it from the default-profile source cut.

The local four-unit series and retained findings are ready for review, with native
acceptance explicitly blocked. After the required repair and acceptance review,
AGY owns publication/integration and
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

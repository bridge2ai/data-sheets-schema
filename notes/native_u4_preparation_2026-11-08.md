# Native U4 preparation — 2026-11-08

This branch ports the public native permission/subscription front door onto D9
`59d2982cfa3f0e88acc66047d2d9428c61eed74b`. It is bounded preparation, not native
acceptance. The task permits D9 because no completed D10 handoff was recorded
when the base was selected. Existing worktrees and evidence are preserved.

The behavioral donors are `f60903154b57c9536f8a6e5425a40d4aaa87d83a`,
`3ed01252003605cde5b864a74e8ea346460831f8` and
`3098aa6d77b0c34458a91d67848512a5f047dcc6`. Their old authority imports and
unknown-kind legacy fallback are not compatible with the current closed v2
interfaces. Only the front-door/probe/provider components are being ported.

## Owner choices and remaining authority

- D105 keeps receipt instrument **v4** primary. The v5 secondary measurements
  do not activate v5 for generation or change the native acceptance floor.
- D106 selects explicit **`--effort high`** and the **LBL work Claude Max
  first-party account, without an API key**. A saved account-choice declaration
  binds that selection intent to the exact command subject and runtime bytes.
  It is not authenticated account-state evidence, a subscription login or a
  launch authorization. No account identifier, email address or credential is
  required in that declaration.
- D107 authorizes drafting the native amendment. Its ratification, final live
  slice/stop choices, real binary/version/thinking evidence and final launch
  word remain outside this branch. No live stop defaults are introduced here.

Offline validation/preparation commands remain separate from explicit future
permission-probe and generation-launch commands. The latter are never executed
for this preparation task. Saved-probe tests use fabricated observations with
real current verifiers; they prove software behavior, not actual native
permission, account access, native generation or scientific acceptance.

## Front-door contract

The module entry is `python -m data_sheets_schema.native_generation`. Every
command requires `--account-choice`, a closed JSON document with these keys:

```json
{
  "kind": "d4d_native_u4_owner_choice",
  "version": 1,
  "decisions": ["D105", "D106"],
  "account_label": "LBL work Claude Max",
  "effort": "high",
  "receipt_instrument": 4,
  "subject_sha256": "<SHA-256 of exact expectation or registration file bytes>",
  "runtime_sha256": "<SHA-256 of canonical selected runtime JSON>"
}
```

The digest placeholders are explanatory, not valid inputs. For
`validate-probe` and `permission-probe`, the subject is the expectation file;
for `prepare-subscription-guard`, `launch` and `read-final`, it is the execution
registration. Runtime canonicalization uses `native_subscription_guard.canonical`.
The output includes the choice-file SHA and an explicit selected-intent basis.
The declaration is re-read before effects or before saved-verification success.

`validate-probe` takes only the saved expectation/probe and choice declaration;
it does not need or create a generation word. Guard preparation additionally
takes an existing word/event and explicit freshness/headroom choices; it cannot
create authority. `read-final` is offline saved-result verification, never a
resume. The explicit future `permission-probe` command and `launch` command
remain distinct: the former does not depend on a prior probe or generation
word, while the latter requires the full registration/review/CI/word/probe/guard
chain. Unknown protocols have no legacy fallback.

## Required later revalidation

Before acceptance, integrate this preparation through a reviewed merge onto the
accepted U1+U3 head, after schema 3.2.0 release and installation of all four
owner-approved U1 packets. Preserve the reviewed merge ancestry and resolve
overlaps by behavior, not by replacing current files with donor copies.

1. Bring A6 `a6da0cd2a5227d768c9f3e21291a0ce848d66640` and C7
   `0a260a632394ce43ae2c8ed2144c05f7a8a21def` through the completed D10 handoff.
   D9 does not establish their capture-class and worker-loader fixes.
2. Rebuild all source, schema, catalog, instruction, preparation, projection,
   runtime expectation and registration captures on the final installed bytes.
   This branch adds source members, so historical source closures/probe hashes
   cannot be treated as evidence for it.
3. Repeat the genuine saved-probe front-door canary, all affected command,
   permission, guard, v2 authority/registration/loader, D capability and boundary
   suites, then complete-path correction/omission/failure and saved-readback
   acceptance. Recheck the public producer's worker/callback lifetime on C7.
4. Repeat final-schema renders, API parity at the same schema baseline,
   specificity discovery, protected-packet/D76 checks, full collection and the
   required final CI roster. Keep expected protected-hook failures explicit
   until the approved installed bundle closes them; no scratch overlay counts
   as installed acceptance.
5. Complete or explicitly disposition the accepted post-U3 quiet-host and
   recorder/parent-readback measurement protocol. No timing acceptance is
   supplied by this preparation.
6. Obtain the ratified native amendment and separate permission for a real
   binary probe, using the actual pinned version/hash/runtime. Revalidate the
   LBL account and headroom through that later authorized process. A synthetic
   loopback transport token in the permission probe is not a real API-key
   fallback for generation.
7. Produce and independently review a fresh canary registration and exact
   review/CI/probe evidence. Only after its separate owner word may a fresh
   word-bound subscription guard be constructed immediately before dispatch.

The validation launcher is
`scripts/adhoc/run_native_u4_prep_tests_20261108.py`. It confines test writes to
`d4d-executions/scratch-native-u4-prep/`, denies network and real native
executables, strips credentials before Python startup, verifies source/dependency
origins, cooperates with the quiet-window lock, limits pytest to two workers and
enforces a 3,600-second process-group deadline using UTC and monotonic clocks.
The final execution report and exact evidence hashes belong in
`d4d-executions/plans/reviews/native_u4_prep_2026-11-08.md`.

## Local review findings (offline issue handoff)

Findings are retained here for the later authorized PR/issue workflow; this
task has no GitHub-write permission. Final test dispositions are recorded in
the execution report rather than inferred from the presence of a patch.

| ID | Finding | Disposition |
|---|---|---|
| U4P-R1 | Initial front-door port tried to serialize the producer's `Path` return value directly as JSON, which would fail after a successful future probe. | Changed to an explicit string `probe_manifest` result. No probe was run. |
| U4P-R2 | Donor local-provider startup bound a listener and started its thread outside the cleanup guard; thread-start failure leaked the listener. | Fixed with guarded startup; fake-server/thread regression `test_provider_listener_cleanup_is_bounded_even_on_start_failure` passes. |
| U4P-R3 | Donor provider body reads could exceed the absolute deadline under continuous trickling; synchronous shutdown could then wait without a bound. | Fixed with absolute-deadline `read1` loops, a stop-event request loop, active-connection close and bounded join. `test_provider_body_uses_absolute_deadline_without_socket` and cleanup regressions pass without a real listener. |
| U4P-R4 | Saved-probe output could imply that D105's v4 choice was a newly verified receipt-policy result. | Output now says `selected_receipt_instrument`, with command-specific proof limits. The account-choice schema is unchanged; producer/registration paths retain genuine receipt-policy checks. |

## Validation checkpoint

Code/test commit `126e54a1891e9444004846abcf0e88e4071340b1` passed the single
genuine saved-probe canary, **103 new-module tests**, **230 permission/guard/path
regressions**, and **237 v2 authority/registration/loader/CI/D9-boundary
regressions**. The latter three cohorts are disjoint: **570 distinct passed
tests**, zero failures, errors or skips. The canary is included in those 570.
Full repository collection found **24,898 tests** with zero collection errors;
the full repository suite was not executed. All five invocations retained
source stability, origin, network-denial and observed-process cleanup evidence.

These are software preparation results on D9. The D9 test asserting a worker
loader refusal is a diagnostic pass, not C7 integration acceptance. The fake
producer-event test verifies capture/consumer behavior without a native process
or listener. Independent read-only review found and rechecked U4P-R2/R3; no
remaining new-port source finding was reported. A6/C7, the protected installed
bundle and full native acceptance remain the later gates listed above.

The follow-up documentation/evidence-helper commit changes no production or
test bytes. Run evidence stays under `scratch-native-u4-prep/{canary-1,port-1,
permissions-1,authority-1,collection-1}`. The checked-in summary helper retains
per-run counts, source heads, exact JUnit identities and artifact hashes, so
overlapping canaries cannot inflate the distinct-test total.

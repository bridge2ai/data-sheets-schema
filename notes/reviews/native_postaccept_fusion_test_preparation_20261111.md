# #5867: fixed component checks prepared, not executed

2026-11-11. Branch `codex/native-postaccept-fusion-20261111`; production stays
byte-for-byte at `6c1719aa9a7d78e773049c0502d54a3b9b7d4dfa`. This checkpoint
implements the lead's test/helper preparation release only. Stop for separate
review before any imports, compilation, pytest, capture peer or other runtime.

## Delta and exact identities

| Artifact | SHA-256 |
|---|---|
| tests/test_native_u4b_a3_reservation.py | `eb0522c4da33b24040cb2e10657b7e97b09a43a51fbf86d19b4c8af043899f96` |
| scripts/adhoc/run_postaccept_fusion_checks_20261111.py | `7975260d7299f2f3f6dee0dfeb98c3f055f7a756050ac63c0bbb2b252894132c` |
| Exact tests/helper diff, notes/reviews/native_postaccept_fusion_test_preparation_20261111.diff | `e3e3b9a5ed3fbbf5da0a5fdffc967e7a753e2492be8f722620e0d4a07fc58025` |
| Corrected prior implementation report | `5f1b3ff0e20c3cbf41ed495973f5d255d98286948e14fa179b4c42b3a01f4ece` |
| Unchanged tests/utils/subprocess_deadline.py | `876c91d211f4870c5622e7403310200b37028a3287c2b94e468a4c9d084b01b7` |

Frozen production postimages remain:
`native_execution_orchestration.py` =
`13573951995c5e7d27b164feaab1b328dad09b33c8dce9ff53afa50ec360a89b`;
`native_shared_execution_orchestration.py` =
`c77d692deafafb483e8ccf0781cad9434f1aee14aa4585fec4a2269d081025e5`.
No other production, protected, existing supervisor or adapter-caller bytes changed.

The prior report's public lease node is corrected to
`tests/test_native_u4b_a3_captures.py::test_admission_lease_excludes_word_renewal_during_reservation`.
The original checkpoint remains recoverable at commit6c1719; this correction
and new test preparation do not rewrite its source diff or claim it was tested.

## Fixture and assertions

The existing reservation fixture now traces `words.locked` and `Journal.require`,
so both the public direct-guard lease and launch-local lease are observed at
their actual shared lock boundary. Lock ownership remains asserted through
controls, margin, mkdir/fsync and release. Post-test reacquisition is untraced.
The public lease is no longer replaced by a tracing wrapper.

The actual shared `_unchanged_inputs` body executes on the fused route. Its
`require_committed` prerequisite alone is isolated. `_file` observations delegate
to the real reader. Darwin success uses the actual `_platform` function.
Following #5868, the original consistent Darwin runtime, minted observation and
production policy remain untouched. Only on non-Darwin hosts, the component
fixture explicitly isolates the platform prerequisite by returning its declared
Darwin platform. This is not native portability evidence. No policy/validator
is weakened, no observation is re-minted and no cases are skipped. The later
platform-mismatch test still injects its deliberate mismatch on either host.
The pre-admission/direct `effects.unchanged` component isolation remains explicit.

The new focused cases cover:

- Current execution changed, fresh execution changed, and both changed to the
  same value after acceptance. All must refuse before the lease lock/mkdir;
  the third case specifically tests the immutable original comparison.
- Engine mutation during an actual authorization-file read, followed by the
  retained fresh authority entry and refusal before the lock.
- Changed authorization bytes, missing authorization file and changed platform,
  through the actual input tail. They refuse before the lease authority call.
- Fused-route controls cost charged to the fixture clock before the original
  90-second margin, with 90 and91 starting seconds producing opposite outcomes.

The deferred success test asserts its new exact tail/authority/lock trace and
that one pre-admission isolated-source-recapture survives. Existing direct,
supersession/poison and margin assertions remain. The fixture checks the actual
scripted peer's retained capture lifecycle before constructing the launch case.

Registration reconstruction, source prerequisites, controller and admission
remain deliberately isolated. The fresh-value mutation is injected into that
component authority result, not into an actual source-loaded producer. These
checks cannot establish genuine producer/projection parity, observed elapsed
freshness, native execution, or a performance improvement.

## Fixed selections and expected counts

All reservation functions below are in `tests/test_native_u4b_a3_reservation.py`.
The caller accepts only these literal group names and starts only that group.
Counts are derived from source parametrization; no collection has run.

| Group | Exact functions | Expected cases / capture manifests |
|---|---|---|
| canary | test_deferred_capture_acceptance_exact_order_to_real_reservation | 1 / 1 |
| values | test_fused_lease_compares_original_current_and_fresh_execution; test_fused_lease_refuses_engine_mutation_during_authorization_read | 4 / 4 |
| inputs | test_fused_lease_uses_actual_shared_input_checks | 3 / 3 |
| direct | test_registered_90_second_margin_permits_first_real_reservation_only; test_registered_89_second_margin_refuses_before_any_attempt_directory; test_source_recapture_time_is_charged_before_measuring_reservation_margin | 4 / 4 |
| margin | test_fused_lease_charges_controls_before_margin | 2 / 2 |
| admission | test_admission_changes_after_initial_join_refuse_before_attempt_reservation; test_deferred_capture_late_load_refuses_admission_mutation | 4 / 6 |
| lease | test_admission_lease_excludes_word_renewal_during_reservation, in test_native_u4b_a3_captures.py | 1 / 0 |

The two poison variants intentionally retain failed capture-status manifests
with successful peer exit/cleanup. The lease group activates words without
executing a peer. The total proposed coverage is19 cases across seven separate
fixed invocations; it is not a released batch. Canary elapsed time must inform
which later group, if any, receives release. No whole-module fanout or automatic
follow-up is implemented.

## Thin caller and proposed first command

The new161-line caller reuses unchanged `tests/utils/subprocess_deadline.py`.
It adapts fixed selection/environment/evidence wiring from the existing
`run_capture_adapter_unit_checks_20261111.py`; it introduces no supervisor,
composition, native runner, profiling hook or dependency installation.

The child work budget is10 seconds minus setup elapsed; nonpositive remaining
time refuses before launch. Existing supervisor cleanup has a20-second reserve.
The result additionally requires elapsed<=30 seconds. This is an acceptance
budget, not a new hard wall alarm or a promise that existing cleanup can never
overrun. No deadline constants or cleanup algorithms were altered.

Each mode requires a new exclusive output directory under
`d4d-executions/scratch-native-postaccept-fusion-20261111/<mode>/`, with fresh
HOME/TMP/basetemp/bytecode locations. Child environment is an allowlist without
credentials; plugin autoload and pytest cache are disabled. Sandbox denies
network and writes outside that output, and permits exec only for the selected
Python/interpreter target and fixed ordinary-Python fixture path under cases.
Native executable paths are excluded by that allowlist, including aliases to
other executable targets. No real native executable is invoked by these tests.

A non-canary mode requires the same selected-file hashes as a passing canary.
JUnit identities/counts must match the fixed selection exactly, with no
failure/error/skip. The caller verifies expected capture-manifest counts,
status, successful peer lifecycle, constituent hashes/sizes and nonempty
claim/stdout/observations. D76's process-group result alone does not certify
separately sessioned peers; their recorded cleanup is checked separately.
Interrupted/missing evidence does not pass, and the caller does not retry.

**Proposed command only; NOT executed or released:**

```bash
env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin HOME=/var/empty \
  /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python -S -P -B \
  /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-native-postaccept-fusion-20261111/scripts/adhoc/run_postaccept_fusion_checks_20261111.py canary
```

The existing Python symlink was inspected as filesystem metadata only; the
executable, helper, imports and tests were not run. This release allows no
capture, runtime, config rearm or automatic next mode. A later canary would need
its exact singleton JUnit and capture cleanup side effects checked before any
separate affected-group release.

## Stop boundary

The #5868 correction removes the runtime rewrite performed after
`runtime_inputs` had already minted its observation. A re-mint would still
conflict with the production Darwin policy, so no runtime or policy bytes are
rewritten. The only new isolation is the non-Darwin host prerequisite described
above; all19 proposed cases remain and no skip is added. The earlier invalid
proposal and its exact diff remain recoverable at
`1768e6a32ff1aad9f82cda71ce6430c523c3e919`; it was never executed. The separately
reviewed helper remains byte-identical. The #5867 whitespace claim is now scoped
explicitly, without stripping normal context whitespace from the patch archive.

`git diff --check` scoped to source/test/helper/document files passes. The
whole-commit check flags normal space-only context lines in the exact archived
`.diff`; those patch bytes remain intact. No syntax check, import, collection, pytest or runtime
has occurred; behavioral results remain unknown. Production stays frozen at6c1719;
original native382f/tools7043/helper8bb and restored configuration/evidence are
preserved. No push/merge or provider/native call. This is prepared work for
#5867, not a claim that the issue, U3K-F1 or native acceptance is complete.

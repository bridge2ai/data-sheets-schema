# Helper 2: pins, admission and capture timing

Lead pins were fast-forwarded into the power branch and the admitted eight-file cohort completed: 162 passed. Admission, documentation, personal-path and pre-reservation diagnostic changes are committed locally. The new controller pin proposal is unapplied; the stalled-verification publication integration awaits lead admission. The specificity scanner also needs review of its frozen authority-source contract. The supplementary generation guard suite was stopped after repeated contract refusals; its reported counts are partial. Nothing was pushed or published; no live native/provider/model call or public completion test ran.

| Branch | Head |
| --- | --- |
| codex-native-host-power-20261113 | `9faacc2522eb05b445d053598f3a8caaad74b8f0` |
| codex-native-production-run-limits-20261112 | `6c62fa27fccdcb4cdbc572b2466a6aa189da56e1` |
| codex-native-helper-cache-home-20261112 | `9d743c87755030ddf687e3a5dd8a7a2b3b762437` |

The requested pin merge was a fast-forward. The four protected files and guard v1 remain equal to candidate f7f8e8bff; no primary-checkout edits. The cache branch has no new commit in this assignment; the three remaining runner fixes are in the power packet.

The admitted rerun used export commit `98f55b2eb7c284cc9d8e35cd7b2350d53190c4aa`, composed from power `a2db8ab6b403e5c70f1020c927dd6185fe8a574c` and limits `0df39c077fb8125dc381302046f4cf7f92a60592`. The new unit checks used source `e648abe2a384be9036fdd77ce239a6db3c311b03` with unchanged pins. The admitted rerun does not certify the subsequent admission-controller change.

Admitted rerun counts, derived from its saved JUnit XML:

| File | Passed | Failures | Errors | Skipped |
| --- | ---: | ---: | ---: | ---: |
| `tests/test_native_attempt_deadline.py` | 10 | 0 | 0 | 0 |
| `tests/test_native_attempt_timing.py` | 3 | 0 | 0 | 0 |
| `tests/test_native_execution_registration_v2.py` | 65 | 0 | 0 | 0 |
| `tests/test_native_failure_publication.py` | 9 | 0 | 0 | 0 |
| `tests/test_native_host_power.py` | 21 | 0 | 0 | 0 |
| `tests/test_native_run_limits.py` | 21 | 0 | 0 | 0 |
| `tests/test_native_shared_live_capture.py` | 7 | 0 | 0 | 0 |
| `tests/test_native_shared_permission_protocol.py` | 26 | 0 | 0 | 0 |

Other saved checks:

| Cohort | Counts | Runner seconds (monotonic) |
| --- | --- | ---: |
| pin-canary | 1 passed | 3.9494875829986995 |
| admission-alarm-canary | 1 passed | 0.8295689160004258 |
| new-unit-files | 10 passed | 2.367245000001276 |
| publication-awaiting-pins | 1 failure | 2.8713197500037495 |
| specificity | scanner exit 2 | 99.85074316700047 |
| generation-guards (partial) | 52 error, 39 failure, 282 passed | 1761.9919628329953 |
| admitted-scanner-baseline | scanner exit 2 | 90.9072394169998 |

All cohorts use outside-execution exports, denied network/native execution and at most two xdist workers; origin and owned-process cleanup checks are saved. The actual-source FIFO canary proves alarm interruption. The additional 13 pure execute_child checks prove refusal, descriptor cleanup and child-clock separation without loading or admitting a registered controller. They do not prove failure publication.

Runner seconds use time.monotonic, not the continuous admission clock. They are not capture-to-reservation measurements or evidence of a quiet, unsuspended host.

900 seconds, as assigned: the earlier timing evidence lacks a measured admission interval that supports a different value. The bound starts at execute_child entry and ends at the dispatch origin on the existing suspension-inclusive elapsed clock. It consumes none of the 900, 21600 or 43200 child seconds. A 0.1-second periodic POSIX alarm checks that clock and raises AdmissionExpired through interruptible Python syscalls; the exception bypasses broad Exception handlers. A synchronous check at dispatch refuses an expired bound even before alarm delivery. Signal ownership is exclusive and restored after admission. Existing controller cleanup, keep-awake cleanup and failure publication retain the distinct reason: native admission deadline elapsed; child was not dispatched. Cleanup/publication themselves lie outside the admission interval.

This in-process mechanism cannot preempt an uninterruptible kernel call or a C extension that never services Python signals; alarm handling resumes when the host and Python run again. The exact dispatch check remains fail-closed. Earlier pre-reservation verification is outside this timer. The real FIFO-open tests exercise interruptible syscall cancellation, not a universal hard-real-time cleanup guarantee.

The new host-pre-dispatch-<registration-sha256>.jsonl lives beside the attempt, outside the closed capture tree. Timestamps are buffered until a freshly verified registration supplies the canonical existing parent. Explicit capture, current guard preparation and public launch scopes append capture observation, current_guard_preparation, every active registration.verified call, admission with classifier, controller construction/prewarm, _current_authority and reservation start/end, plus attempt_reserved. The synthetic fixture records its invented capture at minting. Step IDs, trace IDs, process IDs and registration digest join rows; capture timestamps/digests distinguish captures. It uses the same continuous clock and is never read for admission. It stops after reservation. Byte/row buffering is bounded; failed/contended writes disable observation. Missing rows mean unknown timing. Synchronous diagnostic I/O can add latency; it is not claimed to have zero runtime effect. No newly instrumented public duration is claimed before pins are admitted.

A later capture is possible in principle without changing the 1200-second maximum age or 300-second margin. Source-only registration, review/word/protocol validation, classifier derivation and controller prewarm do not need the captured quota event. _current_authority reconstructs those inputs; its quota request validation does not inspect an observed event. Current guard preparation and latest-claim selection do need the capture and cannot simply move before it. Proposed for the lead: a reviewed preparation phase finishes cold source/controller work, then takes one fresh capture, constructs its current guard, rechecks exact source/input identities and the current word/latest claim under the existing lock, and reserves. Keep all final freshness, source, word and dispatch checks; do not reuse a previously verified value as launch authority. Current consumer-loader scopes cannot simply be held across bootstrap orchestration. Measure the remaining fresh reconstruction before promising that it fits 900 seconds. This needs an explicit two-phase interface/source review; no reordering, retimestamping, recapture or limit relaxation was implemented.

Review-only pin proposal: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/codex-h2-admission-pin-proposal-20261113.diff`. SHA-256 `f2d7a46af762362d3c986f01f00ccf8c6d01ad92a0cf666a5226e7dab9c77cbd`. It contains both manifest rotations and their three authority constants. The test census includes ignored/hidden files and explicitly checks CONTROL_SHA. native_control.py is unchanged, so that live test digest is retained. Historical protocol prose and fixture evidence are not restamped.

The final power-head delta after the unit export and proposal is only the stalled-publication test clock setup; all controller bytes are identical. That integration test remains unverified until new pins are applied.

Documentation and generator describe continuous dispatch origin and the separate admission budget. The negative anchor test refuses before writing; historical draft-v12 references and the 300-second margin remain. run_helper_cache_tests_20261112.py, run_native_h2_tests_20261112.py and run_native_h2_sequence_tests_20261112.py now discover home, NVM and PATH locations without executing the binaries. Other helpers’ runners were untouched.

The specificity scan did not happen (exit 2): its frozen v2-envelope authority contract rejects native_attribution_controller_v2.py. The same source bytes occur in the lead-admitted export and the new-source export. The baseline comparison reproduces the refusal: True. The scanner expects source hash 1e1cc08057523bb6d6c0d2da660af6a1b68a43b5b08bf9e43993c0b17ee75722 at scan.py:13003; both exports contain 3629c90eb3a693f85292d3c32d26a85961666f1d8ed03ed4f6d7fe3cf85d82eb. This requires scanner-instrument review after the controller pin rotations; no scanner pin was changed. No clean specificity result is claimed.

Automatic approval review rejected an additional power-to-limits branch merge as lacking explicit merge authorization. It was not retried. The documentation generator reads both source packets explicitly; their branches remain separate for lead integration.

Separate read-only diff review completed. Pending controller admission, the scanner authority-source contract refusal, and interruptibility limits are explicit findings for the lead; no review issue was published under the offline constraint. No authority, scanner or prompt pin was restamped.

The active admitted rerun survived daemon restart and was not restarted. Only its idle waiting validation driver was identity-checked and restarted with durable stdout. Saved worker/outcome files establish completion and cleanup.

Only the supplementary generation-guard pytest controller received SIGINT after repeated source-contract failures. Pytest retained partial XML/logs, returned normally with interruption status, and the owner runner verified cleanup without forced termination. These counts are not a completed guard suite.

91 recorded guard failures/errors mention the frozen scanner contract refusal. There are no completed results in this supplementary run for test_neutral_generation_schema.py, test_profiles.py or test_external_dataset_onboarding.py; those checks remain pending. Two unnamed interrupted JUnit entries are retained separately and are not counted as passes.

1. Lead review/apply the new pin proposal, retaining the unchanged permission-protocol test CONTROL_SHA.
2. Review the scanner frozen authority-source contract against the final approved pin rotation; rerun the scanner and affected guards without a blind restamp.
3. On admitted new code, run the stalled-verification publication test and touched orchestration/capture/controller integration files.
4. Lead decides whether to implement the proposed later-capture workflow; D138 limits remain unchanged.

Detailed source checks: `/Users/marcin/agent-work/data-sheets-schema/helper2-pins-admission-20261113/source-audit.json`, SHA-256 `b172a35e893a7342604ccc867a255b39b06807d8378a7bfd53254deab9076915`.

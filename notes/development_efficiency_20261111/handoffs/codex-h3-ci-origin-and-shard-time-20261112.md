# H3: import origin and CI time, 2026-11-12

The import-origin error is removed in both tested file orders, but the required all-green proof is blocked: only 19 of the 37 assigned IDs pass on this branch. The remaining 18 reach independent failures, principally the protected main RunSpec constructor rejecting native_shared_generation_version. Neither production checks nor protected files were changed. The local Part A commit is f25230fe1e56c5ad264cf77242f623be0ee6e4d1. Do not describe this as all 37 passing or as the full CI gate passing.

The native-only weight supplement contains 134 measured native files, adding 108 entries to this branch's existing map. It preserves the previous source records and all non-native weights. Six shards contribute JUnit times; the two cancelled shards contribute explicitly labelled worker-completion-interval estimates, including partial files. Sixteen native files have no observation and retain the median fallback shown below. The repository updater was called and refused this unsuccessful run. Its refusal is retained; the helper uses the existing analysis parser and writes an explicitly unsuccessful-run supplement without changing or bypassing the updater's checks.

The scanner repeatedly performs expensive text-flow/AST derivation because discovery fails late and its lru_cache never stores a result: the exact CI source takes 182.462 seconds cold and another 120.966 seconds on the identical repeated call. Fix the derivation mismatch first; a test-only cache of the unchanged-root error is a possible follow-up that must keep every failing verdict. Native-only weights model 49.52 ideal minutes at eight PR shards and 42.46 at ten; all-measured weights model 34.49 at eight. Recommend corrected-source validation and a complete timing refresh before choosing an owner-approved capacity change, with nine/ten shards under the all-measured scenario offering additional margin. No scanner optimization or workflow change was made.

The Part B weights/provenance commit is 01c9b7b862330ad1f8a363a1b45f912e013c702b. The final focused timing validation passes all 15 tests. The earlier broad timing-validation cohort was deliberately interrupted after 36 passes while repeatedly launching synthetic shards; it is retained as partial evidence, not a completed acceptance check. The assigned code branch is clean after the two local commits. The handoff files in the report worktree are left for the lead to review and commit.

## Import isolation and its limits

The smallest reproducing file set is test_audit_recall_leak_rendered.py plus test_native_execution_round5_v2.py. The saved reproduction runs the audit file and the one forged-cache test in the same process: the audit tests pass and the v2 test raises the exact prepare_registration origin refusal. The existing isolated_modules fixture clears all manifest-pinned and additional authority aliases before a test and restores their original identities and sys.path afterward. Applying it through module-level usefixtures in the eight affected files handles both collection-time imports and previous v1 cases. An origin-refusal test can still install its deliberately foreign module inside its own body; the production guard is untouched.

The two completed order cohorts run all eight affected files, the complete audit file, and test_native_attribution_controller.py::test_composition_can_prepare_and_matches_every_selected_command. Reversing those file arguments yields identical totals and zero origin errors. Each cohort's individual assigned-ID outcomes, nonpassing messages, JUnit digest, origin witnesses, OS network-denial evidence and cleanup result are in the JSON and sibling scratch directories. The additional canary proves that the isolated environment, exported source, Git metadata, and alias fix work together. It does not prove the protected native front door is available.

The lead's export script produces an archive without Git metadata. The first outside-tree run therefore fails repository-identity checks. A saved helper adds only local Git metadata using the local object store, at the exact exported commit; it changes no source bytes and sets no remote. Subsequent tests use that tree. Both source-diff witnesses are empty: the exported tree remains unchanged, and the four protected files equal main 7ad8c9e7295f1575ae9108ea62c12c83b1dd4db1. The original export's full collection also reports missing fairscape_models.rocrate submodule content; this is not a full-collection acceptance result.

Ignored and hidden files were included in the import/loader source searches under tests. The collection trigger is test_audit_recall_leak_rendered.py, whose imports transitively load the v1 preparer. Explicit execution-time bare-loader sites also occur in test_canary_controller_receipts.py, test_native_attribution_controller.py, test_native_execution.py and test_native_execution_permissions.py. test_native_attribution_results.py calls results.capture, which calls the same loader; test_native_attempt_supervisor.py calls composition, which also loads that closure. The saved v1-runtime-candidates.txt and reference files retain the broader consumer list, including isolated consumers and import-only uses; those are candidates, not a claim that every listed module leaks. This work does not certify an exhaustive execution-time pollution census of the entire suite.

## Timing interpretation and owner decision

The exact CI scanner fails late in discovery: its native shared render derivation rejects changed native_execution_authority_v2.py bytes. The cold profile takes 182.462 seconds and leaves the parameterless discovery lru_cache empty. The scanner already has per-process discovery, parsed-AST and summary caches; adding another generic session cache is not the diagnosis. Exceptions are not cached, so calls that fail late redo the expensive derivation. In that cold profile, text_flow accounts for 79.978 cumulative seconds, ast.walk for 92.923 cumulative seconds, and _parse for 8.041 cumulative seconds. These overlap and must not be summed. The CI class breakdown below shows where the observed intervals accumulate, including failing test bodies and class-setup errors. The local profile uses Python 3.13 with profiler overhead; CI uses Python 3.12. It establishes the repeated-work mechanism, not a portable wall-time ratio or exclusive attribution of the entire increase.

The second identical call in the exact CI process takes another 120.966 profiled seconds and fails with the same error. CacheInfo then records zero hits, two misses and zero entries. This directly confirms repeated expensive discovery despite unchanged inputs and warmed lower-level caches. It supplies the measurement behind the test-helper proposal below; it does not make the failed derivation acceptable.

The current scanner differs from the original CI scanner. Its separate cold profile takes 197.222 seconds and fails with a different missing native-only-route error. I stopped that profile's next call and preserved the completed first-call data before profiling the exact CI tree; the interrupted call supplies no timing result. No current-tree timings are substituted for the old CI observations.

A narrow candidate, requiring the lead's word, is to cache the unchanged-root test helper's ConfigError outcome as well as its successful value, then re-raise that same error for every consumer. Every affected assertion would still fail; expensive discovery would run once per process. Keep rewritten/mock-dependent discovery helpers separate, and preserve the existing immutable-root assumption or invalidate explicitly when inputs change. Do not cache failures in production authority checks and do not relax source pins. This is a test-setup proposal, not an applied scanner change; resolving the underlying native derivation mismatch remains necessary. No safe, measured small change to the audited text-flow algorithm itself is established here.

I agree that native-only weights do not establish a fit within the existing PR limit. I disagree with treating the ideal four-worker arithmetic as a job-wall prediction, or saying ten shards mathematically cannot fit: the current model gives 42.46 ideal minutes at ten shards, but insufficient evidence of overhead or tail margin. The earlier report used a different branch snapshot. This branch's old fallback is 3.9665 seconds and its old scanner weight is 1803.166 seconds, not the assignment's fallback or the earlier scanner weight. The measured scanner total is a log reconstruction for only 366 of 381 cases, not a complete JUnit measurement.

The partition tables below call this branch's actual balanced_files function. They retain prior weights for unmeasured files, and include the repaired collection driver. They report scheduled load and the load of the same partition evaluated against all available observations. The whole-file split scenario assumes four equal pieces; that distribution has not been measured. CI already distributes individual cases across workers with load scheduling, so splitting a file helps assignment across shards but can multiply expensive per-process discovery work.

Options for the owner under D75 and D81:

The six-shard main model also needs attention: native-only weights give 68.38 ideal minutes against its existing sixty-minute limit. Updating all measured weights models 45.99 ideal minutes for those same six shards. A PR-only shard change does not resolve main's modelled overload.

- Native-only weights plus more PR shards: ten gives limited ideal margin; twelve or sixteen improve it as shown. Additional runners require the owner's capacity decision.
- Keep eight shards and extend the PR job limit to sixty minutes: the predicted load remains 49.52 ideal minutes. Changing the timeout does not reduce work and this still lacks a demonstrated overhead/tail allowance.
- Refresh all measured file weights: the eight-shard scenario is 34.49 ideal minutes; nine or ten buy more margin. These remain failed/partial-run observations, so a completed representative run must verify the prediction.
- Split the scanner file: the equal four-way split alone barely changes the eight-shard full-refresh estimate and may repeat discovery on more workers. It is not the first fix I recommend.

Recommendation: resolve the native/scanner correctness failures first, avoid rediscovering the same failed immutable source in each test, then refresh all weights from a completed run. If the owner needs a capacity change before that evidence exists, the all-measured nine/ten-shard scenarios offer more modelled margin than native-only ten. No workflow edit or scanner optimization is included here.

## Findings for the lead to file and triage

- H3-F1: protected RunSpec lacks the native constructor fields required by the remaining assigned cases. This prevents the requested all-37 passing proof. Resolution belongs with the lead's authorized integration/composition decision, not a test assertion change.
- H3-F2: a broader v1 cohort additionally fails recorder-result assertions. Its interrupted run is preserved separately; no assertion was weakened and it is not counted as a completed proof.
- H3-F3: the archive simulation lacks Git metadata and full fairscape submodule content. Local Git metadata solves the first for these cohorts; full CI collection still needs the proper dependency checkout.
- H3-F4: historical timing tests assumed the previous refresh was the entire current map. The Part B test change keeps all historical checks and adds exact native-overlay equality and observation-source assertions.
- H3-F5: native-only weights and incomplete cancelled-run observations do not establish the owner's PR timeout contract. Scanner profiling and the scenario tables are evidence for a decision, not authorization to change limits.
- H3-F6: the copied test runner's header still named its G07 predecessor. The final provenance commit corrects the header only; execution semantics are unchanged.

No GitHub issues were created because this assignment explicitly forbids GitHub writes. The findings above are the lead's issue-filing queue. No merge or launch is proposed.


## Test evidence

Exit 2 marks interrupted runs; they are not completed acceptance checks. The assigned-ID column applies only to the import-origin cohorts.

| Cohort | Exit | Passed | Failed | Errors | Assigned IDs passed | Origin errors |
|---|---:|---:|---:|---:|---:|---:|
| fixed-canary | 0 | 2 | 0 | 0 | 1/37 | 0 |
| order-forward | 1 | 141 | 9 | 13 | 19/37 | 0 |
| order-reverse | 1 | 141 | 9 | 13 | 19/37 | 0 |
| outside-forward | 1 | 99 | 48 | 58 | 0/37 | 0 |
| outside-forward-git | 2 | 45 | 2 | 0 | 0/37 | 0 |
| outside-git-canary | 0 | 2 | 0 | 0 | 1/37 | 0 |
| reproduce-os | 1 | 37 | 1 | 0 | 0/37 | 1 |
| timing-focused | 0 | 15 | 0 | 0 | 0/37 | 0 |
| timing-validation | 2 | 36 | 0 | 0 | 0/37 | 0 |

## Bare aliases left after full collection attempt

| Alias | Loaded source | Test modules on importing stack |
|---|---|---|
| budgeted_cborg | /Users/marcin/agent-work/data-sheets-schema/ci-sim-f25230fe1e56/notes/matched_cborg_2026-09-13/budgeted_cborg.py | test_audit_recall_leak_rendered.py |
| native_command_policy | /Users/marcin/agent-work/data-sheets-schema/ci-sim-f25230fe1e56/notes/matched_cborg_2026-09-13/native_controls/native_command_policy.py | test_audit_recall_leak_rendered.py |
| native_control | /Users/marcin/agent-work/data-sheets-schema/ci-sim-f25230fe1e56/notes/matched_cborg_2026-09-13/native_controls/native_control.py | test_audit_recall_leak_rendered.py |
| native_file_policy | /Users/marcin/agent-work/data-sheets-schema/ci-sim-f25230fe1e56/notes/matched_cborg_2026-09-13/native_controls/native_file_policy.py | test_audit_recall_leak_rendered.py |
| native_phase_history | /Users/marcin/agent-work/data-sheets-schema/ci-sim-f25230fe1e56/notes/matched_cborg_2026-09-13/native_controls/native_phase_history.py | test_audit_recall_leak_rendered.py |
| native_proxy | /Users/marcin/agent-work/data-sheets-schema/ci-sim-f25230fe1e56/notes/matched_cborg_2026-09-13/native_controls/native_proxy.py | test_audit_recall_leak_rendered.py |
| native_readonly | /Users/marcin/agent-work/data-sheets-schema/ci-sim-f25230fe1e56/notes/matched_cborg_2026-09-13/native_controls/native_readonly.py | test_audit_recall_leak_rendered.py |
| prepare_direct | /Users/marcin/agent-work/data-sheets-schema/ci-sim-f25230fe1e56/notes/claudecode_direct/prepare_direct.py | test_audit_recall_leak_rendered.py |
| prepare_overlay_roster | /Users/marcin/agent-work/data-sheets-schema/ci-sim-f25230fe1e56/notes/matched_cborg_2026-09-13/native_controls/prepare_overlay_roster.py | test_audit_recall_leak_rendered.py |
| prepare_registration | /Users/marcin/agent-work/data-sheets-schema/ci-sim-f25230fe1e56/notes/matched_cborg_2026-09-13/prepare_registration.py | test_audit_recall_leak_rendered.py |
| run_api_canary | /Users/marcin/agent-work/data-sheets-schema/ci-sim-f25230fe1e56/notes/matched_cborg_2026-09-13/run_api_canary.py | test_audit_recall_leak_rendered.py |
| run_direct_canary | /Users/marcin/agent-work/data-sheets-schema/ci-sim-f25230fe1e56/notes/claudecode_direct/run_direct_canary.py | test_audit_recall_leak_rendered.py |
| run_native_canary | /Users/marcin/agent-work/data-sheets-schema/ci-sim-f25230fe1e56/notes/matched_cborg_2026-09-13/native_controls/run_native_canary.py | test_audit_recall_leak_rendered.py |

## Partition scenarios

Values use the current branch partition function. Seconds are summed scheduling weights; minutes divide the evaluated total by four workers and sixty seconds. They are not elapsed-job predictions. Unmeasured files retain prior weights or the current median fallback.

| Model | Shards | Largest scheduled seconds | Largest evaluated seconds | Ideal four-worker minutes |
|---|---:|---:|---:|---:|
| native_only | 6 | 10461.619 | 16410.446 | 68.38 |
| native_only | 8 | 7846.217 | 11884.935 | 49.52 |
| native_only | 9 | 6974.415 | 11048.084 | 46.03 |
| native_only | 10 | 6276.972 | 10189.251 | 42.46 |
| native_only | 12 | 5230.810 | 9363.612 | 39.02 |
| native_only | 16 | 5162.752 | 7945.203 | 33.11 |
| all_measured | 6 | 11038.183 | 11038.183 | 45.99 |
| all_measured | 8 | 8278.637 | 8278.637 | 34.49 |
| all_measured | 9 | 7358.790 | 7358.790 | 30.66 |
| all_measured | 10 | 6622.911 | 6622.911 | 27.60 |
| all_measured | 12 | 5918.253 | 5918.253 | 24.66 |
| all_measured | 16 | 5918.253 | 5918.253 | 24.66 |
| all_measured_equal_four_way_scanner_split | 8 | 8278.905 | 8278.905 | 34.50 |
| all_measured_equal_four_way_scanner_split | 9 | 7359.027 | 7359.027 | 30.66 |
| all_measured_equal_four_way_scanner_split | 10 | 6623.125 | 6623.125 | 27.60 |
| all_measured_equal_four_way_scanner_split | 12 | 5519.272 | 5519.272 | 23.00 |

## Native files without measurements

| File | Scheduled seconds | Median fallback |
|---|---:|---|
| tests/test_native_d128_scanner_comparison.py | 3.7645 | True |
| tests/test_native_execution_round6_v2.py | 3.7645 | True |
| tests/test_native_model_aliases.py | 3.7645 | True |
| tests/test_native_shared_acceptance_runner.py | 3.7645 | True |
| tests/test_native_shared_controls.py | 3.7645 | True |
| tests/test_native_shared_gates.py | 3.7645 | True |
| tests/test_native_shared_permissions.py | 3.7645 | True |
| tests/test_native_shared_registration.py | 3.7645 | True |
| tests/test_native_shared_schema_gates.py | 3.7645 | True |
| tests/test_native_subscription_guard_v2.py | 3.7645 | True |
| tests/test_native_u3b_reuse.py | 3.7645 | True |
| tests/test_native_u3c_test_driver.py | 3.7645 | True |
| tests/test_native_u4b_a3_captures.py | 3.7645 | True |
| tests/test_native_u4b_a4_real_events.py | 3.7645 | True |
| tests/test_native_u4b_capture_retries.py | 3.7645 | True |
| tests/test_native_u5_scanner.py | 3.7645 | True |

## Local scanner profile

| Operation | Profiled seconds | Error |
|---|---:|---|
| cold_discovery | 197.221893 | ConfigError('model-facing native command table lacks its derived native-only route') |

## Exact CI scanner profile

| Operation | Profiled seconds | Cache after call | Error |
|---|---:|---|---|
| cold | 182.462357 | CacheInfo(hits=0, misses=1, maxsize=None, currsize=0) | ConfigError('api meaning not derived: separate native shared render route (v2 envelope authority source changed: src/data_sheets_schema/native_execution_authority_v2.py). The code that decides it changed shape; update the derivation in scan.py rather than reporting a fallback (#4025)') |
| repeat | 120.965951 | CacheInfo(hits=0, misses=2, maxsize=None, currsize=0) | ConfigError('api meaning not derived: separate native shared render route (v2 envelope authority source changed: src/data_sheets_schema/native_execution_authority_v2.py). The code that decides it changed shape; update the derivation in scan.py rather than reporting a fallback (#4025)') |

## Largest scanner class intervals in cancelled CI log

These are completion intervals, including possible scheduling gaps; they are not isolated CPU measurements.

| Class | Seconds | Outcomes |
|---|---:|---|
| TestTheScannerSees | 861.918 | {"FAILED": 7, "PASSED": 12} |
| TestLaunchFlags | 656.156 | {"FAILED": 6, "PASSED": 8} |
| TestApiMeaning | 481.357 | {"ERROR": 22} |
| TestDiscovery | 467.678 | {"ERROR": 21} |
| TestRunShapingYamlAndShell | 435.091 | {"FAILED": 4, "PASSED": 2} |
| TestModelFacingDerivation | 433.236 | {"FAILED": 3, "PASSED": 182} |
| TestProjectKeyedCode | 334.744 | {"FAILED": 3, "PASSED": 2} |
| TestConstantText | 330.626 | {"FAILED": 3, "PASSED": 2} |
| TestWhatTextsRun | 318.315 | {"ERROR": 4} |
| TestAssistantInstructions | 226.278 | {"FAILED": 2} |
| TestControllerRuns | 225.904 | {"FAILED": 2, "PASSED": 2} |
| TestModelFacingAssets | 222.596 | {"FAILED": 2, "PASSED": 8} |

## Artifacts

Code branch head: `01c9b7b862330ad1f8a363a1b45f912e013c702b`. JSON: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/codex-h3-ci-origin-and-shard-time-20261112.json` (SHA-256 `58ac3f3e5c52d6b04f7be3b7c5465986e12d8d722c32b8e287057b7190fb1370`).
Scratch evidence: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-h3-ci-20261112`. Scripts: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy-native-ci-collection-20261112/scripts/adhoc` with the `h3_` prefix and `run_h3_ci_tests_20261112.py`. No push, GitHub write, workflow edit, scanner edit, provider call or native-program call.

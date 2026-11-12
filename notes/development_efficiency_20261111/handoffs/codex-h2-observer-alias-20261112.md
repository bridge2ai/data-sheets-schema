# Helper 2 handoff: observer alias and test repairs

Implemented and locally committed Parts A, B and C. The observer now checks the declared returned label on assistant frames and the requested label on user/result frames, while keeping requested-model initialization. The focused capture assertions and new offline guard CLI test pass. Public completion is still unverified: the unchanged protected candidate fails during RunSpec construction before any assistant/tool-use frame, so this run cannot establish progress beyond G07-F6 in the full public lifetime.

No push, GitHub write, provider/model/native-binary invocation, cpu-monitoring diagnostic, private-composition arming, or pin update was performed. Existing capture component tests execute their scripted Python peer; the new CLI test permits only Git subprocesses. The primary checkout and helper 1 worktree were not edited.

## Local commits

- 91fcdab3311c65ba8591836db75e241b78cf10ac fix(native): check observed frame models against declared alias roles
- 37a4aa5d0ab07ed270ef6211f35e7a377e2472b6 test(native): assert direct capture trace and early pinned-review refusal
- 789778427d029ccc2d66b1b926c8921ceef79556 test(native): exercise v2 guard CLI publication and stale-capture refusal

Branch: `codex/native-observer-alias-20261112`. Worktree: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-native-observer-alias-20261112`. Working tree is clean; the complete commit diff reports one cosmetic finding: `scripts/adhoc/run_native_h2_tests_20261112.py:419: new blank line at EOF`. Changes received a separate read-only diff review; the copied runner retains a trailing blank line, recorded here as H2-F1 and left for the lead to avoid rewriting the required three commits. No remote issue was filed because this assignment prohibits GitHub writes.

## Changes and source reading

Part A: `native_model_aliases.model_aliases` defines the closed requested/returned pair. `require_frame_models` requires the returned label on current assistant frames, rejects contradictory labels in either the frame or nested message, and retains optional labels for historical identical aliases. Trace now derives this pair once and applies that helper to its existing assistant/user/result frame set. `_initialization_from_rows` still requires `runtime.model`. Terminal modelUsage remains checked by the existing final gate; this partial-prefix observer does not replace it.

The other current frame checks already use this division: `native_shared_permissions._native_scope`, `native_gate_engine` terminal checking, `native_u4b_runtime._saved_probe`, and `native_u4b_probe_sequence` saved stream validation. Init and terminal modelUsage use the requested label; assistant frames and the local-provider request use the returned label. No peer or alias-helper behavior was changed.

Added observer coverage for returned labels at frame/message/both locations, wrong/null/opposite labels for assistant/user/result, missing current assistant labels, reversed initialization, and historical optional/equal labels.

Part B: a direct read calls full verified reconstruction followed by outer-claims without the recheck marker. The event lookup still asserts its original four-step trace. A changed review document fails in `_capture_manifest_root` through `validate_bundle` and `_review_document` before `_recheck_verified`, with exact text `review document differs from its pinned bytes` and trace `verified, mutated`. All other mutations retain the recheck assertion. The initial test edit used an incorrect expected error literal; its saved failing run is retained and the literal was corrected to the production message.

Part C: `test_native_generation_guard_v2.py` invokes the actual command body with fabricated retained capture evidence. It checks the supplied manifest and require_latest flag, genuine guard construction, output bytes and reported SHA-256, exclusive publication on repeat, and refusal of that older capture after a second durable unfinished claim without creating another output. Registration reconstruction and render metadata validation are explicit routing stubs; runtime, review/word validation, capture reconstruction, latest-claim enforcement and publication remain real. This is not full registration or account acceptance.

## Saved test results

All rows are extracted from saved JUnit files. Counts overlap across reruns and must not be summed as unique coverage. The initial one-test runner canary passed, with nonempty log/JUnit, source-origin witnesses, OS network-denial witness and verified cleanup; it did not prove public integration.

| Cohort | Passed | Failures | Errors | Skipped |
| --- | ---: | ---: | ---: | ---: |
| alias-canary | 1 | 0 | 0 | 0 |
| alias-unit | 107 | 0 | 2 | 0 |
| capture-assertions | 6 | 1 | 0 | 0 |
| capture-assertions-final | 7 | 0 | 0 | 0 |
| guard-cli | 1 | 0 | 0 | 0 |
| public-completion | 0 | 1 | 0 | 0 |
| public-paths | 31 | 1 | 29 | 0 |

Evidence root: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-h2-observer-alias-20261112/tests`. Each cohort has command, JUnit, log, network, import-origin and outcome files. Full individual test identities and artifact hashes are in `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-h2-observer-alias-20261112/h2-audit.json`.

## Public completion stopping point

The single requested completion test fails in `make_case` during `build_native_fixture` preparation, at `native_execution_registration_v2.py:254`: `RunSpec.__init__() got an unexpected keyword argument native_shared_generation_version`. No assistant frame, worker stage or saved completion is reached. The public-paths cohort uses the same three test modules as helper 1, serially with no xdist workers. Its failures are retained, not repaired.

Helper 1 ran public-paths on `scratch-native-main-integration-20261112/g07-c/tree`, as its saved bootstrap.json shows. This assignment starts from the protected candidate itself and prohibits private-composition arming. Therefore its earlier 60-pass/1-failure result is not an apples-to-apples baseline. The two alias integration setup errors also cite the protected RunSpec mismatch. The lead must rerun this observer commit in the separately authorized composition to establish full public completion. No later failure beyond the assistant frame has been observed or chased here.

## Pin and closure impact

Observer SHA-256 before: `41459563575a0c9e0c396c488cb25afbd0f8421896b904ecfc290972ca1b3ae2`. After: `e11f7a08e1d2e1a969e0bc90402cc70091f144d7ffbf47694e40ab779c66b93e`.

The ignore-independent hidden-file-inclusive searches cover this entire new worktree, excluding only the Git pointer. No literal occurrence of the old observer SHA-256 was found. All observer-name references were retained in scratch. The controller source manifest does not pin this package module; scanner fixed-source dictionaries do not directly pin it. The existing stale scanner authority pin is unchanged and was not repaired or revalidated.

The following derived bindings move and require fresh lead-controlled evidence; none was updated:

- `dependencies.base.package_sources[src/data_sheets_schema/native_shared_observations.py]` changes to the new observer digest, and the containing dependency identity/hash and source_commit change.
- `permission_expectation.production_sources` includes every nonempty package Python source, so the observer row SHA-256/byte length, aggregate production SHA-256, expectation and dependent saved-probe/registration bindings change.
- Verified consumer graphs that reach Trace acquire its direct alias-helper import and observe changed observer bytes; their graph identities must be recomputed. The helper was already present in the full package roster. No fixed pure-graph pin was rewritten.
- Registrations, review/word/guard documents and saved execution evidence bound transitively to the previous source/dependency identity cannot be reused as current authority.

The audit JSON records static before/after package-source and production-source aggregate hashes with this worktree path held fixed. Those are audit calculations, not new authority or approval. Protected files remain byte-identical to both the assigned candidate and integrated main `7ad8c9e7295f1575ae9108ea62c12c83b1dd4db1`; all file hashes are in the audit.

## Handoff artifacts and limits

Audit: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-h2-observer-alias-20261112/h2-audit.json`, SHA-256 `7c5116949b85c9d339df62fad340e95b6cc9288091dc0d1b5b96d29b3d55fb79`.

Report helper left in the report worktree, uncommitted for the lead: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/scripts/adhoc/report_h2_observer_alias_20261112.py`, SHA-256 `d3039eefe7511078ba02b9c0176e4d76d3386c44d8a14d04e4779052d3807aeb`. Repair/runner scripts are committed with Parts A and B under the assigned worktree scripts/adhoc directory.

No full suite, scanner clearance, real capture, real runtime, CI, native canary or full public completion is claimed. Work stops here for the lead to integrate and review the local commits; no pins or protected files should be silently refreshed.

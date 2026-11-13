# Native scanner authority repair and integration — 2026-11-12

The scanner authority repair is committed locally; a complete current scanner comparison is still pending. Of the 96 retained scanner negatives, 96 have verified passing witnesses and 0 remain unobserved. Detailed outcomes and integration status follow. Separately, 42 of 44 retained CI authority-pin identities have verified passing witnesses. The broader scanner cohort remains 740 passed, 2 failed, 0 errors and 9 skipped; clearing retained identities is not whole-cohort acceptance.

Phase: Lead accepted H2 observer/test commits in STATUS; integrating and testing each; earlier comparison preserved and final refresh pending. Branch head: `1cd2264274898fc6dcbf1cb8a3e6c7a6a980eaa2`.

**Owner-facing interpretation**

The scanner checks how local source code selects and constructs model-facing instructions. The repair recognizes reviewed authority bytes while keeping exact rendering templates and refusal checks. It does not authorize native execution or certify successful generation.

The historical D128 approval covers its original source pair. The current itemized comparison below identifies what remains covered and what is new. Approving that comparison would dispose of this new scanner evidence; it would not approve the pending protected API packet, the margin change or a launch.

**Pending decisions**

- The API packet postimage 830eec1e12e96f807fa76ea26e066a1923b60380013c424cfa99f0012af0a881 is not approved.
- D136 settles freshness age 1200 seconds. Margin remains 90 seconds in code. N1 is at ballot draft v12 and is not ratified; its proposed 300-second margin still awaits the owner.
- The current complete D128-form comparison needs an explicit disposition; historical approval applies only to its frozen source pair.
- No launch, native canary, publication or scientific acceptance is claimed.

**Local commits**

| Full SHA | Change |
| --- | --- |
| 66fecb7be53aea49e371e224593203990f33763e | Bind reviewed authority bytes while preserving exact native render derivation |
| 8a00bb828d9df29bfedda3b6745121dc746b6742 | Preserve H1 offline composition and test evidence in separate scratch |
| 058de60779412150c529e41c86c5cfe9047014da | Load the quiet-lock runner from a temporary layout so its tests collect anywhere (#5875) |
| 79089536b698dd2dd968233da4eadc8841f76b10 | Make three native test files independent of this machine's directory layout |
| 6846d84042a84d5fe26513684430815c523e5b75 | fix(native): check observed frame models against declared alias roles |
| 1cd2264274898fc6dcbf1cb8a3e6c7a6a980eaa2 | test(native): assert direct capture trace and early pinned-review refusal |

**Protected branch files**

| Path | Branch SHA-256 | Working and committed bytes equal main |
| --- | --- | --- |
| src/data_sheets_schema/shared_generation.py | 94b3cf6845827c8fdf7bf05cc6251e2fb196ceb91ea8ce377f2c9e3b8be3773d | True |
| src/data_sheets_schema/api_runner.py | 23dcc828d171000173bd521edfbc55b38bfcf6c0adb41c6b962c10f381e911bb | True |
| src/download/prompts/canonical_hashes.yaml | 39b93c009457681a1d8d8b8afee5a869bbd6f5e70b6f4332522db5d7e22d0584 | True |
| tests/utils/run_spec_boundary_contracts.json | a7f96a253a37e994f0c62c7d9b2ab21b0a94d4f342975f84103cd274ef11af72 | True |

**Authority review**

Rendering meaning is preserved. Full authority behavior changed, including legitimate nonconsumer snapshot admission; it is not merely formatting.

- 5503684ee extends launch-scoped schema import metadata reuse.
- e282f0596 clears snapshot LRUs on donor state or phase changes.
- d6f51f8ed replaces consumer-registry membership with exact snapshot name/path/digest attestation and fresh byte checks.
- 033cd731f retains immutable import facts while applying current source checks, lint, origins and graph traversal.

The first source drift and subsequent unsynchronized commits are recorded below.

| Authority-changing commit | Authority SHA-256 | Scanner pin | Scanner edited | Pin matches source |
| --- | --- | --- | --- | --- |
| 5503684eeaabe3305333d4eefb931f311f86c1e8 | 84fb24d1283465bf3a5e7a61e929b6b0e1020508a165c175f57aff4b63682d08 | bfdb5c86feb4c071ebf17e6ececa8fd60f1bc23bda98fefd42c0c211ecd7511a | False | False |
| e282f05960a2b397844acb3ac5f140b1fe192cd8 | 699ba0beb0f3c4e141477c6a11a50531e88975accde53e290dab3e5ea288bc07 | bfdb5c86feb4c071ebf17e6ececa8fd60f1bc23bda98fefd42c0c211ecd7511a | False | False |
| d6f51f8ed3da7928e66e81fa48f47722a77bbdf5 | 9b7a2d3842a007bae35f2d079e6ffa631190e7d2f4b5f10aad9a6d1243407687 | bfdb5c86feb4c071ebf17e6ececa8fd60f1bc23bda98fefd42c0c211ecd7511a | False | False |
| 033cd731f6d9a854143076a8bd13125d61101f92 | b2189db86428b5977bfcbaa72adc5f504f3449c31b583359555b074916a95558 | bfdb5c86feb4c071ebf17e6ececa8fd60f1bc23bda98fefd42c0c211ecd7511a | False | False |

Requested historical checkpoints:

| Full checkpoint SHA | Authority SHA-256 | Scanner pin | Pin matches source |
| --- | --- | --- | --- |
| 1a137b58860416a31618de44173180d021dfcc61 | b2189db86428b5977bfcbaa72adc5f504f3449c31b583359555b074916a95558 | bfdb5c86feb4c071ebf17e6ececa8fd60f1bc23bda98fefd42c0c211ecd7511a | False |
| 382f0dfd1ce863fdf257a77e2bbb2637dbe2f67b | b2189db86428b5977bfcbaa72adc5f504f3449c31b583359555b074916a95558 | bfdb5c86feb4c071ebf17e6ececa8fd60f1bc23bda98fefd42c0c211ecd7511a | False |

The four authority-changing commits omit the scanner file and all retain its old authority digest.
The scanner source dependency was not synchronized while authority changes landed; commit evidence does not identify motive or intentional waiver.

| Rendering authority helper | Exact source unchanged | AST unchanged |
| --- | --- | --- |
| _VerifiedAliasLoader | True | True |
| _VerifiedBytesFinder | True | True |
| _VerifiedBytesLoader | True | True |
| _main_thread | True | True |
| _own_callables | True | True |
| _package_roster | True | True |
| _require_package_roster | True | True |
| _require_v2 | True | True |
| _source_identity | True | True |
| _verified_source_bytes | True | True |
| dependency_identity | True | True |
| launch_derivations | True | True |
| loaded_dependencies | True | True |
| loaded_verified_package_module | True | True |
| module_source_identity | True | True |
| require_committed | True | True |
| verified_source_module | True | True |

Audit path: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/codex-h1-authority-audit-20261112.json`; SHA-256 `2518fb3330c6b027d04f9947ec951e2ab2a625998c52f6488603f11e39998b47`. Raw Git command outputs and all seven other source-pin checks are retained there.

**Composition attempts**

| Manifest | Status | Source | Error | SHA-256 |
| --- | --- | --- | --- | --- |
| /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-h1-scanner-20261112/h1-a/composition.json | refused | 8a00bb828d9df29bfedda3b6745121dc746b6742 | extractall() got an unexpected keyword argument 'filter' | 718809bc855da0f6e009c939ebfa6c97b81a8353244be26c9d2eae0988e6cef8 |
| /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-h1-scanner-20261112/h1-b/composition.json | composed_not_tested | 8a00bb828d9df29bfedda3b6745121dc746b6742 | None | 0cfe7eb584f218071b4b165494ebfaf6c1c83ff4ea0cfba03afba7624a15c97a |
| /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-h1-scanner-20261112/h1-c/composition.json | composed_not_tested | 79089536b698dd2dd968233da4eadc8841f76b10 | None | 79fb7a3a456ee296ca98d13acca162e3139f40d0642bb0c5fc803f3c90ac611e |
| /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-h1-scanner-20261112/h1-d/composition.json | composed_not_tested | 6846d84042a84d5fe26513684430815c523e5b75 | None | dd545d5ee0dc389bb7033cfcff30ccdb7e488c129f77901ed9f4edb47b5163ae |
| /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-h1-scanner-20261112/h1-e/composition.json | composed_not_tested | 1cd2264274898fc6dcbf1cb8a3e6c7a6a980eaa2 | None | 594f06c0066473ac474a20369b22f75acc4e1f56d012165199195831e5cfb576 |

**Test evidence**

| Cohort | State | Exact source | JUnit cases | Exit |
| --- | --- | --- | --- | --- |
| h1-canary | completed | 3a582243c4277934415bceb92cb888d617fd7a14 | {"passed": 1} | 0 |
| h1-ci-scanner | completed | 3a582243c4277934415bceb92cb888d617fd7a14 | {"passed": 34, "failure": 2} | 1 |
| h1-observer-canary | completed | e1d23959737cdbab6a46373fcb5a2c7a16070c8c | {"passed": 1} | 0 |
| h1-observer-file | completed | e1d23959737cdbab6a46373fcb5a2c7a16070c8c | {"passed": 75} | 0 |
| h1-portability-first | completed | 058de60779412150c529e41c86c5cfe9047014da | {"error": 4} | 1 |
| h1-portability-second | completed | 07d87f79522372205c475768516d48f1dab344cd | {"failure": 5, "passed": 2, "skipped": 3} | 1 |
| h1-scanner-cohort | completed | 3a582243c4277934415bceb92cb888d617fd7a14 | {"passed": 740, "skipped": 9, "failure": 2} | 1 |

**Exact prior-negative reconciliation**

| Current state | Prior negative identities |
| --- | --- |
| cleared | 96 |

Every original negative identity and its current witnesses are retained in the JSON. Classnames are mapped through actual source files; absent or unfinished evidence cannot clear a case.

**Retained CI authority-pin failures**

| Current state | Retained CI identities |
| --- | --- |
| cleared | 42 |
| failure | 2 |

| Retained CI module | Distinct identities |
| --- | --- |
| tests/test_native_u3l_scanner.py | 12 |
| tests/test_native_u1_scanner_contracts.py | 14 |
| tests/test_native_u3l_review_fixtures.py | 9 |
| tests/test_native_u4b_a5_scanner.py | 9 |

Exact identity overlap with the prior G07 set: 0. CI identities are a subset of G07: False. All original CI job occurrences and exact current witnesses are retained in the JSON.

**Scanner comparison**

These complete diagnostic arrays belong to an earlier branch head and are retained as intermediate evidence. The current head still needs its own comparison; no owner approval is implied.

| Source comparison | Array | Before | After | Exact occurrences | Line relocations | Field changes | Added | Removed | Positional records |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| current_main_vs_current_candidate | hits | 5307 | 5308 | 5244 | 57 | 6 | 1 | 0 | 4115 |
| current_main_vs_current_candidate | test_dependencies | 101 | 103 | 101 | 0 | 0 | 2 | 0 | 53 |
| current_main_vs_current_candidate | violations | 9 | 9 | 9 | 0 | 0 | 0 | 0 | 0 |
| frozen_D128_main_vs_current_main | hits | 5292 | 5307 | 2796 | 2488 | 2 | 21 | 6 | 3888 |
| frozen_D128_main_vs_current_main | test_dependencies | 101 | 101 | 79 | 22 | 0 | 0 | 0 | 22 |
| frozen_D128_main_vs_current_main | violations | 9 | 9 | 9 | 0 | 0 | 0 | 0 | 0 |
| frozen_D128_candidate_vs_current_candidate | hits | 5293 | 5308 | 2797 | 2488 | 2 | 21 | 6 | 3888 |
| frozen_D128_candidate_vs_current_candidate | test_dependencies | 103 | 103 | 81 | 22 | 0 | 0 | 0 | 22 |
| frozen_D128_candidate_vs_current_candidate | violations | 9 | 9 | 9 | 0 | 0 | 0 | 0 | 0 |

Finite-delta comparison with D128:

| Array | Delta type | Current deltas | Same finite D128 delta | New difference |
| --- | --- | --- | --- | --- |
| hits | added | 1 | 1 | 0 |
| hits | changed_fields | 6 | 5 | 1 |
| hits | relocations | 57 | 41 | 16 |
| hits | removed | 0 | 0 | 0 |
| test_dependencies | added | 2 | 2 | 0 |
| test_dependencies | changed_fields | 0 | 0 | 0 |
| test_dependencies | relocations | 0 | 0 | 0 |
| test_dependencies | removed | 0 | 0 | 0 |
| violations | added | 0 | 0 | 0 |
| violations | changed_fields | 0 | 0 | 0 |
| violations | relocations | 0 | 0 | 0 |
| violations | removed | 0 | 0 | 0 |

Current deltas without an exact finite D128 match (coordinates are retained, not normalized or waived):

| Path | Delta | Before line | After line | Changed fields | Exact before values | Exact after values |
| --- | --- | --- | --- | --- | --- | --- |
| src/data_sheets_schema/agentic_observed.py | changed_fields | 17 | 17 | ["approaches"] | {"approaches": {"present": true, "value": ["api", "native_agentic", "github_assistant"]}} | {"approaches": {"present": true, "value": ["api", "native_agentic", "deterministic", "github_assistant"]}} |
| src/data_sheets_schema/api_runner.py | relocations | 5382 | 5426 | ["line"] | {"line": {"present": true, "value": 5382}} | {"line": {"present": true, "value": 5426}} |
| src/data_sheets_schema/api_runner.py | relocations | 5483 | 5527 | ["line"] | {"line": {"present": true, "value": 5483}} | {"line": {"present": true, "value": 5527}} |
| src/data_sheets_schema/api_runner.py | relocations | 5818 | 5862 | ["line"] | {"line": {"present": true, "value": 5818}} | {"line": {"present": true, "value": 5862}} |
| src/data_sheets_schema/api_runner.py | relocations | 6971 | 7015 | ["line"] | {"line": {"present": true, "value": 6971}} | {"line": {"present": true, "value": 7015}} |
| src/data_sheets_schema/api_runner.py | relocations | 5840 | 5884 | ["line"] | {"line": {"present": true, "value": 5840}} | {"line": {"present": true, "value": 5884}} |
| src/data_sheets_schema/api_runner.py | relocations | 5990 | 6034 | ["line"] | {"line": {"present": true, "value": 5990}} | {"line": {"present": true, "value": 6034}} |
| src/data_sheets_schema/api_runner.py | relocations | 6156 | 6200 | ["line"] | {"line": {"present": true, "value": 6156}} | {"line": {"present": true, "value": 6200}} |
| src/data_sheets_schema/api_runner.py | relocations | 6439 | 6483 | ["line"] | {"line": {"present": true, "value": 6439}} | {"line": {"present": true, "value": 6483}} |
| src/data_sheets_schema/api_runner.py | relocations | 6493 | 6537 | ["line"] | {"line": {"present": true, "value": 6493}} | {"line": {"present": true, "value": 6537}} |
| src/data_sheets_schema/api_runner.py | relocations | 6621 | 6665 | ["line"] | {"line": {"present": true, "value": 6621}} | {"line": {"present": true, "value": 6665}} |
| src/data_sheets_schema/api_runner.py | relocations | 6622 | 6666 | ["line"] | {"line": {"present": true, "value": 6622}} | {"line": {"present": true, "value": 6666}} |
| src/data_sheets_schema/api_runner.py | relocations | 7257 | 7301 | ["line"] | {"line": {"present": true, "value": 7257}} | {"line": {"present": true, "value": 7301}} |
| src/data_sheets_schema/api_runner.py | relocations | 7368 | 7412 | ["line"] | {"line": {"present": true, "value": 7368}} | {"line": {"present": true, "value": 7412}} |
| src/data_sheets_schema/api_runner.py | relocations | 7989 | 8035 | ["line"] | {"line": {"present": true, "value": 7989}} | {"line": {"present": true, "value": 8035}} |
| src/data_sheets_schema/api_runner.py | relocations | 8282 | 8328 | ["line"] | {"line": {"present": true, "value": 8282}} | {"line": {"present": true, "value": 8328}} |
| src/data_sheets_schema/api_runner.py | relocations | 8288 | 8334 | ["line"] | {"line": {"present": true, "value": 8288}} | {"line": {"present": true, "value": 8334}} |

The unmatched approach-label pair at `src/data_sheets_schema/agentic_observed.py:17` has the same approaches-list transition as D128. It is still a different finite pair: the current before/after role annotations are `model_facing` / `model_facing`, whereas the historical annotations are `run_shaping` / `run_shaping`. Full before-object differences: ['role']; full after-object differences: ['role'].

All four objects retain model_facing=false, empty gates_in and violation=false: True. This is not a new violation. The changed annotation is not normalized away and no equivalence or approval is inferred.

Other current model-text function-coordinate changes, shown with their actual finite D128 matching status:

| Path | Before line | After line | Changed fields | Exact before values | Exact after values | Exact finite D128 match |
| --- | --- | --- | --- | --- | --- | --- |
| src/data_sheets_schema/api_runner.py | 2219 | 2261 | ["line", "model_text_function"] | {"line": {"present": true, "value": 2219}, "model_text_function": {"present": true, "value": "PHASE_INSTRUCTIONS (sent in a PhaseRequest at src/data_sheets_schema/api_runner.py:3254)"}} | {"line": {"present": true, "value": 2261}, "model_text_function": {"present": true, "value": "PHASE_INSTRUCTIONS (sent in a PhaseRequest at src/data_sheets_schema/api_runner.py:3298)"}} | True |

The ordered violation arrays match across current main/candidate and both frozen D128 comparisons: True; violation count 9. The complete hit arrays and scanner tool identities still changed. Identical violation objects do not transfer approval or establish semantic equivalence for other differences.

Matching finite object deltas do not approve changed tool, source or array ordering. Every full occurrence object remains in the hash-linked itemized ledger.

Complete occurrence objects, exact match indices, violations and ordering changes: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-h1-scanner-20261112/h1-final-comparison/comparison.json`; SHA-256 `25e4657372c0ca35fc80aff1f67f7769de01f00f4f9fd7bf89b600b5d102ada6`. JSON pointers in the report locate each itemized group.

Approving the new comparison would address these new scanner findings and tool/source identities. It would not approve the API packet, the pending margin proposal or a native launch.

**Findings and limits**

| Finding | Status | Evidence and limits |
| --- | --- | --- |
| H1-F1 | runner_provenance_limitation | The runner records HEAD and four protected hashes but does not itself attest the complete tracked working tree. Composition creation and final tracked-clean witnesses mitigate this gap; they do not establish a full before-run content manifest. |
| H1-F2 | observed_scope_layout_blocker | Completed test evidence records temporary-layout refusals: the copied-helper fixtures reject the allowed TMPDIR under d4d-executions, while system tmp is outside the permitted sandbox scratch. This conflicts with the authorized test environment and is not a demonstrated production failure. The affected copied-helper assertions are not validated. |
| H1-F3 | resolved_by_recorded_helper_controls | Independent pre-execution review found a false-completion risk when worker returncode is null but the OS exit is 1. The comparison helper must require matching, typed worker and process exit codes before treating arrays as complete. No run was claimed complete using this defect. |
| H1-F4 | resolved_by_recorded_helper_controls | Independent pre-execution review found that cleanup by numeric process-group ID risks signalling a reused group. The comparison helper must bind owned processes to their recorded identities and refuse signalling replacements. No affected helper run was performed. |
| H1-F5 | requires_lead_contract_ruling | Two observed ambiguous argv alias tests conflict with main scanner precision policy. Static source and AST comparisons show the four direct-call-path functions are identical from main through the pre-pin candidate and tested composition; this path does not read the native authority pin. This is a pre-existing integration contract disagreement, not a regression caused by the authority digest update. No historical test rerun was performed. |
| H1-F6 | requires_lead_fixture_disposition | Retained historical known-gap fixture expectations disagree with the current complete scanner arrays. Separate source-history audits establish that the F3d and B2 expectations predate intentional main scanner improvements. The current positive controls support those bounded improvements; the historical fixture assertions still fail. Keep each failure visible and do not change frozen fixtures or count retained CI identities as cleared without completed passing witnesses. |

These are local review findings for lead publication. No GitHub issues, comments or reviews were created during this offline assignment.

H1-F2 observed temporary-layout negatives: 9. They are environment-scope refusals, not validated production failures.

H1-F2 recommendation: Request a narrow lead ruling on permitted temporary layout, or refactor the copied-helper fixtures to meet the approved layout while preserving production guards. No fixture assertion weakening, sandbox expansion or out-of-scope repair is authorized here.

**H1-F5: unresolved scanner integration contract**

Two observed ambiguous argv alias tests conflict with main scanner precision policy. Static source and AST comparisons show the four direct-call-path functions are identical from main through the pre-pin candidate and tested composition; this path does not read the native authority pin. This is a pre-existing integration contract disagreement, not a regression caused by the authority digest update. No historical test rerun was performed.

| Observed failed test | Actual failure |
| --- | --- |
| tests/test_native_u1_scanner_contracts.py::test_model_named_table_ambiguous_argv_alias_refuses[args = ('python', '-m', 'data_sheets_schema.second_command')\nargs = ('python', '-m', 'data_sheets_schema.third_command')\n] | Failed: DID NOT RAISE <class 'delegated_scanner.ConfigError'> |
| tests/test_native_u1_scanner_contracts.py::test_model_named_table_ambiguous_argv_alias_refuses[first = ('python', '-m', 'data_sheets_schema.second_command')\nsecond = ('python', '-m', 'data_sheets_schema.third_command')\nargs = first\nargs = second\n] | Failed: DID NOT RAISE <class 'delegated_scanner.ConfigError'> |

Source-history classification: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/codex-h1-ambiguous-table-finding-20261112.json`; SHA-256 `7871e9de51575dd8965ecd5c3948df0853ac0a6f4531680601d491c42b680f7c`.

Main changed this behavior deliberately in `a939fed2eeddc1a6487269230be8b97dde8e6863`; the older native test contract originated in `85ff9bbff76d96f29ae61bc3528f682d92154261`.

Recommended separate follow-up, requiring lead disposition: Preserve main precision behavior pending lead disposition. Replace these two old unconditional-refusal expectations only after adding explicit positive coverage witnesses with both target modules materialized, proving every complete literal alternative is discovered; retain negatives for unresolved alternatives and ambiguous -m operands.

Separate scanner contract follow-up, not an authority-pin repair. No test deletion, xfail, approval expansion or production change performed here.

None: no test deletion, xfail, assertion weakening or scanner behavior change.

**H1-F6: retained known-gap fixture disagreements**

Retained historical known-gap fixture expectations disagree with the current complete scanner arrays. Separate source-history audits establish that the F3d and B2 expectations predate intentional main scanner improvements. The current positive controls support those bounded improvements; the historical fixture assertions still fail. Keep each failure visible and do not change frozen fixtures or count retained CI identities as cleared without completed passing witnesses.

| Observed fixture | Expected violations | Actual violations | Scanner derivation complete | Fixture run status | Saved assertion |
| --- | --- | --- | --- | --- | --- |
| tests/test_native_u3l_review_fixtures.py::test_retained_review_outcome[B2_typed_container_alias_token] | 9 | 10 | True | incomplete | AssertionError: assert 10 == 9<br> +  where 10 = len([{'approaches': ['run_controllers'], 'category': 'gc_project', 'code': True, 'context': 'code_table', ...}, {'approach..., ...}, {'approaches': ['run_controllers'], 'category': 'gc_project', 'code': True, 'context': 'code_table', ...}, ...]) |
| tests/test_native_u3l_review_fixtures.py::test_retained_review_outcome[F3d_module_helper_print] | 9 | 11 | True | incomplete | AssertionError: assert 11 == 9<br> +  where 11 = len([{'approaches': ['run_controllers'], 'category': 'gc_project', 'code': True, 'context': 'code_table', ...}, {'approach..., ...}, {'approaches': ['run_controllers'], 'category': 'gc_project', 'code': True, 'context': 'code_table', ...}, ...]) |

Exact scan arrays, command, stable-input census and completed-test witnesses are hash-linked in the JSON. A saved fixture run does not substitute for the final cohort JUnit and cleanup evidence.

Per-fixture source-history classification:

| Fixture | Evidence state | Audit | SHA-256 |
| --- | --- | --- | --- |
| B2_typed_container_alias_token | present | /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/codex-h1-retained-container-finding-20261112.json | 3661f9ec60752c9a7aafe12d0683f8683c4be622b3eb075760a2125db950b28b |
| F3d_module_helper_print | present | /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/codex-h1-retained-gap-finding-20261112.json | a74ce1bbbf8df2855ef0608d0d9446ad9fd432848e599df4594d8b7a3bde5f7a |

**B2_typed_container_alias_token source evidence**

- The B2 fixture introduces project_hints.project_hint and stores its result via view = contracts; view[worker][hint] = project_hint(project) in typed_audit._derive_uncached.
- Main a4270683eaeebc2f3d676e04614579e743a353e1 intentionally addresses issue5657: _local_writes propagates stores/method arguments across plain aliases; effects walks or refuses alias/subscript writes. Later main commits refine rebinding and branch precision.
- Current evidence attributes helper lines4-5 to project_hint() whose value reaches _derive_uncached(); one CHORUS occurrence at line5 gates all four named generation approaches.
- The nine complete baseline violation occurrences are retained unchanged. The only added violation is the exact planted helper return text.
- The relevant alias/flow functions are compared from main through integration, prepin, pin update and tested composition. H1 changes only the authority digest and enables the integrated scanner to complete; it does not introduce alias tracking.
- Main already contains a positive B2 plain-alias tracing regression with a no-sink negative control, and the finished H1 scanner cohort has its actual result. This supports closure of this bounded plain-alias fixture, not all container-alias gaps.
- Copied aliases such as dict(contracts), contracts.copy(), or dictionary unpacking remain separately documented limitations. This report does not classify B1/B3 outcomes or claim those limitations fixed.

Keep the frozen fixture and D128 unchanged. Add a separately versioned current-composition expectation for B2: baseline9 plus exactly the planted helper occurrence, exact source line/text/span, all four gates, and a direct-versus-plain-alias or removed-sink control. Reuse the existing main positive test as supporting evidence.

Do not rewrite historical expected9 to10, remove alias tracking to retain the gap, infer broad alias soundness, or expand owner approval.

**F3d_module_helper_print source evidence**

- Native parent command discovery only admitted __init__.py/__main__.py package targets, skipping the ordinary source_attribution_preflight.py module named by native_shared_render.commands.
- Main commit b85ac0fb7843866aa767f50e3e2e889ac706f8ba explicitly implements issue5666 module.py command discovery and adds a positive F3d regression for the exact planted print.
- Integration merge b11931410305569aba30b0f593193ae894bd0dc7 keeps main discovery semantics; the relevant functions remain byte-identical through prepin5d63, pin66fec and the tested private composition.
- Current scan records native_shared_render.py:278 and native_source_attribution.py:59 as -m command evidence. The target is model_facing and runs as script only in native_agentic; other listed approaches remain run_shaping.
- The single planted print contains CHORUS twice, producing two duplicate occurrence objects at line174. Both gate only native_agentic. The nine baseline violation objects remain unchanged.
- H1 pin repair permits the complete integrated scan to reach these existing discovery rules; it does not introduce the F3d recognition behavior. A stale prepin full scan might refuse earlier, so no historical fullscan pass is inferred.
- This closes the direct module-print fixture, not the separate imported-helper-return gap F3e. Do not infer complete native-model coverage.

Preserve native_u3l_review_cases.json and D128 bytes as historical evidence. Add or adapt a separately versioned current-composition expectation for F3d using the existing main positive proof: baseline9 plus exactly two planted native-only violations, exact lines/snippet/duplicate count and retained source inventory.

Do not rewrite historical expected9 to11, label historical N1 never existed, weaken discovery to regain the old count, or reuse D128 approval for new instrument identities.

Keep the known-gap expectation disagreement separate from the authority-pin repair. Preserve the frozen U3-L fixture and D128 evidence. Subject to lead approval, version the current expectation separately around the unmutated baseline plus the exact newly detected planted occurrences and their actual gate membership, only after its own source-history classification and violation objects are reviewed. Do not silently relax counts or mark the currently failing CI identity cleared by judgement.

Comparison-helper control evidence: /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-h1-scanner-20261112/h1-comparison-self-check.json; SHA-256 3f89c77057d6f43876d7fbacf9dee3ae1224ed9cf139fac552422f2d2e6cc1cb.

**Composition source witnesses**

| Source tree | Observed HEAD | Tracked clean | Scope |
| --- | --- | --- | --- |
| /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-h1-scanner-20261112/h1-b/tree | 3a582243c4277934415bceb92cb888d617fd7a14 | True | Post-run observation when cohorts are complete; otherwise an interim snapshot. Creation manifest provides the initial witness. This is not continuous attestation. |
| /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-h1-scanner-20261112/h1-c/tree | 07d87f79522372205c475768516d48f1dab344cd | True | Post-run observation when cohorts are complete; otherwise an interim snapshot. Creation manifest provides the initial witness. This is not continuous attestation. |
| /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-h1-scanner-20261112/h1-d/tree | e1d23959737cdbab6a46373fcb5a2c7a16070c8c | True | Post-run observation when cohorts are complete; otherwise an interim snapshot. Creation manifest provides the initial witness. This is not continuous attestation. |
| /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-h1-scanner-20261112/h1-e/tree | 2beb2abc70dddca27a84ee667d5cd091b23cdb45 | True | Post-run observation when cohorts are complete; otherwise an interim snapshot. Creation manifest provides the initial witness. This is not continuous attestation. |

**Integration**

| Donor commit | Local matching commits | Evidence state |
| --- | --- | --- |
| ddcadcdc20ce40cdeb6eb92645c17883f2060be6 | [{"commit": "058de60779412150c529e41c86c5cfe9047014da", "subject": "Load the quiet-lock runner from a temporary layout so its tests collect anywhere (#5875)"}] | exact_cherry_pick_verified |
| ab07c81fedb6ca8a90c22d264556127b11e276a9 | [{"commit": "79089536b698dd2dd968233da4eadc8841f76b10", "subject": "Make three native test files independent of this machine's directory layout"}] | exact_cherry_pick_verified |
| 91fcdab3311c65ba8591836db75e241b78cf10ac | [{"commit": "6846d84042a84d5fe26513684430815c523e5b75", "subject": "fix(native): check observed frame models against declared alias roles"}] | exact_cherry_pick_verified |
| 37a4aa5d0ab07ed270ef6211f35e7a377e2472b6 | [{"commit": "1cd2264274898fc6dcbf1cb8a3e6c7a6a980eaa2", "subject": "test(native): assert direct capture trace and early pinned-review refusal"}] | exact_cherry_pick_verified |
| 789778427d029ccc2d66b1b926c8921ceef79556 | [] | not_yet_present |

Lead acceptance authorizes only the original observer repair and its two test commits, including public-completion verification in a protected-file scratch composition. The later launch-sequence and review-bundle lanes are not included or authorized by this report.

Helper 2 observer/test integration state: lead_accepted_integration_in_progress.

Lead acceptance evidence:

| Purpose | First line | Last line | Exact snippet SHA-256 | Recorded text |
| --- | --- | --- | --- | --- |
| Lead acceptance of the original observer and test lane only | 709 | 710 | c78f4a8932abfd3d2fead09091188e01182d9d8edbe5457e8e71bdd4dc138694 |   - **Helper 2, three handoffs, all accepted by the lead:**<br>    - `codex-h2-observer-alias-20261112.md`: the observer's model-label defect fixed by using the existing alias helper (`91fcdab33`), the two test assertions repaired (`37a4aa5d0`), the missing guard-command test added (`789778427`), on `codex/native-observer-alias-20261112`. The public completion test could not be proven there, because the protected files stay equal to main on a branch; helper 1 reruns it in its scratch composition.<br> |
| Dated lead entry and N1 ballot v12 context | 703 | 704 | 9001d90cf62f4eb0dbd23763cd52511c09ef08ff5473cff88166deeba575b60b | - **Eighth round, recorded 2026-11-12T18:48:30Z:**<br>  - **Amendment N1 is ready for the owner's ballot at draft v12:** commit `c289eed19e37e227e04dd5e0c4fc077da54184aa` on `claude/native-amendment-n1-v7-20261112` (pushed), file sha256 `de1f4a1386d2a5b05feba13f4bd6f7518c9768e73fb1f0e4d16c5a79a2f11c18`, 34 lettered items (a to ah). The ballot is `d4d-executions/plans/n1_v12_ballot_2026-11-12.md`.<br> |

**Retained comparison identities**

| Comparison | Exact branch head | Saved status | Current head | SHA-256 |
| --- | --- | --- | --- | --- |
| /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-h1-scanner-20261112/h1-final-comparison/comparison.json | 79089536b698dd2dd968233da4eadc8841f76b10 | complete_diagnostic_not_owner_approval | False | 25e4657372c0ca35fc80aff1f67f7769de01f00f4f9fd7bf89b600b5d102ada6 |

**Report helpers retained locally**

| Helper path | SHA-256 | Local Git status |
| --- | --- | --- |
| /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/scripts/adhoc/prepare_native_h1_helpers_20261112.py | 8e2719fa99c90a89057c91813c0ce8e307c8bb1229c6aa997324e4203689e84f |  |
| /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/scripts/adhoc/restore_native_h1_config_20261112.py | 5175b882762387f1923aee27da57707b1d4e94a4955d8e0ea61081fac5ffdc56 |  |
| /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/scripts/adhoc/report_native_h1_20261112.py | 29fcae3c36f5ce65df885909b168508984f677d045b91903aecbe22607e354bf | M scripts/adhoc/report_native_h1_20261112.py |
| /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/scripts/adhoc/native_h1_authority_audit_20261112.py | 6c6736db1aedcda20e882ce61a8a94f76b743b80f86b85a59aed96fd8d839360 |  |
| /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/scripts/adhoc/native_h1_scanner_comparison_20261112.py | f8d02429ae353b4613efafc8e973d93149bfa4351012316f8d0dabe647de8573 |  |
| /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/scripts/adhoc/h1_ambiguous_table_finding_20261112.py | 9b73c9d1b58f3fbec65cbaed9a78164a295c1808beef159dfe15fde485e60c7a | ?? scripts/adhoc/h1_ambiguous_table_finding_20261112.py |
| /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/scripts/adhoc/h1_retained_gap_finding_20261112.py | e249a75b52e2926a1fac3604ce435404a9da0cab1d98bf81114c86750a366ae6 | ?? scripts/adhoc/h1_retained_gap_finding_20261112.py |
| /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/scripts/adhoc/h1_retained_container_finding_20261112.py | 762405a1aa137025e0e7250255729701e49ec7da9e0a21656915bf4234122b88 | ?? scripts/adhoc/h1_retained_container_finding_20261112.py |

Private configuration restoration receipts: 4. Exact receipts and all commands, origins, cleanup evidence, output hashes and test identities are retained in the JSON. This report does not execute tests. At-sign characters are represented as [at]; referenced raw evidence retains its original bytes.

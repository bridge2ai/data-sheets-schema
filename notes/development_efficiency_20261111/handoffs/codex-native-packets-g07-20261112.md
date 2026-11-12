# Native protected packets and capture selection — 2026-11-12

Four protected postimages are prepared and independently reviewed in scratch: three equal D127; the API postimage needs a fresh exact-hash decision. Latest-capture enforcement is committed locally at 5d63d0a77dc43c064cfc2b376355f98009dd5b6e and all 21 new tests pass. G07 and native readiness remain blocked: scanner drift prevents a complete D128 comparison, and the public completion test exposes a pre-existing requested-versus-returned model-alias defect. Two pre-existing test-instrumentation failures remain. N1 ratification, protected-byte approval and actual CI are pending. Protected branch files remain main-equal; nothing was published.

D136 decides 1200 seconds and unchanged margin 90; N1 as a whole remains unratified.

Branch head: `5d63d0a77dc43c064cfc2b376355f98009dd5b6e`. Composition manifest: /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-main-integration-20261112/g07-c/composition.json

| Protected file | Proposed postimage SHA-256 | D127 SHA-256 | Equal | Unchanged branch SHA-256 |
| --- | --- | --- | --- | --- |
| src/data_sheets_schema/shared_generation.py | 2ec18e60316423035f88a2a30263c56385bfbbc587303e84e805a8349ab4f781 | 2ec18e60316423035f88a2a30263c56385bfbbc587303e84e805a8349ab4f781 | True | 94b3cf6845827c8fdf7bf05cc6251e2fb196ceb91ea8ce377f2c9e3b8be3773d |
| src/data_sheets_schema/api_runner.py | 830eec1e12e96f807fa76ea26e066a1923b60380013c424cfa99f0012af0a881 | 3e8b7e5d3cc13c5ebc508e33f865e9ac484056fde16126118719d740656a4fb7 | False | 23dcc828d171000173bd521edfbc55b38bfcf6c0adb41c6b962c10f381e911bb |
| src/download/prompts/canonical_hashes.yaml | 543e5cd6dc0da0f622ba2cd11a16a90732e9302a1ed0a4700efb61971299d252 | 543e5cd6dc0da0f622ba2cd11a16a90732e9302a1ed0a4700efb61971299d252 | True | 39b93c009457681a1d8d8b8afee5a869bbd6f5e70b6f4332522db5d7e22d0584 |
| tests/utils/run_spec_boundary_contracts.json | b1e0cbd14c533a51b88eacb84b974cb93963e18d8f1fb71ae4ed3228f784d1ce | b1e0cbd14c533a51b88eacb84b974cb93963e18d8f1fb71ae4ed3228f784d1ce | True | a7f96a253a37e994f0c62c7d9b2ab21b0a94d4f342975f84103cd274ef11af72 |

**Validation**

| Cohort | Source | Seconds | Exit | Counts | Disposition | Log |
| --- | --- | --- | --- | --- | --- | --- |
| g07-capture-canary | 7e4ec62c28226b595e91565f0f0bc3ce47b7bc0d | 5.892562334018294 | 0 | {"tests": 1, "failures": 0, "errors": 0, "skipped": 0, "passed": 1} | One current guard canary passed, verifying persisted selection pair, snapshot/readback, exclusion of another capture while the reservation word lock is held, and no generation reservation. | /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-main-integration-20261112/tests/g07-capture-canary/pytest.log |
| g07-capture-regressions | 7e4ec62c28226b595e91565f0f0bc3ce47b7bc0d | 287.5077316670213 | 1 | {"tests": 534, "failures": 2, "errors": 0, "skipped": 0, "passed": 532} | 532 passed, 2 failed. All 21 new latest-claim tests pass. Independent review confirms the two negatives are unchanged CI instrumentation defects; this bounded cohort introduced no new negative identities. No broad passing-suite claim. | /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-main-integration-20261112/tests/g07-capture-regressions/pytest.log |
| g07-ci-residual-canaries | 7e4ec62c28226b595e91565f0f0bc3ce47b7bc0d | 5.318952957983129 | 1 | {"tests": 3, "failures": 0, "errors": 1, "skipped": 0, "passed": 2} | The closed-registry and owner-delivery canaries pass locally; the native-authority scanner representative still errors on its source pin. Two passes and one setup error; no CI-green claim. | /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-main-integration-20261112/tests/g07-ci-residual-canaries/pytest.log |
| g07-ci-selectors | 7e4ec62c28226b595e91565f0f0bc3ce47b7bc0d | 67.82688045798568 | 0 | {"tests": 27, "failures": 0, "errors": 0, "skipped": 0, "passed": 27} | All 27 exact retained selector-shape CI failures pass locally with the four protected packets. This establishes local clearance of those nodes, not a GitHub CI result. | /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-main-integration-20261112/tests/g07-ci-selectors/pytest.log |
| g07-constructor-canary | ba279821f79fef1650b2ea8c972a8702323f6b17 | 2.781499749980867 | 0 | {"tests": 1, "failures": 0, "errors": 0, "skipped": 0, "passed": 1} | One genuine native construction/replay selection canary passed on the first successful composition. Synthetic software evidence only. | /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-main-integration-20261112/tests/g07-constructor-canary/pytest.log |
| g07-execution | ba279821f79fef1650b2ea8c972a8702323f6b17 | 112.57778591598617 | 0 | {"tests": 554, "failures": 0, "errors": 0, "skipped": 0, "passed": 554} | 554 passed on g07-b, ba279821f79fef1650b2ea8c972a8702323f6b17, before Part B. Every one of the original 62 native-constructor errors and 44 source/basetemp-isolation failures passes there. No production guard was weakened. | /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-main-integration-20261112/tests/g07-execution/pytest.log |
| g07-metadata | 7e4ec62c28226b595e91565f0f0bc3ce47b7bc0d | 18.615431874990463 | 0 | {"tests": 38, "failures": 0, "errors": 0, "skipped": 0, "passed": 38} | All 38 metadata tests pass in the isolated CPython 3.13 environment, including the 29 retained closed-registry failures and metadata assertion case. This is local evidence, not proof that the protected packets caused the improvement or that CI now passes. | /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-main-integration-20261112/tests/g07-metadata/pytest.log |
| g07-public-paths | 7e4ec62c28226b595e91565f0f0bc3ce47b7bc0d | 503.2018241669866 | 1 | {"tests": 61, "failures": 1, "errors": 0, "skipped": 0, "passed": 60} | 60 passed, 1 failed. The saved synthetic public lifetime reaches observation, then correctly declared assistant returned-model bytes are rejected by an unchanged requested-only comparison in native_shared_observations.Trace. This pre-existing observer integration defect is separate from Part B; successful public completion remains unproved. No CPU-monitoring diagnostic or real native execution was run. | /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-main-integration-20261112/tests/g07-public-paths/pytest.log |
| g07-scanner-cohort | 7e4ec62c28226b595e91565f0f0bc3ce47b7bc0d | 1244.3667910420336 | 1 | {"tests": 504, "failures": 44, "errors": 52, "skipped": 9, "passed": 399} | Scanner module: 285 passed, 44 failed, 52 errors; all 96 negatives explicitly identify the pre-existing authority source-pin drift. Schema neutrality: 7 passed; external onboarding: 26 passed; profiles: 81 passed, 9 skipped for fixture artifacts unavailable in this composition. No neutrality failure/error. All original missing-route signatures are gone, but the same 96 scanner test identities remain negative. | /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-main-integration-20261112/tests/g07-scanner-cohort/pytest.log |
| g07-scanner-current | 7e4ec62c28226b595e91565f0f0bc3ce47b7bc0d | 59.69284162501572 | 2 | {} | Exit 2: no complete scan arrays. Exact current authority-source pin refusal retained. Not a clean scan. | /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-main-integration-20261112/tests/g07-scanner-current/pytest.log |
| g07-shared-policy | ba279821f79fef1650b2ea8c972a8702323f6b17 | 941.0684013339924 | 0 | {"tests": 423, "failures": 0, "errors": 0, "skipped": 0, "passed": 423} | 423 passed. All 112 original shared-policy constructor errors now pass. This cohort used the composition before the separate capture-selection commit. | /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-main-integration-20261112/tests/g07-shared-policy/pytest.log |

Commands, environment, cleanup/origin checks and every negative traceback are in the JSON. At-sign characters are displayed as [at]; exact raw evidence remains in the referenced logs and XML.

**Scanner comparison**

The complete-array scanner invocation exited 2: separate native shared render route could not be derived because native_execution_authority_v2.py differs from the scanner's pinned source. Null means unavailable, not zero, clean, or approved.

Current exact matches, relocations, field changes, additions, removals and violation objects are **unavailable**. They are not zero.

Observed source: `src/data_sheets_schema/native_execution_authority_v2.py`.
Scanner expected: `bfdb5c86feb4c071ebf17e6ececa8fd60f1bc23bda98fefd42c0c211ecd7511a`.
Current bytes: `b2189db86428b5977bfcbaa72adc5f504f3449c31b583359555b074916a95558`.

The four packets do not change this authority module or scanner contract. No blind pin update, fallback or synthetic comparison was used.

The retained D128 comparison covers its original source pair only:

| Retained measure | Historical count |
| --- | --- |
| exact | 5229 |
| line_relocations | 57 |
| field_changes | 6 |
| additions | 1 |
| removals | 0 |
| identical_ordered_violations | 9 |
| added_test_dependencies | 2 |

D128 covers these exact retained objects and differences only. The current scanner and skill bytes differ. No current delta or violation object has been shown covered by D128.

Itemized historical ledger: `scratch-native-u1u3/u3h/itemized-scanner-comparison.json`; SHA-256 `98e6d082db4df2176a452ab60bc83280406333ba339a96e30ae501aeb6957ada`. The JSON preserves the complete source and array references.

Review the authority closure against the scanner contract, then obtain complete same-tool main and candidate scans. Itemize current-main to current-candidate, retained-main to current-main, and retained-candidate to current-candidate with duplicate occurrences, ordered indices, field differences and every violation object. Do not approve by aggregate counts alone.

**Capture selection**

implemented; bounded validation complete; public success blocked by a pre-existing observer defect.

Separate local commit: `5d63d0a77dc43c064cfc2b376355f98009dd5b6e`.

Before this change, read_capture_for_event could join an earlier successful slot after a later durable claim. The current-word and freshness checks did not require that slot to be the last claimed capture. Both launch reservation routes were inspected.

- Current guard preparation reconstructs the capture under the existing word lock and retains that lock through guard publication.
- Strict integer capture_index and capture_claim_count are recorded in current guard bytes and their saved snapshot.
- Both actual reservation routes recheck the pair against the durable claim journal under the existing word lock before margin validation and attempt.mkdir.
- The event is independently reconstructed and joined to its capture index; rehashed metadata is not authority.
- Historical exact v2 guard shape remains readable, while current admission requires the new checked selection.

No new lock order, journal event, capture charge or generation-attempt consumption was introduced. No additional owner design decision was needed within this assignment.

The canary passed. All 21 new latest-claim tests passed. The 13-module core regression cohort has 532 passes and two pre-existing assertion failures already present, with identical messages, in retained CI on native1a137. Independent review found no correctness blocker in Part B; the bounded core cohort introduced no new negative test identities. The public-path cohort has 60 passes and one failure: a pre-existing observer rejects the correctly declared returned-model alias. Public successful completion remains unproved.

Component tests deliberately isolate outer registration reconstruction and use scripted Python peers; they are not native-account or launch evidence. The new producer helper and actual reservation branches are exercised; a full prepare-subscription-guard-v2 CLI-body test is not yet included.

**Findings and remaining gates**

| ID | Count | Evidence | Disposition |
| --- | --- | --- | --- |
| G07-F1 | 1 | Current complete-array scanner exits 2 on the native authority source pin; this invocation did not produce complete D128 arrays. | Keep scanner comparison and approval pending. Review and update derivation separately, then repeat the itemized comparison. Do not treat this packet as scanner approval. |
| G07-F2 | 1 | API postimage SHA-256 830eec1e12e96f807fa76ea26e066a1923b60380013c424cfa99f0012af0a881 differs from D127 only by main's declared-type/enum multivalued handling. | Owner exact-hash review remains required. Four protected files remain untouched on the branch; scratch application is not approval. |
| G07-F3 | 1 | D136 settles 1200 seconds and unchanged 90-second margin. N1 draft v8 as a whole remains unratified. | Retain N1 ratification and complete final-source review, CI, registration and separately authorized native checks as later gates. No provider, model, native executable, push or GitHub action occurred. |
| G07-F4 | 2 | Unchanged test_native_subscription_capture.py assertions at lines 315 and 371 fail with the same messages as native1a137 CI. The direct-read tracer labels claims outer, not inner; a changed review document correctly refuses in validate_bundle before the later recheck hook. | Separate test repair: expect verified then outer-claims for the direct read while preserving the event-lookup four-step assertion. For review_document, assert the exact pinned-review refusal and earlier trace; retain recheck assertions for other mutations. No production guard should be weakened. |
| G07-F5 | 1 | The new producer helper and reservation paths are tested, but the complete prepare-subscription-guard-v2 CLI body has only parser coverage in the existing suite; historical CLI preparation tests exercise v1. | Add a focused current-v2 CLI routing/publication test in a later test-only follow-up. This bounded result does not claim a real CLI/account/native launch acceptance run. |
| G07-F6 | 1 | The public completion test fails on the first assistant tool-use frame. Runtime declares requested synthetic-native-model and returned synthetic-native-returned-model; transcript lines 2 and 3 use those exact respective labels. native_shared_observations.py:129-131 incorrectly compares the assistant label with runtime.model. Observer, alias helper, peer, public test and runtime_for are unchanged from native1a137 and pre-B5fa. Observer SHA-256 is 41459563575a0c9e0c396c488cb25afbd0f8421896b904ecfc290972ca1b3ae2. | Separate native-readiness blocker. Have Trace derive the closed alias pair through native_model_aliases.model_aliases(runtime) and use require_frame_models for the same frame types; preserve requested-model initialization. Review pure-graph closure impact and test declared returned assistant labels, wrong/missing labels, wrong requested-frame labels, and historical identical-label behavior. Rerun the single public completion case. Do not change the peer to hide the defect or allow either label everywhere. |

**Retained CI failure classes**

| ID | Count | Evidence | Disposition |
| --- | --- | --- | --- |
| selector_shape | 27 | All 27 exact retained failing nodes pass in g07-ci-selectors. The API packet makes shared selection unconditional while preserving native validation in the shared hook. | Locally resolved by the integrated selector shape; obtain a real CI rerun after authorized integration. |
| authority_source_pin | 44 | The complete scan exits 2, all 96 scanner-cohort negatives cite this pin, and the retained CI representative still errors. The same stale pin and authority bytes already coexist on native1a137. | Not resolved by the four packets. Review/update scanner derivation and produce new complete D128 comparison arrays. |
| closed_dependency_registry | 29 | The canary and complete 38-test metadata module pass locally; all 29 retained failed identities are included. | Locally green under isolated CPython 3.13; no causal credit assigned to protected packets and no assertion that the CI environment is repaired. Real CI verification remains. |
| import_origin | 37 | Retained failures consistently concern prepare_registration import origin. The controlled local runner verifies imports from the explicit tree, but this does not repair CI startup. | Separate assigned CI/environment work. Do not claim these 37 resolved from a packet or origin witness alone. |
| host_layout | 7 | Retained CI inventory has six external-schema-fixture failures and one snapshot-layout failure. Moving local basetemp outside source does clear the separate 44 G04 execution-isolation negatives. | Separate assigned host-layout work; no blanket CI clearance. |
| collection_layout | 2 | One retained collection error and one helper-layout error. The separately prepared collection fix was not merged into this candidate. | Separate collection/layout work. No full CI collection or full-suite green result claimed here. |
| other | 6 | Two capture-instrumentation assertions remain failed and are independently classified as pre-existing. The selected native construction/replay test, metadata readiness assertion and owner-delivery canary pass locally. The remaining native-scanner prefix-regex case was not separately rerun. | Retain the two test repairs and scanner regex follow-up; do not infer clearance for an untested node. |
| cancelled_shards | 2 | The retained CI run cancelled two shards at the 45-minute limit. | Separate shard-time work; cancelled shards are not passing evidence and are not part of the 152 unique failed/error IDs. |

**Exact test identity comparison**

{"path": "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/codex-g07-cohort-comparison-20261112.json", "sha256": "52447ec10ccd606af2b46b4431586d09cbaf074b0305e23ee146c3f310a56594", "pairs": [{"before": "execution-merge", "after": "g07-execution", "merge_cause_negatives": 62, "merge_cause_after_outcomes": {"passed": 62}, "old_signature_still_present": 0, "after_not_observed": 0}, {"before": "shared-policy-merge", "after": "g07-shared-policy", "merge_cause_negatives": 112, "merge_cause_after_outcomes": {"passed": 112}, "old_signature_still_present": 0, "after_not_observed": 0}, {"before": "scanner-merge", "after": "g07-scanner-cohort", "merge_cause_negatives": 96, "merge_cause_after_outcomes": {"failure": 44, "error": 52}, "old_signature_still_present": 0, "after_not_observed": 0}]}

**Private test configuration restoration**

[{"path": "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-main-integration-20261112/g07-b/config-restored.json", "sha256": "34bd2e5d75ed3de49f87271535c2606bf5b925c85a5200e0d012bdc8d31eb5a3", "receipt": {"backup": "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-main-integration-20261112/g07-b/tree/.git/config.bak-g07-20261112", "before_sha256": "8a96cf34356a4adffb3c4cf8f07358fcde3857c9a2ed57a1c15cb9822f329b76", "config": "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-main-integration-20261112/g07-b/tree/.git/config", "manifest": "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-main-integration-20261112/g07-b/composition.json", "manifest_sha256": "b4ea29d6b2839f11707d41573319d9ee1373580de9b3f357047dd1361ad949ff", "restored": true, "restored_sha256": "95a1f7d19be439847af9384dfe1a1f7678aa0902b1601b24c56cc60d783388b1", "scope": "private test-only Git configuration"}}, {"path": "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-main-integration-20261112/g07-c/config-restored.json", "sha256": "7ea9e301464027c578bae2b94423c1a2870dfe9d626f73f826b9d0bbacf7353a", "receipt": {"backup": "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-main-integration-20261112/g07-c/tree/.git/config.bak-g07-20261112", "before_sha256": "8a96cf34356a4adffb3c4cf8f07358fcde3857c9a2ed57a1c15cb9822f329b76", "config": "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-main-integration-20261112/g07-c/tree/.git/config", "manifest": "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-main-integration-20261112/g07-c/composition.json", "manifest_sha256": "a26c49992df1b6edf0fcc133510c9fdda0e40b5c4ddc828450b4d13da2121f48", "restored": true, "restored_sha256": "95a1f7d19be439847af9384dfe1a1f7678aa0902b1601b24c56cc60d783388b1", "scope": "private test-only Git configuration"}}]

**Independent review**

{"packets": "Independent read-only review found no packet derivation defect or report overclaim. The private commit changes exactly four protected files, three postimages equal D127, and the API postimage equals the retained U3-M proposal. Assigned branch protected bytes remain pinned-main bytes.", "capture_selection": "Independent read-only review found no correctness blocker in the stable Part B patch. It checked caller coverage, existing lock order through reservation, failed/interrupted claims, strict/rehashed metadata, historical readback, and unchanged charging. Tests were pending at review time."}

**Saved helper scripts**

[{"path": "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/scripts/adhoc/report_native_g07_20261112.py", "sha256": "d56e768cf3b8db96cf14dc7c58717c23f6b5c3dfd03a7b55ec8106a08f6cbe54", "status": "local report helper; not committed by this assignment"}, {"path": "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/scripts/adhoc/classify_g07_ci_scanner_20261112.py", "sha256": "85968e3740ae2db5cd3ce60472e89c4f1292644bbad0ebc75e36a33a0d716334", "status": "local report helper; not committed by this assignment"}, {"path": "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/scripts/adhoc/restore_g07_private_config_20261112.py", "sha256": "edc91fd2dbe4c9abdb60f4d195245aef815c13d6287129ee06398e06157b64f7", "status": "local report helper; not committed by this assignment"}, {"path": "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/scripts/adhoc/compare_g07_cohorts_20261112.py", "sha256": "fba1b997c680fe9d53cef94e4f0c2faad4517b83805c648bc617a17f2846520c", "status": "local report helper; not committed by this assignment"}, {"path": "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/scripts/adhoc/run_g07_ci_selectors_20261112.py", "sha256": "5ccf71f87b40464c131bf74c17b45bace25390cacc28216e08a001595d273b0c", "status": "local report helper; not committed by this assignment"}, {"path": "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/scripts/adhoc/classify_g07_scanner_cohort_20261112.py", "sha256": "b08abeb10a7e3473f294028736902cb0b5947dfd9c099a1049ad25224004af09", "status": "local report helper; not committed by this assignment"}]

**Reproduce the reports**

```sh
env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin HOME=/var/empty \
  /opt/homebrew/Caskroom/miniforge/base/bin/python3.13 -S -B \
  scripts/adhoc/report_native_g07_20261112.py \
  --composition /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-main-integration-20261112/g07-c/composition.json \
  --phase reported-with-unmet-gates --answer "<answer from JSON>"
```

Tables are generated from this JSON. No publication, provider/native call, protected branch edit or packet approval is implied.

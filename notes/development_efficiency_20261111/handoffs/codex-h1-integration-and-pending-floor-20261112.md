# Native integration and pending receipt floor — 2026-11-12

Reviewed integration: 3 of 3 groups verified on the candidate (8 raw-identical donor patches; 2 context-preserving composed text patches, without postimage-equality claims). Pending-floor defect: reproduced_and_repaired_404_focused_tests_pass_public_blocked_by_owned_HOME_issue. Registered-basis proposal: separate_local_proposal_217_focused_tests_pass_not_approved. The model-facing asset and protected hashes remain subject to owner approval; no launch or scientific acceptance is claimed.

Phase: Bounded assignment complete; public acceptance remains blocked; all attempted cohorts stopped and private configurations restored. Candidate: `2be7c3d769ee2d23cb117b9177aa45cef22f746d`.

**Reviewed integration**

| Group | All integrations verified | Raw-identical donor patches | Verified composed text patches | Local commits |
| --- | --- | --- | --- | --- |
| group1_already_integrated | True | 3 | 0 | ["6846d84042a84d5fe26513684430815c523e5b75", "1cd2264274898fc6dcbf1cb8a3e6c7a6a980eaa2", "df0122254cc7c9fe10470ee9eabc26c71a411a14"] |
| group2_launch_sequence | True | 4 | 1 | ["ac6e03ef411a378228d946f68715a10b55a59503", "c0692d5ef4755a28ad20b26247b2d07ca56338a4", "9cfa92927314606d246546938d7fe7210df2dbe3", "996ad5cc3eefbd28cfc760800d35584dd27a0352", "ae051c767cec9bad2b7a68d9eb89f05cf5ef2da4"] |
| group3_ci_collection | True | 1 | 1 | ["a162512f214c916262603f74d020ed38887d1fca", "7ecbc6d865288bec9ff1ac1f9f9cbaedf868a272"] |

Raw-identical cherry-picks and context-preserving composed text patches are distinct proofs. The latter never claims byte-identical postimages; its differing raw hashes remain recorded.

group1_already_integrated: Already integrated; prior observer/capture/guard evidence remains in the retained H1 report. The prior public completion failed and is not relabelled.

| Touched test file | Full-file pass observed | Pass with complete group lineage verified | Observed validation |
| --- | --- | --- | --- |
| tests/test_native_generation_guard_v2.py | False | False | not_observed |
| tests/test_native_shared_observations.py | False | False | not_observed |
| tests/test_native_subscription_capture.py | True | True | passed_with_verified_composition_and_donor_lineage |

group2_launch_sequence: Whole touched test files must be selected after the complete group. Canary-only witnesses, skips and missing files are not full-file passes.

| Touched test file | Full-file pass observed | Pass with complete group lineage verified | Observed validation |
| --- | --- | --- | --- |
| tests/test_native_launch_sequence.py | True | True | passed_with_verified_composition_and_donor_lineage |
| tests/test_native_review_bundle_v3.py | True | True | passed_with_verified_composition_and_donor_lineage |
| tests/test_native_subscription_capture.py | True | True | passed_with_verified_composition_and_donor_lineage |
| tests/test_native_u4b_readback.py | True | True | passed_with_verified_composition_and_donor_lineage |

Known composed-patch comparison: `cf53497ae2ebfba1da9c64995590115c48437f77` to `996ad5cc3eefbd28cfc760800d35584dd27a0352`; `verified_context_preserving_text_patch`.

Local parent: `9cfa92927314606d246546938d7fe7210df2dbe3`; donor parent: `e936cbb83d091cfab5c2e8b85bdd4c08a1b6b1e0`.

| Side | Raw patch SHA-256 | Text patch after limited normalization SHA-256 | Only metadata removed |
| --- | --- | --- | --- |
| donor | 7ca59fe942197ea0b82e01260b16ec1b3d8244589ff7f678c30cc6d737038766 | 50e418cb275531268113c0a64a0f294fc10deaf7ac9fe89e7edc2e44f720c8eb | {"index_hashes": ["index 000000000..6011ee3d4", "index 000000000..91a0ab918", "index 000000000..130f4e775", "index 000000000..ca7b63417", "index 000000000..03cc0883f", "index 000000000..28734f0b0", "index 141ed2b3f..0c483e047", "index 35caf2e82..5d2f4f96b", "index 83da9e341..3ca2e682f", "index 80ff6d8c3..615962fc1", "index 787d728ff..51935d5a7", "index 4c4c5dd68..a999443c7", "index 000000000..caf893cc1", "index e52aa8a72..91da6213f", "index d4be68fdb..765ac48e3", "index 000000000..4d139a6a8", "index 30b1eab27..ba08865be"], "hunk_coordinates": ["[at][at] -0,0 +1,102 [at][at]", "[at][at] -0,0 +1,100 [at][at]", "[at][at] -0,0 +1,21 [at][at]", "[at][at] -0,0 +1,23 [at][at]", "[at][at] -0,0 +1,23 [at][at]", "[at][at] -0,0 +1,14 [at][at]", "[at][at] -123,7 +123,7 [at][at]", "[at][at] -540,31 +540,36 [at][at]", "[at][at] -667,7 +672,7 [at][at]", "[at][at] -221,7 +221,7 [at][at]", "[at][at] -14,6 +14,10 [at][at]", "[at][at] -149,14 +153,24 [at][at]", "[at][at] -225,12 +239,14 [at][at]", "[at][at] -255,9 +271,26 [at][at]", "[at][at] -289,7 +322,10 [at][at]", "[at][at] -301,6 +337,22 [at][at]", "[at][at] -57,7 +57,7 [at][at]", "[at][at] -137,7 +137,7 [at][at]", "[at][at] -146,7 +146,8 [at][at]", "[at][at] -407,9 +407,10 [at][at]", "[at][at] -429,7 +430,7 [at][at]", "[at][at] -778,7 +779,9 [at][at]", "[at][at] -802,7 +805,11 [at][at]", "[at][at] -0,0 +1,334 [at][at]", "[at][at] -19,7 +19,7 [at][at]", "[at][at] -65,6 +65,7 [at][at]", "[at][at] -81,7 +82,8 [at][at]", "[at][at] -25,7 +25,7 [at][at]", "[at][at] -0,0 +1,26 [at][at]", "[at][at] -115,7 +115,7 [at][at]"]} |
| local | 409850d12dd5126bc62c94c2fb0b19dd6a79bf32d38568ae327f41a4a5748867 | 50e418cb275531268113c0a64a0f294fc10deaf7ac9fe89e7edc2e44f720c8eb | {"index_hashes": ["index 000000000..6011ee3d4", "index 000000000..91a0ab918", "index 000000000..130f4e775", "index 000000000..ca7b63417", "index 000000000..03cc0883f", "index 000000000..28734f0b0", "index 141ed2b3f..0c483e047", "index 35caf2e82..5d2f4f96b", "index 83da9e341..3ca2e682f", "index 80ff6d8c3..615962fc1", "index 787d728ff..51935d5a7", "index 4c4c5dd68..a999443c7", "index 000000000..caf893cc1", "index c747169ae..48b26c3eb", "index d4be68fdb..765ac48e3", "index 000000000..4d139a6a8", "index 30b1eab27..ba08865be"], "hunk_coordinates": ["[at][at] -0,0 +1,102 [at][at]", "[at][at] -0,0 +1,100 [at][at]", "[at][at] -0,0 +1,21 [at][at]", "[at][at] -0,0 +1,23 [at][at]", "[at][at] -0,0 +1,23 [at][at]", "[at][at] -0,0 +1,14 [at][at]", "[at][at] -123,7 +123,7 [at][at]", "[at][at] -540,31 +540,36 [at][at]", "[at][at] -667,7 +672,7 [at][at]", "[at][at] -221,7 +221,7 [at][at]", "[at][at] -14,6 +14,10 [at][at]", "[at][at] -149,14 +153,24 [at][at]", "[at][at] -225,12 +239,14 [at][at]", "[at][at] -255,9 +271,26 [at][at]", "[at][at] -289,7 +322,10 [at][at]", "[at][at] -301,6 +337,22 [at][at]", "[at][at] -57,7 +57,7 [at][at]", "[at][at] -137,7 +137,7 [at][at]", "[at][at] -146,7 +146,8 [at][at]", "[at][at] -407,9 +407,10 [at][at]", "[at][at] -429,7 +430,7 [at][at]", "[at][at] -778,7 +779,9 [at][at]", "[at][at] -802,7 +805,11 [at][at]", "[at][at] -0,0 +1,334 [at][at]", "[at][at] -19,7 +19,7 [at][at]", "[at][at] -65,6 +65,7 [at][at]", "[at][at] -81,7 +82,8 [at][at]", "[at][at] -25,7 +25,7 [at][at]", "[at][at] -0,0 +1,26 [at][at]", "[at][at] -115,7 +115,7 [at][at]"]} |

All postimage blobs equal: False.

Explicitly enumerated donor/local pair only. Strip index old/new hashes and numeric unified hunk coordinates; preserve file paths, modes, hunk section text, context, additions and removals byte-for-byte. Reject binary diffs. This does not assert byte-identical composed postimages.

group3_ci_collection: Collection covers all touched modules. The three public-lifecycle modules have collection and one light routing witness here; their two completions and seventeen failure cases are assigned separately by claude-lead-helper2-public-path-proof-20261112.md. Those cases remain acceptance gates and are not counted as passes here.

| Touched test file | Full-file pass observed | Pass with complete group lineage verified | Observed validation |
| --- | --- | --- | --- |
| tests/test_ci_timing_update.py | True | True | passed_with_verified_composition_and_donor_lineage |
| tests/test_native_execution_engine.py | True | True | passed_with_verified_composition_and_donor_lineage |
| tests/test_native_execution_round3_v2.py | True | True | passed_with_verified_composition_and_donor_lineage |
| tests/test_native_execution_round5_v2.py | True | True | passed_with_verified_composition_and_donor_lineage |
| tests/test_native_receipt_unopened.py | True | True | passed_with_verified_composition_and_donor_lineage |
| tests/test_native_shared_execution.py | False | False | collection_or_partial_only |
| tests/test_native_shared_execution_failure.py | False | False | collection_or_partial_only |
| tests/test_native_shared_execution_variant.py | False | False | collection_or_partial_only |
| tests/test_native_subscription_capture.py | True | True | passed_with_verified_composition_and_donor_lineage |

Known composed-patch comparison: `f25230fe1e56c5ad264cf77242f623be0ee6e4d1` to `a162512f214c916262603f74d020ed38887d1fca`; `verified_context_preserving_text_patch`.

Local parent: `ae051c767cec9bad2b7a68d9eb89f05cf5ef2da4`; donor parent: `ab07c81fedb6ca8a90c22d264556127b11e276a9`.

| Side | Raw patch SHA-256 | Text patch after limited normalization SHA-256 | Only metadata removed |
| --- | --- | --- | --- |
| donor | 301bee2bfa9dc99a2ee4c71c8975a82efa4eecf8ef2b8971ca39f0ea92a41578 | 68488ca6030432462f6a9992fac8cdae3548682f4b75089c292ad79261c252dc | {"index_hashes": ["index 000000000..4598d26c8", "index 000000000..71a749f03", "index 7498c8d27..fe22c418c", "index 2f3a53093..5614bd7de", "index d865b967a..08f3f5c7a", "index 5cbbbdd0c..656531046", "index aa9ad7833..5edaa03c4", "index 2fd97b483..1ac1aae72", "index 853a0fda5..ead57e2cf", "index e52aa8a72..e85ed0d91"], "hunk_coordinates": ["[at][at] -0,0 +1,28 [at][at]", "[at][at] -0,0 +1,410 [at][at]", "[at][at] -208,3 +208,12 [at][at]", "[at][at] -211,3 +211,12 [at][at]", "[at][at] -209,3 +209,12 [at][at]", "[at][at] -58,3 +58,12 [at][at]", "[at][at] -274,3 +274,12 [at][at]", "[at][at] -221,3 +221,12 [at][at]", "[at][at] -128,3 +128,12 [at][at]", "[at][at] -448,3 +448,12 [at][at]"]} |
| local | 591c1c946a101bd6cc37372601e4040713c1cf3e22f709df587179ba36021772 | 68488ca6030432462f6a9992fac8cdae3548682f4b75089c292ad79261c252dc | {"index_hashes": ["index 000000000..4598d26c8", "index 000000000..71a749f03", "index 7498c8d27..fe22c418c", "index 2f3a53093..5614bd7de", "index d865b967a..08f3f5c7a", "index 5cbbbdd0c..656531046", "index aa9ad7833..5edaa03c4", "index 2fd97b483..1ac1aae72", "index 853a0fda5..ead57e2cf", "index 48b26c3eb..773399a8e"], "hunk_coordinates": ["[at][at] -0,0 +1,28 [at][at]", "[at][at] -0,0 +1,410 [at][at]", "[at][at] -208,3 +208,12 [at][at]", "[at][at] -211,3 +211,12 [at][at]", "[at][at] -209,3 +209,12 [at][at]", "[at][at] -58,3 +58,12 [at][at]", "[at][at] -274,3 +274,12 [at][at]", "[at][at] -221,3 +221,12 [at][at]", "[at][at] -128,3 +128,12 [at][at]", "[at][at] -454,3 +454,12 [at][at]"]} |

All postimage blobs equal: False.

Explicitly enumerated donor/local pair only. Strip index old/new hashes and numeric unified hunk coordinates; preserve file paths, modes, hunk section text, context, additions and removals byte-for-byte. Reject binary diffs. This does not assert byte-identical composed postimages.

**New offline validation evidence**

| Cohort | State | Raw private composition SHA | Verified mapped branch source | Composition source mapping verified | JUnit outcomes | Origin, process exit and cleanup verified |
| --- | --- | --- | --- | --- | --- | --- |
| h1-floor-after | completed | 1826bc99e0171a7f9303fabcbb9af29f7837340c | e5fe279a3a685985c51589c867632424e8c110c4 | True | {"passed": 404} | True |
| h1-floor-after-canary | completed | 1826bc99e0171a7f9303fabcbb9af29f7837340c | e5fe279a3a685985c51589c867632424e8c110c4 | True | {"passed": 1} | True |
| h1-floor-basis | completed | 367a409112b1197ef4aa44279bf5201dd6b56b72 | 0059a8d84847263fced9ccb25eff902db0d3d4f4 | True | {"passed": 217} | True |
| h1-floor-basis-canary | completed | 367a409112b1197ef4aa44279bf5201dd6b56b72 | 0059a8d84847263fced9ccb25eff902db0d3d4f4 | True | {"passed": 1} | True |
| h1-floor-before | completed | a3f8622e1d92bf5d567d7134917edd6c3ee195c5 | 0fc003a86081891abbe8e130ac760c01da06423e | True | {"passed": 11, "failure": 3} | True |
| h1-floor-before-canary | completed | a3f8622e1d92bf5d567d7134917edd6c3ee195c5 | 0fc003a86081891abbe8e130ac760c01da06423e | True | {"failure": 1} | True |
| h1-floor-group2 | completed | f5a6f5ceaa574f76af503af75d617b18d47fa158 | ae051c767cec9bad2b7a68d9eb89f05cf5ef2da4 | True | {"passed": 196, "failure": 1} | True |
| h1-floor-group2-canary | completed | f5a6f5ceaa574f76af503af75d617b18d47fa158 | ae051c767cec9bad2b7a68d9eb89f05cf5ef2da4 | True | {"passed": 1} | True |
| h1-floor-group3 | completed | 544781df54ad15465f1cc213549dc440fe0f164c | 7ecbc6d865288bec9ff1ac1f9f9cbaedf868a272 | True | {"passed": 157} | True |
| h1-floor-group3-canary | completed | 544781df54ad15465f1cc213549dc440fe0f164c | 7ecbc6d865288bec9ff1ac1f9f9cbaedf868a272 | True | {"passed": 1} | True |
| h1-floor-group3-collection | completed | 544781df54ad15465f1cc213549dc440fe0f164c | 7ecbc6d865288bec9ff1ac1f9f9cbaedf868a272 | True | {} | True |
| h1-floor-public | completed | f0d418396a3b34359d76581f132b483848ef4602 | dd791a99c86e2693c04d133d09c77243ba0c30ba | True | {"failure": 1} | True |
| h1-floor-test-rulings | completed | 7f45a5974bc69cb6bc843a1f63c14b067d89016c | 2be7c3d769ee2d23cb117b9177aa45cef22f746d | True | {"passed": 93} | True |
| h1-floor-test-rulings-canary | completed | 7f45a5974bc69cb6bc843a1f63c14b067d89016c | 2be7c3d769ee2d23cb117b9177aa45cef22f746d | True | {"passed": 1} | True |

Counts are saved JUnit identities, not inferred from exit status. Skips, failed setup and incomplete runs remain separate.

Read-only, report-time verification of the complete committed Git tree against its branch-source parent, with exactly the four registered protected postimages; physical blobs and modes are checked exhaustively only below src/ and tests/, including ignored/untracked extras and without following symlinks. Physical Fairscape, other sparse/exported paths, dependencies and runtime environment bytes are outside this census. This is not a full physical-checkout claim, a before-run snapshot or owner acceptance.

| Private tree | Raw private SHA | Declared branch source | Source mapping evidence | Unavailable or mismatching evidence |
| --- | --- | --- | --- | --- |
| /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-h1-scanner-20261112/h1-floor-after/tree | 1826bc99e0171a7f9303fabcbb9af29f7837340c | e5fe279a3a685985c51589c867632424e8c110c4 | verified_committed_tree_and_physical_src_tests |  |
| /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-h1-scanner-20261112/h1-floor-basis/tree | 367a409112b1197ef4aa44279bf5201dd6b56b72 | 0059a8d84847263fced9ccb25eff902db0d3d4f4 | verified_committed_tree_and_physical_src_tests |  |
| /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-h1-scanner-20261112/h1-floor-before/tree | a3f8622e1d92bf5d567d7134917edd6c3ee195c5 | 0fc003a86081891abbe8e130ac760c01da06423e | verified_committed_tree_and_physical_src_tests |  |
| /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-h1-scanner-20261112/h1-floor-group2/tree | f5a6f5ceaa574f76af503af75d617b18d47fa158 | ae051c767cec9bad2b7a68d9eb89f05cf5ef2da4 | verified_committed_tree_and_physical_src_tests |  |
| /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-h1-scanner-20261112/h1-floor-group3/tree | 544781df54ad15465f1cc213549dc440fe0f164c | 7ecbc6d865288bec9ff1ac1f9f9cbaedf868a272 | verified_committed_tree_and_physical_src_tests |  |
| /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-h1-scanner-20261112/h1-floor-public/tree | f0d418396a3b34359d76581f132b483848ef4602 | dd791a99c86e2693c04d133d09c77243ba0c30ba | verified_committed_tree_and_physical_src_tests |  |
| /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-h1-scanner-20261112/h1-floor-test-rulings/tree | 7f45a5974bc69cb6bc843a1f63c14b067d89016c | 2be7c3d769ee2d23cb117b9177aa45cef22f746d | verified_committed_tree_and_physical_src_tests |  |

A mapped branch source is credited to a test only when its private HEAD, immediate parent, entire committed tree, four protected postimages and physical src/tests census all verify. Git ancestry errors are unavailable, not proof of non-ancestry. Observed passes remain visible even when lineage cannot be verified.

**Local integration findings**

| Finding | State | Observation |
| --- | --- | --- |
| H1I-F1 | observed_capture_cleanup_evidence_failure | The malformed-response capture test expected lifecycle.cleanup.group_absent, but saved cleanup is null and the assertion raises TypeError. The outer runner cleanup result is a separate observation. |

No later pass erases an earlier failed witness. Import collection and a selected light case do not establish full public completion.

H1I-F1 exact node: `tests/test_native_subscription_capture.py::test_failed_fake_capture_retains_claim_streams_and_cannot_retry[malformed-ValueError]`.

| Witness | Source | Outcome | Outer cleanup verified | Forced cleanup |
| --- | --- | --- | --- | --- |
| h1-floor-group2 | f5a6f5ceaa574f76af503af75d617b18d47fa158 | failure | True | False |
| h1-floor-group3 | 544781df54ad15465f1cc213549dc440fe0f164c | passed | True | False |

| Log line | Saved text | Line SHA-256 |
| --- | --- | --- |
| 8 | _ test_failed_fake_capture_retains_claim_streams_and_cannot_retry[malformed-ValueError] _ | 2723b06b3acd2d0ba7b78e008cfd71d40d2dd9536ac0a431884825512e63ae24 |
| 11 | tmp_path = PosixPath('/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-h1-scanner-20261112/tests/h1-floor-group2/cases/popen-gw0/test_failed_fake_capture_retai1') | 8bfe9db463cab18339f324d718d0c6ccc4645f8056a5765c6fdacad3ec511dec |
| 25 | >       assert result['lifecycle']['cleanup']['group_absent'] is True | d81d211afc42dcbc9e8e34479e19b70467d7a9721e8bfa97ca656cb3d76ca969 |
| 26 | E       TypeError: 'NoneType' object is not subscriptable | a28eb0fed6760e39adcee04358eeec4a8f27a737451b361221e992ce2deacd8f |
| 42 | FAILED tests/test_native_subscription_capture.py::test_failed_fake_capture_retains_claim_streams_and_cannot_retry[malformed-ValueError] | f9828469130eec2dc7db1855a2b424c3e026de692da63bf3d76498276630a8a0 |
| 43 | 1 failed, 196 passed, 14 warnings in 308.58s (0:05:08) | 6d89fe33d774adb67373525a6b81b1a593162be9edd603c0b6a20f24814730aa |

Capture artifact state: `physical_nonempty_json_observed`; path `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-h1-scanner-20261112/tests/h1-floor-group2/cases/popen-gw0/test_failed_fake_capture_retai1/one-capture/captures/3a4a1f1b42c5a797f329bec6fb115888b2f52852425d559960ba167beb33624d/capture-1/capture.json`; SHA-256 `01eb0507a93ddc6c78dd1ce47b7ef72b92435c29a14c9d15987882a2ddd0c842`.

Saved capture lifecycle: {"cleanup": null, "cleanup_error": {"message": "[Errno 1] Operation not permitted", "type": "PermissionError"}, "first_error": {"message": "Expecting property name enclosed in double quotes: line 1 column 2 (char 1)", "type": "JSONDecodeError"}, "returncode": 0, "spawn_count": 1}.

capture.json records its own lifecycle cleanup and cleanup_error. The runner outcome attests observed descendant cleanup only; a true outer cleanup_verified never fills or approves a missing capture lifecycle.cleanup object.

Observed failure only. No intermittent-behavior, race, sandbox-cause or donor-causation inference is made.

Preserve the original failure even if the ordinary Group 3 cohort later passes this node. Later outcomes do not erase or explain the earlier saved capture.

**Pending floor and asset proposal**

Issue 5939 is reproduced and repaired on the native route locally. Before the repair the native final CLI, its phase milestone, and the independent receipt gate fail on pending coverage despite passing structural floors. The repaired single-test canary and all 404 focused tests pass, including API controls, registered floors, structural refusals and policy/identity mutation tests. The one public pending attempt failed at the known synthetic-HOME refusal before final receipts, with a secondary publication failure and no saved final result. No public completion or launch acceptance is claimed.

The native-only final predicate revalidates the captured selection, both policy identities, completed final stage, history-hash shape and the recomputed coverage reading. It removes only the registered-coverage gate for the exact pending diagnostic declaration. The same predicate now serves the explicit native final CLI, independently reconstructed receipt gate and live recorder. Coverage remains state pending and passed false. Callers remain responsible for reconstructing observed history; this helper does not authenticate a supplied history hash in isolation. Shared/API strict predicates and registered arithmetic remain unchanged.

The reproduction used a real receipt assessment and native capture with supplied final-stage delivery; phase and independent-gate fixtures have explicit synthetic boundaries. The added public test chooses pending before any registration identity is minted and uses the existing actual synthetic public lifetime and saved-readback route. A synthetic Python test is not a native-binary/provider run or scientific acceptance.

Remaining blockers from the supplied section:

- Public next blocker reproduced: native shared observation failed: ValueError: synthetic HOME must contain no account or configuration artifacts. The trace shows the full-terms result followed by runtime revalidation refusal; the initial receipts command is observed without a result, final receipts/recorder/independent saved gates are not reached. A secondary publication ValueError leaves no final.json/published.json/actual-result.json. Helper-cache HOME and failed-readback fixes remain owned by helper 2 and have not been integrated without a reviewed handoff. Retain this failing test for the subsequent integration; do not weaken it or treat the missing final as success.
- Model-facing policy sentence contradicts D109 and is deliberately unchanged pending owner-approved wording and successor pins.
- The API packet postimage and margin decision remain unapproved; no packet is applied to the integration branch.
- Fresh final-source scanner comparison and acceptance/CI evidence are still needed after integration; prior source-pinned reports are not relabelled as current.

Implementation status supplied: `reproduced_and_repaired_404_focused_tests_pass_public_blocked_by_owned_HOME_issue`; detailed author evidence and independent checks are in the JSON.

Current policy asset is unchanged from the assigned starting candidate: True.

Exact current pending-floor sentence: A pending floor remains a diagnostic pilot and cannot satisfy strict completion.

Draft minimal wording, pending owner review: A pending floor remains a diagnostic pilot. Report its coverage reading without gating on it; strict completion still requires all structural receipt floors and every other acceptance check.

Complete pin/derived-identity inventory: Author-supplied inventory retained with progress evidence; completeness requires review.

| Pin or derived identity | Why it moves |
| --- | --- |
| native_shared_selection.RECEIPT_POLICY_SHA256 and ASSET_HASHES | Whole-file policy digest changes; descriptor receipt-policy and asset identities change. |
| canonical_hashes.yaml native_shared_receipt_policy_v1.md entry | Successor protected packet must replace whole SHA, Prompt-body SHA, byte count, provenance and reason; no native entry is currently applied on the main-equal branch. |
| Native receipt registration and selection S | runtime_policy_sha256, raw registration SHA and bytes, descriptor SHA, policy/asset pins and selection SHA change; create fresh registrations. |
| Render and execution authority | Render metadata, instruction bytes/SHA, preparation, package dependency/source identities, composition, permission expectation, execution binding and downstream evidence must be freshly derived. |
| Owner/scanner evidence | Successor packet diff/postimage and bundle identities plus scanner comparison change; preserve historical artifacts and prior approvals unchanged. |

| Unapproved wording variant | Whole-file SHA-256 | Prompt-body SHA-256 | Bytes |
| --- | --- | --- | --- |
| pending_only | a2f382bd7156ee514f192984b7d256d47695f50bb1e8a0b212188ab273aad70a | 583beddeac9aaab4548d1263d95a835d841855074d10ff9ef98e958eefcd2459 | 2446 |
| basis_only | e146dc9afa8c0cde2efbd2dedf5446b5b5002ba8f554382ab6fb8f5a8bb1a47f | 76ff95ff7aeae3577b80a6d8897270c6324daab4796e1ec4f061673f5e6cff03 | 2589 |
| combined | 94f0add2ac1785bdd881d4a6a6be9b098aa88c074e2db02687dbd854903ea7d2 | 4cacc66163031b410b7ad7e098dc406e807ad8b599580e3b24413d9f4ab6e98d | 2699 |

These digests describe the exact proposed bytes in the linked identity audit, not approved or applied assets. Different wording or line wrapping changes them.

Exact registered-basis sentence: The registered production floor is the exact integer fraction with_receipt / receiptable on the final record, using the unchanged receipt counters.

Draft registered-basis wording: The registered production floor uses the exact integer fraction named in its registration. With basis: receipted_part, it is with_receipt_at_receipt / receiptable_at_receipt on the sealed phase-1 record assessed with the completed effective receipt. Without a basis, it retains with_receipt / receiptable on the final record. With the snapshot basis, later record edits cannot change the denominator.

**Registered basis proposal**

Recommend an explicit optional registered basis: receipted_part, rather than silently changing the meaning of existing registrations. The implementation is isolated on codex/native-floor-basis-d37-20261112, not merged into the main-targeted integration branch and not approved for use. Its deletion-trap canary and all 217 focused native/API compatibility tests pass in the private packet composition, including real completion additions, fixed snapshot denominator, pending diagnostics and identity refusals.

The proposal extends the native closed registration parser and native floor calculation only. With basis present, exact integer arithmetic uses with_receipt_at_receipt / receiptable_at_receipt while retaining final counters for context. Missing snapshot counters do not fall back to final coverage; zero remains unmeasurable and not passed. Without basis, registered calculations and result shape remain unchanged. Pending registrations remain unchanged; valid snapshot counters can be reported diagnostically without a basis or pass claim.

The API evaluator remains untouched and is the test oracle. No historical raw registration, record or captured policy is rewritten. Old evidence must retain its old software and policy identities; accepting the proposal still requires a deliberate successor registration/builder choice and policy wording/pin update. The model-facing asset is unchanged even on this proposal branch.

Remaining blockers from the supplied section:

- Owner choice of production basis and fraction
- Policy asset wording and successor packet approval
- No public completion campaign was run on the proposal branch; future accepted source requires its own registration/authority/scanner/CI evidence

Separate local proposal branch: `codex/native-floor-basis-d37-20261112`; state `local_proposal_branch_observed`.

The registered production coverage basis remains an owner decision. No proposal is promoted into the integration branch by this report.

**F5 and F6 rulings**

F5 has positive witnesses for both materialized complete argv alternatives plus retained unresolved-alternative and ambiguous -m refusals. F3d and B2 each have their own test-only commit with versioned current expectations. The alias canary and all 93 selected scanner tests pass in the final candidate's private packet composition; both complete touched modules and the existing main precision witness were executed.

The frozen fixture and D128 approval remain byte-identical. F3d requires the complete nine baseline objects plus exactly two saved native-only PRINT violations; B2 requires the baseline nine plus the exact all-arm HINT object, including model_text_function. Ordered complete-object checks supplement existing planted snippet, line, category and input-inventory assertions. Historical known-gap metadata remains separate. There are no xfails or removed fixtures. H1-F2's nine portability negatives remain environment-scoped under the lead ruling; those fixtures are unchanged.

Remaining blockers from the supplied section:

- These tests do not extend owner D128 approval or replace a fresh final-source same-tool comparison and CI acceptance. Historical source-pinned arrays remain historical.

| Finding | Authorized test changes |
| --- | --- |
| F5 | ["Materialize both second_command and third_command package entrypoints for both old alias cases.", "Assert both complete alternatives are discovered with native_agentic model-facing execution provenance.", "Keep an unresolved argv alternative negative and a conflicting -m module-operand negative.", "Preserve existing main precision cases; one tests-only commit."] |
| F6_F3d | ["Keep historical fixture bytes and D128 baseline; version the current expectation separately.", "Require the complete nine baseline violation objects plus exactly two planted PRINT hits at source_attribution_preflight.py, gated only for native_agentic.", "Keep exact snippet, context, line, category, role and extra-object comparisons; one tests-only commit."] |
| F6_B2 | ["Keep historical known-gap evidence; version the current expectation separately.", "Require the nine baseline objects plus exactly one planted HINT hit at project_hints.py gated for api, deterministic, github_assistant and native_agentic.", "Preserve copied-alias refusals and all input inventory checks; one separate tests-only commit."] |

**Protected files and remaining limits**

| Protected path | Candidate SHA-256 | Committed and working bytes equal main |
| --- | --- | --- |
| src/data_sheets_schema/shared_generation.py | 94b3cf6845827c8fdf7bf05cc6251e2fb196ceb91ea8ce377f2c9e3b8be3773d | True |
| src/data_sheets_schema/api_runner.py | 23dcc828d171000173bd521edfbc55b38bfcf6c0adb41c6b962c10f381e911bb | True |
| src/download/prompts/canonical_hashes.yaml | 39b93c009457681a1d8d8b8afee5a869bbd6f5e70b6f4332522db5d7e22d0584 | True |
| tests/utils/run_spec_boundary_contracts.json | a7f96a253a37e994f0c62c7d9b2ab21b0a94d4f342975f84103cd274ef11af72 | True |

- H1-F2 nine setup/layout negatives remain environment-scope under the lead ruling; no fixture change is authorized for them.
- The prior public completion failed on nonempty synthetic HOME. Cache isolation and failed readback belong to another assigned lane; this report does not clear that gate.
- The pending-floor repair must retain structural gates, registered-floor gating and API behavior; missing tests do not prove these obligations.
- The policy sentence and its canonical pin are owner-review proposals only; the API postimage and margin decisions remain pending unless separately supplied owner evidence says otherwise.
- A fresh same-tool D128-form comparison is required for the final integrated source and its successor protected-packet composition: complete source inventory, ordered complete arrays, exact differences and retained approval coverage. Prior source-pinned arrays are historical evidence, not final-source validation.
- Changed scanner tool/source identities and new or changed complete findings require owner review; preserving old fixture bytes or passing new expectations does not extend D128 approval.
- Final acceptance and CI on the final candidate remain separate obligations. Focused passes, a public synthetic attempt, a proposal branch or scanner comparisons do not establish final CI or native-launch acceptance.
- Read-only, report-time verification of the complete committed Git tree against its branch-source parent, with exactly the four registered protected postimages; physical blobs and modes are checked exhaustively only below src/ and tests/, including ignored/untracked extras and without following symlinks. Physical Fairscape, other sparse/exported paths, dependencies and runtime environment bytes are outside this census. This is not a full physical-checkout claim, a before-run snapshot or owner acceptance.
- N1, the registered coverage basis and a native launch require the appropriate owner decisions. No provider or native executable has been run by this generator.

Prior H1 evidence: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/codex-h1-scanner-pin-20261112.json`; SHA-256 `0f0d82d058384d58b3da7e5ac3b986154b7ac2e85ae19a15eb527cd023816c1e`.

This generator imports only retained reporting utilities and the Python standard library. It does not run tests, scan application source, edit source or publish anything.

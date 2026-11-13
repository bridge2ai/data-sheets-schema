# Owner review: four protected native packets — 2026-11-12

| File | Proposed SHA-256 |
| --- | --- |
| src/data_sheets_schema/shared_generation.py | 2ec18e60316423035f88a2a30263c56385bfbbc587303e84e805a8349ab4f781 |
| src/data_sheets_schema/api_runner.py | 830eec1e12e96f807fa76ea26e066a1923b60380013c424cfa99f0012af0a881 |
| src/download/prompts/canonical_hashes.yaml | 543e5cd6dc0da0f622ba2cd11a16a90732e9302a1ed0a4700efb61971299d252 |
| tests/utils/run_spec_boundary_contracts.json | b1e0cbd14c533a51b88eacb84b974cb93963e18d8f1fb71ae4ed3228f784d1ce |

These are proposed scratch bytes, not installed branch bytes. Three postimages match D127 exactly. The API postimage differs and needs a fresh exact-hash decision. This document requests no launch, merge or spend.

Four protected postimages are prepared and independently reviewed in scratch: three equal D127; the API postimage needs a fresh exact-hash decision. Latest-capture enforcement is committed locally at 5d63d0a77dc43c064cfc2b376355f98009dd5b6e and all 21 new tests pass. G07 and native readiness remain blocked: scanner drift prevents a complete D128 comparison, and the public completion test exposes a pre-existing requested-versus-returned model-alias defect. Two pre-existing test-instrumentation failures remain. N1 ratification, protected-byte approval and actual CI are pending. Protected branch files remain main-equal; nothing was published.

**Comparison with D127**

| File | D127 approved SHA-256 | Equal | Main-relative patch |
| --- | --- | --- | --- |
| src/data_sheets_schema/shared_generation.py | 2ec18e60316423035f88a2a30263c56385bfbbc587303e84e805a8349ab4f781 | True | /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-main-integration-20261112/g07-c/packets/shared_generation.patch |
| src/data_sheets_schema/api_runner.py | 3e8b7e5d3cc13c5ebc508e33f865e9ac484056fde16126118719d740656a4fb7 | False | /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-main-integration-20261112/g07-c/packets/api_runner_companion.patch |
| src/download/prompts/canonical_hashes.yaml | 543e5cd6dc0da0f622ba2cd11a16a90732e9302a1ed0a4700efb61971299d252 | True | /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-main-integration-20261112/g07-c/packets/canonical_hashes.patch |
| tests/utils/run_spec_boundary_contracts.json | b1e0cbd14c533a51b88eacb84b974cb93963e18d8f1fb71ae4ed3228f784d1ce | True | /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-main-integration-20261112/g07-c/packets/run_spec_boundary_contracts.patch |

The current main protected blobs equal the earlier main 2cfc4666. The API postimage preserves main's newer datatype handling: multivalued slots whose range is a declared type or enum are included, rather than only slots whose range is literally string. This is the entire difference from the D127-approved API postimage.

The display spells diff hunk markers as [at] to satisfy the report format. Use the linked raw patch for machine replay.

```diff
--- a/src/data_sheets_schema/api_runner.py
+++ b/src/data_sheets_schema/api_runner.py
[at][at] -5350,9 +5350,10 [at][at]
 
 
 def _multivalued_of(view):
+    scalar_ranges = set(view.all_types()) | set(view.all_enums())
     for cls in view.all_classes():
         for slot in view.class_induced_slots(cls):
-            if slot.multivalued and str(slot.range) == 'string':
+            if slot.multivalued and str(slot.range) in scalar_ranges:
                 yield str(slot.name)
```

Relative to current main, the native API patch restores the reviewed native RunSpec fields, renderer/native admission, selection and replay binding, metadata/toolchain handling, assembly digest, native instruction route and API execution refusal. Shared selection remains unconditional and delegates the native validation to the shared-generation hook. The complete patch is linked above; its SHA-256 is `b1931723bdb6866d3a794618c2b1e6e813bcadcf505422eb1007a71787710838`.

The shared-generation packet adds native validation to selection. The canonical packet adds the two native prompt pins at repository-relative location dot, preserving existing entries. The sidecar updates exact function/source pins while preserving the 21 D76 contracts and their approval semantics.

**Current review gates**

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

Approval must name the exact postimage hashes above. Equal historical bytes retain their identity; this report does not extend D128 to any new scanner output or waive complete final-source validation.

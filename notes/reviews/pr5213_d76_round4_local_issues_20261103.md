# Round-four local review findings for PR 5213

These are issue drafts for the lead to publish after the offline restriction is
lifted. No GitHub issue, comment or review has been sent. The existing production
findings remain Issues 13–19 in the lead's round-three re-check issue packet.
Each item below records a separate finding from review of the round-four changes.

| ID | Finding and impact | Disposition |
| --- | --- | --- |
| R4-I01 | The new boundary inventory missed constructors and annotations using a RunSpec subclass or assignment alias, allowing a new public consumer to escape discovery. | Fixed in `884c06bc83843d6575236a1540dc5c53b2958dd2`; its failing-before control subsequently passed. |
| R4-I02 | Flattening function-local imports into module bindings let an unrelated local import hide a genuine public RunSpec alias annotation. | Fixed in `884c06bc83843d6575236a1540dc5c53b2958dd2`; its separate failing-before control subsequently passed. |
| R4-I03 | Public functions/properties declared in `match` arms were absent from the new inventory. | Fixed in `884c06bc83843d6575236a1540dc5c53b2958dd2`; its separate failing-before control subsequently passed. |
| R4-I04 | The recorder command's docstring still claimed that absolute input paths alone establish consumption after the byte-evidence repair. | Corrected in `26f70dab60f053f10711ad4af9efec7f1ba00ad2`, alongside the reviewed recorder repair. |
| R4-I05 | The timing extension checked full collection but omitted its path, digests and expected occurrence multiset from generated evidence, preventing independent replay of its completeness claim. | Collection proof and input-manifest identity are persisted; refresh/planner contracts pass. |
| R4-I06 | The timing extension mixed combined current file weights/source hashes with old round-three counts and artifact metadata under one measurement object. | Replaced with an explicit composite projection and immutable, hash-linked predecessor; refresh/planner contracts pass. |
| R4-I07 | A second timing refresh would assign all retained measurements the old global commit, discarding their existing per-file source revisions. | Preserve and verify the exact per-file commit/digest map, updating only newly measured files; round-trip contracts pass. |
| R4-I08 | The timing extension inherited the predecessor's installation-request flag and omitted the new installation proof, so dry-run evidence could misstate its side effect. | Current request and exclusive verified installation proof are recorded; round-trip contracts pass. |
| R4-I09 | The inventory keyed reasons/calls by qualified name, so an untyped conditional definition could erase the classification of another RunSpec-annotated arm. | Failing-before witness repaired in `3ed05189da0f64af3768c826c0f5c23c385744a6`; its focused control passes. |
| R4-I10 | Splitting annotation names lost the qualification of a known module-qualified RunSpec subclass, so a public annotated consumer could be missed. | Initial control passes after `3ed05189da0f64af3768c826c0f5c23c385744a6`; five further quoted-type controls preserve the failing-before proof for the recursive repair in `04b1e26b5f6c5230825b8116449813383ecdb072`. |
| R4-I11 | The generic SG2 dependency filter dropped all paths inside the repository, including its active local virtual environment's dependencies. A `-S` child could then fail to import pytest. | Fixed in `3ed05189da0f64af3768c826c0f5c23c385744a6`; all18 utility controls and one complete ordinary non-Git SG2 diagnostic pass. Final-head portability remains separately required. |
| R4-I12 | The proposed `latch_journal.owned_artifacts` caller contract omitted the read-only legacy verifier's validated `SimpleNamespace` projection and incorrectly implied that every call followed a RunSpec D76 entry. | Corrected before source application, preserving execution/startup ordering and the protected combined refusal. |
| R4-I13 | Recursive parsing of quoted annotation text treated ordinary `Literal` values and `Annotated` labels as type expressions. Valid unrelated annotations could therefore stop the complete inventory with a syntax error. | Before3 gives1P/2 intended failures. Repair `ffad7148affb097898f2d34bc96f254c502d5cc8` skips resolved non-type metadata while retaining quoted type arguments. |
| R4-I14 | The docstring applicator's dry-run preview added indentation to blank docstring lines, creating trailing whitespace. | Corrected before the single-file application; original preview retained. Applied source passes whitespace checks. |
| R4-I15 | The proposed evidence-ledger helper joined JUnit identities only for nonpassing cases. An all-passing XML file with wrong or duplicated node identities but the same counts could be credited against different selected tests. | Both controls fail before `d40f0c56352a360ecee036207b16af660a57913b` and pass after its complete XML identity join. Legitimate extra error rows remain separate observations. |
| R4-I16 | Appending inventory contracts to Click callback docstrings would expose internal preconditions in ordinary command help. | An escaped formfeed preserves visible help; actual installed Click full/short help comparisons pass for all ten affected callbacks before application. |
| R4-I17 | The proposed evidence ledger trusted the phase/outcome pass claim without also rejecting raw JUnit failures or errors, so contradictory evidence could satisfy `require_pass`. | The explicit control fails at `d40f0c56352a360ecee036207b16af660a57913b`; independently reviewed repair `c5b797bc1f8a5b05f87a7a5ad033864d49cb6eea` also requires zero raw failures/errors. |
| R4-I18 | The copied reviewer helpers lived under `scripts/adhoc/` without a test path component. Their real-looking `RunSpec`/`api.execute` witness code was correctly discovered as two new generation controllers, adding ungated continuations and promoting the complete CLI import closure. | Final81d specificity exposes354P/3F. Move the byte-exact witness/helper payload beneath a literal `tests/` component within its existing review bundle and update only provenance/target paths. Preserve the scanner, original357 tests and all witness assertions/bytes. Recheck the exact three failures and the full suite before further validation. |

The initial missing-chunk fixture failure is a test setup correction, retained in
the evidence: explicitly passing an absent file triggers Click validation before
the recorder. Its corrected omitted-option/discovery witness is committed at
`08fb188ba26661c4c9be60213d0d5a03595c70e2` without changing acceptance assertions.
On unchanged integration production it reaches the intended false-verification
failure; the original fixture error is not counted as defect proof.

The human approved both narrow scope exceptions on 2026-11-03: protected-helper
preconditions may be documented beside the inventory with the protected source
unchanged, and the 83 scanner-extension-specific assertions may be retired.
The three retired modules remain recoverable in the preceding commits; this
does not authorize weakening any remaining guard or assertion.

Validation updates: I01–I03 were reproduced on the tests-only baseline and their
controls passed after repair. I05–I08 passed the refresh/planner contract suites
(18 refresh cases and 31 planner cases). I09 and the first I10 control failed
at `55603b60a4284dfbb6c641acad370b374a086165` and passed at
`020fdc73dbf1469eef12c1a859b56a50f4e6a194`; two additional I10 quoted container
annotation controls failed at that latter head before their further repair.
I11 failed before its dependency-path repair and all 18 generic utility cases
then passed at `020fdc73dbf1469eef12c1a859b56a50f4e6a194`. Final-head acceptance
and the real SG2 portability cases remain separately required.

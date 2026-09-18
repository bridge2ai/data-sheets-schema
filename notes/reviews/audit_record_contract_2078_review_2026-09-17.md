# Audit record namespace review, 2026-09-17

[Issue #2078](https://github.com/bridge2ai/data-sheets-schema/issues/2078) arose when the v10x audit used `record: original_full` and failed its first evidence check. The [stopped outcome](../native_canary_v10x_outcome_2026-09-17.md) and all measured files remain unchanged.

## Change and scope

Opt-in renderer 14 gives both generation arms the same explicit audit contract. A finding's `record` is `full`, `core` or `both`; evidence `artifact` names identify the supplied original/final state. The contract restricts core findings to phases actually supplied that core, and tells the API audit to use `full`. Audit and final-report source reviews retain their distinct original/final identities.

A complete generic example demonstrates a supported recommendation to revise an unsupported completion claim. Its minimal one-field YAML is explicitly an evidence-contract fixture, not a schema-valid D4D. The example's original-byte digest, source quotation, finding evidence, review path and complete scalar review are checked together. It does not infer that a planned deployment never occurred, and it instructs generators to use their actual inputs rather than copy the example.

The change leaves the validator, evidence protocol 3, terminal stop rules, shared playbook and historical contracts unchanged. RunSpec and the registration parser accept renderer 14. Defaults remain native 7, API 8 and registration 9. A future registration must select the new renderer explicitly.

## Verification

- 19 focused tests pass. They extract the example from the actual native instruction and final API audit request block, exercise API extraction and the real native evidence CLI/check_files, and reject mixed record/artifact names, a stale digest, false quotation, unlinked revision and unavailable artifact.
- 373 tests pass in total, including the 19 new tests and related rendering, evidence, source-review, provenance, playbook, registration and phase-flow checks. A separate independent reviewer ran 59 focused tests successfully.
- An in-memory mutation replaces the example's finding `record: full` with the failed `record: original_full`. Both actual-rendered-example tests fail at admission, as expected. No source or measured file was changed by this probe.
- Before/after comparison of 757 offline artifacts across renderers 1–13 is byte-identical: 416 rendered instructions, phase text/contracts, assembly identities, representative phase requests and initial requests. The historical-version variants are replays of recorded v10x specifications, not claims about older run conditions. All 32 frozen v10x instructions and 16 initial API requests also reproduce exactly.
- Independent registration probes exercise parser → spec_for → render → recorded input identity → replay for both arms. Renderer 14 carries the new contract and retains the native Phase 1 correction/terminal evidence distinction. Changing only the new contract changes assembly 14 while versions 1–13 stay unchanged.

Independent adversarial and registration reviews found no blocking defect in this patch. No additional review issue was necessary. The assembly-14 SHA256 is `d5f55d9ff58bbcbf94e70a4528e13bd0b2815a9a87e1d8fd0e6ab7a912bdf924`.

## Retry boundary

This fixes the advertised audit format; it does not establish scientific acceptance or repair the stopped audit. No provider request or paid retry was made for this change. [Issue #2079](https://github.com/bridge2ai/data-sheets-schema/issues/2079) remains the separate semantic prerequisite before a fresh registered canary. Any further attempt must use a new condition and preserved inputs, with the reviewed contract and applicable launch checks pinned. v10x cannot be resumed.

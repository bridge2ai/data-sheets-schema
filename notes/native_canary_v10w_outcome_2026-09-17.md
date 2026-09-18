# v10w CHORUS native retry outcome, 2026-09-17

The authorized retry ran through CBORG on `claude-opus-5` and is **operator-stopped and incomplete**. No full/core pair is accepted. The operator applied the terminal evidence/source-check stop rule too broadly to a Phase 1 receipt correction. This attempt does not establish a source-review failure or a violation of the pre-Phase-2 receipt gate.

## Changes completed before the retry

[PR #2063](https://github.com/bridge2ai/data-sheets-schema/pull/2063) fixed #2061/#2062: registered file targets are checked before Read/Write execution, and callback matching shares the classification deadline. The merged controls passed their tests, pinned-runtime probes and CI. The review records 333 local tests passing, 19 skipped, and zero-provider synthetic probes with 39 cases without project settings and 41 with broad settings, plus the timeout case. See the [controls review](reviews/native_file_policy_2061_review_2026-09-17.md) for scope and limits.

[PR #2064](https://github.com/bridge2ai/data-sheets-schema/pull/2064) registered v10w. The original “resolve and retry” instruction was bound to one CHORUS native job after review and [successful CI on the exact merged launch commit](https://github.com/bridge2ai/data-sheets-schema/actions/runs/35290235245). The condition retained the previous source and scientific-instrument hashes.

[PR #2066](https://github.com/bridge2ai/data-sheets-schema/pull/2066) separately fixed #2065 by retaining safe local file-policy reasons in terminal diagnostics. It passed 57 local tests, regression checks against the old implementation, review and [merged-head CI](https://github.com/bridge2ai/data-sheets-schema/actions/runs/35290986401). It did not change the frozen v10w execution. All three implementation/registration branches were deleted after merging.

## Observed attempt

Launch commit: `f859e31df83b9508642cfe3f2fd735e52538306c`.

Registration SHA256: `1c5723f07e64764bc08810186a2b1e53e7e1c5f759510802041bac5b8ba7d2c4`.

Overlay SHA256: `221d065e2a4f8c1ce1ddea27d9ddc33bd9703b8ac8b5f78df3d050b01ca20d79`.

The attempt started at 2026-09-18 00:23:03 UTC and finished at 00:52:22 UTC (September 17 in America/Los_Angeles). It admitted 91 model requests, all settled, with zero unfinished handlers at evidence freeze and no unresolved charge. Detailed accounting remains in the private sequence ledger.

The tool history shows all eight registered source chunks opened in order, with each receipt entry successfully written before the next chunk was opened. The terminal control audit reconciled 123 decisions: 84 Bash calls and 39 file calls, with no reported control problems. Four forbidden, unprescribed Bash attempts were denied; none was classified as a disqualifying denial. No file call was denied. These observations support the file-control repair, not scientific acceptance.

The full D4D passed schema validation (transcript line 437) and term validation (line 442). The first strict receipt check (line 454) failed on 21 `slot_not_in_record` paths. It reported eight of eight chunks reviewed and 78 of 78 snippets verified. Its six token-overlap diagnostics and incomplete slot coverage were informational, not additional strict-failure findings or proof of unsupported claims.

The model then rewrote the receipt (lines 457/459) and reran the same check. The result at line 462 exited successfully, reporting eight of eight chunks, 78 of 80 snippets verified, two unattesting entries below the floors, one with no value-token overlap, and 58 of 73 slots with receipts, with six exempt. A successful exit does not establish that each snippet supports its assigned claim.

The rewrite changed quotations as well as slot paths: nine snippet occurrences were removed and eleven added. It was not only a path remap. The two unattesting additions were short labels; none of these receipt-content changes has been accepted as semantically supporting its assigned value.

Core derivation had not started. No frozen original pair, Phase 3 audit, reconciliation report or live provenance record was produced. Physical traversal of both output directories, including hidden and ignored files, found only the full record and coverage receipt.

## Correction to the operator stop

The operator set the ledger stop after observing the first failed receipt check. The original reason is retained unchanged in the ledger, controller receipt and evidence archive. It must be read with this correction: treating that Phase 1 failure as terminal was too broad.

The playbook requires a passing receipt gate **before core derivation**. The [earlier #2011 ruling](https://github.com/bridge2ai/data-sheets-schema/issues/2011#issuecomment-5710304055) explicitly distinguishes correction inside Phase 1 from crossing that gate. The generator had corrected and rechecked the receipt without starting Phase 2. No failed Phase 3/4 evidence or source-review check was observed.

Renderer 12's native evidence section says “Stop on any failed check” without naming the commands in that sentence. [Issue #2067](https://github.com/bridge2ai/data-sheets-schema/issues/2067) records the need to make the phase scope explicit and align operator guidance with the actual receipt floors. That ambiguity does not justify recording this interrupted attempt as a demonstrated generation-quality failure. It also does not make the unfinished artifacts acceptable.

## Preservation and next steps

The local archive contains 738 files (71,541,723 bytes) from the condition, attempt and output directories. Physical traversal included hidden and ignored files; source and copy hashes matched. Both receipt versions are also retained as explicitly labeled reconstructions from successful Write payloads in the immutable transcript. The first version is not represented as a contemporaneous filesystem snapshot.

Post-run verification found all 476 registered file pins, 13 native overlay pins, 1,694 prior-attempt files and 3,241 historical files unchanged. The full-record SHA256 is `896426b5aa1ed32a612424b7edeb7d68f455c4db575360d945c95855a8f24153`; the final receipt SHA256 is `abe96003cc59cebd1ecdef5c6d477375e847ff52e4906eddcbc89aa8ec564eb1`. This public report summarizes the private transcript and inventory; it does not publish or independently expose all execution evidence.

1. Resolve #2067 and verify the distinction between permitted Phase 1 corrections, premature core derivation and terminal evidence/source-review failures using offline traces.
2. Register any changed instructions and another attempt under a fresh condition. v10w remains stopped and unchanged. The current authorization covered one retry and does not authorize another automatic paid attempt.
3. After an accepted CHORUS native canary, continue the registered native-first sequence and independent scientific review. #1782/#1815 and the other source-acceptance issues remain open; API transport #1849 remains unresolved.
4. Preserve the broader [plan for both generation arms and all evaluation styles](matched_cborg_2026-09-17_v10w/README.md#both-arms-and-all-evaluation-styles). Production regeneration and manuscript scoring remain gated on accepted canaries; no further generation or evaluation was launched here.

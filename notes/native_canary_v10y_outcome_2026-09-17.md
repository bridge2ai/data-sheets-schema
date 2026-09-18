# v10y CHORUS native canary outcome, 2026-09-17

The authorized canary ran through CBORG on `claude-opus-5` and **stopped before its first receipt check executed**. The proposed command omitted the registered method, bundle and chunk-manifest arguments. The controller rejected its identity before core derivation. A full draft and coverage receipt were preserved; no core, audit, final report, live provenance record or accepted pair was produced. No further generation or evaluation was launched.

## Registration and execution

[PR #2081](https://github.com/bridge2ai/data-sheets-schema/pull/2081) resolved the #2078 audit-record namespace issue with opt-in renderer 14. [PR #2082](https://github.com/bridge2ai/data-sheets-schema/pull/2082) registered v10y after independent private, scientific-plan and fresh-public-checkout reviews. The user's instruction, “do the canary,” was bound to one CHORUS native attempt after registration merge, [successful CI on the exact launch commit](https://github.com/bridge2ai/data-sheets-schema/actions/runs/35314346661), and fresh input, runtime, model and accounting checks. The controller was also verified to reject readiness alone as launch approval.

Launch commit: `815978f12ca1e32b90bb7f328d51779aa6fcbaf7`.

Registration SHA256: `ef0563592109cebd3d0f96928ef796c490f9ad29c137dfa1fb81b713c248d02e`.

Overlay SHA256: `2f6566c7f4d99253a52235939edbf578de6f34138e23579bf300889ff6dc62f7`.

The attempt started at 2026-09-18 06:28:21 UTC and finished at 06:50:06 UTC, September 17 in America/Los_Angeles. All 64 model requests are settled. There were zero unfinished handlers at evidence freeze and no outstanding reservation. Detailed accounting remains in the private sequence ledger.

## Observed progress and stop

All eight source chunks were read in order, with successful cumulative receipt writes before each next initial chunk read. Independent review verified their returned content against the registered bundle. Later source rereads and an automatic compaction are retained in the transcript; these observations do not establish scientific retention or acceptance.

The full draft was written at call/result 270/272. Schema validation passed at 274/278, term validation passed at 279/283, and the record scope check passed at 291/293. The receipt gate had not passed and core derivation had not begun.

At transcript line 295, the model requested a strict receipt check with the correct manifest, label and project, but without `--method`, `--bundle` or `--chunk-manifest`. The complete registered command was present in the rendered instruction. The controller stopped on:

```text
native phase history: event 295: receipts helper arguments differ from the selected run
```

Line 296 is the pending permission callback. No parent decision or tool result followed it, and the receipt checker did not execute. This is an argument-identity stop, not a failed receipt-validation result. No Phase 3 audit was produced, so this attempt did not exercise the repaired #2078 format in a generated audit.

Independent review confirmed that the selected-input instruction explicitly overrides the generic playbook's shorter example. An isolated replay using copies of the frozen files found that the current CLI defaults resolve to the same full, receipt, bundle and chunk manifest as the explicit command. The registered contract requires explicit selection, so that default equivalence does not invalidate the recorded stop. Both replayed strict checks failed on the same 35 receipt paths absent from the draft. This reviewer-run result was never produced by the measured attempt; a failed Phase 1 receipt result would ordinarily permit correction before core derivation.

Two other shell forms were denied as unprescribed. Those denials alone did not disqualify the run. An invalid CLI option was corrected during Phase 1. These events are distinct from the recorded terminal cause.

## Independent draft review

The review covered the complete four-document, 1,698-line source bundle, saved full draft, receipt and relevant schema definitions. The YAML has no duplicate mapping keys and passes independent structural validation. These checks do not establish scientific support. The artifact was an unfinished Phase 1 draft; the findings do not predict what later correction or reconciliation would have changed.

- `/variables/0` through `/variables/8` repeat [#2079](https://github.com/bridge2ai/data-sheets-schema/issues/2079): webinar data-type categories are used as literal file-variable identifiers. The source table at lines 260–375 establishes categories, while the schema requires names or identifiers as they appear in data files.
- `/description` includes EEG in the released dataset without the progress limitation. The webinar says extraction is in process at source line 254; the current-release homepage lists waveform data without establishing an EEG release. A qualification under `/known_limitations` does not qualify the separate released-data assertion. This retains the scope/status concern in #1782/#1815.
- `/creators/2/description` states the 60+ consortium-member quantity without its governing anticipated-final heading at source lines 1064–1074. `/updates` preserves that qualifier elsewhere. This supports neither present attainment nor non-attainment and repeats the occurrence-level scope concern in #1782/#1815.
- `/maintainers/0` promotes a program-manager contact into dataset-maintenance responsibility. Source lines 1106–1108 establish contact details and a program role, without assigning dataset maintenance. The enclosing schema role remains unsupported even though its subordinate contact prose is accurate (#1801/#1815).

Independent receipt replay verified all eight chunk hashes and all 74 literal snippets, while finding 35 addresses absent from the draft. Examples include `variables[*].name` instead of `variable_name`, `grantor.name` where the grantor is a string, and absent collection-timeframe/total-size fields. Coverage was 29 of 92 receiptable leaves, with four exemptions; three no-value-overlap diagnostics were informational. Literal quotation does not establish entailment or repair the missing paths.

The count caveat improves on v10x's categorical disagreement claim. A remaining assertion that the observations describe different moments is not established by the undated homepage; a lower bound of over 45,000 and a count of 50,000 can coexist at one moment. Without a core, audit or report, shared full/core wording, audit classifications, reconciliation claims and the renderer-14 audit format remain unassessed. #1782/#1815/#1801/#1816/#2079 remain open.

## Separate control-audit defect

[Issue #2084](https://github.com/bridge2ai/data-sheets-schema/issues/2084) records a separately reproduced defect at lines 195/196: a `Read` call supplied a string for its numeric offset, and the native runtime rejected the argument before invoking the permission callback. It returned a typed input-validation error and no file content. The frozen controller's completion and retrospective checks cannot represent that unexecuted rejection and require a callback anyway.

This was not the actual terminal cause. The final control report contains both that missing-callback problem and incomplete evidence from the final callback interrupted by the argument-identity stop. The evidence does not establish an unapproved file read or a permission denial for the rejected numeric argument. A future fix must recognize only verified runtime input rejection while retaining strict checks for unexplained missing callbacks and ambiguous execution. The measured controller and outputs remain unchanged.

## Preservation

The private archive contains 554 files and 59,316,529 bytes from the condition, attempt and output directories. Physical traversal included hidden and ignored files; all source and archive hashes match. All 487 registration pins, 14 native pins, 3,276 prior-attempt artifacts and 3,241 historical files remain unchanged. No receipt version was reconstructed for a completed check because this attempt has no completed receipt-check result. The successful Write payloads remain in the original transcript.

| Retained artifact | SHA256 |
|---|---|
| Full draft | `004b3c975e0cbe8ac7f1eb2ecb82a1c30c6727fd931b7a47dfdbe457ea54b868` |
| Coverage receipt | `03eeb338c5750b411289b01909da13708d2eff38829d413e88a3430b110aaef5` |
| Terminal transcript | `7e8954965339fbf185fa8c287fa497d258b62dc9b4e7a7cd7e28b3621be5b9cb` |

This condition is consumed and cannot be resumed. No operator repaired a measured artifact. A later attempt requires a fresh reviewed condition and launch binding. #2079 and the other scientific acceptance issues remain open; a schema-valid draft is not an accepted final D4D.

The [broader registered plan](matched_cborg_2026-09-17_v10y/README.md#both-arms-and-all-evaluation-styles) still includes both generation arms and all applicable evaluation styles. Expansion and manuscript scoring remain gated on accepted canaries. Historical v7/v8, v9 and all subsequent attempts remain preserved.

Separately, [PR #2083](https://github.com/bridge2ai/data-sheets-schema/pull/2083) restricted Python CI to 3.12. Its [merged-main run](https://github.com/bridge2ai/data-sheets-schema/actions/runs/35315286921) passed with four test shards and one schema/example job. The running canary remained frozen at its earlier registered commit.

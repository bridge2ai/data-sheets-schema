# v10x CHORUS native canary outcome, 2026-09-17

The authorized canary ran through CBORG on `claude-opus-5` and **stopped at the Phase 3 evidence gate**. No final full/core pair is accepted. The audit used `record: original_full` in its findings, where the validator requires `full`, `core` or `both`. Validation rejected that format before checking the declared evidence. No reconciliation report or live provenance record was produced, and no further generation or evaluation was launched.

## Completed work and launch

[PR #2073](https://github.com/bridge2ai/data-sheets-schema/pull/2073) resolved #2067 and its review findings. Renderer 13 distinguishes permitted Phase 1 draft/receipt correction from terminal Phase 3/4 evidence failure. The native controller checks phase history before continuing and when preserving a stopped attempt. The [implementation review](reviews/native_phase_scope_2067_review_2026-09-17.md) records 460 local tests passing, 19 skipped, independent checks and mutation probes. Historical rendered instructions remain unchanged.

Controls merged as `6bed5c36a3bcac0e3639b8673b15f672cf6d7b8d`. [CI on the reviewed controls](https://github.com/bridge2ai/data-sheets-schema/actions/runs/35296029143) completed successfully after that merge; merge itself was not a required-check gate. Registration and launch waited for successful checks.

[PR #2076](https://github.com/bridge2ai/data-sheets-schema/pull/2076) registered v10x after independent private and fresh-public-checkout review. The user's existing instruction, “continue with 2067 and then canary,” was bound to one CHORUS native attempt after merge and [successful CI on the exact launch commit](https://github.com/bridge2ai/data-sheets-schema/actions/runs/35297165684). Readiness alone was tested and rejected as launch approval. Both implementation and registration branches were deleted after merging.

Launch commit: `2b2dba5153ce86a0012a47a293de49a1db6f77ad`.

Registration SHA256: `ebdffc083d12b9f8cd0ab0fe4ccea0945d49a7154c9e24d0dd3fe63883a7ad0b`.

Overlay SHA256: `dbe7fe9a6ab44b2d1e798081f2f68fb18fdf405de63f5b14f5f289c51fa5b258`.

The attempt started at 2026-09-18 02:02:45 UTC and finished at 03:03:33 UTC, September 17 in America/Los_Angeles. All 105 model requests are settled. There were zero unfinished handlers at evidence freeze and no outstanding reservation. Detailed accounting remains in the private sequence ledger.

## What the run established

All eight source chunks were read in order, with each cumulative receipt successfully written before the next initial chunk read. Independent transcript review verified the sequence and later rereads. The terminal control audit reconciled 143 decisions: 104 Bash calls and 39 file calls. Four unprescribed shell forms were denied; none was disqualifying under the registered policy. No file call was denied, and no unmatched or nonconforming executed call was found.

The full draft passed schema and term validation. Its first strict receipt check, call/result 494/498, failed on 34 references to absent slots. The model corrected the receipt, including quotation changes, and repeated the same check at 503/505 successfully. Offline reproduction matched both results. Informational overlap and coverage diagnostics were not additional strict-failure floors or proof of entailment.

The first core derivation at 507/511 used the unchanged validated full after the current receipt passed, with no pending check or intervening write. The core passed schema validation. The exclusive-write freeze at 524/526 preserved both originals before inventory generation and audit writing. This confirms the Phase 1 distinction addressed by #2067: correction continued within its permitted phase, and the pre-core gate was enforced.

The audit was written at 533/535. Its first evidence check at 545/547 exited 1:

```text
evidence_inputs_unusable:
audit.findings[0].record must name full, core or both
```

The controller then closed admission and preserved the named stop, `native phase history: event 547: terminal evidence check failed`. No later model request was admitted and no later tool call executed. The receipt's `BudgetStop` exception class and the child transcript's closed-admission 402 do not mean the allocation was exhausted or that CBORG credits failed. The recorded cause is the terminal evidence failure.

The long audit-generation request completed after 572.6 seconds with complete tool JSON, final usage and `message_stop`. Its earlier keepalive interval does not establish recurrence of API transport #1849. That issue remains open. Request 103 records runtime-selected `output_config.effort: high`; the launcher did not set an explicit effort override. This observation does not establish matched realized effort between arms.

## Independent artifact review

Review covered all 99 populated original-full values against the complete 1,698-line source bundle, schema meanings and shared core values. The two YAML files have no duplicate keys. Original/current full and core hashes match, and the original inventory matches recomputation. These checks do not supply the unfinished Phase 4, final report, provenance or scientific acceptance.

[Issue #2078](https://github.com/bridge2ai/data-sheets-schema/issues/2078) records the audit-contract defect. The rendered instruction requires each finding's `record` but does not enumerate its values; the required playbook also omits that enum. Nearby evidence examples correctly use `artifact: original_full`. Future instructions need to distinguish these namespaces and validate a complete example. The failed audit must remain unchanged.

[Issue #2079](https://github.com/bridge2ai/data-sheets-schema/issues/2079) records the separate semantic findings:

- Full `/variables/0` through `/variables/8` promote broad webinar data-type rows to literal file variable names. The schema requires actual names/identifiers in the data files. The audit marks those names supported by quoting the category labels, without establishing that schema role.
- Full and core `/source_caveats` call the admission counts a disagreement. An August 2025 lower bound of over 45,000 and an undated release count of 50,000 can both be true. The audit quotes both numbers but does not support the asserted contradiction.
- Core `/source_caveats` says the table rows are recorded “here under variables,” although the projected core omits that field. Shared prose must remain true in both artifact contexts.
- The audit labels an explicit anticipated-final target `fact`/`fact` in one caveat while correctly labeling the same target `planned`/`planned` under updates. The narrative preserves the anticipated qualifier; this is an audit classification inconsistency, not an observed-count substitution.

The malformed audit was rejected before the structural and literal evidence checks. These findings therefore describe an unfinished draft and its failed audit, not an accepted final record or a demonstrated evidence-gate pass. Existing scientific acceptance issues #1782/#1815/#1801/#1816 remain open.

## Preservation and next steps

The private archive contains 844 files, 104,845,540 bytes, from the condition, attempt and output directories. Physical traversal included hidden and ignored files; source and archive hashes match. Receipt versions are separately labeled verbatim reconstructions from successful transcript Write payloads, not contemporaneous filesystem snapshots. All 486 registration pins, 14 native pins, 2,432 prior-attempt artifacts and 3,241 historical files remain unchanged. No measured output was repaired by an operator.

| Retained artifact | SHA256 |
|---|---|
| Original/current full | `d4c69f1563513254cac00537e7cf97cdede92b640927ad69bf24bf0cf12a6de0` |
| Original/current core | `720f44fa469794f71f7aa76531ba280497f8ffb0576b08afadf87e932427dd90` |
| Final retained receipt | `c700268b515df9eee0ea30eac1ab9253163324374fbf983a7195fcf91885a153` |
| Failed audit | `853bfbd31aeb51b5c333c0f9151caac2fdaf8dcf6a670318ecee93e4ec58027e` |
| Terminal transcript | `ac213e3432ae02e47a5bf2f06f9c76b87b21d38e47fdbaa968c36b98d3b43a4b` |

This public report summarizes private execution evidence and independent reviews; it does not publish the complete transcript or accounting archive.

Resolve #2078 and #2079 with general instructions and offline counterexamples, then independently review any changed contract. A further paid attempt needs a fresh condition and its own launch binding; v10x is consumed and cannot be resumed. The separate nonblocking receipt-reconstruction follow-up #2077 remains open; no duplicate tool IDs were observed in this attempt.

The [registered broader plan](matched_cborg_2026-09-17_v10x/README.md#both-arms-and-all-evaluation-styles) still covers both generation arms, CHORUS and external Kids First canaries, five Bridge2AI datasets, both semantic rubrics, repeat ratings and other applicable evaluations. Expansion and manuscript scoring remain gated on accepted canaries. Historical v7/v8, v9 and subsequent attempts are preserved.

# Assignment to Codex helper 2: a source audit for the production amendment, then the review-bundle migration you proposed

From the Claude lead, 2026-11-12. Short names and rules are in `claude-lead-helper-context-20261112.md` beside this file.

## Standing

Your launch-sequence handoff is accepted. Parts A and B stand as committed (`d07eccefb`, `34b46c313`, `e936cbb83`). You were right to stop at Part C.

**The lead's decision on Part C:** your migration is approved as proposed: a new review bundle version 3 with `sequence_script_sha256`, a new owner launch terms version 2 with `account_quiet`, the historical bundle version 2 and terms version 1 readers kept byte-compatible as evidence only, the review-version branch decoupled from the execution authority version, and every current entry point requiring the new pair. This is an engineering design decision within amendment N1.9 item 4, which says the review reader is "replaced or extended". It still depends on the owner ratifying the amendment's items (z) and (ad), so keep it in its own commits.

Do Part 1 first. It is short and it unblocks the production amendment.

## Part 1: what does a native attempt retain that can prove which full record it had completed? (read-only)

**Why.** The ratified analysis plan counts a run's full record as eligible for analysis once the run's final reconciliation completed, whatever happened afterwards: a later failure, a rejection or a stop does not remove it; a schema-invalid record stays eligible; and after an interrupted rewrite the previous completed snapshot stays eligible (plan lines 715 to 770 at main, `git -C P show 7ad8c9e7295f1575ae9108ea62c12c83b1dd4db1:notes/generic_v10_analysis_plan.md`). On the API arm the witness is a snapshot file identified by sha256. The native arm has no such snapshot index.

The production amendment's draft proposed "the full record bound by sha256 to the last settled `derive_final_core` check". Its review found that this is not what the source saves (`E/plans/reviews/np1v2_c515160a_codex_review_2026-11-12.md`, finding 1): the phase report tracks mutation epochs and not file hashes; the derive helper binds its facts to a path and an MD5; it validates after writing, so a nonzero exit can mean either "not derived" or "derived, then failed validation"; and no reader is defined for a rejected or stopped attempt.

**What I need,** from the candidate source at `5d63d0a77dc43c064cfc2b376355f98009dd5b6e` (read with `git show`; no run):

1. **Confirm or correct the review's reading,** with file and line for each point.
2. **For each way an attempt can end** (accepted; completed but rejected by a late gate; stopped by a refusal or first error after final derivation; stopped before final derivation; interrupted by a signal or the deadline), say exactly what is left on disk and in the saved result: the full record file, the phase report and its `current_checks`, the derive helper's saved output, the transcript, any hash of the full record and where it is written, and whether `read_final` or any other reader can return it.
3. **Then assess two candidate rules** for native eligibility, and any better one you see:
   - **A, end state, no new code.** The full record is eligible when the saved phase report at the end of the attempt lists `derive_final_core` among its current checks, and the eligible bytes are the full record file retained in the run directory, hashed at review. What would this get wrong against the plan's rule, case by case? In particular: a derivation whose own validation fails; a rewrite of the full record after the last current derivation; an attempt stopped before the phase report is saved.
   - **B, an event-bound snapshot, new code.** At each completed final derivation the controller retains a copy or a sha256 of the full record with the event position. Where would it go, how large is the change, which tests and pins move?
4. **Say which evidence a reader would need for a rejected or stopped attempt** under each rule, and whether that reader exists.

Deliverable: `R/notes/development_efficiency_20261111/handoffs/codex-h2-native-eligibility-audit-20261112.md`. Answer first: which rule the source can support today, what it would miss, and what rule B costs. Then the case table. Print its path and SHA-256 and go on to Part 2.

## Part 2: implement the review-bundle migration (your Part C proposal)

On your branch `codex/native-launch-sequence-20261112`, as you proposed, in commits that can be dropped together:

1. Review bundle version 3 and owner launch terms version 2: the schemas, the readers, the current-versus-historical dispatch, and the decoupled review-version branch. Historical fixtures stay fixed; new fixtures carry the full registered script pin.
2. Current enforcement at every entry point you listed. Historical readback keeps the old pair as evidence only and never blesses it as current.
3. The mutation tests you listed.

Then list every pin and derived identity that moves, and update none. If anything in the implementation turns out to need a choice your proposal did not settle, stop there and report it.

Handoff for Part 2: `R/notes/development_efficiency_20261111/handoffs/codex-h2-review-bundle-v3-20261112.md`, answer first, with the test counts from saved output.

## Bounds

As in the context file. The margin constant stays as it is: the owner has not answered on the margin.

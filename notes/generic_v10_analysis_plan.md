# generic_v10 analysis plan (preregistration draft)

**Status: DRAFT awaiting the P4a word. Not preregistered, and it authorizes
nothing.** This is step P2 of `notes/d4d_generation_plan_2026-10-09.md` ("#### P2").
The owner has answered the 37 P4a questions; those answers are recorded as D64 and
applied in this text. The plan becomes binding only when the owner gives the P4a word
on its exact final text, which has not been given. Until then, no generic_v10
registration hash is put to the owner, and no billed generic_v10 step runs (the plan:
"Every billed generic_v10 step depends on P4").

**What performs P4 (D64, item 12).** The generation plan words P4 as "The owner
merges P2 with an explicit word", gated on "Merged on main". P4 is the owner's word
naming this file's sha256 at a named commit, recorded in the decision record, with the
merge following before any registration hash is put to the owner. Merging the draft
without that word does not perform P4. Under D58, P4 has two stages, P4a and P4b
(D64, item 1; "Staged sequence under D58", below).

- **Revised:** 2026-10-27 for R6 F1–F6; authority corrected 2026-10-28 against
  D26–D45 and D50–D61; revised again 2026-10-28 for the two P3 passes on `314189e4b`
  (Claude F1–F23, Codex F1–F13) and for D62–D63; revised a third time 2026-10-28 for
  the two verification passes on `1ed9bb1ef` (Codex V1–V8, Claude N1–N10), with the P4
  agenda consolidated; and updated 2026-10-28 to apply the owner's P4a answers (D64).
  D46–D49 are retired, not owner decisions. The local BC1/N2 implementations remain
  separately identified. This is a draft, not a retrospective registration or a
  declaration that the composed launch condition is ready.
- **Drafted:** 2026-10-20, by the Claude worker session (coordination Lane C2), at main
  `0a1132ecf`, on branch `claude/track-p-analysis-plan`. agy integrates the branch.
  The draft was revised the same day after an independent read-only review.
- **Inputs:**
  - the plan, sha256 `fcc78fab909f94e533d2ed8e00ebc3d5165c82a9d30fcc7aa87db4541ae1266e`;
  - P1, `notes/p1_v8_comparability_recompute.md` (this branch), which holds every v8
    number cited here;
  - `notes/recall_target_baseline.md`;
  - `notes/arm_comparison.md`;
  - `data/_wcrate/README.md`;
  - Lane C1's A1 note, commit `0d45c1ec8` (item 15).
  - `notes/reviews/v10_human_decisions_and_context_review_2026-10-20.md` at
    `a0e28d8821c69e2d4fe1b75b14e3c2a2140ae4d5` was the historical basis of
    the R6 amendment. Claude's correction
    `8f800a5919732cc1b773edc1537cb11e5b874b32` retires D46–D49 and records D50;
    `32c62222e1518db605ce5bfac426344bb5b1b711` records D51–D54, and
    `57784daadcc109839e4c76260ee4e5fd415a1c21` corrects D51's description
    (owner re-approval 2026-10-28T04:13:37Z), consistent with
    `notes/coordination/STATUS.md`;
    `13c81fdc16b66157056c0359e2c4a72086df7647` records D55–D57 and
    `4c6c5ac8b6866786b14e785a147b761cdfd8cba4` records D58–D60. D61 is recorded by
    `8c91e373a39cfc47a128ce21b034bd6587adcddb` on #5164's branch
    (`claude/5164-d52-kf-tables`), not in #5095's record at `4c6c5ac8b`. D62 and D63
    (2026-10-28T20:12:01Z) are recorded in `STATUS.md` only, so far;
  - BC1 `notes/bc1_production_2026-10-27.md` and contract sources at
    `3bd3c41f459b31848aee2f57e26deb86ef786970`;
  - BC1's fit and cost analysis,
    `d4d-executions/plans/reviews/bc1_fit_calibration_claude_2026-10-28.md` (§1 fit,
    §7 cost), and the review of the D59 implementation `8f83d6cb3`,
    `d4d-executions/plans/reviews/bc1_8f83d6cb3_claude_review_2026-10-28.md`;
  - the two P3 passes on `314189e4b`:
    `d4d-executions/plans/reviews/p2_314189e4b_p3_claude_review_2026-10-28.md` and
    `d4d-executions/plans/reviews/p3-codex-work/p2_314189e4b_p3_codex_review_2026-10-28.md`.
    Their dispositions are in `d4d-executions/plans/reviews/p2_p3_dispositions_2026-10-28.md`;
  - N2 `notes/native_n2_parity_delta_review_2026-10-25.md` at
    `be0bd05821256212e89e4d011ba6b30a780e299b`;
  - R_V5 remediation `aff4c9ca530a94b84f934698cdc791960cc31713` (local verification,
    not approval to activate v5 in either generation arm).
- **Plan dependencies:** P2 depends on G3, P1, A1 and A1b.
  - P1 is done.
  - G3 is partly decided (see the decision status below).
  - A1's Lane C1 sizing is superseded as a sizing input. BC1's fit analysis and the
    D59/D62 sizing replace it (item 15), and the owner has decided on them (D58–D60,
    D62).
  - A1b is not done. D63 authorizes one part of it: a single `count_tokens` call by
    agy on one fixed D59 CHORUS worker request, before the CHORUS registration.

  Every token figure that rests on the extrapolated 2.48 bytes per token is provisional
  until D63's measured ratio replaces it.

**Markers used throughout:**
- **(D64, item N):** a rule the owner settled in answering P4 agenda item N: owner,
  P4a answers (D64), 2026-10-28. Items 1–37 are settled this way.
- **[pending Dxx]:** a rule that rests on an undecided owner decision, followed by the
  plan's recommendation.
- **[proposed; …]:** a rule this draft offers for a question that is still open
  (agenda items 38–43), with the stage that decides it.
- **(P4 item N):** the numbered question in "P4 agenda" at the end of this file.

The pending and proposed markers are proposals, not rulings. Nothing in this draft
asserts a decision the owner has not recorded.

**Step IDs.** Two numbering schemes meet in this draft:
- **Plan IDs** are the generation plan's steps, for example A10 (the CHORUS pilot),
  A14 (the AI_READI pilot), A15 (the floor amendment), A16 (the CHORUS replicate
  gate), A17 (production), A18 and A19 (VOICE_PEDIATRIC and Kids First), and A21–A22
  (the optional with-crate stage).
- **Board IDs** are tasks in `notes/coordination/STATUS.md`, for example board A14
  (the S7 rework, #5162), board A17 (list splitting, #5211) and board A21 (the rebuilt
  clean CHORUS re-canary).
- **An unprefixed step ID is a plan ID,** with two exceptions. "A21" alone means board
  A21, the re-canary, so the crate stage is always written "plan A21–A22". "The A14
  digest" means board A14's schema digest, the one D59 keeps downstream.
- **The re-canary fills plan A10's CHORUS-pilot role,** with the 19/20 floor that
  D28/D37 register for it, where plan A10 assumed a pending floor. Plan A10c is its
  contingency.

## Decision status (reconciled 2026-10-28)

The October 20 draft is amended by D26–D45 and D50–D63. The former D46–D49
entries are retired proposals, not owner rulings; D51–D54 decide their subjects. Decisions authorize policy and
engineering; they do not establish a merged implementation, an accepted record,
remaining budget or a fresh launch word. Where the implementation differs from
the requested condition, items 14–15 name the discrepancy before P4.

| ID | Status | Where recorded |
|---|---|---|
| D06 | **Decided 2026-10-19.** Every generic_v10 API registration declares `{"type": "adaptive", "display": "summarized"}`, the routed v10 conditions included (keyed on the condition's base, v10). There is no typed-stage cache breakpoint in this condition. | #1849 comment of 2026-10-19 |
| D07 | **Decided 2026-10-19, option 1.**<br>- A $100 named generic_v10 API pilot allocation: CHORUS pilot $15 cap, one CHORUS contingency $15, AI_READI pilot $35 planning ceiling, one AI_READI contingency at most $35.<br>- At most 2 billed attempts per registered cell, then an owner review.<br>- Every run needs its own owner word naming its registration sha256 (for a roster, the roster sha256 and each registration sha256 it lists) and its cap.<br>- `d4d api batch --max-cost-dollars` is the between-run stop.<br>- The operator trigger is the cap minus the worst-case in-flight call: at most about $11.50 against $15 for CHORUS.<br>- The AI_READI lines are provisional (see "Feasibility under D58" and "Plan amendments"). | #1763 comment of 2026-10-19 |
| D10 | **Decided 2026-10-20: retire** the v10z/audit_controls lineage and audit28. | Owner's answer in the Claude worker session. `notes/reviews/v10z_retirement_2026-10-20.md` (this branch). agy is to post it on #4761. |
| D22 | **Decided 2026-10-20: withdraw.** The v10z standing authorizations do not extend to generic_v10, and they are withdrawn now. | Same record. agy is to post it on #1763 and #4761. |
| D01 | Superseded by D26/D28. | Native/API paths below. |
| D05, D17, D19, D23 | Decided through D34, D35 and D36. | Rule batch, freeze and review below. |
| D26, D27 | Track N with the default runtime profile; name **native agentic (direct arm)** and directories `claudecode_direct{,_core}/<label>/`. | D26 2026-10-23; D27 owner confirmation 2026-10-25. |
| D28 | Void 10-22b; one clean CHORUS API re-canary; 64k/32k/32k worker/omission/integration baseline, 128k report/reconcile, board A17 splitting, versioned wire/registration identity. Builder floor remains pending; 19/20 belongs to the re-canary only. | 2026-10-23; floor basis superseded by D37, partition selection refined by D45, re-canary slice raised by D58; BC1's integration reservation amended to 64k by D64 (item 9). |
| D29 | **Pending owner:** native effort and first-party `claude.ai` account. No API key. | Resolve for the native registration and launch. |
| D30, D38 | Revised R9 criteria limited to `confidentiality_level`/`hipaa_compliant`; American `license` spelling and new prompt pins in both assets. | D30 2026-10-23/24; D38 2026-10-25. |
| D31, D40 | Both 10-20a and 10-22a are archived assisted/invalid engineering evidence. D40 supersedes D31's initial generated-record disposition for 10-22a. Preserve artifacts; no run/archive edits. | 2026-10-23–26; assisted stratum below. |
| D32, D37 | D32's value-matching subtraction is superseded. D37 gates **phase-1 snapshot** receipt quality: `slots.with_receipt_at_receipt / slots.receiptable_at_receipt`. | D37 2026-10-25T19:44Z; item 3a. |
| D33 | Report-family pre-dispatch token-plus-output admission; no independent report-family trim under that decision. D44 subsequently requires a reviewed BC1 condition before the canary. | 2026-10-25/26; items 14–15 disclose the new exposure. |
| D34 | No new rule batch: measure #2918/#2919 with existing lints; defer #2931/#2937; #4018 reasons only; #3336 remains to be measured by CHORUS ×3. | 2026-10-25. |
| D35 | Freeze at rebuilt A21 registration on merged main, after board A17 (#5211), #5155 and #5157. A later runner change needs CHORUS byte-parity evidence and a diagnostic canary. | 2026-10-25; each billed canary still needs its own launch word. |
| D36 | Fresh Claude source reviewer plus Codex pass, neither generator nor operator; owner signs acceptance. Second blind reviewer seeds audit-recall observations against `original_full` before seeing the audit. | 2026-10-25; human decisions are not supplied by this draft. |
| D39 | Versioned worker wording recognizes a split list entry as a removal's owning root. | 2026-10-25; board A17 contract change. |
| D41, D42, D43 | No-touch operation and a terminal/rejection-state guard. D42 required a review of both guard candidates and an owner pick; the review is done and D55 made the pick. **Owner** runs the hash-approved re-canary command; agents monitor read-only. | D43 supersedes D41's operator clause; D55 records the guard pick. D64 (item 7) amends the monitoring rule for A21: agy alone may issue `d4d api stop` at the trigger or the clock (item 10). |
| D44, D45 | Build/review bounded carry for **all six projects** before the single clean CHORUS re-canary. Keep board A17 splitting; select project bounds from cost and output-cap risk inside BC1. | 2026-10-26; D59 chose BC1's request shape. |
| D46 | **Retired; not an owner decision.** Its subjects are decided by D51 and D52. | Claude's correction, §5.10. |
| D47 | **Retired; not an owner decision.** Its subjects are decided by D53. | Claude's correction, §5.10. |
| D48 | **Retired; not an owner decision.** Dropped by D54; the D41 latch journal covers its purpose. | The guard pick is D55's. |
| D49 | **Retired; not an owner decision.** Dropped by D54; it supplies no aggregate-input formula or project profiles. | D45 governs selection of BC1 bounds from reviewed per-project sizing; an allowance does not establish request fit or spending authority. |
| D50 | Decision-record corrections are prepared by Claude; agy fixes assigned code and pushes the permitted prepared bytes. | 2026-10-28T02:24Z in STATUS; Claude's correction §5.10. |
| D51 | Approves #5164's six omission contexts and its `source_manifest.yaml` edit: VOICE and VOICE_PEDIATRIC name their related-but-distinct dataset; the manifest declares CHORUS `release: null`; the AI_READI, CHORUS, CM4AI and KIDS_FIRST contexts are unchanged (CHORUS `ac94a74b…`). Lands before the A21 rebuild. | 2026-10-27; description corrected and re-approved 2026-10-28T04:13:37Z; claude's final independent check precedes merge. |
| D52 | Owner's human review of the evaluation contexts (#2912): CM4AI `human_subjects` and `regulated_access` false; KIDS_FIRST `ml_training_dataset` false; all other values accepted; committee-contact equivalence and the `regulated_access`-false Q9 exclusion accepted as scoring rules. | 2026-10-27; the scoring rules still need their implementation merged before scoring. |
| D53 | No agent edits anything inside a run directory or under `data/ATTIC/`, except README notes the owner or claude direct (extends D41); agy's 10-22a archive commits are ratified. | 2026-10-27. |
| D54 | Drops the retired "D48" guard and "D49" allowance; the reviewed, sizing-based #5155 rule stands. | 2026-10-27. |
| D55 | The D42 pick: codex's latch guard A (#5212), fixed first. Review findings F1–F4, F6 and F7 are fixed and re-reviewed before merge; agy's candidate B is not adopted. | 2026-10-28T07:02Z. State when this revision was written: #5212 is a draft at `db88ca68c`; the fix packet `4f20a300d` is not on it, and its re-review found it not merge-ready (R5, major: a textual conflict with the PR base). What remains open is implementation, re-review and composition, not the pick. |
| D56 | Override semantics: an override never continues a run past a terminal or control-state discrepancy; a retry needs a new registration; an override that can authorize nothing is refused before it is recorded. Amends the H3 spec. | 2026-10-28T07:02Z. |
| D57 | The D41 journal head is anchored at launch: the runner prints it at each start and stop, the monitor record keeps it, and a resume must present the expected head. | 2026-10-28T07:02Z. |
| D58 | The v10 path after BC1's fit and cost analysis: fix BC1 for all projects; raise the A21 slice from about $25 to $60; run the CHORUS re-canary under the fixed BC1; decide the matrix's scope and budget on its measured cost. | 2026-10-28T16:41Z; the matrix decision is deferred to that measurement. D64 (items 1 and 3) adopts the P4a/P4b staging that applies the deferral, and one funded attempt ("Staged sequence under D58", item 10). |
| D59 | BC1's request shape (the D44 design choice): typed-audit calls send the full schema catalog once, drop the redundant per-slot `domain_of` lists and send the bundle once; the full, receipt-completion, reconcile, report and regate calls keep v10's A14 schema digest. | 2026-10-28T16:41Z; implemented in `8f83d6cb3` (items 14–15). |
| D60 | No typed-stage prompt-cache breakpoint; D06 stands. | 2026-10-28T16:41Z. |
| D61 | D52's committee-contact equivalence applies wherever `governance_committee_contact` is scored, rubric10 E2.2 included. | 2026-10-28T18:23Z. |
| D62 | BC1's fit gate for A21: the gate checks the floor and the caps scenario with the measured 1.25× escape factor; the escaped bound is reported, not gated. Request bytes are sized at 2.48 bytes per token and future-response bytes at 1.75. The CHORUS A21 registration uses `aggregate_input_tokens` 4,500,000 (in D62's sizing CHORUS needs about 4.06M, every call at or below 0.85 of its room, which is a sizing result and not an enforced ceiling; added spend exposure at most $3.13). | 2026-10-28T20:12:01Z, after the review of `8f83d6cb3`; item 15. |
| D63 | One `count_tokens` calibration, run by agy from the launch-base checkout through the runner's admission-check route, on one named, fixed D59 CHORUS worker request. It logs the request sha256 and the count; no generation and no other provider call. The measured ratio replaces the extrapolated 2.48 before registration. | 2026-10-28T20:12:01Z; item 15. |
| D64 | **The owner's answers to the 37 P4a questions** (P4 agenda items 1–37). The recommended answer to 36 of them; for item 7, the owner's own choice: agy, stop command only. Among them D02 (items 13–15 and 17–23), D03 (item 29), D04 and D16 (item 37: out of this matrix), D08 (item 8: the written risk acceptance; the CBORG follow-up still needs the owner's separate yes), D20 (item 28) and D21 (item 35). Item 7 amends D41 and D43 for A21. | Owner, P4a answers (D64), recorded by claude, answered by 2026-10-28T23:23Z. The P4a word, naming this file's final sha256 (item 12), is separate and has not been given. |
| D15, D24, rubric20's version (#2911, E4), and D02's VOICE_PEDIATRIC count | **Pending: P4b questions** (items 38–41). | Decided at P4b, before any production registration. |
| Remaining D09 choices, D11–D14, D18, D25 (and D29 above) | **Pending: the native amendment** (item 43). | Decided before native registration. |

The closing comments of October 11 that cited unpushed commits are not rulings; the
appendix records them (A).

### Prospective boundary and assisted-evidence stratum

Generic-v10 evidence already exists. The `2026-10-20a` and `2026-10-22a` CHORUS API
canaries, their retained raw responses, ledgers, hand-edit/recovery findings and
costs informed the redesign. Lane C1, K1/K1 v2 and the BC1 offline sizing also use
historical outputs or explicit proxies. These are disclosed engineering inputs,
not unseen production outcomes or tests of the final BC1 condition.

Under D31/D40 (archive commits ratified by D53), both canaries are **assisted/invalid evidence-only**. Preserve
every known attempt and expenditure in an assisted-engineering table, including
unknowns where originals are missing. Exclude them from clean generated-record
acceptance, confirmatory effects, and **both numerator and denominator** of the
clean automatic-success rate. Report their totals separately so exclusion cannot
hide cost or assistance. No rewrite or rescore promotes them into the clean set.

P4 must precede the first clean outcome from the fully specified, reviewed and
registered production condition. Rules and tolerances below are prospective to
that condition, after observing the disclosed engineering evidence; they are not
claimed to have been fixed before any v10 data existed. A later change is a dated
amendment and condition boundary, not a silent correction to historical results.

### Known v10 values on the predicted metrics

The two assisted CHORUS canaries are the only v10 observations. Their values on
the metrics the Predictions use are disclosed here, so that every P4 choice of a rule,
a tolerance or a conversion to "descriptive" is made with them on the record.

They were recomputed read-only from the records in `launch-base`:
- `receipts.populated_leaves` at P1's pinned `receipts.py` (sha256 `7bfb8470…`);
- `scripts/recall_target_baseline.py` `target_counts` (sha256 `e8960965…`, this
  branch);
- each record's `receipt_completion` and `receipts` blocks.

The full records hash to `ac182648…` (10-20a) and `b1716e82…` (10-22a); the phase-1
originals `O` to `d3b91e60…` and `440ea561…`. The leaf and coverage figures agree with
the P3 Claude review's independent recomputation.

| CHORUS record | Row 1: populated leaves, final (phase-1 `O`) | Row 2: coverage as row 2 reads it, receipted / receiptable | D37 at receipt (`O,R1`) | Final-record coverage (`F,Rf`) | Row 3: lineage | Row 3a: parent datasets; versioned processing software |
|---|---|---|---|---|---|---|
| v8 `04f` rep1 | 235 | 54/186 = 0.290 (stored v3, final) | — | as row 2 | 1 | 0; 0 |
| v8 `04f` rep2 | 278 | 83/248 = 0.335 | — | as row 2 | 1 | 0; 0 |
| v8 `04f` rep3 | 251 | 78/198 = 0.394 | — | as row 2 | 0 | 0; 0 |
| v8, mean or pooled | 254.7 | 215/632 = 0.340 | — | — | 0.67 | — |
| v10 `10-20a` (assisted) | 72 (67) | 51/58 = 0.879 (`receipt_completion.before`, `O,R0`) | 58/58 | 58/63 = 0.921 | 0 | 0; 0 |
| v10 `10-22a` (assisted) | 90 (79) | 52/64 = 0.813 | 64/64 | 64/75 = 0.853 | 1 | 0; 0 |

The D37 values are those in D37's decision text and in the records' provenance
`receipt_completion.after` blocks. 10-20a's own
`intermediate/CHORUS_receipt_completion_result.json` reads `after` = 51/58, the same as
its `before`: one more assisted discrepancy.

**Acceptance rows (item 5) on the same records,** read from each record's stored
receipts and validation blocks with `canary.receipt_floors` and
`canary.duplicate_key_count`:

| CHORUS record | Snippets unverified (mismatched of total) | Other four receipt floors | Validation | Duplicate keys |
|---|---|---|---|---|
| v8 `04f` rep1 | 0 (0 of 79) | 0 | passed | 0 |
| v8 `04f` rep2 | 2 (2 of 90) | 0 | passed | 0 |
| v8 `04f` rep3 | 1 (1 of 117) | 0 | passed | 0 |
| v10 `10-20a` (assisted) | 1 (1 of 115) | 0 | passed | 0 |
| v10 `10-22a` (assisted) | 0 (0 of 133) | 0 | passed | 0 |

So one mismatched snippet is common: two of the three v8 CHORUS records and one of the
two assisted canaries carry at least one. Under item 10's classification as first
proposed, that alone would have been a rule-level rejection of the re-canary, ending
the condition; the content-slip class D64 adopts allows one contingency instead (item
32).

**What these values would imply, if clean records resembled them:**
- **Row 1** would not hold for CHORUS. Its threshold is 0.9 × 254.7 = 229.2 leaves,
  and the assisted records have 72 and 90, 28% and 35% of v8's mean.
- **Row 2** would hold by about 0.55: the pooled ratio is 103/122 = 0.844, against a
  threshold of 0.340 − 0.05 = 0.290. But each assisted record has fewer receipted
  leaves (51, 52) than every v8 replicate (54, 83, 78). The ratio rose because the
  record shrank, which is why row 2 now reports its numerator (Predictions).
- **Row 3** (CHORUS lineage) would not hold: the assisted mean is 0.5, against v8's
  0.67, and row 3 needs a strict rise.
- **Row 3a** would hold for CHORUS: neither record has a parent dataset or a
  versioned processing-software entry.
- **The D37 acceptance ratio** (not a prediction) was 1.00 on both. Receipt completion
  drives it towards 1, which is why item 8's floor rule matters.
- **Rows 4 and 5** have no measurement: neither record has had an E2-protocol review
  or a joint rating. Rows 6–8 are not predictions.

**Why they are not evidence for or against the selected condition.** Both canaries ran
S7 as implemented, with slot descriptions trimmed in generation, and before BC1, the
board A14 rework, D59 and the D30/D38 rule text. Both were also assisted: 10-20a
changed registration mid-run and carries a patched model response, and 10-22a's
ledger was reset by hand mid-run, which bought a second integration call its
registration forbade (D31, D40). The values may not survive those changes. They are
disclosed so that the owner, a later reader and this draft can see what was known
when the rules were chosen: if a row is made descriptive at P4, the P4 record should
say that these values were in view. The owner answered P4a (D64) on the P4a packet,
which cites them for rows 1 and 2 and for content slips; no row was made
descriptive.

## Staged sequence under D58 (D64, items 1–3)

**Why the plan needs stages.** D58 decides the matrix's scope and budget on the
re-canary's measured cost. P4 must come before the re-canary, because every billed
generic_v10 step depends on P4. So the text ratified before A21 cannot fix the
matrix, and the matrix fixed after A21 must not be free to follow A21's outcome. The
sequence below separates the two stages, and fixes now the rules the later stage
applies.

**The sequence:**
1. **P3 dispositions.** Every P3 finding is fixed in this text or converted to a P4
   question, and the revision is re-reviewed.
2. **P4a.** The owner ratifies this file's exact text, by sha256: the A21 condition and
   every rule whose first relevant outcome is A21 or a later run. The owner's answers to
   the P4a questions are D64; the P4a word on this file's final sha256 has not yet been
   given. The P4 agenda gives
   each item's latest decision point. P4a may leave to P4b only the items the agenda
   marks P4b (items 38–41), and to a later stage only items 42 and 43. No rule is
   chosen after an outcome it governs.
3. **The A21 registration.** After D44's all-project build and review, the composed
   head is named by commit, and one registration composes D59's request shape, D62's
   fit gate (with D63's calibrated ratio) and D55's guard. Its review checks the
   composed condition against this ratified text; any deviation needs a P4a amendment
   before the launch word. The owner's launch word names the registration's sha256 and
   the $60 cap (D07, D22, D43).
4. **A21.** One clean CHORUS re-canary, n=1, in plan A10's role. It stays descriptive
   permanently, whatever its outcome: it never becomes a replicate, a confirmatory
   record, or a record of the E2 or E5 rosters.
5. **After A21, by outcome:**
   - **accepted:** the measured-cost packet, then P4b;
   - **rejected for a rule-level cause:** A13 ends the condition and schedules the next
     shared-generation version, and there is no P4b (§10);
   - **any other stop, or an assisted run:** P4b waits for a funded contingency (plan
     A10c, P4 item 3), unless the owner decides scope on the partial packet, which is
     then labelled partial. If the contingency also ends without acceptance, D07's owner
     review decides between scoping on the partial packets and ending the condition.
6. **The measured-cost packet.** It reports:
   - A21's billed cost by stage;
   - each call's outcome: completed, transport error, answer-level rejection or
     terminal;
   - each call's measured size against its room, and the aggregate against D62's
     sizing;
   - the wall clock.

   It carries no quality comparison against v8. A partial packet says which stages it
   lacks.
7. **P4b.** A dated amendment, reviewed as P3 was (a Claude reviewer plus a Codex CLI
   pass, each finding filed), applies the scope rule to the measured-cost packet and to
   the budget the owner sets under D58. It fixes the matrix's scope and budget, and
   with them K, the confirmatory set and the E2 and E5 rosters. It applies the D20
   branch and the D03 sequence that P4a selected, and it answers items 38–41. It
   applies rules; it does not invent them. The owner ratifies it by sha256 before any
   dependent registration (plan A14-reg, A16-reg).
8. **The floor's branch (§8, P4 item 28).** If AI_READI is in scope, its pilot runs and
   is accepted before A15, and A15 computes the floor from both pilots. If AI_READI is
   out of scope, A15 applies the re-canary-only fallback. If the AI_READI pilot ends
   without acceptance for a cause that is not rule-level, AI_READI leaves scope as
   infeasible, reported as a feasibility result, and the fallback applies. No
   production roster starts before A15 registers the floor.
9. **Dependent pilots and rosters,** each with its own registration, review, cap and
   owner word.

**What P4b may change, and what it may not:**
- **It may change** which whole projects are in scope, a replicate count where this
  text predeclares the options (VOICE_PEDIATRIC ×1 or ×3), the budget lines, and the
  answers to the items P4a left to it (38–41). Whether the AI_READI pilot runs follows
  from scope.
- **It may not change** any rule P4a fixed: no metric, instrument, decision rule,
  tolerance, analysis-set definition, eligibility rule or missingness rule. It may not
  use any v10 quality value, A21's included, to choose a project or a threshold.
  Changing a rule needs its own prospective amendment, and it starts a new analysis
  stratum.

**The generation plan needs matching amendments,** for plan A10's role, plan A14's
conditional start, plan A15's inputs and E5b-reg's roster. This draft does not edit
the generation plan; the amendments are listed at the end ("Plan amendments"), with
their deadlines. The generation plan's own P4 gate stands: the ratified plan is merged
on main before any registration hash is put to the owner.

### Scope rule (D64, item 2)

- **Whole projects only.** A project is in or out with all its cells. P4b never trims
  replicates inside a project to fit a budget.
- **The evidence is cost, fit and call failure:** A21's measured cost and call
  outcomes, each project's D62-style sizing, and the single-delivery exposure below.
  It is never a quality metric of A21, or of any v10 record, against v8.
- **The order:** CHORUS ×3 → CM4AI ×3 → VOICE ×3 → AI_READI (pilot + ×3)
  → VOICE_PEDIATRIC ×1 → Kids First ×1.
  - It follows the generation plan's ascending bundle size.
  - AI_READI comes late because its comparator is pending (D02) and it costs the most.
  - P4b funds the longest prefix of the order that the budget covers, each project
    priced per accepted record with its retries (below).
- **A descoped project is "out of scope", not missing.** Every table lists it as "out
  of scope (P4b)", and it is not counted in K. Item 7's missing-cell rules apply only
  to in-scope cells.
- **K, the confirmatory set, and the E2 and E5 rosters** follow from the in-scope
  projects (items 3 and 12).
- **K = 1.** If only CHORUS is in scope, every verdict is a single-project result,
  written "holds for CHORUS", and no "k of K" statement generalizes from it.
- **D03 and D20 follow the floor's branch** (step 8): with AI_READI out of scope its
  pilot does not run, and the production floor comes from the re-canary alone.

### Feasibility under D58 (an input to P4b, not a forecast)

**Money.** These are estimates from BC1's fit analysis (§7: K1 v2's prices, 2.48 bytes
per token, no cache breakpoint under D60). They use its "A + drop `domain_of` + bundle
once" rows, less about $8 per run for D59's downstream A14 digest (the P3 Claude
review's adjustment). They are engineering scenarios, not measured D59 runs:
- they exclude retries, re-address, repair, `report_after_repair` and interrupted
  billed tails;
- the caps column carries half a report regate, K1's convention (fit review §7.1,
  §7.4), so it does not bound an attempt that needs a whole regate;
- D62's 4.5M allowance adds at most $3.13 of exposure to a CHORUS run.

| Item | Expected | At caps | Set against |
|---|---:|---:|---|
| One CHORUS run | about $37 | about $49 | D58's $60 slice: one attempt, no contingency |
| One CM4AI run | about $83 | about $102 | — |
| One VOICE run | about $105 | about $127 | — |
| One VOICE_PEDIATRIC run (VOICE record as proxy) | about $96 | about $118 | — |
| One AI_READI run | about $162 | about $191 | D07's $35 AI_READI planning lines |
| One Kids First run | not priced | not priced | D59 expects its integration at caps to be borderline |
| The 15-run matrix (CHORUS 4, AI_READI 4, CM4AI 3, VOICE 3, VOICE_PEDIATRIC 1) | about $1.46k | about $1.77k | the $420 planning ceiling |
| E5's joint rating | about $190 | about $394 | generation plan E5 |

The fit review's cheapest matrix figure, $1,021, assumes a typed-stage cache breakpoint
with every later call hitting; D60 rules that out.

**Against the $420 figure.** No owner ruling set the $420; it is a planning figure
(decision record §5.1.1). The assisted canaries spent $35.76 settled ($41.79
worst-case reserved) of it, and A21 takes $60, which leaves about $318–324. That buys
CHORUS ×3 (about $110–148) but not CM4AI ×3 (about $250–307). No version of the full
matrix fits it, so D58's later scope decision is necessary, not optional.

**Runs: the single-delivery exposure.** BC1's typed calls and receipt completion each
admit one delivery (`transport_attempts=1` in `bc1_runtime`). The illustration below
uses P1's per-call rate (8 retried calls in 92: 5 transport, 3 answer-level),
independence between calls, and the fit analysis's call counts at current bounds
(typed calls CHORUS 7, CM4AI 14, VOICE and VOICE_PEDIATRIC 17, AI_READI and Kids First
25, plus one receipt-completion call each). D45's bound selection can change these
counts.

| Project | Single-delivery calls per run | Terminal-stop exposure per attempt, all causes (transport only) | Both of D07's two attempts stopped, all causes (transport only) |
|---|---:|---:|---:|
| CHORUS | 8 | 52% (36%) | 27% (13%) |
| CM4AI | 15 | 74% (57%) | 55% (32%) |
| VOICE, VOICE_PEDIATRIC | 18 | 81% (63%) | 65% (40%) |
| AI_READI, Kids First | 26 | 91% (77%) | 82% (59%) |

These are not forecasts: v8's calls were far smaller than BC1's 0.4–0.8M-token typed
inputs, and the stage rates are measured in item 18. They are not tolerances, and they
never choose between projects on quality. They are inputs to three decisions:
- P4b's scope, through the budget per accepted record below;
- the written risk acceptance for single-row runs (D08, decided by D64, item 8), which
  for A21 names its 8 single-delivery calls (item 10);
- the decision after A21 on a transport-only redelivery for production (D64, item 4).

**What the exposure means for complete n=3.** Item 3 requires three accepted cells per
project for a primary verdict, and a cell gets two attempts. Under the same
illustration, the chance that a project reaches complete n=3 is:

| Project | All causes | Transport only | With one transport-only redelivery per call |
|---|---:|---:|---:|
| CHORUS | 39% | 66% | 82% |
| CM4AI | 9% | 31% | 56% |
| VOICE | 4% | 21% | 46% |
| AI_READI | 0.6% | 7% | 25% |

The last column keeps the 3-in-92 answer-level failures terminal (D56) and lets a
redelivered call fail transport again at 5 in 92. Unless BC1's calls fail far less
often than v8's, most primary verdicts beyond CHORUS would be "not measured". This is
the main input to the owner's answers to items 4 and 16 (D64), and it feeds P4b's
budget.

**Budget per accepted record (D64, item 2).** P4b prices each
in-scope project per accepted record, including its expected retries within D07's
bound, not per attempt. The failure rate it uses is P1's 92 v8 calls pooled with A21's
calls, by call type where A21 has them. A stopped attempt bills only the calls made
before the stop.

## 1. Estimands (P2 item 1)

1. **Feasibility and acceptance.** For each registered cell, the outcome is accepted
   or rejected (A11–A13), with its attempt count. Pilots are reported separately from
   production, and billing or native runtime evidence separately again. Two success
   proportions are reported per arm, stage and project (D64, item 25):
   - **All started without assistance (the feasibility headline).** The denominator is
     every registered attempt that started without assistance, fixed at launch.
     Success is acceptance with no later assistance. A later intervention, a terminal
     stop or missing output is a non-success here. An assisted record still never
     enters a clean scientific analysis.
   - **Clean, conditional.** The denominator is the attempts that stayed clean (item 7's
     checks), and the proportion is labelled as conditional on staying clean.

   A registration refused before any billed call is a preflight refusal. It is counted
   separately and is in neither denominator. The two pre-P4 assisted canaries stay in
   their own engineering table (above).
2. **Package effect against v8.** For each primary metric in item 2, the difference
   between the generic_v10 confirmatory cells and the v8 comparator records, project
   by project, in both analysis sets of item 3.
   - It is a **package-level** effect: everything listed in item 4 changes together,
     and nothing here attributes a difference to any one component.
   - For AI_READI the comparator is itself pending (item 2). Under option (a) the
     AI_READI difference also crosses the owner's with-crate arm boundary.
3. **Replicate structure (#2932).** The structure metrics of item 2 for the 3-replicate
   v10 cells against v8's 3 replicates of the same project.
4. **External feasibility.** VOICE_PEDIATRIC and Kids First: whether an accepted
   record is produced, plus descriptive metrics. There is no comparator.
5. **Cross-arm contrast (API against native agentic (direct arm)).** D26/D27 select
   Track N and its default runtime profile. The first native CHORUS canary is
   **n=1 descriptive feasibility only**. Runtime, provider, transport, effort,
   tools, staged exposure and the procedural differences below change together;
   shared prompt assets do not isolate a runtime effect. Native production cells
   are unregistered. No six-project native/API effect is estimable from one canary.

## 2. Comparator, metrics and cell roles (P2 item 2; D02 decided by D64)

**Comparator** (D02, decided by D64, items 13–14): the v8 API fill.
- Prefix `2026-09-04f` for CHORUS and VOICE, and `2026-09-04g` for AI_READI and CM4AI:
  12 records, 3 per project, listed with their sha256s in P1.
- Excluded: the `04` and `04b`–`04e` canaries and the invalid `04f` AI_READI rep1.
- The v9 CHORUS canary (2026-09-12) is a secondary single-point CHORUS reference.

### The AI_READI comparator (D02, decided by D64, item 14)

**Why it is open.** The three AI_READI v8 records (`04g` rep1–3) were generated from
bundle `d22b61a9`, which contained the dataset's RO-Crate.
- The owner's ruling of 2026-10-14 is recorded in `data/_wcrate/README.md`: "generation
  runs read no RO-Crate content. Crates are the input of the separate with-crate and
  crate-only arms only."
- The same file lists these three records, and the invalid `04f` rep1, among the
  with-crate AI_READI records.
- The crate was not inert. Each record's receipt cites the crate chunks (c022–c024 of
  the pinned pre-#5042 manifest) in 32–37 of 314–351 receipted snippets, across 17–22
  top-level slots (P1).

D02's own option text, "bundles byte-identical to today's for all four projects", no
longer holds.

**The answer (D64, item 14).** When AI_READI is in scope, its comparator is option
(d): a new no-crate v8 API run on the historical v8 code with only the bundle swapped,
used only if a render diff shows that only the bundle differs. When AI_READI is out of
scope, or the diff fails, AI_READI is descriptive, option (b). The new run is billed
(about $10–14 per v8 AI_READI run) and needs its own registration, review, allocation
and owner word. The options were:

| option | AI_READI comparator | what it costs or changes |
|---|---|---|
| (a) | keep v8 `04g` rep1–3, **labelled cross-arm** | AI_READI's package effect also crosses the with-crate/no-crate boundary, and it is reported as such, never pooled unlabelled with the other three projects |
| (b) | **leave AI_READI out** of the confirmatory v8 contrast | the confirmatory set is CHORUS, CM4AI and VOICE, 9 + 9 records. AI_READI v10 is reported descriptively |
| (c) | the **2026-10-14b no-crate agentic rerun** (`claudecode_agent`, rep1–3, bundle `1a58ad7b`; untracked in `d4d-executions/aireadi-v8-b`) | Its three provenance records carry runtime `Claude Code`, provider `Anthropic` (not CBORG; `base_url` null) and no `reasoning_effort`. So the AI_READI contrast becomes runtime, provider, transport and effort together, plus the package: item 1.5's terms, never any one of them. The records are not on main, so they need a reviewed data PR first |
| (d) | a **new no-crate v8 API run** of AI_READI | billed; needs its own registration, review, allocation and owner word. D07's allocation covers generic_v10 runs only |

**Consequences of the answer:**
- **The AI_READI pilot's canary baseline (D64, items 14 and 30).** Plan A14-reg plans
  the pilot with `--canary-baseline 2026-09-04g_claude-opus-5-api-generic-v8`, but
  `canary.baseline_for` checks no bundle. It reads the stored check blocks of every
  record whose label matches the prefix, so that baseline would never reveal the crate
  in it. So:
  - under (d), the new run's prefix is the baseline, read as context and never as a
    reason to reject (item 5);
  - under (b), the pilot runs without `--canary-baseline`. With no baseline, `d4d api
    batch` computes no baseline comparison, so the A11 rows decide.
- **E2's blind batch:** under (d), the new no-crate v8 records enter E2 as AI_READI's
  comparator; under (b), AI_READI leaves the confirmatory comparison, and its v10
  records are reviewed as a descriptive stratum.
- **Plan gates that cannot pass as written** (P1; under D50 claude prepares the plan
  amendment and agy pushes it):
  - A4's gate, "The CHORUS and AI_READI bundle md5s equal the comparators'
    (9b2ef4b6, d22b61a9)";
  - A14-reg's gate, "the bundle md5 is d22b61a9";
  - the run tables' "identical bundle d22b61a9".

  Today's AI_READI bundle is `1a58ad7b`, and the plan needs amending before A4.

### Cell roles (D03, decided by D64, item 29: option (a′); scope fixed at P4b)

Every row after the re-canary runs only if P4b puts its project in scope (scope rule
above).

| role | cells | counts as a replicate | analysed as |
|---|---|---|---|
| CHORUS re-canary (A21, in plan A10's role) | 1 | never | descriptive n=1, separately and permanently |
| AI_READI pilot (A14) | 1, only if AI_READI is in scope; after the re-canary passes blind source review, and before A15 | no | pilot, separately |
| CHORUS replicate gate (A16) | 3 under the A15 floor | yes | confirmatory |
| Production (A17) | the in-scope projects among CM4AI, VOICE and AI_READI, 3 each, in the scope rule's order | yes | confirmatory (AI_READI per the comparator decision above) |
| VOICE_PEDIATRIC (A18) | ×1 if in scope (D02's recommendation; ×3 only if the paper needs replicate variance) **[pending: P4b, item 39]** | — | descriptive (item 2a) |
| Kids First (A19) | ×1 if in scope | — | descriptive (item 2a) **[pending D15: P4b, item 38]** |
| With-crate CHORUS (plan A21–A22) | none: not in this matrix (D04, decided by D64, item 37) | — | — |

The plan's A21–A22 identifiers for the optional crate stage are retained only as
historical task references, always written "plan A21–A22". Unprefixed **A21 is the
clean CHORUS API re-canary** (board A21) under D35/D44, not an authorization for a
crate arm.

### Six-project × generation-arm and evaluation matrix

All prospective cells below remain unlaunched/unregistered unless a later,
hash-bound owner record explicitly says otherwise. “Confirmatory” names the analysis
role D64 sets (items 2 and 29), not current authorization or acceptance. The table
shows the full planned matrix; P4b's scope decides which projects run.

| Project | API arm (`claudecode_api{,_core}`) | Native agentic (direct arm) (`claudecode_direct{,_core}`) | Evaluation/contrast role |
|---|---|---|---|
| CHORUS | One clean re-canary, n=1 descriptive for good; production n=3 confirmatory against v8 | First canary n=1, descriptive feasibility only; no production replicates registered | API production enters E2/E5; native canary has independent acceptance review and separately registered descriptive E5 ratings, never a confirmatory native/API verdict |
| AI_READI | If in scope: no-crate pilot separately; n=3, confirmatory against the new no-crate v8 run if its render diff passes, otherwise descriptive (D64, item 14) | Unplanned/unregistered | API E2/E5 use the new no-crate v8 records as comparator; any later native contrast must also declare source/profile/account/effort differences |
| CM4AI | n=3 confirmatory against v8, if in scope | Unplanned/unregistered | API E2/E5 use non-human-subject/non-regulated applicability (D52); companion analyses are not dataset-processing facts |
| VOICE | Adult n=3 confirmatory against v8, if in scope | Unplanned/unregistered | API E2/E5 adult scope; pediatric records never substitute |
| VOICE_PEDIATRIC | n=1 descriptive feasibility if in scope, no v8 comparator [pending: P4b, item 39] | Unplanned/unregistered | Separate pediatric E2-style source review/E5 descriptive row; no confirmatory effect or adult replicate |
| KIDS_FIRST | n=1 descriptive external resource-level feasibility if in scope, neutral profile, subject to actual input fit [pending D15: P4b, item 38] | Unplanned/unregistered | Neutral-context source review/E5 descriptive row; no v8 comparator and no inferred cohort-level equivalence |

For a later registered native/API comparison, freeze identical selected source
bundle, manifest, source policy, full/core schema closures, profile, omission
context and scientific assets where the contrast claims they match. Hash the
complete effective instructions and each stage request separately; if any differ,
declare that difference in the treatment table rather than normalizing it away.
Native uses first-party `claude.ai` login with no API key; the effort/account and
runtime limit basis remain D29 owner choices. API uses the explicitly selected
CBORG route and recorded returned model identity. Attempt, termination, missing
output and assistance rates are reported separately per arm; neither API token
prices nor native subscription charges are assumed interchangeable.

The N2 declaration at `be0bd05821256212e89e4d011ba6b30a780e299b` remains required:

| Difference | Declared treatment difference |
|---|---|
| H1 | API receives supplied text/digests and a no-tools phase boundary; native reads declared files, generates the pair and sees full-schema/provenance instructions. |
| H3 | API RETURN/metadata and protocol-7 batch grammar become native ordered stages, receipt-v1 duties, attribution drafts and relocated role review. |
| H6 | Native can correct phase-1 receipts before sealing and sees captured context/full schema. API's explicit flat-claims/status-matching report clarification is not in the native appendix. |
| H7 | API receipt-v2 continuation/registration becomes native helper commands, recorder metadata and receipt-v1 stage contracts; tool order and asset exposure differ. |

These are mixed scientific and procedural differences. Common uniform/R9 bytes
do not establish identical complete instructions, tool observations or model
attention. BC1 currently supports only the API parent tuple (item 14); native
BC1 parity is **not installed or accepted**. The native n=1 canary therefore
cannot silently stand for the API bounded-carry treatment.

With every project in scope, the v10 confirmatory set is the **three-replicate
CHORUS gate A16** plus the nine other production records, excluding the separate n=1
clean re-canary: 12 records, matching E2's 12 v8 + 12 v10 batch when AI_READI's
comparator is the new no-crate v8 run (D64, item 14). Under its fallback (b), the
confirmatory sets are 9 + 9, and AI_READI's records form a descriptive stratum (item
12). Under P4b's scope, the set
is the in-scope projects' cells: CHORUS alone gives 3 + 3, and a descoped project is
out of scope, not a missing cell.

### Metrics

Classified as D02 classifies them:
- **Primary deterministic metrics:**
  - populated leaves in the full record (`receipts.populated_leaves`);
  - recall-target counts under cue sha256 `768a26a3…` and tools pattern `4726c005…`
    (`scripts/recall_target_baseline.py`'s counters, applied to Set A directly;
    prediction 3 defines the lineage and VOICE version targets);
  - receipt coverage with exact record/receipt snapshots and instrument identities
    (item 3a); the D37 acceptance ratio and pre-completion comparison are distinct;
  - #2932 replicate structure (`replicate_structure.compare_structure` and
    `summarize`);
  - validation, duplicate keys and report findings.
- **Review-pass predictions:** #2930's unsupported-claim and adverse-slot rates,
  measured with the D24 instrument in E2 (item 16). D64 adopts their roster and rule
  (P4 items 21–22); the instrument itself is P4b's (P4 item 40). They are not deterministic
  metrics.
- **Secondary:** rubric scores, from one joint re-rating (E5).
- **Reported, not predicted:** the seven D21 defect metrics (item 9).

## 2a. VOICE_PEDIATRIC and Kids First (descriptive)

- **VOICE_PEDIATRIC.**
  - Its own prefix, under the A15 floor, on absolute floors only (A18-reg). No arm
    has a comparator.
  - "Pooled with VOICE as one cluster" (D02) means it is reported in the VOICE
    section of every table, as its own row beside VOICE's v10 cells. It is never
    counted as a VOICE replicate and never enters a VOICE verdict.
  - Its bundle is `03502237` (P1).
- **Kids First** ([pending D15]: the plan recommends API first, after A14-acc and once
  A15 exists):
  - generated with **the neutral profile and `vocabulary: {}`**, under its own
    curator-written `omission_context_v1`, as a one-row roster under the registered
    floor (A19-reg);
  - its frozen chunk manifest is re-validated first (A19-reg's `d4d bundle chunk …
    --check --strict`);
  - accepted through A11 and an A12 review **under the neutral profile** (A19-acc);
  - **evaluated only after acceptance, with `--profile neutral`** (A19-acc, #1541),
    with #4104 fixed before any outward HTML.

  Its bundle (541,184 bytes) is now the largest of the six projects (P1), which
  matters for item 14.

## 3. Analysis sets and the rules for n=1 and n=3 (P2 item 3; D02 decided by D64)

**Why the two arms need one rule (reviews H2 and N1).** Gates and retries filter the
two arms differently:
- v10 replicates are gated on the registered coverage floor and the receipt floors
  (D21(b)), and the batch stops on invalid output.
- The v8 comparator was not gated the same way. Only its rep1 records passed a canary
  gate, in three projects after earlier attempts that were not retained. Its rep2 and
  rep3 are an ungated fill (`805e6ac7b`, #1049).
- Four of the 12 v8 records fail today's "snippets unverified" floor (P1): CHORUS `04f`
  rep2 (2), CHORUS `04f` rep3 (1), AI_READI `04g` rep2 (1) and CM4AI `04g` rep3 (1).
- Three v8 rep1 cells also hold earlier attempts that left full records (P1, "v8
  attempts per comparator cell"):
  - VOICE `04d` and `04e`, and AI_READI `04f` rep1, under the comparator's prompt pin
    (`506af01b…`);
  - CM4AI `04`, `04b` and `04c`, under an earlier pin (`06666c4d…`).

**Set A: which records each arm contributes (D64, item 15).** Either of two
definitions applies one rule to both arms. The v8 figures are P1's, recomputed.

| definition | v8 records | v10 records | v8 pooled coverage (CHORUS / VOICE / AI_READI / CM4AI) | v8 mean populated leaves |
|---|---|---|---|---|
| (1) every attempt in a comparator cell, under the arm's prompt pin, that left a full record | the 12, plus VOICE `04d`, `04e` and AI_READI `04f` rep1: 15. CM4AI `04`–`04c` (the earlier pin) enter only a sensitivity row: 18 | every attempt in a confirmatory cell that left an eligible full record (at most 2 per cell under D07, a D21 continuation included) | 0.340 / 0.462 / 0.491 / 0.688 (0.682 in the sensitivity row) | 254.7 / 393.0 / 505.5 / 458.0 (447.2) |
| (2) one record per cell: the cell's last attempt that left an eligible full record | the 12 | each confirmatory cell's last attempt that left an eligible full record | 0.340 / 0.592 / 0.538 / 0.688 | 254.7 / 371.7 / 499.7 / 458.0 |

The recall targets move as well. Under (1), VOICE variables average 5.20 (4.00 under
(2)) and VOICE lineage 0.80 (1.00), and AI_READI variables 19.50 (17.67) (P1).

**Definition (2) is primary for the directional rules, with (1) reported beside it as
a sensitivity row (D64, item 15).** The reasons:
- **Equal cell weights.** A cell retried more often does not count more. The v8 VOICE
  rep1 cell holds 3 attempts and CM4AI rep1 holds 4, while a v10 cell holds at most 2,
  a D21 continuation included.
- **It is D02's comparator exactly** (the 12), and it matches E2's batch of one record
  per cell.
- **v8's earlier attempts ran a different package.** They were made while the v8
  package was still being changed: VOICE `04f` rep1 "passed under the final package"
  (commit `251b4ddc3`) after `04d` and `04e` regressed. So pooling v8 attempts mixes
  package states, while every v10 attempt runs the one frozen package (D17).

**What (2) costs.** v8 rep1 is survivor-selected: each was retained after passing a
gate, as late as the fourth attempt, so it has no intention-to-treat counterpart. A
v10 cell gets at most two attempts. This asymmetry stays a stated confound (item 4);
definition (1) shows how large it is from the other side.

**Cells, attempts and eligible records (D64, items 15–16).**
- **A cell** is (arm, project, replicate position). A registration declares the
  positions it fills, and so does a D21 continuation registration, so a replicate
  index means the same cell across prefixes. The re-canary and each pilot are cells of
  their own.
- **An attempt** is one billed launch of a registration for a cell. A cell has at most
  two, counted across every prefix and registration (item 7).
- **An eligible full record** is fixed by a completion event, not by a file's
  existence. The runner writes phase 1's record to the final path
  (`claudecode_api/<label>/<P>_d4d.yaml`), and reconcile and repair overwrite it in
  place, so after an early stop that path still holds the phase-1 record. Each phase
  also writes a snapshot, `intermediate/<P>_<phase>.yaml`, whose sha256 the run's
  snapshot index records.
  - **The event:** `reconcile_full` completed. The runner deletes its progress file
    when a run finishes without validation problems, so the event is established by
    a witness that survives:
    - **a run that finished** (it wrote its provenance record): the record's
      `intermediates` list holds `<P>_reconcile_full.yaml` with its sha256,
      `generation_id` and `usage_id`, and that `usage_id` names a `reconcile_full`
      row of the same record's `api_usage`;
    - **a run that stopped** (no provenance record from its end): its progress file,
      which a stopped run keeps, lists `reconcile_full` as completed, and the run's
      snapshot index holds the matching `<P>_reconcile_full.yaml`. A reconcile
      snapshot without that progress entry does not count: the snapshot is written
      before the progress update, so the phase may not have completed.

    The A21 registration's review confirms that the composed runner writes these
    witnesses.
  - **The record:** the last full-record snapshot written at or after that event,
    either `<P>_reconcile_full.yaml` or, if repair ran, its last round's
    `<P>_repair_full_r<N>.yaml`, identified by the sha256 in the provenance record's
    `intermediates` or, for a stopped run, in the snapshot index. A repair interrupted
    before writing its snapshot leaves the previous one eligible. A report or regate
    that failed after reconcile does not change which record is eligible.
  - **A run with neither witness has no eligible full record.** Its phase-1 record is
    kept and reported, but it is artifact-missing for Set A.
  - A record that fails schema validation is eligible for Set A; Set B removes it.
  - A record with duplicate mapping keys is eligible for the validation and
    duplicate-key counts only. Every metric that reads values is unmeasurable for it,
    because a YAML loader silently keeps one of the values.
  - A value whose shape a metric cannot read (a mapping where the metric expects a list
    or a scalar, say) makes that metric metric-missing for the record.
  - **The analysis manifest** lists, for each record used: label, cell, attempt, the
    completing event, the snapshot's name and its sha256.
  - This rule selects v10's records. v8's are the comparator records P1 lists with
    their sha256s.
- **Selection under definition (2)** takes the cell's last attempt that left an
  eligible full record. If a later attempt left none, the earlier record stands. No
  record is chosen by score.
- **Rows 1–3 and row 4 read different attempts of a cell, by design.** Rows 1–3, 3a and
  6–8 read the last eligible record (definition (2)); definition (1) is their
  all-attempts view. Row 4, and row 5, read the cell's first clean attempt that left an
  eligible record (item 12), because acceptance screens on exactly row 4's classes.
- **Three kinds of missing are kept apart** in every table:
  - acceptance-missing: the cell has no accepted replicate;
  - artifact-missing: the cell has no eligible full record;
  - metric-missing: the record exists, but the metric's required snapshot or block is
    absent or unmeasurable.

**Set B, common gate (D64, item 24).** Within whichever Set A
definition is chosen, these are the records of either arm that pass the same absolute
rows under one common instrument:
- validation passed, under one named schema closure per arm (the arm's own registered
  closure);
- duplicate keys 0 (`canary.duplicate_key_count`);
- exactly the five named receipt floors at 0 (item 5): chunks unreviewed, snippets
  unverified, addressing slips over tolerance, receipts vacuous and receipt findings.

The common checker is the v4 receipts checker at the launch base's pinned source hash,
run on copies of both arms' records. A row counts only if the check ran and every
counter it needs is present. `canary.receipt_floors` defaults a missing counter to
zero, so a missing counter makes the record unmeasurable for Set B, never clean. The
same helper also appends a registered-coverage row when a floor is registered; Set B
excludes that row.

The coverage floor is applied to neither arm, because v8 never had one and applying
v10's floor would select on the measured outcome. P1's v8 Set B memberships, 8 of 12
records under (2) and 9 of 15 under (1), used the stored instruments; they are
historical context until this recipe recomputes them. Set B is reported beside Set A
as a sensitivity analysis, never instead of it. Its intersections with the E2 and E5
rosters (items 12 and 16) are reported separately, because those rosters differ from
Set A. The checker's source hash, the two schema closures and the snapshot and receipt
identities it reads are bound in the P4b amendment, before any confirmatory record
exists.

**Replicate structure** (#2932, prediction 8) has an **n=3 primary estimand**:
exactly three records per compared arm/project, each cell's last eligible record
(definition (2)), with equal cell weights. If one arm supplies only two usable
records, n=3 is missing and n=2 is a separately flagged **sensitivity stratum**,
never the same estimand. Use the two common replicate positions (the cells defined
above) when both arms have them; a continuation's labels restart at rep1, so its
registration's declared positions, not its labels, give the mapping. Otherwise show
unmatched available sets and do not present a paired contrast. Do not choose a
favorable two-record subset from a complete three-record arm. Show each arm's n and
included cell IDs in every structure table. With fewer than two in either arm the
comparison is not computable, not 0.

**Rules for n=1 and n=3.**
- **Tolerances (D64, items 18–23).** D02's default was descriptive comparisons (per
  project, v10 values beside v8 values with mean ± SD and min–max), with no "v10 mean
  at or above the v8 minimum" test unless a tolerance is preregistered per metric;
  plan P2 item 3 allows either. D64 adopts a tolerance for each directional prediction
  (Predictions below), so that each can be judged true or false, and makes no row
  descriptive. The tolerances bind at the P4a word, before the first clean outcome
  under the selected production condition; prior assisted evidence is disclosed above.
  Later changes require an explicit prospective amendment and a new analysis
  stratum.
- **Verdicts** are per project. A prediction's overall statement is "holds in k of K
  confirmatory projects". There is no inferential significance test at n=3.
  Prediction 4 alone retains a descriptive claim/leaf-weighted pooled decision rule,
  with the fixed-weight sensitivity in item 16; it is not a per-project or
  independent-replicate significance claim.
- **K (D64, item 17)** counts the in-scope projects (P4b) whose
  contrast is like-for-like:
  - CHORUS, CM4AI and VOICE count when in scope.
  - AI_READI counts only under comparator option (d), and only after a render diff
    shows that its new v8-condition run differs from the v8 records in the bundle
    alone.
  - Under options (a) and (c), AI_READI's contrast crosses the with-crate boundary or
    the runtime, provider and effort, so it is a labelled separate row and not in K.
    Under (b) it is descriptive.
  - So with every project in scope, K is 3, or 4 under (d). With CHORUS alone in scope,
    K is 1 and the scope rule's single-project wording applies.
- **Missing data (D64, item 16).** A primary directional
  verdict for a project needs:
  - complete n=3 in each arm under Set A definition (2);
  - every snapshot and block the metric requires, measured.

  Otherwise the project's row is descriptive, shows n and the cell IDs, and counts as
  "not measured" in "k of K". A missing snapshot is never replaced by another
  snapshot, and it never shrinks a pooled denominator silently. A rule that needs
  every record (prediction 3a) is "not measured" when a required record is absent;
  it never passes on an empty set.
- **n=1 cells** (the re-canary, pilots, VOICE_PEDIATRIC ×1, Kids First) are
  descriptive only.

## 3a. Receipt snapshots, instruments and coverage estimands

Generation retains **receipt checker v4** and the versioned D37 snapshot gate.
Receipt v5 is **shadow/explicit opt-in only** until a separately reviewed
registration amendment selects it on every participating generation, provenance
readback and evaluation route. Local R_V5 fixes establish offline behavior, not
activation or scientific equivalence. v5 affirmative coverage accepts only
`SUPPORT`/`PARTIAL` and verified source-bound tools; `NEUTRAL`, `REFUTE` and
`NO_EVIDENCE` remain diagnostics without affirmative credit. Record the checker
version, complete instrument string and code identity alongside every metric.
D37 intentionally preserves the old v4 instrument string, so that string alone
cannot identify the measurement: require its snapshot fields and checker/source
hash, with executable round-trip readback on the selected route.

Let `O` be the immutable phase-1 original record, `R0` its receipt before the
completion turn, `R1` the preserved effective phase-1 receipt after that turn
(or `R0` if no turn), and `F` the final full record with final effective receipt
`Rf` after any declared rereceipt. Bind all available snapshots by SHA-256;
“at receipt” is the record snapshot, not the time the checker is rerun.

| Quantity | Record and receipt | Numerator / denominator; selected checker | Use |
|---|---|---|---|
| Pre-completion coverage | `O`, `R0` | `receipt_completion.before.slots.with_receipt / receipt_completion.before.slots.receiptable`, checked with v4 and `original=O` | Prediction 2; unavailable snapshots are missing, never replaced with post-turn or final values |
| D37 at-receipt coverage | `O`, `R1`; when a final check also receives `F`, its snapshot counters still evaluate `O` | `slots.with_receipt_at_receipt / slots.receiptable_at_receipt`, v4 D37 | Primary registered acceptance floor; original unreceipted values removed later still remain in the denominator |
| Final-record coverage | `F`, `Rf`, retaining `O` separately | `slots.with_receipt / slots.receiptable`, v4 | Descriptive final-record coverage, with additions/removals and rereceipt effects separately shown |
| Completion gain | Same `O` and denominator for checks with `R0` and `R1` | `(covered(O,R1) − covered(O,R0)) / receiptable(O)`, v4; also report the integer difference and newly covered/lost leaf IDs | Attributable to the receipt turn's measured attestation change, not to record removal or schema change |
| v5 shadow quantities | Identical explicit snapshot pairs as above | Same named counters with instrument version 5 and its changed polarity/tool semantics | Separate columns/strata only; never substituted for the v4 primary gate or pooled as the same instrument |

The primary D37 acceptance reading freezes `R1` at receipt completion; it does
not substitute a later `Rf` after seeing final results. If a registered rereceipt
route legitimately updates phase-1 attestation, publish that additional reading
with its receipt hash/timestamp and declared acceptance rule, alongside the
unchanged `O,R1` baseline. A final readback must make this receipt choice explicit.

For zero denominators the ratio is undefined/unmeasurable, never 0 or a perfect
score. Report numerator, denominator and unavailable counts, not only percentages.
Retiring audit rows or deleting unreceipted leaves **does not improve source
coverage**: preserve original leaf IDs and lost coverage beside final ratios.
Literal/tool verification checks source location and computation; it is not
semantic support. Copying text intact does not automatically justify `exactMatch`
or a `none` disposition. Fast entailment diagnostics are not adjudicated truth.

Historical v8 retains its original v3 check blocks. Where the exact historical
record, receipt, manifests, schema and sources exist, recompute both conditions
under one explicitly pinned checker on copies and publish that common-instrument
view alongside stored values. Do not invent missing v8 phase-1 or pre-turn
snapshots. If only final-v8 versus pre-completion-v10 is available, label that
timing/instrument contrast as such; it does not estimate an isolated completion
effect. Report-claims v7/v8 and optional watermark-aware v9 likewise remain named
instruments. Rubric changes require their own version and evaluation registration.

## 4. Confounds (P2 item 4)

Every one of these differs between v8 and the v10 API arm at once, so all effects are
package-level (plan risk 21, D02):
- **Prompt:** the generic_v10 text against `d4d_generic_arm_prompt_v8.md`.
- **Harness:** API renderer 25 plus explicitly selected BC1 versus v8's four-phase
  runner; native renderer 26 is a separate declared procedure, not BC1 parity.
  BC1 staged concern/decision carry changes later evidence exposure, and D59 sets
  what schema each call sees (item 14).
- **Coverage timing.** Prediction 2 uses v10's pre-completion figure and names its
  checker separately from the D37 gate (item 3a). It is on the phase-1 record,
  before audit, reconcile and repair. v8's stored figure is on the final record,
  where reconcile and repair had added leaves that have no receipt route (49 of 4094 in
  v8; P1). That residual difference stays a confound.
- **Schema:** 2.0.0 against 3.0.0, and the change in the digest's term source.
  - P1: no v8 record's schema digest re-renders under today's renderer.
  - `d4d runs check` reproduces all 19 digest texts from historical code, but that
    does not attest the consumed implementation or profile.
- **Caps:** historical v8 caps versus D28's selected stage/report caps and BC1's
  separately disclosed implementation delta (items 14–15); thinking and visible
  output consume different bounds and must both be reported.
- **Thinking display:** v10 sends `display: summarized` (D06). v8 declared adaptive
  thinking with no display (the plan's D06: "as v8 and v9 did"). The v8 records
  predate the `model.thinking_requested` field, so this rests on the plan, not on the
  records.
- **AI_READI input arm:** under the owner's 2026-10-14 ruling, the AI_READI v8
  records are with-crate results; v10 reads `1a58ad7b`, without the crate (item 2;
  #5042). P1 found the other three projects' bundles byte-identical; verify those
  identities again in the selected registration rather than assume no later edit.
- **Gating and selection asymmetry:**
  - v8 rep1 records each survived a canary gate. In three projects, earlier canaries
    were not retained: CM4AI (`04`, `04b`, `04c`), VOICE (`04d`, `04e`) and AI_READI
    (`04f` rep1, which passed and was later found invalid). CHORUS had none.
  - v8 rep2 and rep3 were never gated.
  - v10 replicates are gated under D21(b).
  - Item 3's Set A definitions and Set B bound this asymmetry but do not remove it.
    Under definition (2), v8 rep1's survivorship has no counterpart.
- **Check instruments:**
  - **Grounding:** the v8 grounding blocks declare no instrument, while v10's will
    carry v1 (#4090). That affects "ungrounded identifiers" and "resolver URLs" (P1).
  - **Report claims:** v8's stored `report_claims` blocks are instrument v7. The
    v10 baseline is v8 (D64, item 18); watermark checks require separately selected
    v9, never a silent expansion of v7/v8. Recomputed under v8, the 12 v8
    records change in one place: CHORUS rep3 gains one finding (P1).
  - **Form:** current on both sides.
- **The recall rule and the newly exposed Software keys.** #2930's reopen comment of
  2026-10-13 requires the API comparison to "retain the documented confound between the
  recall rule and newly exposed Software keys". Recall-target rises in software counts
  are read with that confound.
- **Transport and provider:** both arms run CBORG `claude-opus-5`. Provider-side
  model drift under one model id cannot be excluded, so v10 records the returned
  model identity per call (plan G4).
- **Effort:** a declared confound. The API arm runs at the provider default (D09), as v8
  did (each v8 record's `unverified` entry; P1). Any Claude Code cell runs at an
  explicit level/account chosen under D29 before its native registration.
- **Repository state:** `repo.dirty` will read true on every v10 run, because run
  inputs and outputs are untracked. It read true on all 12 v8 records too, across
  four commits and six distinct dirty states (P1). Launch cleanliness is defined as
  `git status --porcelain --untracked-files=no` plus an allowlist of output paths.

The coordination prompt names four compounded factors: prompt, model, harness and
AI_READI bundle scope. The list above is the plan's fuller list, plus the gating and
instrument asymmetries the review found. "Model" here means provider-side drift under
one model id plus the thinking display, since the model id is the same.

## 5. Pilot acceptance rows (P2 item 5)

The D28/D37 clean CHORUS re-canary registers **19/20 on the phase-1 snapshot**.
The builder default remains `pending`; a pilot deliberately registered with that
default has an **UNMEASURABLE** coverage gate, not an automatic acceptance. Record
the exact basis and status; never interpret a pending gate as the decided 19/20.
The remaining rows apply separately.

Each row must be 0, or hold, and A11 records each:
1. **The five receipt floors** of `canary.receipt_floors`, all from `d4d receipts check
   --method claudecode_api --label <label> --project <P>`:
   - chunks unreviewed;
   - snippets unverified (mismatched plus unchecked);
   - addressing slips over tolerance (#891: up to ceil(verified snippets / 200) are
     tolerated);
   - receipts vacuous;
   - receipt findings.
2. **Validation passed** for the full and core records.
3. **Duplicate keys:** 0 in the full record and 0 in the core (`canary.duplicate_key_count`).
4. **Report totals (#4766):** the report's stated finding total and severity subtotals
   equal `audit_counts` of the run's `intermediate/{P}_audit.json`. The stated
   values, the computed values and any mismatch are all recorded.
5. **Full-phase cap (API):** every `full` row in `api_usage`, and
   `model.max_tokens_by_phase.full`, read 128000.
6. **Provider (API):** `model.provider` reads 'LBL CBORG (proxy to Anthropic)' and
   `model.base_url` reads `https://api.cborg.lbl.gov`.
7. **Clean run (D64, item 11):** item 7's clean-run checks all
   hold. A run that fails any of them is assisted: evidence only, never accepted.

**Native rows.** Every row above is written for the API arm. The native canary's
acceptance rows are not specified here; they are deferred to a dated native amendment
of this plan, reviewed and ratified before the native launch (P4 item 43).

**Recorded, not gated:**
- item 3a's coverage fractions and snapshot/denominators **other than the
  registered D37 ratio**, which is gated as specified above;
- per-call transport and empty-answer outcomes;
- #2926's items, from its acceptance criteria:
  - `never_receipted` before and after the receipt-completion turn;
  - receipts added by the turn;
  - unsupported paths, each as an integer;
  - the attestation diagnostics (`no_value_overlap`, `unattesting`,
    `entry_single_leaf`) for turn-added receipts, reported separately from the rest;
  - the audit finding counts;
  - the turn's added cost.

**The `--canary-baseline` comparison** (item 9) is recorded in the canary block and
passed to A13 as evidence. **(D64, item 30):** a pilot is not rejected
for exceeding v8's per-project worst on the seven metrics. For AI_READI that holds
under every option of item 2. The grounding rows cross instruments (item 4).

## 6. Acceptance-record format (P2 item 6)

An acceptance record, written at A13, is a dated file committed in the run's data PR.
It carries:
- **Verdict:** accept or reject, and for a rejection the classified cause (item 10's
  criteria).
- **Identities:** the registration sha256, the roster sha256, and the sha256 of every
  artifact A11 confirms on disk.
- **Check rows:** each item-5 row, with its value.
- **Clean-run checks:** the journal verification, the override list (empty), the
  journal heads printed at launch and at each stop against the monitor record, the
  interrupted-write check, and the check that nothing in the run directory was edited
  (item 7).
- **Coverage:** as a fraction with its denominator.
- **Cost:** at that day's prices.
- **Reviewers:** references to the A12 blind source review and its reviewers, named
  under D36, never the generating session.
- **Disagreements (D64, item 11):** each reviewer's finding and
  disposition, kept separately. The owner adjudicates any disagreement before
  signing. A rejecting-class finding that the owner sustains rejects the record;
  evidence that stays unresolved blocks acceptance.
- **What the run does not establish:** for a pilot, one project, n=1, no load test
  and no recall test.

## 7. Attempt accounting, canonical marks and missing cells (P2 item 7; D07 decided)

- **Every attempt is retained**, stopped and rejected ones included, with its
  usage/termination evidence. Item 1 gives the two success proportions: one over every
  attempt that started without assistance, and one over the attempts that stayed
  clean. The pre-P4 assisted 10-20a/10-22a stay in their own engineering table. Which
  clean attempts enter Set A follows item 3's definition.
- **A clean run (D64, item 11)** passes every one of these
  checks, and any other run is assisted:
  - the D41 latch journal verifies;
  - no override is recorded (D56);
  - the journal heads printed at launch and at each stop match the monitor record
    (D57);
  - no write was interrupted (the #5212 re-review, R3: recovering an interrupted write
    needs an override, which makes the run assisted);
  - nothing in the run directory was edited (D41, D53).
- **Attempt bound:** at most 2 billed attempts per cell (D07; cells are defined in item
  3), for example a pilot plus one contingency, or a replicate plus one D21 re-run.
  The count covers every prefix and registration: a new registration under D56 does
  not reset it. Then the owner reviews.
- **Pilots, the re-canary included,** are analysed separately, never as replicates
  (D03, decided by D64, item 29).
- **No replicate is chosen by score.**
- **Canonical marks are never used as the estimate.** Estimates use every record in
  the analysis set.
- **Canonical marks** (A20) go only to accepted replicates, and pilots are never
  candidates. [proposed; owner fixes before the first canonical mark, P4 item 42]: the
  accepted cells and their record hashes are listed from the acceptance records first,
  and the criterion below ranks only within that list. They use `d4d runs select
  --method claudecode_api --project P --config <prefix>`, with `--execute` only on the
  owner's word.

  The criterion is the current code's at `0a1132ecf`, in place since `0169f1feb`
  (#835): "full and core both validate against the current schema, then most slots,
  then lowest label" (`cli/runs.py`).
  - Review counts are reported but neither gate nor rank, and `--review-margin` is
    retired.
  - The sort is by most slots, then lowest label (`cli/runs.py:1810-1811`), so rep1
    wins any tie it is part of, and only those.
  - The four v8 canonical marks P1 shows were made under the earlier, retired
    criterion (`reviews_applied: true`, `review_margin: 2`).

  If the launch base's criterion differs, the launch base's text is the one that
  applies, and this item is amended before P4.
- **Missing cells (D64, item 16).** An in-scope
  confirmatory cell with no accepted replicate after its D07 attempts is a missing
  cell:
  - It is reported explicitly in every table (E6's "explicit missing cells"), with
    item 3's kind of missing: acceptance, artifact or metric.
  - It is never imputed, and never filled from another prefix except as a recorded
    D21 continuation that declares the cell.
  - Its attempts' eligible records still enter Set A where they exist.
  - A project without complete n=3 gets a descriptive comparison showing n and the
    cell IDs, not a primary verdict (item 3's missing-data rule).
  - Structure's primary estimand needs n=3 per arm. n=2 is only the flagged
    sensitivity stratum of item 3; fewer than 2 is not computable, never 0.
  - A project with no primary verdict in a set is counted as "not measured" in "k of
    K" for that set.
- **Out of scope is not missing.** A project P4b leaves out of scope has no cells. It
  is listed as "out of scope (P4b)", and it is not in K (scope rule).
- **Cells split across prefixes:** a cell that D21 splits across prefixes cannot be
  grouped by `d4d runs select --config`. It is marked by a recorded procedure or left
  unmarked (A20; a G4 gap).

## 8. Production-floor decision (P2 item 8; D37 basis decided, D20 rule decided by D64, value at A15)

D37 fixes the snapshot basis. D28 fixes 19/20 for the clean CHORUS re-canary only,
and the builder default is pending. D20 is decided by D64 (item 28), as the
generation plan recommended ("Commit the rule in P2 before the pilots run, and
register the value at A15"): the rule is fixed before any pilot runs, and A15 only
computes its value. The rule never depends on a pilot's outcome.

**The rule (D20, decided by D64, item 28):**

> The registered receipt-coverage floor is the lowest of the eligible pilots' D37
> at-receipt coverage fractions, `with_receipt_at_receipt / receiptable_at_receipt`,
> rounded down to a multiple of 1/20 and capped at 19/20.

- **Eligible pilots.** The A21 re-canary (in plan A10's role) and, if AI_READI is in
  scope, the AI_READI pilot (plan A14). A pilot is eligible only if A13 accepted it.
  Its fraction is read from the accepted attempt's frozen `O,R1` snapshot (item 3a);
  a rejected or assisted attempt never supplies one. A pilot cell has at most one
  accepted attempt, since a contingency runs only after a non-acceptance.
- **The cap at 19/20.** Receipt completion drives the D37 ratio towards 1: both
  assisted canaries read 58/58 and 64/64. Without the cap, two perfect pilots would
  register a floor of 1.00. A production record with hundreds of receiptable leaves
  would then fail on one unreceipted phase-1 leaf, and under D21 that one stop closes
  the roster. With the cap, production's floor is never stricter than the
  re-canary's. The cap removes the 100% requirement; it does not make a roster immune
  to one lost receipt (with 19 receiptable leaves, 18/19 is below 19/20).
- **Arithmetic.** Exact integers: `floor(20 × with_receipt_at_receipt /
  receiptable_at_receipt) / 20`, then the minimum with 19/20.
- **The branch, declared now** (staged sequence, step 8). If P4b puts AI_READI in
  scope, its pilot runs and is accepted before A15, and the floor is the lower of the
  two pilots' values. If AI_READI is out of scope, or leaves it because its pilot ended
  without acceptance for a cause that is not rule-level, the re-canary's fraction alone
  sets the value under the same rule. Under the cap that value is always 19/20, since
  an accepted re-canary has passed its own 19/20 gate. So the AI_READI pilot can only
  lower the floor, and only the AI_READI branch makes the floor depend on a pilot.
- **No value.** If a pilot the branch still requires has no accepted attempt, or has a
  zero denominator, the rule yields no value. No production roster registers until a prospective
  amendment, reviewed as P3 was, supplies one. No other observed ratio is substituted.

D64 chose this rule over three alternatives (P4 item 28): no cap, which can register
20/20; the lowest fraction minus 0.05; and 19/20 fixed for all production, which would
have taken the AI_READI pilot off the floor's path. It also chose the re-canary-only
fallback over having no value until an amendment.

**At A15** the value is computed under the rule and registered in a dated amendment PR
that gets P3's review (a Claude reviewer plus a Codex CLI pass) before the owner
merges it. A15 checks the arithmetic and the inputs; it does not revisit the rule.
That amendment creates a new registration identity and does not certify the pilots.
A floor failure stops the roster without discarding records.

For scale, from P1's per-record coverage:
- A 0.6 floor would fail 8 of the 12 v8 records: all three CHORUS (0.290, 0.335,
  0.394), VOICE rep2 and rep3 (0.540, 0.576), AI_READI rep1 and rep2 (0.583, 0.388)
  and CM4AI rep3 (0.581).
- This matches #2926's statement.
- The receipt floors alone fail 4 of the 12 v8 records today (item 3).
- v8 stored coverage is final-record coverage without a receipt-completion turn;
  it is historical context, not a same-snapshot comparator for the D37 floor.

## 9. Gating and continuation of production rosters (P2 item 9; D21 decided by D64)

D64 adopts D21's option (b) with continuation (ii) (item 35).

**Production rosters** gate on absolute floors only, with no `--canary-baseline`:
- the registered coverage floor, the five receipt floors and duplicate keys gate
  every run;
- a blind check stops the roster as UNMEASURABLE;
- the seven defect metrics are reported but never gated.

**Pilots** keep `--canary-baseline`:
- CHORUS (A21, in plan A10's role): `2026-09-04f_claude-opus-5-api-generic-v8`;
- AI_READI (A14-reg): `2026-09-04g_claude-opus-5-api-generic-v8` as planned, under
  option (a). Under (b) the pilot runs with no baseline, and under (c) and (d) as item
  2 says. It is never `04f`, because that prefix's AI_READI rep1 is declared
  invalid.

The v8 per-project worst values, recomputed in P1. The AI_READI row is with-crate.

| project | report findings | British spellings | pair errors, ungrounded identifiers, resolver URLs, organisational fragments, undeclared prefixes |
|---|---|---|---|
| CHORUS | 2 | 0 | 0 |
| VOICE | 1 | 2 | 0 |
| AI_READI | 1 | 0 | 0 |
| CM4AI | 0 | 0 | 0 |

**Continuation after any stop:**
- a stopped label is never re-run;
- the owner classifies the stop by item 10's criteria;
- the remaining cells run under a new date-letter prefix, with new registrations, a
  new roster, a review and an owner word naming the new roster sha256, every
  registration sha256 it lists, and the cap;
- every attempt is counted within D07's bound (item 7).

**Trigger (A15) (D64, item 36):** if either pilot had a terminal single-delivery
failure, the owner decides at A15 between two courses:
- continue the unchanged procedure under (b), with new registrations;
- if the failure shows the condition is infeasible, move to the next shared-generation
  version with one recorded retry. That is a condition boundary for both arms and ends
  this generic_v10 API matrix.

Building D21's option (c) is not one of them: D64 did not choose it (item 36), and in
any later condition it would need its own reviewed, prospective analysis amendment and
procedure stratum.

**The A15 choice is part of the analysis (D64, item 36).** A change of procedure would
change which calls and cells complete and how many attempts survive, and so which
records enter every metric; D35's parity test and diagnostic canary show that the
engineering is sound, not that a changed selection process has the same estimand. So
the procedure does not change: eligible remaining attempts run under new registrations
and a new prefix, within each cell's two attempts, and no run that stopped on a
terminal or control-state discrepancy is revived (D56). Set A and Set B keep item 3's
definitions, and the choice and its basis are recorded in the A15 amendment before
any multi-row roster.

**A transport redelivery adopted after A21** (D64, item 4) is a procedure change of the
same kind. It needs its own reviewed, prospective analysis amendment before any
production registration; it then applies to every production cell, so production has
one procedure; and A21 stays a separate descriptive record. D35's parity test and
diagnostic canary are needed too, but they are engineering evidence, not that
amendment. A cost-only scope amendment (P4b) cannot adopt it.

**No adopted "< 0.55" trigger.** The October 20 review found that threshold in
its delegation rather than the governing plan; its repository search is historical
evidence, not a fresh exhaustive absence claim. This draft does not adopt it.
Any numerical trigger needs an explicit owner decision before P4.

## 10. Caps, triggers, stop-loss and stop classification (P2 item 10; D07 and D58 decided)

### The re-canary's allocation

- **The cap is D58's $60 A21 slice.** D28's earlier slice of about $25 is superseded.
  The historical D07 allocation stays in the spending record, but it is spent: $35.76
  settled ($41.79 worst-case reserved) against D07's $30 CHORUS lines, with 2 of 2
  attempts used (decision record §5.1.1). It is not evidence of remaining funds. The
  launch packet carries the reconciled ledger, the $60 cap and the owner's word (D07,
  D22).
- **One attempt, no contingency (D64, item 3).** A21 is one funded attempt at $60. A
  fixed-BC1 CHORUS run is estimated at about $37 expected and $49 at caps
  ("Feasibility under D58"), so $60 funds one attempt and no contingency. D07's two
  billed attempts per cell are a ceiling, not funding. A contingency (plan A10c) needs
  its own allocation line, a new registration (D56) and its own owner word.
- **No production money.** P4a funds nothing beyond A21. The matrix's budget is P4b's
  decision (D58).

### Operator trigger (D64, item 5)

The trigger is the cap minus the largest worst case of any call that can still be
pending. The launch packet computes it from the bounds the runtime enforces, not from a
sizing scenario.
- **What the runtime enforces.** BC1's admission holds each typed call to its context
  room (936,000 input tokens beside a 64,000-token reservation), the registered
  per-call limit and the aggregate allowance (`bc1_runtime` at `8f83d6cb3`). #5157 holds
  each report-family call to `count_tokens + max_tokens ≤ 1,000,000`. D62's figure,
  every CHORUS call at or below 0.85 of its room, is a sizing result, not an enforced
  ceiling.
- **Worst cases at those bounds,** with all input priced as cache writes ($6.25 per
  million) and output at $25 per million:
  - a typed call, 936,000 in and 64,000 out: about $7.45;
  - a full, reconcile, report or regate call, 872,000 in and 128,000 out: about $8.65.
- **So the trigger is about $51** at a $60 cap. D62's sizing would put it near $53, but
  only as an illustration.
- **The launch packet recomputes it** over every admitted call type, any calls that can
  be in flight together, unsettled usage and the dispatches that can still follow. An
  interrupted call whose usage is unknown counts at its worst case.
- **No enforced lower ceiling.** Registering and enforcing a lower per-call input
  limit would raise the trigger, at the cost of engineering and a new registration;
  D64 chose the enforced-bound trigger instead (P4 item 5).
- **The margin is thin.** A caps-heavy D59 run is estimated at about $49 before
  retries, repair and re-address, so a legitimate run can reach the trigger. A stop at
  the trigger is a budget stop (classification below), not a defect.
- The old $11.50/$15 CHORUS example is historical.

### Wall clock (D64, item 6)

The 2 h stop came from the pre-BC1 plan A10, and nothing in BC1 justifies it:
- 10-22a's uninterrupted call time was already 51 min, across 9 calls with typed inputs
  of about 139k tokens;
- a BC1 CHORUS run has about 12–13 sequential calls, with typed inputs of 0.4–0.8M
  tokens, which is about 2 h of call time at caps (P3 Claude review).

The clock is 3 h, about 1.5 times that estimate (D64, item 6), and the launch packet
re-derives it from the registered call schedule. It is never extended during a live
attempt.

### Stopping a live run

- **The command.** At the trigger or the clock, `d4d api stop --label-prefix <prefix>`
  stops the run. `--max-cost-dollars` stops only between runs (#5045). It cannot recall
  an in-flight request, and an interrupted stream may still bill (#1849).
- **Who runs it: agy (D64, item 7; the owner's own choice, not the recommendation).**
  This amends the D41 and D43 monitoring rule, under which the agents only monitored.
  For A21, agy alone may issue one command, `d4d api stop --label-prefix <prefix>`,
  when the dollar readout reaches the trigger (about $51, as the launch packet
  computes it) or the run reaches the 3 h clock. agy watches the dollar readout and
  does nothing else to the run: no other command and no edit (D53). For any later run,
  D43's rule stands unless the owner's launch word extends this authority.
- **What the monitor keeps:** the D57 journal heads printed at each start and stop,
  and the A3b readout against the trigger.

### Defect-class stop-loss and A13 (D64, item 34)

- **Pilots: A13 governs.** The first rule-level rejection of a pilot, the re-canary
  included, ends this condition and schedules the next shared-generation version for
  both arms. Nothing below permits a second rule-level pilot attempt, and neither
  assistance nor a change of label does.
- **Production: two rejections with the same root cause** end re-running in this
  condition.
  - The owner records a root-cause ID in each acceptance record. A later finding with
    the same diagnosis takes the same ID, whichever issue it is filed under, so a new
    issue cannot reset the count.
  - The count covers this API condition across every prefix and registration, and it
    never resets.
  - Rule-level causes and content slips count (D64, item 32).
- **The older D05 clause** (if both pilots are rejected for the same rule-level cause,
  the #2918 and #2919 rules enter at the next version) cannot arise once the first
  rule-level pilot rejection ends the condition, and D34 has since decided the rule
  batch. It is historical.
- **Other stops do not count.** Instrument, registration, harness, transport and budget
  stops are counted and reported separately.

### Stop and rejection classification (D64, items 31–33)

Two things are recorded for every stop or rejection, separately:
- **The record's evidence status:** clean or assisted, by item 7's checks. An assisted
  record is evidence only (D40, D53), whatever stopped the run. Assistance never
  changes the cause class, never removes a rule-level cause and never grants an
  attempt.
- **The cause:** exactly one primary class, the first row of this table that matches,
  once the evidence is in the acceptance record and the defect is filed as an issue. A
  stop may carry several diagnostic tags. The class fixes the next action.

| Precedence | Class | Test | Next action |
|---:|---|---|---|
| 1 | **instrument** | an offline recomputation shows that a gate or checker misread a record that is valid under the registered rules | The verdict is re-read once the instrument is corrected and reviewed. No generation re-run, and the attempt is not a rejection |
| 2 | **rule-level** | an A12 rejecting-class finding is sustained on anything the run wrote (the final records, an intermediate record or the report), or the final records fail validation or carry duplicate keys (item 5, rows 2–3), whatever else stopped the run | Pilots: A13, so the condition ends. Production: counts toward the stop-loss; the cell may use its second attempt only while the stop-loss is not reached |
| 3 | **content slip** (D64, item 32) | a receipt floor or the report totals fail (item 5, rows 1 and 4), and row 2 does not match | One contingency under a new registration, within the cell's two attempts. Counts toward production's stop-loss by root cause |
| 4 | **registration or environment** | a configuration row fails (item 5, rows 5–6: the full-phase cap, the provider or base URL), or another fault of the registration or the launch environment rather than of generated content | The attempt is void. One contingency under a corrected registration, within the cell's two attempts |
| 5 | **impossible limit** (harness) | a registered limit no valid answer can meet | No contingency under the same limits. The limits are corrected and reviewed first, and the corrected registration is a new condition identity |
| 6 | **record shape** (harness) | receipt completion's validation refused the phase-1 record for a value of the wrong cardinality or type for its slot: a shape the write-time normaliser does not fix, which the repair call (run only after the phase loop) never had the chance to fix | One contingency under a new registration, within the cell's two attempts. If it is refused for the same shape, the fix is engineering, landing only by D17's procedure or at the next version |
| 7 | **transport** | the terminal call's `api_usage` row records a transport error or a dropped stream, or the provider returned an HTTP error | One contingency under a new registration, within the cell's two attempts |
| 8 | **budget or clock** | the run was stopped at the trigger or the clock | One contingency under a new registration, with a new allocation line and word, within the cell's two attempts |
| 9 | **unknown** | nothing above matches | Held for the owner's adjudication before any retry, then reclassified. No contingency until then |

Rules that go with the table:
- **A content defect outranks every operational class.** A sustained rejecting-class
  finding in a report, followed by a dropped stream, is rule-level. A harness,
  transport or registration label never exempts a substantive rule defect.
- **Unmeasurable is not failed.** A row that could not be measured, because a check did
  not run or a counter is missing, is unmeasurable: class instrument when a checker or
  gate defect caused it, otherwise unknown.
- **An assisted run that completed** leaves its cell without a clean record. The cell
  may take a new attempt only by the owner's decision, under a new registration and
  within its two attempts, and only if no rule-level cause was found.
- **Two attempts per cell, counted across prefixes and registrations.** A new
  registration under D56 does not reset the count; the cell (items 3 and 7) carries
  it.
- **D56 applies to every class.** No class continues a run past a terminal or
  control-state discrepancy, and every retry is a new registration.
- **A13's "transport or operational cause"** is read as rows 3, 4 and 6–8 (D64, item
  33): they allow one contingency. An impossible-limit stop does not, since a
  contingency under the same limits would reproduce it.

Historical examples of the two harness classes are in the appendix (B).

### Single-delivery exposure

- BC1's typed calls and receipt completion each admit exactly one delivery
  (`transport_attempts=1`).
- A21 has 8 such calls. At v8's per-call rate (8 retried calls in 92, P1), with
  independence assumed, that is an illustrative 52% terminal-stop exposure from all
  causes, and 36% from transport alone. The per-project table is under "Feasibility
  under D58".
- The plan's earlier four-, six- and eight-call figures describe the pre-BC1
  single-integrator design. They are not carried into BC1 budgets or predictions.
- Content failures stay terminal under D56. D64 accepts single delivery for A21 and
  decides after A21 whether production gets one transport-only redelivery per typed
  call, through a reviewed analysis amendment (item 9) and a diagnostic canary (D64, item
  4). It would be new engineering.
- Observed stage rates and their uncertainty are reported in item 18. The independence
  illustration is not a measured failure forecast, and it does not choose a favorable
  tolerance.

## 11. Freeze (P2 item 11; D35 decided)

D35 freezes from the rebuilt A21 re-canary registration on merged main, after
board A17 (#5211), #5155 and #5157. Later runner changes require a CHORUS byte-parity
test and one separately authorized diagnostic canary before remaining runs
re-register. Every registration pins the full and core schema closures, the bundle,
the chunk manifest and the source manifest.

Frozen are:
- schema releases (#3972, #3124);
- the draft PR #4508 (#4489);
- #2914 path A;
- source-manifest edits (#3414, decided before A4 or held);
- preprocessing changes (#2934);
- API runtime changes;
- any #4354 merge that touches the API path.

The launch worktree stays at its pinned base. Advances occur only between stages,
with no run live, under D35 and a new reviewed registration. BC1 is a model-access
condition change under D44; integrate and review it before A21 rather than
silently treating assisted-canary results as tests of the rebuilt condition.

## 12. Blinding and reviewers (P2 item 12; D36 decided)

D36 selects a fresh Claude blind source-review session plus a Codex CLI pass;
neither generated nor operated the run. The owner signs each acceptance record.
Record reviewer identities and independence for acceptance and comparison; this
engineering revision is not the owner's scientific sign-off.

**Acceptance review (A12)** is blind source review of the unchanged originals against
the frozen bundle. It covers #1782, #1801/#2924, #1815, #1816 and #2924 dates.
Under D34, #2918 and #2919 are measured by existing lints and reported in E2/E6;
no new rule batch enters v10. A12 never involves the generating
session, and it is not the comparison.

**Comparison batch (E2)** is separate from acceptance. Its roster is D64's (item 21);
its instrument and reviewers are P4b's (P4 item 40, open):
- **The v10 roster is taken before acceptance:** each in-scope confirmatory cell's
  first clean attempt that left an eligible full record, accepted or not.
  - An A12 rejection never removes a record from E2.
  - Why: acceptance rejects any record with a finding in #1782, #1801/#2924, #1815 or
    #1816, which are exactly the classes prediction 4 counts. An accepted-only roster
    would make "v10 ≤ v8" close to true by construction, or block the verdict through
    a missing cell.
  - The accepted final records are reported as a sensitivity analysis. Extra reviews
    arise only where a cell needed a second attempt.
- **The v8 roster** is the in-scope projects' comparator records; for AI_READI, see
  item 2. With every project in scope that is 12 + 12 records, or 9 + 9 under option
  (b).
- **Blinding.** A deterministic transformation with a recorded seed copies the
  records, removes labels, provenance and the `#` header, and shuffles them (#3280).
  What it cannot remove is listed: schema 2.0.0 and 3.0.0 records differ visibly. Each
  reviewer records a guess of the arm before scoring, and the guesses are reported.
- **Reviewers:** a named pair chosen at P4b (P4 item 40). D36 names the acceptance
  reviewers, not E2's. Neither E2 reviewer generated or operated a run under review.
  Each review is dated and bound to the record sha256.
- **The protocol is frozen before any confirmatory outcome** (item 16): at P4b at the
  latest, before any confirmatory roster's launch word.
- E2 runs after plan A17-acc, or after the last in-scope acceptance. No v8 record has
  yet been reviewed under the #1782–#1816 protocol.

Under D36, a second blind model reviewer writes audit-recall observations against
the SHA-256 of `original_full` before anyone reads the audit. This seeds #2921;
unresolved human annotation/matching decisions remain explicit before scoring.

**Joint re-rating (E5)** is one billed rating pass of the v8 and v10 records together,
on the E1 route:
- CBORG selected explicitly, refusing a session whose init line does not read
  `apiKeySource: ANTHROPIC_API_KEY`;
- contexts pinned by hash;
- the instrument version named (rubric10 3.0; rubric20 3.0 or 4.0 per E4, **[pending
  owner, #2911]**), and with it the evaluator implementation that D52 and D61 change
  (rubric10 E2.2, rubric20 Q9). The choice is made at P4b, before the first
  confirmatory launch (D64, item 26; P4 item 41). E5's later registration binds only
  execution details under that choice; it never switches the instrument for records
  already generated. A version label alone does not identify the
  instrument: an unmodified historical 3.0 is not the D52/D61 instrument. Old scores
  are not rewritten. Prediction 5's items, Q11 and Q19, are not among those D52/D61
  change;
- preamble and check-echo (#1077);
- a rubric20 repeat panel (#2912);
- every output validated with `validate_evaluation_schema.py --file`, exit 0.

E5 needs its own registration, review and owner word. D22's withdrawal means no
standing authorization covers it.

**The rating workload is not the analysis roster (D64, items 21 and 23).** E5b-reg rates every accepted generic_v10 API-route record, the v8
comparators and a repeat panel. Prediction 5 reads a narrower roster:
- exactly one primary rating per record of E2's v8 and v10 rosters above, the v10
  roster taken before acceptance. E5b-reg must add any such record it would not
  otherwise rate (a generation-plan amendment);
- excluded from prediction 5's means: the re-canary and the pilots, with-crate
  records, native rows, historical calibration records (such as CM4AI v7 rep2) and
  repeat-panel copies;
- repeat ratings are reliability evidence only.

D64 chose this over keeping E5's accepted-only roster (item 21).

The native CHORUS canary is not automatically included in the API/v8 E2 or E5
batch. If accepted, rate it only through a separately declared descriptive
native-arm stratum: same selected rubric/context bytes, independent blind source
review and exact-file validation, with generation runtime/tool/exposure
differences retained. Other native cells are unplanned and receive no invented
rating rows. #5126's historical-comparator authority route, the separate native
rating authority adapter and any rubric amendment must be settled for the
participating strata before ratings; route engineering does not authorize them.
The atomic-claim protocol belongs to §16 and to D24 (P4b, item 40), not #5126.

## 13. Labels and launches (P2 item 13)

- One distinct date-letter prefix per roster.
- `generic-v10` as a delimited label token.
- No `pilot` or `canary` word in any label.
- Outputs are copied, never moved, into data PRs, so the #795 guard keeps passing.
  The launch worktree is never fast-forwarded over those data PRs except by D17's
  procedure.
- A stopped label is never re-run.
- Every **API-arm** generic_v10 launch, continuations included, goes through `d4d api
  batch` with a roster, never `d4d api run` (D20 and D21, decided by D64, items 28 and
  35). `d4d api run` has no floor verdict, canary block, run lock or #795 guard.
- Native launches use Track N's registered command/recorder path and first-party
  authentication; they never go through the API batch route. D29 and the native
  real-binary/probe/acceptance gates remain separate prerequisites.
- Immediately before every billed launch, the operator (under D43, the owner) hashes
  the roster, every registration it lists and the launcher script, and stops on any
  difference from the sha256s named in the word and the review (A10).

## 14. Selected condition, bounded carry and model-visible identity

The design label **`shared-generation-api-v2-bc1`** names the scientific
condition. It is **not** the installed `shared_generation_version` or an accepted
registration. D64 (item 9) names the installed tuple: shared generation 1 plus
`bounded_carry_version` 1, with this label kept as a design label only. BC1's
implementation lineage:
- **`3bd3c41f4`:** the reviewed BC1 implementation, contract and hook proposal.
- **`8dd00263a`** (`origin/claude/bc1-bounded-carry`): the hook applied. **It is
  superseded, and it does not fit.** BC1's fit analysis (§1) found that no typed call
  fits for any project as built. Each request carried about 3.5 MB of schema catalogs:
  the full catalog twice, a core catalog and per-slot `domain_of` lists. BC1's schema
  block also replaced the A14 digest downstream, which pushed those calls over 1M.
- **`8f83d6cb3`** (`codex/wave5-bc1-d59-20261028`): D59's request shape. Its review
  found that shape exactly implemented on the real wire, D60 holding, and CHORUS
  fitting per call (the largest call at 0.70 of its room at 2.48 bytes per token). It
  is not merge-ready:
  - F1: its fit gate made the escaped bound a hard requirement (settled by D62);
  - F2: it sized integration requests at the response ratio (settled by D62);
  - F3: its CLI sizing route refuses a completed run;
  - F4: BC1 carries 43 test failures and 46 errors that pass on main (present since
    `8dd00263a`).
- **D62's gate packet** is in progress on `codex/wave5-bc1-gate-d62-20261028`, whose
  ref was still at `8f83d6cb3` when this revision was written. It is unreviewed.

The A21 condition is the reviewed composition of that lineage with board A14, board
A17, D38's assets and D55's guard, pinned before the A21 registration. This draft
claims no later head.

| Component | Current reviewed policy / local implementation | Registration obligation |
|---|---|---|
| Scientific assets | D30/D38 generic-v10 prompt SHA-256 `ec081dbb14049449989c56169de7bcd1563076667818c12b78571b5f15acb2db`; uniform-v2 SHA-256 `22a553695536a822e9c7ae877663a9b251c889a6637c637e579c5c6e1c855b2e` | Verify actual merged bytes and native alignment; the BC1 branch itself does not install D38 |
| Actual BC1 selection | `bounded_carry_version=1`, exact `bounded_carry` registration block; `bc1_typed_audit_v1`, parent shared generation **1**, generic_v10, API renderer **25**, playbook **2**, receipt completion **2**, direct API (as reviewed at `8dd00263a`) | Pin full contract/procedure/code/runtime identity at the composed head; shared-generation-v2 routing and native are unsupported |
| Implementation lineage | `3bd3c41f4` (hook diff SHA-256 `10cb0ff8dd77d34ec150ae9b5447a82cdeef4402a477151f220a6c02685b0cb8`) → `8dd00263a542cc2ace25242271e753c5eaade6ea` (applied; superseded, does not fit) → `8f83d6cb36ef56e6cf23684ec6bc56772e7ab8d7` (D59 shape; not merge-ready) → D62's packet (in progress) | Pin the reviewed composed head and rebuild registrations for its source identity; applied hooks establish neither request fit nor launch approval |
| Schema and source, typed calls (D59) | The full schema catalog once, without the per-slot `domain_of` lists (redundant with each class's slot list); the source bundle once; the records under audit | Pin the exact catalogs, bundle, chunk/source manifests, profile and context bytes per cell; no final composed closure or registration hash is yet claimed |
| Schema and source, other calls (D59) | Full (generation), receipt completion, reconcile, report and regate keep v10's A14 schema digest, as the two canaries had | Pin each phase's schema context. The registration also states which context the repair and report-refresh calls receive, and the wire inspection below confirms it |
| Worker/partition contract | Board A17 (#5211) splits large lists; D39 owning-root wording; D45 selects project bounds | Pin exact reviewed contract and each project's measured partition. Numeric partition metadata stays controller-only as specified below |
| Carry | `bc1_codec_v1`, `ConcernPacketV1`, `RecordDigestV1`, stage delta v1 | Pin codec/contract/source digests and each predecessor/request identity; a digest is not evidence of scientific support |
| Receipts and reports | v4 + D37 snapshot gate; v5 shadow only. Baseline report checker v8; watermark-aware v9 is a separate opt-in | Pin checker code, instrument, snapshot fields and any evaluation amendment; never silently activate new checks under old labels |
| Composition | BC1's lineage carries reviewed R9b and board A17 changes, but does **not** install board A14, D38 or D55's guard | Compose with board A14 (#5162), D38's assets and D55's guard A (#5212, after its D55 fixes and re-review), then review the composed head independently; no installed-source or campaign-readiness claim follows from isolated tests |

**What later models receive.** Every worker must review all assigned populated
values and clauses against the complete sources. Each typed call (worker, omission,
group integration and final integration) carries the full schema catalog once,
without per-slot `domain_of`, and the source bundle once (D59). Integrations consume
fixed groups of one or two new worker results plus bounded concern/decision history;
one separate final call checks cross-group consistency. Later typed stages retain
changed rows, concerns, predecessors, every explicit decision, omission candidates
and dispositions. Receipt completion, reconcile, report and regate see the records,
the source, BC1's bounded carry and the A14 digest, not the full catalog. Untouched
supporting/metadata review rows and their evidence text can be absent from those
model views. The host archives the complete worker reviews, raw deliveries and
machine audit.

This is an intentional **change in model access**, not lossless preservation of
the full review procedure. Lossless encoding of retained strings cannot ensure
that models rediscover a contradiction involving omitted supporting-row evidence.
The scientific rationale is bounded context/cost with explicit concern retention;
the tradeoff is unmeasured cross-group detection. D59 adds two smaller changes: the
typed calls lose the per-slot `domain_of` lists, which repeat each class's slot list,
and the downstream calls see the A14 digest with its trimmed slot keys, as the
canaries did, rather than the full catalog. Reconcile must inspect affected
occurrences, and the final report must review every populated final-full value
anew, including unchanged entries. These duties and acceptance/source-review
gates remain; no support judgment is inferred from successful decoding.

**Controller-only partition metadata.** Project-specific numerical bounds
(`max_paths`, inventory-byte limits, `max_workers`), calibration/cost labels and
project-profile metadata belong to the scheduler/registration record, not the
model request. Assigned paths, actual required rows, group predecessors and
scientific duties necessarily remain visible. Do not claim assignment invisibility
or assume that calling a field “scheduler-only” hides it. Before registration,
recursively inspect every captured wire request, including nested registration,
plan and carry text, and run differential renders with only controller bounds
changed. Record any intended visible difference; an unapproved bound leak blocks
the fixed model-facing contract. This draft specifies that gate, not evidence
that it has already passed for the final composition.

Across all six projects the visible protocol and byte envelopes are fixed;
project bounds are selected under D45 and independently recorded. Neutral IDs
remain neutral. Kids First uses actual neutral context with `vocabulary: {}` and
resource-level scope; it is not sized or generated by silently substituting an
AI_READI record. The omission contexts are approved as D51 (#5164), and the
evaluation-context settings were decided by the owner's human review as D52; the
retired D46 entry supplies no approval.
The historical decision note's CHORUS hash `6e3c6b6d…` was incorrect; A23
retains the actual `ac94a74b…` context bytes. Verify and pin the exact
selected artifact before registration without rewriting historical evidence.

## 15. Token caps, visible-byte bounds, call counts and input allowances

D28's decided baseline is **64,000 / 32,000 / 32,000 tokens** for worker /
omission / integration, with **128,000** for report, report regate and
reconcile-full. These caps include thinking where the route uses thinking.
The current BC1 code instead requires **64,000 for both worker and integration**,
including each group and final integration call. This is a material implementation
delta, not an alias for D28's 32k integration. D64 (item 9) adopts 64k for BC1's
integration calls as a declared amendment of D28; D58's cost basis already assumed
it. D28's original baseline is kept on record beside it.

Separate fixed visible envelopes are **98,304 worker bytes**, **131,072 integration
bytes**, **262,144 carry bytes**, and **32 open concerns**. They neither replace
the thinking-inclusive token reservations nor authorize truncation, changed
partitioning or an extra delivery after refusal. An answer must satisfy both
bounds and the existing evidence/grammar checks.

With `W` workers and registered fan-in `f` of 1 or 2, BC1 plans
`G = ceil(W/f)` group integrations plus **one separate final integration**:

- audit calls: `W + 1 omission + G + 1 final`;
- BC1 aggregate output reservation (64k integration, D64, item 9):
  `W × 64,000 + omission_cap + (G + 1) × 64,000`;
- aggregate input allowance: an explicit registered value selected from the
  actual reviewed #5155/BC1 sizing for every admitted worker, group, omission
  and final call. D49's claimed formula stays retired.
  - **CHORUS:** D62 sets `aggregate_input_tokens` to 4,500,000 for the A21
    registration. In D62's sizing, CHORUS needs about 4.06M at 2.48 bytes per token,
    with every call at or below 0.85 of its room (a sizing result, not an enforced
    per-call ceiling), and the allowance adds at most $3.13 of spend exposure.
  - **Every other project:** its allowance is a D62-style owner decision at its own
    registration. The old 4M profile cannot hold any non-CHORUS BC1 roster; in the fit
    analysis the smallest, CM4AI's, needs about 8.35M at 2.48 bytes per token, so
    each allowance is roughly 8M or more;
- generation, receipt-completion, reconcile, report/regate and permitted repair
  calls are added separately to the full-run cost and failure exposure.

“One or two” refers to **new workers per group**, not a universal two-integration
call ceiling. If that interpretation is not the intended scientific condition,
resolve it prospectively instead of reporting the implemented schedule as parity.
Aggregate allowance is a ceiling, not an estimate, a context-fit test or permission
to spend. Current #5157 admission must independently enforce actual request bytes,
provider token count plus the selected output cap, and remaining aggregate budget
before each dispatch, including resumed repair/report refresh.

**The fit gate (D62) and the calibration (D63).**
- The A21 gate checks two scenarios: the floor, and the visible caps with the
  measured 1.25× escape factor. The escaped bound (full caps, every byte escaped 4×)
  is recorded and not gated.
- Request bytes are sized at 2.48 bytes per token, and future-response bytes at 1.75.
- Before the A21 registration, D63's single `count_tokens` call measures the ratio on
  one fixed D59 CHORUS worker request, and the measured ratio replaces 2.48. Every
  token figure in this draft that rests on 2.48 is provisional until then.
- In the scenarios the D59 review inspected, a mid-run refusal arises only in the
  doubly pessimistic one, a per-call failure that no allowance fixes (its §4). Sampled
  byte ratios and response proxies do not exhaust the possible refusals, so runtime
  admission remains the guard.

**Fit evidence, and when it is needed (D64, item 10).**
- **Before A21 (D44, D58):** BC1 is built and reviewed for all six projects under D59.
  Per-call fit is shown for every project from its own sources, schema closure and
  context, at the floor and the caps scenario, through the real planner and formatter.
  VOICE_PEDIATRIC and Kids First have no record of their own. For them the proxy
  record and its margin are declared, and the result is labelled proxy fit, not actual
  fit. D59 expects Kids First's integration at caps to be borderline. CHORUS's full
  fit under D62, and D63's calibration, precede the A21 registration.
- **At each other project's registration:** its own aggregate allowance (a D62-style
  owner decision) and its sizing from its own inputs. Runtime admission (#5157, and
  BC1's per-call count) still refuses any request that does not fit, before it bills.
  Kids First is never sized or cleared by substituting an AI_READI record.
- **P4a does not wait** for sizing that needs records which do not yet exist.

For each project, record worker and group counts, complete source and schema bytes,
carry and omission sizes, billing assumptions (no cache breakpoint, D60), input and
output reservations, and cost and failure exposure per stage. K1 v2 is calibrated
engineering evidence from the two assisted canary ledgers; later responses and
receipt decisions remain unknown. Bytes/token proxies and hypothetical empty/cap
responses are not provider counts or guarantees that all six campaigns fit.

Keep Lane C1 `notes/a1_offline_sizing_2026-10-20.md` at `0d45c1ec8` (SHA-256
`9df27d8e77a24aed80aa3bc206a32fa94755781f80e8474bd496f6102832b4e3`) as historical
engineering evidence: its 4k workers, G5/S7 recommendation, 96k reports and 4M
aggregate limit explain the redesign. They are **superseded registration values**,
not current prescriptions. Likewise the #5072 oversized-row PASS defect is not
launch evidence. D44 holds A21 until all-project design/build/review; any remaining
actual fit failure holds its dependent launch rather than being hidden in a proxy.

## 16. Instrument for the review-pass predictions (P2 item 16; [pending D24])

D24 recommends option 1 **[pending D24: P4b, item 40]**. Row 4's weighting, pools and
verdicts below are decided by D64 (item 22). The units, exclusions and adjudication
rules are this draft's proposal for P4b's protocol (P4 item 40), not yet a ratified
protocol.

**What is frozen, and when (D64, item 26; the content is P4b's, P4 item 40).** These
determine the denominators and the rejecting classes, so they are frozen before any
confirmatory outcome exists: at P4b, before any confirmatory roster's launch word.
"Before E2" would be after the v10 outcomes exist. The list below is this draft's
proposal for that content [proposed; owner fixes at P4b, item 40]:
- the annotation manual, with its eligibility list (the record-metadata fields, empty
  values and nonassertive headings excluded below, named field by field);
- the splitting and dedup rules, and the leaf convention for a scalar list (each
  populated list item is one leaf at its indexed path);
- the adjudication procedure: each reviewer's disposition is kept; disagreements are
  adjudicated by the owner before arm unblinding; a unit still unresolved after that
  is "unresolved" (below);
- the blinding transformation and its seed (item 12), and the reviewers' model,
  settings and session isolation.

Its author is named and declares which v10 records they have read; the disclosed
assisted canaries and the re-canary are the only v10 records available before P4b.
Per-record inventories are built later, blind, under the frozen algorithm, and sealed
before support is adjudicated.

**What the two rates measure.** They count only the rejecting classes below, so they
are **rejecting-class** rates, not rates of every unsupported factual claim. A
fabricated quantity outside these classes is recorded in E2's findings, but it is not
in these rates. The rates of #2930 use the rejecting classes:

- #1782: plans stated as current, and scope;
- #1801 and #2924: roster roles;
- #1815: attribution;
- #1816: qualifiers and headers.

**Semantic units and exclusions.** For the unsupported-claim rate, a unit is one
distinct atomic factual assertion in one record, identified by referent, predicate,
value, temporal/release scope and qualification. Attach every occurrence path.
Split conjunctions into independently verifiable assertions using the same blind
manual in both arms; do not split one assertion because it fails more than one
rejecting class. Repeated wording or paraphrases of the same assertion within a
record count once, even at several paths; retain all occurrences for audit. The
same claim in a different replicate is a different record-level observation.
Different scope/time/qualification makes a distinct claim. Record-metadata-only
fields, empty/unpopulated values and nonassertive headings are excluded using a
frozen explicit eligibility list, not an outcome-dependent decision. Both
affirmative and source-checkable negative factual assertions are eligible.

For the adverse-slot rate, the unit is a unique eligible populated scalar leaf
path in the record. A leaf is adverse if any of its adjudicated assertions falls
in a rejecting class; count that leaf once even if several clauses/classes fail.
Its denominator is the assessed eligible leaf count, not the number of claims or
the full schema's possible slots. These two rates therefore have different units.

Publish supported, rejected, unresolved/unassessed and excluded counts, with
reasons and an immutable claim-to-occurrence/leaf map. Unresolved/unassessed units
are never silently deemed supported or treated as zero. The primary E2 verdict
requires complete adjudication of the frozen eligible inventory; otherwise mark
the affected rate unmeasurable and show a clearly labelled assessed-only
descriptive rate. New splitting/dedup rules require a versioned amendment applied
equally to both arms, not a post-result favorable denominator.

A missing record or project from the fixed E2 roster also blocks the primary
pooled verdict; an available-record pool is descriptive only, even if every
remaining claim was adjudicated. A zero assessed-claim denominator `C=0` or
assessed-leaf denominator `L=0` is unmeasurable, never zero error or a perfect
score. Preserve the missing/zero-denominator row and do not silently redistribute
its project weight.

**Weighting.** For record r/project p/arm a, let `U_apr` be rejected atomic claims
and `C_apr` assessed eligible atomic claims; `A_apr` and `L_apr` are adverse and
assessed eligible leaves. Prediction 4 retains its original **zero-tolerance**
directional rule, evaluated separately for the two rates as two verdicts, **4a**
(claims) and **4b** (leaves) (D64, item 22). Row 4 as a whole
is reported as "4a holds, 4b holds" or as each one's verdict; neither is folded into
the other:

- claim-weighted pool: `sum(U_apr) / sum(C_apr)` over the fixed E2 record roster
  (item 12: in-scope cells, v10 taken before acceptance);
- leaf-weighted pool: `sum(A_apr) / sum(L_apr)` over that same roster;
- project-specific rates: the corresponding ratios summed only within p,
  displayed for every project with record n and both denominators;
- equal-project-weight sensitivity: arithmetic mean of the project-specific
  rates across the **same predeclared K projects**, each weighted `1/K` in both
  arms. It is not recomputed by silently dropping a missing project; report that
  sensitivity unmeasurable and any available-project result separately.

Every assessed claim or leaf gets weight 1 in its pool, so projects and records
with more assessed units receive more weight. A lower pooled rate is **not** a
claim that every project improved, nor an equal-project effect. Publish these
weights, per-project rates and the fixed-weight sensitivity even when they
disagree with the pool. **The primary pool (D64, item 22)**
is over the in-scope projects in K, whatever their number. Under AI_READI comparator
options (a) and (c), AI_READI is outside K: the pool excluding it decides 4a and 4b
(three projects at full scope), and AI_READI is an explicit **AI_READI cross-arm** row
(with-crate v8 / no-crate v10 under (a); runtime, provider and effort as well under
(c)). A combined pool that includes AI_READI may be shown, labelled as mixed input-arm
evidence, but it decides nothing. Do not relabel it as a homogeneous runtime/package
effect.

The support judge remains excluded from these predictions until #3343 is
calibrated under its own registration and word. Literal receipts, tool checks,
BC1 row retirement and rubric scores do not determine E2 semantic verdicts.

**Recorded deviations from #2930's wording:**
- #2930 says "in the review pass". The instrument is the E2 batch instead, because
  the d4d-review-record pass did not meet its calibration criterion (#835).
- #2930 predicts "against v9". The comparator is v8 instead (D02), because v9 is a
  single CHORUS canary.

## 17. The D04 path (P2 item 17; D04 decided by D64)

D64 keeps the crate path out of this matrix (item 37): neither path A nor path B runs
in this condition, and a monolithic API baseline (D16) is out of it as well. A later
with-crate stage needs its own specification, fit, budget, review and word. For the
record, path B would have used the CHORUS context unchanged (release null), so that
the two arms differ only in their bundles; passed no `--canary-baseline`, because the
baseline reader searches no crate directory; and analysed the with-crate cells as
their own stage, never pooled into the confirmatory set.

The owner's 2026-10-14 ruling, that crates belong only to the with-crate and
crate-only arms, is what makes AI_READI's v8 records with-crate (item 2).

## 18. Per-stage transport and empty-answer rates (P2 item 18)

**What is measured.** For every billed v10 call, from `api_usage` and the typed-stage
records:
- the stage: full, typed worker, omission, integration, receipt completion, report,
  regate or repair;
- transport errors;
- answers that ended `end_turn` and were rejected;
- terminal single-delivery failures.

**How it is reported.** Descriptively, per stage and per project, beside v8's per-call
rates from P1: 5 transport errors and 3 answer-level retries in 92 calls. v8 has no
typed stages or receipt completion, so those stages have no v8 rate.

**Whether D06's display changed the rates.** That cannot be tested within this
condition: every v10 call carries the display, and every v8 call carried none, so a
difference is part of the package effect (item 4). It is reported as such, never
attributed to the display.

## Predictions

Each prediction names its metric, comparator, decision rule and instrument, to be
fixed at P4 before clean outcomes from the selected production condition. **Every rule
is decided by D64** (items 18–23). The values the assisted
canaries showed on these metrics are disclosed above ("Known v10 values on the
predicted metrics"), and the P4 record should say they were in view.

**Notation:**
- For project p, `v8_p` and `v10_p` are each arm's values in Set A, under the
  definition item 3 settles. Rows 1–3, 3a and 6–8 read Set A. Row 4 reads E2's
  roster and row 5 reads E5's analysis roster (item 12): the in-scope confirmatory
  cells, with the v10 records taken before acceptance.
- "Holds in k of K" counts the projects whose rule holds. K is item 3's: the in-scope
  projects whose contrast is like-for-like. A project without complete n=3 is "not
  measured" (item 3).
- Set B results are reported beside every row, as a sensitivity analysis; for rows 4
  and 5, Set B's intersection with that row's roster.

For AI_READI, each row is judged under the comparator option chosen in item 2. Under
(a) and (c) it is a labelled separate row outside K (item 3).

| # | prediction (from #2930, restated against v8 per D02) | metric and instrument | decision rule (D64) | v8 values (P1) |
|---|---|---|---|---|
| 1 | Populated leaves fall by no more than 10% (a non-inferiority reading of #2930's "do not fall") | `len(receipts.populated_leaves(full))` per eligible full record, `receipts.py` at P1's pin `7bfb8470…` | holds for p if mean(v10_p) ≥ 0.9 × mean(v8_p); equality passes. v8's replicate SDs are 21.7 (CHORUS), 43.9 (AI_READI), 31.3 (CM4AI) and 68.6 (VOICE) leaves, so 10% of the v8 mean is 1.2, 1.1, 1.5 and 0.5 SD respectively | AI_READI [525, 525, 449], CHORUS [235, 278, 251], CM4AI [422, 473, 479], VOICE [386, 297, 432] |
| 2 | Receipt coverage does not fall, measured pre-completion | **v10:** v4 `receipt_completion.before.slots.with_receipt / receipt_completion.before.slots.receiptable` on `O,R0` (item 3a). **v8, primary:** the stored v3 final-record `receipts.slots.with_receipt / receipts.slots.receiptable` values in the last column. **v8, sensitivity:** a named common-checker recomputation where exact inputs exist. **Pooled** means the sum of the numerators over the sum of the denominators, across the project's Set A records. Pin source/checker identities; do not infer parity from the unchanged v4 string. | holds for p if pooled pre-completion v10 coverage ≥ pooled v8 coverage − 0.05 absolute. **The numerator is reported beside every ratio.** If the ratio holds while v10's pooled receipted-leaf count is below v8's, the result is reported as "ratio held with a smaller record", never as improved coverage, and it is read with row 1. Every required snapshot must be present (item 3): a missing pre-turn snapshot is never 0, never replaced by a post-turn value, and never dropped silently from the pool. Final-v8 versus phase-1-v10 remains a timing/instrument contrast. D37 at-receipt gate coverage, final coverage and completion gain are separately reported, never substituted into this rule. | pooled, under item 3's definition (2), receipted / receiptable: CHORUS 215/632 = 0.340, VOICE 584/986 = 0.592, AI_READI 694/1289 = 0.538, CM4AI 817/1187 = 0.688. Under (1): VOICE 0.462, AI_READI 0.491 (P1) |
| 3 | The recall rule raises recall where the bundle states the targets | The pure counters of `scripts/recall_target_baseline.py` (cues `768a26a3…`, tools `4726c005…`), applied directly to item 3's Set A roster. Not through the script's `collect()`, which skips records whose validation failed, and not through its default arm list, which stops at v9. D02's targets:<br>- AI_READI variables 20/13/20;<br>- CM4AI lexical candidates 9/5/3;<br>- VOICE variables 4/4/4, lineage 1/1/1, lexical candidates 3/0/1, b2aiprep v3.0.0 in `used_software`/`tools` 0/0/0;<br>- CHORUS lineage 1/1/0.<br>**Lineage (D64, item 20)** is a top-level presence indicator: 1 if the record's top-level `was_derived_from` holds at least one populated entry, whatever its type or number of entries, else 0. It does not rely on the schema's single-valued declaration, which Set A's invalid records may break. The script's `target_counts` instead counts lineage entries at every depth, and nested objects can carry `was_derived_from`. On all 12 v8 records and both assisted records the two agree (no nested or multiple lineage occurs; recomputed for this revision), so the v8 values do not change.<br>**VOICE's version target (D64, item 20)** is the fact-specific carriage measure for `voice-b2aiprep-3.0.0` in `notes/recall_target_baseline.md` ("used_software/tools" column, with that note's matching rules). It replaces "tools with a version token", which counts any version-shaped token in `tools`, so a wrong version can raise it; that count stays reported as a lexical carriage proxy. The v8 records carry b2aiprep v3.0.0 elsewhere in all three.<br>**The adapter** that applies these counters to Set A is a script pinned by sha256 in the P4b amendment, before any confirmatory record exists; on the 12 v8 records it must reproduce this row's v8 values.<br>These are carriage counts, not support or recall accuracy. | **Counts the rule should raise** (variables, lineage, b2aiprep carried): holds for a target if mean(v10_p) > mean(v8_p); a tie fails.<br>**Targets at their ceiling, enumerated now:** only VOICE lineage. The presence indicator is at most 1 by construction, and every v8 VOICE replicate is at 1. That target holds if mean(v10_p) ≥ mean(v8_p). No other target gets a ceiling exception after the outcomes.<br>**Lexical candidates**, which should fall as cue chunks are extracted rather than set aside: holds if mean(v10_p) < mean(v8_p).<br>**Combination:** a project's row-3 verdict holds if every target listed for it holds, and "holds in k of K" then counts projects.<br>AI_READI's v8 counts were taken over the with-crate chunking (P1) | as listed |
| 3a | A rise is an error where the bundle states nothing | Same counts, read against the #3289 adjudication in `notes/recall_target_baseline.md`:<br>- no parent dataset in any of the four bundles;<br>- no processing-software version in the AI_READI, CHORUS or CM4AI bundles (CM4AI's versions belong to companion analyses);<br>- VOICE's one stated version is b2aiprep v3.0.0.<br>The adjudication read AI_READI's pre-#5042 bundle, when it still had its RO-Crate, which recorded FAIRSCAPE 1.2.1 as the metadata packager, not processing software. It is re-read against `1a58ad7b` before P4. | holds if every confirmatory v10 record has `parent_datasets` 0; for AI_READI, CHORUS and CM4AI, `used_software` with a version 0; and for VOICE, no versioned `used_software` entry other than b2aiprep v3.0.0, the one processing-software version the adjudication found in VOICE's bundle. Any non-zero instance means it does not hold, and each instance is listed. If a required record is absent, the row is "not measured" for that project; it never passes on an empty set (item 3) | 0 today |
| 4 | The rejecting-class unsupported-claim and adverse-slot rates do not rise (a review-pass prediction) | item 16's atomic-claim and eligible-leaf units, exclusions, dedup/splitting and complete-adjudication rules, as P4b fixes them (P4 item 40) before any confirmatory outcome; E2's roster with the v10 records taken before acceptance (item 12) | **Exception to per-project verdicts:** claim-weighted and leaf-weighted E2 pools over the projects in K, not Set A attempts. Two verdicts: **4a** holds if v10's claim rate ≤ v8's, and **4b** if v10's leaf rate ≤ v8's; zero tolerance, ties hold, and neither is folded into the other. Always show project-specific rates and equal-project-weight sensitivity. Under AI_READI options (a) and (c), AI_READI is outside K: the pool over the in-scope projects in K decides (three at full scope), and AI_READI is a separate cross-arm row (item 16). The accepted-final records are a sensitivity row. Missing/unassessed units do not create a passing verdict. | no adopted E2 annotation result asserted here; measured after protocol/roster freeze |
| 5 | Rubric20 Q11 and Q19 do not fall (secondary) | E5 joint re-rating, instrument version per E4 with the D52/D61 evaluator identity (item 12); one primary rating per record of E5's analysis roster; repeat-panel ratings are reliability evidence only | Two verdicts: **5a** (Q11) holds for p if mean(v10_p) ≥ mean(v8_p) − 0.5 on the item's scale as the selected instrument defines it, and **5b** (Q19) likewise; equality passes, and a project's row-5 label is "holds" only if both do. A rating the instrument scores N/A, or a record with no usable primary rating for an item, is metric-missing for it (item 3). No pilot, re-canary, with-crate, native or calibration record enters these means | measured in E5 |
| 6 | **Not a prediction: an acceptance invariant.** Validation passes with 0 duplicate keys | `validation.passed` and `canary.duplicate_key_count` | true by construction for accepted v10 records, since the batch stops on invalid output and duplicate keys gate. Set A reports the count of v10 attempts whose output failed either, descriptively | 12/12 passed, 0 duplicate keys |
| 7 | **Descriptive, no direction:** report findings | `report_claims.findings` | reported per record and per project in both sets. Reasons:<br>- the counts cross instrument versions: v8's stored blocks are v7, and new runs are checked under v8;<br>- renderer 25's report carries the typed audit's finding totals (#4766), which v8's report did not;<br>- v8's values are 0–2 per record.<br>A directional rule would be decided by noise, as D21 argues against its option (a) | worst, stored v7 and recomputed under v8 alike: CHORUS 2, VOICE 1, AI_READI 1, CM4AI 0. Under v8, CHORUS rep3 goes from 0 to 1 (P1) |
| 8 | **Descriptive, no direction:** replicate structure (#2932) | `replicate_structure` per project: all/some/none, identical, nested counts differ, max/min ≥ 2, intermittent slots | **n=3 primary**, each cell's last eligible record (item 3); n=2 only a separately flagged sensitivity on common replicate positions, n and IDs in every table; fewer than 2 is not computable (items 3/7). D34 says #3336 is in v10 and CHORUS ×3 measures it; that is not empirical proof of a directional structure effect. | P1 section "Replicate structure"; intermittent AI_READI 8, CHORUS 14, CM4AI 17, VOICE 9 |

Rows 1–5 are directional and decidable, rows 6–8 are not predictions, and every
rule is decided by D64 (items 18–23). Leaves and coverage read #2930's "do not fall" with
stated margins: 10% of v8's mean leaves, and 0.05 of pooled coverage.
Recall is "rises where the bundle states the target, and is never invented where it
does not" (3, 3a). Structure and report findings are descriptive, for the stated
reasons.

## Open before P4

### Before the P4a word

The owner's P4a answers (D64) are applied in this text. What remains before the owner
gives the P4a word, naming this file's final sha256 (D64, item 12):

- **P3 closure.** Every P3 finding, and every finding of the verification round on
  `1ed9bb1ef`, is fixed here or converted to an item below; each is filed as an issue;
  and this revision gets its re-review. The dispositions are in
  `d4d-executions/plans/reviews/p2_p3_dispositions_2026-10-28.md`, and the P4a packet,
  with the owner's answers, is `d4d-executions/plans/p4a_decision_packet_2026-10-28.md`.
- **The condition's specification (§14–15),** as P4a ratifies it. The composed head
  (with board A14, board A17, D38's assets and D55's guard), D44's all-project build
  and review, D62's CHORUS fit and D63's calibration are prerequisites of the A21
  registration (staged sequence, step 3), not of P4a. That registration's review checks
  the composed head against the ratified text, and a deviation needs a P4a amendment.
- **The #3289 adjudication,** re-read against AI_READI's `1a58ad7b` bundle
  (prediction 3a).
- **Context and evaluation identities.** The omission contexts are approved (D51) and
  the evaluation-context settings decided (D52); D46 is retired. The D52/D61 scoring
  rules need their implementation merged before scoring, and the selected hashes and
  per-route readback need verification. Preserve A23's current normalized context
  digests when integrating the decision-record correction. Native canary ratings
  remain separately registered and descriptive.

### Plan amendments (claude prepares them under D50; agy pushes them)

This draft does not edit the generation plan. The amendments below go in one PR,
reviewed as P3 was and ratified with P4a; those marked P4b are ratified with P4b. Each
lands before the first registration it affects, and the generation plan's own P4 gate
stands: the ratified plan is merged on main before any registration hash is put to the
owner.
- the `d22b61a9` gates in A4 and A14-reg, and the run tables (§2): before A4;
- D15's and A19-word's "about the size of AI_READI's 542,513" (Kids First's bundle is
  541,184 bytes): before A19-reg (P4b);
- A19-reg's "vocabulary null", which should read `vocabulary: {}` (§2a): before A19-reg
  (P4b);
- D07's AI_READI lines (a $35 planning ceiling and a contingency of at most $35), which a
  D59 AI_READI run, at about $162–191, exceeds: before plan A14-reg (P4b);
- A1's sizing inputs, which do not include Kids First and are superseded by BC1's fit
  analysis (§15): before the A21 registration;
- the staged sequence: plan A10's role, which the re-canary fills with a registered
  19/20 floor, before the A21 registration; plan A14's conditional start and plan A15's
  branch (§8), and E5b-reg's roster (§12), with P4b;
- the wording of P4 itself (the header): with P4a.

### P4 agenda

**How to read it.** There are 43 items, in the order the answers are needed. Items
1–37 are answered: the owner's P4a answers, recorded as D64 (2026-10-28), follow each
item, and the body states the resulting rules. Items 38–43 are open.
- **Each item** gives the question, the options, this draft's recommendation with its
  consequence, the latest point at which it can be decided, and its dependencies. The
  rule itself is in the section cited ("§N" is this file's item N; "item N" inside
  this agenda is an agenda item).
- **Latest decision.** Items 1–37 were decided at P4a (D64), before A21, because A21
  or a later run is their first relevant outcome. Items 38–41 are decided at P4b, before
  any production registration. Items 42–43 come later, at the stage named. Deciding a
  rule is distinct from producing what it governs: a floor's value, a manifest or a
  manual can come later under a rule fixed now.
- **Sources** in brackets: the Claude P3 review's agenda (A1–D3), findings (F) and
  re-review (N); the Codex pass's questions (Q01–Q50), findings (F) and verification
  (V).
- **Recommendations are this draft's; the answers are the owner's** (D64). Where the
  reviews differ, the item says so. Already decided and not asked again: D06, D07, D10, D22, D26–D28,
  D30–D45 and D50–D63. D46–D49 stay retired.

#### Group A. P4a: the A21 condition and its operation (answered, D64)

**1. What P4a ratifies** · the staged sequence · latest P4a · [Claude F2, A1; Codex F1, Q01, V3]
- **Question:** While D58 holds the matrix's scope and budget until A21's cost is
  measured, what does the P4 word before A21 ratify?
- **Options:** (a) the staged sequence: this text, every rule whose first relevant
  outcome is A21 or later, and the latest-decision points of this agenda, with P4b
  applying them; (b) A21 as a feasibility study only, with any comparison registered
  later as a new prospective study; (c) hold everything until a funded full matrix is
  approved, which amends D58.
- **Recommended:** (a). A21 can run under D58, and no later choice can follow a
  quality outcome. *Depends on:* nothing. Every other item assumes (a).
- **Answer (D64):** (a), as recommended.

**2. The scope rule** · "Scope rule" · latest P4a; applied at P4b · [Claude F2, A1; Codex Q01]
- **Question:** Which rule turns D58's later scope decision into K, the confirmatory
  set and the rosters?
- **Options:** (i) the predeclared order CHORUS ×3 → CM4AI ×3 → VOICE ×3 → AI_READI
  (pilot + ×3) → VOICE_PEDIATRIC ×1 → Kids First ×1, whole projects only, on cost, fit
  and call-failure evidence, priced per accepted record, with a descoped project out
  of scope rather than missing; (ii) the owner's discretion at P4b within the same
  limits; (iii) as (i), in another predeclared order.
- **Recommended:** (i). At the $420 figure it stops after CHORUS ×3, so K would be 1.
  *Depends on:* item 1 and D58's budget.
- **Answer (D64):** (i), as recommended.

**3. A21's attempts, and what follows an A21 that is not accepted** · §10; staged sequence, step 5 · latest P4a · [Claude F1, A2, N5; Codex F3, Q19]
- **Question:** Does D58's $60 fund one attempt or two, and what happens after an A21
  that stops or is assisted?
- **Options:** (i) one attempt; a contingency needs its own allocation, registration
  and word, and P4b waits for it unless the owner scopes on a packet labelled partial;
  (ii) raise the slice to about $120 to pre-fund one contingency; (iii) one attempt,
  with P4b proceeding on whatever packet exists.
- **Recommended:** (i). (ii) commits money before the measured cost D58 waits for, and
  (iii) can scope the matrix on a packet missing most stages. *Depends on:* D58, items
  4 and 8.
- **Answer (D64):** (i), as recommended: A21 is one funded attempt at $60.

**4. Single-delivery exposure: allow a transport-only redelivery, or accept it** · "Feasibility under D58"; §9; §10 · latest P4a · [Claude F14, N6; Codex V3]
- **Question:** BC1's typed calls and receipt completion admit one delivery each.
  Allow one transport-only redelivery per typed call, or accept the exposure?
- **Options:** (i) accept it for A21 and production; (ii) build the redelivery before
  A21, so that A21 runs the production procedure; (iii) accept it for A21, and adopt
  it for production only through a reviewed prospective analysis amendment (§9), with
  D35's parity test and diagnostic canary.
- **What holds under every option:** a redelivery is new engineering; it re-sends the
  same request after a transport error only; content failures stay terminal (D56). At
  v8's per-call rate, the chance of complete n=3 rises with it from 39% to 82% for
  CHORUS and from 9% to 56% for CM4AI.
- **Recommended:** (iii): measure A21 first. Adopting it later costs an amendment and
  a diagnostic canary (about $37–49). (ii) delays A21 but has it test the production
  procedure; (i) leaves most non-CHORUS verdicts likely unmeasured. *Depends on:*
  items 3, 8 and 16; D35.
- **Answer (D64):** (iii), as recommended: single delivery for A21; production's
  redelivery is decided after A21, through a reviewed analysis amendment and a
  diagnostic canary.

**5. The operator trigger** · §10 · latest P4a · [Claude F1, A3; Codex F3, Q19, V4]
- **Question:** At what spend is A21 stopped?
- **Options:** (i) the cap minus the worst pending call at the bounds the runtime
  enforces, about $51 at $60, recomputed in the launch packet; (ii) register and
  enforce a lower per-call input ceiling (engineering and a new registration), which
  raises the trigger towards $53; (iii) a fixed $50.
- **Recommended:** (i). *Depends on:* D62, D63, #5157.
- **Answer (D64):** (i), as recommended.

**6. The wall clock** · §10 · latest P4a · [Claude F1, A3; Codex F3, Q20]
- **Question:** What time stop applies to A21?
- **Options:** (i) 3 h, re-derived from BC1's 12–13 calls; (ii) 2 h as a deliberate
  censoring rule, under which a timeout is a feasibility failure; (iii) 4 h; (iv) no
  clock.
- **Recommended:** (i), since 2 h would cut off a legitimate caps-heavy run. The Codex
  pass recommends (ii) unless duration evidence supports more. The clock is never
  extended during a live attempt. *Depends on:* the registered call schedule.
- **Answer (D64):** (i), 3 h, as recommended.

**7. Who runs `d4d api stop`** · §10 · latest P4a · [Claude F1, A3]
- **Question:** D43 does not say who stops a live run at the trigger or the clock. Who
  does?
- **Options:** (i) the owner; (ii) one agent the owner names, for that command only
  and only at the trigger or the clock.
- **Recommended:** (i), consistent with D41 and D43. (ii) stops faster, but makes an
  agent an operator for one action. *Depends on:* D41, D43, D53.
- **Answer (D64):** agy, for the stop command only. This is the owner's own choice,
  not the recommendation: for A21, agy alone runs `d4d api stop` at the trigger or the
  clock and does nothing else to the run, amending D41 and D43 (§10).

**8. D08: A21's written risk acceptance, and the CBORG follow-up** · "Feasibility under D58" · latest P4a for A21; before plan A16 for multi-row · [D08, decided by D64; Claude B6, F14; Codex Q34]
- **Question:** Is the prepared CBORG follow-up sent, and what gates single-row and
  multi-row runs?
- **Options:** (1) prepare the exact message for its own per-action owner approval
  (recipient, channel, text), accept the risk in writing for single-row runs now, and
  require CBORG's answer or a renewed acceptance before the first multi-row roster;
  (2) send nothing, and accept the risk in writing for everything; (3) send nothing,
  and block every roster until CBORG answers.
- **Recommended:** (1). A21's written acceptance names its 8 single-delivery calls.
  Nothing in this draft sends a message. *Depends on:* item 4.
- **Answer (D64):** (1), as recommended. The written risk acceptance is decided;
  sending the CBORG follow-up still needs the owner's separate yes.

**9. BC1's identity: label and integration reservation** · §14, §15 · latest P4a · [Claude F7, A11; Codex Q18]
- **Question:** Which identity does the registration name, and is the integration
  reservation BC1's 64k or D28's 32k?
- **Options:** (a) the installed tuple (shared generation 1 plus
  `bounded_carry_version` 1) with 64k as a declared D28 amendment; (b) the installed
  tuple with 32k, which needs a BC1 change, re-sizing and re-review; (c) a new
  shared-generation version (code changes where #5212's F1 sits), with 64k; (d)
  neither, pending a redesign.
- **Recommended:** (a). D58's cost basis already assumes 64k. *Depends on:* D55's
  composition, D62.
- **Answer (D64):** (a), as recommended.

**10. Fit evidence and the composed head** · §15; staged sequence, step 3 · latest P4a for the standard; the evidence before the A21 registration · [Claude F13, N4; Codex Q50]
- **Question:** Which fit evidence and which composed head must exist, and before
  what?
- **Options:** (a) §15's staging, with the composed head, D44's build and review,
  D62's fit and D63's calibration as prerequisites of the A21 registration, whose
  review checks them against the ratified text (a deviation needs a P4a amendment);
  (b) answer item 9 first, compose and review the head, then hold P4a; (c) hold A21
  until all six projects are sized with their own records, which cannot happen before
  two of them have records.
- **Recommended:** (a). No clean outcome comes before the registration, so nothing is
  lost by checking there. *Depends on:* D44, D58, D62, D63, item 9.
- **Answer (D64):** (a), as recommended.

**11. Acceptance mechanics** · §5 row 7, §6, §7, §3a · latest P4a · [Claude F10, A10; Codex F11, Q22, Q49, V6]
- **Question:** Which test makes a run clean, how is a disagreement between the two
  D36 reviewers settled, and which receipt reading decides acceptance?
- **Options:** (a) as written: §7's five checks applied mechanically; both reviewers'
  dispositions kept, the owner adjudicating before signing, a sustained
  rejecting-class finding rejecting and unresolved evidence blocking acceptance; v4
  with D37 on the frozen `O,R1` snapshot; (b) as (a), with the owner's judgement per
  run for cleanliness; (c) as (a), with a third blind adjudicator.
- **Recommended:** (a). Membership of every analysis set becomes mechanical, and an
  acceptance failure is never repaired by reading `Rf` or v5 instead. *Depends on:*
  D36, D37, D55–D57.
- **Answer (D64):** (a), as recommended.

**12. What performs P4** · header · latest P4a · [Claude F23, A12]
- **Question:** Which act performs P4?
- **Options:** (i) the owner's word naming this file's sha256 at a named commit,
  recorded in the decision record, with the merge following before any registration
  hash is put to the owner; (ii) the merge itself, as the generation plan words it.
- **Recommended:** (i). It binds the exact bytes, and the generation plan's merge gate
  still stands. *Depends on:* nothing.

#### Group B. P4a: the analysis rules (answered, D64)
- **Answer (D64):** (i), as recommended. The P4a word itself has not been given.

**13. D02: the comparator and the metric hierarchy** · §2 · latest P4a · [D02, decided by D64; Codex Q02]
- **Question:** Which comparator and metric hierarchy does the analysis register?
- **Options:** (a) the v8 package contrast, with the deterministic metrics primary and
  E5 secondary; (b) the v9 CHORUS canary as a descriptive reference only; (c)
  descriptive reporting only.
- **Recommended:** (a), conditional on item 2 funding a comparison. The v9 canary
  stays a secondary n=1 reference. *Depends on:* item 2.
- **Answer (D64):** (a), as recommended.

**14. D02: the AI_READI comparator, and its pilot's baseline** · §2 · latest P4a · [D02, decided by D64; Claude A5; Codex Q03, Q04]
- **Question:** Which records are AI_READI's comparator, and which baseline does its
  pilot use?
- **Options:** (a) v8 `04g`, labelled cross-arm, with the baseline informational only;
  (b) AI_READI descriptive only, its pilot running with no baseline; (c) the
  `2026-10-14b` agentic rerun, which also changes runtime, provider, transport and
  effort and needs a reviewed data PR, with P4a recording whether the pilot has no
  baseline or that prefix as an informational one; (d) a new no-crate v8 API run on
  the historical v8 code (billed, about $10–14), used only if a render diff shows that
  only the bundle differs.
- **Recommended:** (b), unless item 2 funds AI_READI; then (d) if the diff passes,
  otherwise (b). *Depends on:* item 2. It gates K, the E2 roster and the `d22b61a9`
  plan gates.
- **Answer (D64):** a new no-crate v8 run, as recommended: (d) when AI_READI is in
  scope and the render diff passes, otherwise (b).

**15. Set A and the eligible record** · §3 · latest P4a · [D02, decided by D64; Claude A6, F16, N3; Codex F5, Q05, V5]
- **Question:** Which records does each arm contribute, and what makes a record
  eligible?
- **Options:** (a) definition (2) primary and (1) as a sensitivity row, with
  eligibility fixed by the completion event and the snapshot's hash (§3); (b)
  definition (1) primary; (c) both descriptive.
- **Recommended:** (a). Cells carry equal weights, so v8 pooled coverage is 0.592 for
  VOICE and 0.538 for AI_READI; v8 rep1's survivorship stays a stated confound.
  *Depends on:* nothing.
- **Answer (D64):** (a), as recommended.

**16. Missing data, and complete n=3** · §3, §7 · latest P4a · [Claude B5, N6; Codex F5, Q06]
- **Question:** When does a project get a primary directional verdict?
- **Options:** (a) only with complete n=3 and every required snapshot; otherwise the
  row is descriptive and "not measured"; (b) n=2 may also be primary, under a
  separately fixed rule; (c) every comparison descriptive.
- **Recommended:** (a). At v8's per-call rate, complete n=3 is likely only for CHORUS
  (39%, or 82% with a redelivery; "Feasibility under D58"). *Depends on:* items 4 and
  15.
- **Answer (D64):** (a), as recommended.

**17. K** · §3 · latest P4a · [Claude F12; Codex Q29, V8]
- **Question:** Which projects count in "k of K"?
- **Options:** (i) only in-scope projects whose contrast is like-for-like: AI_READI is
  outside K under options (a), (b) and (c), and inside under (d) only after the render
  diff; (ii) AI_READI inside K under (a) and (c) as well, labelled mixed-input.
- **Recommended:** (i). *Depends on:* items 2 and 14.
- **Answer (D64):** (i), as recommended.

**18. Rows 1, 3a, 6, 7 and 8 as written** · Predictions · latest P4a · [Claude A7, F17; Codex Q25, Q28, Q31–Q33]
- **Question:** Are these five rows adopted as written?
- **Options:** (a) all as written: row 1, v10 ≥ 0.9 × v8's mean leaves; row 3a, zero
  inventions with the VOICE clause, "not measured" when a record is missing; row 6, an
  invariant with failures over all started attempts reported; rows 7 and 8,
  descriptive; (b) as (a), but row 1 at ≥ 1.00, or row 7 directional under one pinned
  checker; (c) all five descriptive.
- **Recommended:** (a). The assisted CHORUS records sat at 28–35% of v8's leaves, so
  row 1 may well fail for CHORUS, which would be a legitimate result. *Depends on:*
  item 16; for row 3a, the #3289 re-read.
- **Answer (D64):** (a), as recommended.

**19. Row 2: pre-completion coverage** · Predictions · latest P4a · [Claude A7, F6, F11; Codex Q26]
- **Question:** Which rule judges v10's pre-completion coverage against v8's stored
  final coverage?
- **Options:** (a) v10 pooled ≥ v8 pooled − 0.05, with the numerator reported, the
  smaller-record wording and the stored v8 values primary; (b) zero tolerance under
  one common checker, where the inputs can be recovered; (c) descriptive only, as a
  timing and instrument contrast.
- **Recommended:** (a). The Codex pass recommends (c). The assisted values would pass
  (a) by about 0.55, with smaller numerators. *Depends on:* items 15 and 16.
- **Answer (D64):** (a), as recommended, with the numerator reported.

**20. Row 3: the recall metrics** · Predictions · latest P4a · [Claude A7; Codex F10, Q27, V7]
- **Question:** Which lineage and version metrics does row 3 use?
- **Options:** (a) row 3 as written: top-level lineage presence (0 or 1), the
  fact-specific b2aiprep v3.0.0 measure for VOICE, the one enumerated ceiling, ties
  failing and a pinned adapter; (b) the script's recursive count and the version-token
  count, named as lexical proxies; (c) source-adjudicated recall with recomputed
  baselines; (d) descriptive.
- **Recommended:** (a). Its v8 baselines are unchanged. *Depends on:* nothing.
- **Answer (D64):** (a), as recommended.

**21. The E2 and E5 v10 rosters** · §12 · latest P4a · [Claude F4, C2, N9; Codex F9]
- **Question:** Which v10 records do rows 4 and 5 read?
- **Options:** (i) each in-scope cell's first clean attempt with an eligible record,
  accepted or not, with the accepted finals as a sensitivity row; (ii) all clean
  attempts, cell-weighted; (iii) the accepted finals, with row 4 descriptive and row 5
  labelled conditional on acceptance.
- **Recommended:** (i). Row 4 becomes falsifiable, and E5b-reg must add the few
  unaccepted first attempts. *Depends on:* items 2, 14 and 16.
- **Answer (D64):** (i), as recommended.

**22. Row 4: pool, weights and verdicts** · §16, Predictions · latest P4a · [Claude A7, F12, F18; Codex Q29, V8]
- **Question:** How are row 4's two rates pooled, weighted and judged?
- **Options:** (a) claim- and leaf-weighted pools over the projects in K primary,
  equal-project weights as a sensitivity, and two verdicts, 4a and 4b, with zero
  tolerance and ties holding; (b) equal-project rates primary; (c) descriptive.
- **Recommended:** (a). *Depends on:* items 17, 21 and 26.
- **Answer (D64):** (a), as recommended.

**23. Row 5: Q11 and Q19** · Predictions · latest P4a · [Codex F9, Q30]
- **Question:** Which tolerance and combination apply to rubric20 Q11 and Q19?
- **Options:** (a) two verdicts, each v10 mean ≥ v8 mean − 0.5 on the selected
  instrument's scale, over one primary rating per record; (b) zero tolerance for each;
  (c) descriptive.
- **Recommended:** (a). *Depends on:* items 21, 26 and 41.
- **Answer (D64):** (a), as recommended.

**24. Set B** · §3 · latest P4a for the recipe; its identities bound at P4b · [Codex F12, Q07]
- **Question:** What exactly is Set B's common gate?
- **Options:** (a) §3's recipe: the five named floors, measured, one common v4 checker
  on copies, the coverage row excluded and the E2 and E5 intersections reported apart;
  (b) the stored instruments' gates, as a historical sensitivity; (c) no Set B
  verdicts.
- **Recommended:** (a). *Depends on:* item 15.
- **Answer (D64):** (a), as recommended.

**25. The automatic-success estimand** · §1 · latest P4a · [Codex F13, Q24]
- **Question:** Is success measured over every unassisted start, or only over runs
  that stayed clean?
- **Options:** (a) both, with the all-started proportion as the feasibility headline;
  (b) the clean conditional proportion only; (c) only an attempt-flow table.
- **Recommended:** (a). It measures A21 itself, so it is fixed before A21.
  *Depends on:* item 11.
- **Answer (D64):** (a), as recommended.

**26. When the E2 and E5 instruments are fixed** · §12, §16 · latest P4a · [Codex V3; Claude re-review R4]
- **Question:** Are the E2 manual and reviewers and the E5 rubric version fixed now,
  or deferred?
- **Options:** (a) deferred by name to P4b, before any confirmatory launch word, with
  A21 descriptive permanently and the P4b record stating which pilot results the
  authors had seen (items 40 and 41); (b) fixed at P4a; (c) predictions 4 and 5 moved
  to a separate prospective study.
- **Recommended:** (a). The manual does not exist yet, and (b) would hold A21 for it.
  *Depends on:* items 21–23.
- **Answer (D64):** (a), as recommended.

**27. The audit-recall rule** · §12 · latest P4a · [Claude re-review R4; Codex Q48]
- **Question:** Is a scored audit-recall claim wanted, given that A21's audit is the
  first one opened?
- **Options:** (a) freeze a matching rule and its adjudication before A21's audit is
  opened; (b) keep D36's blind observations as a seed only, with no scored recall
  claim from this condition; (c) fund a separate human-annotated recall study.
- **Recommended:** (b), unless a reviewed rule already exists. *Depends on:* D36.

#### Group C. P4a: pilots, the floor, stops and continuation (answered, D64)
- **Answer (D64):** (b), as recommended.

**28. D20: the floor rule and its pilot branch** · §8; staged sequence, step 8 · latest P4a for the rule and branch; the value at A15 · [D20, decided by D64; Claude F3, A4, N7; Codex F6, Q12, V1, V8]
- **Question:** Which rule sets the production floor, and does the AI_READI pilot feed
  it?
- **Options:** (i) the lowest accepted pilot's fraction rounded down to 1/20, with the
  scope branch; it can register 20/20; (ii) as (i), capped at 19/20: AI_READI's pilot
  is accepted before A15 when AI_READI is in scope, otherwise the re-canary alone sets
  the value, which is then always 19/20; (iii) the lowest fraction minus 0.05, with
  the branch; (iv) 19/20 fixed for all production, independent of scope, with no pilot
  on the floor's path.
- **Recommended:** (ii). The floor follows the data where that can matter (AI_READI),
  and no 100% requirement arises. The Codex pass recommended no cap; (iv) is the
  simpler scope-independent route its V1 names. *Depends on:* items 2 and 29.
- **Answer (D64):** (ii), with the scope branch, as recommended.

**29. D03: cell roles and sequence, and A21's role** · §2; staged sequence · latest P4a · [D03, decided by D64; Claude A8, N7; Codex Q08, V2]
- **Question:** Which cells run, in which order, and what is A21's role?
- **Options:** (a) re-canary → AI_READI pilot → floor → CHORUS ×3 → production, at
  every scope; (a′) re-canary → P4b → the AI_READI pilot only if AI_READI is in scope
  → floor → CHORUS ×3 → production in item 2's order; (b) only A21's role fixed now,
  the rest at P4b.
- **Recommended:** (a′), with A21 descriptive permanently. Counting A21 as CHORUS
  replicate 1, which Claude's N7 showed the capped floor would permit, could only be
  chosen now, irrevocably and for every A21 outcome, as a different design. The Codex
  pass recommends against it, and this draft does not propose it. *Depends on:* items
  2 and 28.
- **Answer (D64):** (a′), with A21 descriptive for good, as recommended.

**30. Pilot rejection on v8's per-project worst** · §5 · latest P4a · [Claude A9; Codex Q04]
- **Question:** May a pilot, A21 included, be rejected for exceeding v8's per-project
  worst on the seven defect metrics?
- **Options:** (i) no: the comparison is recorded as evidence only; (ii) yes, on any
  regression; (iii) only on a regression in report findings.
- **Recommended:** (i). The bars are mostly zero and come from a different package.
  *Depends on:* item 14.
- **Answer (D64):** (i), as recommended.

**31. Stop classification** · §10 · latest P4a · [Claude B4, N2; Codex F8, Q16, V6]
- **Question:** Is each stop classified by §10's table: evidence status recorded apart
  from the cause, one primary cause by precedence, registration faults voiding the
  attempt?
- **Options:** (a) §10's table as written; (b) mutually exclusive categories assigned
  by an independent reviewer under a frozen manual; (c) any ambiguous case ends the
  condition.
- **Recommended:** (a). Assistance cannot erase a rule-level cause, and no label can
  exempt one. *Depends on:* items 11 and 32.
- **Answer (D64):** (a), as recommended.

**32. Content slips** · §10, row 3 · latest P4a · [new; Claude N1]
- **Question:** Is a receipt-floor or report-total miss, such as one mismatched
  snippet, rule-level? In A21 a rule-level rejection ends generic_v10.
- **Options:** (i) yes, rule-level, as first proposed; (ii) a "content slip": one
  contingency, counted by root cause toward production's stop-loss, with rule-level
  kept for sustained rejecting-class findings, validation failures and duplicate keys;
  (iii) rule-level only with a filed diagnosis that a rule change would prevent it.
- **Recommended:** (ii). One mismatched snippet is common (10-20a, and two of the
  three v8 CHORUS records), so under (i) A21 has a real chance of ending the condition
  on one. *Depends on:* item 31.
- **Answer (D64):** (ii), a content slip with one contingency, as recommended.

**33. Which classes allow a contingency** · §10 · latest P4a · [Claude A3, B4; Codex Q17]
- **Question:** Which stop classes allow one contingency (A13's "transport or
  operational cause")?
- **Options:** (a) content slips, registration faults, record shapes, transport and
  budget or clock stops allow one, and an impossible limit allows none; (b) transport
  only; (c) no contingency in this condition.
- **Recommended:** (a), within each cell's two attempts, and never by resuming a
  terminal run. *Depends on:* items 3, 31 and 32.
- **Answer (D64):** (a), as recommended.

**34. The defect-class stop-loss and A13** · §10 · latest P4a · [Claude B3, F22; Codex F8, Q15, V8]
- **Question:** What ends re-running in this condition?
- **Options:** (a) the first rule-level pilot rejection (A13); in production, two
  rejections with the same root-cause ID, counted across prefixes and never reset; (b)
  any first rule-level rejection, pilot or production; (c) two rejections of any
  cause, which amends A13.
- **Recommended:** (a). *Depends on:* items 31 and 32.
- **Answer (D64):** (a), as recommended.

**35. D21: production gating, continuation and the launch route** · §9, §13 · latest P4a for the route and A21's retry boundary; applied at P4b · [D21, decided by D64; Claude B1, B9; Codex Q13]
- **Question:** How do production rosters gate and continue, and through which route
  does every API launch go?
- **Options:** (a) D21 (b) with continuation (ii): absolute floors, no baseline, a
  stopped label never re-run, continuation under a new prefix, registration and word,
  and every API launch through `d4d api batch`; (b) as (a), with production also gated
  on v8's per-project worst; (c) an adjudicated-continue path built into `d4d api
  batch`; (d) the condition ends at any roster stop.
- **Recommended:** (a). It matches D56, under which a retry needs a new registration.
  *Depends on:* item 34.
- **Answer (D64):** (a), as recommended.

**36. The A15 adaptation after a pilot's terminal failure** · §9 · latest P4a · [Codex F7, Q14; Claude B2]
- **Question:** If a pilot ends in a terminal single-delivery failure, what may change
  at A15?
- **Options:** (a) nothing: D21 (b) continues under new registrations; (b) D21 (c) as
  its own procedure stratum, under a reviewed prospective analysis amendment; (c) end
  the condition and register the next version.
- **Recommended:** (a), or (c) if the failure shows the condition is infeasible. None
  of them sits outside the analysis. *Depends on:* items 4 and 35.
- **Answer (D64):** (a), or (c) if the failure shows the condition is infeasible, as
  recommended.

**37. Optional arms: the crate path (D04) and a monolithic baseline (D16)** · §17 · latest P4a, or P4b if kept open · [D04 and D16, decided by D64; Claude D2; Codex Q11, Q44]
- **Question:** Does this matrix include the with-crate CHORUS stage, or a monolithic
  API baseline?
- **Options:** (a) neither: both stay out of this matrix, and either needs its own
  specification, fit, budget, review and word later; (b) crate path B after plan
  A16-acc, separately funded (about 4 runs at roughly $40–60 each); (c) a separately
  registered monolithic baseline.
- **Recommended:** (a), given D58's budget. *Depends on:* item 2.

#### Group D. P4b: before any production registration
- **Answer (D64):** (a), as recommended.

**38. D15: Kids First** · §2a · latest P4b · [pending D15; Claude B7; Codex Q10]
- **Question:** Which route, order and floor does Kids First take?
- **Options:** (i) API after plan A14-acc and A15, with the registered floor; (ii)
  last in item 2's order, run only if funded and fitted at its own registration, with
  D33's descriptive own condition if admission refuses it; (iii) defer it, pending its
  own fit; (iv) drop it.
- **Recommended:** (ii). The Codex pass recommends (iii) for now. Kids First is never
  cleared with AI_READI's inputs. *Depends on:* items 2 and 10.

**39. VOICE_PEDIATRIC ×1 or ×3** · §2a · latest P4b · [pending D02; Claude B8; Codex Q09]
- **Question:** How many VOICE_PEDIATRIC runs, and in what role?
- **Options:** (a) ×1, descriptive, if funded; (b) ×3, if replicate variance is a
  stated need and it is funded; (c) defer.
- **Recommended:** (a), at about $96–118 per run. It is never an adult VOICE
  replicate. *Depends on:* item 2.

**40. E2's instrument, protocol and reviewers (D24)** · §12, §16 · latest P4b, before any confirmatory launch word · [pending D24; Claude C1, C3, F19; Codex F11, Q21, Q22]
- **Question:** Which instrument measures row 4, who reviews, and what does the frozen
  protocol contain?
- **Options:** (a) E2's blind source review with §16's units, a fresh Claude session
  plus a Codex pass as reviewers, the seeded blinding and arm guesses recorded; (b) as
  (a), with a cross-family or human rater; (c) the support judge, after #3343's paid
  calibration, which delays E2.
- **Recommended:** (a). *Depends on:* item 26.

**41. E5's instrument and funding (rubric20, E4)** · §12 · latest P4b · [pending owner, #2911; Claude C4, C5; Codex Q23]
- **Question:** Which rubric20 version and evaluator implementation does E5 use, and
  is E5 funded?
- **Options:** (a) the reviewed 3.0-based successor with the D52/D61 changes pinned,
  in one joint re-rating scaled to item 2's scope; (b) 4.0, with its normative-example
  approval and nine-case Q19 calibration; (c) defer E5, which leaves row 5 unmeasured.
- **Recommended:** (a), about $190–394 at full scope, unless 4.0's normative-example
  approval and nine-case Q19 calibration are completed, and 4.0 selected, at P4b before
  the first confirmatory launch (D64, item 26). If the calibration cannot finish by
  then, P4b selects (a) or holds the affected launch. E5's later registration binds
  only execution details and never switches the instrument for records already
  generated. *Depends on:* items 2 and 26.

#### Group E. Later

**42. Canonical marks across prefixes** · §7 · latest before any canonical mark (A20) · [Codex Q47]
- **Question:** How are canonical marks kept to accepted cells?
- **Options:** (a) rank by the existing criterion only within an accepted-cell list
  from the acceptance records; (b) leave cells unmarked until an accepted-only
  selector exists; (c) an owner-recorded manual mark.
- **Recommended:** (a) if the procedure is reviewed, otherwise (b). A mark never
  changes an estimate. *Depends on:* item 35.

**43. The native amendment** · §1 item 5, §5, §12 · latest before native registration · [pending D29 and the native IDs; Claude D1, D3, F20; Codex Q35–Q43, Q45, Q46]
- **Question:** Are the native questions left to a dated native amendment of this
  plan: D29's effort and account, the native acceptance rows, and the pending D09
  remainder, D11–D14, D18 and D25?
- **Options:** (i) yes, an amendment reviewed and ratified before native registration,
  none of them blocking A21; (ii) decide them now.
- **Recommended:** (i). Its proposals for that amendment: D29, the runtime's default
  effort recorded as such, an owner-named first-party account and seven-day headroom
  checked (the v3 direct run stopped at 0.96–1.0); D09, the pause scoped to the old
  generic_v9 arm; D11, the binary and hash deferred; D12, an owner-named operator and
  review pair; D13, toolchain exposure, launch flags, the runtime-closure fix and
  receipt origin pinned; D14, the old spend package validated against current
  evidence; D18, a two-week time-box; D25, no native canary counted as a replicate.
  *Depends on:* nothing on the API side.

#### Dependencies

- **D58's budget** decides item 2, and item 2 decides items 14, 17, 21, 28, 29 and
  37–41.
- **Item 14 (D02's AI_READI comparator)** decides K, the E2 roster, the AI_READI pilot's
  baseline and whether the `d22b61a9` plan gates matter.
- **Item 28 (D20)** feeds plan A15's amendment, which gates plan A16.
- **Rows 4 and 5** need items 21–23, 26, 40 and 41.
- **Item 11** decides membership of every analysis set.
- **Item 8 (D08)** gates A21's risk acceptance and every multi-row roster.
- **D62 and D63** feed the A21 registration; each later project needs its own allowance
  (item 10).

#### Where the reviews' stage splits differ

Both reviews put every rule that A21 or a later run first tests at P4a; they differ only
at the edges. This draft follows the earlier deadline wherever they differ.

| Items (this agenda) | Claude re-review | Codex verification | This draft |
|---|---|---|---|
| 13–24, the comparison rules | P4a | P4a "where feasible"; a named deferral to P4b only with A21 kept out | P4a |
| 26, when the E2/E5 instruments are fixed | the instruments at P4b at the latest | P4a decides whether to fix them now or defer them by name | P4a decides the deferral; items 40–41 at P4b |
| 37, the crate path and D16 | D04 at P4b; D16 with the native items | both may be ruled out of this matrix now; D16 is API, not native | P4a, or P4b if kept open |
| 42, canonical marks | later, at A20 | P4b is adequate | at the latest before any mark (A20) |
| 43, the native items | later, in the native amendment | the native amendment, except D16 | the native amendment, with D16 moved to item 37 |

## Appendix: historical records

These records add no rule. They are kept so that the history the rules rest on stays
visible.

### A. The "Resolved" comments are not rulings

Several issues carry comments citing commits that are on no remote branch:
- `027c2272c`: on #2930 and #2926, 2026-10-11T03:43Z;
- `c92d89824`: on #2930 and #2926, 2026-10-11T08:51Z, naming D01, D07 and D15;
- `25994a4d2`: on #2914, 2026-10-11T03:44Z. It records a proposed Path B (D04's
  subject) and does not name D04;
- `d9f7d9a72`: on #4758, #4759 and #4761, 2026-10-11T03:43–03:44Z.

All six issues were reopened on 2026-10-13, in two groups that state different reasons:
- **#4758, #4759 and #4761, at 06:08Z.** The comments each say the closing record "does
  not reflect an owner decision".
- **#2914, #2930 and #2926, at 17:35:44–17:35:59Z.** These were reopened "at the
  owner's request following the 2026-10-13 closure audit". The cited commits were
  outside GitHub main, and they do not establish the issues' required acceptance. For
  #2914 the comment adds that scheduling a proposed Path B does not establish its
  experimental acceptance.

#2930 and #2926 had already been closed, reopened and closed again on 2026-10-11 (at
03:43, 04:18 and 08:51Z). D07 has since been decided (2026-10-19; see the decision table). D01 and D15
are not established by those closing comments; D01 is now superseded by D26/D28.

### B. Historical examples of the two harness classes (§10)

They informed engineering; they are not assertions about BC1.

- **A record shape the runtime refused** (Lane C1 Finding 2, October 20 code).
  - Receipt completion validates the persisted full record against the captured
    schema (`_validate_record`, called from `_inputs`; `receipt_completion.py:154`,
    `:178`, `:215`). It does so before `_call_with_usage` admits the
    receipt-completion call (`run`, `:554`, `:584`). So the run stops after the
    full phase, and any re-address, have been billed.
  - C1 Finding 2 names the shapes no step repairs. The write-time normaliser misses
    a scalar on a line that opens a sequence item (`- slot: value`), and a scalar
    in a multivalued slot whose range is not `string`. Nothing unwraps or joins a
    list written in a single-valued slot.
  - `_repair_invalid` runs only after the phase loop (`api_runner.py:7456-7471`),
    so nothing repairs such a shape before the originals freeze.
  - C1 notes that its sweep bypasses `_validate_record`, so the gate itself was
    not exercised there.
- **A registered limit no valid answer could meet** (Lane C1 Finding 1). The
  superseded October 20 `worker_output_tokens` (4,000) was below the floor of any worker answer
  the terminal source review accepts, at every valid grid. It stops a run in one of
  two ways:
  - a cut-off answer is refused at the worker stage, and the typed audit is
    terminal after one worker is billed;
  - an answer that fits, by declaring rows as metadata or by shortening its
    quotes, passes the worker stage and fails at assembly, after every typed stage
    is billed. The worker grammar accepts a metadata row for any path.
    - Under the registered caps, the metadata form is open where an all-metadata
      answer fits under the cap at A1b's ratios: at G1, and at G2 and G4 for
      CHORUS, VOICE and VOICE_PEDIATRIC (1,744–3,852 tokens for the largest
      worker, before thinking).
    - For AI_READI, CM4AI and Kids First it is at the cap's edge (3,924–4,763).
  - With raised caps it was open at every grid in that historical experiment.

  The causes are the registration's limit and the worker check's permissiveness,
  so a contingency under the same limits would reproduce the stop. The remedies:
  - the reviewed current limits and metadata checks, before a registration is
    put to the owner; historical C1 paths are not assertions about BC1;
  - optionally, the runtime fix C1 suggests: `check_worker` refusing a metadata row
    on a path that `record_metadata_allowed` does not allow, which would move the
    metadata form's failure to the worker stage.

### C. Historical October 20 delegation differences

The following records the October 20 draft's interpretation of its original
delegation. Search/remote/worktree observations here are historical, not fresh
exhaustive absence findings. D26–D45, D50–D63, the matrix and items 14–16 above
govern the revised draft; this section does not override them.

1. **v8 records.** The prompt describes "v8 04f (`claudecode_assistant_agent`) and 04g
   (`claudecode_api_agent`)". Neither method directory exists in any local checkout
   or on origin/main. The records are one API arm under `claudecode_api`; see P1.
2. **The `< 0.55` trigger.** The prompt's "D21 < 0.55 single-delivery trigger (#5050)"
   is not in the plan or any repository text, and #5050 is unrelated (item 9).
3. **`--profile neutral`.** The prompt applies it to both VOICE_PEDIATRIC and Kids
   First. The plan specifies the neutral profile only for Kids First (A19-reg and
   A19-acc; item 2a). VOICE_PEDIATRIC is analysed beside VOICE (A18-reg).
4. **Confounds.** The prompt lists four compounded factors. The plan lists more
   (item 4).
5. **Line numbers.** The prompt cites "lines 1295–1330" for Track P. In the plan at
   `fcc78fab`, Track P spans lines 853–921: P1 857–875, P2 876–903, P3 904–912 and P4
   913–921. Lines 1295–1330 fall in A12 (which starts at line 1283) through A10c-rev
   (from line 1327).
6. **Worktree.** The plan asks for this file in a durable worktree under
   `d4d-executions`. The coordination prompt put it in
   `/private/tmp/d4d-claude-track-p-20261020`. The branch ref and commits live in the
   main repository, so they survive a reboot even if that directory does not.

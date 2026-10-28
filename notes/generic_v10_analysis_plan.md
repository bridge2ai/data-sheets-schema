# generic_v10 analysis plan (preregistration draft)

**Status: DRAFT, revised after P3, awaiting P4. Not preregistered, and it authorizes
nothing.** This is step P2 of `notes/d4d_generation_plan_2026-10-09.md` ("#### P2").
The plan becomes binding only after the owner's explicit P4 ratification of its exact
final text. Until then, no generic_v10 registration hash is put to the owner, and no
billed generic_v10 step runs (the plan: "Every billed generic_v10 step depends on P4").

**What performs P4 [proposed; owner fixes at P4, item 16].** The generation plan
words P4 as "The owner merges P2 with an explicit word", gated on "Merged on main".
This draft proposes that P4 is the owner's word naming this file's sha256 at a named
commit, recorded in the decision record, with the merge following it. Merging the
draft as an engineering artifact without that word does not perform P4. Under D58,
P4 is proposed in two stages, P4a and P4b ("Staged sequence under D58", below).

- **Revised:** 2026-10-27 for R6 F1–F6; authority corrected 2026-10-28 against
  D26–D45 and D50–D61; revised again 2026-10-28 for the two P3 passes on `314189e4b`
  (Claude F1–F23, Codex F1–F13) and for D62–D63; revised a third time 2026-10-28 for
  the two verification passes on `1ed9bb1ef` (Codex V1–V8, Claude N1–N10), with the P4
  agenda consolidated. D46–D49 are retired, not owner decisions. The local BC1/N2 implementations remain separately identified. This is a
  draft, not a retrospective registration or a declaration that the composed launch
  condition is ready.
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
- **[pending Dxx]:** a rule that rests on an undecided owner decision, followed by the
  plan's recommendation.
- **[proposed; owner fixes at P4]:** every decision rule and tolerance this draft
  offers.
- **(P4 item N):** the numbered question in "P4 agenda" at the end of this file.

The first two markers are proposals for the owner to confirm or amend at P4, not
rulings.
Nothing in this draft asserts a decision the owner has not recorded.

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
| D28 | Void 10-22b; one clean CHORUS API re-canary; 64k/32k/32k worker/omission/integration baseline, 128k report/reconcile, board A17 splitting, versioned wire/registration identity. Builder floor remains pending; 19/20 belongs to the re-canary only. | 2026-10-23; floor basis superseded by D37, partition selection refined by D45, re-canary slice raised by D58. |
| D29 | **Pending owner:** native effort and first-party `claude.ai` account. No API key. | Resolve for the native registration and launch. |
| D30, D38 | Revised R9 criteria limited to `confidentiality_level`/`hipaa_compliant`; American `license` spelling and new prompt pins in both assets. | D30 2026-10-23/24; D38 2026-10-25. |
| D31, D40 | Both 10-20a and 10-22a are archived assisted/invalid engineering evidence. D40 supersedes D31's initial generated-record disposition for 10-22a. Preserve artifacts; no run/archive edits. | 2026-10-23–26; assisted stratum below. |
| D32, D37 | D32's value-matching subtraction is superseded. D37 gates **phase-1 snapshot** receipt quality: `slots.with_receipt_at_receipt / slots.receiptable_at_receipt`. | D37 2026-10-25T19:44Z; item 3a. |
| D33 | Report-family pre-dispatch token-plus-output admission; no independent report-family trim under that decision. D44 subsequently requires a reviewed BC1 condition before the canary. | 2026-10-25/26; items 14–15 disclose the new exposure. |
| D34 | No new rule batch: measure #2918/#2919 with existing lints; defer #2931/#2937; #4018 reasons only; #3336 remains to be measured by CHORUS ×3. | 2026-10-25. |
| D35 | Freeze at rebuilt A21 registration on merged main, after board A17 (#5211), #5155 and #5157. A later runner change needs CHORUS byte-parity evidence and a diagnostic canary. | 2026-10-25; each billed canary still needs its own launch word. |
| D36 | Fresh Claude source reviewer plus Codex pass, neither generator nor operator; owner signs acceptance. Second blind reviewer seeds audit-recall observations against `original_full` before seeing the audit. | 2026-10-25; human decisions are not supplied by this draft. |
| D39 | Versioned worker wording recognizes a split list entry as a removal's owning root. | 2026-10-25; board A17 contract change. |
| D41, D42, D43 | No-touch operation and a terminal/rejection-state guard. D42 required a review of both guard candidates and an owner pick; the review is done and D55 made the pick. **Owner** runs the hash-approved re-canary command; agents monitor read-only. | D43 supersedes D41's operator clause; D55 records the guard pick. |
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
| D58 | The v10 path after BC1's fit and cost analysis: fix BC1 for all projects; raise the A21 slice from about $25 to $60; run the CHORUS re-canary under the fixed BC1; decide the matrix's scope and budget on its measured cost. | 2026-10-28T16:41Z; the matrix decision is deferred to that measurement. This draft reads the $60 as funding one attempt (item 10) and proposes the P4a/P4b staging that applies the deferral ("Staged sequence under D58"). |
| D59 | BC1's request shape (the D44 design choice): typed-audit calls send the full schema catalog once, drop the redundant per-slot `domain_of` lists and send the bundle once; the full, receipt-completion, reconcile, report and regate calls keep v10's A14 schema digest. | 2026-10-28T16:41Z; implemented in `8f83d6cb3` (items 14–15). |
| D60 | No typed-stage prompt-cache breakpoint; D06 stands. | 2026-10-28T16:41Z. |
| D61 | D52's committee-contact equivalence applies wherever `governance_committee_contact` is scored, rubric10 E2.2 included. | 2026-10-28T18:23Z. |
| D62 | BC1's fit gate for A21: the gate checks the floor and the caps scenario with the measured 1.25× escape factor; the escaped bound is reported, not gated. Request bytes are sized at 2.48 bytes per token and future-response bytes at 1.75. The CHORUS A21 registration uses `aggregate_input_tokens` 4,500,000 (in D62's sizing CHORUS needs about 4.06M, every call at or below 0.85 of its room, which is a sizing result and not an enforced ceiling; added spend exposure at most $3.13). | 2026-10-28T20:12:01Z, after the review of `8f83d6cb3`; item 15. |
| D63 | One `count_tokens` calibration, run by agy from the launch-base checkout through the runner's admission-check route, on one named, fixed D59 CHORUS worker request. It logs the request sha256 and the count; no generation and no other provider call. The measured ratio replaces the extrapolated 2.48 before registration. | 2026-10-28T20:12:01Z; item 15. |
| D02–D04, D08, remaining D09 choices, D11–D16, D18, D20–D21, D24–D25 | **Pending where not specifically superseded above.** D02 comparator/analysis-set choices and D04 crate comparison are not decided by this amendment. Each of these, and D29, is a numbered question in the P4 agenda. | Separate proposal, implementation and owner decisions. |

**The "Resolved" comments are not rulings.** Several issues carry comments citing
commits that are on no remote branch:
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
03:43, 04:18 and 08:51Z). D07 has since been decided (2026-10-19, above). D01 and D15
are not established by those closing comments; D01 is now superseded by D26/D28.

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
the condition; the proposed content-slip class allows one contingency instead (P4 item
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
say that these values were in view.

## Staged sequence under D58 [proposed; owner fixes at P4, items 1–3]

**Why the plan needs stages.** D58 decides the matrix's scope and budget on the
re-canary's measured cost. P4 must come before the re-canary, because every billed
generic_v10 step depends on P4. So the text ratified before A21 cannot fix the
matrix, and the matrix fixed after A21 must not be free to follow A21's outcome. The
proposal below separates the two stages, and fixes now the rules the later stage
applies.

**The sequence:**
1. **P3 dispositions.** Every P3 finding is fixed in this text or converted to a P4
   question, and the revision is re-reviewed.
2. **P4a.** The owner ratifies this file's exact text, by sha256: the A21 condition and
   every rule whose first relevant outcome is A21 or a later run. The P4 agenda gives
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
     then labelled partial.
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

### Scope rule [proposed; owner fixes at P4, item 2]

- **Whole projects only.** A project is in or out with all its cells. P4b never trims
  replicates inside a project to fit a budget.
- **The evidence is cost, fit and call failure:** A21's measured cost and call
  outcomes, each project's D62-style sizing, and the single-delivery exposure below.
  It is never a quality metric of A21, or of any v10 record, against v8.
- **The order [proposed]:** CHORUS ×3 → CM4AI ×3 → VOICE ×3 → AI_READI (pilot + ×3)
  → VOICE_PEDIATRIC ×1 → Kids First ×1.
  - It follows the generation plan's ascending bundle size.
  - AI_READI comes late because its comparator is pending (D02) and it costs the most.
  - P4b funds the longest prefix of the order that the budget covers, each project
    priced per accepted record with its retries (below).
  - The alternative (P4 item 2) is the owner's discretion at P4b, within the same
    limits on evidence.
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
- the written risk acceptance D08 recommends for single-row runs, which for A21
  should name its 8 single-delivery calls (item 10, P4 item 9);
- whether to allow a transport-only redelivery (P4 item 4).

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
the main input to P4 items 4 and 16, and to P4b's budget.

**Budget per accepted record [proposed; owner fixes at P4, item 2].** P4b prices each
in-scope project per accepted record, including its expected retries within D07's
bound, not per attempt. The failure rate it uses is P1's 92 v8 calls pooled with A21's
calls, by call type where A21 has them. A stopped attempt bills only the calls made
before the stop.

## 1. Estimands (P2 item 1)

1. **Feasibility and acceptance.** For each registered cell, the outcome is accepted
   or rejected (A11–A13), with its attempt count. Pilots are reported separately from
   production, and billing or native runtime evidence separately again. Two success
   proportions are reported per arm, stage and project [proposed; owner fixes at P4,
   item 31]:
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

## 2. Comparator, metrics and cell roles (P2 item 2; [pending D02])

**Comparator** (D02's recommendation): the v8 API fill.
- Prefix `2026-09-04f` for CHORUS and VOICE, and `2026-09-04g` for AI_READI and CM4AI:
  12 records, 3 per project, listed with their sha256s in P1.
- Excluded: the `04` and `04b`–`04e` canaries and the invalid `04f` AI_READI rep1.
- The v9 CHORUS canary (2026-09-12) is a secondary single-point CHORUS reference.

### The AI_READI comparator: a pending owner decision ([pending D02])

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

**The options.** This draft does not choose. D02 is the likely place to decide.

| option | AI_READI comparator | what it costs or changes |
|---|---|---|
| (a) | keep v8 `04g` rep1–3, **labelled cross-arm** | AI_READI's package effect also crosses the with-crate/no-crate boundary, and it is reported as such, never pooled unlabelled with the other three projects |
| (b) | **leave AI_READI out** of the confirmatory v8 contrast | the confirmatory set is CHORUS, CM4AI and VOICE, 9 + 9 records. AI_READI v10 is reported descriptively |
| (c) | the **2026-10-14b no-crate agentic rerun** (`claudecode_agent`, rep1–3, bundle `1a58ad7b`; untracked in `d4d-executions/aireadi-v8-b`) | Its three provenance records carry runtime `Claude Code`, provider `Anthropic` (not CBORG; `base_url` null) and no `reasoning_effort`. So the AI_READI contrast becomes runtime, provider, transport and effort together, plus the package: item 1.5's terms, never any one of them. The records are not on main, so they need a reviewed data PR first |
| (d) | a **new no-crate v8 API run** of AI_READI | billed; needs its own registration, review, allocation and owner word. D07's allocation covers generic_v10 runs only |

**Consequences that hold whichever option is chosen:**
- **The AI_READI pilot's canary baseline.** Plan A14-reg plans the pilot with
  `--canary-baseline 2026-09-04g_claude-opus-5-api-generic-v8`, but
  `canary.baseline_for` checks no bundle. It reads the stored check blocks of every
  record whose label matches the prefix. So the baseline itself would never reveal
  that the crate was in it. **[proposed; owner fixes at P4]:**
  - Under (a), the pilot keeps that baseline. Its seven AI_READI rows are read as
    cross-arm context, not as a like-for-like bar, and never as a reason to reject
    (item 5).
  - Under (b), the pilot runs without `--canary-baseline`. Under a pending floor with
    no baseline, `d4d api batch` computes no verdict at all (D15's text), so the A11
    rows alone decide.
  - Under (c), there are two choices, and P4a records which one (P4 item 14):
    - the same as (b);
    - the `2026-10-14b` prefix as a baseline, once those records are on the launch
      base. It differs in runtime, provider, transport and effort as well as package,
      and is read only as such. The batch calls `canary.baseline_for` with no method
      (`cli/api.py:1207`), so it searches `claudecode_agent` too. It reads only records
      under the repository's own `data/` tree.
  - Under (d), the new run's prefix becomes the baseline.
- **E2's blind batch:**
  - Under (a), the AI_READI v8 records enter E2 as they are, and the analysis
    stratifies AI_READI.
  - Under (b), AI_READI leaves the confirmatory comparison, and its v10 records are
    reviewed as a descriptive stratum.
  - Under (c) or (d), the replacement records enter E2. Under (c) they differ from
    the v10 records in runtime, provider, transport and effort as well as package, and
    the E2 comparison is labelled so.
- **Plan gates that cannot pass as written** (P1; under D50 claude prepares the plan
  amendment and agy pushes it):
  - A4's gate, "The CHORUS and AI_READI bundle md5s equal the comparators'
    (9b2ef4b6, d22b61a9)";
  - A14-reg's gate, "the bundle md5 is d22b61a9";
  - the run tables' "identical bundle d22b61a9".

  Today's AI_READI bundle is `1a58ad7b`, and the plan needs amending before A4.

### Cell roles (D03's recommended option (a), [pending D03]; scope fixed at P4b)

Every row after the re-canary runs only if P4b puts its project in scope (scope rule
above).

| role | cells | counts as a replicate | analysed as |
|---|---|---|---|
| CHORUS re-canary (A21, in plan A10's role) | 1 | never | descriptive n=1, separately and permanently |
| AI_READI pilot (A14) | 1, only if AI_READI is in scope; after the re-canary passes blind source review, and before A15 | no | pilot, separately |
| CHORUS replicate gate (A16) | 3 under the A15 floor | yes | confirmatory |
| Production (A17) | the in-scope projects among CM4AI, VOICE and AI_READI, 3 each, in the scope rule's order | yes | confirmatory (AI_READI per the comparator decision above) |
| VOICE_PEDIATRIC (A18) | ×1 if in scope (D02's recommendation; ×3 only if the paper needs replicate variance) | — | descriptive (item 2a) |
| Kids First (A19) | ×1 if in scope | — | descriptive (item 2a) **[pending D15]** |
| With-crate CHORUS (plan A21–A22) | only under D04 path B | — | separate stage **[pending D04]** |

The plan's A21–A22 identifiers for the optional crate stage are retained only as
historical task references, always written "plan A21–A22". Unprefixed **A21 is the
clean CHORUS API re-canary** (board A21) under D35/D44, not an authorization for a
crate arm.

### Six-project × generation-arm and evaluation matrix

All prospective cells below remain unlaunched/unregistered unless a later,
hash-bound owner record explicitly says otherwise. “Confirmatory” names the
proposed analysis role after P4, not current authorization or acceptance. The table
shows the full proposed matrix; P4b's scope decides which projects run.

| Project | API arm (`claudecode_api{,_core}`) | Native agentic (direct arm) (`claudecode_direct{,_core}`) | Evaluation/contrast role |
|---|---|---|---|
| CHORUS | One clean re-canary, n=1 descriptive; proposed production n=3 confirmatory against v8 | First canary n=1, descriptive feasibility only; no production replicates registered | API production enters E2/E5; native canary has independent acceptance review and separately registered descriptive E5 ratings, never a confirmatory native/API verdict |
| AI_READI | No-crate pilot separately; proposed n=3, confirmatory only under D02's chosen comparator, otherwise descriptive | Unplanned/unregistered | API E2/E5 retain the cross-arm label if v8 with-crate is selected; any later native contrast must also declare source/profile/account/effort differences |
| CM4AI | Proposed n=3 confirmatory against v8 | Unplanned/unregistered | API E2/E5 use non-human-subject/non-regulated applicability (D52); companion analyses are not dataset-processing facts |
| VOICE | Proposed adult n=3 confirmatory against v8 | Unplanned/unregistered | API E2/E5 adult scope; pediatric records never substitute |
| VOICE_PEDIATRIC | Proposed n=1 descriptive feasibility, no v8 comparator | Unplanned/unregistered | Separate pediatric E2-style source review/E5 descriptive row; no confirmatory effect or adult replicate |
| KIDS_FIRST | Proposed n=1 descriptive external resource-level feasibility, neutral profile, subject to actual input fit | Unplanned/unregistered | Neutral-context source review/E5 descriptive row; no v8 comparator and no inferred cohort-level equivalence |

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

With every project in scope, the proposed v10 confirmatory set is the
**three-replicate CHORUS gate A16** plus the nine other production records, excluding
the separate n=1 clean re-canary: 12 records, matching E2's 12 v8 + 12 v10 batch
under options (a), (c) and (d). Under (b), the confirmatory sets are 9 + 9, and
AI_READI's records form a descriptive stratum (item 12). Under P4b's scope, the set
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
  measured with the D24 instrument in E2 (item 16). They are proposed for
  preregistration at P4, not already registered or deterministic metrics.
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

## 3. Analysis sets and the rules for n=1 and n=3 (P2 item 3; [pending D02])

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

**Set A: which records each arm contributes. [pending owner decision; it overlaps
D02's "exclude the canaries"]** Either of two definitions applies one rule to both
arms. The v8 figures are P1's, recomputed.

| definition | v8 records | v10 records | v8 pooled coverage (CHORUS / VOICE / AI_READI / CM4AI) | v8 mean populated leaves |
|---|---|---|---|---|
| (1) every attempt in a comparator cell, under the arm's prompt pin, that left a full record | the 12, plus VOICE `04d`, `04e` and AI_READI `04f` rep1: 15. CM4AI `04`–`04c` (the earlier pin) enter only a sensitivity row: 18 | every attempt in a confirmatory cell that left an eligible full record (at most 2 per cell under D07, a D21 continuation included) | 0.340 / 0.462 / 0.491 / 0.688 (0.682 in the sensitivity row) | 254.7 / 393.0 / 505.5 / 458.0 (447.2) |
| (2) one record per cell: the cell's last attempt that left an eligible full record | the 12 | each confirmatory cell's last attempt that left an eligible full record | 0.340 / 0.592 / 0.538 / 0.688 | 254.7 / 371.7 / 499.7 / 458.0 |

The recall targets move as well. Under (1), VOICE variables average 5.20 (4.00 under
(2)) and VOICE lineage 0.80 (1.00), and AI_READI variables 19.50 (17.67) (P1).

**Recommendation: definition (2) for the directional rules, with (1) reported beside
it as a sensitivity row. [proposed; owner decides]** The reasons:
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

**Cells, attempts and eligible records [proposed; owner fixes at P4, items 15–16].**
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
  - **The event:** the run's progress file records `reconcile_full` as completed.
  - **The record:** the last full-record snapshot written at or after that event,
    either `<P>_reconcile_full.yaml` or, if repair ran, its last round's
    `<P>_repair_full_r<N>.yaml`, identified by the sha256 in the snapshot index. A
    repair interrupted before writing its snapshot leaves the previous one eligible. A
    report or regate that failed after reconcile does not change which record is
    eligible.
  - **A run that stopped before `reconcile_full` completed has no eligible full
    record.** Its phase-1 record is kept and reported, but it is artifact-missing
    for Set A.
  - A record that fails schema validation is eligible for Set A; Set B removes it.
  - A record with duplicate mapping keys is eligible for the validation and
    duplicate-key counts only. Every metric that reads values is unmeasurable for it,
    because a YAML loader silently keeps one of the values.
  - A value whose shape a metric cannot read (a mapping where the metric expects a list
    or a scalar, say) makes that metric metric-missing for the record.
  - **The analysis manifest** lists, for each record used: label, cell, attempt, the
    completing event, the snapshot's name and its sha256.
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

**Set B, common gate [proposed; owner fixes at P4, item 24].** Within whichever Set A
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
- **Default:** D02 recommends descriptive comparisons (per project, v10 values beside
  v8 values with mean ± SD and min–max), with no "v10 mean at or above the v8
  minimum" test unless a tolerance is preregistered per metric. Plan P2 item 3 allows
  either.
- **This draft's proposal:** adopt a tolerance per directional prediction
  (Predictions below), **[proposed; owner fixes at P4]**, so that each prediction can
  be judged true or false. The owner may replace any of them with "descriptive" at P4.
  Freeze tolerances at P4 before the first clean outcome under the selected
  production condition; prior assisted evidence is disclosed above. Subsequent
  changes require an explicit prospective amendment and a new analysis stratum.
- **Verdicts** are per project. A prediction's overall statement is "holds in k of K
  confirmatory projects". There is no inferential significance test at n=3.
  Prediction 4 alone retains a descriptive claim/leaf-weighted pooled decision rule,
  with the fixed-weight sensitivity in item 16; it is not a per-project or
  independent-replicate significance claim.
- **K [proposed; owner fixes at P4, item 17]** counts the in-scope projects (P4b) whose
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
- **Missing data [proposed; owner fixes at P4, item 16].** A primary directional
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
    proposed v10 baseline remains v8; watermark checks require separately selected
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
7. **Clean run [proposed; owner fixes at P4, item 13]:** item 7's clean-run checks all
   hold. A run that fails any of them is assisted: evidence only, never accepted.

**Native rows.** Every row above is written for the API arm. The native canary's
acceptance rows are not specified here; they are deferred to a dated native amendment
of this plan, reviewed and ratified before the native launch (P4 item 49).

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
passed to A13 as evidence. **[proposed; owner fixes at P4]:** a pilot is not rejected
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
- **Disagreements [proposed; owner fixes at P4, item 14]:** each reviewer's finding and
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
- **A clean run [proposed; owner fixes at P4, item 13]** passes every one of these
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
- **Pilots** are analysed separately, never as replicates **[pending D03]**.
- **No replicate is chosen by score.**
- **Canonical marks are never used as the estimate.** Estimates use every record in
  the analysis set.
- **Canonical marks** (A20) go only to accepted replicates, and pilots are never
  candidates. [proposed; owner fixes at P4, item 42]: the accepted cells and their
  record hashes are listed from the acceptance records first, and the criterion below
  ranks only within that list. They use `d4d runs select --method claudecode_api
  --project P --config <prefix>`, with `--execute` only on the owner's word.

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
- **Missing cells ([proposed; owner fixes at P4, item 16]).** An in-scope
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

## 8. Production-floor decision (P2 item 8; D37 basis decided, D20 rule at P4, value at A15)

D37 fixes the snapshot basis. D28 fixes 19/20 for the clean CHORUS re-canary only,
and the builder default is pending. The generation plan's D20 recommendation is to
"Commit the rule in P2 before the pilots run, and register the value at A15". This
draft follows it **[pending D20]**: the owner fixes the rule at P4a, before any pilot
runs, and A15 only computes its value. The rule never depends on a pilot's outcome.

**The proposed rule [proposed; owner fixes at P4, item 28]:**

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
- **No value.** If a required pilot is missing, rejected or has a zero denominator,
  the rule yields no value. No production roster registers until a prospective
  amendment, reviewed as P3 was, supplies one. No other observed ratio is substituted.

The alternatives (P4 item 28) are: the lowest fraction without the cap, which can give
20/20; the lowest fraction minus 0.05, rounded down; and 19/20 fixed for all
production. The last is an owner value (D28), not one derived from the pilots as
#2926 asked ("from the canary's post-turn distribution, not a guess"). It is
independent of scope, so it takes the AI_READI pilot off the floor's path altogether,
and the re-canary's registration body then matches production's. For the fallback,
the alternative is no value until an amendment.

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

## 9. Gating and continuation of production rosters (P2 item 9; [pending D21])

D21 recommends option (b) with continuation (ii).

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

**Trigger (A15):** if either pilot had a terminal single-delivery failure, the owner
decides at A15 between three options:
- continue under (b);
- build (c) before A16, landed by D17's advance procedure;
- move to the next shared-generation version with one recorded retry. That is a
  condition boundary for both arms and ends this generic_v10 API matrix.

**The A15 choice is part of the analysis [proposed; owner fixes at P4, item 36].**
It can change which calls and cells complete and how many attempts survive, and so
which records enter every metric. D35's parity test and diagnostic canary show that
the engineering is sound; they do not show that a changed selection process has the
same estimand. So:
- **Preferred: (b), with continuation (ii).** The procedure does not change. Eligible
  remaining attempts run under new registrations and a new prefix, within each cell's
  two attempts.
- **If (c) is chosen,** it needs its own reviewed, prospective analysis amendment
  before any affected production roster.
  - The amendment states exactly what continues. It never revives a run that stopped
    on a terminal or control-state discrepancy (D56).
  - Production then runs wholly under (c), or its (c) cells form a separately
    reported procedure stratum. (b) and (c) cells are pooled into one estimate only
    under a rule that amendment states.
- **Moving to the next shared-generation version** ends this matrix (plan A15).
- Under every option, Set A and Set B keep item 3's definitions. The choice and its
  basis are recorded in the A15 amendment before any multi-row roster.

**A transport redelivery adopted after A21** (P4 item 4) is a procedure change of the
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
- **One attempt, no contingency [proposed; owner fixes at P4, item 3].** A fixed-BC1
  CHORUS run is estimated at about $37 expected and $49 at caps ("Feasibility under
  D58"), so $60 funds one attempt and no contingency. D07's two billed attempts per
  cell are a ceiling, not funding. A contingency (plan A10c) needs its own allocation
  line, a new registration (D56) and its own owner word, unless the owner adds a
  funded contingency at P4.
- **No production money.** P4a funds nothing beyond A21. The matrix's budget is P4b's
  decision (D58).

### Operator trigger [proposed; owner fixes at P4, item 5]

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
- **A higher trigger needs an enforced ceiling.** Registering and enforcing a lower
  per-call input limit would raise it; that is an engineering change and a new
  registration (P4 item 5).
- **The margin is thin.** A caps-heavy D59 run is estimated at about $49 before
  retries, repair and re-address, so a legitimate run can reach the trigger. A stop at
  the trigger is a budget stop (classification below), not a defect.
- The old $11.50/$15 CHORUS example is historical.

### Wall clock [proposed; owner fixes at P4, item 6]

The 2 h stop came from the pre-BC1 plan A10, and nothing in BC1 justifies it:
- 10-22a's uninterrupted call time was already 51 min, across 9 calls with typed inputs
  of about 139k tokens;
- a BC1 CHORUS run has about 12–13 sequential calls, with typed inputs of 0.4–0.8M
  tokens, which is about 2 h of call time at caps (P3 Claude review).

This draft proposes a 3 h clock, about 1.5 times that estimate, re-derived in the
launch packet from the registered call schedule. The alternatives (P4 item 6) are to
keep 2 h as a deliberate censoring rule, under which a timeout is a feasibility
failure, or to have no clock. The clock is never extended during a live attempt.

### Stopping a live run

- **The command.** At the trigger or the clock, `d4d api stop --label-prefix <prefix>`
  stops the run. `--max-cost-dollars` stops only between runs (#5045). It cannot recall
  an in-flight request, and an interrupted stream may still bill (#1849).
- **Who runs it: open (P4 item 8).** D43 has the owner launch and the agents monitor
  read-only, and the decision record does not say who runs the stop command. The
  options are the owner, or one agent the owner names to run only that command, only
  at the trigger or the clock. Under D43's read-only monitoring, no agent runs it
  unless the owner's answer authorizes one.
- **What the monitor keeps:** the D57 journal heads printed at each start and stop,
  and the A3b readout against the trigger.

### Defect-class stop-loss and A13 [proposed; owner fixes at P4, item 34]

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
  - Rule-level causes and content slips count (content slips: P4 item 32).
- **The older D05 clause** (if both pilots are rejected for the same rule-level cause,
  the #2918 and #2919 rules enter at the next version) cannot arise once the first
  rule-level pilot rejection ends the condition, and D34 has since decided the rule
  batch. It is historical.
- **Other stops do not count.** Instrument, registration, harness, transport and budget
  stops are counted and reported separately.

### Stop and rejection classification [proposed; owner fixes at P4, items 31–33]

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
| 3 | **content slip** [proposed; P4 item 32] | a receipt floor or the report totals fail (item 5, rows 1 and 4), and row 2 does not match | One contingency under a new registration, within the cell's two attempts. Counts toward production's stop-loss by root cause. Under P4 item 32's option (i) this row merges into row 2 |
| 4 | **registration or environment** | a configuration row fails (item 5, rows 5–6: the full-phase cap, the provider or base URL), or another fault of the registration or the launch environment rather than of generated content | The attempt is void. One contingency under a corrected registration, within the cell's two attempts |
| 5 | **impossible limit** (harness) | a registered limit no valid answer can meet | No contingency under the same limits. The limits are corrected and reviewed first, and the corrected registration is a new condition identity |
| 6 | **record shape** (harness) | receipt completion's validation refused the phase-1 record for a value of the wrong cardinality or type for its slot: a shape the write-time normaliser does not fix, which the repair call (run only after the phase loop) never had the chance to fix | One contingency under a new registration, within the cell's two attempts. If it is refused for the same shape, the fix is engineering, landing only by D17's procedure or at the next version |
| 7 | **transport** | the terminal call's `api_usage` row records a transport error or a dropped stream, or the provider returned an HTTP error | One contingency under a new registration, within the cell's two attempts |
| 8 | **budget or clock** | the operator stopped the run at the trigger or the clock | One contingency under a new registration, with a new allocation line and word, within the cell's two attempts |
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
- **A13's "transport or operational cause"** is read as rows 3, 4 and 6–8 [proposed;
  P4 item 33]: they allow one contingency. An impossible-limit stop does not, since a
  contingency under the same limits would reproduce it.

**Historical examples of the two harness classes** (they informed engineering; they
are not assertions about BC1):
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

### Single-delivery exposure

- BC1's typed calls and receipt completion each admit exactly one delivery
  (`transport_attempts=1`).
- A21 has 8 such calls. At v8's per-call rate (8 retried calls in 92, P1), with
  independence assumed, that is an illustrative 52% terminal-stop exposure from all
  causes, and 36% from transport alone. The per-project table is under "Feasibility
  under D58".
- The plan's earlier four-, six- and eight-call figures describe the pre-BC1
  single-integrator design. They are not carried into BC1 budgets or predictions.
- Content failures stay terminal under D56. Whether to allow one transport-only
  redelivery per typed call is P4 item 4; it would be new engineering, and adopted
  after A21 it needs item 9's analysis amendment.
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

**Comparison batch (E2)** is separate from acceptance [proposed; owner fixes at P4,
items 26 and 44]:
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
- **Reviewers:** a named pair chosen at P4 (P4 item 44). D36 names the acceptance
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
  (rubric10 E2.2, rubric20 Q9). A version label alone does not identify the
  instrument: an unmodified historical 3.0 is not the D52/D61 instrument. Old scores
  are not rewritten. Prediction 5's items, Q11 and Q19, are not among those D52/D61
  change;
- preamble and check-echo (#1077);
- a rubric20 repeat panel (#2912);
- every output validated with `validate_evaluation_schema.py --file`, exit 0.

E5 needs its own registration, review and owner word. D22's withdrawal means no
standing authorization covers it.

**The rating workload is not the analysis roster [proposed; owner fixes at P4, items
26 and 28].** E5b-reg rates every accepted generic_v10 API-route record, the v8
comparators and a repeat panel. Prediction 5 reads a narrower roster:
- exactly one primary rating per record of E2's v8 and v10 rosters above, the v10
  roster taken before acceptance. E5b-reg must add any such record it would not
  otherwise rate (a generation-plan amendment);
- excluded from prediction 5's means: the re-canary and the pilots, with-crate
  records, native rows, historical calibration records (such as CM4AI v7 rep2) and
  repeat-panel copies;
- repeat ratings are reliability evidence only.

The alternative (P4 item 26) is to keep E5's accepted-only roster and label row 5 as
conditional on acceptance.

The native CHORUS canary is not automatically included in the API/v8 E2 or E5
batch. If accepted, rate it only through a separately declared descriptive
native-arm stratum: same selected rubric/context bytes, independent blind source
review and exact-file validation, with generation runtime/tool/exposure
differences retained. Other native cells are unplanned and receive no invented
rating rows. #5126's historical-comparator authority route, the separate native
rating authority adapter and any rubric amendment must be settled for the
participating strata before ratings; route engineering does not authorize them.
The proposed atomic-claim protocol belongs to D24/P4 (item 16), not #5126.

## 13. Labels and launches (P2 item 13)

- One distinct date-letter prefix per roster.
- `generic-v10` as a delimited label token.
- No `pilot` or `canary` word in any label.
- Outputs are copied, never moved, into data PRs, so the #795 guard keeps passing.
  The launch worktree is never fast-forwarded over those data PRs except by D17's
  procedure.
- A stopped label is never re-run.
- Every **API-arm** generic_v10 launch, continuations included, goes through `d4d api batch` with
  a roster, never `d4d api run` ([pending D20]: D20's recommendation). `d4d api run`
  has no floor verdict, canary
  block, run lock or #795 guard.
- Native launches use Track N's registered command/recorder path and first-party
  authentication; they never go through the API batch route. D29 and the native
  real-binary/probe/acceptance gates remain separate prerequisites.
- Immediately before every billed launch, the operator (under D43, the owner) hashes
  the roster, every registration it lists and the launcher script, and stops on any
  difference from the sha256s named in the word and the review (A10).

## 14. Selected condition, bounded carry and model-visible identity

The design label **`shared-generation-api-v2-bc1`** names the proposed scientific
condition. It is **not** the installed `shared_generation_version` or an accepted
registration; the label is P4 item 10. BC1's implementation lineage:
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
delta, not an alias for D28's 32k integration. The owner settles it at P4 (P4 item 11);
this draft does not silently approve it. D58's cost basis already assumes 64k. Retain
the original decided baseline and the proposed BC1 value in the decision packet.

Separate fixed visible envelopes are **98,304 worker bytes**, **131,072 integration
bytes**, **262,144 carry bytes**, and **32 open concerns**. They neither replace
the thinking-inclusive token reservations nor authorize truncation, changed
partitioning or an extra delivery after refusal. An answer must satisfy both
bounds and the existing evidence/grammar checks.

With `W` workers and registered fan-in `f` of 1 or 2, BC1 plans
`G = ceil(W/f)` group integrations plus **one separate final integration**:

- audit calls: `W + 1 omission + G + 1 final`;
- proposed BC1 aggregate output reservation:
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

**Fit evidence, and when it is needed [proposed; owner fixes at P4, item 12].**
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

D24 recommends option 1. The following precise E2 units and weighting are a
**prospective proposal for D24/P4, not an already ratified protocol**.

**What is frozen, and when [proposed; owner fixes at P4, item 44].** These determine
the denominators and the rejecting classes, so they are frozen before any
confirmatory outcome exists: at P4b at the latest, before any confirmatory roster's
launch word. "Before E2" would be after the v10 outcomes exist.
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
(claims) and **4b** (leaves) [proposed; owner fixes at P4, item 22]. Row 4 as a whole
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
disagree with the pool. **The primary pool [proposed; owner fixes at P4, item 22]**
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

## 17. The D04 path (P2 item 17; [pending D04])

D04 recommends never path A in this condition. It recommends path B, scheduled after
A16-acc, or Defer if the paper does not need a crate-versus-no-crate delta at the same
prompt version.

Under B:
- the with-crate context is the CHORUS context unchanged (release null), so the two
  arms differ only in their bundles;
- the runs pass no `--canary-baseline`, because the baseline reader searches no crate
  directory;
- the with-crate cells are analysed as their own stage and never pooled into the
  confirmatory set.

The owner's 2026-10-14 ruling, that crates belong only to the with-crate and
crate-only arms, is consistent with B, and it is what makes AI_READI's v8 records
with-crate (item 2).

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
remains [proposed; owner fixes at P4]** (P4 items 18–23). The values the assisted
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

| # | prediction (from #2930, restated against v8 per D02) | metric and instrument | decision rule [proposed; owner fixes at P4] | v8 values (P1) |
|---|---|---|---|---|
| 1 | Populated leaves fall by no more than 10% (a non-inferiority reading of #2930's "do not fall") | `len(receipts.populated_leaves(full))` per eligible full record, `receipts.py` at P1's pin `7bfb8470…` | holds for p if mean(v10_p) ≥ 0.9 × mean(v8_p); equality passes. v8's replicate SDs are 21.7 (CHORUS), 43.9 (AI_READI), 31.3 (CM4AI) and 68.6 (VOICE) leaves, so 10% of the v8 mean is 1.2, 1.1, 1.5 and 0.5 SD respectively | AI_READI [525, 525, 449], CHORUS [235, 278, 251], CM4AI [422, 473, 479], VOICE [386, 297, 432] |
| 2 | Receipt coverage does not fall, measured pre-completion | **v10:** v4 `receipt_completion.before.slots.with_receipt / receipt_completion.before.slots.receiptable` on `O,R0` (item 3a). **v8, primary:** the stored v3 final-record `receipts.slots.with_receipt / receipts.slots.receiptable` values in the last column. **v8, sensitivity:** a named common-checker recomputation where exact inputs exist. **Pooled** means the sum of the numerators over the sum of the denominators, across the project's Set A records. Pin source/checker identities; do not infer parity from the unchanged v4 string. | holds for p if pooled pre-completion v10 coverage ≥ pooled v8 coverage − 0.05 absolute. **The numerator is reported beside every ratio.** If the ratio holds while v10's pooled receipted-leaf count is below v8's, the result is reported as "ratio held with a smaller record", never as improved coverage, and it is read with row 1. Every required snapshot must be present (item 3): a missing pre-turn snapshot is never 0, never replaced by a post-turn value, and never dropped silently from the pool. Final-v8 versus phase-1-v10 remains a timing/instrument contrast. D37 at-receipt gate coverage, final coverage and completion gain are separately reported, never substituted into this rule. | pooled, under item 3's definition (2), receipted / receiptable: CHORUS 215/632 = 0.340, VOICE 584/986 = 0.592, AI_READI 694/1289 = 0.538, CM4AI 817/1187 = 0.688. Under (1): VOICE 0.462, AI_READI 0.491 (P1) |
| 3 | The recall rule raises recall where the bundle states the targets | The pure counters of `scripts/recall_target_baseline.py` (cues `768a26a3…`, tools `4726c005…`), applied directly to item 3's Set A roster. Not through the script's `collect()`, which skips records whose validation failed, and not through its default arm list, which stops at v9. D02's targets:<br>- AI_READI variables 20/13/20;<br>- CM4AI lexical candidates 9/5/3;<br>- VOICE variables 4/4/4, lineage 1/1/1, lexical candidates 3/0/1, b2aiprep v3.0.0 in `used_software`/`tools` 0/0/0;<br>- CHORUS lineage 1/1/0.<br>**Lineage [proposed; P4 item 20]** is a top-level presence indicator: 1 if the record's top-level `was_derived_from` holds at least one populated entry, whatever its type or number of entries, else 0. It does not rely on the schema's single-valued declaration, which Set A's invalid records may break. The script's `target_counts` instead counts lineage entries at every depth, and nested objects can carry `was_derived_from`. On all 12 v8 records and both assisted records the two agree (no nested or multiple lineage occurs; recomputed for this revision), so the v8 values do not change.<br>**VOICE's version target [proposed; P4 item 20]** is the fact-specific carriage measure for `voice-b2aiprep-3.0.0` in `notes/recall_target_baseline.md` ("used_software/tools" column, with that note's matching rules). It replaces "tools with a version token", which counts any version-shaped token in `tools`, so a wrong version can raise it; that count stays reported as a lexical carriage proxy. The v8 records carry b2aiprep v3.0.0 elsewhere in all three.<br>**The adapter** that applies these counters to Set A is a script pinned by sha256 in the P4b amendment, before any confirmatory record exists; on the 12 v8 records it must reproduce this row's v8 values.<br>These are carriage counts, not support or recall accuracy. | **Counts the rule should raise** (variables, lineage, b2aiprep carried): holds for a target if mean(v10_p) > mean(v8_p); a tie fails.<br>**Targets at their ceiling, enumerated now:** only VOICE lineage. The presence indicator is at most 1 by construction, and every v8 VOICE replicate is at 1. That target holds if mean(v10_p) ≥ mean(v8_p). No other target gets a ceiling exception after the outcomes.<br>**Lexical candidates**, which should fall as cue chunks are extracted rather than set aside: holds if mean(v10_p) < mean(v8_p).<br>**Combination:** a project's row-3 verdict holds if every target listed for it holds, and "holds in k of K" then counts projects [proposed].<br>AI_READI's v8 counts were taken over the with-crate chunking (P1) | as listed |
| 3a | A rise is an error where the bundle states nothing | Same counts, read against the #3289 adjudication in `notes/recall_target_baseline.md`:<br>- no parent dataset in any of the four bundles;<br>- no processing-software version in the AI_READI, CHORUS or CM4AI bundles (CM4AI's versions belong to companion analyses);<br>- VOICE's one stated version is b2aiprep v3.0.0.<br>The adjudication read AI_READI's pre-#5042 bundle, when it still had its RO-Crate, which recorded FAIRSCAPE 1.2.1 as the metadata packager, not processing software. It is re-read against `1a58ad7b` before P4. | holds if every confirmatory v10 record has `parent_datasets` 0; for AI_READI, CHORUS and CM4AI, `used_software` with a version 0; and for VOICE, no versioned `used_software` entry other than b2aiprep v3.0.0, the one processing-software version the adjudication found in VOICE's bundle. Any non-zero instance means it does not hold, and each instance is listed. If a required record is absent, the row is "not measured" for that project; it never passes on an empty set (item 3) | 0 today |
| 4 | The rejecting-class unsupported-claim and adverse-slot rates do not rise (a review-pass prediction) | D24/P4 proposed atomic-claim and eligible-leaf units, exclusions, dedup/splitting and complete-adjudication rules in item 16, frozen before any confirmatory outcome; E2's roster with the v10 records taken before acceptance (item 12) | **Exception to per-project verdicts:** claim-weighted and leaf-weighted E2 pools over the projects in K, not Set A attempts. Two verdicts: **4a** holds if v10's claim rate ≤ v8's, and **4b** if v10's leaf rate ≤ v8's; zero tolerance, ties hold, and neither is folded into the other. Always show project-specific rates and equal-project-weight sensitivity. Under AI_READI options (a) and (c), AI_READI is outside K: the pool over the in-scope projects in K decides (three at full scope), and AI_READI is a separate cross-arm row (item 16). The accepted-final records are a sensitivity row. Missing/unassessed units do not create a passing verdict. | no adopted E2 annotation result asserted here; measured after protocol/roster freeze |
| 5 | Rubric20 Q11 and Q19 do not fall (secondary) | E5 joint re-rating, instrument version per E4 with the D52/D61 evaluator identity (item 12); one primary rating per record of E5's analysis roster; repeat-panel ratings are reliability evidence only | Two verdicts: **5a** (Q11) holds for p if mean(v10_p) ≥ mean(v8_p) − 0.5 on the item's scale as the selected instrument defines it, and **5b** (Q19) likewise; equality passes, and a project's row-5 label is "holds" only if both do. A rating the instrument scores N/A, or a record with no usable primary rating for an item, is metric-missing for it (item 3). No pilot, re-canary, with-crate, native or calibration record enters these means | measured in E5 |
| 6 | **Not a prediction: an acceptance invariant.** Validation passes with 0 duplicate keys | `validation.passed` and `canary.duplicate_key_count` | true by construction for accepted v10 records, since the batch stops on invalid output and duplicate keys gate. Set A reports the count of v10 attempts whose output failed either, descriptively | 12/12 passed, 0 duplicate keys |
| 7 | **Descriptive, no direction:** report findings | `report_claims.findings` | reported per record and per project in both sets. Reasons:<br>- the counts cross instrument versions: v8's stored blocks are v7, and new runs are checked under v8;<br>- renderer 25's report carries the typed audit's finding totals (#4766), which v8's report did not;<br>- v8's values are 0–2 per record.<br>A directional rule would be decided by noise, as D21 argues against its option (a) | worst, stored v7 and recomputed under v8 alike: CHORUS 2, VOICE 1, AI_READI 1, CM4AI 0. Under v8, CHORUS rep3 goes from 0 to 1 (P1) |
| 8 | **Descriptive, no direction:** replicate structure (#2932) | `replicate_structure` per project: all/some/none, identical, nested counts differ, max/min ≥ 2, intermittent slots | **n=3 primary**, each cell's last eligible record (item 3); n=2 only a separately flagged sensitivity on common replicate positions, n and IDs in every table; fewer than 2 is not computable (items 3/7). D34 says #3336 is in v10 and CHORUS ×3 measures it; that is not empirical proof of a directional structure effect. | P1 section "Replicate structure"; intermittent AI_READI 8, CHORUS 14, CM4AI 17, VOICE 9 |

Rows 1–5 are directional and decidable, rows 6–8 are not predictions, and every
rule is the owner's to fix at P4. Leaves and coverage read #2930's "do not fall" with
stated margins: 10% of v8's mean leaves, and 0.05 of pooled coverage.
Recall is "rises where the bundle states the target, and is never invented where it
does not" (3, 3a). Structure and report findings are descriptive, for the stated
reasons.

## Historical October 20 delegation differences

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

## Open before P4

### What P4a needs, apart from the owner's answers

- **P3 closure.** Every P3 finding is fixed here or converted to an item below, each is
  filed as an issue, and this revision gets its re-review. The dispositions are in
  `d4d-executions/plans/reviews/p2_p3_dispositions_2026-10-28.md`.
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

This draft does not edit the generation plan. These amendments are needed:
- the `d22b61a9` gates in A4 and A14-reg, and the run tables (§2);
- D15's and A19-word's "about the size of AI_READI's 542,513" (Kids First's bundle is
  541,184 bytes);
- A19-reg's "vocabulary null", which should read `vocabulary: {}` (§2a);
- D07's AI_READI lines (a $35 planning ceiling and a contingency of at most $35), which
  a D59 AI_READI run, at about $162–191, exceeds;
- A1's sizing inputs, which do not include Kids First and are superseded by BC1's fit
  analysis (§15);
- for the staged sequence: plan A10's role, which the re-canary fills with a
  registered 19/20 floor; plan A14's start, conditional on scope; plan A15's inputs,
  under §8's fallback; E5b-reg's roster (§12); and the wording of P4 itself
  (the header).

### P4 agenda

**How to read it:**
- Items are numbered once, in the order the answers are needed.
  - Group A is needed at P4a, before the A21 re-canary.
  - Group B holds the analysis rules. P4a fixes them. An item may be deferred to P4b
    only if P4a names it, and never past the first confirmatory launch word.
  - Groups C–E are needed later, at the stage named.
- Each item gives the question, the options, this draft's recommendation and what it
  depends on. The sources in brackets are the Claude P3 review's agenda items (A1–D3)
  and findings, and the Codex P3 pass's questions (Q01–Q50) and findings.
- Inside this agenda, "item N" is an agenda item and "§N" is this file's item N.
- A recommendation is this draft's, not an owner decision. Where the two reviews
  recommend differently, the item says so.
- What the decision table records as decided (D06, D07, D10, D22, D26–D28, D30–D45
  and D50–D63) is not asked again; D29 is pending, and D46–D49 stay retired.

#### Group A: P4a, before the A21 re-canary

**1. What P4a ratifies** [new; Claude F2, A1(iii); Codex F1, Q01]
- **Question:** while D58 holds the matrix's scope and budget until A21's cost is
  measured, what does the P4 word before A21 ratify?
- **Options:**
  - (a) the staged sequence: P4a ratifies this text (the A21 condition and every
    analysis rule), and P4b, a dated, reviewed amendment, fixes scope and budget under
    the scope rule ("Staged sequence under D58");
  - (b) P4a ratifies A21 as a feasibility study only, and any comparison is
    registered later as a new prospective study;
  - (c) hold everything until a funded full matrix is approved, which would amend D58.
- **Recommendation:** (a). It lets A21 run under D58, and it keeps the later scope
  choice blind to quality outcomes.
- **Depends on:** nothing. Items 2–51 assume (a).

**2. The matrix scope rule** [new; Claude F2, A1; Codex F1, Q01]
- **Question:** which rule turns D58's later scope decision into K, the confirmatory
  set
  and the E2 and E5 rosters?
- **Options:**
  - (i) the predeclared order (CHORUS ×3 → CM4AI ×3 → VOICE ×3 → AI_READI pilot + ×3
    → VOICE_PEDIATRIC ×1 → Kids First ×1): whole projects only, on cost, fit and
    call-failure evidence, with a descoped project out of scope, not missing;
  - (ii) the owner's discretion at P4b, limited to whole projects and the same
    evidence;
  - (iii) as (i), with a different predeclared order.
- **Recommendation:** (i). At the $420 figure it stops after CHORUS ×3, so K would be 1
  and every verdict a single-project result.
- **Depends on:** item 1 and D58's budget. It gates items 18, 21, 26, 32, 33, 40, 41,
  46 and 50.

**3. The re-canary's attempts and contingency** [new; Claude F1, A2; Codex F3, Q19]
- **Question:** does D58's $60 fund one attempt or two, and what funds a contingency?
- **Options:**
  - (i) one attempt; a contingency needs its own allocation line, registration and
    word (D07, D56);
  - (ii) raise the slice to about $120, to pre-fund one contingency;
  - (iii) split $60 into two smaller caps, which an estimate of about $37–49 per run
    does not support.
- **Recommendation:** (i). A transport or harness stop then needs a new word and money
  before anything else runs. (ii) shortens that path, but commits money before the
  measured cost D58 waits for.
- **Depends on:** D58, item 4.

**4. Single-delivery exposure: allow a transport-only redelivery, or accept it** [new; Claude F14]
- **Question:** BC1's typed calls and receipt completion admit one delivery each. At
  v8's per-call rate that is an illustrative 52% terminal-stop exposure for A21's 8
  calls, and 74–91% for the larger projects. Allow one transport-only redelivery per
  BC1 typed call, or accept the exposure?
- **Options:**
  - (i) accept it for A21 and for production, under item 9's written risk acceptance;
  - (ii) build one transport-only redelivery per typed call before A21;
  - (iii) accept it for A21, and decide for production at P4b from A21's observed call
    outcomes.
- **Facts that hold under every option:**
  - Redelivery would be new engineering in BC1's runtime, with its own review and D35's
    parity test.
  - It would re-send the same request after a transport error only. Content failures
    stay terminal under D56.
  - A change made after the A21 freeze also needs D35's diagnostic CHORUS canary,
    about $37–49.
- **Recommendation:** (iii). A21 runs the condition already built, and the per-call
  rates are measured first. If P4b then wants redelivery, the diagnostic canary is its
  price.
- **Depends on:** items 3 and 9; D35.

**5. The operator trigger** [new; Claude F1, A3; Codex F3, Q19]
- **Question:** at what spend is A21 stopped?
- **Options:**
  - (i) the cap minus the largest pending worst case, from D62's sizing, computed in
    the launch packet: about $53 at $60;
  - (ii) a fixed $50.
- **Recommendation:** (i). A caps-heavy run (about $49) leaves a thin margin; a stop at
  the trigger is a budget stop (item 7), not a defect.
- **Depends on:** D62, D63.

**6. The wall clock** [new; Claude F1, A3; Codex F3, Q20]
- **Question:** what time stop applies to A21?
- **Options:**
  - (i) 3 h, re-derived from BC1's 12–13 calls (about 2 h of call time at caps);
  - (ii) keep 2 h as a deliberate censoring rule, a timeout counting as a feasibility
    failure;
  - (iii) 4 h;
  - (iv) no clock.
- **Recommendation:** (i): 2 h would cut off a legitimate caps-heavy run. The Codex pass
  recommends (ii) unless duration evidence supports a longer clock. Under every option
  the clock is never extended during a live attempt.
- **Depends on:** the registered call schedule.

**7. The class of a budget or clock stop** [new; Claude F1, A3]
- **Question:** what class, and what next action, does a stop at the trigger or the
  clock get?
- **Options:**
  - (i) a new "budget or clock" class that allows one contingency, under a new
    registration, allocation and word;
  - (ii) a harness "registered limit", which allows none.
- **Recommendation:** (i). Without it, such a stop has no class and no contingency rule
  (§10's table).
- **Depends on:** item 3.

**8. Who runs `d4d api stop`** [new; Claude F1, A3]
- **Question:** D43 has the owner launch and the agents monitor read-only, and the
  decision record does not say who runs the stop command at the trigger or the clock.
  Who does?
- **Options:**
  - (i) the owner;
  - (ii) one agent the owner names, for that command only, and only at the trigger or
    the clock.
- **Recommendation:** (i), consistent with D41 and D43. (ii) gives a faster stop, but it
  makes an agent an operator for one action.
- **Depends on:** D41, D43, D53.

**9. D08: A21's written risk acceptance, and the CBORG follow-up** [pending D08; Claude B6, F14; Codex Q34]
- **Question:** is the prepared CBORG timeout and keepalive follow-up sent, and what
  gates single-row and multi-row runs?
- **Options:**
  - (1) prepare the exact message for its own per-action owner approval, naming the
    recipient, channel and text; accept the risk in writing for single-row runs now;
    require CBORG's answer, or a renewed written acceptance, before the first multi-row
    roster;
  - (2) send nothing, and accept the risk in writing for everything;
  - (3) send nothing, and block every roster until CBORG answers.
- **Recommendation:** (1). Under any option, A21's written acceptance names its 8
  single-delivery calls and BC1's exposure, replacing the obsolete four-to-eight-call
  estimate. Nothing in this draft sends a message.
- **Depends on:** item 4. It gates A21 (the acceptance) and plan A16 (multi-row).

**10. The condition's label** [open in §14; Claude F7, A11; Codex Q18]
- **Question:** what identity does the registration name?
- **Options:**
  - (i) the installed tuple, shared generation 1 plus `bounded_carry_version` 1, with
    `shared-generation-api-v2-bc1` kept as a design label only;
  - (ii) bump the shared-generation version, which needs code changes in the shared-v2
    routing that #5212's F1 concerns.
- **Recommendation:** (i).
- **Depends on:** D55's guard composition.

**11. The integration reservation** [open in §15; Claude F7, A11; Codex Q18]
- **Question:** BC1 requires 64k for every group and final integration call, where D28
  decided 32k. Which is the condition?
- **Options:**
  - (i) amend D28 to 64k for BC1's integration calls, as a declared amendment;
  - (ii) keep 32k, which needs a BC1 change, re-sizing and re-review;
  - (iii) withhold the selection pending a redesign.
- **Recommendation:** (i). D58's cost basis already assumes 64k.
- **Depends on:** D62's sizing.

**12. Fit evidence per project, and when** [new; Claude F13; Codex Q50]
- **Question:** what fit evidence must exist before A21, and what waits for each
  project's own registration?
- **Options:**
  - (i) §15's staging: before A21, the all-project build and review with per-call
    fit from each project's own sources (proxy fit labelled as such for
    VOICE_PEDIATRIC and Kids First), and CHORUS's D62/D63 fit before its registration;
    each other project's allowance and full sizing at its own registration;
  - (ii) as (i), but VOICE_PEDIATRIC and Kids First sized only at their registration,
    from their own full phase, through runtime admission;
  - (iii) hold A21 until all six are sized with their own records, which cannot happen
    before two of them have records.
- **Recommendation:** (i).
- **Depends on:** D44, D58, D62, D63.

**13. What makes a run clean** [new; Claude F10, A10]
- **Question:** which test puts a run in the clean set rather than the assisted one?
- **Options:**
  - (i) §7's checks, applied mechanically: the journal verifies, no override, the
    D57 heads match, no interrupted write, nothing edited;
  - (ii) the owner's judgement per run, recorded.
- **Recommendation:** (i). Membership of every analysis set becomes mechanical.
- **Depends on:** D55–D57 and #5212's composition.

**14. Acceptance when the two D36 reviewers disagree** [new; Codex F11, Q22]
- **Question:** what happens when the Claude and Codex acceptance reviewers disagree
  on
  a rejecting-class finding?
- **Options:**
  - (a) both dispositions are kept; the owner adjudicates before signing; a sustained
    rejecting-class finding rejects; unresolved evidence blocks acceptance;
  - (b) as (a), with a third blind adjudicator before the owner signs;
  - (c) any disagreement rejects.
- **Recommendation:** (a).
- **Depends on:** D36.

**15. The receipt reading that decides acceptance** [Codex Q49]
- **Question:** which receipt and checker reading decides acceptance, including any
  later re-receipt?
- **Options:**
  - (a) v4 with D37, on the frozen `O,R1` snapshot; `Rf` readings and v5 are separate
    diagnostics;
  - (b) a separately reviewed re-receipt amendment before the affected runs;
  - (c) hold, if the selected route cannot reproduce the frozen snapshot reading.
- **Recommendation:** (a), with (c) if readback fails. An acceptance failure is never
  repaired by replacing `R1` with `Rf`, or by activating v5.
- **Depends on:** D37 and #5158's implementation.

**16. What records P4** [new; Claude F23, A12]
- **Question:** what act performs P4?
- **Options:**
  - (i) the owner's word naming this file's sha256 at a named commit, recorded in the
    decision record, with the merge following;
  - (ii) the merge itself, as the generation plan words it.
- **Recommendation:** (i). It binds the exact bytes, independently of any later merge
  commit. The generation plan's P4 wording is then amended to match.
- **Depends on:** nothing.

#### Group B: the analysis rules (fixed at P4a; at P4b only if P4a names the item)

**17. D02: the primary comparator and the metric hierarchy** [pending D02; Codex Q02]
- **Question:** Which comparator and metric hierarchy does the confirmatory analysis
  register?
- **Options:**
  - (a) the v8 package contrast, with the deterministic metrics primary and E5
    secondary;
  - (b) the v9 CHORUS canary as a descriptive reference only;
  - (c) feasibility and descriptive reporting only, with no directional comparison.
- **Recommendation:** (a), conditional on item 2 funding a production comparison. The
  v9 canary stays a secondary n=1 reference.
- **Depends on:** item 2. It gates E2's comparator manifest and E5.

**18. D02: the AI_READI comparator, and the AI_READI pilot's baseline** [pending D02; Claude A5; Codex Q03, Q04]
- **Question:** Which records are AI_READI's v8 comparator, and with which baseline
  does the AI_READI pilot run?
- **Options:**
  - (a) v8 `04g`, labelled cross-arm;
  - (b) AI_READI descriptive only;
  - (c) the `2026-10-14b` agentic no-crate rerun, which also changes runtime,
    provider, transport and effort, and needs a reviewed data PR first;
  - (d) a new no-crate v8 API run on the historical v8 code with only the bundle
    swapped (billed, about $10–14), used only if a render diff shows that only the
    bundle differs.
- **Recommendation:** (b), unless item 2 funds AI_READI; then (d) if the parity check
  passes, otherwise (b). Under (b) the AI_READI pilot runs with no `--canary-baseline`,
  so the A11 rows decide; under (a) its baseline is informational only (item 34). The
  `d22b61a9` plan gates still need amending.
- **Depends on:** item 2. It gates K (item 21) and the E2 roster.

**19. D02: the Set A definition and the eligible-record rule** [pending D02; Claude A6; Codex Q05, F5]
- **Question:** Which records does each arm contribute to Set A?
- **Options:**
  - (a) definition (2) primary and (1) as a sensitivity row, with §3's
    last-eligible-record rule;
  - (b) definition (1) primary;
  - (c) both descriptive, with no directional Set A verdict.
- **Recommendation:** (a). Cells carry equal weights. v8 pooled coverage is then 0.592
  for VOICE, not 0.462, and 0.538 for AI_READI, not 0.491. v8 rep1's survivorship stays
  a stated confound.
- **Depends on:** nothing.

**20. Missing cells, snapshots and metrics** [proposed; Codex F5, Q06; Claude B5]
- **Question:** When does a project get a primary directional verdict, if cells,
  snapshots or metrics are missing?
- **Options:**
  - (a) a primary project verdict needs complete n=3 and every required snapshot;
    a reduced n is descriptive and "not measured";
  - (b) n=2 may be primary under a separately fixed rule, n=1 descriptive;
  - (c) every comparison descriptive.
- **Recommendation:** (a), with "out of scope is not missing" (item 2) and the three
  kinds of missing kept apart.
- **Depends on:** item 19.

**21. K and the primary pool** [proposed; Claude F12; Codex Q29]
- **Question:** Which projects count in K, and which pool decides row 4, when
  AI_READI's contrast crosses an arm?
- **Options:**
  - (i) K counts only like-for-like in-scope projects. AI_READI is a labelled separate
    row under (a) and (c), descriptive under (b), and in K under (d) only after the
    render-parity check. The three-project pool decides row 4;
  - (ii) K counts AI_READI under (a) and (c) too, and a labelled mixed-input pool
    decides.
- **Recommendation:** (i).
- **Depends on:** items 2 and 18.

**22. Prediction 1: populated leaves** [proposed; Claude A7; Codex Q25]
- **Question:** Is a fall of up to 10% in populated leaves compatible with prediction
  1?
- **Options:**
  - (a) v10 mean ≥ 0.9 × v8 mean, worded as non-inferiority;
  - (b) v10 mean ≥ v8 mean;
  - (c) descriptive.
- **Recommendation:** (a). The disclosed assisted CHORUS records sat at 28–35% of v8's
  mean, so row 1 may well fail for CHORUS, which would be a legitimate result.
- **Depends on:** item 20.

**23. Prediction 2: pre-completion coverage** [proposed; Claude A7, F6, F11; Codex Q26]
- **Question:** Which rule judges v10's pre-completion coverage against v8's stored
  final coverage?
- **Options:**
  - (a) v10 pooled ≥ v8 pooled − 0.05, with the numerator rule, the stored v8 values
    primary and complete snapshots;
  - (b) zero tolerance under one common checker, where the inputs can be recovered;
  - (c) descriptive only, as a timing and instrument contrast, with D37 acceptance
    kept separately.
- **Recommendation:** (a). The Codex pass recommends (c), because final-v8 against
  phase-1-v10 crosses timing and instrument; the numerator rule answers part of that,
  not all of it. The disclosed assisted values would pass (a) by about 0.55, with
  smaller numerators.
- **Depends on:** items 19 and 20.

**24. Prediction 3: the recall metric** [proposed; Claude A7; Codex F10, Q27]
- **Question:** Which lineage and version metrics does prediction 3 use, and which
  ceilings are exempt?
- **Options:**
  - (a) row 3's corrected carriage counts: top-level lineage, the fact-specific
    b2aiprep v3.0.0 measure for VOICE, the one enumerated ceiling, ties failing;
  - (b) the script's recursive lineage count and "tools with a version token" as they
    are, named as lexical carriage proxies, with a weaker interpretation;
  - (c) source-adjudicated recall of each target, with recomputed baselines;
  - (d) descriptive.
- **Recommendation:** (a). Its v8 baselines are unchanged, recomputed for this
  revision.
- **Depends on:** nothing.

**25. Prediction 3a: inventions** [proposed; Claude A7, F17; Codex Q28]
- **Question:** What counts as an invention in prediction 3a, and what happens when a
  required record is missing?
- **Options:**
  - (a) the exact named-slot zero rule, with the VOICE clause, and an absent required
    record "not measured";
  - (b) source-adjudicated unsupported parent or software assertions anywhere in the
    record, under a frozen manual;
  - (c) descriptive counts.
- **Recommendation:** (a), once the #3289 adjudication is re-read against `1a58ad7b`.
- **Depends on:** that re-read.

**26. The E2 and E5 v10 rosters** [new; Claude F4, C2; Codex F9]
- **Question:** Which v10 records do E2 (row 4) and E5's analysis (row 5) use?
- **Options:**
  - (i) each in-scope cell's first clean attempt that left an eligible full record,
    accepted or not, for rows 4 and 5, with the accepted finals as a sensitivity row;
  - (ii) all clean attempts, cell-weighted;
  - (iii) accepted finals, as before, with row 4 made descriptive and row 5 labelled
    conditional on acceptance.
- **Recommendation:** (i). Row 4 becomes falsifiable. Extra reviews and ratings arise
  only where a cell needed a second attempt, and E5b-reg must add those records.
- **Depends on:** items 2, 18 and 20.

**27. Prediction 4: weighting and verdicts** [proposed; Claude A7, F18; Codex Q29]
- **Question:** How are row 4's rates weighted, and how are its two rates combined?
- **Options:**
  - (a) claim- and leaf-weighted pools primary, equal-project weights as a
    sensitivity, and two verdicts, 4a and 4b;
  - (b) equal-project rates primary, the pools as a sensitivity;
  - (c) descriptive.
- **Recommendation:** (a): zero tolerance, ties hold, and missing or unadjudicated
  units never pass.
- **Depends on:** items 21, 26, 43 and 44.

**28. Prediction 5: Q11 and Q19, and E5's analysis roster** [proposed; Codex F9, Q30]
- **Question:** Which tolerance and combination apply to Q11 and Q19, over which
  ratings?
- **Options:**
  - (a) two verdicts, each v10 mean ≥ v8 mean − 0.5 on the item's scale, over one
    primary rating per record of E5's analysis roster;
  - (b) zero tolerance for each;
  - (c) descriptive.
- **Recommendation:** (a), once item 45 fixes the scale. Repeat ratings measure
  reliability only.
- **Depends on:** items 26, 45 and 46.

**29. Rows 6–8** [proposed; Codex Q31–Q33]
- **Question:** Do rows 6–8 stay an invariant and two descriptive rows, as written?
- **Options:**
  - (a) as written: row 6 an acceptance invariant, with validity failures over all
    started attempts reported as feasibility; row 7 descriptive under named
    instruments; row 8 n=3 primary, with n=2 a sensitivity on common positions;
  - (b) as (a), but row 7 directional under one pinned checker;
  - (c) all three descriptive only.
- **Recommendation:** (a).
- **Depends on:** item 20.

**30. Set B's common gate** [proposed; Codex F12, Q07]
- **Question:** What exactly is Set B's common gate?
- **Options:**
  - (a) §3's recipe: the five named floors, measured; one common v4 checker on
    copies; the coverage row excluded; separate E2 and E5 intersections;
  - (b) the stored instruments' gates, as a clearly historical sensitivity;
  - (c) no Set B verdicts, only defect strata.
- **Recommendation:** (a).
- **Depends on:** item 19.

**31. The automatic-success estimand** [proposed; Codex F13, Q24]
- **Question:** Is automatic success measured over every unassisted start, or only
  over runs that stayed clean?
- **Options:**
  - (a) both proportions, with the one over all attempts started without assistance as
    the feasibility headline;
  - (b) the clean conditional proportion only, named as such;
  - (c) no proportion, only a complete attempt-flow table.
- **Recommendation:** (a).
- **Depends on:** item 13.

**32. D20: the production-floor rule** [pending D20; Claude F3, A4; Codex F6, Q12]
- **Question:** Which rule, fixed now, sets the production floor's value at A15?
- **Options:**
  - (i) the lowest accepted pilot's D37 fraction, rounded down to 1/20, which can
    register 20/20;
  - (ii) as (i), capped at 19/20;
  - (iii) the lowest fraction minus 0.05, rounded down;
  - (iv) 19/20 fixed for all production.
- **Sub-rules under (i)–(iii):** accepted pilots only, each read from its accepted
  attempt's `O,R1`. If AI_READI is out of scope, the re-canary alone sets the value; the
  Codex pass's alternative is no value until an amendment. A missing or
  zero-denominator input gives no value and no roster.
- **Recommendation:** (ii), with the re-canary-alone fallback. One unreceipted leaf can
  then never close a roster, and the floor is never stricter than the re-canary's. The
  Codex pass recommends (i) without the cap, and did not address the 20/20 case.
- **Depends on:** items 2 and 33. (iv) enables item 33's (d′).

**33. D03: cell roles and sequence** [pending D03; Claude A8; Codex Q08]
- **Question:** Which cells run, in which order, and in which role?
- **Options:**
  - (a) re-canary → AI_READI pilot → floor → CHORUS ×3 → production;
  - (a′) re-canary → floor → CHORUS ×3 → production in item 2's order, with the
    AI_READI pilot only if AI_READI is in scope;
  - (d′) as (a′), with the re-canary counting as CHORUS replicate 1: valid only under
    item 32 (iv), and only if a byte diff shows its model-facing inputs equal
    production's;
  - (b) only A21 now, and the rest at P4b.
- **Recommendation:** (a′), confirmed at P4b. It takes the AI_READI pilot (about
  $162–191) off the critical path; if AI_READI is descoped, the owner waives #2926's
  AI_READI pilot for this condition. The Codex pass recommends (b) at P4a, with (a) as
  the frozen proposed path.
- **Depends on:** items 2 and 32.

**34. May a pilot be rejected for exceeding v8's per-project worst?** [proposed; Claude A9; Codex Q04]
- **Question:** May a pilot be rejected for exceeding v8's per-project worst on the
  seven defect metrics?
- **Options:**
  - (i) no: the comparison is recorded as evidence for A13 only;
  - (ii) yes, on any regression, which is D21 (a) applied to pilots;
  - (iii) only on a regression in report findings.
- **Recommendation:** (i). The bars are mostly zero, and they come from a different
  package.
- **Depends on:** item 18.

**35. D21: production gating, continuation and the launch route** [pending D21 and D20's route clause; Claude B1, B9; Codex Q13]
- **Question:** How do production rosters gate and continue, and through which launch
  route?
- **Options:**
  - (a) D21 (b) with continuation (ii): absolute floors and no `--canary-baseline`; a
    stopped label is never re-run; continuation runs under a new prefix, registration
    and word; every API launch goes through `d4d api batch`;
  - (b) as (a), and production is also gated on v8's seven per-project worst values;
  - (c) an adjudicated-continue path built into `d4d api batch`;
  - (d) the condition ends at any roster stop.
- **Recommendation:** (a). It matches D56, under which a retry needs a new
  registration.
- **Depends on:** item 37.

**36. The A15 choice after a pilot's terminal single-delivery failure** [proposed; Codex F7, Q14; Claude B2]
- **Question:** If a pilot ends in a terminal single-delivery failure, what may change
  at A15, and how does the analysis treat it?
- **Options:**
  - (a) continue the unchanged D21 (b) procedure under new registrations;
  - (b) introduce D21 (c) as its own procedure stratum, under a reviewed, prospective
    analysis amendment;
  - (c) end the condition and register the next version.
- **Recommendation:** (a), or (c) if the failure shows that the condition is
  infeasible. None of them sits "outside the confirmatory analysis" (§9).
- **Depends on:** items 4 and 35.

**37. The defect-class stop-loss and A13** [proposed; Claude B3, F22; Codex F8, Q15]
- **Question:** What counts toward the defect-class stop-loss, and does a pilot's
  rule-level rejection end the condition?
- **Options:**
  - (a) A13 governs pilots: the first rule-level rejection ends the condition. In
    production, two rejections with the same recorded root cause, counted across this
    API condition and never reset, end it;
  - (b) any first rule-level rejection, pilot or production, ends it;
  - (c) two of any cause end it, which amends A13.
- **Recommendation:** (a).
- **Depends on:** item 38.

**38. Stop classification** [proposed; Claude B4; Codex F8, Q16]
- **Question:** How is a stop with mixed, ambiguous or unknown causes classified?
- **Options:**
  - (a) §10's table: several diagnostic tags, one primary class by a frozen
    precedence, and unknown causes held for the owner;
  - (b) mutually exclusive categories, assigned by an independent reviewer under a
    frozen manual;
  - (c) any ambiguous case ends the condition.
- **Recommendation:** (a). A convenient harness label can never exempt a substantive
  rule defect.
- **Depends on:** item 7.

**39. A13's "operational" contingency** [proposed; Claude B4; Codex Q17]
- **Question:** Which stops does A13's "transport or operational cause" cover?
- **Options:**
  - (a) transport, record-shape and budget stops allow one contingency, and an
    impossible-limit stop does not (§10, rows 5–7);
  - (b) transport only;
  - (c) no contingency in this condition.
- **Recommendation:** (a), within each cell's two attempts, and never by resuming a
  terminal run.
- **Depends on:** items 7 and 38.

#### Group C: before production rosters (P4b)

**40. D15: Kids First** [pending D15; Claude B7; Codex Q10]
- **Question:** Which route, order and floor does Kids First take?
- **Options:**
  - (i) API after plan A14-acc and A15, with the registered floor;
  - (ii) last in item 2's order, run only if funded and fitted at its own
    registration; if admission refuses it, D33's descriptive own condition applies;
  - (iii) defer it, pending its own fit and D58's scope;
  - (iv) drop it from this condition.
- **Recommendation:** (ii): one resource-level descriptive record under the neutral
  context, never cleared by substituting AI_READI's inputs. The Codex pass recommends
  (iii) now and (i) only if later funded and fitted.
- **Depends on:** items 2 and 12.

**41. VOICE_PEDIATRIC ×1 or ×3** [pending D02; Claude B8; Codex Q09]
- **Question:** How many VOICE_PEDIATRIC runs, and in what role?
- **Options:**
  - (a) ×1, descriptive, if funded;
  - (b) ×3, if replicate variance is a stated need and it is funded;
  - (c) defer.
- **Recommendation:** (a), at about $96–118 per run with no comparator. It is never an
  adult VOICE replicate or part of K.
- **Depends on:** item 2.

**42. Canonical marks across prefixes** [Codex Q47]
- **Question:** How are canonical marks kept to accepted cells across prefixes?
- **Options:**
  - (a) rank with the existing criterion, but only within an accepted-cell list taken
    from the acceptance records;
  - (b) leave cells unmarked until an accepted-only selector exists;
  - (c) an owner-recorded manual mark under the same criterion.
- **Recommendation:** (a) if the procedure is reviewed, otherwise (b). A canonical mark
  never changes an estimate.
- **Depends on:** item 35.

#### Group D: before E2 and E5

**43. D24: the review-pass instrument** [pending D24; Claude C1; Codex Q21]
- **Question:** Which instrument measures the two review-pass rates?
- **Options:**
  - (1) E2's blind source review, with §16's units and weights;
  - (2) calibrate the support judge first, which delays E2;
  - (3) the support judge as a secondary measure, after #3343's paid calibration.
- **Recommendation:** (1).
- **Depends on:** nothing.

**44. E2's protocol freeze, reviewers and blinding** [new; Claude F19, C3; Codex F11, Q22]
- **Question:** who reviews, how blind, and when is the protocol frozen?
- **Options for the reviewers:**
  - (i) a fresh Claude session plus a Codex pass, D36's pattern applied to E2;
  - (ii) a cross-family rater;
  - (iii) human reviewers.
- **Options for the freeze:**
  - (a) at P4b, before any confirmatory launch word, by a named author who declares
    which v10 records they have read;
  - (b) at P4a, which delays A21 until the manual exists;
  - (c) defer prediction 4 to a separate prospective study.
- **Recommendation:** (i) and (a), with the seeded blinding transformation, and arm
  guesses recorded before scoring (§12).
- **Depends on:** item 43.

**45. Rubric20's version (E4, #2911) and the evaluator identity** [pending owner, #2911; Claude C4; Codex Q23]
- **Question:** Which rubric20 version and evaluator implementation does E5 use?
- **Options:**
  - (a) the reviewed 3.0-based successor, with the D52/D61 changes versioned and
    pinned;
  - (b) 4.0, with its normative-example approval and nine-case Q19 calibration;
  - (c) defer E5, and drop prediction 5's directional rule.
- **Recommendation:** (a), unless 4.0's calibration is approved before E5's
  registration. Row 5 reads Q19, so that calibration matters.
- **Depends on:** D52, D61.

**46. E5's funding and scope** [Claude C5]
- **Question:** How is E5 funded and scoped?
- **Options:**
  - (i) one joint re-rating, scaled to item 2's scope (about $190–394 for the full
    matrix);
  - (ii) defer E5, which leaves row 5 unmeasured;
  - (iii) use the stored v8 ratings, which come from older instruments.
- **Recommendation:** (i).
- **Depends on:** items 2, 26 and 45.

**47. The audit-recall matching rule** [Codex Q48]
- **Question:** When and how is the audit-recall matching rule fixed?
- **Options:**
  - (a) freeze the matching rule and adjudication before the relevant audit is opened;
  - (b) keep D36's blind observations as a seed, and make no scored recall claim yet;
  - (c) fund a separate human-annotated recall study.
- **Recommendation:** (b), unless a reviewed exact rule already exists. The seed is
  still written before anyone reads the audit (D36).
- **Depends on:** D36.

#### Group E: native and optional arms

**48. D29: native effort and account** [pending D29; Claude D1; Codex Q43]
- **Question:** Which effort level and which first-party account does the native
  registration name?
- **Options:**
  - (a) the runtime's default effort level for the model, recorded as such, and an
    owner-named first-party account;
  - (b) explicit `high`;
  - (c) explicit `max`, as the generic_v9 direct arm used;
  - (d) defer native registration until both are supplied.
- **Recommendation:** (a), with seven-day quota headroom checked before launch: the v3
  direct run stopped at 0.96–1.0. The Codex pass recommends (d) unless the owner
  supplies both now. No account is inferred, and "default" is never equated with an
  effort level.
- **Depends on:** nothing on the API side; it gates only the native canary.

**49. Native acceptance rows** [new; Claude F20]
- **Question:** When are the native canary's acceptance rows specified?
- **Options:**
  - (i) a dated native amendment of this plan lists them, reviewed and ratified before
    the native launch;
  - (ii) list them now.
- **Recommendation:** (i), since the native condition's acceptance evidence is not yet
  settled.
- **Depends on:** item 48 and the native gates.

**50. D04: the CHORUS crate path** [pending D04; Claude D2; Codex Q11]
- **Question:** Does this study include the optional with-crate CHORUS stage?
- **Options:**
  - (a) defer it;
  - (b) path B after plan A16-acc, separately funded, registered and analysed: about 4
    runs at roughly $40–60 each;
  - (c) path A, as a separate future condition with a changed bundle.
- **Recommendation:** (a), given D58's budget, unless the paper needs the crate delta
  and it is funded.
- **Depends on:** item 2.

**51. The remaining legacy and native pending IDs** [Claude D3; Codex Q35–Q42, Q44–Q46]
- **Question:** D08 aside, the generation plan's D09 (its remainder), D11–D14, D16,
  D18
  and D25 are pending. Are they part of this P4?
- **Options:**
  - (i) out of scope for the API P4a: each goes to the native registration's own
    amendment, and none is a prerequisite for A21;
  - (ii) decide them now, on the Codex pass's per-ID recommendations;
  - (iii) decide only D16 now (no monolithic API baseline in this matrix), and defer
    the native ones.
- **Recommendation:** (i). Their subjects, with the Codex pass's recommendations:
  - D09's remainder: scope the 2026-09-25 direct-arm pause to the old generic_v9 arm;
  - D11, the native binary and its hash: defer;
  - D12, native roles: the owner names an operator and a review pair;
  - D13, toolchain exposure, launch flags, the runtime-closure fix and receipt origin:
    pin each before native registration;
  - D14, the native spend package: validate the old proposal against current evidence;
  - D16: no monolithic API baseline in this matrix;
  - D18: a two-week time-box, if native work continues;
  - D25: no native canary counts as a replicate, and no native production is planned
    here.
- **Depends on:** item 48.

#### Dependencies

- **D58's budget** decides item 2. Item 2 decides K (21), the rosters (26), the floor's
  fallback (32), the sequence (33), Kids First (40), VOICE_PEDIATRIC (41), E5's scope
  (46) and the crate path (50).
- **Item 18 (D02's AI_READI comparator)** decides K and the E2 roster, so D02 gates the
  comparison batch, the AI_READI pilot's baseline, and whether the `d22b61a9` plan gates
  matter.
- **Item 32 (D20)** feeds plan A15's amendment, which gates plan A16. Its option (iv)
  enables item 33's (d′).
- **Row 4** needs items 26, 27, 43 and 44. **Row 5** needs items 26, 28, 45 and 46.
- **Item 13** decides membership of every analysis set.
- **Item 9 (D08)** gates A21's risk acceptance and every multi-row roster.
- **D62 and D63** feed the A21 registration. Each later project needs its own
  allowance decision (item 12).
- **Items 48–51** gate only the native arm and the optional crate stage.

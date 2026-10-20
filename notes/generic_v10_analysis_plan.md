# generic_v10 analysis plan (preregistration draft)

**Status: DRAFT for P3 review. Not preregistered, and it authorizes nothing.** This
is step P2 of `notes/d4d_generation_plan_2026-10-09.md` ("#### P2"). The plan becomes
binding only when the owner merges it with an explicit word (P4). Until then, no
generic_v10 registration hash is put to the owner, and no billed generic_v10 step runs
(the plan: "Every billed generic_v10 step depends on P4").

- **Drafted:** 2026-10-20, by the Claude worker session (coordination Lane C2), at main
  `0a1132ecf`, on branch `claude/track-p-analysis-plan`. agy integrates the branch.
- **Inputs:**
  - the plan, sha256 `fcc78fab909f94e533d2ed8e00ebc3d5165c82a9d30fcc7aa87db4541ae1266e`;
  - P1, `notes/p1_v8_comparability_recompute.md` (this branch), which holds every v8
    number cited here;
  - `notes/recall_target_baseline.md`;
  - `notes/arm_comparison.md`.
- **Plan dependencies:** P2 depends on G3, P1, A1 and A1b. P1 is done. G3 is partly
  decided (see the decision status below). A1 and A1b are not done, so every number
  that depends on them is marked pending.

Rules that rest on an undecided owner decision are marked **[pending Dxx]**, followed
by the plan's recommendation. Each is a proposal for the owner to confirm or amend at
P4, not a ruling. Nothing in this draft asserts a decision the owner has not recorded.

## Decision status (2026-10-20)

Since the plan was written (2026-10-09), owner rulings have been recorded only for D06
and D07, both on 2026-10-19. D10 and D22 were decided today in the Claude worker
session.

| ID | Status | Where recorded |
|---|---|---|
| D06 | **Decided 2026-10-19.** Every generic_v10 API registration declares `{"type": "adaptive", "display": "summarized"}`, the routed v10 conditions included (keyed on the condition's base, v10). There is no typed-stage cache breakpoint in this condition. | #1849 comment of 2026-10-19 |
| D07 | **Decided 2026-10-19, option 1.**<br>- A $100 named generic_v10 API pilot allocation: CHORUS pilot $15 cap, one CHORUS contingency $15, AI_READI pilot $35 planning ceiling, one AI_READI contingency at most $35.<br>- At most 2 billed attempts per registered cell, then an owner review.<br>- Every run needs its own owner word naming its registration sha256 (for a roster, the roster sha256 and each registration sha256 it lists) and its cap.<br>- `d4d api batch --max-cost-dollars` is the between-run stop.<br>- The operator trigger is the cap minus the worst-case in-flight call: at most about $11.50 against $15 for CHORUS.<br>- The AI_READI lines are provisional (see item 15). | #1763 comment of 2026-10-19 |
| D10 | **Decided 2026-10-20: retire** the v10z/audit_controls lineage and audit28. | Owner's answer in the Claude worker session. `notes/reviews/v10z_retirement_2026-10-20.md` (this branch). agy is to post it on #4761. |
| D22 | **Decided 2026-10-20: withdraw.** The v10z standing authorizations do not extend to generic_v10, and they are withdrawn now. | Same record. agy is to post it on #1763 and #4761. |
| D01–D05, D08, D09, D11–D21, D23–D25 | **Pending.** No owner ruling is recorded. | Several issues carry "Resolved" comments that cite `c92d89824` (#2930, #2926: D01, D07 and D15), `25994a4d2` (#2914: D04) and `d9f7d9a72` (#4758, #4759, #4761). None of those commits is on any remote branch. #2914, #4758, #4759 and #4761 were reopened on 2026-10-13 because those comments did not reflect owner decisions. D07 has since been decided (2026-10-19, above); D01 and D15 have not. This draft treats every decision in this row as pending. |

## 1. Estimands (P2 item 1)

1. **Feasibility and acceptance.** For each registered cell, the outcome is accepted
   or rejected (A11–A13), with its attempt count. Per stage and project, the outcome
   is the share of billed attempts that ended in an accepted record. Pilots are
   reported separately from production.
2. **Package effect against v8.** For each primary metric in item 2, the difference
   between the generic_v10 confirmatory cells and the v8 confirmatory records,
   project by project. It is a **package-level** effect: everything listed in item 4
   changes together, and nothing here attributes a difference to any one component.
3. **Replicate structure (#2932).** The structure metrics of item 2 for the 3-replicate
   v10 cells against v8's 3 replicates of the same project.
4. **External feasibility.** VOICE_PEDIATRIC and Kids First: whether an accepted
   record is produced, plus descriptive metrics. There is no comparator.
5. **Cross-arm contrast (API against Claude Code direct).** **[pending D09]** The plan
   recommends option (a) for the first Claude Code canary, with every such cell
   labelled the direct arm, not native. Any contrast is then preregistered as
   runtime, provider, transport and effort together, never as one of them.

## 2. Comparator, metrics and cell roles (P2 item 2; [pending D02])

**Comparator** (D02's recommendation): the v8 API fill.
- Prefix `2026-09-04f` for CHORUS and VOICE, and `2026-09-04g` for AI_READI and CM4AI:
  12 records, 3 per project, listed with their sha256s in P1.
- Excluded: the `04` and `04b`–`04e` canaries and the invalid `04f` AI_READI rep1.
- The v9 CHORUS canary (2026-09-12) is a secondary single-point CHORUS reference.

**Cell roles** (D03's recommended option (a), **[pending D03]**):

| role | cells | counts as a replicate | analysed as |
|---|---|---|---|
| CHORUS pilot (A10) | 1 | no | pilot, separately |
| AI_READI pilot (A14) | 1, started only after the CHORUS pilot passes blind source review | no | pilot, separately |
| CHORUS replicate gate (A16) | 3 under the A15 floor | yes | confirmatory |
| Production (A17) | CM4AI, VOICE and AI_READI, 3 each, in that order | yes | confirmatory |
| VOICE_PEDIATRIC (A18) | ×1 (D02's recommendation; ×3 only if the paper needs replicate variance) | — | descriptive, pooled with VOICE as one cluster |
| Kids First (A19) | ×1 | — | descriptive **[pending D15]** |
| With-crate CHORUS (A21–A22) | only under D04 path B | — | separate stage **[pending D04]** |

The v10 confirmatory set is therefore 12 records: the CHORUS gate plus the 9
production records. That matches E2's 12 v8 + 12 v10 comparison batch.

**Primary metrics.** These are deterministic, with D02's list and P1's v8 values:
- populated leaves in the full record (`receipts.populated_leaves`);
- recall-target counts under cue sha256 `768a26a3…` and tools pattern `4726c005…`
  (`scripts/recall_target_baseline.py`);
- receipt coverage, `with_receipt / receiptable`, with its denominator;
- #2932 replicate structure (`replicate_structure.compare_structure` and
  `summarize`);
- validation, duplicate keys and report findings.

**Secondary metrics:**
- rubric scores from one joint re-rating (E5);
- the D24 review-instrument counts (item 16);
- the seven D21 defect metrics, reported (item 9).

## 3. Rules for n=1 and n=3 (P2 item 3; [pending D02])

D02 recommends that every n=3 comparison be descriptive: per project, v10 rep values
beside v8 rep values, with mean ± SD and min–max. There is no "v10 mean at or above
the v8 minimum" test, unless the owner preregisters a numeric tolerance per metric at
P4. Any such tolerance must be written into this plan before P4 and cannot be added
after any v10 data exist. n=1 cells (pilots, VOICE_PEDIATRIC ×1, Kids First) are
descriptive only.

## 4. Confounds (P2 item 4)

Every one of these differs between v8 and the v10 API arm at once, so all effects are
package-level (plan risk 21, D02):
- **Prompt:** the generic_v10 text against `d4d_generic_arm_prompt_v8.md`.
- **Harness:** renderer 25's typed audit and receipt completion against v8's
  four-phase runner, and renderer 26 against 25 where it applies. The
  receipt-completion turn means v10 coverage is post-turn and v8 coverage is not.
- **Schema:** 2.0.0 against 3.0.0, and the change in the digest's term source. P1
  shows that no v8 record's schema digest re-renders under today's renderer.
- **Caps:** the audit and report caps, 24k against 96k.
- **Thinking display:** v10 sends `display: summarized` (D06). v8 declared adaptive
  thinking with no display (the plan's D06: "as v8 and v9 did"). The v8 records
  predate the `model.thinking_requested` field, so this rests on the plan, not on the
  records.
- **AI_READI bundle scope (#5042):** the v8 AI_READI records read `d22b61a9`, a bundle
  that carried the dataset's RO-Crate. v10 will read `1a58ad7b`, without it (P1). The
  other three projects read byte-identical bundles.
- **Transport and provider:** both arms run CBORG `claude-opus-5`. Provider-side
  model drift under one model id cannot be excluded, so v10 records the returned
  model identity per call (plan G4).
- **Effort:** a fixed confound. The API arm runs at the provider default (D09), as v8
  did (each v8 record's `unverified` entry; P1). Any
  Claude Code cell runs at an explicit level chosen at N6.
- **Repository state:** `repo.dirty` will read true on every v10 run, because run
  inputs and outputs are untracked, as it did on all 12 v8 records (P1). Launch
  cleanliness is defined as `git status --porcelain --untracked-files=no` plus an
  allowlist of output paths.

The coordination prompt names four compounded factors: prompt, model, harness and
AI_READI bundle scope. The list above is the plan's fuller list. "Model" here means
provider-side drift under one model id plus the thinking display, since the model id
is the same.

## 5. Pilot acceptance rows (P2 item 5)

Under the pending floor, the registered receipt gate is **UNMEASURABLE by design**.
A10 expects exit 1 with "registered receipt gate unmeasurable". That exit is not a
rejection; the rows below decide.

Each must hold, and A11 records each:
- **Receipts:** `d4d receipts check --method claudecode_api --label <label> --project
  <P>` gives 0 unreviewed chunks, 0 unverified snippets, 0 gated findings and a
  receipt that is not vacuous.
- **Duplicate keys:** 0 in the full record and 0 in the core.
- **Report totals (#4766):** the report's stated finding total and severity subtotals
  equal `audit_counts` of the run's `intermediate/{P}_audit.json`. The stated values,
  the computed values and any mismatch are all recorded.
- **Caps:** every `full` row in `api_usage`, and `model.max_tokens_by_phase.full`,
  read 128000.
- **Provider:** `model.provider` reads 'LBL CBORG (proxy to Anthropic)' and
  `model.base_url` reads `https://api.cborg.lbl.gov`.

Reported, not gated:
- coverage as a fraction with its denominator (`with_receipt / receiptable`);
- #2926's items (the slot-driven re-receipt turn and the slot-coverage measures);
- per-call transport and empty-answer outcomes.

The `--canary-baseline` comparison for the pilots is in item 9.

## 6. Acceptance-record format (P2 item 6)

An acceptance record, written at A13, is a dated file committed in the run's data PR.
It carries:
- **Verdict:** accept or reject, and for a rejection the classified cause (transport
  or operational, rule-level, or instrument).
- **Identities:** the registration sha256, the roster sha256, and the sha256 of every
  artifact A11 confirms on disk.
- **Check rows:** each item-5 row, with its value.
- **Coverage:** as a fraction with its denominator.
- **Cost:** at that day's prices.
- **Reviewers:** references to the A12 blind source review and its reviewer, named
  under D23, never the generating session.
- **What the run does not establish:** for a pilot, one project, n=1, no load test
  and no recall test.

## 7. Attempt accounting (P2 item 7; D07 decided)

- **Every attempt counts**, stopped and rejected ones included, together with its
  usage rows.
- **Attempt bound:** at most 2 billed attempts per registered cell (D07), for example
  a pilot plus one contingency, or a replicate plus one D21 re-run. Then the owner
  reviews.
- **Pilots** are analysed separately, never as replicates (D03).
- **No replicate is chosen by score.**
- **Canonical marks are never used as the estimate.** Estimates use every accepted
  replicate of a cell.
- **Canonical marks** (A20) go only to accepted replicates, and pilots are never
  candidates. They use `d4d runs select --method claudecode_api --project P --config
  <prefix>`, with `--execute` only on the owner's word. Its criterion is fixed now:
  validity, then the fewest review adverse verdicts (differences of 2 or less are a
  tie), then the most slots, then the label. So remaining ties go to the lowest
  replicate, which is rep1.
- **Cells split across prefixes:** a cell that D21 splits across prefixes cannot be
  grouped by `d4d runs select --config`. It is marked by a recorded procedure or
  left unmarked (A20; a G4 gap).

## 8. The D20 floor rule (P2 item 8; [pending D20])

The proposed rule, D20's option 1 and the plan's default, is committed here before
the pilots:

> The registered receipt-coverage floor is the lower of the CHORUS pilot's (A10) and
> the AI_READI pilot's (A14) post-turn coverage fractions, `with_receipt /
> receiptable`, rounded down to the nearest 0.05.

The value is registered at A15, in a dated amendment PR that gets P3's review
(a Claude reviewer plus a Codex CLI pass) before the owner merges it. That amendment
creates a new registration identity and does not certify the pilots. A floor failure
stops the roster without discarding records.

For scale, from P1's per-record coverage:
- A 0.6 floor would fail 8 of the 12 v8 records: all three CHORUS (0.290, 0.335,
  0.394), VOICE rep2 and rep3 (0.540, 0.576), AI_READI rep1 and rep2 (0.583, 0.388)
  and CM4AI rep3 (0.581).
- This matches #2926's statement.
- v8 coverage is pre-turn, so it is context for the rule, not a comparator for it.

## 9. Gating and continuation of production rosters (P2 item 9; [pending D21])

D21 recommends option (b) with continuation (ii).

**Production rosters** gate on absolute floors only, with no `--canary-baseline`:
- the registered coverage floor, the receipt defect floors and duplicate keys gate
  every run;
- a blind check stops the roster as UNMEASURABLE;
- the seven defect metrics are reported but never gated.

**Pilots** keep `--canary-baseline`:
- CHORUS (A10): `2026-09-04f_claude-opus-5-api-generic-v8`;
- AI_READI (A14-reg): `2026-09-04g_claude-opus-5-api-generic-v8`. It is never `04f`,
  because that prefix's AI_READI rep1 is declared invalid.

The v8 per-project worst values, recomputed in P1:

| project | report findings | British spellings | pair errors, ungrounded identifiers, resolver URLs, organisational fragments, undeclared prefixes |
|---|---|---|---|
| CHORUS | 2 | 0 | 0 |
| VOICE | 1 | 2 | 0 |
| AI_READI | 1 | 0 | 0 |
| CM4AI | 0 | 0 | 0 |

**Continuation after any stop:**
- a stopped label is never re-run;
- the owner classifies the stop as transport, rule-level or instrument;
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

**Not adopted: a "< 0.55" trigger.** The coordination prompt states a "D21 < 0.55
single-delivery trigger (#5050)". No such threshold appears in the plan, on main, or
on the open integration branches. #5050 is the GitHub assistant smoke-test issue. This
draft keeps the plan's trigger above: any terminal single-delivery failure in either
pilot. If a numeric trigger is intended, the owner states it and its source before P4.

## 10. Caps, triggers and the single-delivery estimate (P2 item 10; D07 decided)

- **Caps:** as decided under D07 (decision table above).
- **Operator trigger:** the cap minus the largest worst case of any call that can be
  pending. The worst case comes from A3b's bounds, the pending phase's output cap plus
  its stated input. For CHORUS the plan puts the trigger at most about $11.50 against
  $15. The AI_READI triggers wait for A1 and A1b (item 15).
- **Stop-loss:**
  - the operator watches the A3b readout and runs `d4d api stop --label-prefix
    <prefix>` at the trigger, or after 2 h for the pilot (A10);
  - `--max-cost-dollars` stops between runs (#5045). It cannot recall an in-flight
    request, and an interrupted stream may still bill (#1849).
- **Single-delivery terminal-failure estimate:**
  - Typed stages and receipt completion admit exactly one delivery.
  - At v8's per-call rate of 8 retried calls in 92 (5 transport, 3 answer-level; P1),
    with independence assumed, a run with 4, 6 or 8 single-delivery calls ends
    terminally 30%, 42% or 52% of the time. Transport alone gives 20% (4 calls) and
    36% (8 calls).
  - A 3-row roster then completes without a stop in 11–34% of cases.
  - This is illustrative only. The pilots measure the typed-stage rates (item 18), and
    those, not this estimate, inform the A15 trigger decision.

## 11. Freeze (P2 item 11; [pending D17])

D17 recommends a freeze from the first generic_v10 registration until each arm
completes, unless v1 byte parity is shown and the remaining runs re-register. Every
registration pins the full and core schema closures, the bundle, the chunk manifest
and the source manifest.

Frozen are:
- schema releases (#3972, #3124);
- the draft PR #4508 (#4489);
- #2914 path A;
- source-manifest edits (#3414, decided before A4 or held);
- preprocessing changes (#2934);
- API runtime changes;
- any #4354 merge that touches the API path.

The launch worktree stays at the launch base for the whole matrix. Any advance follows
D17's procedure between stages, with no run live.

## 12. Blinding and reviewers (P2 item 12; [pending D23])

D23 recommends a mixed model:
- a human curator;
- a Claude reviewer plus a Codex CLI pass for registrations and code;
- named source reviewers for acceptance and for the comparison batch.

The owner names them at G3.

**Acceptance review (A12)** is blind source review of the unchanged originals against
the frozen bundle. It covers #1782, #1801/#2924, #1815, #1816 and #2924 dates, and
counts the #2918 and #2919 classes separately (D05). It never involves the generating
session, and it is not the comparison.

**Comparison batch (E2)** is separate from acceptance:
- 24 records: the 12 v8 confirmatory records and the 12 v10 confirmatory records;
- shuffled, and stripped of labels and provenance headers where feasible (#3280);
- reviewed blind to arm under the A12 protocol, with D24's counts and denominators;
- each review dated and bound to the record sha256;
- E2 starts after A17-acc. No v8 record has yet been reviewed under the #1782–#1816
  protocol.

**Joint re-rating (E5)** is one billed rating pass of the v8 and v10 records together,
on the E1 route:
- CBORG selected explicitly, refusing a session whose init line does not read
  `apiKeySource: ANTHROPIC_API_KEY`;
- contexts pinned by hash;
- the instrument version named (rubric10 3.0; rubric20 3.0 or 4.0 per E4, **[pending
  owner, #2911]**);
- preamble and check-echo (#1077);
- a rubric20 repeat panel (#2912);
- every output validated with `validate_evaluation_schema.py --file`, exit 0.

E5 needs its own registration, review and owner word. D22's withdrawal means no
standing authorization covers it.

## 13. Labels and launches (P2 item 13)

- One distinct date-letter prefix per roster.
- `generic-v10` as a delimited label token.
- No `pilot` or `canary` word in any label.
- Outputs are copied, never moved, into data PRs, so the #795 guard keeps passing.
  The launch worktree is never fast-forwarded over those data PRs except by D17's
  procedure.
- A stopped label is never re-run.
- Every generic_v10 launch, continuations included, goes through `d4d api batch` with
  a roster, never `d4d api run` (D20). `d4d api run` has no floor verdict, canary
  block, run lock or #795 guard.
- Immediately before every billed launch, the operator hashes the roster, every
  registration it lists and the launcher script, and stops on any difference from the
  sha256s named in the word and the review (A10).

## 14. Fixed model-facing values (P2 item 14)

- **One receipt-completion registration body** (`receipt_completion_registration_v2`)
  for every project and role, identical apart from the floor. The floor is pending
  until A15.
- **Neutral identifiers:** that body's `registration_id` and `context_limit_basis` are
  neutral.
- **Audit limits:** the model-facing audit limits are the ones A1 identifies by
  rendering twice with one limit changed. At `15d053d1a` those include at least
  `max_request_bytes` and `omission_output_tokens`. They are fixed across projects
  and sized for the largest bundle. Only non-model-facing allowances vary.
- **Registration ids:** each registration's top-level `registration_id` differs,
  because a roster refuses a reused one. It is neutral and sits outside the fixed
  receipt body.

The values themselves are set at A6 from A1, A1b and A3, and reviewed at A7. This
draft fixes the rule, not the numbers.

## 15. Stage caps and non-model-facing allowances (P2 item 15; pending A1 and A1b)

Pending. Two sources will fill this item:
- **A1 (offline sizing):** the Claude worker session's Lane C1 note,
  `notes/a1_offline_sizing_2026-10-20.md` on branch `fix/5072-offline-sizing-recovery`.
  It was not yet written when this draft was made.
- **A1b (unbilled `count_tokens`):** run by agy.

This draft gives no sizing figure. #5072 records that the 2026-10-12 A1b calibration
report printed PASS on rows whose totals exceed its stated window, so it is not launch
evidence until re-measured on the selected condition's payloads.

A1's AI_READI floors also predate #5042: the plan's "bundle 542,513" is the old
bundle. Today's bundle is 430,393 bytes. Whatever the figures turn out to be, the
rule is fixed:
- each counted request plus its output cap fits the route's window;
- the report and its regate, with the 96k output cap, are counted figures (A1b);
- if an AI_READI worst case does not fit, A14 waits for the owner's decision
  (D07's re-plan clause).

## 16. Instrument for the review-pass predictions (P2 item 16; [pending D24])

D24 recommends option 1. The "unsupported-claim rate" and "adverse-slot rate" of
#2930 are measured in the blind E2 comparison batch, as per-record counts of the
rejecting classes over a stated denominator:
- #1782: plans stated as current, and scope;
- #1801 and #2924: roster roles;
- #1815: attribution;
- #1816: qualifiers and headers.

The support judge is excluded from preregistered predictions until #3343 is
calibrated under its own registration and word.

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

Each prediction names its metric, comparator, decision rule and instrument, fixed here
before any v10 data exist. Status is **proposed** until P4. The comparator throughout
is the v8 confirmatory records of the same project (item 2). The decision rule
throughout is descriptive, per item 3, unless the owner adds a tolerance at P4.

| # | prediction (#2930, restated against v8 per D02) | metric and instrument | v8 values (P1) |
|---|---|---|---|
| 1 | Populated leaves do not fall | `len(receipts.populated_leaves(full))` per record | AI_READI [525, 525, 449], CHORUS [235, 278, 251], CM4AI [422, 473, 479], VOICE [386, 297, 432] |
| 2 | Receipt coverage does not fall | `receipts.with_receipt / receiptable`, from `d4d receipts check`, with denominators | pooled 2310/4094 = 56.4%; per record in P1 |
| 3 | The recall rule raises recall where the bundle states the targets | `scripts/recall_target_baseline.py` (cues `768a26a3…`, tools `4726c005…`) per record. Tested only where v8 has targets (D02):<br>- AI_READI: variables 20/13/20.<br>- CM4AI: lexical candidates 9/5/3.<br>- VOICE: variables 4/4/4, lineage entries 1/1/1, lexical candidates 3/0/1, tools with a version token 0/0/0.<br>- CHORUS: lineage 1/1/0 only, since variables and lexical candidates are 0/0/0. | as listed |
| 3a | A rise is an error where the bundle states nothing | Same counts, read against the #3289 adjudication in `notes/recall_target_baseline.md`:<br>- no parent dataset in any of the four bundles;<br>- no processing-software version in the AI_READI, CHORUS or CM4AI bundles (CM4AI's versions belong to companion analyses);<br>- VOICE's one stated version is b2aiprep v3.0.0.<br>A v10 `parent_datasets` entry, or a software version for those three projects, is reported as a recall-rule overreach, not a gain.<br>The adjudication read the AI_READI bundle before #5042, when it still had its RO-Crate, which recorded FAIRSCAPE 1.2.1 as the metadata packager, not processing software. It is re-read against `1a58ad7b` before P4. | 0 today |
| 4 | The unsupported-claim and adverse-slot rates do not rise | The D24 instrument: E2 blind counts of the rejecting classes over a stated denominator | no v8 record reviewed yet; measured in E2 |
| 5 | Rubric20 Q11/Q19 do not fall (secondary) | E5 joint re-rating, instrument version per E4 | measured in E5 |
| 6 | Validation passes with 0 duplicate keys in every confirmatory v10 record | `validation.passed` and `duplicate_keys`, as the gate reads them | 12/12 passed, 0 duplicate keys |
| 7 | Report findings | `report_claims.findings`, the canary metric | worst: CHORUS 2, VOICE 1, AI_READI 1, CM4AI 0 |
| 8 | Replicate structure (#2932) | `replicate_structure` per project:<br>- all / some / none;<br>- identical;<br>- nested counts differ;<br>- max/min ≥ 2;<br>- intermittent slots. | P1 section "Replicate structure"; intermittent AI_READI 8, CHORUS 14, CM4AI 17, VOICE 9 |

No prediction states a direction the evidence cannot support. Coverage and leaves are
"do not fall" (#2930's wording). Recall is "rises where the bundle states the target,
and is never invented where it does not". Structure is descriptive.

## Differences between the coordination prompt and the plan

The plan is followed in every case:
1. **v8 records.** The prompt describes "v8 04f (`claudecode_assistant_agent`) and 04g
   (`claudecode_api_agent`)". The records are one API arm under `claudecode_api`; see
   P1.
2. **The `< 0.55` trigger.** The prompt's "D21 < 0.55 single-delivery trigger (#5050)"
   is not in the plan, and #5050 is unrelated (item 9).
3. **`--profile neutral`.** The prompt applies it to both VOICE_PEDIATRIC and Kids
   First. The plan specifies the neutral profile only for Kids First (A19-reg).
   VOICE_PEDIATRIC is analysed with VOICE as one cluster (A18-reg).
4. **Confounds.** The prompt lists four compounded factors. The plan lists more
   (item 4).
5. **Worktree.** The plan asks for this file in a durable worktree under
   `d4d-executions`. The coordination prompt put it in
   `/private/tmp/d4d-claude-track-p-20261020`. The branch ref and commits live in the
   main repository, so they survive a reboot even if that directory does not.

## Open before P4

- **Owner rulings:** every [pending Dxx] above. In order of need: D02, D03, D20, D21,
  D24, D17, D23, D09, D04, D15.
- **A1 and A1b**, for items 14 and 15.
- **P3:** adversarial review by a Claude reviewer plus a Codex CLI pass. Each finding
  is filed as an issue and fixed in the PR.
- **Rubric20 version** (#2911, E4).

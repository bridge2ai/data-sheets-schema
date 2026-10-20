# generic_v10 analysis plan (preregistration draft)

**Status: DRAFT for P3 review. Not preregistered, and it authorizes nothing.** This
is step P2 of `notes/d4d_generation_plan_2026-10-09.md` ("#### P2"). The plan becomes
binding only when the owner merges it with an explicit word (P4). Until then, no
generic_v10 registration hash is put to the owner, and no billed generic_v10 step runs
(the plan: "Every billed generic_v10 step depends on P4").

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
- **Plan dependencies:** P2 depends on G3, P1, A1 and A1b.
  - P1 is done.
  - G3 is partly decided (see the decision status below).
  - A1 has a measured result that leaves an owner decision open.
  - A1b is not done.

  Every number that depends on A1 or A1b is marked pending.

**Markers used throughout:**
- **[pending Dxx]:** a rule that rests on an undecided owner decision, followed by the
  plan's recommendation.
- **[proposed; owner fixes at P4]:** every decision rule and tolerance this draft
  offers.

Both are proposals for the owner to confirm or amend at P4, not rulings. Nothing in
this draft asserts a decision the owner has not recorded.

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
| D01–D05, D08, D09, D11–D21, D23–D25 | **Pending.** No owner ruling is recorded. | See the note below. This draft treats every decision in this row as pending. |

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
have not.

## 1. Estimands (P2 item 1)

1. **Feasibility and acceptance.** For each registered cell, the outcome is accepted
   or rejected (A11–A13), with its attempt count. Per stage and project, the outcome
   is the share of billed attempts that ended in an accepted record. Pilots are
   reported separately from production.
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
  - Under (c), there are two choices:
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
- **Plan gates that cannot pass as written** (for agy and the owner; P1):
  - A4's gate, "The CHORUS and AI_READI bundle md5s equal the comparators'
    (9b2ef4b6, d22b61a9)";
  - A14-reg's gate, "the bundle md5 is d22b61a9";
  - the run tables' "identical bundle d22b61a9".

  Today's AI_READI bundle is `1a58ad7b`, and the plan needs amending before A4.

### Cell roles (D03's recommended option (a), [pending D03])

| role | cells | counts as a replicate | analysed as |
|---|---|---|---|
| CHORUS pilot (A10) | 1 | no | pilot, separately |
| AI_READI pilot (A14) | 1, started only after the CHORUS pilot passes blind source review | no | pilot, separately |
| CHORUS replicate gate (A16) | 3 under the A15 floor | yes | confirmatory |
| Production (A17) | CM4AI, VOICE and AI_READI, 3 each, in that order | yes | confirmatory (AI_READI per the comparator decision above) |
| VOICE_PEDIATRIC (A18) | ×1 (D02's recommendation; ×3 only if the paper needs replicate variance) | — | descriptive (item 2a) |
| Kids First (A19) | ×1 | — | descriptive (item 2a) **[pending D15]** |
| With-crate CHORUS (A21–A22) | only under D04 path B | — | separate stage **[pending D04]** |

The v10 confirmatory set is the CHORUS gate plus the production records: 12 records,
matching E2's 12 v8 + 12 v10 batch under options (a), (c) and (d). Under (b), the
confirmatory sets are 9 + 9, and AI_READI's records form a descriptive stratum
(item 12).

### Metrics

Classified as D02 classifies them:
- **Primary deterministic metrics:**
  - populated leaves in the full record (`receipts.populated_leaves`);
  - recall-target counts under cue sha256 `768a26a3…` and tools pattern `4726c005…`
    (`scripts/recall_target_baseline.py`);
  - receipt coverage, `with_receipt / receiptable`, with its denominator (item 3 says
    which coverage);
  - #2932 replicate structure (`replicate_structure.compare_structure` and
    `summarize`);
  - validation, duplicate keys and report findings.
- **Review-pass predictions:** #2930's unsupported-claim and adverse-slot rates,
  measured with the D24 instrument in E2 (item 16). They are preregistered
  predictions but not deterministic metrics.
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
  - generated with **the neutral profile and vocabulary null**, under its own
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
| (1) every attempt in a comparator cell, under the arm's prompt pin, that left a full record | the 12, plus VOICE `04d`, `04e` and AI_READI `04f` rep1: 15. CM4AI `04`–`04c` (the earlier pin) enter only a sensitivity row: 18 | every attempt in a confirmatory cell that left a full record (up to 2 per cell under D07, plus any D21 continuation) | 0.340 / 0.462 / 0.491 / 0.688 (0.682 in the sensitivity row) | 254.7 / 393.0 / 505.5 / 458.0 (447.2) |
| (2) one record per cell: the cell's final attempt that left a full record | the 12 | each confirmatory cell's final attempt | 0.340 / 0.592 / 0.538 / 0.688 | 254.7 / 371.7 / 499.7 / 458.0 |

The recall targets move as well. Under (1), VOICE variables average 5.20 (4.00 under
(2)) and VOICE lineage 0.80 (1.00), and AI_READI variables 19.50 (17.67) (P1).

**Recommendation: definition (2) for the directional rules, with (1) reported beside
it as a sensitivity row. [proposed; owner decides]** The reasons:
- **Equal cell weights.** A cell retried more often does not count more. The v8 VOICE
  rep1 cell holds 3 attempts and CM4AI rep1 holds 4, while a v10 cell can hold up to 2
  plus D21 continuations.
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

**Set B, common gate.** Within whichever Set A definition is chosen, these are the
records of either arm that pass the same absolute rows:
- validation passed;
- duplicate keys 0;
- the five receipt floors at 0 (item 5).

The coverage floor is applied to neither arm, because v8 never had one and applying
v10's floor would select on the measured outcome. v8's Set B is 8 of 12 records under
(2) and 9 of 15 under (1) (P1). Set B is reported beside Set A as a sensitivity
analysis, never instead of it.

**Replicate structure** (#2932, prediction 8) is computed over exactly three records
per arm and project, one per cell (the cell's final attempt), under either definition,
so cells weigh equally.

**Rules for n=1 and n=3.**
- **Default:** D02 recommends descriptive comparisons (per project, v10 values beside
  v8 values with mean ± SD and min–max), with no "v10 mean at or above the v8
  minimum" test unless a tolerance is preregistered per metric. Plan P2 item 3 allows
  either.
- **This draft's choice:** it preregisters a tolerance per directional prediction
  (Predictions below), **[proposed; owner fixes at P4]**, so that each prediction can
  be judged true or false. The owner may replace any of them with "descriptive" at P4.
  No tolerance can be added or changed after any v10 data exist.
- **Verdicts** are per project. A prediction's overall statement is "holds in k of K
  confirmatory projects", where K is 4, or 3 under AI_READI option (b). There is no
  pooled test at n=3.
- **n=1 cells** (pilots, VOICE_PEDIATRIC ×1, Kids First) are descriptive only.

## 4. Confounds (P2 item 4)

Every one of these differs between v8 and the v10 API arm at once, so all effects are
package-level (plan risk 21, D02):
- **Prompt:** the generic_v10 text against `d4d_generic_arm_prompt_v8.md`.
- **Harness:** renderer 25's typed audit and receipt completion against v8's
  four-phase runner, and renderer 26 against 25 where it applies.
- **Coverage timing.** v10 coverage is post-turn and v8's is not, so the coverage
  comparison uses v10's pre-turn figure (prediction 2). That figure is on the
  full-phase record, before audit, reconcile and repair. v8's is on the final record,
  where reconcile and repair had added leaves that have no receipt route (49 of 4094 in
  v8; P1). That residual difference stays a confound.
- **Schema:** 2.0.0 against 3.0.0, and the change in the digest's term source.
  - P1: no v8 record's schema digest re-renders under today's renderer.
  - `d4d runs check` reproduces all 19 digest texts from historical code, but that
    does not attest the consumed implementation or profile.
- **Caps:** the audit and report caps, 24k against 96k.
- **Thinking display:** v10 sends `display: summarized` (D06). v8 declared adaptive
  thinking with no display (the plan's D06: "as v8 and v9 did"). The v8 records
  predate the `model.thinking_requested` field, so this rests on the plan, not on the
  records.
- **AI_READI input arm:** under the owner's 2026-10-14 ruling, the AI_READI v8
  records are with-crate results; v10 reads `1a58ad7b`, without the crate (item 2;
  #5042). The other three projects read byte-identical bundles.
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
  - **Report claims:** v8's stored `report_claims` blocks are instrument v7, while
    v10's will be v8, the `check_report` default. Recomputed under v8, the 12 v8
    records change in one place: CHORUS rep3 gains one finding (P1).
  - **Form:** current on both sides.
- **The recall rule and the newly exposed Software keys.** #2930's reopen comment of
  2026-10-13 requires the API comparison to "retain the documented confound between the
  recall rule and newly exposed Software keys". Recall-target rises in software counts
  are read with that confound.
- **Transport and provider:** both arms run CBORG `claude-opus-5`. Provider-side
  model drift under one model id cannot be excluded, so v10 records the returned
  model identity per call (plan G4).
- **Effort:** a fixed confound. The API arm runs at the provider default (D09), as v8
  did (each v8 record's `unverified` entry; P1). Any Claude Code cell runs at an
  explicit level chosen at N6.
- **Repository state:** `repo.dirty` will read true on every v10 run, because run
  inputs and outputs are untracked. It read true on all 12 v8 records too, across
  four commits and six distinct dirty states (P1). Launch cleanliness is defined as
  `git status --porcelain --untracked-files=no` plus an allowlist of output paths.

The coordination prompt names four compounded factors: prompt, model, harness and
AI_READI bundle scope. The list above is the plan's fuller list, plus the gating and
instrument asymmetries the review found. "Model" here means provider-side drift under
one model id plus the thinking display, since the model id is the same.

## 5. Pilot acceptance rows (P2 item 5)

Under the pending floor, the registered receipt gate is **UNMEASURABLE by design**.
A10 expects exit 1 with "registered receipt gate unmeasurable". That exit is not a
rejection; the rows below decide.

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
5. **Full-phase cap:** every `full` row in `api_usage`, and
   `model.max_tokens_by_phase.full`, read 128000.
6. **Provider:** `model.provider` reads 'LBL CBORG (proxy to Anthropic)' and
   `model.base_url` reads `https://api.cborg.lbl.gov`.

**Recorded, not gated:**
- coverage as a fraction with its denominator (`with_receipt / receiptable`);
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
- **Coverage:** as a fraction with its denominator.
- **Cost:** at that day's prices.
- **Reviewers:** references to the A12 blind source review and its reviewer, named
  under D23, never the generating session.
- **What the run does not establish:** for a pilot, one project, n=1, no load test
  and no recall test.

## 7. Attempt accounting, canonical marks and missing cells (P2 item 7; D07 decided)

- **Every attempt counts**, stopped and rejected ones included, together with its
  usage rows, in the attempt table. Which attempts enter Set A follows item 3's
  definition.
- **Attempt bound:** at most 2 billed attempts per registered cell (D07), for example
  a pilot plus one contingency, or a replicate plus one D21 re-run. Then the owner
  reviews.
- **Pilots** are analysed separately, never as replicates **[pending D03]**.
- **No replicate is chosen by score.**
- **Canonical marks are never used as the estimate.** Estimates use every record in
  the analysis set.
- **Canonical marks** (A20) go only to accepted replicates, and pilots are never
  candidates. They use `d4d runs select --method claudecode_api --project P --config
  <prefix>`, with `--execute` only on the owner's word.

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
- **Missing cells ([proposed; owner fixes at P4]).** A confirmatory cell with no
  accepted replicate after its D07 attempts is a missing cell:
  - It is reported explicitly in every table (E6's "explicit missing cells").
  - It is never imputed, and never filled from another prefix except as a recorded
    D21 continuation.
  - Its attempts' records still enter Set A where they exist.
  - A per-project comparison uses the replicates available and shows n.
  - Replicate structure (#2932) needs at least 2 replicates per arm, so with fewer it
    reads "not computable", never 0.
  - A project with no v10 record in a set is counted as "not measured" in "k of K"
    for that set.
- **Cells split across prefixes:** a cell that D21 splits across prefixes cannot be
  grouped by `d4d runs select --config`. It is marked by a recorded procedure or left
  unmarked (A20; a G4 gap).

## 8. The D20 floor rule (P2 item 8; [pending D20])

The proposed rule, D20's option 1 and the plan's default, is committed here before
the pilots:

> The registered receipt-coverage floor is the lower of the CHORUS pilot's (A10) and
> the AI_READI pilot's (A14) post-turn coverage fractions, `with_receipt /
> receiptable`, rounded down to the nearest 0.05.

**[pending D20]** The value is registered at A15, in a dated amendment PR that gets
P3's review (a Claude reviewer plus a Codex CLI pass) before the owner merges it. That
amendment creates a new registration identity and does not certify the pilots. A
floor failure stops the roster without discarding records.

For scale, from P1's per-record coverage:
- A 0.6 floor would fail 8 of the 12 v8 records: all three CHORUS (0.290, 0.335,
  0.394), VOICE rep2 and rep3 (0.540, 0.576), AI_READI rep1 and rep2 (0.583, 0.388)
  and CM4AI rep3 (0.581).
- This matches #2926's statement.
- The receipt floors alone fail 4 of the 12 v8 records today (item 3).
- v8 coverage is pre-turn, so it is context for the rule, not a comparator for it.

## 9. Gating and continuation of production rosters (P2 item 9; [pending D21])

D21 recommends option (b) with continuation (ii).

**Production rosters** gate on absolute floors only, with no `--canary-baseline`:
- the registered coverage floor, the five receipt floors and duplicate keys gate
  every run;
- a blind check stops the roster as UNMEASURABLE;
- the seven defect metrics are reported but never gated.

**Pilots** keep `--canary-baseline`:
- CHORUS (A10): `2026-09-04f_claude-opus-5-api-generic-v8`;
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

**[proposed; owner fixes at P4]:** the A15 choice changes what runs next, not how
results are judged, so it sits outside the confirmatory analysis.
- Whichever option is chosen, Set A and Set B keep the definitions item 3 settles;
  the A15 choice does not change them.
- Cells completed under a different procedure, such as (c), are flagged in every
  table.
- The choice and its basis are recorded in the A15 amendment before any multi-row
  roster.

**Not adopted: a "< 0.55" trigger.** The coordination prompt states a "D21 < 0.55
single-delivery trigger (#5050)". No such threshold exists in any of these places:
- the plan;
- main, or any remote-tracking or local branch;
- the primary checkout's `notes/`, `.local_drafts` included, or any `d4d-executions`
  worktree's `notes/`.

The only occurrence is the coordination prompt itself,
`notes/coordination/2026-10-20-claude-prompt.md`, an untracked file in the primary
checkout. #5050 is the GitHub assistant
smoke-test issue. This draft keeps the plan's trigger above: any terminal
single-delivery failure in either pilot. If a numeric trigger is intended, the owner
states it and its source before P4.

## 10. Caps, triggers, stop-loss and stop classification (P2 item 10; D07 decided)

- **Caps:** as decided under D07 (decision table above).
- **Operator trigger:** the cap minus the largest worst case of any call that can be
  pending. The worst case comes from A3b's bounds, the pending phase's output cap plus
  its stated input. For CHORUS the plan puts the trigger at most about $11.50 against
  $15. The AI_READI and Kids First triggers wait for item 15.
- **Dollar stop-loss:**
  - the operator watches the A3b readout and runs `d4d api stop --label-prefix
    <prefix>` at the trigger, or after 2 h for the pilot (A10);
  - `--max-cost-dollars` stops between runs (#5045). It cannot recall an in-flight
    request, and an interrupted stream may still bill (#1849).
- **Defect-class stop-loss (plan risk 1; [proposed; owner fixes at P4]).** Two
  rejections in one defect class end re-running in this condition and schedule the
  next shared-generation version. With D05: if both pilots are rejected for the same
  rule-level cause, the #2918 and #2919 rules enter at that next-version boundary.
- **Stop and rejection classification ([proposed; owner fixes at P4]).** The owner
  classifies each stop or rejection by these criteria, after the evidence is in the
  acceptance record:
  - **transport:** the terminal call's `api_usage` row records a transport error or a
    dropped stream, or the provider returned an HTTP error, and no content defect is
    identified in what was written;
  - **harness:** a deterministic stop caused by the run's own validation or by a
    registered limit, not by the provider and not by the instruction's rules. Two
    known cases:
    - **A record shape the runtime refuses** (Lane C1 Finding 2).
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
    - **A registered limit no valid answer can meet** (Lane C1 Finding 1). The
      registered `worker_output_tokens` (4,000) is below the floor of any worker answer
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
        - With raised caps it is open at every grid (item 15).

      The causes are the registration's limit and the worker check's permissiveness,
      so a contingency under the same limits would reproduce the stop. The remedies:
      - A6's output limits, set before any registration is put to the owner;
      - optionally, the runtime fix C1 suggests: `check_worker` refusing a metadata row
        on a path that `record_metadata_allowed` does not allow, which would move the
        metadata form's failure to the worker stage.
    - The defect is filed as an engineering issue before the classification;
  - **instrument:** an offline recomputation shows that a gate or checker misread a
    record that is valid under the registered rules. The defect is filed as an issue
    before the classification;
  - **rule-level:** otherwise, a deterministic row failure or an A12 rejecting-class
    finding attributable to the generated content.

  The class and its evidence appear in the attempt table.

  **A13's "operational" cause** ("a transport or operational cause allows one
  contingency") is read as transport or harness [proposed; owner fixes at P4]. Under
  that reading:
  - **a record-shape stop** allows one contingency. If the contingency is refused for
    the same shape, the fix is an engineering change, which lands only by D17's
    advance procedure or at the next shared-generation version;
  - **a registered-limit stop** allows no contingency under the same registration,
    since it would reproduce the stop. The limits are corrected first;
  - no harness stop counts toward the defect-class stop-loss.
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
D17's procedure between stages, with no run live. Any compaction or report-family
change item 15 describes is model-facing. It lands before A4, or at the next
shared-generation version, never inside the matrix. The output limits are
registration values, set at A6.

## 12. Blinding and reviewers (P2 item 12; [pending D23])

D23 recommends a mixed model:
- a human curator;
- a Claude reviewer plus a Codex CLI pass for registrations and code;
- named source reviewers for acceptance and for the comparison batch.

The owner names them at G3.

**Acceptance review (A12)** is blind source review of the unchanged originals against
the frozen bundle. It covers #1782, #1801/#2924, #1815, #1816 and #2924 dates.
**[pending D05]:** the #2918 and #2919 classes are counted separately and do not
reject on their own (D05's recommendation). A12 never involves the generating
session, and it is not the comparison.

**Comparison batch (E2)** is separate from acceptance:
- 24 records: the v8 comparator records and the 12 v10 confirmatory records; for
  AI_READI, see item 2;
- shuffled, and stripped of labels and provenance headers where feasible (#3280);
- reviewed blind to arm under the A12 protocol, with D24's counts and denominators;
- each review dated and bound to the record sha256;
- E2 starts after A17-acc. No v8 record has yet been reviewed under the #1782–#1816
  protocol.

**[pending D19]:** whether A12's CHORUS review also seeds the #2921 audit-recall
ground truth. D19 recommends yes, if D23 names a second blind reviewer before A12.

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
  a roster, never `d4d api run` ([pending D20]: D20's recommendation). `d4d api run`
  has no floor verdict, canary
  block, run lock or #795 guard.
- Immediately before every billed launch, the operator hashes the roster, every
  registration it lists and the launcher script, and stops on any difference from the
  sha256s named in the word and the review (A10).

## 14. Fixed model-facing values (P2 item 14; pending item 15)

**The rule:**
- **One receipt-completion registration body** (`receipt_completion_registration_v2`)
  for every project and role, identical apart from the floor. The floor is pending
  until A15.
- **Neutral identifiers:** that body's `registration_id` and `context_limit_basis` are
  neutral.
- **Audit limits:** the model-facing audit limits are the ones A1 identifies by
  rendering twice with one limit changed. At `15d053d1a` those include at least
  `max_request_bytes` and `omission_output_tokens`. They are fixed across projects
  and sized for **the largest bundle**. Only non-model-facing allowances vary.
- **Registration ids:** each registration's top-level `registration_id` differs,
  because a roster refuses a reused one. It is neutral and sits outside the fixed
  receipt body.

**The largest bundle is now Kids First, not AI_READI.**
- Kids First is 541,184 bytes, against AI_READI's 430,393 since #5042 (P1).
- The plan's A1 sizes only CHORUS and AI_READI, and D15 and A19-word describe Kids
  First as "about the size of AI_READI's 542,513", which is now false (for agy and the
  owner).
- Lane C1 sized Kids First by proxy (C1 Finding 5): it has no A5d omission context
  and no record, and an A1b count of it needs an A5d context first.

The values themselves are set at A6 and reviewed at A7. This draft fixes the rule,
not the numbers. Item 15 shows the numbers cannot yet be set.

## 15. Stage caps and non-model-facing allowances (P2 item 15; pending an owner decision and A1b)

Still pending. The A1 offline sizing has a result: Lane C1's
`notes/a1_offline_sizing_2026-10-20.md` on branch `fix/5072-offline-sizing-recovery`,
commit `0d45c1ec8`, local and readable with `git show`, note sha256
`9df27d8e77a24aed80aa3bc206a32fa94755781f80e8474bd496f6102832b4e3`.
- It was under a final verification when this was written.
- It replaces the note's first version (`64082b98d`, `e6d46f3a3`), whose
  recommendation and three of whose claims it corrects. Its "Corrections" section
  also lists the errors of two unpushed intermediate revisions, `118af93de` and
  `9dcb4390a`. This draft cited `9dcb4390a` and then `e38abbf4c` before.
- It measured tree `8ea79861` (PR #5095's pre-launch stack).
- Every token figure in it is an estimate from bytes, except where it quotes A1b's
  count.

Its answer, in the order a run would meet the problems:

1. **No partition makes a typed-audit worker's input fit**, for any of the six
   projects, under the current protocol.
   - CHORUS: A1b counted its largest worker at 1,009,249 input tokens on the same
     record at the same grid. That is over the 1,000,000-token window before the
     4,000-token output cap is added.
   - The other five: an estimated 24–60% over.
   - The cause: every typed request carries the schema twice. Once as its own catalog
     (1,486,502 bytes in every worker and in integration), and again as the schema
     context's induced-slot classes. The worker's own assignment, the only part
     partitioning controls, is 0.2–0.3% of the request.
2. **No worker's valid answer fits its output cap, at any valid grid** (C1 Finding 1).
   - The registered `worker_output_tokens` is 4,000, and thinking draws on the same
     `max_tokens`.
   - The floor of an answer the terminal source review accepts is:
     - 2.7–3.0 times the cap at G2;
     - 3.4–6.1 times at G5;
     - 1.4–1.5 times at G1, where G1 is valid (CHORUS, VOICE, VOICE_PEDIATRIC).
   - **The worker stage accepts far less.** Its check (`audit_batches.check_worker`)
     tests structure only.
     - Its grammar accepts a declared-metadata row (`{"path", "metadata_reason"}`)
       for any path. Only the terminal check, at assembly, asks whether the path may be
       declared metadata (`record_metadata_allowed`).
     - An all-metadata answer for the largest worker, before any thinking (C1 Result
       2):

       | grid | at 4 bytes a token | at A1b's ratios | against the 4,000 cap |
       |---|---|---|---|
       | G1 (CHORUS, VOICE, VOICE_PEDIATRIC) | 1,282–1,355 | 1,744–2,223 | under |
       | G2 and G4, those three | 2,226–2,349 | 3,027–3,852 | under |
       | G2 and G4, AI_READI, CM4AI, Kids First | 2,885–2,904 | 3,924–4,763 | at the edge |

       Figures at 4 bytes a token err low (the note), so they cannot by themselves
       show that an answer fits under the cap. The verdict column rests on A1b's
       ratios.
   - **So the costlier failure path is open where that answer fits.** Such an answer
     passes the worker stage and fails only at assembly, after every typed stage is
     billed.
     - Under the registered caps, it is open at G1, and at G2 and G4 for CHORUS, VOICE
       and VOICE_PEDIATRIC. For AI_READI, CM4AI and Kids First it is at the edge.
     - With the raised caps any valid answer needs, it is open at every grid.
   - **A runtime fix to consider** (C1 Finding 1). If `check_worker` refused a
     metadata row on a path not allowed one, that form would fail at the worker stage,
     at the cost of one worker.
   - No compaction option helps: this is output, not input. Item 10 classifies the
     ways it stops a run.
3. **Under S7, the closest compaction option, the report family is not shown to fit
   for AI_READI or Kids First.** The audit is carried at its floor, a lower bound, and
   the report as written at its 96k cap. On those figures:
   - Kids First's regate is 880,265 tokens, 3.6% over the 850,000 report-family
     ceiling.
   - AI_READI's is 816,145, with room for 172 bytes per source-review row. The note
     judges that a real row likely needs more.
   - A report-family change is needed for Kids First and likely for AI_READI. The note
     names three, each of which would clear Kids First's excess at the floor:
     - carry only the audit's findings and revised rows;
     - drop the remaining classes from the report family's schema context;
     - stop repeating the source-review inventory there.
   - The other four projects keep at least 949 bytes per row.
   - Every other request fits under S7 at the floor, on every project. The least room
     is in Kids First's requests:
     - integration, 718,171 tokens, about 925 bytes of answer per row;
     - `reconcile_full`, 624,048 tokens, 1,829 bytes per row.

     Result 2's output problem remains.
4. **The typed input aggregate rules out G2 under S7.** The registered
   `aggregate_input_tokens` is 4,000,000.
   - At G2, AI_READI needs 4.33M and Kids First 4.71M.
   - With three workers (G3, G5), they need 2.70M and 2.93M.
5. **Kids First is the largest case and is sized by proxy** (C1 Finding 5; item 14).
6. **Byte estimates, not counts.** Only the unbilled A1b `messages.count_tokens`
   count, which agy runs, can clear a request.

**The note's recommendation: "Nothing launches as registered."** If S7 or S6 is
adopted, it recommends G5 (`max_paths` 384, `max_inventory_bytes` 65,536,
`max_workers` 4), together with the report-family change. It also needs output limits
that A6 sizes from a measured worker answer:
- `worker_output_tokens`: at least 24,290 tokens at the floor (4 bytes a token;
  CM4AI's largest worker), and 33,035–39,836 at A1b's ratios, before real content and
  thinking;
- `aggregate_output_tokens`: the registered 100,000 is likely too small for AI_READI
  and Kids First. The runtime's admission rule needs 80,242–96,762 at A1b's ratios at
  the floor, before thinking.

Its alternative is G2, which needs A6 to raise `aggregate_input_tokens` to at least
4.71M plus a margin.

**What follows for this plan:**
- **Nothing here is decided.** S7 or S6, the report-family change and the partition
  are the owner's decisions; the output limits are A6's.
  - Each compaction or report-family change alters model-facing text. That makes it a
    new shared-generation version at a condition boundary (D17), touching
    `shared_generation.py`, the typed audit and receipt completion.
- **No stage cap, input bound or allowance is fixed here**, until those decisions and
  the A1b counts exist.
- **D07.** The note quotes D07's two triggers. Its estimates point at the second:
  "If a counted AI_READI report or regate request, with its 96k output cap, does not
  fit the route's window, A14 waits for the owner's decision". They point at it for
  Kids First as well as AI_READI. That trigger fires on A1b counts, not on the note.
- **The rule that will apply**, whatever the figures:
  - each counted request plus its output cap fits the route's window, and the report
    family fits under 850,000;
  - **[proposed; owner fixes at P4]** every worker's answer, at the size A6
    measures, fits its `worker_output_tokens`, and the run's typed stages fit
    `aggregate_output_tokens` under the admission rule;
  - the report and its regate, with the 96k output cap, are counted figures (A1b);
  - if a worst case does not fit, the dependent pilot waits for the owner's decision
    (D07), and Kids First is now among them.

#5072 records that the 2026-10-12 A1b calibration report printed PASS on oversized
rows. It is not launch evidence.

## 16. Instrument for the review-pass predictions (P2 item 16; [pending D24])

D24 recommends option 1. The "unsupported-claim rate" and "adverse-slot rate" of
#2930 are measured in the blind E2 comparison batch, as per-record counts of the
rejecting classes over a stated denominator:
- #1782: plans stated as current, and scope;
- #1801 and #2924: roster roles;
- #1815: attribution;
- #1816: qualifiers and headers.

The denominator is fixed in the E2 protocol before E2 starts. The support judge is
excluded from preregistered predictions until #3343 is calibrated under its own
registration and word.

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

Each prediction names its metric, comparator, decision rule and instrument, fixed here
before any v10 data exist. **Every rule is [proposed; owner fixes at P4].**

**Notation:**
- For project p, `v8_p` and `v10_p` are each arm's values in Set A, under the
  definition item 3 settles. Rows 1–3, 3a and 6–8 read Set A. Row 4 reads E2's
  records (item 12), and row 5 reads the records E5 re-rates.
- "Holds in k of K" counts the projects whose rule holds. K is 4, or 3 if AI_READI
  leaves the contrast.
- Set B results are reported beside every row, as a sensitivity analysis.

For AI_READI, each row is judged under the comparator option chosen in item 2, and
under (a) it is labelled cross-arm.

| # | prediction (from #2930, restated against v8 per D02) | metric and instrument | decision rule [proposed; owner fixes at P4] | v8 values (P1) |
|---|---|---|---|---|
| 1 | Populated leaves do not fall | `len(receipts.populated_leaves(full))` per record | holds for p if mean(v10_p) ≥ 0.9 × mean(v8_p). v8's replicate SDs are 21.7 (CHORUS), 43.9 (AI_READI), 31.3 (CM4AI) and 68.6 (VOICE) leaves, so 10% of the v8 mean is 1.2, 1.1, 1.5 and 0.5 SD respectively | AI_READI [525, 525, 449], CHORUS [235, 278, 251], CM4AI [422, 473, 479], VOICE [386, 297, 432] |
| 2 | Receipt coverage does not fall, measured pre-turn | **v10:** `receipt_completion.before.slots.with_receipt / receipt_completion.before.slots.receiptable`, from the provenance record's `receipt_completion` block (written by `api_runner.py:7384-7386` from `receipt_completion.recover`). Its `before` check is `rereceipt.complete`'s `receipts.check` of the full-phase record with `original=record`. So its `added_after_receipt` is 0, and `receipt_completion.counts.never_receipted_before` equals its `receiptable − with_receipt`.<br>**v8:** `receipts.slots.with_receipt / receipts.slots.receiptable` of the final record.<br>The v4 instrument's coverage is v3's (`receipts.py`: "v3 coverage and gates unchanged") | holds for p if v10_p's pooled pre-turn coverage ≥ v8_p's pooled coverage − 0.05 (absolute). A v10 record without a `receipt_completion.before` block has missing pre-turn coverage: never 0, and never replaced by the post-turn value. Residual confound: v10's figure is on the full-phase record, and v8's is on the final record after reconcile and repair (item 4). Post-turn coverage, which the gate selects on, is reported descriptively only | pooled, under item 3's definition (2): CHORUS 0.340, VOICE 0.592, AI_READI 0.538, CM4AI 0.688. Under (1): VOICE 0.462, AI_READI 0.491 (P1) |
| 3 | The recall rule raises recall where the bundle states the targets | `scripts/recall_target_baseline.py` (cues `768a26a3…`, tools `4726c005…`) per record, at D02's targets:<br>- AI_READI variables 20/13/20;<br>- CM4AI lexical candidates 9/5/3;<br>- VOICE variables 4/4/4, lineage 1/1/1, lexical candidates 3/0/1, tools with a version token 0/0/0;<br>- CHORUS lineage 1/1/0. | **Counts the rule should raise** (variables, lineage entries, versioned tools): holds for a target if mean(v10_p) > mean(v8_p).<br>**Targets at their ceiling:** where every v8 replicate already sits at the target's ceiling under this plan's rules, the target holds if mean(v10_p) ≥ mean(v8_p) ("does not fall"). VOICE lineage 1/1/1 is at its ceiling: the count is the top-level `was_derived_from`, a single-valued slot (not `multivalued` in the run's schema or today's), and row 3a forbids `parent_datasets`.<br>**Lexical candidates**, which should fall as cue chunks are extracted rather than set aside: holds if mean(v10_p) < mean(v8_p).<br>**Combination:** a project's row-3 verdict holds if every target listed for it holds, and "holds in k of K" then counts projects [proposed].<br>AI_READI's v8 counts were taken over the with-crate chunking (P1) | as listed |
| 3a | A rise is an error where the bundle states nothing | Same counts, read against the #3289 adjudication in `notes/recall_target_baseline.md`:<br>- no parent dataset in any of the four bundles;<br>- no processing-software version in the AI_READI, CHORUS or CM4AI bundles (CM4AI's versions belong to companion analyses);<br>- VOICE's one stated version is b2aiprep v3.0.0.<br>The adjudication read AI_READI's pre-#5042 bundle, when it still had its RO-Crate, which recorded FAIRSCAPE 1.2.1 as the metadata packager, not processing software. It is re-read against `1a58ad7b` before P4. | holds if every confirmatory v10 record has `parent_datasets` 0 and, for AI_READI, CHORUS and CM4AI, `used_software` with a version 0. Any non-zero instance means it does not hold, and each instance is listed | 0 today |
| 4 | The unsupported-claim and adverse-slot rates do not rise (a review-pass prediction) | The D24 instrument: E2 blind counts of the rejecting classes over the denominator fixed in the E2 protocol | **The one exception to per-project verdicts:** pooled over the E2 batch, because E2's denominator is set per batch, not per project (item 16). The v10 records are E2's 12 confirmatory records (item 12), not Set A's attempts. Holds if the pooled v10 rate ≤ the pooled v8 rate, per rate, with no tolerance. Ties hold | no v8 record reviewed yet; measured in E2 |
| 5 | Rubric20 Q11/Q19 do not fall (secondary) | E5 joint re-rating, instrument version per E4 | holds for p if mean(v10_p) ≥ mean(v8_p) − 0.5 on the item's scale, over the records E5 re-rates, under the one joint re-rating | measured in E5 |
| 6 | **Not a prediction: an acceptance invariant.** Validation passes with 0 duplicate keys | `validation.passed` and `canary.duplicate_key_count` | true by construction for accepted v10 records, since the batch stops on invalid output and duplicate keys gate. Set A reports the count of v10 attempts whose output failed either, descriptively | 12/12 passed, 0 duplicate keys |
| 7 | **Descriptive, no direction:** report findings | `report_claims.findings` | reported per record and per project in both sets. Reasons:<br>- the counts cross instrument versions: v8's stored blocks are v7, and new runs are checked under v8;<br>- renderer 25's report carries the typed audit's finding totals (#4766), which v8's report did not;<br>- v8's values are 0–2 per record.<br>A directional rule would be decided by noise, as D21 argues against its option (a) | worst, stored v7 and recomputed under v8 alike: CHORUS 2, VOICE 1, AI_READI 1, CM4AI 0. Under v8, CHORUS rep3 goes from 0 to 1 (P1) |
| 8 | **Descriptive, no direction:** replicate structure (#2932) | `replicate_structure` per project:<br>- all / some / none;<br>- identical;<br>- nested counts differ;<br>- max/min ≥ 2;<br>- intermittent slots. | reported per project, over exactly three records per arm and project, one per cell (item 3). It needs at least 2 replicates per arm (item 7). Reason: #2932's source-anchored granularity rule is not established to be in generic_v10 (#2932 is open, and #3336's retained remainder asks to verify it). Without it, the recall rule could raise intermittency by filling slots in some replicates, or lower it, so there is no directional hypothesis | P1 section "Replicate structure"; intermittent AI_READI 8, CHORUS 14, CM4AI 17, VOICE 9 |

Rows 1–5 are directional and decidable, rows 6–8 are not predictions, and every
rule is the owner's to fix at P4. Coverage and leaves use #2930's "do not fall".
Recall is "rises where the bundle states the target, and is never invented where it
does not" (3, 3a). Structure and report findings are descriptive, for the stated
reasons.

## Differences between the coordination prompt and the plan

The plan is followed in every case:
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

- **Owner rulings.** Every [pending Dxx] above. In order of need:
  - D02, including the **AI_READI comparator** (options (a)–(d), item 2) and the
    **Set A definition** (item 3);
  - D03, D20, D21, D24, D17, D23, D09, D04, D15, D05, D08 and D19.
- **Item 15's open decisions**, for items 14 and 15:
  - S7 or S6, a report-family change and the partition (the owner);
  - the output limits, from a measured worker answer (A6);
  - the A1b counts (agy), with Kids First's A5d context first.
- **Plan amendments, for agy and the owner; this draft does not edit the plan:**
  - the `d22b61a9` gates in A4 and A14-reg, and the run tables;
  - D15's and A19-word's "about the size of AI_READI's 542,513";
  - A1's sizing inputs, which do not include Kids First.
- **The #3289 adjudication**, re-read against AI_READI's `1a58ad7b` bundle (prediction
  3a).
- **The E2 protocol's denominator** (item 16).
- **Rubric20 version** (#2911, E4).
- **P3:** adversarial review by a Claude reviewer plus a Codex CLI pass. Each finding
  is filed as an issue and fixed in the PR.

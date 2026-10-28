# generic_v10 analysis plan (preregistration draft)

**Status: DRAFT for P3 review. Not preregistered, and it authorizes nothing.** This
is step P2 of `notes/d4d_generation_plan_2026-10-09.md` ("#### P2"). The plan becomes
binding only when the owner merges it with an explicit word (P4). Until then, no
generic_v10 registration hash is put to the owner, and no billed generic_v10 step runs
(the plan: "Every billed generic_v10 step depends on P4").

- **Revised:** 2026-10-27 for R6 F1–F6, against the decision record through D49 and
  the local BC1/N2 implementations. This remains a draft, not a retrospective
  registration or a declaration that the composed launch condition is ready.
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
    `a0e28d8821c69e2d4fe1b75b14e3c2a2140ae4d5` (D26–D49), reconciled with
    the owner's dated rulings in `notes/coordination/STATUS.md`;
  - BC1 `notes/bc1_production_2026-10-27.md` and contract sources at
    `3bd3c41f459b31848aee2f57e26deb86ef786970`;
  - N2 `notes/native_n2_parity_delta_review_2026-10-25.md` at
    `be0bd05821256212e89e4d011ba6b30a780e299b`;
  - R_V5 remediation `aff4c9ca530a94b84f934698cdc791960cc31713` (local verification,
    not approval to activate v5 in either generation arm).
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

## Decision status (reconciled 2026-10-27)

The October 20 draft below is amended by D26–D49. Decisions authorize policy and
engineering; they do not establish a merged implementation, an accepted record,
remaining budget or a fresh launch word. Where the implementation differs from
the requested condition, items 14–15 name the discrepancy before P4.

| ID | Status | Where recorded |
|---|---|---|
| D06 | **Decided 2026-10-19.** Every generic_v10 API registration declares `{"type": "adaptive", "display": "summarized"}`, the routed v10 conditions included (keyed on the condition's base, v10). There is no typed-stage cache breakpoint in this condition. | #1849 comment of 2026-10-19 |
| D07 | **Decided 2026-10-19, option 1.**<br>- A $100 named generic_v10 API pilot allocation: CHORUS pilot $15 cap, one CHORUS contingency $15, AI_READI pilot $35 planning ceiling, one AI_READI contingency at most $35.<br>- At most 2 billed attempts per registered cell, then an owner review.<br>- Every run needs its own owner word naming its registration sha256 (for a roster, the roster sha256 and each registration sha256 it lists) and its cap.<br>- `d4d api batch --max-cost-dollars` is the between-run stop.<br>- The operator trigger is the cap minus the worst-case in-flight call: at most about $11.50 against $15 for CHORUS.<br>- The AI_READI lines are provisional (see item 15). | #1763 comment of 2026-10-19 |
| D10 | **Decided 2026-10-20: retire** the v10z/audit_controls lineage and audit28. | Owner's answer in the Claude worker session. `notes/reviews/v10z_retirement_2026-10-20.md` (this branch). agy is to post it on #4761. |
| D22 | **Decided 2026-10-20: withdraw.** The v10z standing authorizations do not extend to generic_v10, and they are withdrawn now. | Same record. agy is to post it on #1763 and #4761. |
| D01 | Superseded by D26/D28. | Native/API paths below. |
| D05, D17, D19, D23 | Decided through D34, D35 and D36. | Rule batch, freeze and review below. |
| D26, D27 | Track N with the default runtime profile; name **native agentic (direct arm)** and directories `claudecode_direct{,_core}/<label>/`. | D26 2026-10-23; D27 owner confirmation 2026-10-25. |
| D28 | Void 10-22b; one clean CHORUS API re-canary; 64k/32k/32k worker/omission/integration baseline, 128k report/reconcile, A17 splitting, versioned wire/registration identity. Builder floor remains pending; 19/20 belongs to the re-canary only. | 2026-10-23; floor basis superseded by D37, partition selection refined by D45/D49. |
| D29 | **Pending owner:** native effort and first-party `claude.ai` account. No API key. | Resolve for the native registration and launch. |
| D30, D38 | Revised R9 criteria limited to `confidentiality_level`/`hipaa_compliant`; American `license` spelling and new prompt pins in both assets. | D30 2026-10-23/24; D38 2026-10-25. |
| D31, D40, D47 | Both 10-20a and 10-22a are archived assisted/invalid engineering evidence. D40 supersedes D31's initial generated-record disposition for 10-22a. Preserve artifacts; no run/archive edits. | 2026-10-23–26; assisted stratum below. |
| D32, D37 | D32's value-matching subtraction is superseded. D37 gates **phase-1 snapshot** receipt quality: `slots.with_receipt_at_receipt / slots.receiptable_at_receipt`. | D37 2026-10-25T19:44Z; item 3a. |
| D33 | Report-family pre-dispatch token-plus-output admission; no independent report-family trim under that decision. D44 subsequently requires a reviewed BC1 condition before the canary. | 2026-10-25/26; items 14–15 disclose the new exposure. |
| D34 | No new rule batch: measure #2918/#2919 with existing lints; defer #2931/#2937; #4018 reasons only; #3336 remains to be measured by CHORUS ×3. | 2026-10-25. |
| D35 | Freeze at rebuilt A21 registration on merged main, after A17/#5155/#5157. A later runner change needs CHORUS byte-parity evidence and a diagnostic canary. | 2026-10-25; each billed canary still needs its own launch word. |
| D36 | Fresh Claude source reviewer plus Codex pass, neither generator nor operator; owner signs acceptance. Second blind reviewer seeds audit-recall observations against `original_full` before seeing the audit. | 2026-10-25; human decisions are not supplied by this draft. |
| D39 | Versioned worker wording recognizes a split list entry as a removal's owning root. | 2026-10-25; A17 contract change. |
| D41, D42, D43 | No-touch operation and a terminal/rejection-state guard; compare both guard candidates then obtain the owner's choice. **Owner** runs the hash-approved re-canary command; agents monitor read-only. | D43 supersedes D41's operator clause; guard selection is not inferred here. |
| D44, D45 | Build/review bounded carry for **all six projects** before the single clean CHORUS re-canary. Keep A17 splitting; select project bounds from cost and output-cap risk inside BC1. | 2026-10-26. |
| D46 | Owner approved the seven omission/evaluation settings, including CM4AI's two false applicability flags, cohort separation and Kids First neutral `vocabulary: {}`. | 2026-10-26; corrected narratives and exact-file identities still require verification. |
| D48 | Preflight refuses duplicated, nonretryable repeated, over-retried or out-of-order usage phases before a call or file write. | 2026-10-26; installed integration must be verified. |
| D49 | Derive aggregate input allowance as `max_calls × 1,000,000`, with all six project profiles and A17-aware sizing; D45 governs final BC1 bounds. | 2026-10-26; an allowance does not prove request fit or authorize spending. |
| D02–D04, D08, remaining D09 choices, D11–D16, D18, D20–D21, D24–D25 | **Pending where not specifically superseded above.** D02 comparator/analysis-set choices and D04 crate comparison are not decided by this amendment. | Separate proposal, implementation and owner decisions. |

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

Under D31/D40/D47, both canaries are **assisted/invalid evidence-only**. Preserve
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

## 1. Estimands (P2 item 1)

1. **Feasibility and acceptance.** For each registered cell, the outcome is accepted
   or rejected (A11–A13), with its attempt count. Per arm/stage/project, report the
   share of clean registered attempts ending in acceptance, with billing or native
   runtime evidence separately. Assisted attempts are the separate stratum above.
   Pilots are reported separately from production.
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

The older plan's A21–A22 identifiers for the optional crate stage are retained
only as historical task references. Current coordination's **A21 is the clean
CHORUS API re-canary** under D35/D44, not an authorization for a crate arm.

### Six-project × generation-arm and evaluation matrix

All prospective cells below remain unlaunched/unregistered unless a later,
hash-bound owner record explicitly says otherwise. “Confirmatory” names the
proposed analysis role after P4, not current authorization or acceptance.

| Project | API arm (`claudecode_api{,_core}`) | Native agentic (direct arm) (`claudecode_direct{,_core}`) | Evaluation/contrast role |
|---|---|---|---|
| CHORUS | One clean re-canary, n=1 descriptive; proposed production n=3 confirmatory against v8 | First canary n=1, descriptive feasibility only; no production replicates registered | API production enters E2/E5; native canary has independent acceptance review and separately registered descriptive E5 ratings, never a confirmatory native/API verdict |
| AI_READI | No-crate pilot separately; proposed n=3, confirmatory only under D02's chosen comparator, otherwise descriptive | Unplanned/unregistered | API E2/E5 retain the cross-arm label if v8 with-crate is selected; any later native contrast must also declare source/profile/account/effort differences |
| CM4AI | Proposed n=3 confirmatory against v8 | Unplanned/unregistered | API E2/E5 use D46's non-human-subject/non-regulated applicability; companion analyses are not dataset-processing facts |
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

The proposed v10 confirmatory set is the **three-replicate CHORUS gate A16** plus
the nine other production records, excluding the separate n=1 clean re-canary:
12 records,
matching E2's 12 v8 + 12 v10 batch under options (a), (c) and (d). Under (b), the
confirmatory sets are 9 + 9, and AI_READI's records form a descriptive stratum
(item 12).

### Metrics

Classified as D02 classifies them:
- **Primary deterministic metrics:**
  - populated leaves in the full record (`receipts.populated_leaves`);
  - recall-target counts under cue sha256 `768a26a3…` and tools pattern `4726c005…`
    (`scripts/recall_target_baseline.py`);
  - receipt coverage with exact record/receipt snapshots and instrument identities
    (item 3a); the D37 acceptance ratio and pre-completion comparison are distinct;
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

**Replicate structure** (#2932, prediction 8) has an **n=3 primary estimand**:
exactly three records per compared arm/project, one final attempt per registered
replicate cell, with equal cell weights. If one arm supplies only two usable
records, n=3 is missing and n=2 is a separately flagged **sensitivity stratum**,
never the same estimand. Use the two common registered replicate indices when
both arms have them; otherwise show unmatched available sets and do not present
a paired contrast. Do not choose a favorable two-record subset from a complete
three-record arm. Show each arm's n and included cell IDs in every structure
table. With fewer than two in either arm the comparison is not computable, not 0.

**Rules for n=1 and n=3.**
- **Default:** D02 recommends descriptive comparisons (per project, v10 values beside
  v8 values with mean ± SD and min–max), with no "v10 mean at or above the v8
  minimum" test unless a tolerance is preregistered per metric. Plan P2 item 3 allows
  either.
- **This draft's choice:** it preregisters a tolerance per directional prediction
  (Predictions below), **[proposed; owner fixes at P4]**, so that each prediction can
  be judged true or false. The owner may replace any of them with "descriptive" at P4.
  Freeze tolerances at P4 before the first clean outcome under the selected
  production condition; prior assisted evidence is disclosed above. Subsequent
  changes require an explicit prospective amendment and a new analysis stratum.
- **Verdicts** are per project. A prediction's overall statement is "holds in k of K
  confirmatory projects", where K is 4, or 3 under AI_READI option (b). There is no
  inferential significance test at n=3. Prediction 4 alone retains a descriptive
  claim/leaf-weighted pooled decision rule, with the fixed-weight sensitivity in
  item 16; it is not a per-project or independent-replicate significance claim.
- **n=1 cells** (pilots, VOICE_PEDIATRIC ×1, Kids First) are descriptive only.

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
  BC1 staged concern/decision carry changes later evidence exposure (item 14).
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
- **Coverage:** as a fraction with its denominator.
- **Cost:** at that day's prices.
- **Reviewers:** references to the A12 blind source review and its reviewer, named
  under D23, never the generating session.
- **What the run does not establish:** for a pilot, one project, n=1, no load test
  and no recall test.

## 7. Attempt accounting, canonical marks and missing cells (P2 item 7; D07 decided)

- **Every attempt is retained**, stopped and rejected ones included, with its
  usage/termination evidence. Clean registered attempts form the per-arm automatic
  success denominator; assisted 10-20a/10-22a and any later intervention form the
  separately reported engineering stratum, excluded from both clean numerator and
  denominator. Which clean attempts enter Set A follows item 3's definition.
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
  - Structure's primary estimand needs n=3 per arm. n=2 is only the flagged
    sensitivity stratum of item 3; fewer than 2 is not computable, never 0.
  - A project with no v10 record in a set is counted as "not measured" in "k of K"
    for that set.
- **Cells split across prefixes:** a cell that D21 splits across prefixes cannot be
  grouped by `d4d runs select --config`. It is marked by a recorded procedure or left
  unmarked (A20; a G4 gap).

## 8. Production-floor decision (P2 item 8; D37 basis decided, D20 value pending)

D37 fixes the snapshot basis. D28 fixes 19/20 for the clean CHORUS re-canary only,
and the builder default is pending. The older D20 recommendation below is retained
as a **proposed production-value rule**, subject to a dated owner decision after
the clean pilots; it does not override the re-canary registration:

> The registered receipt-coverage floor is the lower of the CHORUS pilot's (A10) and
> the AI_READI pilot's (A14) effective at-receipt D37 coverage fractions,
> `with_receipt_at_receipt / receiptable_at_receipt`, rounded down to the nearest 0.05.

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

**No adopted "< 0.55" trigger.** The October 20 review found that threshold in
its delegation rather than the governing plan; its repository search is historical
evidence, not a fresh exhaustive absence claim. This draft does not adopt it.
Any numerical trigger needs an explicit owner decision before P4.

## 10. Caps, triggers, stop-loss and stop classification (P2 item 10; D07 decided)

- **Caps:** the historical D07 allocation remains part of the spending record.
  It is not evidence of remaining funds after the two assisted canaries. The
  rebuilt packet must carry the current reconciled ledger, new allocation/cap and
  owner word; D28's planning allowance is not itself a launch authorization.
- **Operator trigger:** the cap minus the largest worst case of any call that can be
  pending. The worst case comes from A3b's bounds, the pending phase's output cap plus
  its stated input. Recompute it from BC1's actual groups/final call and measured
  request sizes (item 15), including simultaneous in-flight calls. The old
  $11.50/$15 CHORUS example is historical, not the new trigger.
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
    historical cases that informed engineering:
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
  - These four/six/eight-call examples describe the old single-integrator design,
    not BC1. Current exposure uses `W + 1 + ceil(W/fan_in) + 1` audit calls plus
    the separately counted generation/receipt/reconcile/report calls (item 15).
    Do not carry the old roster probabilities into BC1 budgets or predictions.
  - Report observed stage rates and uncertainty; the independence illustration is
    not a measured failure forecast and does not choose a favorable tolerance.

## 11. Freeze (P2 item 11; D35 decided)

D35 freezes from the rebuilt A21 re-canary registration on merged main, after
A17, #5155 and #5157. Later runner changes require a CHORUS byte-parity test and
one separately authorized diagnostic canary before remaining runs re-register. Every
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

**Comparison batch (E2)** is separate from acceptance:
- 24 records: the v8 comparator records and the 12 v10 confirmatory records; for
  AI_READI, see item 2;
- shuffled, and stripped of labels and provenance headers where feasible (#3280);
- reviewed blind to arm under the A12 protocol, with D24's counts and denominators;
- each review dated and bound to the record sha256;
- E2 starts after A17-acc. No v8 record has yet been reviewed under the #1782–#1816
  protocol.

Under D36, a second blind model reviewer writes audit-recall observations against
the SHA-256 of `original_full` before anyone reads the audit. This seeds #2921;
unresolved human annotation/matching decisions remain explicit before scoring.

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
- Immediately before every billed launch, the operator hashes the roster, every
  registration it lists and the launcher script, and stops on any difference from the
  sha256s named in the word and the review (A10).

## 14. Selected condition, bounded carry and model-visible identity

The design label **`shared-generation-api-v2-bc1`** names the proposed scientific
condition. It is **not** the installed `shared_generation_version` or an accepted
registration. The current local BC1 implementation at
`3bd3c41f459b31848aee2f57e26deb86ef786970` selects the following actual tuple;
these differences must be resolved and pinned before P4/A21.

| Component | Current reviewed policy / local implementation | Registration obligation |
|---|---|---|
| Scientific assets | D30/D38 generic-v10 prompt SHA-256 `ec081dbb14049449989c56169de7bcd1563076667818c12b78571b5f15acb2db`; uniform-v2 SHA-256 `22a553695536a822e9c7ae877663a9b251c889a6637c637e579c5c6e1c855b2e` | Verify actual merged bytes and native alignment; the BC1 branch itself does not install D38 |
| Actual BC1 selection | `bounded_carry_version=1`, exact `bounded_carry` registration block; `bc1_typed_audit_v1`, parent shared generation **1**, generic_v10, API renderer **25**, playbook **2**, receipt completion **2**, direct API | Pin full contract/procedure/code/runtime identity; shared-generation-v2 routing and native are unsupported |
| Hook status | Protected shared-generation hooks are an **unapplied proposal**, diff SHA-256 `10cb0ff8dd77d34ec150ae9b5447a82cdeef4402a477151f220a6c02685b0cb8` | Review/integrate first; applying the patch changes source identity and requires rebuilt registrations |
| Schema and source | Complete captured reachable Dataset and CoreDataset definitions, descriptions and annotations; complete original records and source bundle | Pin exact full/core import closures, bundle, chunk/source manifests, profile and context bytes per cell; no final composed closure/registration hash is yet claimed |
| Worker/partition contract | A17 splits large lists; D39 owning-root wording; D45 selects project bounds | Pin exact reviewed contract and each project's measured partition. Numeric partition metadata stays controller-only as specified below |
| Carry | `bc1_codec_v1`, `ConcernPacketV1`, `RecordDigestV1`, stage delta v1 | Pin codec/contract/source digests and each predecessor/request identity; a digest is not evidence of scientific support |
| Receipts and reports | v4 + D37 snapshot gate; v5 shadow only. Baseline report checker v8; watermark-aware v9 is a separate opt-in | Pin checker code, instrument, snapshot fields and any evaluation amendment; never silently activate new checks under old labels |
| Composition | BC1 branch has reviewed R9b/A17 changes but does **not** install A14, D38 or D41 | Finish composition, D42 guard selection and independent review; no installed-source or campaign-readiness claim follows from isolated tests |

**What later models receive.** Every worker must review all assigned populated
values and clauses against the complete sources. Integrations consume fixed
groups of one or two new worker results plus bounded concern/decision history;
one separate final call checks cross-group consistency. Later stages retain
changed rows, concerns, predecessors, every explicit decision, omission candidates
and dispositions, plus full records/schema/source. Untouched supporting/metadata
review rows and their evidence text can be absent from that model view. The host
archives the complete worker reviews, raw deliveries and machine audit.

This is an intentional **change in model access**, not lossless preservation of
the full review procedure. Lossless encoding of retained strings cannot ensure
that models rediscover a contradiction involving omitted supporting-row evidence.
The scientific rationale is bounded context/cost with explicit concern retention;
the tradeoff is unmeasured cross-group detection. Reconcile must inspect affected
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
AI_READI record. D46 approved settings, not arbitrary narrative/citation text.
The decision note's CHORUS hash `6e3c6b6d…` conflicts with retained actual
`ac94a74b…` bytes; resolve and pin the exact artifact before registration rather
than copying that inconsistent digest or rewriting evidence.

## 15. Token caps, visible-byte bounds, call counts and input allowances

D28's decided baseline is **64,000 / 32,000 / 32,000 tokens** for worker /
omission / integration, with **128,000** for report, report regate and
reconcile-full. These caps include thinking where the route uses thinking.
The current BC1 code instead requires **64,000 for both worker and integration**,
including each group and final integration call. This is a material implementation
delta, not an alias for D28's 32k integration. The owner/reviewed registration must
settle the resulting contract and budget before P4; this draft does not silently
approve it. Retain the original decided baseline and the proposed BC1 value in
the decision packet.

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
- D49 aggregate input allowance: `max_calls × 1,000,000`, with `max_calls`
  covering every registered maximum worker, group, omission and final call;
- generation, receipt-completion, reconcile, report/regate and permitted repair
  calls are added separately to the full-run cost and failure exposure.

“One or two” refers to **new workers per group**, not a universal two-integration
call ceiling. If that interpretation is not the intended scientific condition,
resolve it prospectively instead of reporting the implemented schedule as parity.
Aggregate allowance is a ceiling, not an estimate, a context-fit test or permission
to spend. Current #5157 admission must independently enforce actual request bytes,
provider token count plus the selected output cap, and remaining aggregate budget
before each dispatch, including resumed repair/report refresh.

Size **CHORUS, CM4AI, AI_READI, VOICE, VOICE_PEDIATRIC and KIDS_FIRST** at expected
size and visible caps with each project's own original/full/core/receipt/context
inputs and the real planner/formatter. Record worker/group counts, complete source
and schema bytes, carry and omission sizes, cached/uncached assumptions, input and
output reservations, cost and failure exposure per stage. K1 v2 is calibrated
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
**prospective proposal for D24/P4, not an already ratified protocol**. Pin the
annotation manual, reviewed inventory and adjudication rules before E2. The
unsupported-claim and adverse-slot rates of #2930 use the rejecting classes:

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
directional rule, evaluated separately for the two rates:

- claim-weighted pool: `sum(U_apr) / sum(C_apr)` over the fixed E2 record roster;
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
disagree with the pool. Under AI_READI comparator option (a), retain an explicit
**AI_READI cross-arm (with-crate v8 / no-crate v10)** row and label the combined
pool as mixed input-arm evidence; also show the prespecified three-project pool
excluding AI_READI. Do not relabel it as a homogeneous runtime/package effect.

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
fixed at P4 before clean outcomes from the selected production condition. The
assisted evidence already observed is disclosed above. **Every rule remains
[proposed; owner fixes at P4].**

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
| 2 | Receipt coverage does not fall, measured pre-completion | **v10:** v4 `receipt_completion.before.slots.with_receipt / receipt_completion.before.slots.receiptable` on `O,R0` (item 3a). **v8:** stored v3 final-record `receipts.slots.with_receipt / receipts.slots.receiptable`; add a named common-checker recomputation where exact inputs exist. Pin source/checker identities; do not infer parity from the unchanged v4 string. | holds for p if pooled pre-completion v10 coverage ≥ pooled v8 coverage − 0.05 absolute. Missing pre-turn snapshots remain missing, never 0 or replaced by post-turn values. Final-v8 versus phase-1-v10 remains a timing/instrument contrast. D37 at-receipt gate coverage, final coverage and completion gain are separately reported, never substituted into this rule. | pooled, under item 3's definition (2): CHORUS 0.340, VOICE 0.592, AI_READI 0.538, CM4AI 0.688. Under (1): VOICE 0.462, AI_READI 0.491 (P1) |
| 3 | The recall rule raises recall where the bundle states the targets | `scripts/recall_target_baseline.py` (cues `768a26a3…`, tools `4726c005…`) per record, at D02's targets:<br>- AI_READI variables 20/13/20;<br>- CM4AI lexical candidates 9/5/3;<br>- VOICE variables 4/4/4, lineage 1/1/1, lexical candidates 3/0/1, tools with a version token 0/0/0;<br>- CHORUS lineage 1/1/0. | **Counts the rule should raise** (variables, lineage entries, versioned tools): holds for a target if mean(v10_p) > mean(v8_p).<br>**Targets at their ceiling:** where every v8 replicate already sits at the target's ceiling under this plan's rules, the target holds if mean(v10_p) ≥ mean(v8_p) ("does not fall"). VOICE lineage 1/1/1 is at its ceiling: the count is the top-level `was_derived_from`, a single-valued slot (not `multivalued` in the run's schema or today's), and row 3a forbids `parent_datasets`.<br>**Lexical candidates**, which should fall as cue chunks are extracted rather than set aside: holds if mean(v10_p) < mean(v8_p).<br>**Combination:** a project's row-3 verdict holds if every target listed for it holds, and "holds in k of K" then counts projects [proposed].<br>AI_READI's v8 counts were taken over the with-crate chunking (P1) | as listed |
| 3a | A rise is an error where the bundle states nothing | Same counts, read against the #3289 adjudication in `notes/recall_target_baseline.md`:<br>- no parent dataset in any of the four bundles;<br>- no processing-software version in the AI_READI, CHORUS or CM4AI bundles (CM4AI's versions belong to companion analyses);<br>- VOICE's one stated version is b2aiprep v3.0.0.<br>The adjudication read AI_READI's pre-#5042 bundle, when it still had its RO-Crate, which recorded FAIRSCAPE 1.2.1 as the metadata packager, not processing software. It is re-read against `1a58ad7b` before P4. | holds if every confirmatory v10 record has `parent_datasets` 0 and, for AI_READI, CHORUS and CM4AI, `used_software` with a version 0. Any non-zero instance means it does not hold, and each instance is listed | 0 today |
| 4 | The unsupported-claim and adverse-slot rates do not rise (a review-pass prediction) | D24/P4 proposed atomic-claim and eligible-leaf units, exclusions, dedup/splitting and complete-adjudication rules in item 16 | **Exception to per-project verdicts:** claim-weighted and leaf-weighted E2 pools, not Set A attempts. Holds separately if each v10 rate ≤ its v8 rate, zero tolerance; ties hold. Always show project-specific rates and equal-project-weight sensitivity. AI_READI option (a) stays visibly cross-arm, with the separate three-project pool. Missing/unassessed units do not create a passing verdict. | no adopted E2 annotation result asserted here; measured after protocol/roster freeze |
| 5 | Rubric20 Q11/Q19 do not fall (secondary) | E5 joint re-rating, instrument version per E4 | holds for p if mean(v10_p) ≥ mean(v8_p) − 0.5 on the item's scale, over the records E5 re-rates, under the one joint re-rating | measured in E5 |
| 6 | **Not a prediction: an acceptance invariant.** Validation passes with 0 duplicate keys | `validation.passed` and `canary.duplicate_key_count` | true by construction for accepted v10 records, since the batch stops on invalid output and duplicate keys gate. Set A reports the count of v10 attempts whose output failed either, descriptively | 12/12 passed, 0 duplicate keys |
| 7 | **Descriptive, no direction:** report findings | `report_claims.findings` | reported per record and per project in both sets. Reasons:<br>- the counts cross instrument versions: v8's stored blocks are v7, and new runs are checked under v8;<br>- renderer 25's report carries the typed audit's finding totals (#4766), which v8's report did not;<br>- v8's values are 0–2 per record.<br>A directional rule would be decided by noise, as D21 argues against its option (a) | worst, stored v7 and recomputed under v8 alike: CHORUS 2, VOICE 1, AI_READI 1, CM4AI 0. Under v8, CHORUS rep3 goes from 0 to 1 (P1) |
| 8 | **Descriptive, no direction:** replicate structure (#2932) | `replicate_structure` per project: all/some/none, identical, nested counts differ, max/min ≥ 2, intermittent slots | **n=3 primary**, one final attempt per cell; n=2 only a separately flagged sensitivity with common cell indices, n and IDs in every table; fewer than 2 is not computable (items 3/7). D34 says #3336 is in v10 and CHORUS ×3 measures it; that is not empirical proof of a directional structure effect. | P1 section "Replicate structure"; intermittent AI_READI 8, CHORUS 14, CM4AI 17, VOICE 9 |

Rows 1–5 are directional and decidable, rows 6–8 are not predictions, and every
rule is the owner's to fix at P4. Coverage and leaves use #2930's "do not fall".
Recall is "rises where the bundle states the target, and is never invented where it
does not" (3, 3a). Structure and report findings are descriptive, for the stated
reasons.

## Historical October 20 delegation differences

The following records the October 20 draft's interpretation of its original
delegation. Search/remote/worktree observations here are historical, not fresh
exhaustive absence findings. Current D26–D49, the matrix and items 14–16 above
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

- **Owner rulings.** Every still-pending choice above. In order of need:
  - D02, including the **AI_READI comparator** (options (a)–(d), item 2) and the
    **Set A definition** (item 3);
  - D03, D20 production floor, D21, D24, remaining D09 choices, D29 native
    effort/account, D04, D15 and D08. D35/D36 already decide freeze/review policy;
    D34 already decides the rule batch.
- **Items 14–15's composition decisions and evidence:**
  - reconcile the BC1 design label/actual parent tuple and 64k integration delta;
  - integrate reviewed hooks/dependencies, select the D42 guard, and verify the
    complete installed condition and controller-only wire projection;
  - size all six real project contexts at expected/cap scenarios and retain
    request-admission gates; no unsupported proxy certifies Kids First;
  - build exact prompt/schema/contract/receipt/context/registration identities and
    a current budget/trigger from the actual call schedule, then freeze under D35.
- **Plan amendments, for agy and the owner; this draft does not edit the plan:**
  - the `d22b61a9` gates in A4 and A14-reg, and the run tables;
  - D15's and A19-word's "about the size of AI_READI's 542,513";
  - A1's sizing inputs, which do not include Kids First.
- **The #3289 adjudication**, re-read against AI_READI's `1a58ad7b` bundle (prediction
  3a).
- **The E2 protocol and denominator:** owner review/adoption of item 16's exact
  units/weights, blind inventory and split/dedup rules before E2, without changing
  the directional threshold after seeing outcomes.
- **Evaluation identities:** D46 settings remain approved; corrected narratives,
  citations, CHORUS digest inconsistency and per-route readback still need exact
  verification. Native canary ratings remain separately registered/descriptive.
- **Rubric20 version** (#2911, E4).
- **P3:** adversarial review by a Claude reviewer plus a Codex CLI pass. Each finding
  is filed as an issue and fixed in the PR.

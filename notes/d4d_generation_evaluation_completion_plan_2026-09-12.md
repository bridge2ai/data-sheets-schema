# D4D generation and evaluation completion plan — 2026-09-12

Registered in America/Los_Angeles after PR #1339 merged at
`01482abeb31a9999eeeb510c1a821e191f80588b`. This is the continuation plan;
the earlier generation and evaluation registrations remain unchanged.

## Objective and boundaries

Complete the manuscript evidence and prepare a reusable generation pipeline,
covering **both API and agentic generation**, **full and core records**, and
**every existing evaluation style**. Generation runtime, input arm, evaluator
runtime, rubric, and record variant are separate dimensions. A CBORG-backed
semantic agent evaluating an API-generated record does not supply evidence for
the agentic generation arm or for the direct API evaluator.

Use existing source bundles; downloads remain deferred. Preserve all original
records, evaluations, excluded attempts, receipts, registrations and historical
reports. Write new measurements and adjudications beside their predecessors
with their own date, instrument identity and condition. Changes to generic
prompts, schemas, vocabulary or evaluation rules require a new condition;
never restamp a completed experiment to match changed code.

The user has requested this complete arm/style plan and continued issue work.
The completed 56-rating registration and one-record v9 canary are not an
unbounded budget for new model calls. Prepare the exact expanded cohort,
canary commands, output paths, cost limits and review evidence before its
execution decision. Use CBORG for new model work. Do not reuse historical
commands that silently select a different provider or model.

## Verified starting point

| Work | Status and limits |
|---|---|
| CBORG v7/v8 reference rescore | Complete: 24 API-generated full records, 48 primary ratings across the two semantic rubrics and eight rubric10 repeats; 56 accepted ratings. No agentic-generation or core-record extension is implied. |
| Preservation | All 259 prior evaluations retained; 981 measurement-file hashes verified at merge. |
| v9 API generation | One CHORUS full/core canary; all 13 registered gates passed. All 15 artifact hashes still match. No v9 production cohort or v9 semantic-rubric scores yet. |
| Review and merge | PR #1339 merged; review issues #1340–#1360 closed; its branch and temporary worktree removed. |
| CI | PR tests passed. Post-merge run [34731936891](https://github.com/bridge2ai/data-sheets-schema/actions/runs/34731936891) failed the same corpus test on Python 3.10–3.12, with 3,723 passing and four skipped in each job. Repair is the first task. |
| Interpretation | Nine of 24 Q19 rationales and CM4AI pilot Q13/version-scope judgments require adjudication. CHORUS licensing and other model narratives must not be quoted as verified dataset facts. |
| Reliability and costs | Rubric10 repeats cover four v7 records only; rubric20 repeatability is unmeasured. Permission and deadline boundaries confound some comparisons. Two interrupted attempts remain unpriced; the known $161.39939450 CLI subtotal is not total expenditure or a reconciled CBORG invoice. |

Sources: [completion summary](reference_rescore_2026-09-12_cborg_runtime/completion_summary.md),
[semantic inspection](reference_rescore_2026-09-12_cborg_runtime/semantic_review.md),
[v9 review](cborg_canaries_2026-09-12/v9_canary_review.md), and
[API evaluator identity](api_evaluation_instrument_2026-09-11.md).

## Generation coverage

| Dimension | Required coverage and action |
|---|---|
| API runtime | Retain v7/v8 production references and the separate v9 canary. Register a proposed v9 production matrix only after checking remaining generation-impacting issues and instrument stability. |
| Agentic runtime | Inventory the existing v5/v6 generation cohorts, their canonical selections, validation, receipts and evaluation coverage. Prepare a separate current-condition agentic canary using the same declared source bytes as its API comparator. An API canary cannot pass the agentic launch gate. |
| Full/core | Inventory and validate both variants for each runtime. Evaluate each available variant separately; a derived core is not an independent generation replicate. Report missing variants and exclusions explicitly. |
| Input arms | Inventory `baseline`, `de_novo` (documents plus crate), `crate_only`, `healthsheet_only`, `deterministic_upstream`, and `deterministic_ours` from `GENERATION_ARMS`. Keep existing study restrictions and missing inputs visible. Treat these as source/mapping comparisons, separate from API versus agentic runtime. Preserve historical curated and other-model baselines when used in manuscript tables. |
| General-user boundary | Reusable code must accept external datasets and optional vocabulary profiles without requiring Bridge2AI project names, registries or study content. Study-specific inputs and expectations belong in explicit study configuration and fixtures. |

Enumerate actual paths and hashes from the run registry and provenance, not
from method-directory names alone: historical API runs share
`claudecode_agent` directories. Use explicit runtime/configuration selectors.
Do not silently select a latest or best-scoring replicate. A planned cell must
be marked `available`, `missing`, `excluded` with reason, or `not applicable`;
missing evidence is never a zero score.

## Evaluation coverage for both runtimes and both record variants

| Evaluation style | Instruments and outputs | Completion requirement |
|---|---|---|
| Presence/structural rubric scoring | `src/evaluation/evaluate_d4d.py`; rubric10 and rubric20 | Pin the exact mappings, code and source rubrics; evaluate exact manifest paths offline and retain denominators. Presence does not certify factual correctness. |
| Direct API quality scoring | `src/evaluation/evaluate_d4d_llm.py`; both expanded rubric system prompts | Separate CBORG canary and execution registration. Retain driver-attested system/user prompt digests, model/provider and usage. Do not substitute semantic-agent definitions for these prompts or pool their scores. |
| Legacy rubric-agent quality scoring | `.claude/agents/d4d-rubric10.md` and `d4d-rubric20.md` | Inventory and retain historical results. Include this style explicitly in the coverage matrix; any new ratings need their own pinned canary and justification. These field-oriented agents are distinct from the semantic agents. |
| Semantic-agent scoring | `d4d-rubric10-semantic.md` and `d4d-rubric20-semantic.md` | Keep the completed API-full rescore frozen. Prepare missing agentic/core coverage separately. Prepend the registered agents preamble at every spawn, verify check-echo and quoted definition SHA, validate schema/arithmetic, and bind the accepted output to the original evaluator Write. |
| Deterministic validity and provenance | Full/core schemas, duplicate-key detection, pair consistency, schema/prompt/input pins, run/source-bundle checks | Run for every eligible cell under named instruments. Distinguish original run attestations from later recomputation/backfill. Retain findings and denominators. |
| Source grounding, coverage and report checks | `verifiable`, grounding/form checks, receipt/snippet/chunk checks, reconciliation/report claims, related-dataset defects | Use the exact sources each run saw. Keep unavailable historical receipts or snapshots as unmeasured; preserve coverage denominators, spelling/identifier qualifications, and study-specific naming metrics as optional study outputs. |
| Record/source semantic review | `d4d-review-record` with frozen review pack, instruction, sources, schema and receipts | Check instruction compliance and whether evidence supports the populated value. Include unsupported/missed content and report defects. Preserve independent reviews, reviewer identity, timestamps and agreement/adjudication artifacts. These verdicts are separate from rubric scores. |
| Human/adjudicated interpretation and reliability | Original ratings, cited input passages, frozen rubric rules, reviewer decisions | Resolve disputed rationales with an explicit audit trail. Record original verdict, instrument, evidence, adjudicator and date; store any revised verdict beside the original. Include repeat-rating and inter-reviewer agreement coverage, clearly marking unmeasured styles/rubrics. |

Schema-description review is a check on the schema instrument itself; include
it when schema semantics change, rather than counting it as a record rating.
The coverage inventory must retain every row above even where execution is
historical-only, pending a canary, or not applicable. A manuscript table must
identify its evaluator style, generation runtime, input arm, variant, cohort,
instrument digest and scoring denominator.

## Priority loop and deliverables

1. **Restore CI before further release work (#1361).** Reproduce the corpus failure;
   distinguish the backfill authorship marker from measurement content; update
   the registered corpus expectations for the added canary. Preserve every
   frozen artifact. Include corpus tests in PR validation so this failure is
   caught before merge. Require adversarial review and green checks, then merge
   and delete the owned branch.
2. **Build the arm × variant × evaluation-style inventory.** Enumerate current
   records and evaluation outputs, exact paths, hashes, condition identities,
   validation status, counts and gaps. Reconcile canonical/all-replicate
   selectors with provenance. Use the same inventory to derive workload and
   estimates; do not declare a complete cross-arm comparison from 24 API full
   records. Audit offline evaluator entry points against exact-path inputs
   before running them on a cohort.
3. **Resolve semantic interpretation before final manuscript comparisons.**
   Adjudicate the nine flagged Q19 cases and CM4AI pilot concerns against the
   pinned rules and supplied text. Retain CHORUS narrative qualifications,
   timestamp/receipt distinctions and execution-boundary cautions. Prepare a
   dated adjudication protocol and evidence ledger first; any correction is a
   new result, not an edit to the original evaluation.
4. **Settle generation changes before expanding v9.** Prioritize #1299
   (external bundle/chunk onboarding), #1302 (neutral ontology guidance), and
   #1301 (installable resources/CLI). Verify current defects with offline
   external biomedical/clinical fixtures. Keep the historical Bridge2AI study
   reproducible as an explicit profile. Register any changed generation
   condition separately from the already completed v9 canary.
5. **Prepare canaries for each new runtime/instrument combination.** Pin
   source bytes, prompts/playbooks, schemas, definitions, provider/model,
   effort, token caps, permissions, deadlines and exact output paths. Specify
   one-record acceptance gates, attempt and total budgets, repeat panels and
   stop rules. Run each authorized canary and review its original evidence
   before expanding that combination. A changed execution or instrument
   condition requires its own dated boundary record.
6. **Complete the registered production and evaluation matrices.** Include
   both generation runtimes and full/core variants, with the evaluation styles
   above explicitly accounted for. Distinguish generation-replicate spread
   from evaluator repeatability. Preserve exclusions and missing data; never
   use small qualified score differences to select the winning run. Expand
   external evaluation contracts under #1300 as a separate reusable instrument
   while retaining the frozen manuscript reference schemas.
7. **Publish reproducible manuscript artifacts and release evidence.** Derive
   tables/figures from the frozen inventory and named instruments; keep
   historical API/agentic comparisons distinct where the evaluator changed.
   Report source-supported review findings, repeatability limits and known/
   unknown costs. Verify neutral-package smoke tests, all CI jobs, immutable
   evidence hashes and final independent review before merging and cleaning
   up each owned branch.

At the top of each iteration, refresh this priority list against verified
open issues and the current stage. Plan the highest-impact resolution,
implement it, review it, file concrete review findings, and address them.
Use up to five review/fix rounds when needed; if findings persist after five,
run the explicitly requested Codex plugin review. An independent Codex review
may be used earlier. Do not close a finding merely because its measurement is
preserved, and do not mark a scope complete while its required gates remain
pending. Reprioritize newly discovered blockers before new paid work.

## Execution log

- 2026-09-12: Saved this plan before the continuation changes. Confirmed both
  generation runtimes and the distinct evaluation styles from repository
  code. Reproduced the CI mismatch offline: the sole canary-block difference
  is `recorded_by: backfill_checks`; all 15 canary artifact hashes match.
  Corpus totals now include 278 checked records and 1,058 checked claims;
  the old test expects 277 and 1,033. No new model call or download occurred.
- 2026-09-12: PR #1362 implements #1361. Independent review found #1363:
  accepting an absent origin marker without a per-record expectation could
  recast a historical backfill as an original-run check. The correction pins
  all 278 checked provenance paths and their original markers from the merged
  baseline, rejects origin changes and membership changes, and leaves the
  original records unchanged. CI and review must pass on this correction.
- 2026-09-12: The arm inventory found #1364. The default agentic planner
  admitted canonical selections with stale schema-validation pins, whereas
  all-replicate planning excluded them. Record artifact hashes still match.
  The next correction applies one current-validation eligibility policy in
  both modes and runtimes, reports exclusions (on stderr for path-only output),
  and checks the selected corpus root. Revalidation against an explicitly
  chosen schema is a separate act; no original provenance is rewritten.
- 2026-09-12: Review of #1364 found #1365: record diagnostics and canonical
  integrity tests also used the evaluation planner. Those callers now read
  the unfiltered canonical set so stale or invalid records remain inspectable.
  Evaluation workload planning retains its validation gate. Regression cases
  include defective full/core artifacts in both runtimes and project-scoped
  diagnostics with another eligible project present.

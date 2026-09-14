# Source audit after the v10b canary — 2026-09-14

The v10b CHORUS API canary completed at `2026-09-14T06:42:44Z` and is
**rejected for source-support defects**, not accepted for expansion. The
[original review summary](matched_cborg_2026-09-13_v10b/rejected_canaries/CHORUS_api_rep1/README.md)
records the result and hashes of all 38 unchanged original artifacts.
The source registration was
`841bfbcc773e23a83c5c9d4b71e711e18e07a75878653357125f00b1649808a1`;
the launch commit was `e56cd2aeb2d0c530ea8ad920fe5d22a9377c1909`.

Independent local recomputation passes both schemas, duplicate-key checks,
full/core consistency, byte-identical deterministic core derivation, live
provenance and report checks (30 claims, no findings). All 8 chunks were
reviewed and all 94 snippet parts matched. Those lexical checks do not prove
semantic support: only 55 of 112 receiptable slots had receipts, and the
external-identifier checker examined no identifiers. The original record
still turned planned deployment and unestablished modality availability
into current-state assertions (#1782), and attributed a documented text
operation to a privacy method without evidence of that role (#1783).

## Resolution and condition boundary

The API audit instruction and native four-phase playbook now require an
explicit pass over every occurrence of availability, deployment, collection,
processing and privacy claims. The audit compares the passage's subject,
release/date and status, records each affected slot and the lost qualifier,
and distinguishes a software capability from its use on the dataset.
Privacy fields require evidence of the operation's stated privacy role.
Reconciliation revisits every occurrence of the same unsupported assertion
and checks the meaning and status of newly written values.

These are generic generation instructions. They contain no study names,
consortium identifiers, named modalities or vendors. They retain supported
plans and documented privacy methods with their appropriate scope. The
change adds no model phase and does not claim a deterministic semantic gate.
Existing prompt-template files, source bytes and schemas remain unchanged;
the API assembly and native playbook identities change. Tests and public-code
review can validate routing and identity, not establish improved model output.
A new paid canary is still required before either issue's scientific
acceptance condition is satisfied.

Register a distinct **generalized_v10c** condition after this change passes
review and exact-commit CI. Pin the new code, API assembly, native playbook,
runtime and model, existing source bundles, profiles, schemas, output paths
and budgets. Preserve v7/v8, the historical v9 canary, and both rejected v10
and v10b attempts, including original requests, responses and charges. Never
modify a rejected D4D to make the measured attempt pass.

## Work and spending still required

The [parent plan](matched_cborg_canaries_and_cohort_2026-09-13.md) retains
matched **API and agentic generation**, full records and derived cores, all
five Bridge2AI datasets including VOICE_PEDIATRIC, and the complete external
Kids First bundle: 55 documents and all 36 participating-study descriptions.
Use existing Bridge2AI downloads. The Kids First paper's full text remains
uncaptured; its metadata/abstract limitation stays part of the condition.

Only the newly registered CHORUS API canary may launch first. Its original
outputs need independent acceptance before CHORUS agentic, followed by the
external canaries. Kids First also needs the separate full-attempt budget
decision in #1781; its complete sources must not be trimmed to fit a cap.
Stop expansion when any canary fails.

Evaluation remains separately registered: deterministic presence rubrics,
schema/pair/provenance checks, grounding/fitness/subtype/receipts/report
checks, direct API rubric10 and rubric20 quality, field-oriented agents,
both semantic rubric agents with repeat ratings, and source review and
historical adjudication. Pin applicability and each complete instrument;
agent evaluations require the preamble and verified check-echo. The streaming
API evaluator support merged in #1780 after 4,745 CI tests, plus 24 budget
and 23 native transport tests, passed. That merge grants no evaluator launch.

The v10b retry's five settled calls cost an estimated **$3.030621**. Together
with v10's five settled calls, **$6.322086** has been charged against the
additional **$200** allocation, leaving **$193.677914**. The next registration
must carry all ten rows through the canonical ledger without resetting the
allocation or losing pending/unknown charges. Keep the cumulative **$5 per
whole attempt** cap. Catalogue-based estimates are not a reconciled invoice.
The proposed production and complete evaluation matrices still require the
parent plan's explicit workload/cost decision; no runtime, dataset, rubric,
variant or repeat is silently removed to fit the allocation.

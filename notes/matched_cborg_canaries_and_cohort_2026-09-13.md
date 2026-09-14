# Matched CBORG canaries, regeneration and manuscript comparisons — 2026-09-13

This continues the user's five-step sequence after #1469 merged in PR #1760
at `c5fdcaad8830eec58dfb2fb77bd5061bad1382f5`. Work is isolated on
`canaries-v10-cborg`. Registration and offline preparation begin here; this
note alone does not attest a completed canary or a new measurement.

Execution tracking: [#1763](https://github.com/bridge2ai/data-sheets-schema/issues/1763).

## Scope and preservation

Use existing Bridge2AI source documents and the newly authorized Kids First
documentation capture described below. Preserve v7/v8, the historical v9 API canary,
all prior evaluations, exclusions, usage and registrations. New results get
new paths and an explicit dated condition; no completed run is restamped.
The new series will identify its actual prompt-template condition separately
from its cohort version and code/schema/profile identities.

Both **API and agentic generation** are required. Both produce a full D4D and
a deterministically derived core. Input arms are a separate dimension:
inventory baseline, documents-plus-crate, crate-only, healthsheet-only and
deterministic mappings, retaining unavailable and historical-only cells.
The proposed new production comparison uses the baseline documents-only arm
for a matched runtime comparison. Other input-arm comparisons keep their own
conditions and evidence instead of being silently pooled.

The study cohort contains **five datasets: AI_READI, CHORUS, CM4AI, VOICE and
VOICE_PEDIATRIC**. The pediatric dataset retains its own scope and 206,008-byte
bundle (SHA256 `eb823708a16342a3b12cc1dabb57529cea4f95fd596abf9cbecd657a17d61e47`),
six source documents and a validated 13-chunk manifest. Five of those six
documents are shared with VOICE; analyses must retain that dependency rather
than count the two source collections as independent evidence. Its pediatric
referent remains distinct from the adult dataset.

The user nominated **Kids First** for the external biomedical/clinical canary
on 2026-09-13, with the AJHG paper
[The Gabriella Miller Kids First Data Resource for genomic research in pediatric
cancer and congenital anomalies](https://doi.org/10.1016/j.ajhg.2026.07.010).
It will use the neutral profile and the same frozen source bytes in both
runtimes. The original Cell URL had an extra trailing `j`; PubMed confirms
PII `S0002-9297(26)00276-4` and PMID 42607672. The user authorized the Kids First
documentation capture and explicitly required links and information about its
participating datasets. Existing Bridge2AI downloads remain the source for all five study
datasets. The prepared synthetic clinical fixture is retained for offline
software checks only and does not substitute for the Kids First canary.

Scope the external example to the **Kids First Data Resource** described by
the nominated paper. It aggregates multiple studies; a resource-level D4D
must preserve study-specific differences and unknowns. The proposed new
source bundle contains the paper's indexed metadata and abstract, public project
documentation and public descriptions for every study in the captured catalogue,
with capture URLs, dates and byte hashes. Full-text paper retrieval was unavailable
from the publisher; that limitation is part of this source condition. The source
bundle excludes participant-level data files and historical identifier mappings.

## Sequence and acceptance gates

1. **Register before launch.** Inventory actual records, variants and evaluator
   styles; verify post-merge CI; pin code, interpreter/CLI, provider/model,
   sources, source context, chunk manifests, profiles, prompts, schemas,
   definitions, applicability evidence, exact output paths and budgets.
   Query the CBORG model catalogue read-only and retain the selected route,
   limits and prices with their observation date. Verify the actual returned
   model identity when running. No fallback to a different provider is allowed.
2. **Run matched generation canaries.** Use CHORUS and the selected external
   example, each through API and agentic execution using identical source
   bytes and the same declared profile within its pair. Run one attempt at a
   time initially. A failed attempt stops expansion, is retained, and requires
   diagnosis and a separately recorded retry decision. Full/core validation,
   duplicate-key checks, pair consistency, provenance, input/instrument pins,
   chunk/receipt coverage, grounding and report checks must pass. Independently
   inspect source support and original artifacts before accepting either arm.
3. **Run evaluator canaries separately.** A generation canary does not approve
   an evaluator. Exercise each applicable current evaluator style on exact
   full/core inputs from both runtimes. Keep both semantic rubrics and their
   repeat ratings. Agent launches prepend the registered preamble and verify
   check-echo, the quoted definition SHA and original-output binding. Each
   evaluator retains its own scoring domain, applicability context, fixed and
   adjusted denominators, model/runtime and complete instrument identity.
4. **Expand only accepted combinations.** The proposed production matrix is
   the five study datasets × three independent generation replicates × two
   runtimes: 30 full generations and 30 derived cores. Its final manifest and
   spend limit must be fixed before expansion. A CHORUS canary may count as
   replicate 1 only if that inclusion is registered before launch and the
   execution condition remains identical. Preserve failures and exclusions;
   do not choose a replicate using small score differences.
5. **Build manuscript artifacts.** Compare matched source/runtime/variant
   cells under the same named evaluator. Keep generation-replicate variation
   separate from evaluator repeatability. Derive tables from the frozen
   inventory and accepted receipts. Missing, excluded and historical-only
   cells remain explicit, with denominators and reasons.

## Every evaluation style remains accounted for

| Style | Planned treatment |
|---|---|
| Presence/structural rubric10 and rubric20 | Offline exact-file scoring for each eligible full/core record; separate from correctness. |
| Direct API rubric10 and rubric20 quality | CBORG canary per new contract, followed by the registered cohort if accepted; separate from agent scores. |
| Field-oriented rubric agents | Inventory historical evidence; register current canaries explicitly. Any production extension must appear in the workload and budget. |
| Semantic rubric10 and rubric20 agents | New pinned canaries and primary cohort ratings; repeat panels cover both rubrics. Preserve the completed historical rescore. |
| Deterministic schema, pairs and provenance | Required for all generated records, with exact source/schema/renderer pins and duplicate-key checks. |
| Grounding, fitness, receipts, snippets, chunks and report claims | Pin each instrument and its source denominator. Fitness/subtype uses the #1469 specification identity; model-judged work needs its own canary and budget. |
| Record/source semantic review | Frozen source/review pack and independent original-artifact review; retain reviewer identity and decisions separately from rubric totals. |
| Human/adjudicated interpretation and reliability | Preserve original verdicts and store adjudications beside them; disclose which decisions are automated and which are human. Report repeats and agreement without treating one passing canary as repeatability evidence. |

For a candidate semantic repeat panel, use replicate 1 of each study dataset
in each runtime and variant, with three ratings per rubric. This gives 120
primary semantic ratings on 60 records plus 80 additional repeat ratings.
These are proposed counts, not authorization to exceed the final spend cap.

## Historical adjudication remains separate

Prepare an evidence ledger for the nine flagged rubric20 Q19 rationales and
the CM4AI pilot Q13/version-scope concerns. Record original verdict,
instrument, exact cited input passages, adjudicator identity/date and the
reason for any revised interpretation. Preserve CHORUS licensing narrative
qualifications and execution permission/deadline boundaries. A model's
narrative is not a verified fact about the dataset. Never edit old scores
or silently present an automated adjudication as human review.

## Budget and execution status

The user has authorized this sequence and CBORG use and approved **an additional
$200** for this sequence on 2026-09-13. Earlier charges are outside that new
allocation. Prepare the complete workload and cost projection before expansion;
the proposed full matrix is not assumed to fit this allocation. The earlier
$5-per-attempt limit remains in force; every proposed use of that
limit must distinguish an evaluator session, generation session and API
request. Do not hide multiple billable calls behind one nominal attempt.
Actual usage, estimated charges, retries, excluded attempts and unknown costs
must remain visible. Catalogue/CLI estimates are not reconciled invoices.

No paid launch has occurred under this registration. Each launch will require
the final immutable manifest, a reviewed preflight result, the applicable
spend allocation and a clear stop rule. Acceptance records will name the
original output and actual observed instrument/runtime, never a later copy
or a self-reported identity alone.

## Execution log

- 2026-09-13: Saved this plan before new measurements. Documentation deployment
  after #1760 passed; the Python 3.10–3.12 post-merge matrix was still running
  at the initial check. Current Claude Code reports 2.1.270, so the old 2.1.269
  runtime registration cannot be reused unchanged. Main's 26 unrelated
  untracked files and original status were hashed before creating the worktree.
- 2026-09-13: The ignored-inclusive inventory preserves 3,241 files across the
  generation and evaluation directories and enumerates 582 full/core records
  (including flat historical layouts) and 601 individual evaluation files.
  File presence does not attest an accepted rating. The single known duplicate-
  key historical AI_READI attempt remains unchanged.
- 2026-09-13: Preflight reproduced #1761, unsupported temperature in the direct
  API rubric evaluator. PR #1762 carries the fix; 55 focused tests pass and
  independent Codex review approves the exact implementation head. CI is a
  launch gate. The extra compatibility change must be in the new code pin.
- 2026-09-13: Prepared a clearly labeled synthetic external clinical fixture
  under the neutral profile, outside manuscript performance comparisons. Its
  three source documents concatenate through the public CLI and its explicit
  four-chunk manifest validates. No dataset was downloaded. A non-generating
  CBORG token-count probe succeeded; the sanitized receipt is retained.
- 2026-09-13: Updated the study cohort to five datasets and selected Kids First
  as the required external example following the user's correction. No new
  generation or scoring has occurred. The earlier four-dataset/synthetic
  registration remains a superseded, unexecuted planning draft. PR #1762 merged
  as `194fb9ce17edcae3f038605543abc041e9cb9624`; its branch and worktree were
  removed after green CI and independent approval. The additional $200 cap
  remains unchanged; the larger evaluation matrix is a scope proposal, not an
  authorization to exceed that cap.
- 2026-09-13: Main `194fb9ce17edcae3f038605543abc041e9cb9624` passed
  [post-merge build/test CI](https://github.com/bridge2ai/data-sheets-schema/actions/runs/34797045522)
  and documentation deployment. The updated draft contains 15 matched
  API/agentic pairs across all five datasets, 30 distinct unused generation
  output directories and 248 verified input pins. Kids First is explicitly
  pending, so the launch controller refuses scientific execution.
- 2026-09-13: A fresh wheel installed successfully with its declared
  dependencies. Offline checks passed for schema synchronization, simulated
  API generation, full/core derivation, provenance, evaluation/rendering,
  installed agentic helper commands and agent-definition check-echo. These
  checks used synthetic inputs and a fake provider; they are software checks,
  not scientific generation or evaluation canaries.
- 2026-09-13: The user required links, documentation and information about
  participating Kids First datasets. Captured and verified public dbGaP
  descriptions for all 36 catalogue accessions, plus NIH project abstracts and
  resource/access/processing/dictionary/security guides. The resulting
  [source bundle](matched_cborg_2026-09-13/kids_first/README.md) contains 55
  documents, 541,184 bytes and 58 validated chunks; SHA256
  `cc45c89548158a7a909699fbf1f75e6cc88c32ac8486d5518c5d4e46cdc9447c`.
  The paper is explicitly represented by indexed metadata and abstract only.
  The earlier source-capture approval is no longer pending. The previous
  unexecuted registration and its offline validation receipt are archived.
- 2026-09-13: Register the public CLI's standard full/core corpus layout with
  dataset-qualified labels. This makes generation, receipt checks and provenance
  recording select the same files and isolates each attempt's output directories.
  No scientific generation or scoring has run under this new condition.
- 2026-09-13: CBORG's non-generating token-count endpoint measured the exact
  initial API requests: CHORUS 41,479 input tokens; Kids First 233,161.
  With the registered 128,000 output-token ceilings and conservative input
  margins, the first-request reservations are $3.51749375 and $4.95511250.
  Both fit the $5 attempt cap initially; this does not establish that all
  phases will fit. Every later request needs fresh admission against the same
  cumulative attempt and $200 sequence caps. Fourteen offline controller/SDK
  tests pass, including invalid usage, unknown charges and model substitution.
- 2026-09-13: Independent Codex review of public PR #1764 found one spending-guard defect, filed as [#1765](https://github.com/bridge2ai/data-sheets-schema/issues/1765). A streamed response with no verified terminal stop reason now retains its reservation and blocks further spending. Both real-SDK malformed-stream regressions fail against the prior controller and pass with the fix; all 16 offline tests pass. The unexecuted round-1 registration is archived before refreshing pins. No scientific calls have run.

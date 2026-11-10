# Final-generation readiness implementation plan — 2026-11-10

## Objective and scope

Implement and verify only what is needed to generate trustworthy full D4D YAML, derived Core and full-record HTML. User direction: broader AI-readiness assessment machinery, Core expansion and historical migration **should not become prerequisites for this run**.

Main source base: `7233f193ad102a8488b31ec7333662c8fefaa996`, schema 3.2.0.
Native base, separately owned: `5f4a8e211826fe7f83ec51e6262d750687216aba`.
Review: PR #5791 and `notes/schema_review_20261110/` on its branch.
Integration branch/worktree: `codex/final-generation-readiness-20261110`, this checkout.

This task authorizes implementation, bounded offline acceptance, review and PR preparation. It does not launch a model, native CLI, provider campaign, evaluation, release or publication; it does not merge a new PR. Preserve earlier exact protected-packet and scientific decision boundaries. Fix proven failures within assigned scope; do not create new architecture to satisfy hypothetical risks.

## Work units and ownership

| Unit | Owner / current terminal | Scope | Deliverable |
|---|---|---|---|
| G1 | agy1, window 3155 / ttys034 | Tiny end-to-end record-shape, full/Core preservation and HTML acceptance | One maintained regression module and saved bounded evidence |
| G2 | agy2, window 6245 / ttys048 | Issue #2975 collection-type instruction contradiction | Minimal schema-description correction with required generated/release provenance; no cardinality redesign |
| G3 | agy3, window 341 / ttys002 | Operational content acceptance | Concise checklist reusing actual audit, receipt, source review, pair checks and lint; full is authoritative, Core is a projection |
| G4 | agy4, window 6921 / ttys010 | Independent read-only review | Review plan and finished commits; enumerate issues, distinguish blockers from deferrals |
| N1 | Native Codex, thread 01a0f037-6988-7731-a35d-63532027e07a | Native final-record stub refusal | Cheap negative acceptance check through genuine existing gates; narrow fix only if a real gap is demonstrated |
| Lead | Codex lead | Budget, reviews, integration and current-state ledger | Reviewed PR(s), exact evidence, honest remaining blockers |

Parallelize reading, editing and independent review. Serialize schema generation, imports/diagnostics and test execution with one shared worker budget. Native retains sole ownership of its code; main-line workers never edit that worktree.

## Acceptance boundaries

G1 positive fixture: a small fictional full Dataset with scalar narrative, inline identified Person, DUO permission list, scalar collection_type, a file/standard, and evidence-backed-looking synthetic variable/split/privacy examples. Use true pinned schema loading, real full-to-Core derivation, LinkML validation, pair checks and full HTML rendering. Check meaningful values, not only exit codes:
- full input bytes and full-only facts remain intact;
- shared Person, permission and distribution facts survive in Core;
- intended Core omissions are explicit;
- full HTML contains the relevant human-facing values;
- persisted evidence is nonempty and identifies code/schema/interpreter.

Negative variants: narrative array, bare Person string, unnormalized scalar permission and collection-type list must be refused under the appropriate schema. The API normalizer's scalar-permission wrapping is a separate compatibility fact, not permission for silent lossy list flattening. Reuse existing tests where they already cover the boundary rather than duplicating them.

N1 must distinguish an isolated schema pass from whole acceptance. Test an ID-only/stub result through the actual available final-record gates, without manufacturing a misleading passing receipt/evidence claim. A refused gate with an unrelated fixture error is not proof of stub rejection. If complete native composition is needed and exceeds the bounded cheap case, report that exact dependency, keep it unverified and do not repeatedly run the expensive failing prerequisite.

Content acceptance: existing audit/receipt success is necessary in its declared scope; independent source review must disposition missing applicable variables, splits and privacy facts as represented, unavailable or inapplicable. Do not require invented values, make every optional slot mandatory, activate receipt v5, or introduce a new 28-criterion gating engine. Existing lint warnings support review; they are not all automatic failures.

## G2 release handling

Correct only the contradictory scalar collection-type prose while preserving accepted values/cardinality. Schema prose is model-visible to native and changes captured bytes. Follow current release-history rules, regenerate required products and comprehensive mappings, and retain old 3.2.0 identities. Determine the smallest valid patch-release treatment from current release code/history; do not infer it from the obsolete datasheet HTML version guide. Propose final schema identity in the handoff. No release/tag/DOI publication. No unrelated ontology/mapping corrections.

Changes to protected runner/prompt-registry/scanner files are not part of this unit. If a generated consistency check reveals a necessary protected update, prepare an exact reviewable packet and notify lead; do not silently widen scope.

## Execution budget and efficiency

- No new environments, dependency installs, full corpus copies or heavyweight worktrees.
- Use sparse isolated worktrees outside the primary repo, pinned to the assigned base, and the existing environment.
- No edits, stash, reset or branch switch in the dirty/diverged primary checkout.
- First run exactly one relevant tiny canary, capped at 30 seconds; inspect artifacts before expansion.
- After a passing canary, affected focused checks may run serially, ordinarily capped at 300 seconds. Stop a known prerequisite failure; repair/re-canary before dependent cases.
- G1 owns the initial execution budget. G2/N1 prepare source and exact commands first and request budget via their handoff/status; this is coordination, not a new human permission flow.
- Use existing proven subprocess deadlines/process cleanup. Do not invent a benchmarking framework or claim the helper canary establishes native runtime acceptance.
- Lead grants the next owner and records release; no nested worker fanout.
- One integration CI checkpoint after reviewable stable main-line changes. Do not launch whole-suite local tests during routine iteration.
- Keep scripts in scripts/adhoc with purpose/date/inputs/outputs. Preserve failed evidence. No shell/network helpers that disclose email addresses or notify people.
- Existing required native lifecycle gates remain separate from these content checks. Do not claim final generation is ready until its actual execution prerequisites are met.

## Deferred work

No new Core fields, 28-criterion assessment engine, bulk historical migration, FAIRSCAPE redesign or general semantic vocabulary cleanup. Issues #4034, #3972, #3025, #4044, #5788, #5789, #5790 remain export/semantic-release work unless a current acceptance check demonstrates a direct generation defect. #5786/#5787 assurance wording may be clarified in the checklist; a broad documentation rewrite is not a prerequisite.

## Delivery and review

Workers commit locally on their assigned branches and report exact SHAs, changed paths, commands, test outcomes, artifact paths, preserved limitations and budget release. Lead combines compatible main-line work into one reviewable PR; native-base changes remain separate with their integration dependencies explicit. Every adversarial finding gets an issue or an existing issue association, and is triaged before merge readiness. User has not yet approved merging this new PR.

Run-ready requires: exact final schema/source/registration identities; required existing native/runtime acceptance completed; G1 and N1 proven at the relevant integrated head or explicitly unresolved; source-review procedure ready; one genuinely authorized canary before any batch. This plan itself is not a generation launch word.

## Live ledger

- Initial source and worker identities verified; all five designated workers were idle.
- Disk available at start: about 23 GiB; preserve existing recovery evidence.
- G1 initial execution grant: one 30-second canary, then focused checks only after verified success.
- G2, G3, G4 and N1: assigned preparation/review; G2 and N1 executions wait for serial budget.
- 2026-11-10 21:57 UTC: G1 explicitly released its budget with no active test (`handoffs/agy1-budget.md`). N1 granted exactly the prepared 30-second receipt-component canary at `41e0d1c1330d52f4bee34d018a8a958fffb99315`; inspect evidence and release before any follow-on. G1 continues source-only fixture work.
- 2026-11-10 21:59 UTC: N1 receipt canary completed normally (one test, 0.779 seconds total), artifacts and retirement verified, budget released. Identifier-only attestation can satisfy these receipt components; whole native acceptance remains unverified. Independent wrapper findings recorded as #5792/#5793; native handles source-only fixes. G1 regains the bounded execution grant. G4 report corrections are tracked as #5794.

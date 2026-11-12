# agy4: native D4D latency assessment and implementation plan

Assigned by the Codex lead at the owner's request, 2026-11-10 UTC.
Worker identified as Terminal window 6921, tab 1, tty /dev/ttys010. Its
last-login banner refers to ttys053; ttys053 is the lead, not this worker.

## Objective

Independently assess the saved discussion, investigate its claims against the
current code and evidence, and write a concrete implementation plan for the lead
to review. Do not implement that plan. The user wants faster native-agentic D4D
development and reliable generation, without confusing model runtime with
adapter, observer, test, CI, or coordination overhead.

## Locations and ownership

- Primary repository: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema`.
- Input document: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.temp/generation-eta-20261110/notes/reviews/native_development_latency_2026-11-10.md`.
- Analysis worktree: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.temp/generation-eta-20261110`, branch `codex/generation-eta-evidence-20261110`.
- Required output: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.temp/generation-eta-20261110/notes/reviews/native_latency_implementation_plan_2026-11-10.md`.
- Optional supporting artifacts: `notes/reviews/native_latency_plan_evidence_2026-11-10/` inside that analysis worktree.
- If a new extraction/diagnostic helper is necessary, save it under that worktree's
  `scripts/adhoc/agy4_native_latency_*.py` with purpose, inputs, outputs, date, and
  this assignment as provenance. No inline result-producing scripts or temporary
  helper files. Prefer existing evidence and simple read-only tools.

The lead explicitly delegates only those output paths to you. Do not switch
branches, stage, commit, push, open or modify PRs/issues, or change other files in
the shared analysis worktree. The lead handles the plan's review and publication.
Read the primary coordination STATUS before working. You may append one concise
entry under `### agy`, labeled `agy4 native latency plan`, with output path,
hash, source snapshots and outcome. Do not edit others' entries or the Board.

## Investigation

1. Build a claim table: input claim, supported/corrected/uncertain, exact evidence,
   and practical consequence. Explicitly separate historical API timings, old
   synthetic native successes, current synthetic failures, and unmeasured live
   native performance. File timestamps alone do not prove work duration or cause.
2. Inspect current native source and test call paths. Read the latest U3-K report
   and retained profile summaries; identify actual commits/trees and snapshot
   times because the existing Codex worker may still be updating them. Also read
   U3-L/M assignments, relevant U3/J2/readiness reports, and the tiny synthetic
   fixture. Locate repeated schema/selection/registration verification and what
   invariants each call protects. Do not assume that every repeated verification
   is redundant or that a cached admission verdict is safe.
3. Investigate instrumentation overhead separately. Design the smallest matched
   observer-on/off comparison that preserves correctness assertions and source,
   inputs, process configuration and result checks. State what historical numbers
   cannot establish. Recommend this diagnosis before a large architectural change
   if the evidence warrants it.
4. Assess CHORUS as the first real canary versus inner-loop development data.
   Explain the role of tiny-schema contracts, real-schema micro integration,
   genuine synthetic completion and full CHORUS acceptance. Preserve registered
   scientific inputs; smaller development fixtures do not certify a full canary.
5. Inspect current CI workflow and recent real run/job timings read-only. Separate
   queue, environment setup, test execution and cancellation/restart. Assess test
   selection, fixture cost, required complete-suite coverage and dependencies.
   Do not claim a recent regression without a comparable earlier baseline. Look
   for existing timing/sharding facilities before proposing new infrastructure.
6. Identify process waste: downstream tests blocked at the same prerequisite,
   broad reruns after narrow edits, overlapping ownership, unnecessary artifact
   regeneration, and stale branch integration. Distinguish evidence from inference.
   Existing hashes, replay, refusal tests and required final coverage stay intact.
7. Research relevant technical uncertainties using official/primary documentation
   when needed. Use read-only connected tools or anonymous web requests, never
   disclose email addresses, and cite the exact source supporting any external
   claim. Local source and retained measurements should carry the main argument.

## Required plan structure

- Short verdict and corrected understanding of the bottleneck.
- Evidence table with measured values, exact source/head, scope and limitations.
- A dependency-ordered sequence of SMALL work packages. For each: objective,
  files/functions, owner lane, prerequisites, proposed change or experiment,
  smallest decisive test, acceptance criterion, failure/stop condition, expected
  cost/runtime budget, broader regression obligations, and rollback/recovery.
- Distinguish measured duration from proposed time budgets. No fabricated native
  throughput, calibrated ETA, CPU savings or success probability.
- First package should resolve one observable question or broken boundary; avoid
  a speculative framework rewrite. Explain whether the proposed verified-current
  snapshot is needed, premature, or replaceable by a smaller change.
- Include timing/call-count regression strategy and safe reuse boundaries. Never
  cache `validated=True`, widen freshness/deadline limits, weaken source/refusal
  checks, skip failing tests to claim success, or change scientific contracts as
  an incidental performance fix.
- Specify gates between fast tests, real-schema integration, one complete
  synthetic case, affected cohorts, full CI, real-binary probe, and CHORUS.
  Report blocked/unrun tests honestly; preserve complete final acceptance.
- Identify conflicts/dependencies with current Codex U3-K/L/M and agy scanner/PR
  work. Propose ownership that does not edit another active worker's tree.
- Explicitly list any owner decisions or new permissions genuinely needed before
  implementation or live probes; do not manufacture approval steps for routine
  read-only research. Stop after delivering the plan for lead review.

## Execution limits

This is research/planning. Do not run pytest cohorts, builds, installations,
provider/model calls, real native executables, permission probes or generation.
Do not mutate any production/test/scanner/prompt/schema/workflow, packet,
registration, existing evidence or another session's worktree. No merges, rebases,
branch cleanup, force pushes or external notifications. No at-mentions.

Use ignore-independent searches (`rg -uu`, explicit filesystem enumeration) for
completeness claims. Read-only Git and GitHub inspection is permitted. A small
existing-evidence extraction may run in the foreground; if a batch becomes
necessary, verify one real unit before expansion. No background jobs or new
subagents: this worker is the assigned research lane.

When done, verify the output is nonempty, calculate its SHA-256, log the one
STATUS entry, and return the full path and findings. The Codex lead will perform
a separate read-only review and may send a bounded revision request. Do not
start implementation even if your plan appears straightforward.

# Collective worker checkpoint review — 2026-09-24

Issue #2386 adds an explicit experimental audit condition. A complete, closed
worker set can supply one fresh integration session after an unpaid budget
denial, provided the original integration never attempted the terminal
scientific check. This change does not accept worker judgments or an audit.

The source must be the immediate settled predecessor and an ordinary fresh
batch. All workers retain their original registration, closure, proposal and
request identities. Their costs, failed integration costs and unknown provider
fees remain consumed. New integration requests use a distinct attempt with no
new worker allowance. No stopped integration output or feedback becomes a
model input, and existing registrations never select this mode implicitly.

Independent accounting and scientific/runtime reviews identified and resolved:

- #2387: enforce the stopped source's original attempt and worker ceilings,
  reservation witnesses and debit limit before reuse.
- #2388: bind the original parent job, plan, scientific implementation and input
  bytes. Rebuild both integration prompts at their original locators and compare
  their hashes without reading old integration text. Check the proposed
  repository before creating a preparation destination.
- #2389: retain immutable historical evidence pins while allowing a later
  finalization/evaluation checkout to pin its own verifier implementation.

Regression coverage includes real worker closure replay, identical scientific
assembly bytes, original-locator prompt equivalence, complete source and finding
context, forbidden historical text, exact accounting-prefix preservation,
ownership races and per-request revalidation. Removing the inherited-worker
revalidation call makes its admission test fail before simulated transport.
The new tests use synthetic records and scripted providers.

The independent reviews found no remaining blocking source findings. A canary
still requires a separate pinned registration, complete original worker proof,
current ownership, launch review and execution checks. A successful integration
then requires full independent scientific review before Phase 4 or evaluations.
This review authorizes no new budget and records no scientific acceptance.

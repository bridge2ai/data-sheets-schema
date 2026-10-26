# D41: retain failure, rejection and response history before continuation

Local implementation for #5138/#5142, starting from `f8c5ac73c` in the assigned
`claude/d41-latch-guard` worktree. This is offline engineering. No provider,
token-count endpoint, live probe, registration launch, push or merge is part of
this work. Final verification is recorded below; this note does not authorize
generation or scientific acceptance.

## Contract

The runner writes `{P}_latch_journal.jsonl` in the run metadata directory. Its
append-only hash chain binds the run identity and generation to failures,
rejections, consumed control state and each saved response's usage ID, name,
path and SHA256. A saved response has corresponding ledger and snapshot-index
pins; verification checks actual file bytes too. The ledger retains a journal
checkpoint so deleting a valid suffix is not indistinguishable from an older
intact journal. Recovery inventories include the journal and override sidecar.

Startup verifies integrity before recovery can settle or rewrite a delivery.
Each physical transport attempt verifies again immediately before dispatch.
The callback is controller state and does not enter SDK request arguments.
Existing transport retries remain subject to their original limits.

Report rejection is not automatically a terminal failure. The first rejected
report and a worse rejected replacement remain in immutable history, including
when the original text is restored. The existing one-regeneration allowance
is retained. Pending source review can become accepted through the existing
validated writer; editing the persisted admission directly is a discrepancy.

Raw regenerated reports and repairs are saved before rejection, truncation or
parsing can discard them. Applied repair and unusable-response snapshots retain
the actual delivery's usage ID, even if a readdressing call appended another
row. Partial streams share the existing abandoned-row ID with their snapshot;
they do not create a completed charge. An unfinished resume proves those
snapshot IDs against the real abandoned journal as well as completed usage.

The receipt transcript selector may advance to an already journaled exchange
before completion intent or the full seal exists. Both old and new exchanges
remain immutable, independently usage-linked snapshots. The prior and proposed
ledger must both be pre-seal, and the new selector must name an already saved
snapshot; adding its alleged proof in the same write is refused. The full seal
is itself a monotone allowance latch. This preserves legitimate re-addressing
without permitting a raw selector rollback or another completion purchase.

Terminal history never grants a new call after an override. Existing receipt,
typed-audit, accounting, request-size and budget guards stay operative. The
shared-generation prohibition on fresh reuse of spent outputs stays in place.
The existing nonshared explicit fresh-generation path still archives its prior
generation; startup integrity checking is separate from spending permission.

## Explicit acknowledgements remain assisted evidence

An owner-authorized `{P}_latch_override.json` must name the exact run identity,
generation and affected journal event hashes, together with nonblank
`authorization`, `authorized_by` and timezone-aware `authorized_at`. Its format
is `d4d_latch_override_v1`. It acknowledges specified observed discrepancies;
it does not rewrite the journal, restore a clean state, reset allowances or
certify a scientific result. This implementation does not invent authorization
or write an override for any real run.

Applied acknowledgements are retained in the journal and ledger. Removing the
sidecar cannot remove the assistance history. An unchanged authorization file
cannot authorize a later, different edit to the same event. Missing or corrupt
history must not be silently adopted as an intact new history. A deliberately
acknowledged legacy baseline is labelled unverifiable, rather than clean.

Provenance stores `model.runtime_integrity`, with exact journal path/SHA/head/
line count, `verified`, `assisted`, `evidence_only`, and acknowledgement history.
This is controller metadata, not a statement about model behavior. Its declared
authentication limit is `not_cryptographically_authenticated`: local hashes
detect inconsistency against retained checkpoints, not a coordinated rewrite
of every local artifact and every supposed trust anchor.

## Acceptance and evaluation boundaries

Live and offline canary admission refuse a present assisted, evidence-only,
unverified or malformed D41 block. Such records cannot supply a canary
baseline or enter registered evaluation preparation. Quality and schema-validity
measurements are preserved; eligibility does not rewrite their counts. Legacy
records without this new block acquire no invented integrity attestation.

Completed resume cannot return a provenance record that omits an applied
override as though it were an unassisted completion. Other diagnostic readers,
historical evaluation-plan builders, support-scoring tools and blind-review
pack construction remain distinct entrances; these changes are not a universal
ban on inspecting or measuring retained evidence. Any final-campaign admission
through those entrances needs the same D41 eligibility check or an explicit
evidence-only designation. This is a follow-up for orchestration, not a claim
that historical quality scores were invalidated or recomputed.

## Model-facing and protected-file boundary

The bounded parity helper compares exact SDK HTTP request bodies for CHORUS
generic-v10/shared-v1 using the same fixed inputs and original `f8c5ac73c`
controller source. It includes full, reconcile, report, report-regate, receipt
completion, typed worker, omission and integration construction. Synthetic
records/replies and MockTransport make this a construction/transport check,
not generation or complete state-machine acceptance.

Shared-v2 binds controller code into its registration, which is itself exposed
in typed requests. Fresh v2 identities therefore change after controller
changes; old registrations must remain stale. They must not be normalized away
to manufacture request equality.

`shared_generation.py` and canonical hash registries remain untouched. The
exact [proposal](d41_shared_generation_patch_proposal.diff) adds the new journal
module to shared-v2's routing dependency closure. **AGY must apply and review
that protected-file proposal before treating the v2 stack as complete.** The
registered evaluation route separately pins the new eligibility implementation
in its own executable authority inventory.

## Review findings and verification

Independent read-only review identified override-file reuse, consumed regate
scalar edits, missing-ledger legacy classification, executable-authority
pinning, durable directory sync and expected/found diagnostics. These have
corrections and causal coverage. Regression testing additionally found the
legitimate pre-seal receipt-selector transition described above. Final review
found repair, unusable and partial-stream saved deliveries without usage pins;
those hooks and their causal tests are now included and independently reviewed.

Completed offline batches are retained, including failed runs:

| Batch | Observed result | Interpretation |
| --- | --- | --- |
| focused | 74 passed / 1 failed / 125 deselected | Override fixture named one affected event instead of three; corrected. |
| core-parity | 201 passed / 1 failed | Core/API/eligibility checks passed; parity fixture needed valid typed claims and isolated baseline imports. |
| regressions | 38 passed / 12 failed; interrupted | Stopped for fixture/changed-boundary triage; not a complete group. |
| parity-fixed | 4 passed | Eight exact shared-v1 SDK request bodies matched. |
| regressions-fixed | 332 passed / 8 failed; declared failure bound | Genuine receipt-selector regression plus seven fixture/diagnostic mismatches; corrected. |
| final-gates | 245 passed / 1 failed; 574.09 s | Full shared completion/replay, real readdress and fresh parity passed. New restoration fixture had unfinished snapshot activation; it now settles through the production function before the unchanged byte-equality assertions. |
| delivery-gates | 349 passed / 1 failed; 266.53 s | Final production bytes passed transport, accounting, repair, resume, eligibility and fresh parity cases. The new readdress-attribution fixture supplied an empty receipt and stopped before its intended boundary. |
| unusable-final | 18 passed; 3.38 s | Corrected nonempty receipt reaches readdressing exactly once; every usage-ID, row-separation and byte-preservation assertion remains. No production bytes changed after delivery-gates. |

These overlapping batches are not additive counts of distinct tests or a full
repository suite. All observed failures have been addressed and the affected
cases passed their final reruns. Earlier logs are observations at their stated
iteration, not claims about every final byte. The full shared completion/replay
pass preceded the final repair/partial-delivery API hooks; the later batch
exercised those hooks and their resume paths, without repeating that long test.

The [retained manifest](d41_validation_2026-10-26/manifest.json) pins all eight
log/XML pairs and the final baseline/candidate captures and registrations.
`scripts/adhoc/d41_archive_validation_20261026.py` copied exact bytes and checked
the parity summary's eight body hashes. Python was the primary checkout's
3.13.12 environment, with explicit guard-tree imports, bytecode disabled,
pytest plugin autoload disabled and serial execution. The recorded dependency
deprecation warnings were not failures. Installed package bytes are not
independently authenticated by this evidence.

`git apply --check notes/d41_shared_generation_patch_proposal.diff` passed on
this base; the protected proposal remains unapplied. Both protected production
files are unchanged. This is a locally validated H3 implementation ready for
the separately required final-SHA review, not an integrated v2 stack, CI pass,
remote publication or generation clearance.

The existing primary-checkout review named
`notes/reviews/d41_latch_guard_review_2026-10-25.md` describes a different
`9fa5d391b` implementation and does not review this patch. A separate final-SHA
review remains Claude's/AGY's publication gate.

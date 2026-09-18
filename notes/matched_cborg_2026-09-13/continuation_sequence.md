# Shared budget ownership foundation

`continuation_sequence.py` supports two explicitly registered transfers:
independently accepted native audit → reconciliation → evaluation. It is not yet
wired into any launcher. It does not implement Phase 4, accept its scientific
results, authorize a job, retry an attempt, or complete issues #2114/#2115.

The original `audit_sequence.json` and its unchanged `.lock` remain the single
ownership namespace. The state is atomically upgraded to version 2. Its legacy
tip fields permanently point at a pinned **non-ledger** seal, while `active_tip`
identifies the current successor registration and real ledger. Both historical
audit guards refuse the seal. A stage label alone would not stop those guards.
Historical registrations, artifacts, ledgers and request rows are unchanged.

## Calling contract

```python
with owned_sequence(manifest, registration_path, registration_sha256) as owner:
    # Existing controller still checks its independent launch review, code,
    # instrument, exact permitted tools, canaries and exclusive attempt paths.
    owner.verify_admission()  # before token counting and again before reservation
    ticket = owner.reserve(registration_sha256 + ':' + registered_job_id,
                           estimate, request_sha256)
    # Existing transport executes, retains evidence and settles through
    # owner.ledger. Complete bounded shutdown before leaving this context.
```

Only jobs in `manifest.job` (reconciliation) or `manifest.evaluation_jobs`
(evaluation) may reserve. The original total/default caps are preserved;
explicit successor per-job caps must name roster members. Their approval remains
the launch review's responsibility. The lock context is shared across threads,
and an owner cannot admit or reserve after context exit. The controller must
use this gate on every admission; direct calls to a free-standing `Ledger` do
not provide sequence ownership.

Reopening the exact active registration requires its existing ledger, correct
manifest/caps, unchanged carried prefix and valid descendant request identities.
It also reconstructs the complete activation state from the pinned predecessor
snapshot and exact transfer, including prior transfers. Missing, extra or changed
state/history fields are refused even if `active_tip` still names this owner.
This permits sequential evaluation jobs and status inspection. **It is not
permission to restart a consumed native/API attempt.** Exclusive attempt/result
files, stop rules and unknown-charge handling remain controller responsibilities.

## Manifest fields

Paths are canonical, absolute and nonsymlinked. A `ref` means exactly
`{"path": "...", "sha256": "..."}`. Every referenced file and this module must
be present in `pinned_files`. The registration file is checked against the
caller's exact hash and in-memory manifest.

```text
budget_sequence:
  protocol: shared_sequence_v2
  stage: reconciliation | evaluation
  state_path: original-generation-ledger-parent/audit_sequence.json
  origin:
    registration: ref to original generation registration
    ledger_path: exact ledger location declared by that registration
  audit_origin: predecessor describing the accepted original audit
  predecessor:
    stage: audit | reconciliation
    registration: ref
    ledger: ref to actual settled predecessor ledger
    state: ref to immutable exact pre-transfer state snapshot
    result: ref to completed controller result
    acceptance: ref to independent acceptance
  seal: ref to deterministic seal_document(manifest)
budget:
  additional_usd: unchanged original allocation
  per_attempt_usd: unchanged original default cap
  per_job_attempt_usd: optional explicit roster-bound exceptions
  ledger_path: this-registration-directory/billing.json
  continuation:
    checkpoint: exact predecessor ledger path
    sha256: exact predecessor ledger hash
    cost_usd: sum of all settled predecessor request costs
```

`audit_origin` stays unchanged in every successor. `seal_document` is a pure
renderer of the immutable seal; preparation writes and pins those bytes before
review. It contains no successor manifest hash, avoiding circular hashes, and
no `manifest_sha256` or `requests` fields. It cannot be mistaken for real
accounting. The activation state binds the final successor registration hash.

The accepted predecessor result must bind its registration/job, completed
mechanical validation, no unresolved requests, a completed proxy shutdown and
an actual integer zero for unfinished handlers. An audit result uses the
existing `phase3_audit_only` scope and `audit_path`/`audit_sha256` fields.
Its actual pure-validator report must be checked, have empty findings/errors,
name the registered job and match the accepted audit hash/path. The registration
hash belongs to the outer result; it is not required inside that pure report.
Reconciliation will need a `phase4_reconciliation` result with an `artifacts`
map of exact absolute paths to hashes. All named artifact bytes are verified.
Independent acceptance must contain `verdict: accept`, the exact registration,
result and ledger hashes, and the identical artifact map. The foundation
verifies bindings; it does not decide whether the audit/final pair is correct
or whether the caller's reviewer is sufficiently independent.

The future Phase4 controller must require all intended full/core/report/
provenance artifacts and scientific/procedural checks. A hash map alone does
not establish those requirements. The existing evaluation controllers need an
explicit integration for this lineage; their separate chain initializer must
not also run. Aggregate evaluation closure → conditional subtype registration
is not implemented in this bounded foundation.

## Transition and failure behavior

Under the legacy lock, the module rechecks pinned evidence and exact current
predecessor state, verifies closure/acceptance and settled costs, exclusively
creates the new ledger and calls real `Ledger.continue_from`. It fsyncs the new
ledger and directory, writes/fsyncs a same-directory state temporary, atomically
replaces the canonical state, then fsyncs that directory. The lock file is never
replaced. This closes old audit admission and activates the new owner in one
state transition. Per-admission checks revalidate ownership, immutable evidence
and the carried accounting prefix.

Before lock acquisition, it rejects overlaps between immutable pins/references
and the mutable state, lock, new ledger or ledger write companions. This includes
hard-link aliases among mutable destinations as well as immutable inputs:
acquiring an OS lock must not truncate accounting state or a pinned input. The
same check is repeated under the lock before creating or replacing anything.

If preparation crashes before state replacement, the old owner remains; any
orphan successor ledger is refused rather than adopted. Prepare a separately
reviewed destination after verifying the current state. If a crash occurs after
activation, the audit stays sealed. Ownership/status reentry does not require a
nonexistent successor acceptance, but the controller must determine whether any
attempt started before it can execute anything. Never roll back the seal or
silently rerun an ambiguous attempt. Missing, malformed or changed state fails
closed. Unresolved predecessor charges and unknown/nonzero unfinished handlers
prevent transfer.

The handoff fsyncs its own new durable boundary. Existing later
`Ledger.transaction` writes retain their current atomic-replace behavior; this
change does not claim a new power-loss guarantee for every transport write.

## Offline verification

```bash
PYTHONPATH=src python -m pytest -q \
  notes/matched_cborg_2026-09-13/test_continuation_sequence.py
```

Tests use real `Ledger`, real filesystem locks, worker-thread admission and
synthetic immutable closure evidence. `historical_sequence_guards.json` retains
the exact PR2108/PR2113 function bodies with original commit, full-source and
function hashes. Tests execute those old guards, proving they admit ordinary
predecessors before sealing and refuse both seal-as-ledger and confirmed-charge
bridge attempts afterward. They also cover two-child budget forks, both stage
transfers, repeated owner use, changed source/current accounting, lifetime and
roster bounds, interrupted activation and durable write ordering. They are not
claims of scientific acceptance, provider execution or successful Phase 4.

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

## Durable ownership evidence for new registrations

The optional `--durable-sequence-claim` flag is available to the audit,
finalization, composite evaluation and subtype preparers
([#2137](https://github.com/bridge2ai/data-sheets-schema/issues/2137)). It selects
`sequence_claim: {protocol: durable_sequence_claim_v1}` and pins the shared
`sequence_claim.py` helper and its audit lock implementation. Select it explicitly
for each new condition. Omission leaves claim preservation disabled; no old
registration or stopped evidence changes.
Legacy evaluation accounting outside `shared_sequence_v2` does not claim this
guarantee. The optional claim protocol does not change financial authorization.

All audit guards in this updated implementation acquire their existing lock with
nontruncating `open` and `flock`, even without claim opt-in
([#2141](https://github.com/bridge2ai/data-sheets-schema/issues/2141)). The lock must
be a regular file owned by the current user, with exactly one link, and still name
the opened inode before and after acquisition. The implementation lives in the
already pinned audit module; frozen historical checkouts remain unchanged. The
claim helper uses this same lock for shared ownership and pins its source too.

After the existing origin lock and ordinary ownership checks, the canonical owner
advances normally. Before the guard yields, the helper creates `sequence_claim/`
beside the validated condition's `registration.json` and `billing.json`. This
destination is derived, never supplied as an unbound caller pathname. It contains:

- `owner.json`: the exact bytes read from the canonical owner, not a reserialized
  dictionary.
- `predecessor.json`: the exact preceding owner bytes, unless this was the first
  audit claim and no owner existed.
- `manifest.json`: canonical owner path, claiming registration path/hash,
  original generation registration/ledger identity, stage, helper hash, owner and
  predecessor byte hashes, and explicit first-claim absence where applicable.
- `ready.json`: an exact hard link to the manifest inode, published only after
  every required persistence operation and byte comparison succeeds.

The canonical owner and directories are synced. Each snapshot file is written to
an exclusive temporary inode, flushed and fsynced, then published atomically with
a no-replace hard link. The claim and containing directories are fsynced and the
canonical/retained bytes are rechecked before admission. Existing foreign files,
symlinks and hard-link aliases are refused, except for the exact two-link
manifest/witness pair. Partial temporary files remain for review after failure;
they never count as a complete claim.

The no-replace `ready.json` link is the publisher's last fallible operation
([#2142](https://github.com/bridge2ai/data-sheets-schema/issues/2142)). No fsync or
verification follows that publication inside preservation. All snapshot bytes
and directory entries have already been synced. The additional witness entry
itself may disappear on a crash; absence blocks reentry and cannot be repaired
automatically. This trades recovery availability for fail-closed admission. It
avoids allowing a later attempt after a reported fsync failure merely because
all ordinary claim files were already visible. This assumes local filesystem
atomic link/fsync behavior; it is not a guarantee against dishonest storage or
arbitrary privileged replacement of evidence.

If preservation fails after advancement, the new owner stays consumed and the
guard does not yield. A best-effort `sequence_claim_failed.json` records that
no-admission failure; a failing filesystem cannot guarantee that even this marker
persists. An existing failure marker or its unfinished temporary file blocks
reentry, but correctness does not depend on that marker: every failed persistence
boundary leaves the required success witness unpublished. Missing or incomplete
claims are never repaired during reentry. The
shared owner verifies its existing claim read-only on each reentry/admission;
audit identity reuse remains forbidden regardless of snapshot existence.

Claims are administrative records and are not model inputs. They are evidence of
an observed transition, not proof that this owner is still the sequence tip, not
permission to resume an attempt, and not instructions to reconstruct a lost
canonical state. Recovery still requires the complete claimant chain and separate
review. These snapshots do not settle provider charges or accept scientific work,
and do not add power-loss guarantees to later transport/ledger writes.

## Offline verification

```bash
PYTHONPATH=src python -m pytest -q \
  notes/matched_cborg_2026-09-13/test_continuation_sequence.py \
  notes/matched_cborg_2026-09-13/test_sequence_claim.py
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

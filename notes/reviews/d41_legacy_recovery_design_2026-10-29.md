# D41 legacy recovery: design for owner review, 2026-10-29

**Proposal and offline evidence only; no production change or publication approval.**
The owner kept legacy recovery blocking #5212 at 2026-10-29T18:42Z. This note
does not supersede that decision or close #5268. The recommendation is an
explicit, manifest-bound import into a fresh destination, plus a separate
strictly no-spend completed-replay operation. The source remains immutable.
The alternative is a more invasive transaction in the original generic-run
directory. Neither option relaxes any existing-journal guard.

## Authority and scope

- Tested base: `d9b69d84d9a6936809681ae240bb8e767649ca11`, #5212
  `20def9d63` plus the test-only fixture repairs; branch
  `codex/wave8-5212-legacy-design-20261029`.
- Emitting source: `f8c5ac73caba610d40c49aaceddb31ead3590a72`, detached
  worktree under `$TMPDIR`. No latch-journal module exists in that Git tree
  or in an ignore-independent physical search of its `src/` directory.
- Owner boundary and exact IDs: Wave 7
  `wave7_ci21_disposition_2026-10-29.md`, “Owner decision and compatibility
  boundary”; `wave7_ci21_mapping_evidence_20261029/mapping.md`; and
  `wave7_pre_d41_control_selection_2026-10-29.md` on local branch
  `codex/wave7-suite-tools-20261029` (re-read with `git show` after the reboot;
  source commit `e13badedf556ddfa5ffce506b96ec188b5e1a8c3`).
- [D41 and D55–D57](v10_human_decisions_and_context_review_2026-10-20.md):
  guard A, fixed first; terminal/control discrepancy ends the run; a retry
  needs a new registration; the expected journal head comes from the launch
  monitor, never from the directory being checked. Assisted means evidence-only.
- Claude's `pr5212_4f20a300d_claude_rereview_2026-10-28.md` in
  `d4d-executions/plans/reviews/`: R3 says innocent interrupted-write recovery
  is assisted; F4 does not authorize recovery of terminal/control suffixes;
  F10 was deferred, not solved. The owner's later blocking decision governs.

## Authentic controls and what they establish

The reproducible driver is
[`scripts/adhoc/d41_legacy_controls_20261029.py`](../../scripts/adhoc/d41_legacy_controls_20261029.py).
It runs the **original f8 tests** against f8 imports, captures the entire
fixture root immediately before and after each public `execute`, and retains
the original test assertions. Recovery faults are the original tests' faults:
missing/corrupt **pre-D41 usage ledgers**, synthetic unrelated archives, an
injected index-publication error, and malformed reasoning. It never removes
a current latch journal. Every imported package/test module's source path
and hash is recorded.

These are external-project `generic_v6` / `custom` fixtures. They establish
the specified generic recovery boundaries, not general shared-v2 historical
compatibility or the authenticity of any campaign's retained data.

Each target capture is copied byte-for-byte into a newly created run root
and consumed with #5212 imports and #5212 as the working directory. The old
root is moved aside intact. The destination uses the same absolute pathname
because those names are part of the original input/snapshot identity; no
embedded path, hash, generation ID, date, record or JSON formatting is rewritten.
The driver verifies the complete relative-path/size/SHA-256 manifest before
execution. Live executions and pytest basetemps stay outside the worktree;
the retained evidence copies are under this note's evidence directory.

Two original tests start with hand-written old-format progress/index bytes
rather than runner output (C5 and C6). They are retained as exact historical
test controls, **not misrepresented as production-emitted files**. Supplemental
controls first run the real f8 pipeline through a delivered full phase and
an audit interruption. C5 drops input evidence from that emitted progress
and omits its f8 ledger; C6 retains the emitting run separately and transfers
a truncated prefix of its emitted index. These supplements test both the
earlier diagnostic and the successful explicit-restart obligation. Original
undamaged and damaged bytes are both retained. These are controlled faults
in synthetic offline runs, not claims about actual historical campaign data.

The C3 end-to-end canary ran first. It passed its original f8 test, verified
a nonempty capture, and completed
the exact-byte #5212 replay with four mocked dispatches. Only then did the
serial launcher run the remaining cases. This proves code selection,
persistence and transplantation for the canary; it establishes no provider,
load, concurrency or real-spend result.

The session was interrupted and the subsequent reboot removed its original
temporary evidence. All eight controls and both supplements were regenerated
from the same two commits after the reboot. Replacement captures and streamed
reports are written into this worktree, while live run directories and pytest
basetemps remain in `$TMPDIR`. No pre-reboot raw artifact or unfinished test
collection is counted as retained validation evidence.

The retention helper independently checks each recorded imported source hash
against its claimed Git blob, verifies all 14 before/after manifests, and checks
archival/predecessor side effects. Successful returns alone are insufficient:
the old index/reasoning bytes must survive where applicable, the selected
predecessor must be recorded, and active reasoning must use the new generation.

The committed [result ledger](d41_legacy_recovery_evidence_20261029/results.json)
records all 14 paired replay points, source checks, test outcomes and helper
hashes. The [exact-byte evidence archive](d41_legacy_recovery_evidence_20261029/authentic_controls.tar.gz)
contains 1,269 regular files (4,114,924 compressed bytes), including captures,
replays, full validation reports, superseded harness attempts and blocked-write
controller traces. Every decompressed member was compared with its source.
Archive SHA-256:
`314ad171427e2a42244fe963874c1082137ea99228bc40d6f12809058a36de6a`.

### Exact cases and policy classification

The three classes are **A: malformed historical archival**, **B: missing-ledger
fresh recovery**, and **C: no-spend completed replay**. “Malformed archival”
includes structurally readable but unaccounted/unrelated historical material;
it does not mean that C1's JSON fails to parse.

| Case | Exact original node ID | Class |
|---|---|---|
| C1 | `tests/test_fresh_orphan_partial_generation.py::test_fresh_restart_does_not_accept_unrelated_archived_attempts` | A |
| C2 | `tests/test_fresh_orphan_partial_generation.py::test_fresh_restart_records_an_orphaned_partial_predecessor[malformed]` | A |
| C3 | `tests/test_fresh_orphan_partial_generation.py::test_fresh_restart_records_an_orphaned_partial_predecessor[missing]` | B |
| C4 | `tests/test_fresh_orphan_partial_generation.py::test_predecessor_binding_survives_interrupted_index_activation` | B; includes the prepared-ledger state after the interruption |
| C5 | `tests/test_generation_manifest_identity.py::test_legacy_progress_without_input_evidence_requires_explicit_restart` | B |
| C6 | `tests/test_generation_recovery_review.py::test_explicit_restart_preserves_an_unreadable_snapshot_index` | A |
| C7 | `tests/test_midnight_resume.py::test_automatic_date_is_restored_before_cached_instruction_or_portable_checks[True-False]` | C |
| C8 | `tests/test_reasoning_generation_restart.py::test_fresh_generation_archives_malformed_predecessor_reasoning[True]` | A |

### Results and causes

All eight original tests pass at f8. Counts below are **mocked physical
dispatches**, never provider calls. Line numbers are at `d9b69d84d` unless
explicitly marked f8. The machine-readable ledger retains the exact exceptions,
trace frames, source-module hashes and before/after manifests.

| Case | Pre-D41 behavior | #5212 on the exact f8 bytes | Cause / boundary |
|---|---|---|---|
| C1 | Refuses the unrelated unaccounted attempt; 0 calls | Same intended refusal; 0 calls | `snapshot_store.require_accounted:400` (f8), `:402` (base), reached from `api_runner._require_surviving_accounting:6720`. Unrelated archive is preserved and not admitted. |
| C2 | Archives opaque malformed ledger and restarts; 4 calls | Refuses `invalid usage ledger`; 0 calls, unchanged captured tree | f8 `usage_ledger.prepare_usage:475`, tolerant archival at `:498`; base `latch_journal._validated:477–479` strictly decodes before `prepare_usage` can archive. **Authentic archival incompatibility.** |
| C3 | Restarts, records predecessor and preserves snapshots/index; 4 calls | Restarts; 4 calls | Base `latch_journal.check:635–636` passes `allow_new=True` for explicit fresh; `_validated:468–474` permits a missing ledger with no journal. `usage_ledger.prepare_usage:574–609` establishes the fresh boundary. The earlier current-journal test failure is not reproduced by authentic f8 bytes. |
| C4 | Injected index publication failure; 0 calls. Subsequent resume completes; 4 calls | The same injected failure is reached; 0 calls. Separately transplanted **f8 post-interruption** state then refuses unacknowledged legacy adoption; 0 calls | Both first attempts reach `snapshot_store.finish_activation:126`. The post-interruption f8 ledger exists but has no latch journal: base `_validated:484` → `_legacy:352` → `_override:285`. No acknowledgement was fabricated. **Authentic recovery incompatibility.** |
| C5 | Ordinary resume refuses `no recorded generation input identity`; 0 calls | Ordinary resume refuses earlier with the missing-ledger/history diagnostic; 0 calls | f8 `api_runner:6996`; base `api_runner:7094` → `latch_journal._validated:471–473`. Emitted-progress supplement confirms explicit restart completes in both versions with 4 calls. **Earlier diagnostic remains incompatible; fresh restart itself works.** |
| C6 | Ordinary resume refuses `cannot recover generation snapshots`; 0 calls. Explicit restart archives exact unreadable bytes and completes; 4 calls | Earlier missing-ledger/history refusal on ordinary resume; 0 calls. Explicit restart still archives and completes; 4 calls | f8/base `snapshot_store._load:56`, superseded on ordinary resume by base `_validated:471–473`. Fresh activation uses `usage_ledger:582` and `snapshot_store.finish_activation:113–129`. **Earlier diagnostic differs; archival success is retained.** |
| C7 | Restores `2026-09-12`, returns `already_complete`; 0 calls and unchanged tree | Restores the same date, then refuses missing accounting/history; 0 calls and unchanged tree | f8 date restoration `api_runner:6673`, completed return `:7136`; base restoration `:6924` precedes `:7094`, then `_validated:471–473` blocks before completed replay. **Authentic no-spend replay incompatibility.** |
| C8 | Archives malformed predecessor reasoning verbatim, records predecessor, starts new usage; 4 calls | Same successful restart; 4 calls | Base explicit-fresh admission `_validated:468–474`, then `usage_ledger.prepare_usage:600–608` and `_finish_reasoning_archive:612–642` preserve opaque predecessor reasoning. Active reasoning corruption remains outside this exception. |

These results do **not** turn eight current tests green. The original tests
often create a current journal and then remove their current usage ledger;
`latch_journal._validated:469–470` must still refuse that state. C1 is a required
negative, not a request to accept unrelated archives. C5/C6 have earlier-message
obligations separate from their explicit-restart obligations.

Successful compatibility is also not proof of the proposed stronger preservation
policy: C3's resulting run does not retain the original progress bytes, while
the evidence capture does. Its newly written provenance says `verified: true`,
`assisted: false`, `evidence_only: false` for the new active journal. That is not
proof of complete historical accounting. The proposed bundle and separate
accounting-completeness disclosure are therefore required even on already
successful legacy paths; merely bypassing the three refusals is insufficient.

## Common contract required of either option

1. **Guarded history wins.** Before any legacy route, inspect the exact selected
   run under its lock. Any journal, any ledger/provenance reference to one, or
   any external launch record indicating guarded history selects the existing
   D41/D57 path. Missing, malformed, edited, truncated or re-chained current
   journals refuse exactly as now. `resume=False`, a new label, an archive
   switch or an import manifest cannot turn this into a legacy exception.
   Do not add a general `allow_legacy=True` to `_validated`.
2. **Absence is not proof of age.** A directory with both journal and ledger
   removed is not distinguishable from old history using absence alone. A
   spending recovery requires a separately reviewed source manifest and
   explicit owner authorization binding the captured bytes and provenance
   basis. Compare retained launch inventory, not an operator's claimed date
   or a newly computed head. If earlier guarded history cannot be excluded,
   permit only evidence inspection; never continue that run. This is a
   stated limit of local hash chains, not a claim of cryptographic provenance.
3. **Retain every byte found.** Read-only inventory includes ignored/hidden
   files, opaque/malformed files, inactive indexes, records, progress, reasoning,
   abandoned attempts, snapshots and partial transaction files. Record relative
   names, lengths and SHA-256, plus missing expected files and unreadable items.
   Copy/flush/verify the immutable evidence bundle before any activation. No
   overwrite, rename that loses the source, JSON repair, silent discard or
   garbage collection. Refuse unsafe links/path escape or unreadable bytes;
   do not follow a link outside the authorized source. Retaining bytes found
   cannot recreate a ledger already lost before inventory.
4. **Bind the interpretation as well as the bytes.** A versioned recovery
   manifest contains the source bundle root digest, source identity and code
   provenance with its confidence, selected predecessor and selection evidence,
   excluded/unrelated artifacts, observed accounting, unknowns, operation
   (`fresh_import` or `completed_replay`), destination identity, authorization,
   and transaction state. A new run's immutable journal observation binds this
   manifest; its provenance carries the same digest and assisted/evidence-only
   status. A read-only replay emits a separate result envelope referring to
   the unchanged original record and manifest; it does not restamp the record.
5. **Unknown stays unknown.** Missing or malformed historical accounting is
   `unknown`, with any recovered rows explicitly described as observed rows
   or a lower bound. Never supply `[]`, `0`, or a fresh account's zero as the
   historical total. New-generation usage is a separate measured account.
   Do not refund old quotas, clear a consumed allowance, or reuse historical
   spend as budget authorization. Starting again needs its own approved budget
   and, for registered execution, a fresh registration.
6. **D56 and R3 remain operative.** A historical terminal/control discrepancy
   cannot be overridden into continuation; the predecessor stays ended. A
   retry is a new registration, not the interrupted generation with a cleared
   flag. Recovery of an otherwise permissible interrupted write is still
   assisted/evidence-only. No legacy route clears terminal latches, recovers a
   consumed allowance or upgrades assisted evidence to a campaign result.
7. **No hidden spend in replay.** The replay operation has no client, count,
   transport, regeneration, repair, receipt-recovery or usage-initialization
   capability. Incompleteness/refusal is a terminal result of that operation,
   never a fall-through into generation. Evidence-only replay must be excluded
   from campaign eligibility even when output quality checks succeed.

### Class-specific policy

| Class | Accept/archive | Refuse | Assistance and accounting |
|---|---|---|---|
| A | Accept opaque bytes into the immutable evidence bundle. A fresh approved generation may reference only a specifically identified predecessor. Keep unreadable indexes/ledgers and malformed reasoning without parsing them into active state. | Unrelated archived attempts cannot become known predecessor IDs or accounted usage (C1). Missing ownership proof, inconsistent identities and any current-journal damage refuse. Malformed active reasoning remains a refusal. | Recovery/import is assisted and evidence-only. Historical totals stay unknown where incomplete. A separate fresh account measures only new calls. |
| B | Preserve the orphan's full evidence and explicitly select its predecessor. Regenerate all owed output under a fresh identity; do not skip phases merely because old progress says they finished. C4 preserves both the old index and the prepared ledger/activation intent. | Ordinary resume with no input evidence (C5) names the missing identity and explicit-restart obligation. Never recover C4 by manufacturing a historical D57 head. A mismatched activation intent, terminal state or control discrepancy ends that run. | Explicit recovery is assisted/evidence-only. Treat a pre-D41 prepared zero-row ledger as insufficient proof of the earlier generation's zero spend. In the new transaction, repeat only verified archival steps, not provider work. |
| C | Accept an attested completed portable record for read-only verification. Restore only the implicit original date in memory before instruction comparison. Verify identity, input/instruction/schema bindings, output and intermediate hashes, ownership, observed usage and all applicable completion checks. | Changed explicit date, input/instruction, missing phase, stale/invalid record, unaccounted surviving attempt, active corruption, terminal discrepancy or a guarded-history conflict. Never repair/rebuild a record as a side effect. | Report `already_complete` only with `legacy_unverifiable`, `evidence_only`, and an explicit accounting-completeness field in the separate result. Verification itself makes zero new calls; that is **not** a historical zero-spend claim. If assistance was required, disclose it. |

For C1, quarantining unrelated bytes in a bundle is preservation, not admission.
The existing attempted restart must still refuse before dispatch. A subsequent
independent new registration can be considered by the owner; it must not list
the unrelated generation as its legitimate predecessor or imply accounted spend.

## Two implementation options

### Option 1: explicit transactional recovery in the original generic directory

Add a reviewed-plan argument to the generic explicit-restart route. With no
guarded-history evidence, snapshot the complete source into a sibling immutable
bundle, validate the authorization and selected predecessor, then publish a
durable activation intent. Only after byte verification may the active namespace
be replaced with a fresh generation. Every overwritten original has an exact
retained copy. Recovery of the transaction is idempotent and hash-bound; a
nonmatching intent refuses. Add the separate pure completed-replay route for C7.

This most closely preserves the older generic same-directory interface. It
requires transaction logic across ledger, reasoning, progress, index, record and
outputs, with several crash boundaries. The unreadable-ledger branch cannot be
implemented by simply catching `_validated`'s exception. It needs a narrow
pre-journal admission protocol that proves the common contract first. Shared-v2
same-directory reuse remains prohibited; f8 already refused that operation.

Minimal proposed production surface:

- New `src/data_sheets_schema/legacy_recovery.py`: inventory, manifest,
  authorization validation, archival transaction, and pure replay verifier.
- `api_runner.py`: explicit legacy dispatch before mutable recovery, retaining
  existing guarded-history dispatch first; result/provenance integration and
  clear diagnostics; extract reusable **pure** completed checks without changing
  their ordinary guarded invocation.
- `usage_ledger.py`: persist the new generation's recovery-manifest binding and
  distinguish historical unknowns from active rows; preserve the original ledger
  and reasoning through the transaction.
- `snapshot_store.py`: activation through the manifest-bound transaction,
  retaining opaque index bytes and exact predecessor ownership.
- `latch_journal.py`: immutable import-manifest observation and corresponding
  assisted/evidence-only metadata on a **new** journal. No relaxed `_events`,
  `_validated`, D56 or D57 condition for an existing journal.
- `cli/api.py`: plan/execute/replay choices and expected-manifest digest.

**Protected `shared_generation.py`: a code-identity list change is proposed
only in [this unapplied diff](d41_legacy_recovery_shared_generation_proposal.diff).**
Add the new authority-bearing module to `ROUTING_CODE` (and therefore
`REQUEST_CODE`); otherwise its bytes would not be covered by the captured
controller identity. No new shared-v2 same-directory exception or request text
is proposed. Changed controller files naturally change code identity in newly
built registrations; old registrations must not be repinned in place. The diff
must only be applied with the reviewed implementation, when the module exists.

### Option 2 (recommended): immutable source, explicit import into a fresh directory

Expose a recovery-plan operation, then an authorized fresh-import operation
that requires a fresh destination and label. The source is never made active.
Copy and verify the evidence bundle, bind its manifest into the destination's
new ledger/journal, and regenerate under the new registration and budget.
Once this policy is adopted, an ordinary same-directory `resume=False` on
journal-less historical evidence must stop before initialization and direct
the caller to this import operation. Leaving the currently successful implicit
reset paths enabled would still lose original progress/record bytes and would
not satisfy the preservation invariant. Truly empty fresh starts and existing
journal-bearing paths retain their current guards.
Malformed source bytes can be preserved without requiring the normal runner's
strict ledger reader to parse them. C4's interrupted f8 activation is evidence
about the predecessor, not a fabricated journal prefix for the new run.

Provide the same separate pure completed-replay operation for C7. It reads the
source through an explicit manifest-bound path resolver, checks the historical
logical paths against the manifest, and reads the copied blobs without rewriting
their embedded paths. This also makes frozen authentic fixtures portable in CI.
Refuse if the mapping is ambiguous or escapes the bundle.
Place any inspection lease outside the immutable source tree; even new empty
lock files are excluded from the no-write replay contract.

Minimal proposed production surface:

- New `legacy_recovery.py`: immutable inventory/bundle, strict plan and import
  authorization, path binding, and pure completed replay.
- `cli/api.py`: explicit plan/import/replay operations; require expected manifest
  digest and a fresh destination identity for import.
- `api_runner.py`: route the explicit import to a new-generation execution only
  after guarded-source checks; factor the pure completed checks; write the
  recovery binding into the open `model` provenance block and returned checks.
- `usage_ledger.py`: initialize the fresh account with the recovery-manifest
  binding; keep historical accounting completeness separate from active rows.
- `latch_journal.py`: latch that binding at generation start and report its
  inherited assistance/evidence-only status. Existing-journal validation and
  launch-head comparison remain unchanged.

`snapshot_store.py` needs **no archival-policy change** in this option: the new
destination begins empty, and old snapshots remain immutable evidence. The
generation-record schema already uses an open `AnyBlock` for `model`; the
recovery manifest needs a strict validator in the new module, not a dataset
schema or prompt change. **Protected `shared_generation.py`: the same unapplied
one-line code-identity proposal as Option 1.** Its actual file stays untouched.

This has a smaller dangerous interaction surface and preserves source evidence
even if destination activation crashes. Costs: an explicit new-directory
workflow, an additional bundle, and no promise that the old same-directory
invocation becomes successful. That interface change needs the owner's design
approval. Preserve the old tests as historical controls; add explicit-operation
acceptance tests instead of silently changing recovery-success assertions into
refusal expectations. Existing current-journal deletion tests stay negative.

The owner must choose the interface and policy before implementation. This
session recommends Option 2 but does not claim that this note is the required
independent design review or that #5212's blocker has been discharged.

## Permanent test plan and acceptance gates

Promote the retained f8 captures, original test provenance, perturbation recipe
and complete hash manifests into `tests/fixtures/pre_d41/`, consumed by a new
`tests/test_legacy_recovery.py`. Tests must consume these
exact bytes; do not reconstruct “legacy” by removing a current journal. Use the
manifest path resolver for frozen absolute paths rather than reserializing
records or weakening identity comparisons. Keep the emitting script and source
commit identity; routine CI need not have a historical Git ref or a provider.

1. Keep one positive and one precise negative per class and all eight exact
   obligations. C4 has separate pre-write and post-interruption captures; C5
   and C6 test both the diagnostic and explicit operation. C1 asserts refusal,
   no dispatch/count, unchanged unrelated bytes and no false predecessor ID.
2. Assert every source byte is unchanged and every bundle entry verifies after
   success, refusal, crash and retry. Canary one crash point before sweeping
   capture/flush/manifest/activation failures serially. Test torn/duplicate-key
   manifests, unsafe links/path escape, partial copies and mismatched digests.
3. Assert historical unknowns stay unknown throughout ledger, provenance,
   returned checks and reports; observed rows remain attributable. No old
   spending/allowance can become new budget. An imported result remains
   ineligible after another resume, export or no-spend replay.
4. For C7, assert zero transport **and token-count** calls, zero recovery/repair
   hooks, byte-identical source/output trees, implicit date restoration, and
   preserved explicit-date/input/instruction negatives. Reconcile all surviving
   accounting evidence with recorded completion; disclose missing historical
   totals as unknown and reject a completed record hiding a later attempt.
5. Repeat current-journal deletion/malformed/truncation/rechaining controls with
   every legacy flag and import entry point. External expected head, terminal
   state and control latches must still refuse before writes or spend. Test
   journal markers without the journal, and missing journal+ledger against a
   retained external launch record. No automatic legacy classification.
6. Keep D55 interrupted-write assistance, D56 terminal and control refusals,
   D57 monitor anchors, round-3/4 refusal-output redaction and request parity.
   Add a normal fresh empty-directory launch proving no legacy branch is taken.
7. Before publication: independent read-only design/implementation review,
   permanent authentic-artifact tests, full collection, required complete
   #5212-plus-simulated-batch2 gate and CI. The focused run below is evidence
   for this unchanged base, not a substitute for that still-required full gate.

## A21 boundary

An A21 launch with a genuinely fresh label **and empty fresh run directory**
has no predecessor, archival index, progress or completed record. It cannot
enter any of these eight legacy paths, and neither proposed option should be
selected implicitly. Copying older artifacts into it would violate that premise.

After A21 has started, its own interrupted write or damaged journal can reach
the existing D41/D55/D57 recovery/refusal paths. R3 still makes an acknowledged
permissible interrupted write assisted/evidence-only; a terminal/control
discrepancy ends the run under D56. Such an event is not legacy compatibility
and cannot use the proposed import route to continue A21. The owner kept legacy
recovery blocking #5212 despite fresh-launch non-reachability; this finding
does not waive the blocker or authorize the A21 re-canary.

## Validation and review status

Reproduction uses the committed scripts, local Git objects and the existing
dependency environment. Keep the scripts on this review branch, create a fresh
`$TMPDIR` root, and add detached worktrees at f8 (`scratch/pre-d41`) and the
tested d9 base (`scratch/base`). Use a new evidence directory, never overwrite
the retained packet. `--mode plan` records the selected head and dependencies.
The launchers take the following positional arguments:

```sh
bash scripts/adhoc/run_d41_legacy_serial_20261029.sh "$python" "$base" "$scratch" "$evidence" canary
# Inspect C3's capture, generation.json and exact-transplant result before rest.
bash scripts/adhoc/run_d41_legacy_serial_20261029.sh "$python" "$base" "$scratch" "$evidence" rest
bash scripts/adhoc/run_d41_validation_serial_20261029.sh "$python" "$base" "$scratch" "$evidence" canary
# Inspect the canary's nonempty JUnit report and passing result before rest.
bash scripts/adhoc/run_d41_validation_serial_20261029.sh "$python" "$base" "$scratch" "$evidence" observer-canary
# Verify that the observer also survives a test prohibiting filesystem lookups.
bash scripts/adhoc/run_d41_validation_serial_20261029.sh "$python" "$base" "$scratch" "$evidence" rest
# Environment controls use external reports so checkout snapshots remain stable.
bash scripts/adhoc/run_d41_environment_serial_20261029.sh "$python" "$base" "$control_scratch" "$control_evidence" poetry canary
# Verify the canary's complete reports and generated-schema assertion first.
bash scripts/adhoc/run_d41_environment_serial_20261029.sh "$python" "$base" "$control_scratch" "$control_evidence" poetry control
bash scripts/adhoc/run_d41_environment_serial_20261029.sh "$python" "$base" "$control_scratch" "$control_evidence" checkout canary
# Verify the checkout-preservation canary, including its teardown, first.
bash scripts/adhoc/run_d41_environment_serial_20261029.sh "$python" "$base" "$control_scratch" "$control_evidence" checkout control
"$python" -S -P -B scripts/adhoc/retain_d41_legacy_evidence_20261029.py "$evidence" "$packet" \
  --environment-evidence "$control_evidence" --runtime-ci-root "$scratch/ci/tmp"
```

The original controls require the f8 head exactly; the replay driver requires
the d9 head exactly. A new review commit must therefore not be used as its own
replay base. Populate the pinned FAIRSCAPE submodule from already-local Git
objects for broad collection; no download or dependency installation is part of
this recipe. This packet used submodule object
`8c80311d7d8b0fadac07dca9567d632103691f48`. The launchers enforce offline
networking in descendants with macOS `sandbox-exec`; the validation profile also
restricts writes to runtime scratch and retained raw evidence. The driver strips
provider credentials and proxy variables, disables site/`.pth` execution, and
places bytecode, matplotlib state and pytest basetemps outside the checkout.

Completed on the unchanged d9 base on 2026-10-30, after the reboot:

- The validation-launcher canary passed (one complete CI-partition test).
- The corrected observer's filesystem-prohibition canary passed (one complete
  case, nonempty JUnit and complete setup/call/teardown reporting).
- Literal whole-tree `pytest --collect-only -q`: **24,044 collected, 17
  collection errors**, exit 2. Eleven are FAIRSCAPE submodule test imports,
  three are FAIRSCAPE integration imports in the parent collection, two are
  obsolete renderer tests requiring unavailable `weasyprint`, and one is an
  obsolete downloader attempting networking during import. The offline audit
  blocked that attempt at DNS resolution. No outgoing request was allowed.
  These errors are retained, not hidden with an ignore list or dependency edit.
- Focused unchanged-base suites: **161 passed**, zero collection errors,
  complete selected/completed occurrence accounting, exit 0 in 1,592.63 s.
  Scope: latch journal, public D41 guard, D55 fixes and D55–D57 controls,
  round-3 fixes, round-4 fixes, and request parity.
- The CI-equivalent `tests/` process **executed all 20,557 collected
  occurrences**, with zero collection errors and exact multiset coverage of
  ordinary plus dedicated lanes for both four- and six-shard partitions.
  Pytest reported **20,488 passed, 19 failed, 45 skipped, 8 errors**, exit 1,
  in 28,700.57 s (7:58:20). Three cases passed their call and failed teardown,
  so those phase totals must not be summed as distinct case counts.
  **All four dedicated API cases passed setup, call and teardown without
  skip/xfail.** The process finished normally after writing its final result.
- The 19 call failures comprise the eight disposition cases, six Poetry CLI
  failures, two process-lock failures, two blocked `data/` fixture writes,
  and one blocked checkout-local temporary directory. The eight errors are
  five Poetry setup failures and three reporting-induced teardown errors.
- Targeted Poetry environment control: **12 passed, 1 skipped** across all
  13 selected cases, no failures/errors, complete occurrence accounting,
  exit 0 in 62.10 s. This covers the five schema cases, review-pack refresh,
  four DataCite positive/negative controls, and three FileCollection cases.
  The skip is the missing `D4D_-_AI-READI_FAIRHub_v3_data.yaml` example.
  The canary separately passed its nonempty generated-schema assertion.
- Targeted checkout-reporting control: **37 passed**, including all three
  previously failing teardowns, no collection errors, complete occurrence
  accounting, exit 0 in 58.12 s. Its one-case canary also passed. All live
  logs/reports were outside the checkout; frozen copies are retained verbatim.

The follow-ups explain particular environment/harness failures; they do not
replace or relabel the original red full-suite result. No assertion, production
source, installed dependency or protected write rule was changed.

**Local review item LR2 (harness corrected, full rerun completed):** the first CI
attempt completed 1,322 cases before the observer's own `Path.open` conflicted
with `test_worker_recovery_ranges_do_not_access_filesystem_and_keep_exact_locator`,
which deliberately forbids filesystem access during its call. The observer
failed before teardown and pytest could not write a final result. Retained
`ci-observer-error/` and `ci-observer-error.log` are superseded evidence, not
coverage credit for the final gate. The revised observer opens its report stream
before pytest and uses that stream during reports. The exact affected test
passes with the revised observer; the complete CI selection was rerun in a
fresh basetemp and completed as recorded above. No production code or test
assertion changed. The adjacent
`d41_legacy_controls_20261029_v1.py` preserves the exact driver used for the
authentic controls, whole-tree collection and successful 161-case gate; the
retention manifest resolves each executed helper hash to its retained version.

Additional full-run findings retained for lead triage (no remote issues are
filed in this offline session):

- **LR3, environment:** all five `TestD4DFullSchema` cases hit a setup error
  because `poetry run gen-linkml` tries to create an environment under
  `~/Library/Caches/pypoetry/virtualenvs`, outside the authorized write roots.
  Six other positive checks failed through Poetry (`test_review_pack_schema_refresh`
  and the DataCite/FileCollection validator classes). Selecting the already
  installed environment with `VIRTUAL_ENV`, its `bin` on `PATH`,
  `POETRY_VIRTUALENVS_CREATE=false`, and a scratch Poetry cache yields the
  12-pass/1-skip control above. The DataCite negative cases are included so
  a broken validator cannot pass merely by rejecting every input.
- **LR4, no-touch fixture conflict:** the `success` and `signal` variants of
  `test_real_legacy_launcher_keeps_guards_and_receipts` try to create
  `data/d4d_concatenated/claudecode_direct/...` from the current working
  directory. Their controller traces end in `PermissionError: Operation not
  permitted` at the fixture's `write_outputs` callback. The sandbox prevented
  these writes. No protected run directory was changed, no test assertion was
  weakened, and the write policy must not be relaxed to make them pass.
- **LR5, reporting interference:** the three
  `test_preflight_resource_authority.py` teardown errors came from
  `checkout_unchanged` detecting growth of the deliberately retained
  `raw/ci.log` and `raw/ci/reports.jsonl`. Their call phases passed. Moving
  all live reports outside the worktree makes the exact canary and all 37
  module cases pass, without changing the fixture or its assertions.
- **LR6, unresolved native-process result:**
  `test_run_lock.py::TestAgainstARealProcess::test_it_becomes_stale_once_stopped`
  and `::test_stop_actually_stops_it` still reported a terminated child as
  alive (`test_run_lock.py:152` and `:143`). The implementation observes
  native `ps` state in `run_lock.py:65`. Process inspection can be restricted
  in this macOS sandbox, but this session does not establish the cause or
  relabel these failures as passes. Retain them for lead triage.
- **LR7, stricter harness write restriction:**
  `test_rubric20_hybrid_parity.py::TestTheDenominator::test_the_scorer_itself_refuses_a_drifted_table`
  tries `TemporaryDirectory(dir=REPO)` at line 111. The validation profile
  allows writes only to scratch and raw reports, so it refuses that temporary
  checkout write before the scorer assertion. This is a limitation of the
  chosen read-only checkout harness, not evidence of a scorer defect. It is
  distinct from LR4's forbidden `data/` writes. The test was not edited.
- **LR8, follow-up launcher corrected:** the first environment canary passed,
  but the control launch stopped before pytest when this Bash rejected an
  empty array under `set -u`. The corrected launcher builds a nonempty
  command array; it was re-canaried in fresh directories before either full
  control. The exact `_v1.sh`, original canary reports and launch error are
  retained. Only the fresh, completed controls receive final coverage credit.

This is macOS/Python 3.13.12 with pytest 7.4.4, linkml 1.9.3,
linkml-runtime 1.9.4, anthropic 0.72.0 and PyYAML 6.0.2; source and lock hashes
are retained. It is a CI **test-selection** equivalence check, not a claim to
have run Linux/Python 3.12 Actions, the separate notes-based offline jobs,
schema builds, or the still-outstanding #5212-plus-simulated-batch2 gate.

Read-only self-review checked the authentic-source selection, byte manifests,
fault recipes, guard citations, preservation/accounting policy, and protected
file proposal. The final pass also checked full-suite occurrence accounting,
dedicated-case phase gates, follow-up controls and the archive digest; it
corrected LR6's native-process line citation from 64 to 65.
**Local review item LR1 (corrected):** the evidence-location
sentence originally conflated live temporary executions with retained copies;
it now distinguishes them. No remote issue was filed because the task forbids
GitHub operations. The self-review is not the independent owner/lead design
review required before implementation or publication.

No protected source, decision record,
`STATUS.md`, repository run directory or `data/ATTIC/` has been edited. No
network, provider call, push, GitHub operation or PR publication is authorized
in this session. The local commit is an owner-review packet only.

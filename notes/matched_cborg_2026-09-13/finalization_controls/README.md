# Native Phase 4 continuation

This experimental controller corrects a new full D4D from a separately accepted
native audit, derives a new core, and checks a new reconciliation report. It
preserves the original generation, stopped attempts, accepted audit and their
accounting. It makes no claim that an earlier stopped generation completed.

Preparation and tests make no provider calls. A real launch requires an exact
independently accepted audit, settled accounting and completed shutdown, a new
registration, independent launch review and passing CI. No accepted scientific
pair or real Phase 4 execution is supplied by this change.

## Preparation and execution

From the committed execution checkout, with its Python environment and
`PYTHONPATH=src:notes/matched_cborg_2026-09-13`:

```bash
python -m finalization_controls.prepare \
  --accepted-audit-registration /absolute/accepted-audit/registration.json \
  --acceptance /absolute/independent-acceptance.json \
  --destination /absolute/new-phase4-condition \
  --job-id dataset_finalize --attempt-cap 20

python -m finalization_controls.native \
  --registration /absolute/new-phase4-condition/registration.json \
  --review /absolute/independent-launch-review.json
```

The cap is explicit registration data, subject to launch review and existing
user authorization. Preparation does not authorize spending. It snapshots the
current original accounting state and creates an immutable non-ledger seal,
without modifying the live state or opening a successor ledger. The complete
parent request history carries under the unchanged original allocation and
default cap when execution acquires the shared owner.

The acceptance document binds `verdict: accept`, the accepted audit registration,
result and settled ledger SHA256 values, and its exact artifact map. The launch
review binds `verdict: approve`, the new registration hash, repository commit,
`ci_conclusion: success` and exactly the registered job in `allowed_jobs`.
These binding checks do not establish reviewer independence or scientific merit.

The controller holds the existing canonical audit lock throughout handoff,
counting, reservations, model execution and bounded shutdown. Each reservation
uses the shared owner's roster and ancestry gate. Earlier audit controllers see
the permanent compatibility seal. A consumed attempt never reopens; pending
charges, unknown shutdown state and stale predecessor evidence prevent transfer.

## Scientific and procedural boundaries

The registered native instruction replays the parent's renderer-14 scientific
instrument. It supplies the source bundle, schemas, original records and accepted
audit inline. The model writes only the new full record and report. Trusted exact
helpers derive the core, check both schemas and terms, check the pair and
identifiers, and construct the final source inventory and report context.
Duplicate keys and projection identity are checked. Helper outputs and original
inputs cannot be rewritten by the model, including through otherwise valid
native Write tool callbacks: the live observer checks the call before callback
admission.

A checked ordinary record failure before reporting permits a full-record
correction and fresh derivation. The closing checker runs actual evidence and
source-review checks first. A failed or uncheckable source/evidence review is
terminal. Only a clean source/evidence review permits one ordinary closing
repair, including a full correction when required, another derivation and fresh
inventory, and a rewritten complete report. A failed second closing check is
terminal. Typed native result evidence and current file hashes are required;
merely finding a successful receipt on disk does not authorize another request.

The original coverage receipt remains Phase 1 evidence. It is never retargeted,
rewritten or presented as a new source-reading receipt. Per-value final source
review supplies the explicit evidence for retained and corrected values.
Mechanical evidence checks do not prove entailment, correct status classification
or complete identification of unsupported claims; those need independent review.

## Bounded report-context delivery

The helper does not print a full report request to Bash stdout. It first proves
that the omitted shared prefix equals the reconciliation context supplied at
launch, then retains every report-specific block: the final pair, actual audit
counts, core inventory, final-full inventory and report contract.

It stores that exact text as numbered JSONL fragments below the new output's
`report_contexts` directory. Each physical line is at most 1,000 UTF-8 bytes;
there is no trailing blank line. A compact receipt binds the file and recovered
text hashes, byte/line counts and predetermined ranges of at most 12 lines.
Before writing the report, the model must Read all ranges in order. The
controller checks the actual typed file result and the complete numbered tool
result content against those exact lines. Truncated, substituted, persisted-only
or missing deliveries do not count. A new derivation invalidates prior delivery
and report passes, including during the permitted repair.

This avoids duplicated source context and unobserved Bash truncation. It does
not establish that a real workload fits the model window: the exact accepted
audit and final records still determine request size. Register and inspect
actual token-count evidence before expanding a canary. Native compaction and
runtime transport behavior require review from their actual execution trace.

## Results and provenance

A successful controller result is `completed_pending_independent_review` with
scope `phase4_reconciliation`. It binds the final full/core/report, validation,
typed tool history, complete report-context delivery, initial inline-context
observation, settled requests and actual bounded-shutdown evidence.

`lineage.json` is a separate composite continuation record. It identifies the
original generation, independently accepted audit, new final artifacts and
observed Phase 4 steps. It explicitly records that Phases 1–3 were not performed
here, that native temperature remains unobserved and that scientific acceptance
has not been established. It is not passed off as the existing single-run
`d4d provenance record` format. Independent acceptance must bind this lineage
alongside the final pair and report. Evaluation support for this composite
ancestry remains separate (#2115).

## Offline verification and limits

```bash
PYTHONPATH=src python -m pytest -q \
  notes/matched_cborg_2026-09-13/finalization_controls \
  notes/matched_cborg_2026-09-13/audit_controls \
  notes/matched_cborg_2026-09-13/test_continuation_sequence.py
```

Tests exercise real evidence/source/schema/term/pair/grounding/report functions,
actual filesystem accounting and locks, and scripted native children with local
mocked HTTP responses. Some focused cases replace only expensive subprocess
validators or full registration ancestry; those boundaries are stated in the
tests. They do not claim performance or successful completion by the real model.
No existing pinned worktree, real budget ledger or source artifact is changed.

A fresh Phase 4 registration can independently select `--context-recovery`. It
frames the unchanged current instruction, frozen inputs and accepted audit into
pinned JSONL references. Its persistent system prompt retains the current artifact
paths, exact helper commands and recovery index location. The index distinguishes
`instruction` (current task) from `parent_instruction` (historical reference).
This option does not inherit an earlier condition's recovery paths or modify its
sources. Defaults and the scientific renderer remain unchanged.

The recovery index and documents use at most 1,000 UTF-8 bytes per physical line
and exact native Read ranges of at most 12 lines. Typed file metadata and complete
raw/numbered content must match each prescribed delivery. Arbitrary whole-frame
Reads are denied without disqualifying a run; incomplete prescribed delivery stops
it. These optional recovery reads do not replace the mandatory current derivation's
report-context reads described above and do not assert complete current-context
coverage. Native compaction, runtime limits and all scientific acceptance checks
remain in force. The runtime's auxiliary requests can have their own system prompts;
there is no new blanket provider-request system-prompt gate.

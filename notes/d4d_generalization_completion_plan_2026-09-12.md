# Generalization completion plan — 2026-09-12

Continue the agentic and API generation and evaluation plan in
`d4d_generation_evaluation_completion_plan_2026-09-12.md`. The requested order
below takes precedence over starting new measurements. Downloads remain deferred.

1. Finish PR #1367: explicit dataset context, bundle mappings and chunk
   manifests (#621, #623, #624, #637, #1299). Recover Claude's prepared round-3
   patch and both round-2 reports, address #1384–#1395 and the two CI
   regressions, and verify both CLI and direct-library callers.
2. Generalize evaluation identities and applicability (#1300, #627, #159).
3. Move vocabulary and study-specific prose behind profiles (#1302, #628).
4. Make packaging installable and usable outside a repository checkout (#1301).

At each stage, re-prioritize verified blockers, implement, test, run adversarial
review, file concrete findings and resolve them. Repeat up to five review
rounds as needed, with the requested Codex plugin review if findings persist;
independent Codex review may be used earlier. Merge only the reviewed head
after CI passes, and delete the completed branch. Preserve unrelated local work.

All generation arms remain in scope: API and agentic execution, full and core
records, and each registered input style. Evaluation coverage includes rubric10
and rubric20 presence checks, direct API quality evaluation, legacy rubric
agents, semantic rubric agents, deterministic schema/provenance checks,
grounding/receipt/report checks, record/source semantic review, and human
adjudication and repeated ratings. Preserve prior evaluations and identify any
new instrument or condition beside them. No new paid run is registered here.

## Recovery and prerequisite #1381

PR #1367's round-2 head `5ba2b64ae6779bcfadd3e2ea3ed9bbd9d11a9a61`
failed CI with 25 completion-report guard failures and two test regressions.
Both review reports and the unapplied patch were recovered from the previous
session's scratch directory. Claude's review found the same working-directory,
backfill and validator defects covered by the prepared patch; its source-dir
finding also overlaps #1390.

The report guard currently compares live production sources against measured
September 12 bytes. A prerequisite worktree preserves those 20 input files
under `reference_rescore_2026-09-12_cborg_runtime/registrations/measured_inputs_1381/`,
plus the two previous agent definitions needed to reproduce the registered
check-echo challenges. Each copy matches its original audited SHA256. The new
preservation record binds the unchanged original manifest and measurement
inventory; its own digest is pinned in the report resolver.

Completed report replay uses the preserved reference runner, schemas and
agent-pin implementation, including the original challenge preimages. Ordinary
digests still describe the bytes of the path read. Original records, attempts,
transcripts, receipts, evaluations, audit and manifest are not rewritten or
redirected. Altered original evidence or archive bytes must fail verification.
The public completed-condition commands continue to refuse new measurements.

This is a report-replay maintenance boundary, not a new scoring condition. The
56 ratings retain their original definition SHA256 values, inputs and outputs;
no record is rescored and no score changes. Tests must show identical report
contents (apart from the reporting timestamp) despite live input changes, while rejecting archive and
original-evidence tampering. No test skips or relaxed frozen hashes are used.

## Prerequisite review round 1 and fixes

PR #1396 preserves the measured inputs required to unblock #1367. The Codex
plugin reviewed public commit `955f57e97` and found three concrete defects:
completed audit rewrote the inventory it must preserve; its v9 check still
read live source inputs; and replay imported live pin/reporting dependencies.
The first two are tracked in #1397 and the dependency defects in #1398.

The audit now recomputes all session, original-Write and inventory facts and
compares them with the originals, writing no evidence files. Input checks use
the preserved paths. The runner and pin/reporting imports execute verified
source bytes in private modules; public modules and bytecode caches cannot
replace the measured helpers. The two reporting dependencies are copied from
Git revision `03cf94bf08f82e7399201c09140b32221e42c4dc`, which the registration
names, and are identical to the prior reporting code. They have a separately
identified section in the preservation record because the original audit did
not list them. The original 981-file inventory is unchanged.

Round-2 local validation: 92 targeted tests pass, including the complete
read-only audit after simulated evolution of every archived live input,
refused imports of all three live pin/report helper modules, original
check-echo reconstruction, and tampering/publication rollback tests. An actual
offline audit also reproduced all retained facts, including 56 accepted
ratings and six recorded v9 requests, without starting a measurement.
Independent review and CI must still pass on the final head before merge.

## Prerequisite review round 2 and fixes

The second Codex review verified all archive copies and found two remaining
paths: the audit utility eagerly imported its live default runner (#1400), and
the report trusted some retained audit statistics that were not hash-bound
(#1401). The utility now loads its default only if used, allowing completed
verification to inject the archived runner first. Both retained audit documents
are bound in the preservation record; the reporter verifies the exact byte
strings it parsed before publishing any derived file. Field-specific missing
qualification checks still run, and the original audit files remain untouched.

Round-3 validation: 112 tests pass, including audit → report → audit with a
fresh audit-module import each time, real session accounting, blocked network
connections, and refused imports of the live runner/pin/report helpers.
Changing the retained v9 request count, its cost, or the successful-Write audit
now stops publication. Default-runner compatibility and the original receipt
uniqueness/accounting tests also pass. Independent review and CI on this
committed round-3 head remain required before merge.

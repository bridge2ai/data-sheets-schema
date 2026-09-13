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

## Completed prerequisite and current generation review

PR #1396 merged as `140cd10b90231beda811ece02d59929112f70f1e` after
independent round-3 approval and full CI (3,760 passed, 4 skipped). Issues
#1381, #1397, #1398, #1400 and #1401 are closed; its branch and worktree
were deleted. The merged read-only audit reproduced all retained facts, and
the pre-existing unrelated main-checkout files remained unchanged.

PR #1367 round 4 passed full CI (3,815 passed, 4 skipped), but independent
review still found five defects. Together with an additional backfill
reproduction, they are tracked as #1408–#1413 and addressed in round 5; see
`reviews/pr_1367_round5_2026-09-12.md`. Review and exact-head CI remain
required before merging that patch. The next evaluation-applicability stage
also includes #1414, the incorrectly gated preprocessing item.

## Generation review round 6

The round-5 reviewer found two remaining recovery defects (#1415, #1416),
and a strict missing-bundle check was independently reproduced (#1417).
Round 6 binds every snapshot consumer to the requested run or its portable
attestation, retains logical phase/generation identities, reads verified
bytes once, and checks surviving attempt evidence before completed-run
shortcuts. Strict checks now fail on absent selected bundles. See
`reviews/pr_1367_round6_2026-09-12.md` for reproductions and boundary details.
Round-5 CI passed 3,831 tests and found two outdated recovery fixtures; those
are updated without relaxing the behavior being tested. The revised head
still requires green full CI and independent plugin approval. Evaluation
identities/applicability (#1300, #627, #159, #1414), vocabulary/study profiles
(#1302, #628), and installable packaging (#1301) remain queued in that order.

## Generation review round 7

Round 6 still found a stale same-generation index overriding completed
checks (#1420) and a strict registry check with zero targets (#1419). Local
corpus replay identified the historical pin needed for #1418. These are
addressed in round 7, with 158 tests passing, including the registered
historical report aggregate. Two adjacent interrupted-resume probes found
#1421 (progress lacks phase-history recovery evidence) and #1422 (a completed
return omits later journaled charges); both have fixes under expanded testing.
See `reviews/pr_1367_round7_2026-09-12.md`. Merge still requires exact-head CI
and independent Codex plugin approval. No measurement is launched by this
maintenance work; all API and agentic arms and evaluation styles remain in
the next-stage plan.

## Generation review round 8

Round-7 independent review found four remaining defects (#1423–#1426):
receipt read/hash identity, surviving accounting on completed returns, empty
strict bundle audits, and historical replay depending on the current source
manifest. All are addressed, with 77 targeted tests passing; see
`reviews/pr_1367_round8_2026-09-12.md`. Broader recovery tests, full CI and
independent approval of the revised head still precede merge. Stage order and
all API/agentic and evaluation-style requirements remain unchanged.

## Generation review round 9

Round 8 confirmed its preceding fixes and found partial-resume accounting,
predecessor reasoning isolation and historical backfill gaps (#1427–#1429).
These are addressed with 36 focused tests and two additional snapshot/failure
guards passing. See `reviews/pr_1367_round9_2026-09-12.md`. Broad tests, full
CI and independent review still precede merge. Evaluation preparation is
isolated on `generalize-evaluation-applicability`; its merge remains after
generation, followed by profiles and packaging. No paid measurement or source
download is launched by these maintenance stages.

## Generation review round 10

Independent round-9 review confirmed the preceding fixes and found #1430:
an explicit fresh restart failed when a partial predecessor retained its
snapshot index but had lost its usage journal. The successor now durably
records that specific predecessor before activating a new index. Unrelated
archives remain unaccounted and are refused. All 107 focused and broader
recovery tests pass; see `reviews/pr_1367_round10_2026-09-12.md`. Round-8 full
CI passed 3,884 tests with four skips. The final generation head still needs
green CI and independent approval. Evaluation applicability preparation
continues in its separate worktree without new scoring; profiles and
installable packaging remain the subsequent stages.

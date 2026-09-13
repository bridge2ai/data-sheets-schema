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

## Generation review round 11 — 2026-09-13

The next independent review found #1431–#1433: pre-provenance chunk selection,
inconsistent source-directory precedence, and canonical bundle-name recovery.
All are addressed; see `reviews/pr_1367_round11_2026-09-13.md`. Renderer
version 3 carries the selected agentic receipt command and an unambiguous
version stamp, while historical versions 1 and 2 remain replayable. Round-9
full CI is green. Exact-head CI and independent review still precede merge.
The evaluation worktree has passing applicability/collection and fake API
judge acceptance tests; agent instruction/schema alignment is in progress.
All earlier stage ordering and measurement-preservation requirements remain.

## Generation review round 12 — 2026-09-13

Round 11 found mixed-renderer resume and interrupted label-switch activation
defects (#1434/#1435). Durable instruction pins and exact predecessor activation
intent address both. Three CI fixture assumptions are corrected in #1437.
The recovery lane passes 203 tests and final compatibility passes 100;
see `reviews/pr_1367_round12_2026-09-13.md`. Exact-head full CI and independent
approval remain required. Evaluation implementation is isolated in its own
worktree. Existing profile PR #1436 is the candidate for the subsequent
profile stage; review it after generation and evaluation rather than duplicate
that work. Packaging follows. All API/agentic arms and evaluation styles above
remain in scope, with historical measurements preserved and downloads deferred.

## Generation review round 13 — 2026-09-13

Round 12 found #1448: automatic date selection prevented ordinary resumes on
the next UTC day. Resume now restores the date from matching persisted render
evidence while preserving explicit choices and all other instruction/input
pins. Nine new cases include real batch reconstruction, completed canary
reuse, portable provenance and controls for fresh/foreign runs and instruction
drift. The API/batch/canary lane passes 189 tests and the usage-journal/midnight
lane passes 60. Round-12 CI passes 3,928
tests with four skips and one corrected condition fixture (#1437). See
`reviews/pr_1367_round13_2026-09-13.md`; full revised-head checks and review
still precede merge.

The evaluation stage is now draft PR #1449, based on #1367 and held for its
first independent review. Its dated boundary note and hash registration cover
all requested generation arms and evaluation styles; the historical condition
audit passes unchanged. Merge order remains generation, evaluation, existing
profile PR #1436, then packaging. Preserve Claude's separate profile/packaging
worktrees while their work continues.

## Generation review round 14 — 2026-09-13

Round 13 is green in full CI. Its independent review reproduced #1454:
backfill could replace a selected chunk instrument with a discovered sidecar.
The fix verifies and preserves the original bundle/chunk identity, retains
recorded absence and refuses unverifiable evidence before writing. The
manifest/replay lane passes 48 tests and provenance compatibility passes 88;
see `reviews/pr_1367_round14_2026-09-13.md`. Revised-head CI and independent
approval remain required before merge.

Evaluation PR #1449 is addressing round-1 findings #1450–#1453 (new-output
version downgrade, source-item criteria, format/MIME double counting, semantic
score-band instructions), plus current hash-contract fixtures and instrument
inventory. No new measurement is launched. The remaining work order stays
evaluation, Claude's profile PR #1436, then packaging, with both generation
arms, every evaluation style and historical preservation still in scope.

## Generation review round 15 — 2026-09-13

Round 14 reproduced #1456: replacing an existing provenance record loses
runtime evidence even if its chunk attestation is preserved. Backfill now
creates only missing records and keeps existing bytes unchanged. Exclusive
publication prevents concurrent replacement and partial canonical records.
Actual fake-provider generation tests preserve accounting, portable snapshots,
receipt enforcement and completed resume. The final provenance lane passes
105 tests and the receipt/recovery lane passes 96; see
`reviews/pr_1367_round15_2026-09-13.md`. Full revised-head CI and independent
approval still precede merge.

Evaluation PR #1449 round 2 has finished: all prior measurement attributions
and boundary hashes were independently confirmed. Remaining findings concern
optional empty Dataset resources, Core collection schema detection, additional
format/MIME aliases and two later semantic score-band instructions. These are
being addressed before its next review. Claude's profile PR #1436 and packaging
PR #1455 are committed; packaging's remaining complete-workflow acceptance is
tracked in #1457. Keep the merge order and all prior measurement constraints.

## Generation review round 16 — 2026-09-13

Round 15 is green (3,957 passed, four skipped). Independent review found
#1472 (incomplete chunk mappings accepted by the pre-provenance strict gate)
and #1473 (a positive source-manifest header lost by missing-record backfill).
Both are fixed, including paths containing “not used.” #1475 removes unsupported
study-history assertions from new unverified external records. Final local
receipt/recovery/rendering verification passes 81 tests; see the round-16
review note. Exact-head CI and approval still precede merge.

Evaluation PR #1449 round 3 resolves its input/alias/instruction findings and
#1474: the reference-rescore harness must copy/pin its complete version-2
validator, original input and definition and verify the registered context.
The offline rescore workflow passes 166 tests, including both rubrics in real
isolated validator subprocesses. The historical CBORG instrument remains
archived and is audited separately. Claude continues profile PR #1436 and
packaging PR #1455. Merge order, all arms/evaluation styles, preservation and
the no-download/no-new-measurement boundary remain unchanged.

## Generation review round 17 — 2026-09-13

Round 16 found #1507: required agentic playbook reads/checks still used default
inputs. Renderer 4 now carries the selected bundle/chunks/source declaration
through every phase, limits scope checks to the current pair and records the
artifact paths used in its instruction. Older renderer controls remain byte
identical. The broad compatibility lane passes 139 tests; final replay checks
pass 34. Round-16 CI's one historical unused-header regression is also fixed;
3,971 tests passed with four skips. See the round-17 review note.

Evaluation PR #1449 round 3 confirms all 21 boundary pins and 315 historical
attributions. It found #1508 (standalone semantic validation must bind context
to the caller) and #1509 (explicit Dataset declarations must survive valid
resources). Both are being addressed before its next review. The local
combined evaluation lane passed 816 tests, final controller checks 169 and
inventory checks 12. Continue generation, evaluation, profile PR #1436, then
packaging PR #1455; preserve both generation arms, all evaluation styles and
all measured artifacts, with source downloads and new measurements deferred.

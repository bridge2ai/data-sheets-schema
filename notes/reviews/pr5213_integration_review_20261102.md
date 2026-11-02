# #5213 integration review notes — 2026-11-02

Offline issue drafts and review decisions for the integration of D76 with
main `ddfd45c3b520d37da247cf899401437794880e0c`. AGY owns any GitHub publication.

## I1 — Timing evidence must distinguish requested installation from completion

The first timing-helper draft wrote `installed: args.install` into its evidence
before atomically installing the duration file. If installation then failed,
that retained evidence could incorrectly imply successful installation.

Disposition: fixed and verified by the no-install preview followed by the
byte-checked install. The prepared evidence records
`installation_requested`; a separate, exclusively created installation record
is written only after replacing the target and verifying its bytes. The output
must retain the main weights and provenance and bind the installed digest.
The no-install preview and subsequent verified install are the acceptance
checks; their results belong to the integration report. No GitHub issue was
filed during this offline task.

## I2 — Ordering checks need an independent inventory-read witness

The first ordering-test draft asserted D76's diagnostic and trapped authority,
client and lock calls, but did not independently record D69 inventory reads.
An inventory read whose result was ignored could precede D76 and still satisfy
those assertions.

Disposition: fixed in the test draft before execution. Delegate spies now
record the real `_legacy_evidence` and `owned_artifacts` calls after fixture
prechecks. D76-negative and inspection routes require zero such reads. The
valid-D76 combined-refusal control requires the real inventory calls while
retaining zero authority, client and lock observations. No production guard
or existing assertion is weakened. Validation results remain in the report.

## I3 — A full-collection proof must reject filtered selections

The initial integration planner checked a successful `tests --collect-only`
run but did not independently reject lane/shard filters or require selected
and collected occurrence Counters to agree in its partition path. That could
mislabel a filtered run as the authoritative complete collection.

Disposition: fixed before execution. Require an unfiltered collection, exact
collected/selected Counters, and the same archive tree as the collection plan.
Also enforce the separate serial SG2/notes session constraints when reporting,
rather than checking only the broad two-worker maximum. Contract tests cover
the rejected proof shapes. No existing runner guard is relaxed.

## I4 — Scratch-commit evidence paths must not alias the source

Independent review found that the scratch-commit helper initially checked
output containment lexically. A relative path or symlinked parent could bypass
those checks and place its temporary index or evidence in the source tree.

Disposition: fixed before execution. Require an absolute, nontraversing output
with a physically checked parent outside both source and scratch trees. Bind
the mutation proof to the original head and source hashes before writing.
Three path contracts exercise rejection, and independent re-review cleared the
revised guards. Only isolated scratch commits may contain ordering mutations.

## I5 — Calibrate the competing owner refusal in the actual resume mode

The first fixture checked the competing owner refusal with `resume=True` even
for the no-resume execution case. Main refuses both, but with different
diagnostics; the test should establish the exact competing condition it claims.

Disposition: fixed before execution. Fresh execution/dry-run cases calibrate
`resume=False` and the no-resume spent-output refusal. Other cases calibrate
the ordinary ownership refusal. Both dry-run modes are also included in the
shared authority/owner matrix. These additions produce81 intended cases;
the executed collection remains authoritative for the eventual count.

## Reviewed mutation-evidence method

The existing validation runner correctly refuses an uncommitted source mutation.
Do not bypass its tracked-source/archive checks for ordering experiments.
Each intended route mutation is instead a commit in an isolated scratch local
repository, with the final integration commit as its parent. Archive that
mutation commit, retain the exact patch and unchanged test hashes, and reuse
the normal strict runner. No scratch commit is pushed or merged into the author
branch. Run one mutation end to end and verify its intended assertion failure
and complete evidence before running the remaining route mutations.

Nested guards on the selected route may otherwise mask moving its outer guard.
Any necessary nested relocation must be explicit in that mutation's patch and
report; changing execute alone does not establish CLI, batch or render coverage.
Setup errors and missing fixtures do not count as successful mutation checks.

# Bounded implementation brief: adjacent post-acceptance reconstruction

2026-11-11. Lead release for source implementation and review only, within the
user's native development-efficiency task. This does not release runtime.

## Evidence and scope

Base is frozen source `382f0dfd1ce863fdf257a77e2bbb2637dbe2f67b`.
Read `d4d-executions/plans/reviews/native_postaccept_producer_boundary_20261111.md`,
SHA256 `8c4286318f6f2c69f346c3692b897d6a294d5f951d570c4c92cfd0386c46adc9`,
and the lead's `../reviews/remaining_postaccept_feasibility.md`.
Three independent source reviews found no concrete new pre-reservation gap in
the proposed fusion. They did not establish strict sampling equivalence or
performance. Removing a full verification also removes its intermediate sample;
do not claim detection of every transient change restored before the remaining
verification. If the existing contract requires both distinct samples, retain
both and report the conflict instead of weakening it.

Create a new isolated branch and worktree from that exact base before editing.
Preserve the original source worktree, preparation tools, helper worktree,
private composition, restored configuration and all evidence unchanged.

## Exact intended change

Only the actual shared `CurrentSelection` route inside the live `_launch` may
combine the second `_unchanged` reconstruction with the adjacent lease's full
reconstruction. Keep initial verification, pre-admission `_unchanged`, acceptance,
join, public/direct entry points and all later dispatch checks unchanged.

Retain the genuine initial execution value as canonical immutable bytes local
to this invocation. Those bytes are comparison data, never a supplied verdict,
capability or persistent cache. Track actual selection acceptance in local
control flow rather than a caller flag.

Preserve the second `_unchanged`'s input-only tail at its current position and
with its actual dependencies: shared `_file`, shared `_platform` and committed
source verification. Do not silently substitute `effects.file`, `sys.platform`
or another implementation. An extracted input-only tail called by the existing
full `_unchanged` and this private path is acceptable if it preserves behavior.
Explicitly document the skipped `effects.unchanged` invocation; no branch may
detect monkeypatches or fall back based on test state.

Keep the existing `_current_authority` fresh producer chain and current v3
request check at the lease boundary. Compare its fresh execution value to both
the original canonical bytes and the current engine value before the journal
lock. Keep the composition local to the genuine launch rather than creating a
public supplied-value/verdict interface.

Retain `words.locked(create=False)` and `journal.require`, then controls,
original-clock freshness/margin, profile validation, mkdir and fsync within the
same lock lifetime. Do not nest capture/journal locking, retimestamp a capture,
alter age300/margin90, or change the later launch/dispatch path.

## Review checkpoint

Report the exact diff, before/after call order, known semantic differences and
smallest affected test proposal. Existing cheap fixture seams may be used to
design tests of the real orchestration ordering; label their limits explicitly.
Include unchanged success, changed engine value and producer/input mutation
before reservation, and unchanged direct/public behavior in the proposed checks.
Do not replace real reconstruction evidence with call counts alone.

Stop after implementation for a separate adversarial review. No tests, imports,
profiling, native/provider calls, genuine capture/diagnostic retry, preparation,
configuration rearm, protected-file edit, merge or cleanup is released here.
No push is needed until the review checkpoint; preserve local work on the new
branch. Lead will record every concrete finding in an issue before repair.

This slice cannot close the whole U3K-F1 obligation or demonstrate freshness or
speed. Existing issues5722/5836 remain the trackers. It adds no prerequisite to
the separately scoped API-only final D4D run.

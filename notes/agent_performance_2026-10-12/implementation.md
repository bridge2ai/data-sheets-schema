# Performance implementation ledger

This ledger tracks implementation of the [historical audit](README.md). The
audit is a preserved baseline; changes and their validation belong here.

Tracking issue: [#5014](https://github.com/bridge2ai/data-sheets-schema/issues/5014).
Initial implementation base: `df2aa6c663c8d5712e3bd51885a6806f00982d79`.

## Priority queue

Reassess the queue before starting the next unit. Prioritize demonstrated
critical-path costs, then repeated iteration costs. New defects discovered while
implementing a unit become linked issues with a concrete failure and acceptance
criteria; unrelated new behavior is a separate scope decision.

| Priority | Issue | Scope | Current evidence/status |
| --- | --- | --- | --- |
| 1 | [#5015](https://github.com/bridge2ai/data-sheets-schema/issues/5015) | Long shared-generation replay test | Baseline passed in799.95 s;19 execute calls; catalog reuse prioritized |
| 1 | [#5016](https://github.com/bridge2ai/data-sheets-schema/issues/5016) | Current shard weights | Refreshed18,848 occurrences/524 files; focused regressions passed; PR pending |
| 1 prerequisite | [#5020](https://github.com/bridge2ai/data-sheets-schema/issues/5020) | Legitimate repeated JUnit labels | Independent review clear;13 updater and 24 partition/workflow tests passed |
| 2 | [#5017](https://github.com/bridge2ai/data-sheets-schema/issues/5017) | Agent instructions and workflow routes | 178-line guide drafted; independent review underway; incorporates #3863 |
| 2 | [#5018](https://github.com/bridge2ai/data-sheets-schema/issues/5018) | Collection and nested concurrency | Planned measurement and coverage-preserving implementation |
| 2 | [#5019](https://github.com/bridge2ai/data-sheets-schema/issues/5019) | Workspace/search/guard costs | Guard traversal improvement reviewed; runtime comparison pending; existing work preserved |

Existing related work: [#3863](https://github.com/bridge2ai/data-sheets-schema/issues/3863)
and [#4517](https://github.com/bridge2ai/data-sheets-schema/issues/4517), including
its review corrections #4519, #4520 and #4522 in PR #4508. Reconcile the actual
state of that active PR before editing its lane-selection contract. This ledger
does not claim ownership of another session's pending changes.

## Acceptance and review loop

For each unit:

1. Record the selected issue, intended behavior, preserved invariants and exact
   source/environment identity.
2. Implement and run the smallest decisive checks, followed by the required
   acceptance gates. Reuse unchanged evidence only when its inputs remain valid.
3. Obtain adversarial review of the actual diff. File concrete review defects,
   fix them, and record the next review round. After more than five issue-bearing
   rounds, invoke the Codex plugin review required by the user.
4. Take the PR through green required CI, merge, and delete only its completed
   task branch. Record PR/head/check/merge evidence and issue closure.

The tracker remains open until the full issue set and directly related review
defects have verified dispositions. A passing focused test, a proposed plan or a
reviewer acknowledgment alone does not prove completion.

## Preserved boundaries

- Existing checkouts, unpushed commits, worktrees, registered instruments,
  historical generations and scientific evidence remain intact.
- Full corpus and independent fresh reconstruction/validation checks remain
  required. Timing weights schedule tests; they never select coverage.
- The benchmark uses scripted offline deliveries. It does not authorize paid
  provider runs, scientific scoring decisions or publication of held outputs.
- Use a shared runtime budget across sessions. This task's project execution is
  serial; independent source review can proceed in parallel.
- Scope normal searches to the code or evidence required. Absence/deletion
  claims still require ignored-inclusive discovery with explicit exclusions.

## Progress

- Saved the audit as Markdown with portable supporting measurements and hashes.
- Created the tracker and five implementation issues after checking existing
  open issues/PRs; filed the concrete timing-updater blocker separately.
- Created an isolated worktree on current remote main and installed the locked
  dependencies in a fresh Python 3.12.11 virtual environment.
- Retrieved run `38158491197` and verified archive hashes. Its four core reports
  contain 18,848 testcase occurrences, 18,847 unique label pairs, and 524 mapped
  test files. One legitimate repeated label occurs twice within shard 4; no
  identities cross core artifacts. No source test was renamed or deduplicated.

No optimization is yet claimed as shipped. Baseline and changed-source timings,
review rounds, PR checks and merge receipts will be recorded as they occur.

### Critical replay baseline

The unchanged node passed in799.95 s in the locked Python3.12.11 environment. The instrumentation recorded 19 API execute entries: five of seven mutation cases enter execute; two refuse during fresh run construction, correcting the audit’s static 21 estimate. All source pins remained unchanged; instrumentation reported no errors and restored all bindings. The outer timing command returned1 only because `/usr/bin/time -l` could not read sandboxed `sysctl` metadata; pytest itself exited0. No unchanged rerun is needed.

The profile attributes 290.390 inclusive seconds to 50 schema catalog calls,471.026 to 53 runtime rebuilds, and 29.667 to 13 validator subprocess calls. These nested inclusive times overlap. Catalog construction is the next optimization target; final independent checks and all original replay assertions remain required. This local profile establishes attribution, not a speedup against earlier CI runs.

### Timing refresh validation

The corrected updater retained all 18,848 testcase occurrences and 524 file totals from the four verified core artifacts. All four recorded XML hashes match the downloaded evidence. The 13 new updater cases and 24 existing partition/workflow tests passed in 89.73 s; the refreshed-weight balance test passed again in 0.06 s. [Refresh evidence](timing-refresh.json) records provenance and scheduling estimates. Full PR CI remains pending.

The instruction compaction exposed [#5021](https://github.com/bridge2ai/data-sheets-schema/issues/5021): an existing smoke test required actual project leakage in the root guide. The bounded correction preserves nonvacuous root discovery, classification and gates while retaining the separate planted-leak regression. Independent static review of the guide and guard changes is clear; their runtime checks are underway.

# D4D coding-agent performance investigation


> Correction from implementation profiling: the original static estimate below
> of 21 execution attempts was incorrect. The unchanged test at `df2aa6c`
> executes 19 attempts, including five mutation replays. All controls remain
> required. See [implementation results](implementation.md).

2026-10-12, America/Los_Angeles

> Historical baseline. “Current” and “latest” below refer to the audit snapshot,
> not the state at a later reading. The source audit is retained unchanged; its
> SHA256 and sanitized supporting measurements are in [evidence.json](evidence.json).
> This Markdown conversion added no project execution or new performance measurement.

## Conclusion

The largest measured delay is the validation/CI critical path. One test took
28–31 minutes in two recent runs. Repeated collection, stale scheduling weights,
large instruction/search surfaces, and a busy shared machine add separate costs.
Basic Git operations and cached dependency installation were fast in this audit.
Deleting branches or scientific evidence is not the first performance intervention.

## Scope and limits

Audited checkout: the primary local repository (private filesystem path omitted).
Local HEAD: ce82966c7fc113916832b6dbcaaee4e93cac8572, branch main.
Remote main observed by the CI audit: df2aa6c663c8d5712e3bd51885a6806f00982d79.
The four inspected CI/config files match remote main. The timed test's historical
source was not joined byte-for-byte to every current local implementation file.
Historical CI timings and current static structure are therefore identified
separately below. The workspace has other active writers and existing changes.

This was a read-only investigation: filesystem/AST metadata, source inspection,
Git timing, host counters, and existing GitHub Actions logs. No project imports,
test suite, provider generation, installs, CI triggers, repository edits, issues,
commits, pushes, cleanup, or worktree removal. At the time of the investigation,
the prior engineering goal was paused and
evidence was saved externally. This document preserves that historical audit; it
does not state the present task status or claim any optimization has shipped.

## Ranked findings and actions

### 1. HIGH: An indivisible integration test dominates merge feedback.

Latest 50 main-workflow runs sampled, October 10–11 UTC: 46 successes,
three cancellations, one failure. Successful pull-request feedback median:
1,926s (32.1min, n=23). Successful main/push median: 2,255s (37.6min, n=23).
Feedback is API created_at to updated_at, including orchestration/queue time.

`test_real_complete_api_pipeline_and_completed_recheck` took:

- 1,703.75s in PR job 114497106389, 77.4% of that run's feedback interval.
- 1,889.52s in main job 114526286493, 73.2% of that run's feedback interval.

These are pytest call-phase wall durations, not CPU time.

Current local tests/test_shared_generation_runtime.py:140–175 puts 21
execution/replay attempts inside one test item: initial execution, clean
replay, seven mutation attempts, eight attribution attempts, four authority
attempts. Some intentionally fail early. xdist cannot divide this item.
Completion checks reconstruct saved stages with fresh independent caches;
output validation can spawn LinkML validator children. Those boundaries are
supported by source inspection; their individual runtime shares are unmeasured.

First action: profile this exact node once in the matching locked environment
on a quiet host, with timings for each replay group, validation subprocesses,
and independent reconstruction. Then optimize the demonstrated repeated work
or safely isolate cases around immutable fixtures. Preserve every assertion,
fresh-reader check, mutation, generation phase, and no-new-provider-call check.
Blindly parameterizing 21 independently regenerated pipelines could be slower.
More shards alone cannot remove this serial lower bound.

Evidence: [portable summaries and source-receipt hashes](evidence.json).
[PR timing log](https://github.com/bridge2ai/data-sheets-schema/actions/runs/38148606188/job/114497106389)
[Main timing log](https://github.com/bridge2ai/data-sheets-schema/actions/runs/38158491197/job/114526286493)

### 2. HIGH: Scheduling data is old; collection is repeated before sharding.

utils/ci_test_durations.json comes from September 16 UTC, 281 files and 5,209
historical cases. Current filename candidates: 509; 228 lack timing entries.
Separately, AST inventory finds 508 files with literal test definitions, 227
without weights. Neither is a fresh pytest collected-case roster.
Untimed files receive a median estimate of 1.775s, including the file with the
28–31min test and test_generation_specificity_skill.py.

In 12 sampled successful runs, median slowest/fastest core-shard ratio was
2.16. Median summed elapsed job time was 123min per run; this is aggregate
job duration, not CPU usage, billing, or elapsed user wait.

utils/pytest_shard.py:98–120 deselects after imports and collection. Six PR
shards with up to four workers therefore perform up to 24 full worker
collections. This proves work multiplication, not a 24x wall-time slowdown.
Process-local schema/scanner caches may also warm repeatedly.

First bounded fix: refresh weights from a complete successful current run
with the existing utils/update_ci_shard_timings.py procedure documented in
utils/ci_sharding.md:70–84. Retain artifact hashes/run identity and a verifiable
union of all collected tests and corpus checks; do not mix runs/interpreters.
Then measure collection/import time. If material, select files before worker
collection using one authoritative current discovery/coverage manifest.
A manually curated timing table must never determine which tests are covered.

Evidence: [portable summaries and source-receipt hashes](evidence.json).

### 3. HIGH FOR AGENT EFFICIENCY: Instructions are large and partly stale.

Root CLAUDE.md is 1,873 lines / 109,384 bytes. Lines 345–1805 account for 86%
of its bytes and contain extensive domain history/reference material.
This is a context-size measurement, not a measured token bill or latency.
Conditional agent/playbook bodies are additional context only when selected;
they should not all be counted as automatically loaded.

Concrete avoidable work:

- CLAUDE.md:1809–1819 describes an obsolete CI/corpus/Python-version matrix.
  Current CI includes the corpus on PRs, six PR shards, four main shards,
  Python 3.12, and separate offline lanes.
- CLAUDE.md:125–131,1871 prescribes make test-schema and then make test;
  Makefile:236–245 makes the latter perform the schema check again.
- CLAUDE.md:289–298 routes workflow work into 61.7KB of retired assistant/MCP
  instructions, while the current workflow uses input-bundle/API generation.
- CLAUDE.md:15 describes make setup as initial setup, but Makefile:160,361–368
  runs generators/docs, stages files, and commits. It is a scaffolding action,
  not a dependency-only bootstrap; it can create unrelated recovery work.

Recommended first documentation change: a short current operating guide with
explicit task routing, commands, preservation rules, and links to intact
historical/domain references. Correct the stale routes and duplicated gate.
Version model-facing instruction changes; preserve registered historical bytes.
Do not globally deduplicate immutable prompt/agent instruments.

Evidence: [portable summaries and source-receipt hashes](evidence.json).

### 4. MEDIUM, REPEATED LOCALLY: Search and test discovery cross evidence/worktrees.

Tracked files: 9,476 / 431.1MiB logical bytes. data/ and notes/ account for
91.7% of those bytes. Normal filename enumeration: 9,936 names / 0.048s.
Explicit code scope (src, scripts, tests, .github): 1,336 names / 0.028s.
Ignored/hidden-inclusive enumeration, excluding Git/dependency/private dirs:
105,851 names / 0.429s, generating 14.9MB of filename output. This includes
52,151 files under notes/.local_worktrees and 38,781 under v10d local drafts.
Enumeration is quick; feeding broad results to agents and repeatedly parsing
their contents creates a different, potentially much larger cost.

A separate metadata walk excluding nested repositories, environments, Git,
symlinks and private boundaries counted 52,737 regular files / 7.30GiB.
Major retained contents: v10d local drafts (~3.55GiB) and the CM4AI raw image
archive (~3.19GiB). These are evidence/payloads, not disposable caches.
Full workstation/worktree/environment disk usage was not measured.

tests/conftest.py:42–67 walks all notes paths before and after EVERY selected
tests/ session. Reproducing those two stdlib traversals examined 109,552 paths
per pass and took 2.672s + 1.476s = 4.148s in this local checkout. This is a
local snapshot, not CI overhead or a stable benchmark. Concurrent writers can
also trigger this guard because it cannot attribute who added a notes path.

Recommended operating changes: explicit source/test paths for routine coding;
separate evidence searches; bounded search output; future scratch checkouts
outside the repository. Preserve all existing protected worktrees and evidence.
Keep ignored-inclusive searches for absence/deletion claims. An ignore rule
cannot speed os.walk unless the guard itself is redesigned; do not weaken its
protection casually. Compare focused-test latency in a complete clean checkout.
Bare pytest is also a discovery risk: root config has no testpaths and dated
nonhidden notes contain tests. Actual bare collection was not executed.

Evidence: [portable summaries and source-receipt hashes](evidence.json).

### 5. MEDIUM/HIGH UNDER CONCURRENCY: Shared host and nested test processes.

Machine: 10 cores, 64GiB RAM. Observed load averages ~17–19. Snapshot process
groups included 15 Python processes using ~384% CPU, 20 Claude processes and
37 Codex processes (the latter counts do not imply actively computing agents).
These executable groups may include unrelated work; no owner was inferred.

Swap used ~9.5GiB, but over 119s only 32 swap-in pages and zero swap-out pages
were added. memory_pressure reported 50% system-wide free. This does NOT
establish active swap thrashing. Disk had ~448GiB available (88% used).
High load is a contention signal; it does not isolate CPU versus I/O causes.

tests/test_ci_sharding.py launches pytest inside pytest. Four scheduling cases
alone create 24 child controllers and up to 80 worker starts ACROSS those
cases, not 80 necessarily simultaneous workers. Outer parallelism can multiply
their overlap. Current cost/peak overlap needs measurement.

Recommended operating rule: one shared test/benchmark concurrency budget
across coding sessions; bounded worker counts; serial comparative benchmarks
on a quiet host. Audit nested process scheduling before increasing xdist.
Do not kill, reset, or remove other sessions to obtain a benchmark.

Evidence: [portable summaries and source-receipt hashes](evidence.json).

### 6. IMPORTANT PROCESS COST: Broad task/review loops and large reasoning surfaces.

api_runner.py is 433.5KB; receipt-origin tests 400.7KB; specificity scanner
335.6KB; specificity tests 244.1KB. Current AST inventory finds 8,981 literal
test definitions across 527 Python files. These are size/count measurements,
not proof each file executes slowly. They make broad whole-file reviews and
repeated imports/analysis expensive candidates.

The prior session also accumulated many review/freeze/handoff artifacts.
Their count is not a count of wasted rounds: reviews found real issues.
The full freeze/plugin/serial machinery was session-specific, not a universal
requirement for every repository edit. It remains binding where authorized.

Recommendation: one current acceptance ledger with scope, unresolved defects,
source/test/environment identity, ownership, and the next decisive check.
Review the delta; reuse still-valid unchanged evidence; classify new proposed
behavior separately from violations of the accepted contract. Run focused
tests during iteration and the required complete gate at the proper checkpoint.
Preserve adversarial review, scientific acceptance and explicit user holds.

Additional unmeasured candidates: schema term hooks may run on every edit
with 60s timeouts; activation was not checked. Function-scoped copies, LinkML
views, and cache invalidation deserve profiling, but schema caching already
exists. Do not present historical cache fixes as newly discovered omissions.

Evidence: [portable summaries and source-receipt hashes](evidence.json).

## What is lower priority given current measurements

- Git status: 0.125s tracked-only, 0.284s normal. Worktree listing: 0.175s for
  50 registered worktrees. Ref enumeration: 0.070s for 80 refs. No Git cleanup
  is justified by those latencies; active work must remain preserved.
- Cached CI setup median ~8s and checkout median ~12s in sampled successful
  jobs. Cold installs were not characterized. Dependency trimming is secondary.
- The docs workflow median was 42.5s in 20 runs. Its published-output obligations
  should not be disturbed to save seconds before addressing the minute-scale test.
- Small caches/build trees and duplicate environments are not demonstrated as
  dominant. .venv and venv use ~727MiB and ~363MiB allocated disk respectively;
  their presence is an environment-selection consideration, not deletion authority.

## Suggested implementation order

1. Instrument the long integration test and preserve its full contract.
2. Refresh shard timings from current complete CI evidence; track imbalance.
3. Correct and shrink agent entry instructions, preserving versioned references.
4. Adopt explicit search/test scopes and a shared worker budget immediately.
5. Measure collection, nested pytest and filesystem guard costs; then make the
   smallest demonstrated optimization with unchanged coverage/acceptance checks.

6. Consider conservative CI change classification only after documenting all
   executable/model-facing schema, notes, prompt and corpus dependencies. Treating
   every Markdown/data-only change as harmless would be incorrect in this repo.

No speedup percentage is promised. Record before/after wall time, total job time,
test coverage identity, environment and machine load for each approved change.

## Immutable source anchors and evidence

The original audit joined four CI/configuration files to remote main. During this
Markdown conversion, a read-only Git-object comparison also matched eight of the
nine saved source-snapshot hashes to the commit below, including both pipeline test
files. The saved primary Makefile differs overall; its cited setup and test targets
are independently present at this commit. This later metadata check does not join
all production/dependency bytes or either historical execution environment.

| Claim | Immutable source |
|---|---|
| Indivisible pipeline attempts | [tests/test_shared_generation_runtime.py:140–175](https://github.com/bridge2ai/data-sheets-schema/blob/df2aa6c663c8d5712e3bd51885a6806f00982d79/tests/test_shared_generation_runtime.py#L140-L175) |
| Post-collection shard selection | [utils/pytest_shard.py:72–120](https://github.com/bridge2ai/data-sheets-schema/blob/df2aa6c663c8d5712e3bd51885a6806f00982d79/utils/pytest_shard.py#L72-L120) |
| Current CI shard/lane policy at audit | [.github/workflows/main.yaml:1–84](https://github.com/bridge2ai/data-sheets-schema/blob/df2aa6c663c8d5712e3bd51885a6806f00982d79/.github/workflows/main.yaml#L1-L84) |
| Timing refresh procedure | [utils/ci_sharding.md:70–84](https://github.com/bridge2ai/data-sheets-schema/blob/df2aa6c663c8d5712e3bd51885a6806f00982d79/utils/ci_sharding.md#L70-L84) |
| Historical timing table | [utils/ci_test_durations.json:1–24](https://github.com/bridge2ai/data-sheets-schema/blob/df2aa6c663c8d5712e3bd51885a6806f00982d79/utils/ci_test_durations.json#L1-L24) |
| Root memory and schema workflow | [CLAUDE.md:125–131](https://github.com/bridge2ai/data-sheets-schema/blob/df2aa6c663c8d5712e3bd51885a6806f00982d79/CLAUDE.md#L125-L131) |
| Obsolete CI directions in root memory | [CLAUDE.md:1807–1837](https://github.com/bridge2ai/data-sheets-schema/blob/df2aa6c663c8d5712e3bd51885a6806f00982d79/CLAUDE.md#L1807-L1837) |
| Assistant instruction routing | [CLAUDE.md:287–298](https://github.com/bridge2ai/data-sheets-schema/blob/df2aa6c663c8d5712e3bd51885a6806f00982d79/CLAUDE.md#L287-L298) |
| Actual bundle/API assistant | [.github/workflows/d4d-agent.yml:277–323](https://github.com/bridge2ai/data-sheets-schema/blob/df2aa6c663c8d5712e3bd51885a6806f00982d79/.github/workflows/d4d-agent.yml#L277-L323) |
| Schema gate duplication | [Makefile:232–245](https://github.com/bridge2ai/data-sheets-schema/blob/df2aa6c663c8d5712e3bd51885a6806f00982d79/Makefile#L232-L245) |
| Scaffold setup side effects | [Makefile:360–368](https://github.com/bridge2ai/data-sheets-schema/blob/df2aa6c663c8d5712e3bd51885a6806f00982d79/Makefile#L360-L368) |
| Notes preservation traversal | [tests/conftest.py:42–67](https://github.com/bridge2ai/data-sheets-schema/blob/df2aa6c663c8d5712e3bd51885a6806f00982d79/tests/conftest.py#L42-L67) |

The compact [evidence file](evidence.json) includes the 50-run and 20-run public CI
samples, 12 successful-run job summaries, two log excerpts and their hashes,
source joins, static test counts, aggregate filesystem/host observations and
hashes of the detailed external component reports. Public workflow links permit
rechecking CI observations while Git object anchors preserve source identity.
Raw logs, full private inventories, process command lines, and private executable
paths are intentionally excluded. Receipt hashes identify retained external
evidence; a hash alone is not a substitute for unavailable raw measurements.

The external cleanup inventory had its own exclusions and completeness scope;
it was not a whole-workspace inventory or deletion verdict. No evidence or
working checkout is made disposable by this report.

## Implementation tracking

These follow-up issues were filed after the audit. Their presence does not imply
that a change has been implemented, validated or merged; the baseline above
remains a historical observation.

| Work | Issue |
|---|---|
| Full performance work tracker | [#5014](https://github.com/bridge2ai/data-sheets-schema/issues/5014) |
| Critical integration-test path | [#5015](https://github.com/bridge2ai/data-sheets-schema/issues/5015) |
| CI timing refresh and scheduling evidence | [#5016](https://github.com/bridge2ai/data-sheets-schema/issues/5016) |
| Instruction size and stale routing | [#5017](https://github.com/bridge2ai/data-sheets-schema/issues/5017), related [#3863](https://github.com/bridge2ai/data-sheets-schema/issues/3863) |
| Focused iteration and execution coordination | [#5018](https://github.com/bridge2ai/data-sheets-schema/issues/5018), related [#4517](https://github.com/bridge2ai/data-sheets-schema/issues/4517), [#4519](https://github.com/bridge2ai/data-sheets-schema/issues/4519), [#4520](https://github.com/bridge2ai/data-sheets-schema/issues/4520), [#4522](https://github.com/bridge2ai/data-sheets-schema/issues/4522) |
| Workspace/search and preservation-guard scope | [#5019](https://github.com/bridge2ai/data-sheets-schema/issues/5019) |

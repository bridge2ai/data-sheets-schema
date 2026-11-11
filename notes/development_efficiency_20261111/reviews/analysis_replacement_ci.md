# Analysis replacement PR: CI evidence

Observed 2026-11-11 at 05:40:02 UTC. This review used read-only GitHub queries and
local Git object inspection. The lead requested the cancellation; the reviewer
performed no cancellation, dispatch, remote write, notification or test run.

[PR 5843](https://github.com/bridge2ai/data-sheets-schema/pull/5843) closed at
05:28:53 UTC after its evidence-base branch was merged/deleted. Replacement
[draft PR 5853](https://github.com/bridge2ai/data-sheets-schema/pull/5853) targets
main `925d726d67cdd03fe28fdeafdde60fa27df57205`.

| CI run | Exact head | Terminal result | Created → updated, UTC | Elapsed |
|---|---|---|---|---|
| [42963052291](https://github.com/bridge2ai/data-sheets-schema/actions/runs/42963052291), old PR | `aa86cf0039293a042666751d69dd703a20bfabf5` | **success** | 05:02:06 → 05:39:16 | 2230 s / 37m10s |
| [42966522505](https://github.com/bridge2ai/data-sheets-schema/actions/runs/42966522505), replacement | `76a443ee34103ed18f30041c111f9f2aae1af40e` | **cancelled** | 05:33:21 → 05:39:55 | 394 s / 6m34s |

The old run completed all 18 test jobs successfully: eight ordinary shards,
four API cases, three SG2 cases and three offline jobs. Schema-examples was the
expected PR skip. Its aggregate `test` job **130345592163** then passed at
05:39:13–05:39:15 (2 s), giving 19 successful jobs and one expected skip.

The last test job was shard 8, **130333865199**, successful at 05:35:22. Its job
wall time was 1993 s (33m13s), including an execution step of 1964 s (32m44s),
05:02:34–05:35:18. The aggregate was observed queued after that completion;
its later start is scheduling delay, not additional test execution.

Immediately before cancellation, the replacement had six dedicated jobs running,
12 test jobs queued and one expected skip. All eight ordinary shards were still
queued. Terminal evidence records 18 cancelled jobs, the expected schema skip,
and aggregate `test` **130347121309** failed at 05:39:52–05:39:54 (2 s). That
aggregate failure is consistent with its unchanged requirement that every
applicable lane succeed; cancelled lanes do not pass. **The replacement head has
no green full-CI result.** Its separate [large-files run 42966522496](https://github.com/bridge2ai/data-sheets-schema/actions/runs/42966522496)
passed at 05:33:44; the mention workflow 42966522511 was skipped.

## Value of repeating the full suite

Both local heads have full tree `d5104e82d26fabfe0af981a3c8168b5e03abfdb0`.
GitHub's reported synthetic merge commits also have exactly that tree:

- Old PR: `bea53805bfb34a91d6ab023ef5b934a92d79712f`, parents
  `fa4f3a7f01ee9531555899ffdc7838b64a2992ab` and `aa86cf0039293a042666751d69dd703a20bfabf5`.
- Replacement: `f0ac52faf0b83d19c5ed14cfa740ff891b00a696`, parents
  `925d726d67cdd03fe28fdeafdde60fa27df57205` and `76a443ee34103ed18f30041c111f9f2aae1af40e`.

There is no changed file tree, workflow, sharding configuration or test selection
to validate again. The workflow's concurrency group includes the PR number, so
opening 5853 did not supersede 5843's run automatically. The completed old run
provides successful full-suite evidence for the identical tree.

A repeated run would add a result attached to the new commit/PR context and
re-exercise changed Git ancestry and variable runner/environment state. Tree
equality alone does not prove all history-sensitive behavior identical. For
this draft's development feedback, the duplicate full suite adds little new
coverage; retaining the old result and recording the cancellation is reasonable.
It does **not** transfer a green status to 5853, bypass its aggregate gate,
authorize merging, or establish native freshness acceptance.

## Retained provenance

Helper: `scripts/adhoc/capture_analysis_replacement_ci_20261111.py`, SHA256
`ba5df7c303aec85c29b894e67bc9616a9c24a5660c9937819c2eac8bc2d15fb0`.
It uses only GitHub read commands and local Git reads; no project imports.
Three successive snapshots remain under ignored `tmp/analysis-replacement-ci-`
directories ending `20261111T053856Z`, `20261111T053923Z`, and
`20261111T053958Z`. Each retains exact query arguments, selected JSON responses,
response hashes and a computed duration summary.

Final summary: `tmp/analysis-replacement-ci-20261111T053958Z/summary.json`, SHA256
`67c30d1c9f174eba28f55b95600497f55580b00e342d818b5a42c3120748bb6c`.
The summary field `queue_to_started_seconds` measures run creation to job start,
including dependency waits; it is not an isolated queue-duration measurement.
Elapsed workflow times above use terminal `updatedAt - createdAt`, while job
and execution-step times use their own recorded start/end timestamps.

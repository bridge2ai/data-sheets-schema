# CI Queue vs. Execution Checkpoint (2026-11-10)

Historical snapshot (`2026-11-10T06:18:34Z`) from `.temp/ci-queue-checkpoint-20261110/` via `scripts/adhoc/analyze_ci_queue_checkpoint_20261110.py`.

## 1. Trigger & Concurrency
- `main.yaml:1-30,83-381` runs on unfiltered `pull_request` (`#1361`), spawning **18 `ubuntu-latest` test jobs** plus skipped `schema-examples` and final `test` (`if: always()`). `large-files.yaml:1-15` adds `1` job (`20` jobs/push).
- `concurrency` (`main.yaml:16-18`) cancels superseded runs only within the same PR (`Build and test data_sheets_schema-<pr>`). Cross-PR contention (~20 concurrent jobs inferred from active counts, not observed cap) delays starts.

## 2. Workflow-Creation-to-Job-Start vs. Whole-Job Duration (`main.yaml`)
Start delay is `job.started_at - run.created_at` for runner-assigned jobs (`runner_id > 0`, non-empty `steps`); whole-job duration is `job.completed_at - job.started_at` (including setup/checkout/post steps).

|PR (`head`)|Run & `06:18Z` State|Created|Start Delay|Whole-Job Duration|
|---|---|---|---|---|
|`#5678` (`0e28ab54d`)|[42734850581](https://github.com/bridge2ai/data-sheets-schema/actions/runs/42734850581) `success`|`01:18:30Z`|`3–4s` (`01:18:33Z–01:18:34Z`)|`276–1852s` (done `01:49:32Z`)|
|`#5677` (`c135e916b`)|[42740507255](https://github.com/bridge2ai/data-sheets-schema/actions/runs/42740507255) `success`|`02:07:09Z`|`25–1264s` (last `02:28:13Z`)|`287–2329s` (done `02:58:11Z`)|
|`#5710` (`db9295538`)|[42743340595](https://github.com/bridge2ai/data-sheets-schema/actions/runs/42743340595) `success`|`02:31:24Z`|`2–791s` (last `02:44:35Z`)|`283–2180s` (done `03:14:59Z`)|
|`#5709` (`807417fc2`)|[42764693028](https://github.com/bridge2ai/data-sheets-schema/actions/runs/42764693028) `in_progress` (`13/18` done)|`05:51:10Z`|`27–86s` (`05:51:37Z–05:52:36Z`)|`294–1475s` (`13` done `06:17:11Z`; `5` running)|
|`#5665` (`2a5db4ac5`)|[42765972713](https://github.com/bridge2ai/data-sheets-schema/actions/runs/42765972713) `queued` (`1` done, `15` running, `2` queued)|`06:03:36Z`|`457–816s` (`16` started `06:11:13Z–06:17:12Z`; `2` unstarted `>885s`)|`169s` (`1` done `06:14:04Z`; `17` incomplete)|
|`#5711` (`c22a08538`)|[42764805517](https://github.com/bridge2ai/data-sheets-schema/actions/runs/42764805517) `queued` (`3` done, `15` cancelled: `11` started + `4` unstarted; `test` queued)|`05:52:16Z`|`27–949s` (`14` started `05:52:43Z–06:08:05Z`)|`290–603s` (`3` done; `15` cancelled `06:10:56–06:11:14Z`)|
|`#5711` (`3ae8bd672`)|[42766780586](https://github.com/bridge2ai/data-sheets-schema/actions/runs/42766780586) `pending` (`0` jobs at `06:18Z`; large-files [42766780319](https://github.com/bridge2ai/data-sheets-schema/actions/runs/42766780319) `36s`)|`06:10:55Z`|Unavailable at `06:18Z` (`>459s`)|Unavailable at `06:18Z` (later root readback: `2` running/`16` queued)|

## 3. Docs-Only `3ae8bd672`, Uncertainty & Recommendation
- **Full suite triggered**: Yes (`42766780586` at `06:10:55Z`). Inferred mechanism: it cancelled `42764805517` (`11` running, `4` unstarted), freeing runners for `#5665`, while `42764805517`'s `test` job (`06:11:14Z`) held the `#5711` concurrency lock until a runner cleared it.
- **Uncertainty**: Unstarted/queued jobs report placeholder timestamps (`started_at == created_at`, `runner_id == 0`); `#5709`, `#5665`, and `#5711` remain incomplete.
- **Recommendation**: Batch non-urgent checkpoint pushes on docs PR `#5711` while code PRs (`#5665`, `#5709`) run CI.

# AGY2 Read-Only Sizing: Ordinary Shard-Count Option (`8/6` vs `10/6`, `10/8`, `12/8`)

- **Assignment**: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/notes/development_efficiency_20261111/assignments/claude-lead-agy2-shard-count-option.md`
- **Role**: `AGY2` (read-only analysis; no source edits, test runs, or network fetches)
- **Evaluated checkout**: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/claude-pr5808-combined-20261111` (`b8803c228024ce40275e9f31d81c182441be29ff`)
- **Saved CI evidence**:
  - PR run `42947560899`: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/tmp/ci-observed-42947560899/run.json`, `shard8.log`, `post_ci_analysis_corrected.json`, and `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy-ci-timing-refresh-20261111/tmp/run-42947560899/jobs.json`
  - `main` run `42953302794`: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/tmp/ci-main-42953302794/run-raw.json` and `run.json`

---

## 1. Concurrency (`PR 42947560899` and `main 42953302794`)

### Observed Job Starts, Delays, Queueing, and Peak Concurrency

| Metric | PR Run `42947560899` (`pull_request`) | `main` Run `42953302794` (`push` to `main`) |
| --- | --- | --- |
| **Saved evidence files** | `tmp/ci-observed-42947560899/run.json`, `tmp/run-42947560899/jobs.json` | `tmp/ci-main-42953302794/run-raw.json`, `tmp/ci-main-42953302794/run.json` |
| **Run creation / start** | Run `startedAt = 2026-11-11T02:39:56Z`; all 18 initial jobs `created_at = 02:39:57Z` (`+1s`) | Run `createdAt = startedAt = 2026-11-11T03:31:20Z` |
| **Total workflow jobs** | **20** (`19` executed + `1` skipped `schema-examples`) | **18** (`18` executed, `0` skipped) |
| **Initial parallel jobs started** | **18** (`8` ordinary shards + `4` `API case` + `3` `SG2 case` + `3` offline suites) | **17** (`6` ordinary shards + `4` `API case` + `3` `SG2 case` + `3` offline suites + `1` `schema-examples (3.12)`) |
| **Start time relative to run creation/start** | **3 jobs** (`API case routing-regate`, `API case routing-dispatch`, `shard 6`) started at `02:39:58Z` (**`+2s`** after `startedAt`, **`+1s`** after job `created_at`); **15 jobs** started at `02:39:59Z` (**`+3s`** after `startedAt`, **`+2s`** after job `created_at`). `schema-examples` was marked skipped at `02:40:03Z` (`+7s`). Final `test` gate (`needs` all 19 jobs) was created at `03:13:08Z` (`+1s` after `shard 8` completed at `03:13:07Z`) and started at `03:13:09Z` (`+1993s`). | **1 job** (`offline audit and finalization`) started at `03:31:22Z` (**`+2s`** after `createdAt`); **16 jobs** started at `03:31:23Z` (**`+3s`** after `createdAt`). Final `test` gate was created/started at `04:17:44Z` (`+2784s`, **`+2s`** after `shard 6` completed at `04:17:42Z`). |
| **Jobs queued?** | **None (`0` jobs queued)** — every eligible initial job acquired a runner within `1–2s` of job creation (`2–3s` of run start). | **None (`0` jobs queued)** — every initial job acquired a runner within `2–3s` of `createdAt`. |
| **Peak concurrent jobs in `main.yaml`** | **18** (from `02:39:59Z` to `02:44:53Z`, `4m54s`, until `offline evaluation` finished first). | **17** (from `03:31:23Z` to `03:33:29Z`, `2m06s`, until `schema-examples (3.12)` finished first; then **16** until `03:36:14Z` when `offline evaluation` finished). |
| **Other workflows triggered by same event** | `.github/workflows/large-files.yaml:4-15` runs `1` job (`Check added or modified files`, `~36s`) on `pull_request` and `push`, bringing peak concurrent jobs on a PR push to **19**. | `.github/workflows/large-files.yaml` (`1` job on `push`) and `.github/workflows/deploy-docs.yaml` (on `main` pushes touching docs/schema) add **1–2** short concurrent jobs (`18–19` total). |

### Account Concurrent-Job Limit and Queueing Thresholds

- **Exact billing-plan cap**: **unverified** (no GitHub billing API snapshot or organization plan tier is committed in the repository).
- **What repository notes record empirically**:
  1. `notes/ci_efficiency_review_2026-09-15.md:88`: *"Six for every interpreter created 21 concurrent jobs and filled the observed 20-runner pool (#1872), queueing the entire PR check; that experiment was stopped."*
  2. `notes/reviews/ci_queue_checkpoint_2026-11-10.md:6-7, 17-18`: *"Concurrency limit: ~20 concurrent jobs (inferred from active counts, not observed cap)"* — at `06:18Z` on `2026-11-10`, PR `#5709` had `5` jobs running and PR `#5665` had `15` running + `2` queued (`20` running total across the `bridge2ai` organization).
  3. `notes/coordination/STATUS.md:526-531` (`D81`): *"Main and manual runs use six Python 3.12 ordinary shards and keep schema-examples; PR runs use eight shards (`main.yaml`, 18 concurrent Python jobs on PRs and 17 on main/manual, plus the aggregate test job)."*
- **Fixed non-shard concurrency per run**:
  - **PR run**: `10` fixed `main.yaml` Python jobs (`4` `API case` + `3` `SG2 case` + `3` offline suites) + `1` `large-files.yaml` job during the first `~36s` = **$10 + S_{\text{PR}}$ in `main.yaml` ($11 + S_{\text{PR}}$ across workflows at `t = 0..36s`)**.
  - **`main` push run**: `11` fixed `main.yaml` jobs (`10` Python suites + `1` `schema-examples` running for `~2m06s`) + `1` `large-files.yaml` job (`~36s`) = **$11 + S_{\text{main}}$ in `main.yaml` ($12 + S_{\text{main}}$ across workflows at `t = 0..36s`)**.
- **What shard count starts to queue under each plausible account concurrency limit** (assuming zero other concurrent workflow runs in the `bridge2ai` org):
  - **Cap = 20 concurrent jobs** (GitHub Free / standard public-repo 20-runner pool observed in `#1872` and `ci_queue_checkpoint_2026-11-10.md`):
    - **Single isolated PR run**: queues at **$S_{\text{PR}} \ge 10$** (`10` shards + `10` fixed Python jobs = `20` in `main.yaml`, plus `1` `large-files` job = **`21` jobs**, queueing 1 job for `~36s`; at **$S_{\text{PR}} = 11$**, `main.yaml` alone is `21` jobs, queueing 1 shard for `~4m54s` until `offline evaluation` finishes; at **$S_{\text{PR}} = 12$**, `22` `main.yaml` jobs + `1` `large-files` = **`23` jobs**, queueing 2 shards for `~4m54s` until `offline evaluation` finishes).
    - **Single isolated `main` run**: queues at **$S_{\text{main}} \ge 9$** in `main.yaml` alone (`11 + 9 = 20`), or at **$S_{\text{main}} = 8$** during the first `~36s` when `large-files` (+ `deploy-docs`) also run (`11 + 8 + 1 = 20–21` jobs; `schema-examples` frees 1 slot after `~2m06s`).
    - **Any two overlapping runs** (e.g., 1 PR + 1 `main` run, or 2 PR runs): **already queues at `8/6`** (`18 + 17 = 35 > 20`); increasing `8/6` to `10/8` or `12/8` adds `2–4` more queued jobs per active run.
  - **Cap = 40 concurrent jobs** (GitHub Pro / Team standard Linux tier):
    - A single isolated PR or `main` run does not queue until **$S_{\text{PR}} \ge 30$** (`40` jobs in `main.yaml`).
    - **Two concurrent PR runs** fit without queueing at `S_PR = 8` (`2 × 19 = 38 <= 40`), sit right at the ceiling at **`S_PR = 10` (`2 × 20 = 40` in `main.yaml`, `42` with `large-files`)**, and queue `4–6` jobs for `~4m54s` at **`S_PR = 12` (`2 × 22 = 44 > 40`)**.
  - **Cap = 60 concurrent jobs** (GitHub Team higher pool / Enterprise standard):
    - Single and dual runs do not queue at `8`, `10`, or `12`; **three concurrent PR runs** fit at `S_PR = 8` (`3 × 19 = 57 <= 60`), hit the ceiling at **`S_PR = 10` (`3 × 20 = 60` in `main.yaml`, `63` with `large-files`)**, and queue `6–9` jobs at **`S_PR = 12` (`3 × 22 = 66 > 60`)**.

---

## 2. What Pins `8` and `6` (Exact File and Line Inventory)

### A. Workflow Configuration and Gates
1. **`.github/workflows/main.yaml:2-3`** (header comment):
   - `# CI uses Python 3.12 throughout. D81 selects eight PR shards and six on` / `# main/manual without removing test or schema coverage.`
2. **`.github/workflows/main.yaml:29`** (`python-tests` matrix shard list):
   - `shard: ${{ fromJSON(github.event_name == 'pull_request' && '[1, 2, 3, 4, 5, 6, 7, 8]' || '[1, 2, 3, 4, 5, 6]') }}`
   - Must change to `'[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]'` (or `1..12`) for PRs and `'[1, 2, 3, 4, 5, 6, 7, 8]'` for `main`/manual if `main` also changes.
3. **`.github/workflows/main.yaml:59`** (`python-tests` Step 5 `--ci-shard` denominator):
   - `-p utils.pytest_shard --ci-shard=${{ matrix.shard }}/${{ github.event_name == 'pull_request' && 8 || 6 }}`
   - Must match line 29 (`10` or `12` on `pull_request`; `6` or `8` on `main`/manual).
4. **`.github/workflows/main.yaml:354-381`** (aggregate `test` gate job):
   - **Does NOT pin `8` or `6`**. Line `356` lists `needs: [python-tests, api-completion, sg2-completion, offline-canary, offline-audit, offline-evaluation, schema-examples]` and line `362` binds `PYTHON_RESULT: ${{ needs.python-tests.result }}`, which aggregates any matrix size automatically.

### B. Automated Tests That Pin `8` and `6`
1. **`tests/test_ci_sharding.py:41-42, 59`** (`_assert_complete_partition` synthetic fixture):
   - Line `41`: `# Twenty-one files populate every hash bucket at both D81 partition sizes.`
   - Line `42`: `for number in range(21):` (and line `59`: `assert sum(expected.values()) == (97 if lanes else 84)`).
   - **Critical test behavior by shard count**:
     - For `total = 6`, `8`, and `10`, the 21 synthetic filenames (`test_0.py` .. `20_test.py`) populate all `total` SHA-256 hash buckets in `shard_for()` (`utils/pytest_shard.py:164-166`), so `weighted=False` passes without changing `range(21)`.
     - For **`total = 12`**, **hash bucket `2` is empty (`0` of the 21 files hash to `2 mod 12 + 1`)**! Under `weighted=False`, shard `2/12` exits with pytest status `5` (`NO_TESTS_COLLECTED`) and fails `assert result.returncode == 0` at `tests/test_ci_sharding.py:75` unless the fixture loop at line `42` (and expected case total at line `59`) is increased to at least `26` files.
2. **`tests/test_ci_sharding.py:93-95`** (`test_shards_cover_the_real_collection_exactly_once_with_xdist`):
   - Line `94`: `_assert_complete_partition(tmp_path, weighted, 8)` — pins the PR shard count `8`.
3. **`tests/test_ci_sharding.py:98-100`** (`test_main_shards_retain_the_same_complete_collection`):
   - Line `99`: `_assert_complete_partition(tmp_path, weighted, 6)` — pins the `main` shard count `6`.
4. **`tests/test_ci_sharding.py:140-150`** (`test_measured_partition_is_order_independent_and_reduces_estimated_imbalance`):
   - Lines `142, 143, 145, 147`: hardcodes `8` in `balanced_files(weights, 8, weights)`, `balanced_files(reversed(list(weights)), 8, weights)`, `[0.0] * 8`, and `shard_for(path, 8)`.
   - Line `150`: `assert max(balanced) / min(balanced) < 1.05`.
   - **Critical test behavior by shard count**:
     - At `total = 8`, `max(balanced) / min(balanced) = 1.0000` (`< 1.05`).
     - At `total = 10`, `max(balanced) / min(balanced) = 5162.752 / 5106.288 = 1.0111` (`< 1.05`, passes).
     - At **`total = 12`**, **`max(balanced) / min(balanced) = 5162.752 / 4177.848 = 1.2357` (`>= 1.05`, FAILS)** because the single file `tests/test_report_admission.py` (`5,162.752s`) is heavier than the 12-shard mean (`4,259.9s`) and sits alone in Shard 1 while the remaining 675 files divide into `4,177.8s` shards.
5. **`tests/test_ci_sharding.py:294-297`** (`test_explicit_lanes_and_real_shards_equal_full_default_collection`):
   - Line `294`: `pytest.mark.parametrize("total", [6, 8])` — pins `[6, 8]`. (Note: each parameter value spawns `2 × total + 7` pytest subprocesses; changing `[6, 8]` to `[8, 10]` adds `+4` subprocess invocations per `weighted` mode = `+8` subprocesses in this test.)
6. **`tests/test_ci_sharding.py:402-404`** (`test_case_workflow_binds_all_lanes_and_retains_budget_setup_and_evidence`):
   - Line `402-403`: asserts `jobs["python-tests"]["strategy"]["matrix"]["shard"] == "${{ fromJSON(github.event_name == 'pull_request' && '[1, 2, 3, 4, 5, 6, 7, 8]' || '[1, 2, 3, 4, 5, 6]') }}"`.
   - Line `404`: asserts `"--ci-shard=${{ matrix.shard }}/${{ github.event_name == 'pull_request' && 8 || 6 }}" in ordinary`.

### C. Documentation and Timing / Analysis Helpers
1. **`.github/workflows/README.md:50-57`**:
   - Lines `51-52`: `eight shards for PRs, six for main/manual runs (D81)`.
   - Line `56`: `There are 18 Python jobs on PRs and 17 on main/manual runs, plus the aggregate test job.`
2. **`utils/ci_sharding.md:3-5, 11-12, 191-194, 209-210`**:
   - Lines `3-5`: `on eight Python 3.12 shards. Main and manual runs use six Python 3.12 shards (D81)`.
   - Lines `11-12`: `There are eighteen Python jobs on PRs and seventeen on main/manual runs, plus the aggregate test job.`
   - Lines `191-194`: `PRs have nineteen required successes plus the expected schema/example skip; main/manual have eighteen successes (D81). Across PR, manual and the separate large-files check this is thirty-eight required successes and one expected skip`.
   - Lines `209-210`: `D81's 8/6 ordinary shards and D75's 45/60-minute limits are unchanged.`
3. **`utils/update_ci_shard_timings.py:12-61`** (production timing refresh builder):
   - **Does NOT pin `8` or `6`**. Line `21` discovers artifacts via `files = sorted(results.rglob("pytest.xml"))`, accepting any positive number of shard XMLs as long as they partition the collected cases disjointly.
4. **`tests/test_ci_timing_update.py:170-204`**:
   - Lines `177-186` (`expected_artifacts`) pin the 8 historical artifact IDs and SHA-256 digests of **completed run `42916359440`** inside `source.ci_refresh_42916359440_20261111`. Changing the workflow shard count for future runs does **not** break this test unless `source.ci_refresh_42916359440_20261111` itself is overwritten.
5. **Run-specific adhoc scripts (`scripts/adhoc/`)**:
   - `scripts/adhoc/refresh_ci_timings_42916359440_20261111.py:57-66, 205, 214, 323-348` (`EXPECTED_ORDINARY_ARTIFACT_IDS` for `shard1..shard8`, `len(built_artifacts_by_path) != 8`, `range(1, 9)`, and `_evaluate_partition` calls at `8` and `6`) and `scripts/adhoc/analyze_ci_run_42947560899_20261111.py:68, 81` (`range(1, 9)`) are pinned to historical 8-shard runs `42916359440` and `42947560899` by name and purpose; they are not invoked by CI or `pytest`, though any future refresh/analysis script for a 10- or 12-shard run would loop over `1..N`.

---

## 3. Cost per Added Shard (From Saved Step and Log Timings)

### Step-Level Breakdown of Non-Test Overhead per Ordinary Shard
From `tmp/ci-observed-42947560899/run.json` (`8` PR shards) and `tmp/ci-main-42953302794/run-raw.json` (`6` `main` shards):

| Step # | Step Name | PR `42947560899` (8 shards) | `main` `42953302794` (6 shards) |
| --- | --- | --- | --- |
| 1 | `Set up job` | `1–2s` (mean `1.4s`) | `1–2s` (mean `1.3s`) |
| 2 | `Check out repository` | `5–6s` (mean `5.6s`) | `5–8s` (mean `6.2s`) |
| 3 | `Initialise the FAIRSCAPE models submodule` | `1–2s` (mean `1.4s`) | `1–3s` (mean `1.5s`) |
| 4 | `Set up the cached project environment` | `11–18s` (mean `14.1s`) | `12–16s` (mean `13.5s`) |
| 6 | `Require the suite to leave notes/, tests/ and utils/ untouched` | `0s` | `0–1s` (mean `0.2s`) |
| 7 | `Preserve test results and per-test timings` (`upload-artifact`) | `1–2s` (mean `1.6s`) | `1–2s` (mean `1.3s`) |
| 8–11 | `Post` cleanup steps (env, checkout, `Complete job`) | `1–3s` (mean `1.9s`) | `1–2s` (mean `1.7s`) |
| — | **Total outside Step 5 (`job_seconds - step5_seconds`)** | **`23–33s` (mean `29.0s`, explicit step sum `26.0s`)** | **`24–34s` (mean `28.2s`, explicit step sum `25.7s`)** |

### Collection Overhead Inside Step 5 (`Run the suite shard including corpus checks`)
From `tmp/ci-observed-42947560899/shard8.log:354-377`:
- Step 5 launched at `02:40:27.771Z` (`shard8.log:354`).
- `pytest` printed its session header at `02:40:32.987Z` (`+5.22s` for `poetry run python -m pytest` startup and plugin import, `shard8.log:366`).
- Four `xdist` workers (`gw0..gw3`) spawned (`02:40:35.060Z`, `shard8.log:374`) and **each of the 4 workers independently imported and collected the entire repository `tests/` tree (`23,277` items across `676` files)** before `pytest_collection_modifyitems` (`utils/pytest_shard.py:170-202`) deselected items not owned by that shard (`shard8.log:376`).
- The first test (`tests/test_bc1_g2_journal.py::test_every_bc1_response_is_journaled_before_parse`) was dispatched at `02:41:37.026Z` (`shard8.log:377`) — **`69.26s` after Step 5 started** (`5.22s` Poetry/interpreter startup + **`64.04s` 4-worker full-tree collection**).
- **Does the 4-worker full-tree collection (`~69s` Step-5 pre-test phase) get paid again per added shard?**
  - **Yes, 100% of it is paid again in every added shard.** Because `.github/workflows/main.yaml:58-60` passes `tests` (the full directory) to `pytest` and filters inside `pytest_collection_modifyitems` after collection completes, every new shard spawns 4 `xdist` workers that collect all `23,277` items from scratch.
- **Net added runner time per extra shard**:
  - Because the total test execution work ($\sum \text{case\_seconds}$) is partitioned disjointly across shards rather than duplicated, each extra shard adds its fixed non-Step-5 overhead (`~28.6s`) plus its Step-5 startup and 4-worker full-tree collection (`~69.3s`) = **`~97.9s` (`~1.63 runner minutes`) of fixed overhead per added shard** (plus `~15–20s` of 4-worker tail-drain idle time at the end of the shard, or **`~1.6–2.0 runner minutes` per added shard**: **`+3.3 to +3.9 runner minutes` for `+2` shards**, **`+6.5 to +7.8 runner minutes` for `+4` shards**).

---

## 4. Does the Timing File Still Work? (`utils/ci_test_durations.json`)

- **Yes — `utils/ci_test_durations.json` and `utils/update_ci_shard_timings.py` work unchanged at `6`, `8`, `10`, `12`, or any shard count $N \ge 1$.**
  1. **Schema and weights (`utils/ci_test_durations.json`, `utils/pytest_shard.py:118-141`)**:
     - `read_weights()` reads only `data["schema_version"] == 1` (`line 128-130`) and `data["file_seconds"]` (`line 131-139`), which maps each repository test file path (`676` files, e.g. `"tests/test_report_admission.py": 5162.752`) to its summed JUnit case-seconds. Nothing in `file_seconds` is keyed by shard index or shard count.
  2. **Partitioner (`utils/pytest_shard.py:144-161`)**:
     - `balanced_files(paths, total, weights)` takes `total` dynamically from `--ci-shard=index/total` (`line 184-187`), initializes `loads, counts = [0.0] * total, [0] * total` (`line 154`), and greedily assigns each collected file (sorted by `(-estimates[path], path)`) to the least-loaded shard `min(range(total), key=lambda index: (loads[index], counts[index], index))` (`line 156-160`).
  3. **Refresh builder (`utils/update_ci_shard_timings.py:12-61`)**:
     - `build(results, root, run_id, commit)` discovers all `pytest.xml` files under `results` via `files = sorted(results.rglob("pytest.xml"))` (`line 21`), verifies no testcase `(classname, name)` appears in more than one XML artifact (`line 37-39`), and sums testcase durations by repository file (`line 44-51`). It has no hardcoded `8` or `6`.
  4. **Historical provenance metadata (`tests/test_ci_timing_update.py:170-204`)**:
     - The extra `source.ci_refresh_42916359440_20261111` provenance object inside `utils/ci_test_durations.json` records the 8 artifacts of historical run `42916359440` (`tests-py3.12-shard1` .. `shard8`), which `read_weights()` ignores.
- **One structural limitation of whole-file weights at $N \ge 10$**:
  - While the file format works for any $N$, the largest single entry in `file_seconds` is `tests/test_report_admission.py` at **`5,162.752s`** (out of `51,119.345s` total across all 676 files, or `10.10%` of the entire ordinary suite).
  - Consequently, for any **$N \ge 10$** (where the mean planned shard weight is $\le 5,111.9\text{s}$), `balanced_files()` places `tests/test_report_admission.py` **alone in Shard 1 (`5,162.8s`)**, and **increasing $N$ beyond `10` (e.g. to `12`) cannot remove a single testcase from Shard 1**.

---

## 5. Limits and Headroom Under `D75` (`45 min` PR, `60 min` `main`)

### Justifying a Pessimistic Runner Factor from Saved Runs
1. **Observed slowest-runner factor in PR run `42947560899`: `1.17x`**
   - In `42947560899`, every shard was assigned `6,389.2s` of baseline `42916359440` case-seconds. Shard 8 recorded `7,492.5s` of actual case-seconds (`7492.5 / 6389.2 = 1.1727x`, or `7434 / 6389 = 1.164x` on the 674-file replay subset) and `33m08s` (`1,988s`) job wall vs `28m25s` (`1,705s`) on `1.00x` Shard 1 (`1988 / 1705 = 1.166x`).
2. **Observed slowest-runner factor in `main` run `42953302794`: `1.20x`**
   - In `42953302794` (`6` shards, each with `8,518.9s` of baseline `42916359440` case-seconds), Shards 2, 3, and 4 ran at `0.96x–0.99x` of baseline (`37m12s–38m33s` job wall; `2,200s–2,286s` Step 5), whereas **Shard 6 ran for `46m19s` (`2,779s` job wall, `2,752s` Step 5)** — an implied case-second multiplier of **`1.203x`** over baseline (`(2752 - 69) × 3.82 / 8518.9 = 1.203`, and `2779 / 2313 = 1.201x` relative to `0.99x` Shard 2). Notably, **`46.3 min` in `42953302794` already exceeded the `42.7 min` 6-shard replay estimate by `+3.6 min` (`1.085x` of the replay wall) and exceeded the `45 min` PR limit by `+1.3 min`**.
3. **Justified pessimistic factor: `1.31x` over baseline (or `1.17x` applied on top of the replay table)**
   - Within `42947560899`, the two heaviest multi-case files driving tail risk inflated by **`1.260x`** (`tests/test_download/test_api_runner.py`: `3,200.6s / 2,539.5s` on Shard 4) and **`1.308x`** (`tests/test_bc1_g2_journal.py`: `1,389.6s / 1,062.1s` on Shard 8) relative to `42916359440`. If a shard dominated by one heavy file (`tests/test_report_admission.py` at `5,162.8s` in Shard 1 for `N=10, 12`, or `test_api_runner.py` in Shard 4) lands on a slow runner with that **`1.31x`** file-level slowdown over baseline, or equivalently if the replay table's slowest shard (`25.7 min` at `N=10`, `23.4 min` at `N=12`) is scaled by **`1.17x–1.31x`**, we get the pessimistic wall times below.

### Headroom Table (`D75` Limits: `45.0 min` on PR, `60.0 min` on `main`)
Using the lead's replay formula `wall_min = (slowest_case_s * factor / 3.8 + 100) / 60`, shown both for **(A) scaling the replay table's `Slowest shard (s)` directly** and **(B) scaling the undiluted `42916359440` planned slowest shard (`8,520s` at `6`, `6,390s` at `8`, `5,163s` at `10` and `12`)**:

| Shards ($N$) | Planned Max (s) | Replay Slowest (s) | Replay `1.00x` Wall (Margin vs `45m` PR / `60m` `main`) | Replay `× 1.17` Wall (Margin vs `45m` / `60m`) | Replay `× 1.31` Pessimistic (Margin vs `45m` / `60m`) | Undiluted Planned `× 1.17` / `× 1.20` (`main` S6) / `× 1.31` Wall (Margin vs `45m` / `60m`) |
| --- | --- | --- | --- | --- | --- | --- |
| **`6`** (`main` now) | `8,520s` | `9,351s` | **`42.7m`** (`+2.3m` / **`+17.3m`**) | **`49.7m`** (`-4.7m` / **`+10.3m`**) | **`55.4m`** (`-10.4m` / **`+4.6m`**) | **`45.4m` / `46.6m` (obs `46.3m`) / `50.6m`** (`-0.4m..-5.6m` PR / **`+14.6m..+9.4m` `main`**) |
| **`8`** (PR now, or `main` option) | `6,390s` | `7,434s` *(already `1.17x`)* | **`34.3m`** *(obs `33.1m`)* (**`+10.7m`** / **`+25.7m`**) | **`39.8m`** *(is `1.17²=1.37x` base)* (**`+5.2m`** / **`+20.2m`**) | **`44.4m`** (**`+0.6m`** / **`+15.6m`**) | **`34.5m` / `35.4m` / `38.4m`** (**`+10.5m..+6.6m` PR** / **`+25.5m..+21.6m` `main`**) |
| **`10`** (PR option) | `5,163s` *(Shard 1)* | `5,484s` *(Shard 4, `1.07x`)* | **`25.7m`** (**`+19.3m`** / `+34.3m`) | **`29.8m`** (**`+15.2m`** / `+30.2m`) | **`33.2m`** (**`+11.8m`** / `+26.8m`) | **`28.2m` / `28.9m` / `31.3m`** (**`+16.8m..+13.7m` PR** / `+31.8m..+28.7m` `main`) |
| **`12`** (PR option) | `5,163s` *(Shard 1)* | `4,951s` *(Shard 1, `0.96x`)* | **`23.4m`** (**`+21.6m`** / `+36.6m`) | **`27.1m`** (**`+17.9m`** / `+32.9m`) | **`30.1m`** (**`+14.9m`** / `+29.9m`) | **`28.2m` / `28.9m` / `31.3m`** (**`+16.8m..+13.7m` PR** / `+31.8m..+28.7m` `main`) |

- **Headroom takeaway**:
  - **On PRs (`45.0 min` limit)**: **`10` shards** increases PR margin from **`+10.7 min`** (`8` shards at `1.17x` observed = `34.3m`) to **`+15.2 min`–`+16.8 min`** at `1.17x` (`28.2m–29.8m` wall) and **`+11.8 min`–`+13.7 min`** under the `1.31x` pessimistic factor (`31.3m–33.2m` wall).
  - **On `main` (`60.0 min` limit)**: **`6` shards** currently leaves **`+13.7 min`** against the `60 min` limit in actual run `42953302794` (`46.3m` wall at `1.20x`), and **`+4.6 min`–`+9.4 min`** under the `1.31x` pessimistic factor (`50.6m–55.4m`). Moving `main` to **`8` shards** increases `main` margin to **`+24.6 min`–`+25.7 min`** at `1.17x–1.20x` (`34.3m–35.4m` wall) and **`+15.6 min`–`+21.6 min`** under `1.31x` (`38.4m–44.4m`).

---

## 6. What Makes the Replay Table Misleading?

1. **Runner-Speed Confounding / Dilution Bias Across Shard Counts (Primary Bias)**:
   - In PR run `42947560899`, each file's recorded duration $t_f^{\text{obs}} = w_f \cdot r_{s_8(f)}$ bakes in the speed multiplier $r_{s_8}$ of whichever of the 8 runners executed that file's shard in `42947560899`:
     - Shards 2 and 3 ran on fast runners (**`0.637x`** and **`0.625x`** of `42916359440` baseline weights: `4,067s` and `3,995s` vs `6,389s` planned).
     - Shards 5 and 6 ran on moderately fast runners (**`0.868x`** and **`0.805x`**).
     - Shards 1, 4, and 7 ran on near-baseline runners (**`0.998x`**, **`0.986x`**, **`0.991x`**).
     - Shard 8 ran on a slow runner (**`1.173x`**: `7,492.5s` vs `6,389.2s` planned).
     - Across all 8 shards, the run-wide mean multiplier was **$45,247\text{s} / 51,113\text{s} = 0.885\times$**.
   - When the replay re-partitions files into $N = 6, 10, 12$ shards using `balanced_files(paths, N, weights)`, the greedy partitioner mixes files from different `42947560899` shards:
     - At **$N = 8$**, all `6,389.2s` of Shard 8's files stay together in Shard 8, preserving the full **`1.173x`** slow-runner factor (`7,434s` / `7,492s`).
     - At **$N = 10$**, original Shard 8's files are split across Shards 2–10 (at most `2,705.9s` of planned weight stays in Shard 8 alongside `934.1s` of `0.63x` fast-runner files from Shards 2/3, giving Shard 8 an artificial blended multiplier of `0.986x`!). The replay's slowest shard at $N = 10$ (`Shard 4`, `5,484s` / `5,493s` on `5,105.6s` planned) has an effective multiplier of only **`1.076x`**, **not `1.173x`**.
     - Consequently, the replay makes `8 -> 10` look like a **`-26.2%` drop in slowest-shard case-seconds (`7,434s -> 5,484s`)** when the true reduction in planned work is only **`-19.2%` (`6,389.9s -> 5,162.8s`)**! In a real 10-shard CI run, each shard still executes on a **single** physical runner VM (and drawing 10 VMs instead of 8 slightly *increases* $\mathbb{E}[\max_{1 \le i \le N} R_i]$ rather than diluting it toward `0.885x`). If a `5,106s–5,163s` shard in a 10-shard run lands on the same `1.173x` runner as Shard 8, its case-seconds will be **`5,989s–6,056s` (`~28.2 min` wall)**, not `5,484s` (`25.7 min`).

2. **Single-File Ceiling at $N \ge 10$ (`tests/test_report_admission.py` = `5,162.8s` Planned)**:
   - The replay table suggests moving from `10` to `12` shards reduces the slowest shard from `5,484s` (`25.7 min`) to `4,951s` (`23.4 min`).
   - In reality, **Shard 1 at $N = 10$ and Shard 1 at $N = 12$ are 100% identical**: both contain **only the single file `tests/test_report_admission.py`** (`5,162.752s` planned weight; `4,950.5s` observed on Shard 1's `0.959x` runner in `42947560899`).
   - At $N = 10$, Shard 1 (`5,162.8s`) is already the heaviest planned shard (`57s` heavier than Shards 2–10 at `5,105.6s`); it only appeared faster than Shard 4 (`5,484s`) in the replay because Shard 1's runner in `42947560899` was `0.959x` while Shard 4's `test_api_runner.py` ran at `1.260x`.
   - Therefore, **under whole-file sharding, increasing $N$ from `10` to `12` reduces the maximum planned shard load by `0.0 seconds` (`5,162.8s -> 5,162.8s`)**, while breaking `test_measured_partition_is_order_independent_and_reduces_estimated_imbalance` (`max/min = 1.236 > 1.05`).

3. **Non-Shard Critical-Path Floor (`API case routing-portable` = `31.6 min`)**:
   - In PR run `42947560899`, the dedicated job `Python 3.12 / API case routing-portable` took **`31m38s` (`1,898s`)**, and in `main` run `42953302794` it took **`31m32s` (`1,892s`)**.
   - Even if ordinary shards drop from `33.1 min` (`8` shards) to `25.7–28.2 min` (`10` shards), **total PR workflow wall-clock time cannot drop below `~31.6 min`** (saving at most `~1.5 min` of end-to-end PR wall time) unless `routing-portable` is also shortened or split (while still improving ordinary-shard timeout margin against `45 min`).

4. **Single-Test Floor and 4-Worker Tail Drain (`1,416.6s` and `1,381.2s` Single Cases)**:
   - `tests/test_bc1_pipeline.py::test_public_bc1_pipeline_multiple_groups_final_and_completed_replay` took **`1,416.6s` (`23.6 min`)** on a single worker in Shard 5, and `tests/test_bc1_g2_journal.py::test_every_bc1_response_is_journaled_before_parse` took **`1,381.2s` (`23.0 min`)** on a single worker in Shard 8.
   - Dividing shard case-seconds by `3.8` assumes all 4 workers stay busy throughout the shard. When total shard case-seconds drop toward `3,761s–4,514s` ($N = 12$ or $10$), a single `1,381s–1,417s` test occupies 1 worker for longer than one-fourth of the entire shard (`1,417s > 4,177s / 4 = 1,044s`), causing the other 3 workers to drain early and lowering effective parallelism below `3.8` (`wall >= max_single_case_s + 98s >= 25.2 min`).

---

## 7. Summary Table of Shard-Count Options (`PR / main`)

| Option (`PR / main`) | Expected Slowest-Shard Wall (`PR / main`) | Added Jobs per Run (`PR / main` vs `8/6`) | Added Runner Minutes per Run (`PR / main` vs `8/6`) | What Is Unverified |
| --- | --- | --- | --- | --- |
| **`8 / 6` (current `D81`)** | **PR**: `34.3m` replay (`33.1m` actual in `42947560899`; `29.7m` at `1.00x` plan, `38.4m–44.4m` at `1.31x` pess; **`+10.7m` PR margin** at `1.17x`).<br>**`main`**: `42.7m` replay (`46.3m` actual in `42953302794` at `1.20x`; `50.6m–55.4m` at `1.31x` pess; **`+13.7m` actual `main` margin** vs `60m`). | `+0 / +0`<br>(`18` Python jobs on PR, `19` with `large-files`; `17` on `main`, `18` with `large-files`; plus `test` gate) | `+0.0 / +0.0 min`<br>(Baseline: `211.2m` across 8 PR shards in `42947560899`; `224.5m` across 6 `main` shards in `42953302794`) | Exact org billing concurrency cap; tail risk if a `6`-shard `main` run or `8`-shard PR run hits a `>1.35x` runner slowdown + file inflation simultaneously. |
| **`10 / 6`** | **PR**: `25.7m` replay (`28.2m–29.8m` at undiluted `1.17x` slow runner; `31.3m–33.2m` at `1.31x` pess; **`+15.2m..+16.8m` PR margin** at `1.17x`).<br>**`main`**: `42.7m` replay (`46.3m` actual in `42953302794`; **`+13.7m` actual `main` margin** vs `60m`). | **`+2 / +0`**<br>(`20` Python jobs on PR, **`21` with `large-files`**; `17` on `main`) | **`+3.3 to +3.9 min` on PR / `+0.0 min` on `main`**<br>(`2 × ~98s` fixed setup + 4-worker full-tree collection overhead per PR run) | Whether the `bridge2ai` org cap is `20` jobs (if `20`, the `21st` job on a PR push with `large-files` queues for `~36s`, and any overlapping run queues `+2` extra jobs); actual CI wall time of single-file Shard 1 (`test_report_admission.py`, `5,162.8s`). |
| **`10 / 8`** | **PR**: `25.7m` replay (`28.2m–29.8m` at `1.17x`; `31.3m–33.2m` at `1.31x` pess; **`+15.2m..+16.8m` PR margin** vs `45m`).<br>**`main`**: `34.3m` replay (`34.5m–35.4m` at `1.17x–1.20x`; `38.4m–44.4m` at `1.31x` pess; **`+24.6m..+25.7m` `main` margin** vs `60m`). | **`+2 / +2`**<br>(`20` Python jobs on PR, `21` with `large-files`; `19` on `main`, **`20–21` with `large-files`/docs**) | **`+3.3 to +3.9 min` on PR / `+3.3 to +3.9 min` on `main`**<br>(`2 × ~98s` fixed setup + collection overhead on both PR and `main`) | Same `20`-job org-pool question on both PR (`20–21` jobs) and `main` (`19–21` jobs); extra `+8` subprocesses in `tests/test_ci_sharding.py:294` if parametrized at `[8, 10]`. |
| **`12 / 8`** | **PR**: `23.4m` replay on Shard 1, **but `28.2m` at `1.17x` and `31.3m` at `1.31x` — identical to `10` shards** because Shard 1 (`test_report_admission.py`, `5,162.8s`) cannot split across whole-file shards.<br>**`main`**: `34.3m` replay (`34.5m–35.4m` at `1.17x–1.20x`; **`+24.6m..+25.7m` `main` margin** vs `60m`). | **`+4 / +2`**<br>(`22` Python jobs on PR, **`23` with `large-files`**; `19` on `main`, `20–21` with `large-files`/docs) | **`+6.5 to +7.8 min` on PR / `+3.3 to +3.9 min` on `main`**<br>(`4 × ~98s` fixed overhead on PRs for **zero reduction in max planned shard weight** vs `10` shards) | Under a `20`-job org cap, `22–23` PR jobs **always queue `2–3` jobs for `~4m54s`** (until `offline evaluation` finishes), erasing the nominal `2.3m` replay gain; also breaks `tests/test_ci_sharding.py:75` (empty hash bucket `2/12` for 21 files) and `tests/test_ci_sharding.py:150` (`max/min = 1.236 > 1.05`). |

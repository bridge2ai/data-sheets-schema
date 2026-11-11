# Handoff: `agy1` Post-CI Observation (`run 42947560899` vs. `42916359440` Replay)

- **Work Unit**: `E2` — CI timing refresh (read-only post-CI follow-up; updated for `#5824`, `#5831`, `#5832`)
- **PR / Commit**: PR `#5814` (`head_sha: 95b9e6b16babd1eb72a4074c73003da5cdb0d7e5`); `agy1` worktree frozen at `e42825f9f801f98018a1412a38e414192e8e1bb9` (unpushed)
- **Observed Run**: GitHub Actions run `42947560899` (`SUCCESS`, `2026-11-11T02:39:56Z` to `2026-11-11T03:13:13Z` = **`33m17s`**, vs. reference run `42916359440` at **`36m37s`**, `3m20s` shorter in this two-run comparison)
- **Saved Evidence & Provenance Helper Paths**:
  - Lead-saved run metadata and Shard 8 log:
    - `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/tmp/ci-observed-42947560899/run.json` (`37,703` bytes)
    - `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/tmp/ci-observed-42947560899/shard8.log` (`1,324,412` bytes)
  - Analysis helper scripts:
    - Lead evidence branch path (`codex/development-efficiency-evidence-20261111`): `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/scripts/adhoc/analyze_ci_run_42947560899_20261111.py` (updated for `#5831` explicit dedicated execution-step selection and JUnit header assertion)
    - Prior frozen-worktree copy: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy-ci-timing-refresh-20261111/scripts/adhoc/analyze_ci_run_42947560899_20261111.py`
  - Per-shard JUnit XML comparison outputs (gitignored):
    - Corrected output (`#5831` / `#5832`): `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/tmp/ci-observed-42947560899/post_ci_analysis_corrected.json`
    - Preserved original output: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy-ci-timing-refresh-20261111/tmp/run-42947560899/post_ci_analysis.json`

---

## 1. Ordinary Shards & Dedicated Lanes (`run 42947560899` Actual vs. Refreshed Replay)

Under the refreshed `utils/ci_test_durations.json` (`source_run_id: 42916359440`), `utils/pytest_shard.py` balanced all 8 ordinary shards across the **674** active `main` test files (`23,265` total JUnit testcases) to within **`0.004` replayed case-seconds** (`6389.168s` to `6389.172s`).

| Ordinary Shard | Job ID | Job Wall | Step 5 (`Run the suite shard...`) | Pytest Wall (`testsuite`) | Files | Cases | Replayed Case-s (`42916359440`) | Actual Case-s (`42947560899`) | Case-s Delta | Overlapping Case-s / Suite Wall (`actual_case_s / suite_wall_s`) | Slowest Single Case in Shard (`pytest.xml` total) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `shard 1` | `130283922721` | `28m25s` (`1705s`) | `27m53s` (`1673s`) | `27m49s` (`1669.12s`) | 78 | 2738 | `6389.171s` | `6373.588s` | `-15.583s` (`-0.2%`) | `3.819` | `743.04s` (`test_report_admission.py::test_chorus_wire_is_byte_identical...`) |
| `shard 2` | `130283922934` | `18m18s` (`1098s`) | `17m55s` (`1075s`) | `17m52s` (`1071.77s`) | 84 | 2753 | `6389.172s` | `4067.083s` | `-2322.089s` (`-36.3%`) | `3.795` | `294.16s` (`test_d42_claude_d55.py::test_g_shared_full_phase_retry...`) |
| `shard 3` | `130283922871` | `18m04s` (`1084s`) | `17m38s` (`1058s`) | `17m34s` (`1053.90s`) | 84 | 2460 | `6389.168s` | `3995.222s` | `-2393.946s` (`-37.5%`) | `3.791` | `717.81s` (`test_shared_generation_runtime.py::test_real_complete_api_pipeline...`) |
| `shard 4` | `130283922766` | `27m53s` (`1673s`) | `27m22s` (`1642s`) | `27m17s` (`1636.96s`) | 85 | 3064 | `6389.171s` | `6299.508s` | `-89.663s` (`-1.4%`) | `3.848` | `681.88s` (`test_download/test_api_runner.py::test_missing_corrupt_or_stale...`) |
| `shard 5` | `130283922783` | `25m34s` (`1534s`) | `25m03s` (`1503s`) | `24m58s` (`1497.91s`) | 85 | 3217 | `6389.169s` | `5543.962s` | `-845.207s` (`-13.2%`) | `3.701` | `1416.55s` (`test_bc1_pipeline.py::test_public_bc1_pipeline_multiple_groups...`) |
| `shard 6` | `130283922684` | `22m54s` (`1374s`) | `22m27s` (`1347s`) | `22m23s` (`1343.32s`) | 86 | 2965 | `6389.171s` | `5141.534s` | `-1247.637s` (`-19.5%`) | `3.827` | `148.02s` (`test_generation_specificity_skill.py::test_violations_are_exit_1`) |
| `shard 7` | `130283922714` | `28m17s` (`1697s`) | `27m46s` (`1666s`) | `27m41s` (`1661.01s`) | 86 | 2911 | `6389.171s` | `6333.654s` | `-55.517s` (`-0.9%`) | `3.813` | `781.87s` (`test_d69_artifact_completeness.py::test_every_emitted_artifact...`) |
| `shard 8` | `130283922622` | `33m08s` (`1988s`) | `32m35s` (`1955s`) | `32m30s` (`1949.74s`) | 86 | 3157 | `6389.172s` | `7492.495s` | `+1103.323s` (`+17.3%`) | `3.843` | `1381.15s` (`test_bc1_g2_journal.py::test_every_bc1_response_is_journaled...`) |

- **Dedicated lanes (`#5831` explicit execution-step durations)**:
  - **Longest dedicated lane**: `Python 3.12 / API case routing-portable` (`job 130283922669`) ran in **`31m38s` (`1898s`)** job wall time, with execution **step 5 (`Run the required offline API case`) taking `30m58s` (`1858s`**, `2026-11-11T02:40:34Z` to `2026-11-11T03:11:32Z`).
  - **Remaining 9 dedicated lanes**: Job wall times spanned `4m54s` (`294s`) to `15m32s` (`932s`), with explicit execution-step durations spanning **`4m19s` (`259s`)** (`offline evaluation` step 5 `Exercise registered evaluation controls offline`) to **`14m59s` (`899s`)** (`SG2 case sg2-explicit` step 5 `Run the required offline SG2 case`); `offline canary controls` (`job 130283922479`, `13m38s` / `818s` job wall) ran two sequential execution steps totaling **`13m06s` (`786s`)**: step 5 `Exercise experimental canary admission offline` (`0m17s` / `17s`) + step 6 `Exercise native canary transport and shutdown offline` (`12m49s` / `769s`).

---

## 2. Shard 8 (`job 130283922622`) Slowest-25 Table & File Deltas

From `shard8.log:6732-6758` (`3156 passed, 1 skipped, 81 warnings in 1949.78s (0:32:29)`), the 25 slowest call durations in Shard 8 belong to **5 test files**:

1. **`tests/test_bc1_g2_journal.py`** (4 cases; `1062.111s` replayed -> **`1423.920s` actual**, **`+361.809s` / `+34.1%`**):
   - `#1`: `test_every_bc1_response_is_journaled_before_parse` — **`1361.09s` call** (`1381.153s` total in `pytest.xml`). In `shard8.log`, its start line was logged at `2026-11-11T02:41:37.0290069Z` (`shard8.log:378`), its `PASSED` line on `[gw1]` was logged at `2026-11-11T03:04:38.1740438Z` (`shard8.log:743`, `23m01.15s` after start), and the Shard 8 pytest summary finished at `2026-11-11T03:13:02.7538060Z` (`shard8.log:6758`, **`8m24.58s` / `504.58s`** after `test_every_bc1_response_is_journaled_before_parse` logged `PASSED`).
2. **`tests/test_native_execution.py`** (73 cases; `1402.260s` replayed -> **`1899.441s` actual**, **`+497.181s` / `+35.5%`**):
   - Holds **13 of the top 25** slowest calls in Shard 8 (`shard8.log:6735-6749`), spanning `79.27s` to `132.15s` each:
     - `test_actual_closed_consumer_real_helpers_complete[no_correction]` (`132.15s`),
     - `test_cleanup_capture_and_saved_consistency[none]` (`118.73s`),
     - `test_actual_closed_consumer_real_helpers_complete[correction]` (`115.90s`),
     - `test_keep_awake_actual_consumer_lifecycle_uses_only_fake_iokit[none]` (`115.02s`),
     - `test_real_callback_and_usage_failures_stay_failed[unknown_usage]` (`114.13s`),
     - `test_keep_awake_actual_consumer_lifecycle_uses_only_fake_iokit[release]` (`113.47s`),
     - `test_runtime_observation_capture_and_saved_consistency[False]` (`113.41s`),
     - `test_cleanup_capture_and_saved_consistency[contradiction]` (`112.14s`),
     - `test_cleanup_capture_and_saved_consistency[whitespace]` (`111.32s`),
     - `test_runtime_observation_capture_and_saved_consistency[True]` (`110.44s`),
     - `test_cleanup_capture_and_saved_consistency[restore_after_gate]` (`110.30s`),
     - `test_real_callback_and_usage_failures_stay_failed[contradictory_exit]` (`80.48s`),
     - `test_real_callback_and_usage_failures_stay_failed[protected_correction]` (`79.27s`).
3. **`tests/test_evaluation/test_cross_family_judge_analysis.py`** (35 cases; `897.451s` replayed -> **`890.987s` actual**, `-6.464s`):
   - 4 calls in the top 25 (`144.02s`, `84.07s`, `78.90s`, `67.13s`).
4. **`tests/test_source_heading_output_layout.py`** (10 cases; `577.254s` replayed -> **`600.977s` actual**, `+23.723s`):
   - 6 calls in the top 25 (`70.26s`, `69.19s`, `64.40s`, `63.54s`, `63.39s`, `63.15s`).
5. **`tests/test_report_claims_corpus.py`** (16 cases; `143.913s` replayed -> **`154.028s` actual**, `+10.115s`):
   - 1 call in the top 25 (`test_all_report_measurements_reproduce_with_the_registered_aggregate` at `115.81s`).

In addition, **`tests/test_preflight_resource_authority.py`** (40 cases not individually in the top 25) grew from `276.723s` replayed to **`462.224s` actual (`+185.501s`, `+67.0%`)**.

---

## 3. Accounting for the Observed Spread (`#5824`)

The recorded per-file case-duration deltas in `pytest.xml` account for how the shards' recorded case-seconds diverged from the `~6389.17s` replay target (`3995.222s` in Shard 3 to `7492.495s` in Shard 8), while the underlying physical causes of those duration changes between the two runs are unmeasured:

1. **Ratio of overlapping case-duration to suite wall time (`actual_case_s / suite_wall_s`)**:
   - Across all 8 shards, the ratio of summed overlapping testcase durations (`actual_case_s`) to `testsuite` wall time (`suite_wall_s`) ranged from **`3.701` to `3.848`** (Shard 8: `3.843` = `7492.495s / 1949.74s`; Shard 3: `3.791` = `3995.222s / 1053.90s`). This ratio is strictly `actual_case_s / suite_wall_s` from JUnit XML, **not** a measurement of CPU utilization or active worker utilization.
   - Because `tests/test_bc1_g2_journal.py` had the highest per-item ordering priority in Shard 8 (`1062.111s / 4 = 265.528s/item`), `test_every_bc1_response_is_journaled_before_parse` started at `2026-11-11T02:41:37.0290069Z` (`shard8.log:378`) and logged `PASSED` at `2026-11-11T03:04:38.1740438Z` (`shard8.log:743`), **`8m24.58s` (`504.58s`)** before the Shard 8 pytest run completed at `2026-11-11T03:13:02.7538060Z` (`shard8.log:6758`).
2. **Shards `1`, `4`, and `7` (`-0.2%` to `-1.4%` vs. replay)**:
   - Shards 1, 4, and 7 recorded `6373.588s`, `6299.508s`, and `6333.654s` of actual case-seconds against `6389.171s` replayed, with step-5 durations of **`27m22s–27m53s`** (`27m53s–28m25s` job wall).
3. **Shard 8 recorded case-time delta (`+1103.323s` / `+17.3%` vs. replay; `32m35s` step 5)**:
   - Three files accounted for **`+1044.491s` (`94.7%`)** of Shard 8's `+1103.323s` recorded case-second increase over `42916359440`: `tests/test_native_execution.py` (`+497.181s`), `tests/test_bc1_g2_journal.py` (`+361.809s`, led by `test_every_bc1_response_is_journaled_before_parse` at `1361.09s` call), and `tests/test_preflight_resource_authority.py` (`+185.501s`). At Shard 8's `3.843` overlapping case-duration / wall ratio, `+1103.323` case-seconds corresponds to `+287s` (`+4m47s`) of `testsuite` wall time.
4. **Shard 3 recorded case-time delta (`-2393.946s` / `-37.5%` vs. replay; `17m38s` step 5)**:
   - In Shard 3, **`tests/test_shared_generation_runtime.py` recorded `-1228.654s` less case time than its `42916359440` weight** (`2999.822s` replayed -> `1771.168s` actual, `51.3%` of Shard 3's total delta), followed by `tests/test_usage_ledger.py` (`-254.147s`), `tests/test_evaluation_model.py` (`-220.111s`), `tests/test_pr5212_r4_fixes.py` (`-136.818s`), and `tests/test_source_heading_runtime.py` (`-121.539s`). Shard 2 similarly recorded `-2322.089s` (`4067.083s` actual vs. `6389.172s` replayed; `17m55s` step 5).

### Conclusion
- **What the evidence establishes**: The observed per-file case-duration deltas in `pytest.xml` explain how the recorded case-time spread across shards (`3995.222s` in Shard 3 to `7492.495s` in Shard 8) maps to the `18m04s` (`shard 3`) to `33m08s` (`shard 8`) job wall-time spread, and `test_every_bc1_response_is_journaled_before_parse` (`02:41:37.03Z` to `03:04:38.17Z`) finished `8m24.58s` before Shard 8 ended (`03:13:02.75Z`).
- **What remains unmeasured (single-run caveat)**: Static file-duration replay is a scheduling estimate from a single reference run (`42916359440`), not a wall-clock guarantee. Whether the per-file duration shifts between `42916359440` and `42947560899` were caused by hosted-runner throughput variance, historical shard contention inflating prior weights, or workload/subprocess sensitivity is **unmeasured** and remains a hypothesis that cannot be established from two runs.
- **Two-run workflow comparison**: In this comparison, overall workflow wall time was **`33m17s` (`42947560899`) versus `36m37s` (`42916359440`), or `3m20s` shorter**, with Shard 8 at `33m08s` and dedicated `API case routing-portable` at `31m38s`; how much of that `3m20s` difference reflects the rebalanced partition versus between-run variance cannot be isolated from a single post-refresh run.
- Per Lead instructions, `E2` remains frozen at `e42825f9f801f98018a1412a38e414192e8e1bb9` (`95b9e6b16babd1eb72a4074c73003da5cdb0d7e5` on PR `#5814`) with no further code edits, commits, pushes, or CI runs.

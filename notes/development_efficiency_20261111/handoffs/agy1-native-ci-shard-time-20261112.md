# Native CI Shard Time Analysis (`42976790438` at `1a137b58860416a31618de44173180d021dfcc61`)

## Answer

On this one run's evidence (and one run is one measurement), adding only the measured native test file durations to `utils/ci_test_durations.json` does NOT fit the 45-minute PR limit on 8 shards (or 9 shards), because `tests/test_generation_specificity_skill.py` on Shard 8 grew from its 1,148.699s weight to 5,918.248s (and `tests/test_d42_claude_d55.py` on Shard 5 grew from 2,184.783s to 3,352.067s): if only native weights are added, balanced_files predicts a largest scheduled shard of 7,518.450s (8 shards), 6,683.063s (9 shards), and 6,014.757s (10 shards), but packs ~6,370s of other files onto the `tests/test_generation_specificity_skill.py` shard for an actual measured load of 13,861.539s (57.76 ideal 4-worker min) at 8 shards, 12,062.054s (50.26 min) at 9 shards, and 10,756.118s (44.82 min) at 10 shards. If all 714 files measured in run 42976790438 (both native and non-native) are updated in the weights, the largest shard drops to 8,253.583s (34.39 ideal 4-worker min, ~37–38 min job wall) at 8 shards, 7,336.518s (30.57 min) at 9 shards, and 6,602.866s (27.51 min) at 10 shards (or 8,464.084s, 7,523.630s, and 6,771.267s when also imputing the 15 unrun Shard-8 native files at the 105.094s measured native mean) — meaning a full weight refresh (not native-only) can fit 45 minutes at 8 shards with ~6–7 min wall margin, while moving to 9 or 10 PR shards buys ~4–7 min of additional wall-clock headroom.

> **Single-run caveat:** One CI run is one measurement. In run `42976790438`, Python 3.12 shard 5 (99%, 3,106 of 3,109 cases completed) and Python 3.12 shard 8 (16%, 627 of 3,860 cases completed) were cancelled at the 45-minute job timeout (2,715.0s and 2,717.0s), leaving 3 cases on Shard 5 and 3,233 cases (85 unstarted files + 2 partially completed files) on Shard 8 unmeasured in CI.

### Why Shard 5 and Shard 8 Timed Out

1. **Workflow & weights configuration at `1a137b58860416a31618de44173180d021dfcc61`**: `.github/workflows/main.yaml` invokes `utils/pytest_shard.py` with 8 shards on pull requests (timeout 45 minutes = 2,700s) or 6 shards on main and manual runs (timeout 60 minutes = 3,600s), reading `utils/ci_test_durations.json` and running 4 xdist workers (`-n logical --maxprocesses=4 --dist load --maxschedchunk=1`).
2. **128 unweighted native test files scheduled at 1.622s fallback**: Out of 801 test files in `tests/` (799 collected in run `42976790438` after excluding `tests/test_renderer.py` with 0 test functions and `tests/test_native_u3c_test_driver.py` which failed at collection), 143 files (141 collected) have no entry in `utils/ci_test_durations.json`: **128 native files** (`test_native_` prefix) and **15 non-native files**. `utils/pytest_shard.py` assigns every unweighted file the median known weight (1.622s). Across the 112 unweighted native files that actually ran, scheduled weight was 181.664s (112 x 1.622s), whereas their measured time was **11,770.535s** (64.8x their scheduled fallback).
3. **Shard 5 (2,715.0s, cancelled at 99%, 3,106 of 3,109 cases completed across 101 of 101 files)**: Completed worker intervals totaled **9,948.120s** (plus 497.181s of in-flight worker time between each worker's last completed case and cancellation = 10,445.301s against a 6,097.547s scheduled total, an overrun of **+3,850.573s** completed or **+4,347.754s** including in-flight tails). Two factors drove the timeout: (a) **19 unweighted native files** scheduled at 30.818s (19 x 1.622s) consumed **1,883.059s** of completed worker intervals (led by `tests/test_native_shared_results.py` at 602.251s + 179.619s in-flight on `gw3`, `tests/test_native_permission_projection_derivation.py` at 316.250s, and `tests/test_native_generation_frontdoor.py` at 227.033s), and because their 1.622s fallback gave them tiny per-case priorities, `utils/pytest_shard.py` queued them near the end of the shard; (b) **weighted files on Shard 5 also grew by +1,796.609s**, led by `tests/test_d42_claude_d55.py` (3,352.067s vs 2,184.783s weight, +1,167.284s), weighted native file `tests/test_native_attempt_supervisor.py` (1,120.114s vs 770.845s, +349.269s), and `tests/test_source_heading_runtime_api.py` (918.268s vs 636.861s, +281.407s).
4. **Shard 8 (2,717.0s, cancelled at 16%, 627 of 3,860 cases completed across 16 of 101 files)**: Completed worker intervals totaled **10,229.580s** (plus 211.662s in-flight = 10,441.242s) across only 16 files. Only **1 unweighted native file** (`tests/test_native_u3d_round9_preparation.py`, 1 case, 45.802s) ran before cancellation; the other **15 unweighted native files** (741 cases) never started. Shard 8 timed out because **`tests/test_generation_specificity_skill.py`** (which runs the specificity scanner across the codebase and grew on the native branch) consumed **5,918.248s** across 366 of 381 completed cases (with `gw0`, `gw1`, `gw2` still running its remaining 15 cases at cancellation) against a recorded weight of **1,148.699s** (**+4,769.549s**, or **5.15x** its weight), and `tests/test_d69_artifact_completeness.py` consumed 1,545.220s (vs 1,357.606s).

## 1. Measured Time Source & Cancelled Shard Availability (`42976790438`)

- **Downloaded artifacts directory**: `/Users/marcin/agent-work/data-sheets-schema/ci-run-42976790438`
- **Completed/failed shards (`1, 2, 3, 4, 6, 7`)**: Uploaded per-shard JUnit XML artifacts (`/Users/marcin/agent-work/data-sheets-schema/ci-run-42976790438/tests-py3.12-shard1/pytest.xml`, `/Users/marcin/agent-work/data-sheets-schema/ci-run-42976790438/tests-py3.12-shard2/pytest.xml`, `/Users/marcin/agent-work/data-sheets-schema/ci-run-42976790438/tests-py3.12-shard3/pytest.xml`, `/Users/marcin/agent-work/data-sheets-schema/ci-run-42976790438/tests-py3.12-shard4/pytest.xml`, `/Users/marcin/agent-work/data-sheets-schema/ci-run-42976790438/tests-py3.12-shard6/pytest.xml`, `/Users/marcin/agent-work/data-sheets-schema/ci-run-42976790438/tests-py3.12-shard7/pytest.xml`) are present and used as the primary per-file measurement (summing `<testcase time="...">` per file, matching `utils/update_ci_shard_timings.py`).
- **Cancelled shards (`5` and `8`)**: No JUnit XML artifact was uploaded because the runner terminated pytest at the 45-minute timeout before session finish. Per-file times are extracted from the saved GitHub Actions job logs (`/Users/marcin/agent-work/data-sheets-schema/ci-run-42976790438/logs/shard5.log` and `/Users/marcin/agent-work/data-sheets-schema/ci-run-42976790438/logs/shard8.log`) using the repo's established worker-completion-interval method (elapsed time between consecutive `[gwN]` results on each of the 4 workers, starting from worker creation).

| Cancelled Shard | Job ID | Job Wall (s) | Assigned Files | Files Started (Full / Partial / Unstarted) | Cases Completed / Expected | Completed Worker-Interval Sum (s) | Unreported In-Flight Worker Tail (s) | Unstarted Weighted Files (Weight Sum) | Unstarted Unweighted Files (`test_native_` / Other) |
| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | --- | --- |
| Shard 5 | `131032305768` | 2715.0 | 101 | 101 (98 / 3 / 0) | 3106 / 3109 (99%) | 9948.124 | 494.324 | 0 (0.000s) | 0 (0 / 0) |
| Shard 8 | `131032305812` | 2717.0 | 101 | 16 (14 / 2 / 85) | 627 / 3860 (16%) | 10229.579 | 205.398 | 69 (1039.787s) | 16 (15 / 1) |

### Partially Completed Files on Cancelled Shards 5 and 8

| Shard | File | Completed / Expected Cases | Unfinished Cases | Completed Worker-Interval Time (s) | Committed Weight (s) | Scheduled Estimate (s) |
| ---: | --- | ---: | ---: | ---: | ---: | ---: |
| 5 | `tests/test_d69_fail_closed.py` | 49 / 50 | 1 | 21.579 | 1.601 | 1.601 |
| 5 | `tests/test_native_generation_frontdoor.py` | 40 / 41 | 1 | 227.028 | none | 3.554 |
| 5 | `tests/test_native_shared_results.py` | 11 / 12 | 1 | 602.254 | none | 3.554 |
| 8 | `tests/test_generation_specificity_skill.py` | 366 / 381 | 15 | 5918.253 | 1148.699 | 1148.699 |
| 8 | `tests/test_shared_generation_cli.py` | 36 / 55 | 19 | 81.700 | 142.732 | 142.732 |

## 2. Which Files Have No Weight at `1a137b58860416a31618de44173180d021dfcc61`

- **Weights file read by `.github/workflows/main.yaml`**: `utils/ci_test_durations.json` (SHA-256: `0773c06a3f96c1cff5a6e6d32bd4e944edcce6032cd016cb49596d41fbda7ce2`, `661` entries; median fallback across the `658` weighted collected files = **`3.554s`**).
- **Unweighted native test files (`test_native_` prefix)**: **`128` files** (`112` ran and measured **`11770.535s`**, mean `105.094s`, median `2.493s`; `15` were assigned to cancelled Shard 8 and never started; `1` failed at collection across all shards: `tests/test_native_u3c_test_driver.py`).
- **Already-weighted native test files**: **`23` files** (committed weight sum `3505.992s`; measured sum in run `42976790438` = `3219.486s`).
- **Unweighted non-native test files**: **`15` files** (`13` ran and measured `709.615s`; `tests/test_historical_eval_pack.py` was unstarted on Shard 8; `tests/test_renderer.py` has `0` tests).

### All `128` Unweighted Native Test Files, Ordered by Measured Seconds

| # | Native Test File | Shard | Status | Cases (Done / Exp) | Scheduled Fallback (s) | Measured Seconds (s) | Source |
| ---: | --- | ---: | --- | ---: | ---: | ---: | --- |
| 1 | `tests/test_native_shared_attribution.py` | 4 | measured_complete | 48 / 48 | 3.554 | 3828.030 | shard4:junit_xml |
| 2 | `tests/test_native_u3l_review_fixtures.py` | 1 | measured_complete | 13 / 13 | 3.554 | 1846.102 | shard1:junit_xml |
| 3 | `tests/test_native_shared_provenance.py` | 7 | measured_complete | 3 / 3 | 3.554 | 741.746 | shard7:junit_xml |
| 4 | `tests/test_native_shared_controller.py` | 3 | measured_complete | 47 / 47 | 3.554 | 669.859 | shard3:junit_xml |
| 5 | `tests/test_native_shared_live_capture.py` | 7 | measured_complete | 5 / 5 | 3.554 | 639.377 | shard7:junit_xml |
| 6 | `tests/test_native_shared_results.py` | 5 | partial_on_cancelled_shard_5 (11/12 cases) | 11 / 12 | 3.554 | 602.254 | shard5:job_log_worker_intervals |
| 7 | `tests/test_native_shared_saved_pool_bound.py` | 1 | measured_complete | 1 / 1 | 3.554 | 367.410 | shard1:junit_xml |
| 8 | `tests/test_native_u4b_audit_counts.py` | 3 | measured_complete | 25 / 25 | 3.554 | 363.270 | shard3:junit_xml |
| 9 | `tests/test_native_permission_projection_derivation.py` | 5 | measured_complete | 9 / 9 | 3.554 | 316.246 | shard5:job_log_worker_intervals |
| 10 | `tests/test_native_generation_frontdoor.py` | 5 | partial_on_cancelled_shard_5 (40/41 cases) | 40 / 41 | 3.554 | 227.028 | shard5:job_log_worker_intervals |
| 11 | `tests/test_native_permission_probe.py` | 4 | measured_complete | 65 / 65 | 3.554 | 210.622 | shard4:junit_xml |
| 12 | `tests/test_native_u3f2_construction.py` | 5 | measured_complete | 4 / 4 | 3.554 | 194.932 | shard5:job_log_worker_intervals |
| 13 | `tests/test_native_u4b_a5_producer_integration.py` | 5 | measured_complete | 18 / 18 | 3.554 | 183.542 | shard5:job_log_worker_intervals |
| 14 | `tests/test_native_u4b_probe_sequence.py` | 4 | measured_complete | 57 / 57 | 3.554 | 182.672 | shard4:junit_xml |
| 15 | `tests/test_native_shared_callback_preloading.py` | 5 | measured_complete | 18 / 18 | 3.554 | 175.346 | shard5:job_log_worker_intervals |
| 16 | `tests/test_native_launch_schema_metadata.py` | 1 | measured_complete | 38 / 38 | 3.554 | 111.115 | shard1:junit_xml |
| 17 | `tests/test_native_execution_registration_v2.py` | 2 | measured_complete | 65 / 65 | 3.554 | 102.234 | shard2:junit_xml |
| 18 | `tests/test_native_shared_receipt_readers.py` | 1 | measured_complete | 3 / 3 | 3.554 | 91.561 | shard1:junit_xml |
| 19 | `tests/test_native_u1_scanner_contracts.py` | 2 | measured_complete | 77 / 77 | 3.554 | 86.855 | shard2:junit_xml |
| 20 | `tests/test_native_shared_stages.py` | 5 | measured_complete | 18 / 18 | 3.554 | 84.406 | shard5:job_log_worker_intervals |
| 21 | `tests/test_native_u3l_scanner.py` | 3 | measured_complete | 50 / 50 | 3.554 | 82.582 | shard3:junit_xml |
| 22 | `tests/test_native_execution_bridge_v2.py` | 5 | measured_complete | 42 / 42 | 3.554 | 72.262 | shard5:job_log_worker_intervals |
| 23 | `tests/test_native_u1_api_parity.py` | 6 | measured_complete | 14 / 14 | 3.554 | 71.297 | shard6:junit_xml |
| 24 | `tests/test_native_shared_execution_failure.py` | 2 | measured_complete | 17 / 17 | 3.554 | 54.005 | shard2:junit_xml |
| 25 | `tests/test_native_u3d_round9_preparation.py` | 8 | measured_complete | 1 / 1 | 3.554 | 45.802 | shard8:job_log_worker_intervals |
| 26 | `tests/test_native_schema_metadata_reuse.py` | 3 | measured_complete | 38 / 38 | 3.554 | 36.536 | shard3:junit_xml |
| 27 | `tests/test_native_shared_capture_integration.py` | 7 | measured_complete | 6 / 6 | 3.554 | 33.071 | shard7:junit_xml |
| 28 | `tests/test_native_u4b_a5_scanner.py` | 6 | measured_complete | 23 / 23 | 3.554 | 30.820 | shard6:junit_xml |
| 29 | `tests/test_native_shared_owner_delivery.py` | 2 | measured_complete | 2 / 2 | 3.554 | 27.013 | shard2:junit_xml |
| 30 | `tests/test_native_u3d_round9_boundaries.py` | 1 | measured_complete | 9 / 9 | 3.554 | 26.628 | shard1:junit_xml |
| 31 | `tests/test_native_receipt_origin_stage_join.py` | 2 | measured_complete | 1 / 1 | 3.554 | 26.532 | shard2:junit_xml |
| 32 | `tests/test_native_preparer_v2_equivalence.py` | 6 | measured_complete | 1 / 1 | 3.554 | 21.073 | shard6:junit_xml |
| 33 | `tests/test_native_shared_execution_variant.py` | 1 | measured_complete | 1 / 1 | 3.554 | 16.738 | shard1:junit_xml |
| 34 | `tests/test_native_authority_v2.py` | 2 | measured_complete | 12 / 12 | 3.554 | 13.600 | shard2:junit_xml |
| 35 | `tests/test_native_u3c_round4_helpers.py` | 4 | measured_complete | 3 / 3 | 3.554 | 13.599 | shard4:junit_xml |
| 36 | `tests/test_native_shared_projection_handoff.py` | 5 | measured_complete | 4 / 4 | 3.554 | 12.250 | shard5:job_log_worker_intervals |
| 37 | `tests/test_native_u4b_a3_reservation.py` | 7 | measured_complete | 18 / 18 | 3.554 | 12.028 | shard7:junit_xml |
| 38 | `tests/test_native_shared_consumer_census.py` | 2 | measured_complete | 16 / 16 | 3.554 | 11.471 | shard2:junit_xml |
| 39 | `tests/test_native_shared_execution.py` | 6 | measured_complete | 2 / 2 | 3.554 | 10.440 | shard6:junit_xml |
| 40 | `tests/test_native_execution_ci_v2.py` | 7 | measured_complete | 74 / 74 | 3.554 | 10.105 | shard7:junit_xml |
| 41 | `tests/test_native_shared_saved_advance.py` | 2 | measured_complete | 28 / 28 | 3.554 | 10.001 | shard2:junit_xml |
| 42 | `tests/test_native_subscription_capture.py` | 1 | measured_complete | 32 / 32 | 3.554 | 9.739 | shard1:junit_xml |
| 43 | `tests/test_native_preparer_v2_boundaries.py` | 7 | measured_complete | 12 / 12 | 3.554 | 9.291 | shard7:junit_xml |
| 44 | `tests/test_native_execution_round3_v2.py` | 1 | measured_complete | 21 / 21 | 3.554 | 9.131 | shard1:junit_xml |
| 45 | `tests/test_native_execution_round5_v2.py` | 3 | measured_complete | 30 / 30 | 3.554 | 8.932 | shard3:junit_xml |
| 46 | `tests/test_native_u3k_freshness_order.py` | 6 | measured_complete | 18 / 18 | 3.554 | 6.619 | shard6:junit_xml |
| 47 | `tests/test_native_u4b_readback.py` | 5 | measured_complete | 15 / 15 | 3.554 | 5.379 | shard5:job_log_worker_intervals |
| 48 | `tests/test_native_execution_verified_loader_v2.py` | 4 | measured_complete | 35 / 35 | 3.554 | 5.077 | shard4:junit_xml |
| 49 | `tests/test_native_u3d_round9_capabilities.py` | 3 | measured_complete | 14 / 14 | 3.554 | 4.988 | shard3:junit_xml |
| 50 | `tests/test_native_u3d_guard_contract.py` | 5 | measured_complete | 16 / 16 | 3.554 | 4.727 | shard5:job_log_worker_intervals |
| 51 | `tests/test_native_execution_authority_v2.py` | 4 | measured_complete | 29 / 29 | 3.554 | 4.426 | shard4:junit_xml |
| 52 | `tests/test_native_u4b_windows_v2.py` | 1 | measured_complete | 67 / 67 | 3.554 | 4.058 | shard1:junit_xml |
| 53 | `tests/test_native_u4b_admission.py` | 1 | measured_complete | 11 / 11 | 3.554 | 3.732 | shard1:junit_xml |
| 54 | `tests/test_native_u4b_a3_policy.py` | 5 | measured_complete | 50 / 50 | 3.554 | 3.157 | shard5:job_log_worker_intervals |
| 55 | `tests/test_native_shared_render.py` | 4 | measured_complete | 39 / 39 | 3.554 | 3.039 | shard4:junit_xml |
| 56 | `tests/test_native_u3d_prompt_cli.py` | 7 | measured_complete | 3 / 3 | 3.554 | 2.654 | shard7:junit_xml |
| 57 | `tests/test_native_shared_permission_protocol.py` | 1 | measured_complete | 26 / 26 | 3.554 | 2.332 | shard1:junit_xml |
| 58 | `tests/test_native_u4b_a4_review.py` | 4 | measured_complete | 63 / 63 | 3.554 | 2.030 | shard4:junit_xml |
| 59 | `tests/test_native_u4b_addendum_authority.py` | 2 | measured_complete | 15 / 15 | 3.554 | 1.543 | shard2:junit_xml |
| 60 | `tests/test_native_launch_review.py` | 2 | measured_complete | 47 / 47 | 3.554 | 1.512 | shard2:junit_xml |
| 61 | `tests/test_native_u1_selector_refusals.py` | 1 | measured_complete | 32 / 32 | 3.554 | 1.306 | shard1:junit_xml |
| 62 | `tests/test_native_u4b_runtime.py` | 6 | measured_complete | 70 / 70 | 3.554 | 1.261 | shard6:junit_xml |
| 63 | `tests/test_native_u4b_registration_observation.py` | 7 | measured_complete | 32 / 32 | 3.554 | 1.121 | shard7:junit_xml |
| 64 | `tests/test_native_shared_selection.py` | 4 | measured_complete | 26 / 26 | 3.554 | 1.033 | shard4:junit_xml |
| 65 | `tests/test_native_u4b_a5_reasons.py` | 7 | measured_complete | 19 / 19 | 3.554 | 0.807 | shard7:junit_xml |
| 66 | `tests/test_native_shared_publication.py` | 6 | measured_complete | 7 / 7 | 3.554 | 0.676 | shard6:junit_xml |
| 67 | `tests/test_native_initial_structure_mode.py` | 6 | measured_complete | 29 / 29 | 3.554 | 0.662 | shard6:junit_xml |
| 68 | `tests/test_native_u4b_a4_cross_word.py` | 6 | measured_complete | 2 / 2 | 3.554 | 0.633 | shard6:junit_xml |
| 69 | `tests/test_native_shared_effects.py` | 5 | measured_complete | 119 / 119 | 3.554 | 0.630 | shard5:job_log_worker_intervals |
| 70 | `tests/test_native_shared_phase.py` | 4 | measured_complete | 98 / 98 | 3.554 | 0.591 | shard4:junit_xml |
| 71 | `tests/test_native_shared_receipt_delivery.py` | 2 | measured_complete | 11 / 11 | 3.554 | 0.582 | shard2:junit_xml |
| 72 | `tests/test_native_shared_initial_receipts.py` | 4 | measured_complete | 10 / 10 | 3.554 | 0.574 | shard4:junit_xml |
| 73 | `tests/test_native_ci_evidence_adversarial.py` | 3 | measured_complete | 6 / 6 | 3.554 | 0.560 | shard3:junit_xml |
| 74 | `tests/test_native_synthetic_evidence.py` | 4 | measured_complete | 1 / 1 | 3.554 | 0.460 | shard4:junit_xml |
| 75 | `tests/test_native_wp1_capture_recheck.py` | 5 | measured_complete | 33 / 33 | 3.554 | 0.434 | shard5:job_log_worker_intervals |
| 76 | `tests/test_native_u3d_receipt_policy.py` | 6 | measured_complete | 17 / 17 | 3.554 | 0.411 | shard6:junit_xml |
| 77 | `tests/test_native_u4b_toolchain.py` | 2 | measured_complete | 9 / 9 | 3.554 | 0.381 | shard2:junit_xml |
| 78 | `tests/test_native_synthetic_profiles.py` | 5 | measured_complete | 46 / 46 | 3.554 | 0.353 | shard5:job_log_worker_intervals |
| 79 | `tests/test_native_shared_schema_derivation_once.py` | 3 | measured_complete | 6 / 6 | 3.554 | 0.348 | shard3:junit_xml |
| 80 | `tests/test_native_import_facts.py` | 7 | measured_complete | 27 / 27 | 3.554 | 0.303 | shard7:junit_xml |
| 81 | `tests/test_native_shared_runtime_values.py` | 6 | measured_complete | 73 / 73 | 3.554 | 0.256 | shard6:junit_xml |
| 82 | `tests/test_native_lexical_ancestry.py` | 3 | measured_complete | 36 / 36 | 3.554 | 0.240 | shard3:junit_xml |
| 83 | `tests/test_native_shared_contract.py` | 1 | measured_complete | 39 / 39 | 3.554 | 0.225 | shard1:junit_xml |
| 84 | `tests/test_native_shared_streams.py` | 2 | measured_complete | 32 / 32 | 3.554 | 0.225 | shard2:junit_xml |
| 85 | `tests/test_native_u5_external_schema.py` | 3 | measured_complete | 6 / 6 | 3.554 | 0.176 | shard3:junit_xml |
| 86 | `tests/test_native_u3a_test_driver.py` | 3 | measured_complete | 11 / 11 | 3.554 | 0.169 | shard3:junit_xml |
| 87 | `tests/test_native_u4b_a3_frontdoor.py` | 4 | measured_complete | 5 / 5 | 3.554 | 0.144 | shard4:junit_xml |
| 88 | `tests/test_native_u4b_a4_producer.py` | 3 | measured_complete | 18 / 18 | 3.554 | 0.128 | shard3:junit_xml |
| 89 | `tests/test_native_ci_evidence.py` | 1 | measured_complete | 19 / 19 | 3.554 | 0.125 | shard1:junit_xml |
| 90 | `tests/test_native_shared_layer_split.py` | 5 | measured_complete | 10 / 10 | 3.554 | 0.107 | shard5:job_log_worker_intervals |
| 91 | `tests/test_native_shared_observations.py` | 6 | measured_complete | 49 / 49 | 3.554 | 0.082 | shard6:junit_xml |
| 92 | `tests/test_native_shared_current.py` | 4 | measured_complete | 8 / 8 | 3.554 | 0.080 | shard4:junit_xml |
| 93 | `tests/test_native_shared_gate_primitives.py` | 3 | measured_complete | 52 / 52 | 3.554 | 0.076 | shard3:junit_xml |
| 94 | `tests/test_native_shared_permission_split.py` | 3 | measured_complete | 30 / 30 | 3.554 | 0.071 | shard3:junit_xml |
| 95 | `tests/test_native_u5_scanner_comparison.py` | 4 | measured_complete | 19 / 19 | 3.554 | 0.067 | shard4:junit_xml |
| 96 | `tests/test_native_u4b_a4_paths.py` | 1 | measured_complete | 14 / 14 | 3.554 | 0.052 | shard1:junit_xml |
| 97 | `tests/test_native_shared_stream_diagnostics.py` | 7 | measured_complete | 26 / 26 | 3.554 | 0.049 | shard7:junit_xml |
| 98 | `tests/test_native_execution_engine.py` | 6 | measured_complete | 15 / 15 | 3.554 | 0.041 | shard6:junit_xml |
| 99 | `tests/test_native_shared_evidence.py` | 7 | measured_complete | 22 / 22 | 3.554 | 0.037 | shard7:junit_xml |
| 100 | `tests/test_native_subscription_guard.py` | 3 | measured_complete | 35 / 35 | 3.554 | 0.037 | shard3:junit_xml |
| 101 | `tests/test_native_receipt_unopened.py` | 1 | measured_complete | 7 / 7 | 3.554 | 0.034 | shard1:junit_xml |
| 102 | `tests/test_native_synthetic_startup.py` | 7 | measured_complete | 1 / 1 | 3.554 | 0.032 | shard7:junit_xml |
| 103 | `tests/test_native_authority_replay_v1.py` | 6 | measured_complete | 1 / 1 | 3.554 | 0.027 | shard6:junit_xml |
| 104 | `tests/test_native_shared_stream_diagnostics_adversarial.py` | 6 | measured_complete | 15 / 15 | 3.554 | 0.026 | shard6:junit_xml |
| 105 | `tests/test_native_u3d_round9_arguments.py` | 2 | measured_complete | 5 / 5 | 3.554 | 0.020 | shard2:junit_xml |
| 106 | `tests/test_native_shared_record_contract.py` | 3 | measured_complete | 5 / 5 | 3.554 | 0.016 | shard3:junit_xml |
| 107 | `tests/test_native_shared_runtime_constants.py` | 7 | measured_complete | 8 / 8 | 3.554 | 0.014 | shard7:junit_xml |
| 108 | `tests/test_native_u3d_runner_evidence.py` | 4 | measured_complete | 1 / 1 | 3.554 | 0.010 | shard4:junit_xml |
| 109 | `tests/test_native_u3k_profile.py` | 2 | measured_complete | 4 / 4 | 3.554 | 0.008 | shard2:junit_xml |
| 110 | `tests/test_native_u4b_a4_packet.py` | 2 | measured_complete | 4 / 4 | 3.554 | 0.006 | shard2:junit_xml |
| 111 | `tests/test_native_shared_capture_split.py` | 6 | measured_complete | 2 / 2 | 3.554 | 0.002 | shard6:junit_xml |
| 112 | `tests/test_native_u3j2_metrics_canary.py` | 7 | measured_complete | 1 / 1 | 3.554 | 0.001 | shard7:junit_xml |
| 113 | `tests/test_native_d128_scanner_comparison.py` | 8 | unstarted_on_cancelled_shard_8 | 0 / 28 | 3.554 | not measured | n/a |
| 114 | `tests/test_native_execution_round6_v2.py` | 8 | unstarted_on_cancelled_shard_8 | 0 / 2 | 3.554 | not measured | n/a |
| 115 | `tests/test_native_model_aliases.py` | 8 | unstarted_on_cancelled_shard_8 | 0 / 34 | 3.554 | not measured | n/a |
| 116 | `tests/test_native_shared_acceptance_runner.py` | 8 | unstarted_on_cancelled_shard_8 | 0 / 23 | 3.554 | not measured | n/a |
| 117 | `tests/test_native_shared_controls.py` | 8 | unstarted_on_cancelled_shard_8 | 0 / 15 | 3.554 | not measured | n/a |
| 118 | `tests/test_native_shared_gates.py` | 8 | unstarted_on_cancelled_shard_8 | 0 / 29 | 3.554 | not measured | n/a |
| 119 | `tests/test_native_shared_permissions.py` | 8 | unstarted_on_cancelled_shard_8 | 0 / 94 | 3.554 | not measured | n/a |
| 120 | `tests/test_native_shared_registration.py` | 8 | unstarted_on_cancelled_shard_8 | 0 / 21 | 3.554 | not measured | n/a |
| 121 | `tests/test_native_shared_schema_gates.py` | 8 | unstarted_on_cancelled_shard_8 | 0 / 28 | 3.554 | not measured | n/a |
| 122 | `tests/test_native_subscription_guard_v2.py` | 8 | unstarted_on_cancelled_shard_8 | 0 / 105 | 3.554 | not measured | n/a |
| 123 | `tests/test_native_u3b_reuse.py` | 8 | unstarted_on_cancelled_shard_8 | 0 / 48 | 3.554 | not measured | n/a |
| 124 | `tests/test_native_u3c_test_driver.py` | n/a | collection_error_all_shards | 0 / 0 | n/a | not measured | n/a |
| 125 | `tests/test_native_u4b_a3_captures.py` | 8 | unstarted_on_cancelled_shard_8 | 0 / 17 | 3.554 | not measured | n/a |
| 126 | `tests/test_native_u4b_a4_real_events.py` | 8 | unstarted_on_cancelled_shard_8 | 0 / 233 | 3.554 | not measured | n/a |
| 127 | `tests/test_native_u4b_capture_retries.py` | 8 | unstarted_on_cancelled_shard_8 | 0 / 13 | 3.554 | not measured | n/a |
| 128 | `tests/test_native_u5_scanner.py` | 8 | unstarted_on_cancelled_shard_8 | 0 / 51 | 3.554 | not measured | n/a |

### Unweighted Non-Native Test Files (`15` files)

| # | Non-Native Test File | Shard | Status | Cases (Done / Exp) | Scheduled Fallback (s) | Measured Seconds (s) |
| ---: | --- | ---: | --- | ---: | ---: | ---: |
| 1 | `tests/test_wave7_5213_d76_integration_ordering.py` | 1 | measured_complete | 81 / 81 | 3.554 | 231.239 |
| 2 | `tests/test_transformation_measure.py` | 7 | measured_complete | 31 / 31 | 3.554 | 170.070 |
| 3 | `tests/test_derive_core_selected_schemas.py` | 2 | measured_complete | 11 / 11 | 3.554 | 88.574 |
| 4 | `tests/test_historical_eval_parity.py` | 4 | measured_complete | 10 / 10 | 3.554 | 77.810 |
| 5 | `tests/test_transformation_measure_cli.py` | 6 | measured_complete | 41 / 41 | 3.554 | 40.449 |
| 6 | `tests/test_bc1_planline_cli.py` | 7 | measured_complete | 5 / 5 | 3.554 | 38.172 |
| 7 | `tests/test_historical_eval_review_fixes.py` | 5 | measured_complete | 19 / 19 | 3.554 | 27.566 |
| 8 | `tests/test_historical_eval_audit.py` | 3 | measured_complete | 48 / 48 | 3.554 | 17.047 |
| 9 | `tests/test_typed_audit_captured_assets.py` | 2 | measured_complete | 11 / 11 | 3.554 | 10.887 |
| 10 | `tests/test_historical_eval_admission.py` | 1 | measured_complete | 59 / 59 | 3.554 | 4.752 |
| 11 | `tests/test_context_evidence_verbatim.py` | 6 | measured_complete | 90 / 90 | 3.554 | 1.735 |
| 12 | `tests/test_historical_eval_route.py` | 7 | measured_complete | 1 / 1 | 3.554 | 0.928 |
| 13 | `tests/test_bc1_catalog_fixture.py` | 5 | measured_complete | 2 / 2 | 3.554 | 0.386 |
| 14 | `tests/test_historical_eval_pack.py` | 8 | unstarted_on_cancelled_shard_8 | 0 / 19 | 3.554 | not measured |
| 15 | `tests/test_renderer.py` | n/a | zero_tests_not_collected | 0 / 0 | n/a | not measured |

## 3. Where the Time Went: Per-Shard Totals, Native Sums, and 10 Slowest Files (`1..8`)

| Shard | Conclusion | Job Wall (s / min) | Pytest Wall (s) | Source | Files (Ran / Assigned) | Scheduled Case-Seconds (s) | Measured Case-Seconds Total (s) | Measured All Native `test_native_` (s) | Measured Unweighted Native (s) | Measured Weighted Native (s) |
| ---: | --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | `failure` | 2543.0s (42.38m) | 2508.41s | `junit_xml` | 96 / 96 | 6097.546 | **9584.807** | **2756.960** | 2490.288 | 266.672 |
| 2 | `failure` | 2452.0s (40.87m) | 2417.86s | `junit_xml` | 99 / 99 | 6097.549 | **9092.034** | **355.741** | 335.988 | 19.753 |
| 3 | `failure` | 1662.0s (27.70m) | 1625.43s | `junit_xml` | 100 / 100 | 6097.546 | **6059.679** | **1323.634** | 1167.988 | 155.646 |
| 4 | `failure` | 2263.0s (37.72m) | 2225.14s | `junit_xml` | 100 / 100 | 6097.550 | **8528.670** | **4258.579** | 4252.454 | 6.125 |
| 5 | `cancelled` | 2715.0s (45.25m) | 2610.63s | `job_log_worker_intervals` | 101 / 101 | 6097.542 | **9948.124** | **3010.726** | 1883.053 | 1127.672 |
| 6 | `failure` | 1316.0s (21.93m) | 1277.89s | `junit_xml` | 101 / 101 | 6097.546 | **4861.588** | **1777.817** | 144.326 | 1633.491 |
| 7 | `failure` | 1757.0s (29.28m) | 1724.61s | `junit_xml` | 101 / 101 | 6097.542 | **6619.322** | **1460.763** | 1450.636 | 10.127 |
| 8 | `cancelled` | 2717.0s (45.28m) | 2608.76s | `job_log_worker_intervals` | 16 / 101 | 6097.546 | **10229.579** | **45.802** | 45.802 | 0.000 |

### Shard 1 — 10 Slowest Files (`failure`, measured total `9584.807s`, native sum `2756.960s`)

| Rank | Test File | Measured (s) | Committed Weight (s) | Scheduled (s) | Delta vs Scheduled (s) | Cases (Done / Exp) | Native? |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | `tests/test_report_admission.py` | 5217.652 | 4576.868 | 4576.868 | +640.784 | 32 / 32 | no |
| 2 | `tests/test_native_u3l_review_fixtures.py` | 1846.102 | none | 3.554 | +1842.548 | 13 / 13 | yes |
| 3 | `tests/test_native_shared_saved_pool_bound.py` | 367.410 | none | 3.554 | +363.856 | 1 / 1 | yes |
| 4 | `tests/test_native_attribution_results.py` | 260.669 | 139.986 | 139.986 | +120.683 | 87 / 87 | yes |
| 5 | `tests/test_wave7_5213_d76_integration_ordering.py` | 231.239 | none | 3.554 | +227.685 | 81 / 81 | no |
| 6 | `tests/test_evaluation/test_support_calibration_adversarial.py` | 160.067 | 161.298 | 161.298 | -1.231 | 34 / 34 | no |
| 7 | `tests/test_wave7_5213_d76_relative_registration.py` | 121.054 | 93.427 | 93.427 | +27.627 | 13 / 13 | no |
| 8 | `tests/test_native_launch_schema_metadata.py` | 111.115 | none | 3.554 | +107.561 | 38 / 38 | yes |
| 9 | `tests/test_e3x_rereview_fixes.py` | 107.708 | 75.197 | 75.197 | +32.511 | 29 / 29 | no |
| 10 | `tests/test_native_shared_receipt_readers.py` | 91.561 | none | 3.554 | +88.007 | 3 / 3 | yes |

### Shard 2 — 10 Slowest Files (`failure`, measured total `9092.034s`, native sum `355.741s`)

| Rank | Test File | Measured (s) | Committed Weight (s) | Scheduled (s) | Delta vs Scheduled (s) | Cases (Done / Exp) | Native? |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | `tests/test_download/test_api_runner.py` | 4449.413 | 3200.050 | 3200.050 | +1249.363 | 158 / 158 | no |
| 2 | `tests/test_pr5531_regressions.py` | 1053.253 | 400.518 | 400.518 | +652.735 | 29 / 29 | no |
| 3 | `tests/test_wave7_5213_d76_round3_binding.py` | 722.698 | 591.185 | 591.185 | +131.513 | 42 / 42 | no |
| 4 | `tests/test_d68_legacy_readonly.py` | 300.630 | 237.369 | 237.369 | +63.261 | 323 / 323 | no |
| 5 | `tests/test_shared_generation_resources.py` | 282.711 | 279.376 | 279.376 | +3.335 | 47 / 47 | no |
| 6 | `tests/test_ci_sharding.py` | 219.924 | 149.022 | 149.022 | +70.902 | 76 / 76 | no |
| 7 | `tests/test_typed_audit_figure.py` | 219.213 | 130.397 | 130.397 | +88.816 | 47 / 47 | no |
| 8 | `tests/test_shared_output_ownership_entrypoints.py` | 210.146 | 186.067 | 186.067 | +24.079 | 19 / 19 | no |
| 9 | `tests/test_completed_surviving_usage.py` | 139.220 | 86.718 | 86.718 | +52.502 | 4 / 4 | no |
| 10 | `tests/test_generation_record_schema.py` | 132.289 | 100.127 | 100.127 | +32.162 | 22 / 22 | no |

### Shard 3 — 10 Slowest Files (`failure`, measured total `6059.679s`, native sum `1323.634s`)

| Rank | Test File | Measured (s) | Committed Weight (s) | Scheduled (s) | Delta vs Scheduled (s) | Cases (Done / Exp) | Native? |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | `tests/test_shared_generation_runtime.py` | 2298.329 | 3017.212 | 3017.212 | -718.883 | 10 / 10 | no |
| 2 | `tests/test_native_shared_controller.py` | 669.859 | none | 3.554 | +666.305 | 47 / 47 | yes |
| 3 | `tests/test_pr5212_round7_journal.py` | 496.713 | 629.007 | 629.007 | -132.294 | 24 / 24 | no |
| 4 | `tests/test_native_u4b_audit_counts.py` | 363.270 | none | 3.554 | +359.716 | 25 / 25 | yes |
| 5 | `tests/test_preflight_resource_authority.py` | 357.948 | 400.561 | 400.561 | -42.613 | 40 / 40 | no |
| 6 | `tests/test_pr5212_r4_fixes.py` | 258.675 | 280.798 | 280.798 | -22.123 | 5 / 5 | no |
| 7 | `tests/test_profiles.py` | 144.691 | 199.201 | 199.201 | -54.510 | 90 / 90 | no |
| 8 | `tests/test_shared_schema_sync_resources.py` | 136.668 | 137.042 | 137.042 | -0.374 | 35 / 35 | no |
| 9 | `tests/test_removal_repair.py` | 132.710 | 96.908 | 96.908 | +35.802 | 59 / 59 | no |
| 10 | `tests/test_native_attribution_controller.py` | 128.234 | 163.502 | 163.502 | -35.268 | 43 / 43 | yes |

### Shard 4 — 10 Slowest Files (`failure`, measured total `8528.670s`, native sum `4258.579s`)

| Rank | Test File | Measured (s) | Committed Weight (s) | Scheduled (s) | Delta vs Scheduled (s) | Cases (Done / Exp) | Native? |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | `tests/test_native_shared_attribution.py` | 3828.030 | none | 3.554 | +3824.476 | 48 / 48 | yes |
| 2 | `tests/test_usage_ledger.py` | 671.407 | 666.370 | 666.370 | +5.037 | 60 / 60 | no |
| 3 | `tests/test_d69_round5_boundaries.py` | 455.174 | 402.895 | 402.895 | +52.279 | 71 / 71 | no |
| 4 | `tests/test_assistant_generation_integration.py` | 449.725 | 273.599 | 273.599 | +176.126 | 1 / 1 | no |
| 5 | `tests/test_schema_straddle.py` | 396.019 | 377.021 | 377.021 | +18.998 | 18 / 18 | no |
| 6 | `tests/test_bc1_registration.py` | 351.738 | 2808.544 | 2808.544 | -2456.806 | 30 / 30 | no |
| 7 | `tests/test_audit_evaluation_comparability.py` | 228.990 | 207.971 | 207.971 | +21.019 | 116 / 116 | no |
| 8 | `tests/test_playbook_drift.py` | 221.919 | 140.690 | 140.690 | +81.229 | 10 / 10 | no |
| 9 | `tests/test_native_permission_probe.py` | 210.622 | none | 3.554 | +207.068 | 65 / 65 | yes |
| 10 | `tests/test_absence_second_reading.py` | 204.325 | 170.881 | 170.881 | +33.444 | 13 / 13 | no |

### Shard 5 — 10 Slowest Files (`cancelled`, measured total `9948.124s`, native sum `3010.726s`)

| Rank | Test File | Measured (s) | Committed Weight (s) | Scheduled (s) | Delta vs Scheduled (s) | Cases (Done / Exp) | Native? |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | `tests/test_d42_claude_d55.py` | 3352.068 | 2184.783 | 2184.783 | +1167.285 | 23 / 23 | no |
| 2 | `tests/test_native_attempt_supervisor.py` | 1120.107 | 770.845 | 770.845 | +349.262 | 87 / 87 | yes |
| 3 | `tests/test_source_heading_runtime_api.py` | 918.268 | 636.861 | 636.861 | +281.407 | 14 / 14 | no |
| 4 | `tests/test_native_shared_results.py` | 602.254 | none | 3.554 | +598.700 | 11 / 12 | yes |
| 5 | `tests/test_arm_comparison.py` | 404.890 | 402.117 | 402.117 | +2.773 | 81 / 81 | no |
| 6 | `tests/test_evaluation/test_cross_family_judge_panel.py` | 339.231 | 332.778 | 332.778 | +6.453 | 45 / 45 | no |
| 7 | `tests/test_native_permission_projection_derivation.py` | 316.246 | none | 3.554 | +312.692 | 9 / 9 | yes |
| 8 | `tests/test_evaluation/test_cross_family_panel_analysis.py` | 268.170 | 265.218 | 265.218 | +2.952 | 53 / 53 | no |
| 9 | `tests/test_native_generation_frontdoor.py` | 227.028 | none | 3.554 | +223.474 | 40 / 41 | yes |
| 10 | `tests/test_assistant_workflow.py` | 199.491 | 195.855 | 195.855 | +3.636 | 22 / 22 | no |

### Shard 6 — 10 Slowest Files (`failure`, measured total `4861.588s`, native sum `1777.817s`)

| Rank | Test File | Measured (s) | Committed Weight (s) | Scheduled (s) | Delta vs Scheduled (s) | Cases (Done / Exp) | Native? |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | `tests/test_native_execution.py` | 1153.036 | 1865.454 | 1865.454 | -712.418 | 73 / 73 | yes |
| 2 | `tests/test_bc1_pipeline.py` | 1087.045 | 779.194 | 779.194 | +307.851 | 1 / 1 | no |
| 3 | `tests/test_native_receipt_origin_reporting.py` | 467.966 | 475.608 | 475.608 | -7.642 | 76 / 76 | yes |
| 4 | `tests/test_routed_condition_reporting.py` | 359.861 | 715.424 | 715.424 | -355.563 | 68 / 68 | no |
| 5 | `tests/test_shared_generation_batch_authority.py` | 348.770 | 399.284 | 399.284 | -50.514 | 22 / 22 | no |
| 6 | `tests/test_d69_round4_ownership.py` | 209.009 | 278.655 | 278.655 | -69.646 | 60 / 60 | no |
| 7 | `tests/test_d69_round5_launch.py` | 175.125 | 219.042 | 219.042 | -43.917 | 14 / 14 | no |
| 8 | `tests/test_source_heading_runtime.py` | 97.063 | 176.592 | 176.592 | -79.529 | 15 / 15 | no |
| 9 | `tests/test_review_pack.py` | 95.574 | 107.481 | 107.481 | -11.907 | 55 / 55 | no |
| 10 | `tests/test_absence_lint.py` | 75.783 | 140.492 | 140.492 | -64.709 | 46 / 46 | no |

### Shard 7 — 10 Slowest Files (`failure`, measured total `6619.322s`, native sum `1460.763s`)

| Rank | Test File | Measured (s) | Committed Weight (s) | Scheduled (s) | Delta vs Scheduled (s) | Cases (Done / Exp) | Native? |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | `tests/test_bc1_g2_journal.py` | 1099.227 | 1492.334 | 1492.334 | -393.107 | 4 / 4 | no |
| 2 | `tests/test_receipt_completion_runtime.py` | 965.690 | 1068.698 | 1068.698 | -103.008 | 85 / 85 | no |
| 3 | `tests/test_native_shared_provenance.py` | 741.746 | none | 3.554 | +738.192 | 3 / 3 | yes |
| 4 | `tests/test_native_shared_live_capture.py` | 639.377 | none | 3.554 | +635.823 | 5 / 5 | yes |
| 5 | `tests/test_evaluation/test_cross_family_judge_analysis.py` | 582.844 | 745.260 | 745.260 | -162.416 | 35 / 35 | no |
| 6 | `tests/test_source_heading_output_layout.py` | 446.299 | 565.555 | 565.555 | -119.256 | 10 / 10 | no |
| 7 | `tests/test_d41_request_parity.py` | 332.952 | 394.567 | 394.567 | -61.615 | 6 / 6 | no |
| 8 | `tests/test_deterministic_arm_validity.py` | 220.959 | 199.935 | 199.935 | +21.024 | 15 / 15 | no |
| 9 | `tests/test_name_grounding.py` | 219.910 | 270.355 | 270.355 | -50.445 | 128 / 128 | no |
| 10 | `tests/test_transformation_measure.py` | 170.070 | none | 3.554 | +166.516 | 31 / 31 | no |

### Shard 8 — 10 Slowest Files (`cancelled`, measured total `10229.579s`, native sum `45.802s`)

| Rank | Test File | Measured (s) | Committed Weight (s) | Scheduled (s) | Delta vs Scheduled (s) | Cases (Done / Exp) | Native? |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | `tests/test_generation_specificity_skill.py` | 5918.253 | 1148.699 | 1148.699 | +4769.554 | 366 / 381 | no |
| 2 | `tests/test_d69_artifact_completeness.py` | 1545.219 | 1357.606 | 1357.606 | +187.613 | 11 / 11 | no |
| 3 | `tests/test_wave7_5213_d76_round2_binding.py` | 833.238 | 757.573 | 757.573 | +75.665 | 47 / 47 | no |
| 4 | `tests/test_shared_generation_scope_context.py` | 757.589 | 583.657 | 583.657 | +173.932 | 13 / 13 | no |
| 5 | `tests/test_evaluation_model.py` | 409.881 | 394.885 | 394.885 | +14.996 | 48 / 48 | no |
| 6 | `tests/test_build_api_registrations.py` | 194.851 | 171.121 | 171.121 | +23.730 | 34 / 34 | no |
| 7 | `tests/test_registration_input_sizing.py` | 120.214 | 123.122 | 123.122 | -2.908 | 19 / 19 | no |
| 8 | `tests/test_wave6_a14_a17_sizing.py` | 106.395 | 101.523 | 101.523 | +4.872 | 1 / 1 | no |
| 9 | `tests/test_shared_generation_cli.py` | 81.700 | 142.732 | 142.732 | -61.032 | 36 / 55 | no |
| 10 | `tests/test_github_assistant_generation.py` | 67.187 | 63.076 | 63.076 | +4.111 | 18 / 18 | no |

## 4. What Partition Would Fit (`utils/pytest_shard.py` at `1a137b58860416a31618de44173180d021dfcc61`)

- **Partition module**: Imported from `/Users/marcin/agent-work/data-sheets-schema/ci-run-42976790438/pytest_shard_1a137b588604.py` (SHA-256: `ed2486e31fd850ff8dee6084aee47672c8609ed450cfa75c76443b067c73f3e2`), exported directly from commit `1a137b58860416a31618de44173180d021dfcc61` path `utils/pytest_shard.py`.
- **Why two numbers are reported for each shard count**: `balanced_files(paths, total, weights)` balances the **scheduled weights** it is given. If only native test durations are added to `utils/ci_test_durations.json` (Models 1–2), `balanced_files` still sees `tests/test_generation_specificity_skill.py` at its old weight 1,148.699s (instead of its measured 5,918.248s) and `tests/test_d42_claude_d55.py` at 2,184.783s (instead of 3,352.067s), so the shard containing `tests/test_generation_specificity_skill.py` receives ~6,370s of additional files and actually totals 13,861.539s at 8 shards! Therefore the table below reports **both** the largest predicted scheduled shard total (in the model's own weights) **and** the largest shard total when that partition is evaluated against all 714 measured file durations from run `42976790438`.

### Largest Predicted Shard Totals for Current (`8` PR / `6` main), `+1` (`9` PR / `7` main), and `+2` (`10` PR / `8` main) Shards

| Weight Model | Shards | Role | Largest Scheduled Shard (s / ideal 4w min) | Largest Actual Measured Shard (s / ideal 4w min) | Heaviest File on Largest Measured Shard | All Shards Scheduled Totals (s) |
| --- | ---: | --- | ---: | ---: | --- | --- |
| `0_committed_weights_at_1a137b588604` | 8 | PR current (8) / main +2 (8) | **6097.550s** (25.41m, shard 4) | **11334.437s** (47.23m, shard 8) | `tests/test_generation_specificity_skill.py` (5918.253s) | `[6097.5, 6097.5, 6097.5, 6097.6, 6097.5, 6097.5, 6097.5, 6097.5]` |
| `0_committed_weights_at_1a137b588604` | 9 | PR +1 (9) | **5420.042s** (22.58m, shard 1) | **10506.169s** (43.78m, shard 9) | `tests/test_generation_specificity_skill.py` (5918.253s) | `[5420.0, 5420.0, 5420.0, 5420.0, 5420.0, 5420.0, 5420.0, 5420.0, 5420.0]` |
| `0_committed_weights_at_1a137b588604` | 10 | PR +2 (10) | **4878.038s** (20.33m, shard 6) | **11438.651s** (47.66m, shard 9) | `tests/test_generation_specificity_skill.py` (5918.253s) | `[4878.0, 4878.0, 4878.0, 4878.0, 4878.0, 4878.0, 4878.0, 4878.0, 4878.0, 4878.0]` |
| `0_committed_weights_at_1a137b588604` | 6 | main current (6) | **8130.063s** (33.88m, shard 1) | **12460.512s** (51.92m, shard 3) | `tests/test_native_shared_attribution.py` (3828.030s) | `[8130.1, 8130.1, 8130.1, 8130.1, 8130.1, 8130.1]` |
| `0_committed_weights_at_1a137b588604` | 7 | main +1 (7) | **6968.627s** (29.04m, shard 1) | **12339.886s** (51.42m, shard 6) | `tests/test_generation_specificity_skill.py` (5918.253s) | `[6968.6, 6968.6, 6968.6, 6968.6, 6968.6, 6968.6, 6968.6]` |
| `1_add_112_measured_unweighted_native_files` | 8 | PR current (8) / main +2 (8) | **7518.447s** (31.33m, shard 7) | **13861.544s** (57.76m, shard 6) | `tests/test_generation_specificity_skill.py` (5918.253s) | `[7518.4, 7518.4, 7518.4, 7518.4, 7518.4, 7518.4, 7518.4, 7518.4]` |
| `1_add_112_measured_unweighted_native_files` | 9 | PR +1 (9) | **6683.064s** (27.85m, shard 5) | **12062.051s** (50.26m, shard 8) | `tests/test_generation_specificity_skill.py` (5918.253s) | `[6683.1, 6683.1, 6683.1, 6683.1, 6683.1, 6683.1, 6683.1, 6683.1, 6683.1]` |
| `1_add_112_measured_unweighted_native_files` | 10 | PR +2 (10) | **6014.759s** (25.06m, shard 1) | **10756.120s** (44.82m, shard 10) | `tests/test_generation_specificity_skill.py` (5918.253s) | `[6014.8, 6014.8, 6014.8, 6014.8, 6014.8, 6014.8, 6014.8, 6014.8, 6014.8, 6014.8]` |
| `1_add_112_measured_unweighted_native_files` | 6 | main current (6) | **10024.595s** (41.77m, shard 3) | **14723.154s** (61.35m, shard 2) | `tests/test_generation_specificity_skill.py` (5918.253s) | `[10024.6, 10024.6, 10024.6, 10024.6, 10024.6, 10024.6]` |
| `1_add_112_measured_unweighted_native_files` | 7 | main +1 (7) | **8592.510s** (35.80m, shard 3) | **12925.931s** (53.86m, shard 4) | `tests/test_generation_specificity_skill.py` (5918.253s) | `[8592.5, 8592.5, 8592.5, 8592.5, 8592.5, 8592.5, 8592.5]` |
| `2_update_all_134_measured_native_files` | 8 | PR current (8) / main +2 (8) | **7482.799s** (31.18m, shard 5) | **14134.214s** (58.89m, shard 6) | `tests/test_generation_specificity_skill.py` (5918.253s) | `[7482.8, 7482.8, 7482.8, 7482.8, 7482.8, 7482.8, 7482.8, 7482.8]` |
| `2_update_all_134_measured_native_files` | 9 | PR +1 (9) | **6651.378s** (27.71m, shard 3) | **11327.594s** (47.20m, shard 8) | `tests/test_generation_specificity_skill.py` (5918.253s) | `[6651.4, 6651.4, 6651.4, 6651.4, 6651.4, 6651.4, 6651.4, 6651.4, 6651.4]` |
| `2_update_all_134_measured_native_files` | 10 | PR +2 (10) | **5986.240s** (24.94m, shard 4) | **10166.243s** (42.36m, shard 10) | `tests/test_generation_specificity_skill.py` (5918.253s) | `[5986.2, 5986.2, 5986.2, 5986.2, 5986.2, 5986.2, 5986.2, 5986.2, 5986.2, 5986.2]` |
| `2_update_all_134_measured_native_files` | 6 | main current (6) | **9977.064s** (41.57m, shard 1) | **15003.569s** (62.51m, shard 2) | `tests/test_generation_specificity_skill.py` (5918.253s) | `[9977.1, 9977.1, 9977.1, 9977.1, 9977.1, 9977.1]` |
| `2_update_all_134_measured_native_files` | 7 | main +1 (7) | **8551.770s** (35.63m, shard 1) | **13131.805s** (54.72m, shard 4) | `tests/test_generation_specificity_skill.py` (5918.253s) | `[8551.8, 8551.8, 8551.8, 8551.8, 8551.8, 8551.8, 8551.8]` |
| `3_add_all_125_measured_unweighted_files` | 8 | PR current (8) / main +2 (8) | **7602.040s** (31.68m, shard 7) | **13889.088s** (57.87m, shard 6) | `tests/test_generation_specificity_skill.py` (5918.253s) | `[7602.0, 7602.0, 7602.0, 7602.0, 7602.0, 7602.0, 7602.0, 7602.0]` |
| `3_add_all_125_measured_unweighted_files` | 9 | PR +1 (9) | **6757.369s** (28.16m, shard 6) | **11942.688s** (49.76m, shard 8) | `tests/test_generation_specificity_skill.py` (5918.253s) | `[6757.4, 6757.4, 6757.4, 6757.4, 6757.4, 6757.4, 6757.4, 6757.4, 6757.4]` |
| `3_add_all_125_measured_unweighted_files` | 10 | PR +2 (10) | **6081.633s** (25.34m, shard 9) | **10917.469s** (45.49m, shard 10) | `tests/test_generation_specificity_skill.py` (5918.253s) | `[6081.6, 6081.6, 6081.6, 6081.6, 6081.6, 6081.6, 6081.6, 6081.6, 6081.6, 6081.6]` |
| `3_add_all_125_measured_unweighted_files` | 6 | main current (6) | **10136.052s** (42.23m, shard 4) | **14660.190s** (61.08m, shard 2) | `tests/test_generation_specificity_skill.py` (5918.253s) | `[10136.1, 10136.1, 10136.1, 10136.1, 10136.1, 10136.1]` |
| `3_add_all_125_measured_unweighted_files` | 7 | main +1 (7) | **8688.045s** (36.20m, shard 4) | **12513.942s** (52.14m, shard 4) | `tests/test_generation_specificity_skill.py` (5918.253s) | `[8688.0, 8688.0, 8688.0, 8688.0, 8688.0, 8688.0, 8688.0]` |
| `4_update_all_714_measured_files_from_run_42976790438` | 8 | PR current (8) / main +2 (8) | **8253.585s** (34.39m, shard 7) | **8253.585s** (34.39m, shard 7) | `tests/test_native_u3l_review_fixtures.py` (1846.102s) | `[8253.6, 8253.6, 8253.6, 8253.6, 8253.6, 8253.6, 8253.6, 8253.6]` |
| `4_update_all_714_measured_files_from_run_42976790438` | 9 | PR +1 (9) | **7336.520s** (30.57m, shard 6) | **7336.520s** (30.57m, shard 6) | `tests/test_shared_generation_runtime.py` (2298.329s) | `[7336.5, 7336.5, 7336.5, 7336.5, 7336.5, 7336.5, 7336.5, 7336.5, 7336.5]` |
| `4_update_all_714_measured_files_from_run_42976790438` | 10 | PR +2 (10) | **6602.868s** (27.51m, shard 6) | **6602.868s** (27.51m, shard 6) | `tests/test_shared_generation_runtime.py` (2298.329s) | `[6602.9, 6602.9, 6602.9, 6602.9, 6602.9, 6602.9, 6602.9, 6602.9, 6602.9, 6602.9]` |
| `4_update_all_714_measured_files_from_run_42976790438` | 6 | main current (6) | **11004.778s** (45.85m, shard 3) | **11004.778s** (45.85m, shard 3) | `tests/test_download/test_api_runner.py` (4449.413s) | `[11004.8, 11004.8, 11004.8, 11004.8, 11004.8, 11004.8]` |
| `4_update_all_714_measured_files_from_run_42976790438` | 7 | main +1 (7) | **9432.668s** (39.30m, shard 4) | **9432.668s** (39.30m, shard 4) | `tests/test_native_shared_attribution.py` (3828.030s) | `[9432.7, 9432.7, 9432.7, 9432.7, 9432.7, 9432.7, 9432.7]` |
| `5_update_all_714_measured_plus_impute_16_unstarted_unweighted_at_native_mean` | 8 | PR current (8) / main +2 (8) | **8455.639s** (35.23m, shard 5) | **8455.639s** (35.23m, shard 5) | `tests/test_d42_claude_d55.py` (3352.068s) | `[8455.6, 8455.6, 8455.6, 8455.6, 8455.6, 8455.6, 8455.6, 8455.6]` |
| `5_update_all_714_measured_plus_impute_16_unstarted_unweighted_at_native_mean` | 9 | PR +1 (9) | **7516.123s** (31.32m, shard 3) | **7516.123s** (31.32m, shard 3) | `tests/test_download/test_api_runner.py` (4449.413s) | `[7516.1, 7516.1, 7516.1, 7516.1, 7516.1, 7516.1, 7516.1, 7516.1, 7516.1]` |
| `5_update_all_714_measured_plus_impute_16_unstarted_unweighted_at_native_mean` | 10 | PR +2 (10) | **6764.511s** (28.19m, shard 2) | **6764.511s** (28.19m, shard 2) | `tests/test_report_admission.py` (5217.652s) | `[6764.5, 6764.5, 6764.5, 6764.5, 6764.5, 6764.5, 6764.5, 6764.5, 6764.5, 6764.5]` |
| `5_update_all_714_measured_plus_impute_16_unstarted_unweighted_at_native_mean` | 6 | main current (6) | **11274.183s** (46.98m, shard 2) | **11274.183s** (46.98m, shard 2) | `tests/test_report_admission.py` (5217.652s) | `[11274.2, 11274.2, 11274.2, 11274.2, 11274.2, 11274.2]` |
| `5_update_all_714_measured_plus_impute_16_unstarted_unweighted_at_native_mean` | 7 | main +1 (7) | **9663.587s** (40.26m, shard 5) | **9663.587s** (40.26m, shard 5) | `tests/test_d42_claude_d55.py` (3352.068s) | `[9663.6, 9663.6, 9663.6, 9663.6, 9663.6, 9663.6, 9663.6]` |

## 5. Reproduction Command

```sh
PYTHONDONTWRITEBYTECODE=1 python3 /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/scripts/adhoc/native_ci_shard_time_20261112.py
```

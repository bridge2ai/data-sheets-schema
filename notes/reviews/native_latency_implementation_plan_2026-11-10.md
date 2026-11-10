# Native Development & Validation Latency: Independent Audit and Implementation Plan (2026-11-10)

- **Worker**: `agy4` (Terminal window 6921, tab 1, `/dev/ttys010`; lead: Codex `/dev/ttys053`)
- **Assignment**: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.temp/generation-eta-20261110/notes/reviews/agy4_native_latency_assignment_2026-11-10.md` (SHA-256 `51c30f2a5bfc87c9933e8faea1639e9cb63d52490217487ea2f38d2304301b9f`)
- **Assessed Report**: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.temp/generation-eta-20261110/notes/reviews/native_development_latency_2026-11-10.md` (SHA-256 `c0164a3d41ad85112adb1ecb3f6d918580a2eb91ad86ca0d00619be0b594bbbd`)
- **Source Snapshots Inspected**:
  - Analysis worktree (`/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.temp/generation-eta-20261110`): branch `codex/generation-eta-evidence-20261110` at `911662277698b6a5cb1256875d81141b14372da9`
  - Codex native U1+U3 worktree (`/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-native-u1u3`): branch `codex/native-u1u3-combined-20261108` at `2c6537d0f84b6ac562887bd67bd564bd1f6c312e` (U3-L dependency-isolation fix), `70457f66e6f18c3e170c9752fcf6ed682aa93342` (U3-K measured public source), `03426fd33f3b311fa766e33c09d4474e5e6ac993` (initial U3-K cache/freshness commit), `a2241d4c6fa413e11cf07db59b999c5f2f95fc4b` (pre-U3-K baseline), and private D127 composition reference `c2feff1a1d44f0f4277facc9ed9ad5486866a6bb`
- **Scope**: Independent verification, call-graph and cost-model decomposition, root-cause taxonomy, and ranked implementation plan. No production, test, scanner, schema, workflow, or PR changes were executed during this assessment.

---

## 1. Executive Summary

### 1.1 Independent Assessment Verdict
The diagnosis in `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.temp/generation-eta-20261110/notes/reviews/native_development_latency_2026-11-10.md` is **quantitatively accurate on all primary timings, call counts, and SHA-256 evidence records**, and our direct inspection of the retained U3-K artifacts (`scratch-native-u1u3/u3k/`) and source tree (`2c6537d0f`) uncovered **four additional high-impact findings** that must be addressed in the implementation plan:

1. **Confirmed Primary Finding**: Launch-scoped schema caching (`03426fd33` + `70457f66e`, `schema-cache-proposal-r2.diff`) cut `schema_reconstruction` during `synthetic_launch` (`public_launch`) from **16 calls / 90.02 s CPU** (`control-pre-reservation-a2241d4c6`) to **3 calls / 27.39 s CPU** (`public-correction-70457f66e`) and **3 calls / 29.57 s CPU** (`public-omissions-70457f66e`). However, single-case public execution tests still take **628.14 s** (`public-correction-70457f66e`) and **658.60 s** (`public-omissions-70457f66e`) and fail at `native_subscription_guard_v2.py:430` (`ValueError: subscription observation is stale or future-dated`) before reaching `before_reservation()`.
2. **Additional Finding A — `make_case()` (`public_fixture`) Still Runs Uncached**: `tests/native_shared_fixture.py:make_case` does **not** enter `with authority.launch_derivations():`. Consequently, `public_fixture` still executes **13 `schema_reconstruction` calls (72.48 s CPU in correction, 72.36 s CPU in omissions)**, **5 `shared_registration_verified` calls (74.97 s CPU)**, **5 `execution_registration_verified` calls (63.93 s CPU)**, and **17 `preparer_verified` calls (60.58 s CPU)** before `launch_case` even starts.
3. **Additional Finding B — `authority_for()` Mints `capture_now` Before `read_capture` and Before 424 s of Pre-Acceptance Verification**: Inside `tests/utils/native_synthetic_evidence.py:authority_for` (line 144), `capture_now` is stamped before `capture.read_capture` (line 176, which itself takes ~15 s to re-verify registration), and before `launch_case` spends **423.95 s wall** (`public-correction-70457f66e`) in repeated pre-acceptance verification (`shared_registration_verified` x8, `execution_registration_verified` x13, `preparer_verified` x20, `controller_prewarm` 117.66 s wall) plus **70.29 s wall** inside `load_current` before `SubscriptionGuard.__init__` checks `_fresh()` (`max_age_seconds = 300 s`). By the time `_fresh()` runs at `native_subscription_guard_v2.py:430`, **477.54 s** has elapsed since `captured_at`.
4. **Additional Finding C — Commit `03426fd33` Introduced 13 Regressions in `u4b-70457f66e` (`test_native_u4b_a5_scanner.py` x12 and `test_native_u4b_addendum_authority.py` x1)**:
   - Copying the 10-line D114 `spec._native_shared_runtime_capture = runtime_capture` + `limits_basis` block into `native_execution_registration_v2.py:prepare_synthetic` (in addition to `prepare`) made `source.count(helper.ANCHOR + helper.INSERTION) == 2` instead of `1` and caused `scan.derive_native_shared_route` to fail with `ConfigError: api meaning not derived: separate native shared render route (unsupported v2 render producer: prepare)` across **12 tests in `tests/test_native_u4b_a5_scanner.py`**.
   - Changing `native_shared_execution_orchestration.py:launch` from calling `load_current(...)` before `engine.launch(...)` to calling `select_current(...)` (which is data-only and performs no freshness check) caused `tests/test_native_u4b_addendum_authority.py::test_expired_capture_stays_spent_and_refuses_before_generation_reservation` to fail because `engine.launch` (monkeypatched to `forbidden`) was invoked before expired-capture refusal.
5. **Additional Finding D — All 13 Test Failures in `failure-lifecycle-70457f66e` (5/5), `failure-readback-70457f66e` (4/4), and `failure-reservation-70457f66e` (4/8) Are the Exact Same Freshness/Margin Expiry**: Every failure in `tests/test_native_shared_execution_failure.py` at `70457f66e` is either `ValueError: subscription observation is stale or future-dated` (`>300 s`) or `ValueError: subscription pre-reservation freshness margin is insufficient` (`>210 s`) after 445–868 s per test.

### 1.2 Summary of Recommended Architecture & Expected Impact
We recommend a four-phase implementation plan (**P0 -> P1 -> P2 -> P3**) centered on **Option B (Launch- and Fixture-Scoped Content-Addressed Verification Memoization with Live Boundary Stat/Hash Re-Checks)** combined with **Targeted Option A (Pre-Engine Non-Consuming Freshness Gate + Post-Prewarm Final Acceptance + `authority_for` Timestamp Ordering)** and **Option C (Reusable Base Fixture Templates for Non-Mutating Cohorts)**:

| Metric | Pre-U3-K Baseline (`a2241d4c6`) | Current U3-K (`70457f66e`) | Target After P0 + P1 | Target After P0 + P1 + P2 |
| :--- | ---: | ---: | ---: | ---: |
| `make_case` (`public_fixture`) wall time | ~169.8 s | 163.1–167.2 s | **18–25 s** | **8–14 s** |
| `launch_case` (`public_launch`) pre-reservation wall time | ~527.1 s | 460.9–495.5 s (fails) | **20–30 s** | **12–20 s** |
| Single public case (`test_native_shared_execution.py`) wall time | 696.95 s (fails) | 628.14–658.60 s (fails) | **38–55 s (passes)** | **22–35 s (passes)** |
| Subscription age at `before_reservation()` (limit: `<= 210 s`) | >450 s (stale) | 477.5 s (stale at 300 s) | **20–32 s (>178 s margin)** | **12–20 s (>190 s margin)** |
| `schema_reconstruction` calls per test (`fixture + launch`) | `13 + 16 = 29` | `13 + 3 = 16` | **`1 + 1 = 2`** (or `1` shared) | **`1`** |
| `preparer_verified` calls per test (`fixture + launch`) | `17 + 20 = 37` | `17 + 20 = 37` | **`2` cold + `35` fast-stat** | **`1–2` cold + fast-stat** |
| `shared_registration_verified` calls per test (`fixture + launch`) | `5 + 8 = 13` | `5 + 8 = 13` | **`1` cold + `12` fast-stat** | **`1` cold + fast-stat** |
| `u4b` cohort (`1,089` cases) wall time & status | ~515 s | 514.97 s (13 failed) | **<360 s (1,089 passed)** | **<180 s (1,089 passed)** |
| `failure-*` 3 cohorts (`17` cases total) wall time & status | >5,000 s (fails) | 5,184 s (13 failed) | **450–700 s (17 passed)** | **240–400 s (17 passed)** |
| Post-U3 quiet-host 21-run campaign (`native_u3_plan`) | ~4.0 hours | ~3.7 hours (broken) | **~18–25 minutes** | **~12–16 minutes** |

---

## 2. Verification of Current Evidence

We audited every claim in `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.temp/generation-eta-20261110/notes/reviews/native_development_latency_2026-11-10.md` against the raw JSON/log artifacts under `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3k/`, `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/plans/reviews/native_u3k_2026-11-09.md`, and `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.temp/generation-eta-20261110/notes/reviews/generation_eta_2026-11-10/timestamps.json`.

### 2.1 Claim-by-Claim Audit Matrix

| Claim in `native_development_latency_2026-11-10.md` | Verification Status | Retained Evidence Source & Exact Values | Notes / Nuances Added by `agy4` Audit |
| :--- | :--- | :--- | :--- |
| U3-A through U3-J2 took ~35.9h across ~3 days (`2026-11-07` to `2026-11-10`), vs ~10m–2h for PR #5709/#5710/#5711 | **Confirmed** | `generation_eta_2026-11-10/timestamps.json` (`u3_subphases_from_status_md`), `README.md` | Note: `native_u3k_2026-11-09.md` was updated at `2026-11-10T02:27:19Z` (SHA-256 `b43e62923f6516c08394b0d79376dfe97990b9bce728cc29814f673d0d2cc058`) after `timestamps.json` was generated (`01:09:49Z`). |
| Pre-reservation control/profile runs (`a2241d4c6`) took `696.95 s` and `675.08 s` (`705.23 s` and `683.48 s` supervisor) | **Confirmed** | `u3k/baseline-profile-summary.json` (`b2390517...`), `control-pre-reservation-a2241d4c6/supervisor.json` | Both failed at `native_execution_orchestration.py:345` (`load_current` -> `SubscriptionGuard.__init__` -> `ValueError: subscription observation is stale or future-dated`). |
| Launch-phase `schema_reconstruction` dropped from `16` calls / `90.02 s` CPU (`a2241d4c6`) to `3` calls / `27.39 s` CPU (`public-correction-70457f66e`) and `3` calls / `29.57 s` CPU (`public-omissions-70457f66e`) | **Confirmed** | `u3k/public-pair-grouped-summary.json` (`fe4a51f0...`), `u3k/public-pair-summary.json` (`19f70e3f...`) | Crucially, `public_fixture` (`make_case`) was **not** wrapped in `launch_derivations()`, so `public_fixture` still ran `13` `schema_reconstruction` calls (`72.48 s` / `72.36 s` CPU). |
| Public pair at `70457f66e` took `628.14 s` (`636.33 s` supervisor) and `658.60 s` (`666.35 s` supervisor) and failed with `subscription observation is stale or future-dated` | **Confirmed** | `u3k/public-correction-70457f66e/pytest.log`, `u3k/public-omissions-70457f66e/pytest.log`, `u3k/correction-summary.json` | Failure occurred at `native_execution_orchestration.py:366` (`accept_current_selection` -> `load_current` -> `SubscriptionGuard.__init__`), before reaching `before_reservation()` at line 385. |
| Elapsed time from `captured_at` (`1794270296.47657`) to `SubscriptionGuard.__init__` (`1794270774.020969`) in `public-correction-70457f66e` was `477.54 s` (`177.54 s` over `300 s`) | **Confirmed** | `u3k/correction-summary.json` (`12eb360c...`) | `authority_for()` stamps `capture_now` at line 144, then runs `read_capture` (~15 s) inside `make_case()`, so `~15 s` is already gone when `make_case()` returns; `launch_case` then spends `423.95 s` before `accept_current_selection` and `38.6 s` inside `load_current` before `_fresh()`. |
| Remaining `70457f66e` cohort wall times: `failure-lifecycle` `1,846.82 s` (`rc=125`), `failure-readback` `1,531.65 s` (`rc=1`), `failure-reservation` `1,807.47 s` (`rc=1`), `u4b` `514.97 s` (`rc=1`), `shared-policy` `29.10 s` (`rc=0`), `execution-v2` `16.43 s` (`rc=0`), `hooks` `10.17 s` (`rc=0`), `frontdoor-canary` `50.25 s` (`rc=0`) | **Confirmed** | `u3k/*/supervisor.json` and `u3k/validation-rollup-canary.json` (`7eb4191e...`) | Total wall time across the 11 recorded `70457f66e` cohort runs is **6,695.07 s (1.86 hours)**, and `failure-*` + `u4b` had **26 failed test cases** (`5 + 4 + 4 + 13`). |
| `failure-lifecycle-70457f66e` `rc=125` was caused by 19 `fairscape_models/__pycache__/*.pyc` files (47,828 bytes) in the shared dependency tree, fixed by `2c6537d0f` (`dependency-isolation-canary-2c6537d0f`, `25.88 s`, `rc=0`) | **Confirmed** | `u3k/dependency-stop-audit.json` (`fb82c312...`), `u3k/dependency-isolation-canary-2c6537d0f/supervisor.json` | Spawned child processes with scrubbed environments strip `PYTHONDONTWRITEBYTECODE=1`, causing Python 3.12 to write `.pyc` files into whatever `PYTHONPATH` tree holds `fairscape_models`. |

---

## 3. Exact Hot-Path Call-Graph and Cost Model

### 3.1 Phase-Separated Call Counts and CPU/Wall Breakdown (`a2241d4c6` vs `70457f66e`)

Data extracted directly from `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3k/public-pair-grouped-summary.json` and `baseline-profile-summary.json`:

#### Table 3A: `public_fixture` (`make_case` in `tests/native_shared_fixture.py`)

| Instrumentation Category | `control-a2241d4c6` Calls / CPU (s) | `profile-a2241d4c6` Calls / CPU (s) | `public-correction-70457f66e` Calls / CPU (s) / Wall (s) | `public-omissions-70457f66e` Calls / CPU (s) / Wall (s) | Why It Occurs in `make_case()` |
| :--- | ---: | ---: | ---: | ---: | :--- |
| **`public_fixture` (total)** | `1` / `157.82` (`169.81` wall) | `1` / `154.02` (`165.43` wall) | `1` / `152.64` / `167.20` | `1` / `150.46` / `163.05` | Full synthetic fixture creation per test function |
| `shared_registration_verified` | `5` / `75.77` | `5` / `74.47` | `5` / `74.97` / `81.28` | `5` / `73.55` / `79.22` | `make_case:62` (1) + `authority_for:121,132,134,176` (4) |
| `execution_registration_verified` | `5` / `64.61` | `5` / `63.61` | `5` / `63.93` / `69.43` | `5` / `62.82` / `67.74` | 1 inside each `shared_registration.verified` call |
| `preparer_verified` (`verify_preparer`) | `17` / `62.10` | `17` / `60.69` | `17` / `60.58` / `66.65` | `17` / `59.56` / `64.59` | `build_native_fixture` (4) + `runtime_for` (4) + `synthetic_registration` (4) + `execution_registration_verified` (5) |
| `selection_capture` | `74` / `76.55` | `74` / `75.02` | `74` / `74.98` / `79.64` | `74` / `74.12` / `77.89` | Repeated `selection_derivations` / `runtime_capture` construction |
| `selection_rebuild` | `74` / `74.47` | `74` / `73.00` | `74` / `72.96` / `77.45` | `74` / `72.18` / `75.81` | Rebuilding schema/selection inside `selection_capture` |
| `schema_cache_lookup` | `0` / `0.00` | `0` / `0.00` | `74` / `72.73` / `77.19` | `74` / `71.95` / `75.56` | `make_case` is outside `launch_derivations()`, so only per-`selection_derivations` cache applies |
| **`schema_reconstruction`** | **`13` / `74.16`** | **`13` / `72.70`** | **`13` / `72.48` / `76.92`** | **`13` / `71.71` / `75.31`** | **13 cold LinkML `SchemaView` / `RunSpec` reconstructions (`26` `schema_capture` calls, `54.99 s` CPU)** |

#### Table 3B: `public_launch` (`launch_case` -> `execute.synthetic_launch`)

| Instrumentation Category | `control-a2241d4c6` Calls / CPU (s) | `profile-a2241d4c6` Calls / CPU (s) | `public-correction-70457f66e` Calls / CPU (s) / Wall (s) | `public-omissions-70457f66e` Calls / CPU (s) / Wall (s) | Why It Occurs in `synthetic_launch()` |
| :--- | ---: | ---: | ---: | ---: | :--- |
| **`public_launch` (total)** | `1` / `489.64` (`527.12` wall) | `1` / `474.24` (`509.63` wall) | `1` / `431.75` / `460.92` | `1` / `461.37` / `495.52` | Aborts at `SubscriptionGuard.__init__` before reservation |
| `shared_registration_verified` | `6` / `217.56` | `6` / `209.26` | `8` / `216.72` / `231.26` | `8` / `246.66` / `265.17` | Increased from 6 to 8 at `70457f66e` because `inspect_current_selection` added 2 calls before `accept_current_selection` |
| `execution_registration_verified` | `11` / `265.87` | `11` / `256.81` | `13` / `253.99` / `271.22` | `13` / `281.45` / `302.50` | 8 in `shared_registration_verified` + 3 in `admission.verified` + 1 in `CallbackAdapter` + 1 in `prewarm_before_acceptance` |
| `preparer_verified` (`verify_preparer`) | `18` / `195.88` | `18` / `189.24` | `20` / `175.79` / `188.62` | `20` / `204.88` / `221.37` | 13 in `execution_registration_verified` + 7 in `CallbackAdapter` / `prewarm_before_acceptance` (`compose` / `reconstruct_composition`) |
| `selection_capture` | `69` / `81.90` | `69` / `79.66` | `81` / `22.35` / `23.70` | `81` / `24.16` / `25.84` | Fast when `launch_derivations()` hits, slow on misses |
| `selection_rebuild` | `72` / `90.26` | `72` / `88.14` | `84` / `31.36` / `33.24` | `84` / `33.76` / `36.12` | Includes 3 extra rebuilds inside `controller_prewarm` |
| `schema_cache_lookup` | `0` / `0.00` | `0` / `0.00` | `82` / `19.41` / `20.57` | `82` / `21.22` / `22.69` | `79` cache hits + `3` cache misses inside `launch_derivations()` |
| **`schema_reconstruction`** | **`16` / `90.02`** | **`16` / `87.91`** | **`3` / `27.39` / `29.01`** | **`3` / `29.57` / `31.65`** | **1 initial cold populate + 2 misses in `CallbackAdapter` / `prewarm_before_acceptance` temp schema roots** |
| `controller_prewarm` | `0` (ran after `load_current` at `a2241d4c6`? No, failed before it!) | `0` | `1` / `112.26` / `117.66` | `1` / `109.56` / `114.73` | Moved BEFORE `accept_current_selection` by `03426fd33`, adding ~115–118 s wall before freshness check! |
| `accept_saved_capture` (`load_current`) | `1` / `115.69` (`124.22` wall) | `1` / `111.75` (`119.52` wall) | `1` / `65.52` / `70.29` | `1` / `74.08` / `79.43` | Calls `read_capture_for_event` -> `_authority` (2x `shared_registration.verified`) before `SubscriptionGuard.__init__` |

### 3.2 Critical Mechanistic Insight from Comparing `a2241d4c6` vs `70457f66e`
Look closely at why `public-correction-70457f66e` (`460.92 s` launch wall) only saved `~66 s` over `control-pre-reservation-a2241d4c6` (`527.12 s` launch wall) despite `schema_reconstruction` saving `~63 s` CPU, and why `captured_at` age at `SubscriptionGuard.__init__` remained **477.54 s**:
1. At `a2241d4c6`, `native_shared_execution_orchestration.py:launch` called `load_current` at the **start** of `_launch` (line 345), **before** `admission.admit`, `CallbackAdapter`, and `prewarm_before_acceptance`. Wait: why did `a2241d4c6` take 527 s before failing at line 345? Because at `a2241d4c6` without `launch_derivations()`, each of the 6 `shared_registration_verified` calls up to line 345 rebuilt the schema 2–3 times (`16` `schema_reconstruction` calls = `90 s` CPU, plus `265 s` in `execution_registration_verified`).
2. At `03426fd33` / `70457f66e`, `freshness-order-proposal.diff` replaced `load_current` before `engine.launch` with `select_current` (no freshness check), added `inspect_current_selection` at line 345 (which runs **2 full `shared_registration_verified` calls**), and deferred `accept_current_selection` (`load_current`, which runs **another 2 full `shared_registration_verified` calls**) until line 366—**after** `admission.admit` (2x `execution_registration_verified`), `CallbackAdapter.__init__` (1x `execution_registration_verified` + 3x `verify_preparer` + 1x temp-root `schema_reconstruction`), and `prewarm_before_acceptance` (`117.66 s` wall)!
3. In other words, moving `load_current` after `prewarm_before_acceptance` **added 4 extra `execution_registration_verified` calls, 2 extra `shared_registration_verified` calls, and 117.66 s of `controller_prewarm` into the clock window between `captured_at` and `SubscriptionGuard.__init__`**, completely wiping out the ~63 s saved by `launch_derivations()` schema caching!

### 3.3 Exact Call-Graph Multiplier Map (`make_case` + `synthetic_launch`)
Below is the exact file-and-line trace showing how a single public test invokes `verify_preparer` **37 times** (would be **41 times** if lines 369–379 were reached), `execution_registration.verified` **18 times** (**22 times** if lines 369–379 were reached), and `shared_registration.verified` **13 times** (**17 times** if lines 369–379 were reached):

```
[Phase 1: make_case(tmp_path) in tests/native_shared_fixture.py:39-108 — outside launch_derivations()]
 ├── build_native_fixture(tmp_path) [tests/native_Execution_fixture.py]
 │    └── 4x verify_preparer + 3x schema_reconstruction (cold)
 ├── runtime_for(base) [tests/utils/native_synthetic_evidence.py:29-80]
 │    └── 4x verify_preparer + 2x schema_reconstruction (cold)
 ├── synthetic_registration(base, runtime) [native_synthetic_evidence.py:83-110]
 │    └── _registration_body -> 4x verify_preparer + 3x schema_reconstruction (cold)
 ├── registration.verified(base.root, ...) [native_shared_fixture.py:62]               [shared_reg #1, exec_reg #1, preparer #13, schema_recon #9]
 └── authority_for(base, runtime, shared_registration) [native_synthetic_evidence.py:113-192]
      ├── registration.verified(...) [line 121]                                         [shared_reg #2, exec_reg #2, preparer #14, schema_recon #10]
      ├── activate_capture_word(...) [line 132 -> _authority -> registration.verified]  [shared_reg #3, exec_reg #3, preparer #15, schema_recon #11]
      ├── capture._authority(...) [line 134 -> registration.verified]                   [shared_reg #4, exec_reg #4, preparer #16, schema_recon #12]
      ├── capture_now = _iso(clock) [line 144]  <=== CAPTURED_AT TIMESTAMP MINTED HERE
      └── capture.read_capture(...) [line 176 -> _authority -> registration.verified]   [shared_reg #5, exec_reg #5, preparer #17, schema_recon #13] (~15s burned AFTER captured_at!)

[Phase 2: launch_case(case) -> execute.synthetic_launch in src/data_sheets_schema/native_shared_execution_orchestration.py:92-122]
 └── with authority.launch_derivations(): [line 109]
      ├── registration.verified(...) [line 112]                                         [shared_reg #6, exec_reg #6, preparer #18, schema_recon #14 (cold #1 in launch)]
      ├── capture.select_current(...) [line 120] (reads JSON only; NO freshness check -> breaks U4b test!)
      └── engine.synthetic_launch(...) [native_execution_orchestration.py:268-311]
           ├── registration.verified(...) [line 290]                                    [shared_reg #7, exec_reg #7, preparer #19]
           └── _launch(..., synthetic=True) [native_execution_orchestration.py:314-480]
                ├── registration.verified(...) [line 328]                               [shared_reg #8, exec_reg #8, preparer #20]
                ├── authorizations(...) [line 330 -> admission.verified]                [exec_reg #9, preparer #21]
                ├── inspect_current_selection(...) [line 345 -> context(current=False)]
                │    ├── read_capture_for_event -> _authority [capture.py:299]          [shared_reg #9, exec_reg #10, preparer #22]
                │    └── read_capture -> _authority [capture.py:282]                    [shared_reg #10, exec_reg #11, preparer #23]
                ├── _unchanged() [line 342 -> registration.verified]                    [shared_reg #11, exec_reg #12, preparer #24]
                ├── admission.admit(...) [line 352 -> 2x admission.verified]            [exec_reg #13, #14, preparer #25, #26]
                ├── CallbackAdapter(...) [line 363]                                     [exec_reg #15, preparer #27..#30, schema_recon #15 (temp root miss #2)]
                ├── controller.prewarm_before_acceptance() [line 364] (117.66 s wall!)  [exec_reg #16, preparer #31..#35, schema_recon #16 (temp root miss #3)]
                ├── accept_current_selection(...) [line 366 -> load_current -> context(current=True)]
                │    ├── read_capture_for_event -> _authority [capture.py:299]          [shared_reg #12, exec_reg #17, preparer #36]
                │    ├── read_capture -> _authority [capture.py:282]                    [shared_reg #13, exec_reg #18, preparer #37]
                │    └── load_guard -> SubscriptionGuard.__init__ [guard_v2.py:430]     <=== FAILS HERE (477.54 s > 300 s max_age)
                ├── [NOT REACHED] _unchanged() [line 369 -> 2x shared_reg.verified]     [would be shared_reg #14, #15]
                ├── [NOT REACHED] _unchanged() [line 371 -> 1x shared_reg.verified]     [would be shared_reg #16]
                ├── [NOT REACHED] _unchanged() [line 379 -> 1x shared_reg.verified]     [would be shared_reg #17]
                └── [NOT REACHED] subscription.before_reservation() [line 385]          [requires remaining >= 90 s, i.e., elapsed <= 210 s]
```

### 3.4 What Each Verification Layer Repeats on Unchanged Bytes
Why does a single `shared_registration.verified` call still cost **~27–31 s** inside `public_launch` even when `schema_reconstruction` hits the `launch_derivations()` cache?
1. **`native_shared_registration_orchestration.py:verified` (lines 723–878)**:
   - Calls `execution_registration.verified(root, ...)` (~19–21 s).
   - Calls `probe.verified(root, ...)` (`native_u4b_probe_sequence.py`), which re-verifies the probe sequence, binary identity, and 8 stage records.
   - Calls `_verify_Execution_contract`, `_verify_runtime_envelope`, `selection_derivations`, and `limits_basis`, re-parsing YAML/JSON artifacts and re-computing contract digests.
2. **`native_execution_registration_v2.py:verified` (lines 320–455)**:
   - Calls `preparer.verify_preparer(root, ...)` (~8.8–10.2 s).
   - Reconstructs and validates the v2 registration payload, D114 runtime capture, and execution contract against the preparer output.
3. **`native_execution_preparer.py:verify_preparer` / `compose` / `reconstruct_composition`**:
   - Re-reads and parses all composition/packet/rubric/prompt/schema files, runs `scan.derive_native_shared_route` (which parses Python ASTs across `src/data_sheets_schema/native_*.py`!), and re-verifies every file pin and SHA-256 digest.
4. **`native_shared_controller_orchestration.py:prewarm_before_acceptance` (117.66 s wall)**:
   - Invokes `CallbackAdapter` / `preloaded_callbacks` (`native_shared_callback_loading.py`) and `stage_attribution.live` (`native_shared_stage_attribution.py`), which construct a temporary directory (`TemporaryDirectory`), copy schema files into that temp root (causing a **`launch_derivations()` cache miss** because `os.path.realpath(root)` is a brand-new temp path!), and run multiple `verify_preparer` / `reconstruct_composition` cycles.

---

## 4. Root-Cause Taxonomy (R1–R7)

| ID | Root Cause | Exact Files & Functions | Quantitative Impact | Classification |
| :--- | :--- | :--- | :--- | :--- |
| **R1** | **Multiplicative Full-Chain Verification Across Orchestration Layers**: `shared_registration.verified` (13–17x), `execution_registration.verified` (18–22x), `verify_preparer` (37–41x), and `probe.verified` re-execute heavy AST/YAML/contract/composition reconstruction on identical on-disk files within a single fixture+launch flow. | `src/data_sheets_schema/native_shared_registration_orchestration.py:verified`, `native_execution_registration_v2.py:verified`, `native_subscription_capture.py:_authority`, `native_subscription_admission.py:verified`, `native_execution_orchestration.py:_launch` | **~380–420 s CPU** per public test (`~60 s` in fixture + `~320 s` in launch) | Production verification architecture bottleneck |
| **R2** | **Incomplete Scope & Temp-Root Keying of `launch_derivations()` Schema Cache**: (a) `make_case()` does not enter `launch_derivations()`, causing 13 cold `schema_reconstruction` calls (`72.5 s` CPU); (b) `CallbackAdapter` and `prewarm_before_acceptance` materialize temporary schema directories whose `realpath(root)` differs from the main root, causing 2 additional cold `schema_reconstruction` misses (`~19 s` CPU) inside `launch_derivations()`. | `tests/native_shared_fixture.py:make_case`, `src/data_sheets_schema/native_shared_authority.py:cached_schema_derivation`, `native_shared_callback_loading.py`, `native_shared_stage_attribution.py` | **~91.5 s CPU** per public test (`72.5 s` in fixture + `~19 s` in launch temp-root misses) | Cache-scope and cache-key defect |
| **R3** | **Freshness-Window Inversion Between `captured_at` Minting, Pre-Engine Check, and Post-Prewarm Acceptance**: (a) `authority_for()` stamps `capture_now` (line 144) before `read_capture` (line 176, ~15 s); (b) `03426fd33` deferred `load_current` after 424 s of launch verification + `prewarm_before_acceptance` (`117.7 s`), causing `SubscriptionGuard.__init__` to fail at `477.54 s > 300 s`; (c) removing the pre-engine freshness check broke `test_expired_capture_stays_spent_and_refuses_before_generation_reservation`. | `tests/utils/native_synthetic_evidence.py:authority_for`, `src/data_sheets_schema/native_shared_execution_orchestration.py:launch/synthetic_launch`, `native_execution_orchestration.py:_launch`, `native_subscription_capture.py:select_current/load_current` | Causes **100% failure rate** on `public-correction`, `public-omissions`, `failure-lifecycle` (5/5), `failure-readback` (4/4), `failure-reservation` (4/8), and 1 `u4b` test | Freshness lifecycle & test-setup ordering defect |
| **R4** | **Duplicate D114 Anchor Block in `native_execution_registration_v2.py` Breaking Scanner Route Derivation**: Commit `03426fd33` duplicated the 10-line `spec._native_shared_runtime_capture = runtime_capture` + `limits_basis` block into `prepare_synthetic` (lines 285–296) as well as `prepare` (lines 246–257). `scan.derive_native_shared_route` rejects `prepare` as an unsupported v2 render producer when the anchor block appears twice. | `src/data_sheets_schema/native_execution_registration_v2.py:246-257, 285-296`, `tests/test_native_u4b_a5_scanner.py` | Causes **12 test failures** in `u4b-70457f66e` (`test_native_u4b_a5_scanner.py`) | U3-K regression in AST scanner contract |
| **R5** | **Unconditional `sys.setprofile` Consumer-Scope Observer Across Full Launch**: `launch_case` (`tests/test_native_shared_execution.py:92`) wraps the entire `execute.synthetic_launch` call in `with observe_consumer_calls(forbidden, forbid=True):`, firing a Python-level profile hook on every function call/return across tens of millions of calls. | `tests/test_native_shared_execution.py:92`, `tests/utils/native_shared_consumer_scope.py:30-56` | **~8–15% Python interpreter overhead** across every function call during `launch_case` | Test instrumentation overhead |
| **R6** | **Child-Process Bytecode Contamination in Shared Dependency Trees**: Child Python processes launched with scrubbed env (`PYTHONDONTWRITEBYTECODE` removed) write `.pyc` files into shared `PYTHONPATH` directories (`fairscape_models/__pycache__`), tripping `origins-after.json` (`rc=125`). | `scripts/adhoc/run_native_u3k_20261109.py` (fixed in `2c6537d0f`), child-process invocation in native harness | Caused `rc=125` abort after `1,846.82 s` in `failure-lifecycle-70457f66e` | Environment/isolation defect (fixed in `2c6537d0f`; needs permanent test guard) |
| **R7** | **CI Linux Multiplier (2.729x) & Unweighted Native Test Files in Shard Balancer**: Native tests not listed in `utils/ci_test_durations.json` receive a ~1–2 s median fallback estimate in `utils/pytest_shard.py:_estimates`, risking multi-file packing on 4-vCPU Linux shards where wall times scale by **2.729x** (`bc1_g2_measured_ratio_scaling_20261103`). | `utils/ci_test_durations.json`, `utils/pytest_shard.py`, `.github/workflows/main.yaml` | A 600 s macOS test becomes **~1,637 s (27.3 min)** on Linux CI; a 1,800 s file exceeds the **45-min PR shard timeout** | CI capacity & shard-balancing risk |

---

## 5. Evaluation of Architectural Options & Ranked Implementation Plan

### 5.1 Architectural Options Matrix (Options A, B, C, D)

| Option | Description | Pros | Cons / Risks | Verdict |
| :--- | :--- | :--- | :--- | :--- |
| **Option A** | **Pure Ordering / No-Cache Reordering**: Keep all verification uncached; move freshness checks or reorder `authority_for` / `prewarm_before_acceptance`. | Zero caching state; simple diff. | Even if `captured_at` is minted at the end of `authority_for`, `launch_case` still takes **461–495 s** (`>300 s` `max_age` and `>210 s` pre-reservation limit). And if `load_current` runs before `prewarm_before_acceptance`, `before_reservation()` at line 385 STILL fails because `prewarm_before_acceptance` (118 s) + prior verifications (300+ s) exceed the 210 s pre-reservation window! | **Insufficient alone; necessary as a complement to Option B** for `authority_for` timestamp ordering and pre-engine refusal. |
| **Option B** | **Scoped Content-Addressed Verification Memoization with Live Boundary Stat/Byte Re-Verification**: Cache expensive derived verification products (`schema_derivation`, `verify_preparer`, `execution_registration.verified`, `shared_registration.verified`, `probe.verified`) inside an explicit context (`launch_derivations`), keyed by **content SHA-256 digests of all governed on-disk files + source-state token + runtime arguments**, and re-read/stat the governed on-disk files on every call to detect any mutation, symlink swap, or permission change. | Eliminates 90%+ of redundant CPU (`~500 s -> ~35 s`) while **preserving every security, refusal, and post-verification mutation check** (`_unchanged()`, symlink refusal, permission checks, content tamper refusal). | Must ensure cache keys include every governed file's live content SHA-256 and stat mode/link-target check so no mid-launch file tamper can pass via a stale cache entry. | **Primary Recommended Architecture (Core of P1).** |
| **Option C** | **Session/Module-Scoped Base Fixture Template + Fast CoW/Copy Per Test**: Build the immutable base fixture (`build_native_fixture` + `runtime_for` + `synthetic_registration`) once per test module/session in a read-only template directory, then `shutil.copytree` into each test's `tmp_path` before applying test-specific mutations or `authority_for`. | Cuts `make_case` setup across multi-test files (`test_native_shared_execution_failure.py` has 17 cases!) from `17 x 165 s = 2,805 s` to `1 x 25 s + 17 x 2 s = ~59 s`. | Must never share mutable state across tests; each test must get its own isolated `tmp_path` copy and fresh `authority_for` capture/guard with its own clock timestamp. | **Recommended for P2 (Multi-Test Cohort Acceleration).** |
| **Option D** | **Split Monolithic Verification into Fast Structural Hash Check vs Full Reconstruction**: Refactor `shared_registration`, `execution_registration_v2`, and `preparer` APIs into separate `verified_full()` and `verified_fast()` entrypoints. | Makes fast vs full checks explicit in the call graph. | Intrusive API surface change across `native_shared_*` and `native_execution_*` modules; risks breaking AST/source-inspection tests (`test_native_u4b_a5_scanner.py` and contract scanners) that inspect exact function calls and signatures. | **Reject as a separate API split; subsume its fast-hash verification mechanism inside Option B's existing `.verified()` entrypoints.** |

---

### 5.2 Ranked Implementation Phases (P0 -> P1 -> P2 -> P3)

#### Phase P0: Fix U3-K Regressions (`u4b` 13 Failures) & Correct Freshness Lifecycle Ordering
**Objective**: Repair the 13 regressions introduced by `03426fd33` in `test_native_u4b_a5_scanner.py` (12) and `test_native_u4b_addendum_authority.py` (1), and stop burning freshness budget inside `authority_for()`.

1. **Target 1 — Remove Duplicate D114 Insertion Block in `src/data_sheets_schema/native_execution_registration_v2.py`**:
   - **Problem**: `03426fd33` (`schema-cache-proposal-r2.diff`) inserted the 10-line D114 `spec._native_shared_runtime_capture = runtime_capture` + `limits_basis` block into `prepare_synthetic` (lines 285–296) in addition to `prepare` (lines 246–257). That broke `tests/test_native_u4b_a5_scanner.py` (`source.count(helper.ANCHOR + helper.INSERTION) == 1` and `scan.derive_native_shared_route`).
   - **Exact Change**: In `src/data_sheets_schema/native_execution_registration_v2.py:prepare_synthetic`, do **not** duplicate the literal `helper.ANCHOR + helper.INSERTION` text block. Instead, factor the runtime-capture attachment into a helper call or pass the pre-computed `runtime_capture` through `_prepare_common` / `selection_derivations` without duplicating the scanner-anchored statement block in `prepare_synthetic`.
   - **Invariants Preserved**: `source.count(helper.ANCHOR + helper.INSERTION) == 1` in `native_execution_registration_v2.py`; `scan.derive_native_shared_route` returns the exact expected route; `prepare_synthetic` still benefits from `launch_derivations()` schema caching.

2. **Target 2 — Restore Pre-Engine Expired-Capture Refusal Without Prematurely Consuming Valid Guard Margin in `src/data_sheets_schema/native_shared_execution_orchestration.py` and `src/data_sheets_schema/native_subscription_capture.py`**:
   - **Problem**: `test_expired_capture_stays_spent_and_refuses_before_generation_reservation` requires `execution.launch` to refuse an already-expired or spent capture **before** invoking `engine.launch`. However, `03426fd33` replaced `load_current` before `engine.launch` with `select_current` (which only reads JSON and does not validate guard state or clock freshness).
   - **Exact Change**:
     - Enhance `select_current` (or call `inspect_current_selection` / a non-consuming ` precheck_current` in `native_shared_execution_orchestration.py:launch` and `synthetic_launch` before `engine.launch`) so that **before** `engine.launch` is called, it verifies:
       1. The capture and guard files exist and are regular files (`read_regular`),
       2. The guard state is unspent and matches the capture binding, and
       3. `SubscriptionGuard.before_dispatch(check_only=True)` passes against the live clock (`0 <= now - captured_at <= max_age_seconds`).
     - Then, inside `engine._launch` (`native_execution_orchestration.py:366`), `accept_current_selection` (`load_current(current=True)`) performs the state-consuming acceptance immediately before the final `_unchanged()` checks and `subscription.before_reservation()` (line 385).
   - **Invariants Preserved**: Expired or spent captures are refused **before** `engine.launch` is entered (satisfying `test_expired_capture_stays_spent_and_refuses_before_generation_reservation`), while valid captures are both checked at entry and re-verified/consumed immediately before reservation after `prewarm_before_acceptance`.

3. **Target 3 — Mint `capture_now` After Pre-Capture Verification in `tests/utils/native_synthetic_evidence.py:authority_for`**:
   - **Problem**: `authority_for()` (`lines 113–192`) calls `registration.verified` three times (lines 121, 132, 134), stamps `capture_now = _iso(clock)` at line 144, and then calls `capture.read_capture` at line 176 (which runs a 4th `registration.verified`, burning ~15 s of the capture's freshness window before `make_case` even finishes).
   - **Exact Change**:
     - Reuse the already-verified `shared_registration` passed into `authority_for(base, runtime, shared_registration)` (or run within `authority.launch_derivations()`), and stamp `capture_now` immediately before writing the capture event and guard files.

- **P0 Measured vs Estimated Savings**:
  - Fixes all **12 failures** in `tests/test_native_u4b_a5_scanner.py` and **1 failure** in `tests/test_native_u4b_addendum_authority.py`.
  - Saves **~15–45 s** in `authority_for()` and recovers **~15 s** of wasted `captured_at` age.
- **P0 Risk & Rollback**: Low risk; localized to `native_execution_registration_v2.py`, `native_shared_execution_orchestration.py`, `native_subscription_capture.py`, and `tests/utils/native_synthetic_evidence.py`. Cleanly revertible via single commit.

---

#### Phase P1: Content-Addressed Schema & Verification Memoization Across Fixture and Launch (`Option B`)
**Objective**: Reduce single-case `make_case + launch_case` runtime from **~628 s to ~38–55 s** and reduce elapsed `captured_at` age at `before_reservation()` from **477.5 s to ~20–32 s** (well inside the `210 s` pre-reservation limit and `300 s` `max_age` limit), without weakening any security, refusal, or file-mutation check.

1. **Target 1 — Content-Address `cached_schema_derivation` by Schema Content Digest Instead of Temp Directory Path (`src/data_sheets_schema/native_shared_authority.py:213-253`)**:
   - **Problem**: `cached_schema_derivation` currently keys `_LAUNCH_DERIVATION_CACHE` by `(os.path.realpath(root), os.path.realpath(full), os.path.realpath(core), full_bytes, core_bytes, source_state_token())`. When `CallbackAdapter` (`native_shared_callback_loading.py`) and `prewarm_before_acceptance` (`native_shared_stage_attribution.py`) copy the schema files into a temporary directory, `os.path.realpath(full)` changes even though `(full_bytes, core_bytes, source_state_token())` are byte-for-byte identical! That causes **2 cold `schema_reconstruction` misses (`~19 s` CPU)** inside `public_launch`.
   - **Exact Change**: Key `_LAUNCH_DERIVATION_CACHE` by `(hashlib.sha256(full_bytes).hexdigest(), hashlib.sha256(core_bytes).hexdigest(), source_state_token())` (while still calling `read_regular(full)` and `read_regular(core)` on every lookup so symlink/permission/missing-file refusals execute on the exact target path every time!).
   - **Invariants Preserved**: Every call still executes `read_regular(full)` and `read_regular(core)` on the actual paths passed in (so any unreadable, missing, symlinked, or mutated schema file is caught immediately), and any change to `full_bytes`, `core_bytes`, or `source_state_token()` produces a cache miss and full reconstruction.

2. **Target 2 — Wrap `make_case` (`tests/native_shared_fixture.py:39-108`) and Failure-Fixture Builders in `authority.launch_derivations()`**:
   - **Problem**: `make_case` runs outside `authority.launch_derivations()`, causing **13 cold `schema_reconstruction` calls (`72.48 s` CPU)** during fixture setup.
   - **Exact Change**: Enter `with authority.launch_derivations():` inside `make_case()` (or around the fixture setup steps `build_native_fixture`, `runtime_for`, `synthetic_registration`, and `authority_for`).
   - **Invariants Preserved**: `launch_derivations()` is torn down when `make_case()` exits, so `launch_case()` starts with a clean derivation scope unless explicitly scoped. Reduces `make_case` `schema_reconstruction` from **13 calls (`72.5 s` CPU) to 1 call (`~5.5 s` CPU)**, saving **~67 s** per test in `make_case` alone!

3. **Target 3 — Scoped Content-Hash Memoization for `verify_preparer`, `execution_registration.verified`, and `shared_registration.verified` Within `launch_derivations()`**:
   - **Problem**: Even with `schema_reconstruction` cached, `make_case + launch_case` calls `verify_preparer` **37 times (`236 s` CPU)**, `execution_registration.verified` **18 times (`318 s` CPU)**, and `shared_registration.verified` **13 times (`292 s` CPU)**.
   - **Exact Change**:
     - Extend the active `_LAUNCH_DERIVATION_CACHE` context in `src/data_sheets_schema/native_shared_authority.py` with three content-addressed sub-tables (`preparer_verified`, `execution_registration_verified`, `shared_registration_verified`).
     - **Crucial Security & Mutability Rule (Fast Boundary Fingerprint)**:
       - On every call to `verify_preparer(root, ...)`, `execution_registration.verified(root, ...)`, or `shared_registration.verified(root, ...)`, when `_LAUNCH_DERIVATION_CACHE` is active:
         1. **Always execute all filesystem stat, regular-file, symlink-refusal, directory-mode, and path-containment checks (`read_regular`, `_stat_regular`, symlink checks) on every governed file in `root`** and hash their live bytes (`SHA-256`) + `(st_mode, st_uid)` + `source_state_token()` + call arguments (`synthetic`, `allow_synthetic_composition`, etc.). Computing SHA-256 over the ~25 governed YAML/JSON/Python/MarkDown files in `root` (<2 MB total) takes **<3 ms** per call.
         2. Look up the composite content-fingerprint key in `_LAUNCH_DERIVATION_CACHE`.
         3. On a **cache miss** (first call, or whenever any governed file's bytes, mode, symlink status, or `source_state_token()` has changed), execute the full uncached verification and store a deep-copied / immutable snapshot of the returned verification structure.
         4. On a **cache hit** (all governed files on disk were just re-read via `read_regular` and matched the exact byte-for-byte SHA-256 digest and stat invariants), return a fresh deep copy (`copy.deepcopy`) of the verified result so callers cannot mutate shared state.
   - **Why This Preserves Every Refusal & Mutation Test**:
     - If a test mutates a single byte of any registration JSON, composition file, prompt, schema, probe artifact, or binary between `_unchanged()` checks or before `launch`, the live `read_regular` + SHA-256 fingerprint changes immediately, causing a cache miss that runs the full verification path and raises the exact same `ValueError` refusal!
     - If a test replaces any governed file with a symlink, FIFO, or directory, or changes permissions, the live `read_regular` / stat pass runs **before** the cache lookup and raises the exact same refusal!
     - Because the cache only exists while `with authority.launch_derivations():` is active on the current thread (`ContextVar`) and keys include `source_state_token()`, monkeypatching any module attribute or function in a test changes `source_state_token()` and bypasses any prior entry!

- **P1 Measured vs Estimated Savings**:
  - `make_case` (`public_fixture`):
    - `schema_reconstruction`: `13` calls (`72.48 s` CPU) -> **`1` call (`~5.6 s` CPU)** (saves **~66.9 s**).
    - `verify_preparer` / `execution_registration_verified` / `shared_registration_verified`: `17 / 5 / 5` calls -> **`1–2` cold calls + fast stat/SHA-256 hits** (saves **~65–75 s**).
    - Total `make_case` wall time: `167.20 s` -> **~18–25 s**.
  - `launch_case` (`public_launch`):
    - `schema_reconstruction`: `3` calls (`27.39 s` CPU) -> **`1` call (`~5.6 s` CPU)** (or `0` if schema digest cached, saving **~21.8 s**).
    - `shared_registration_verified` (8–12 calls), `execution_registration_verified` (13–17 calls), `verify_preparer` (20–24 calls), `controller_prewarm` (117.66 s): **`1` cold verification + fast stat/SHA-256 hits** -> total `launch_case` wall time drops from `460.92 s` to **~20–30 s**!
  - **Combined Single Public Test (`make_case + launch_case`)**:
    - Drops from **628.14 s (failed)** to **~38–55 s (passes with >175 s of pre-reservation freshness margin!)**.
- **P1 Risk & Rollback**: Medium-low risk; gated entirely by `_LAUNCH_DERIVATION_CACHE` context and live `read_regular` + SHA-256 + `source_state_token()` keys. Can be toggled or rolled back in `native_shared_authority.py` without altering external function signatures.

---

#### Phase P2: Test-Suite Acceleration (`Option C` Base Fixture Template + Targeted Consumer-Scope Profiling)
**Objective**: Further cut multi-test cohort wall times (`failure-lifecycle`, `failure-readback`, `failure-reservation`, `u4b`) from **~10–15 minutes to ~3–6 minutes total**, so full local validation and CI shards run comfortably within interactive and CI budgets.

1. **Target 1 — Module-Scoped Immutable Base Fixture Template for Multi-Case Native Execution Suites (`tests/native_shared_fixture.py` / `tests/test_native_shared_execution_failure.py`)**:
   - **Problem**: `tests/test_native_shared_execution_failure.py` contains **17 test functions** (`5` lifecycle + `4` readback + `8` reservation), each calling `make_case(tmp_path)` from scratch. Even after P1 reduces `make_case` from `167 s` to `~20 s`, running `make_case` 17 times sequentially costs `~340 s`.
   - **Exact Change**:
     - Build the deterministic pre-capture base tree (`build_native_fixture` + `runtime_for` + `synthetic_registration`) once per module into a temporary template directory (`tmp_path_factory.mktemp("native_shared_base_template")`), mark the template read-only, and for each test case copy the template into `tmp_path` (`shutil.copytree`) before running `authority_for(...)` (which mints a fresh per-test clock timestamp, capture event, and subscription guard in `tmp_path`).
   - **Invariants Preserved**: Every test function receives its own private, mutable `tmp_path` directory and its own freshly minted subscription capture and guard; mutations in one test never touch the template or another test.

2. **Target 2 — Narrow or Optimize `observe_consumer_calls` (`tests/utils/native_shared_consumer_scope.py`)**:
   - **Problem**: `observe_consumer_calls` installs a Python `sys.setprofile` callback across the entire `execute.synthetic_launch` execution, checking `(code.co_filename, code.co_firstlineno, code.co_name)` on every Python function call event (~80M+ events before P1, ~6M events after P1).
   - **Exact Change**:
     - In `tests/utils/native_shared_consumer_scope.py:34`, fast-path the profile callback by checking `if event == "call" and frame.f_code in target_codes:` using a precomputed `frozenset` of `types.CodeType` objects (or `(frame.f_code.co_name in target_names)` first before constructing the 3-tuple `(os.path.realpath(code.co_filename), ...)`!).
     - **Critical Finding in `native_shared_consumer_scope.py:39`**: Currently, on **every single Python function call in the entire interpreter**, `profiler()` executes `os.path.realpath(code.co_filename)`! Calling `os.path.realpath()` (which performs filesystem `lstat` syscalls along every path component!) on **every Python function call** (`event == "call"`) is a massive hidden bottleneck! Filtering by `if event != "call" or code.co_name not in target_names: return` before touching `os.path.realpath(code.co_filename)` eliminates 99.99% of `os.path.realpath` calls in one line!

3. **Target 3 — Permanent Child-Process `PYTHONDONTWRITEBYTECODE=1` Guard in Native Test & Harness Helpers**:
   - **Problem**: `2c6537d0f` isolated `fairscape_models` in `scripts/adhoc/run_native_u3k_20261109.py`, but any direct `pytest` invocation using a shared `PYTHONPATH` dependency tree could still write `.pyc` files when a child Python process runs with a scrubbed environment.
   - **Exact Change**: Ensure test fixture / harness `PYTHONPATH` setup either points at a per-session/per-run copy of `fairscape_models` or sets `sys.dont_write_bytecode = True` in synthetic child wrappers where allowed by the execution contract.

- **P2 Measured vs Estimated Savings**:
  - Eliminating `os.path.realpath(code.co_filename)` on every Python function call in `tests/utils/native_shared_consumer_scope.py:39` saves **~15–30% of total wall time** during `observe_consumer_calls`!
  - Module-scoped template + `copytree` cuts `make_case` in 17-case `test_native_shared_execution_failure.py` from `~20 s` to **~3–5 s per test** (saving **~250 s** across the 17 failure tests).

---

#### Phase P3: CI Sharding & Duration Calibration (`utils/ci_test_durations.json` & `.github/workflows/main.yaml`)
**Objective**: Prevent native execution tests from overloading GitHub Actions PR/main shards (`45-min` PR timeout, `2.729x` Linux slowdown factor).

1. **Target 1 — Record Measured Native Test Durations in `utils/ci_test_durations.json`**:
   - **Problem**: `utils/pytest_shard.py:_estimates` assigns the median duration (~1–2 s) to any test file missing from `utils/ci_test_durations.json`. When the U1+U3 branch opens its PR, `tests/test_native_shared_execution.py`, `tests/test_native_shared_execution_failure.py`, `tests/test_native_u4b_a5_scanner.py`, `tests/test_native_u4b_addendum_authority.py`, and related `test_native_*` files must have accurate Linux-scaled weights (`macOS_seconds * 2.729`) in `utils/ci_test_durations.json` so `balanced_files()` spreads them across shards instead of stacking them onto one worker.
2. **Target 2 — Verify `tests/test_ci_sharding.py` Budget Invariants**:
   - Ensure the heaviest shard's estimated total weight remains well below the 45-minute (2,700 s) PR timeout across all 8 PR shards and 6 `main` shards.

---

## 6. Concrete Canary and Validation Protocol

In strict compliance with the repository's **Canary First** rule and U3-K supervisory gates (`run_native_u3k_20261109.py`):

### Step 1: Static & Scanner Gate (Zero-Cost Canary, <15 s)
Before running any full native execution test:
1. Run the single scanner regression canary that failed in `u4b-70457f66e`:
   - `tests/test_native_u4b_a5_scanner.py -k test_derive_native_shared_route` (1 test)
   - Verify `rc == 0` and confirm `source.count(helper.ANCHOR + helper.INSERTION) == 1` in `native_execution_registration_v2.py`.
2. Run the single expired-capture pre-engine refusal canary that failed in `u4b-70457f66e`:
   - `tests/test_native_u4b_addendum_authority.py -k test_expired_capture_stays_spent_and_refuses_before_generation_reservation` (1 test)
   - Verify `rc == 0` and wall time `< 30 s`.

### Step 2: Focused Cache & Controller Synthetic Canaries (<60 s each)
1. Run `focused-cache-order` (`tests/test_native_u3k_profile.py`, 4 cases) under `run_native_u3k_20261109.py`.
2. Run `focused-controller-synthetic` (2 cases) under `run_native_u3k_20261109.py`.
3. **Side-Effect Verification**:
   - Inspect `supervisor.json`, `origins-before.json`, `origins-after.json`, `ps-samples.jsonl`, and `pytest.log` on disk.
   - Verify `rc == 0`, `origins_clean == true`, `private_leak_count == 0`, `git_status_clean == true`.

### Step 3: Single Public Execution Canary (`public-correction`, 1 Test Case)
1. Run **only** `tests/test_native_shared_execution.py::test_public_synthetic_launch_writes_correction_and_validates` with `U3K_OBSERVE=1` under `run_native_u3k_20261109.py`.
2. **Pass Criteria (Must Hold Before Running Any Other Public or Failure Cohort)**:
   - `rc == 0` (passes end-to-end through reservation, synthetic launch, readback, and validation!).
   - Total wall time **`<= 90 s`** (target `25–55 s`, down from `628.14 s`).
   - `u3k_metrics.json` confirms:
     - `public_fixture` `schema_reconstruction` calls **`<= 1`** (down from `13`),
     - `public_launch` `schema_reconstruction` calls **`<= 1`** (down from `3`),
     - Elapsed subscription age at `before_reservation()` **`<= 60 s`** (leaving `>= 150 s` margin against the `210 s` pre-reservation limit and `>= 240 s` against the `300 s` `max_age` limit).
   - `origins-after.json` clean, zero `fairscape_models/__pycache__` leaks, zero `/tmp/d4d-*` leftovers.

### Step 4: Second Public Execution Canary (`public-omissions`, 1 Test Case)
1. Run `tests/test_native_shared_execution.py::test_public_synthetic_launch_writes_omissions_and_validates` with `U3K_OBSERVE=1`.
2. Verify `rc == 0`, wall time **`<= 90 s`**, and `u3k_metrics.json` on disk.

### Step 5: Single-Test Mutation & Refusal Canary Before Failure Cohort Fan-Out
1. Run 1 test from `tests/test_native_shared_execution_failure.py` (e.g., a post-verification tamper test between `_unchanged()` checks and a pre-reservation margin test) to prove that Option B's live `read_regular` + SHA-256 fingerprint immediately catches mid-flight file tampering and raises the expected `ValueError`.
2. Only after that single test passes (`rc == 0`, `< 60 s`), run the remaining cohorts (`failure-lifecycle`, `failure-readback`, `failure-reservation`, `u4b`, `shared-policy`, `execution-v2`, `hooks`, `frontdoor-canary`).

---

## 7. CI and Sharding Plan

### 7.1 Current CI Topology (`.github/workflows/main.yaml` at `911662277`)
- **Ordinary `pytest` matrix**:
  - Pull requests: **8 shards** (`0..7`), `timeout-minutes: 45`, `ubuntu-latest` (4 vCPUs), running `poetry run pytest -n logical --maxprocesses=4 --dist load --maxschedchunk=1` over the files selected by `poetry run python utils/pytest_shard.py --shard-index $INDEX --shard-total $TOTAL`.
  - Push to `main`: **6 shards** (`0..5`), `timeout-minutes: 60`.
- **Dedicated slow lanes** (excluded from ordinary shards in `utils/pytest_shard.py:DEDICATED_API_COMPLETION_TEST_FILES` / `DEDICATED_SG2_COMPLETION_TEST_FILES`):
  - `pytest-api-completion`: 4 lanes (`timeout-minutes: 45`, serial).
  - `pytest-sg2-completion`: 3 lanes (`timeout-minutes: 45`, serial).
  - `offline-canary`, `offline-audit`, `offline-evaluation`: `timeout-minutes: 45`.

### 7.2 Linux Runtime Multiplier & Shard Budget Analysis
- According to `utils/ci_test_durations.json` (`recalibration: bc1_g2_measured_ratio_scaling_20261103`), the measured GitHub Actions Linux-to-local runtime ratio is **`2.729x`**.
- **Without P0–P2**:
  - `test_native_shared_execution.py` (2 cases = `1,287 s` local) -> **`~3,512 s` (58.5 min)** on Linux CI (exceeds the 45-min PR shard timeout by itself!).
  - `test_native_shared_execution_failure.py` (17 cases = `5,184 s` local) -> **`~14,147 s` (235.8 min)** on Linux CI (5.2x over the 45-min PR shard timeout!).
- **With P0–P2**:
  - `test_native_shared_execution.py` (2 cases = `~55–90 s` local) -> **`~150–245 s` (2.5–4.1 min)** on Linux CI.
  - `test_native_shared_execution_failure.py` (17 cases = `~240–400 s` local) -> **`~655–1,090 s` (11–18 min)** on Linux CI (or split into 3 files matching the U3-K cohorts: `test_native_shared_execution_failure_lifecycle.py` [5 cases, ~3.5 min Linux], `test_native_shared_execution_failure_readback.py` [4 cases, ~3 min Linux], `test_native_shared_execution_failure_reservation.py` [8 cases, ~6 min Linux] so `pytest_shard.py` distributes them across separate shards and xdist workers!).
  - **Recommendation**: In addition to adding measured weights (`local_seconds * 2.729`) to `utils/ci_test_durations.json`, either split `tests/test_native_shared_execution_failure.py` along the existing 3 cohort boundaries (`lifecycle`, `readback`, `reservation`) or ensure its weight in `utils/ci_test_durations.json` places it on a shard with light companions, and update `tests/test_ci_sharding.py` to assert that no shard exceeds the 45-minute budget.

---

## 8. Effect on Remaining Critical Path to Native Canary and Final Generation

| Critical-Path Stage | Upstream Dependency | Impact of Latency Plan (P0–P3) | Estimated Wall-Clock Duration After Fix |
| :--- | :--- | :--- | :--- |
| **1. U3-K / U3-L / U3-M Offline Repair & Full Rollup** | Implement P0 + P1 (+ P2 `consumer_scope` fast-path) on `codex/native-u1u3-combined-20261108` | Unblocks the 2 failing public tests, 13 failing `failure-*` tests, and 13 failing `u4b` tests; reduces full 11-cohort rollup from `6,695 s (1.86 h, failing)` to **`~12–18 minutes (all passing)`**. | **1.5–2.5 hours** (implementation + single-test canaries + full 11-cohort rollup) |
| **2. Post-U3 Quiet-Host Paired Measurement (`native_u3_plan_2026-11-06.md`)** | Requires U3-K/L/M green + 60-sample quiet-host gate (`foreign_cpu <= 15%`) across 1 canary + 10 T/C or C/T pairs (21 runs) | At ~630 s/run, 21 runs required **~3.7–4.0 hours** of uninterrupted quiet-host time (nearly impossible on an active workstation). At ~35–50 s/run after P1+P2, 21 runs take **~15–20 minutes**! | **0.5–1.0 hour** (including quiet-host pre-gate and post-run summaries) |
| **3. Combined U1+U3 PR Review, Issue Triage & 8-Shard CI** | Requires U3 rollup + `utils/ci_test_durations.json` update (P3) | Prevents 45-minute PR shard timeouts on Linux runners (`2.729x` multiplier); enables clean single-pass CI and adversarial PR review. | **1.5–3.0 hours** (PR open, CI shards, review pass, issue filing/fixes, owner merge) |
| **4. U4–U7 Real Native Binary Probe, Registration & Single CHORUS Canary (`native_u4u7_readiness_2026-11-08.md`)** | Requires U1+U3 merged + real `claude` 2.1.112 probe + two independent reviews + owner `AUTHORIZE_ONE_NATIVE_ATTEMPT` | **Critical**: In a real native CHORUS canary, the 300 s subscription `max_age` and 210 s pre-reservation margin apply to the **live quota observation** before `attempt.mkdir`! Reducing pre-reservation orchestration latency from **>460 s to ~20–30 s** is mandatory so the real native launch does not expire its live subscription guard before `before_reservation()`! | **2.0–4.0 hours** (G4–G6 preflight, two reviews, owner launch authorization, 1 CHORUS native attempt + evaluation) |
| **5. A21 Downstream Aggregate Rebuild & v10 Generation / Fairscape Packaging** | After approved generation / canary gate | Unaffected by native orchestration overhead once generation artifacts land, but unblocked 1–2 days earlier because U3/U4–U7 stop timing out. | Per `generation_eta_2026-11-10` schedule |

---

## 9. Explicit Non-Goals and Prohibited Shortcuts

To preserve every D4D native execution invariant, the following shortcuts are **explicitly prohibited** during implementation:

1. **Do NOT weaken `SubscriptionGuard` freshness constants**:
   - Do not increase `max_age_seconds` above `300 s` or reduce `MINIMUM_PRE_RESERVATION_FRESHNESS_SECONDS` below `90 s` in `src/data_sheets_schema/native_subscription_guard_v2.py`.
2. **Do NOT inject fake or frozen clocks into production `SubscriptionGuard` or `launch`**:
   - Production `check_real_clock(self._clock)` must continue to require the real wall clock (`_now`).
3. **Do NOT remove `_unchanged()`, symlink refusal, `read_regular`, or post-verification mutation checks**:
   - Every boundary check in `native_execution_orchestration.py:_launch` (lines 328, 342, 369, 371, 379) must still execute live filesystem `read_regular` + stat + SHA-256 verification across all governed files so any mid-launch tamper is refused immediately.
4. **Do NOT cache across tests without verifying live on-disk file bytes and `source_state_token()`**:
   - Any memoized verification entry in `_LAUNCH_DERIVATION_CACHE` must be scoped to an explicit `with authority.launch_derivations():` block, keyed by the live SHA-256 of every governed file on disk plus `source_state_token()`, and must return a deep copy so mutations never leak.
5. **Do NOT duplicate AST-anchored code blocks in `native_execution_registration_v2.py`**:
   - Keep `source.count(helper.ANCHOR + helper.INSERTION) == 1` and verify `scan.derive_native_shared_route` via `tests/test_native_u4b_a5_scanner.py` before running any long cohort.
6. **Do NOT run live native model/provider calls or real `claude` executables during U3 latency validation**:
   - All U3-K/L/M validation remains strictly offline and synthetic under `run_native_u3k_20261109.py` supervision.

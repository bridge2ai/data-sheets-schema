# Handoff from AGY4: Native Test Suite CI Collection Fix (Issue 5875)

- **Date:** 2026-11-12
- **Worker:** `agy4` (`E4`)
- **Assignment:** `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/notes/development_efficiency_20261111/assignments/claude-lead-agy4-native-ci-collection-fix-20261112.md`
- **Edit Worktree:** `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy-native-ci-collection-20261112` (branch **agy/native-ci-collection-5875-20261112** at commit `b11931410305569aba30b0f593193ae894bd0dc7`, uncommitted)
- **Changed Test File:** `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy-native-ci-collection-20261112/tests/test_native_u3c_test_driver.py`
- **Untouched Script Under Test:** `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy-native-ci-collection-20261112/scripts/adhoc/run_native_u3a_tests_20261107.py` (`sha256: 54cf869049703c0a5cf38326a75f2f41838939051212f6215c2d96c873738282`)
- **CI Simulation Tree Outside `d4d-executions`:** `/Users/marcin/agent-work/data-sheets-schema/ci-sim-b11931410305`
- **Helper Script (Step 3):** `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/scripts/adhoc/native_tests_layout_dependence_20261112.py`
- **Structured JSON Handoff:** `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/agy4-native-ci-collection-fix-20261112.json`

---

## 1. Answer First

1. **Route taken (`Preferred` route):**
   - We implemented the **preferred route** in `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy-native-ci-collection-20261112/tests/test_native_u3c_test_driver.py` without fallback skipping and without touching `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy-native-ci-collection-20261112/scripts/adhoc/run_native_u3a_tests_20261107.py`.
   - Instead of executing `scripts/adhoc/run_native_u3a_tests_20261107.py` at module import time, a module-scoped fixture (`driver = pytest.fixture(scope='module')(_driver)`) selects a writable resolved temporary base directory outside `d4d-executions` (`_temp_base()`), creates a temporary `d4d-executions` directory with `plans` inside it, copies `scripts/adhoc/run_native_u3a_tests_20261107.py` into a `checkout` subdirectory at the exact same relative depth (`parents[2]`), and executes the module inside the fixture.
   - We also renamed the helper function `setup()` to `_setup(driver_module)` and passed `driver` explicitly to the `4` test functions so pytest's xunit plugin does not treat `setup` as a module/function setup hook.
   - Because `EXECUTIONS` in the loaded module points to the temporary directory tree, all `4` tests run on any checkout path and can never touch the real quiet-window lock.

2. **Do the four tests pass in both places?**
   - **Yes.**
   - **Inside the worktree (`/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy-native-ci-collection-20261112`):** `4 passed in 0.24s`, `0` failed, `0` errors, exit code `0` (saved log: `/tmp/agy4-5875-step1-worktree-pytest.log`).
   - **Outside `d4d-executions` (`/Users/marcin/agent-work/data-sheets-schema/ci-sim-b11931410305`):** `4 passed in 0.09s`, `0` failed, `0` errors, exit code `0` (saved log: `/tmp/agy4-5875-step2-cisim-pytest.log`).

3. **Is collection clean of the `tests/test_native_u3c_test_driver.py` error outside `d4d-executions`?**
   - **Yes.**
   - Before the fix (`/Users/marcin/agent-work/data-sheets-schema/ci-sim-b11931410305.collect.log`), `pytest --collect-only -q tests` collected `26236` tests with `4` errors (`ERROR collecting tests/test_native_u3c_test_driver.py` plus the `3` `fairscape_models.rocrate` environment errors).
   - After copying the fixed `tests/test_native_u3c_test_driver.py` into `/Users/marcin/agent-work/data-sheets-schema/ci-sim-b11931410305/tests/test_native_u3c_test_driver.py` (`/tmp/agy4-5875-step2-cisim-collect.log`), `pytest --collect-only -q tests` collects `26240` tests (`+4` tests from `tests/test_native_u3c_test_driver.py`) with `3` errors (only the `3` `fairscape_models.rocrate` environment errors remain; `ERROR collecting tests/test_native_u3c_test_driver.py` is completely gone).

4. **What CI may still trip over at test run time (Step 3 summary):**
   - Across the `78` baseline files (`601` matching lines) under `tests/` that mention `d4d-executions` (`79` files / `604` lines including our edited `tests/test_native_u3c_test_driver.py`), **`0` files have import-time statements** mentioning `d4d-executions`, and **`74` files (`597` baseline lines; `599` post-fix lines) only contain `d4d-executions` inside strings that are compared or printed** (`73` `.json` and `.yaml` fixtures + `tests/test_receipt_origin.py` line `3543`, plus lines `21` and `28` of `tests/test_native_u3c_test_driver.py`).
   - Of the `4` baseline files (`4` lines) classified as `a path that is opened or resolved`:
     - `tests/test_5139_relative_paths.py` (line `60`) and `tests/test_arm_comparison.py` (line `1254`) construct synthetic foreign `Path` objects that `arm_comparison._path` lexically strips to `data/preprocessed` under `tmp_path`; both are safe on CI.
     - `tests/offline_bc1_planline.py` (line `16`) is not named `test_*.py` or `*_test.py` and is not collected by pytest.
     - **`tests/test_native_u3c_round4_helpers.py` line `25` (`test_parent_worker_and_subprocess_reenter_c4_wrapper`) WILL FAIL at test execution time on a CI runner outside `d4d-executions`**: it collects cleanly because it calls `helper('run_native_u3c_round4_20261107.py')` inside the test body, which loads `scripts/adhoc/run_native_u3a_tests_20261107.py` (`RuntimeError: source must be below the canonical d4d-executions root`) and then evaluates `next(path for path in ROOT.parents if path.name == 'd4d-executions')` (`StopIteration`).
   - Our script also scanned `tests` for indirect references to `scripts/adhoc` helpers that enforce `d4d-executions` layout checks without mentioning `d4d-executions` directly in the test file:
     - **`tests/test_native_u3d_runner_evidence.py` line `11` (`test_source_snapshot_binds_tracked_and_untracked_bytes`)**: loads `scripts/adhoc/run_native_u3d_tests_20261107.py` inside the test function, which checks `_executions = [path for path in ROOT.parents if path.name == "d4d-executions"]` at lines `30-32` and raises `RuntimeError: expected one enclosing d4d-executions directory`.
     - **`tests/test_native_u5_external_schema.py` line `97` (`test_same_external_320_api_instruction_before_after`, `test_api_comparison_refuses_other_scratch_roots`)**: requires pre-materialized `scratch-native-u5-prep` exports and invokes `scripts/adhoc/native_u5_api_render_20261108.py`, which checks `executions = [p for p in checkout.parents if p.name == 'd4d-executions']` at line `28` and raises `SystemExit('source root must sit under d4d-executions')`.

---

## 2. Tables Printed from `agy4-native-ci-collection-fix-20261112.json`

### Table 1 — Verification Commands and Outcomes (Part 2, Steps 1–2)

| Step | Location | Exit Code | Passed | Collection Errors | Collected Tests | Saved Log |
|---|---|---:|---:|---:|---:|---|
| Step 1 (`pytest tests/test_native_u3c_test_driver.py`) | `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy-native-ci-collection-20261112` | `0` | `4` | `0` | `4` | `/tmp/agy4-5875-step1-worktree-pytest.log` |
| Step 2a (`pytest tests/test_native_u3c_test_driver.py` outside `d4d-executions`) | `/Users/marcin/agent-work/data-sheets-schema/ci-sim-b11931410305` | `0` | `4` | `0` | `4` | `/tmp/agy4-5875-step2-cisim-pytest.log` |
| Step 2b Baseline (`pytest --collect-only -q tests` before fix) | `/Users/marcin/agent-work/data-sheets-schema/ci-sim-b11931410305` | `2` | n/a | `4` (includes `test_native_u3c_test_driver.py`) | `26236` | `/Users/marcin/agent-work/data-sheets-schema/ci-sim-b11931410305.collect.log` |
| Step 2b After Fix (`pytest --collect-only -q tests` after fix) | `/Users/marcin/agent-work/data-sheets-schema/ci-sim-b11931410305` | `2` | n/a | `3` (only 3 `fairscape_models.rocrate`; `u3c` error gone) | `26240` | `/tmp/agy4-5875-step2-cisim-collect.log` |

### Table 2 — Mechanical Classification Summary (`tests/` Mentions of `d4d-executions`)

| Classification | Baseline `b11931410305` Files (of 78) | Baseline `b11931410305` Lines (of 601) | Edited Worktree Files (of 79) | Edited Worktree Lines (of 604) |
|---|---:|---:|---:|---:|
| `inside a string that is only compared or printed` | `74` | `597` | `74` | `599` |
| `a path that is opened or resolved` | `4` | `4` | `5` | `5` |
| `an import-time statement` | `0` | `0` | `0` | `0` |
| **Total** | **`78`** | **`601`** | **`79`** | **`604`** |

### Table 3 — Python Files Under `tests/` Mentioning `d4d-executions` (Line-by-Line)

| File | Line | Classification | Mechanical Basis | CI Run-Time Assessment | Excerpt |
|---|---:|---|---|---|---|
| `tests/offline_bc1_planline.py` | `16` | `a path that is opened or resolved` | `in_function:main:path_or_parents_operation` | Not collected by pytest (filename does not match `test_*.py` or `*_test.py`); only runs if invoked as `__main__`. | scratch = Path('/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-bc1-planline') |
| `tests/test_5139_relative_paths.py` | `60` | `a path that is opened or resolved` | `in_function:test_arm_comparison_resolves_historical_worktree_preprocessed_paths:path_or_parents_operation` | Safe on CI: synthetic foreign worktree path is lexically stripped to its relative `data/preprocessed` suffix under `tmp_path` by `arm_comparison._path`. | old_wt = Path("/Users/example/d4d-executions/claude-canary1") |
| `tests/test_arm_comparison.py` | `1254` | `a path that is opened or resolved` | `in_function:test_arm_comparison_resolves_historical_worktree_preprocessed_paths:path_or_parents_operation` | Safe on CI: synthetic foreign worktree path is lexically stripped to its relative `data/preprocessed` suffix under `tmp_path` by `arm_comparison._path`. | old_wt = Path("/Users/nonexistent/d4d-executions/launch-base") |
| `tests/test_native_u3c_round4_helpers.py` | `25` | `a path that is opened or resolved` | `in_function:test_parent_worker_and_subprocess_reenter_c4_wrapper:path_or_parents_operation` | **CI RUN-TIME FAILURE**: `test_parent_worker_and_subprocess_reenter_c4_wrapper` loads `scripts/adhoc/run_native_u3c_round4_20261107.py` (which loads `scripts/adhoc/run_native_u3a_tests_20261107.py`) and walks `ROOT.parents` for `d4d-executions`. | executions = next(path for path in ROOT.parents if path.name == 'd4d-executions') |
| `tests/test_native_u3c_test_driver.py` | `21` | `inside a string that is only compared or printed` | `in_function:_temp_base:string_literal_comparison_or_message` | Added by this fix: skips any temp root whose resolved path is inside `d4d-executions`. | if 'd4d-executions' in resolved.parts: |
| `tests/test_native_u3c_test_driver.py` | `28` | `inside a string that is only compared or printed` | `in_function:_temp_base:string_literal_comparison_or_message` | Added by this fix: `RuntimeError` message string if no writable temp dir exists. | raise RuntimeError('no writable temporary directory outside d4d-executions') |
| `tests/test_native_u3c_test_driver.py` | `33` | `a path that is opened or resolved` | `in_function:_driver:path_or_parents_operation` | Added by this fix: creates synthetic `d4d-executions` directory under resolved temp base inside module fixture. | root = Path(raw_temp).resolve(strict=True) / 'd4d-executions' |
| `tests/test_receipt_origin.py` | `3543` | `inside a string that is only compared or printed` | `in_function:test_backstop:string_literal_comparison_or_message` | Safe on CI: string key in dict passed to `ro._backstop(command)` and compared to `False`. | "cd d4d-executions && grep derive x": False, "ls data/d4d_concatenated derive": False} |

### Table 4 — Run-Time `d4d-executions` Layout Hazards for CI Execution

| Test File | Line | Test Function | Direct `d4d-executions` Mention in `tests/` | Collection-Time Impact | Run-Time Impact on CI Runner Outside `d4d-executions` |
|---|---:|---|---|---|---|
| `tests/test_native_u3c_round4_helpers.py` | `25` | `test_parent_worker_and_subprocess_reenter_c4_wrapper` | `True` | None (loads helper inside test function, not at module import time). | FAILS at test execution time outside d4d-executions: line 24 calls helper('run_native_u3c_round4_20261107.py'), which executes scripts/adhoc/run_native_u3a_tests_20261107.py (raising RuntimeError: 'source must be below the canonical d4d-executions root'), and line 25 evaluates `next(path for path in ROOT.parents if path.name == 'd4d-executions')` (raising StopIteration). |
| `tests/test_native_u3d_runner_evidence.py` | `11` | `test_source_snapshot_binds_tracked_and_untracked_bytes` | `False` | None (loads script inside test function, not at module import time). | FAILS at test execution time outside d4d-executions: line 14 executes scripts/adhoc/run_native_u3d_tests_20261107.py, which checks `_executions = [path for path in ROOT.parents if path.name == 'd4d-executions']` at module top level (lines 30-32) and raises RuntimeError: 'expected one enclosing d4d-executions directory'. |
| `tests/test_native_u5_external_schema.py` | `97` | `test_same_external_320_api_instruction_before_after, test_api_comparison_refuses_other_scratch_roots` | `False` | None (runs subprocess inside test functions). | FAILS at test execution time outside d4d-executions: requires pre-materialized scratch-native-u5-prep exports and invokes scripts/adhoc/native_u5_api_render_20261108.py, which checks `executions = [p for p in checkout.parents if p.name == 'd4d-executions']` (line 28) and raises SystemExit('source root must sit under d4d-executions'). |

### Table 5 — Complete File-by-File Inventory of `d4d-executions` Mentions Under `tests/` (78 Baseline Files + 1 Edited Test File)

| # | File | Type | Matching Lines | Token Occurrences | Line Numbers | Classification |
|---:|---|---|---:|---:|---|---|
| 1 | `tests/fixtures/audit_batches/chorus_v10_2026-10-22a/CHORUS_core.yaml` | `yaml` | `2` | `2` | `9, 11` | `inside a string that is only compared or printed` |
| 2 | `tests/fixtures/audit_batches/chorus_v10_2026-10-22a/CHORUS_full.yaml` | `yaml` | `2` | `2` | `9, 10` | `inside a string that is only compared or printed` |
| 3 | `tests/fixtures/native_u2_m7/composition.json` | `json` | `63` | `298` | `58, 73, 75, 77, 79, 81, 83, 85, 87, 89, 91, 93, 95, 97, 99, 101, 103, 105, 107, 114, 115, 116, 117, 119, 122, 123, 124, 125, 126, 127, 131, 132, 133, 134, 136, 137, 139, 146, 149, 152, 153, 156, 159, 160, 168, 171, 172, 196, 200, 204, 210, 211, 212, 213, 214, 215, 216, 217, 218, 219, 222, 224, 232` | `inside a string that is only compared or printed` |
| 4 | `tests/fixtures/native_u2_m7/registration.json` | `json` | `39` | `153` | `285, 289, 293, 297, 301, 319, 320, 321, 322, 327, 328, 329, 330, 331, 332, 333, 334, 335, 336, 337, 338, 339, 340, 341, 342, 343, 344, 345, 346, 347, 348, 349, 350, 351, 355, 357, 359, 360, 374` | `inside a string that is only compared or printed` |
| 5 | `tests/fixtures/native_u3l_review_cases.json` | `json` | `1` | `1` | `4` | `inside a string that is only compared or printed` |
| 6 | `tests/fixtures/pre_d41/c1/before/outputs/EXTERNAL_api_progress.json` | `json` | `9` | `9` | `9, 13, 17, 33, 36, 38, 42, 56, 63` | `inside a string that is only compared or printed` |
| 7 | `tests/fixtures/pre_d41/c1/before/outputs/EXTERNAL_d4d_core.yaml` | `yaml` | `1` | `1` | `2` | `inside a string that is only compared or printed` |
| 8 | `tests/fixtures/pre_d41/c1/before/outputs/intermediate/EXTERNAL_core.yaml` | `yaml` | `1` | `1` | `2` | `inside a string that is only compared or printed` |
| 9 | `tests/fixtures/pre_d41/c1/before/outputs/intermediate/EXTERNAL_snapshot_index.json` | `json` | `9` | `9` | `12, 16, 20, 36, 39, 41, 45, 53, 59` | `inside a string that is only compared or printed` |
| 10 | `tests/fixtures/pre_d41/c1/before/outputs/intermediate/EXTERNAL_snapshot_index.previous-unrelated.json` | `json` | `1` | `9` | `1` | `inside a string that is only compared or printed` |
| 11 | `tests/fixtures/pre_d41/c1/before/source manifest.yaml` | `yaml` | `1` | `1` | `6` | `inside a string that is only compared or printed` |
| 12 | `tests/fixtures/pre_d41/c1/invocation.json` | `json` | `7` | `7` | `4, 49, 52, 59, 61, 66, 69` | `inside a string that is only compared or printed` |
| 13 | `tests/fixtures/pre_d41/c2/before/outputs/EXTERNAL_api_progress.json` | `json` | `9` | `9` | `9, 13, 17, 33, 36, 38, 42, 56, 63` | `inside a string that is only compared or printed` |
| 14 | `tests/fixtures/pre_d41/c2/before/outputs/EXTERNAL_d4d_core.yaml` | `yaml` | `1` | `1` | `2` | `inside a string that is only compared or printed` |
| 15 | `tests/fixtures/pre_d41/c2/before/outputs/intermediate/EXTERNAL_core.yaml` | `yaml` | `1` | `1` | `2` | `inside a string that is only compared or printed` |
| 16 | `tests/fixtures/pre_d41/c2/before/outputs/intermediate/EXTERNAL_snapshot_index.json` | `json` | `9` | `9` | `12, 16, 20, 36, 39, 41, 45, 53, 59` | `inside a string that is only compared or printed` |
| 17 | `tests/fixtures/pre_d41/c2/before/source manifest.yaml` | `yaml` | `1` | `1` | `6` | `inside a string that is only compared or printed` |
| 18 | `tests/fixtures/pre_d41/c2/invocation.json` | `json` | `7` | `7` | `4, 49, 52, 59, 61, 66, 69` | `inside a string that is only compared or printed` |
| 19 | `tests/fixtures/pre_d41/c3/before/outputs/EXTERNAL_api_progress.json` | `json` | `9` | `9` | `9, 13, 17, 33, 36, 38, 42, 56, 63` | `inside a string that is only compared or printed` |
| 20 | `tests/fixtures/pre_d41/c3/before/outputs/EXTERNAL_d4d_core.yaml` | `yaml` | `1` | `1` | `2` | `inside a string that is only compared or printed` |
| 21 | `tests/fixtures/pre_d41/c3/before/outputs/intermediate/EXTERNAL_core.yaml` | `yaml` | `1` | `1` | `2` | `inside a string that is only compared or printed` |
| 22 | `tests/fixtures/pre_d41/c3/before/outputs/intermediate/EXTERNAL_snapshot_index.json` | `json` | `9` | `9` | `12, 16, 20, 36, 39, 41, 45, 53, 59` | `inside a string that is only compared or printed` |
| 23 | `tests/fixtures/pre_d41/c3/before/source manifest.yaml` | `yaml` | `1` | `1` | `6` | `inside a string that is only compared or printed` |
| 24 | `tests/fixtures/pre_d41/c3/invocation.json` | `json` | `7` | `7` | `4, 49, 52, 59, 61, 66, 69` | `inside a string that is only compared or printed` |
| 25 | `tests/fixtures/pre_d41/c4/before/outputs/EXTERNAL_api_progress.json` | `json` | `9` | `9` | `9, 13, 17, 33, 36, 38, 42, 56, 63` | `inside a string that is only compared or printed` |
| 26 | `tests/fixtures/pre_d41/c4/before/outputs/EXTERNAL_api_usage_f4cd3de7180382eb.json` | `json` | `7` | `7` | `17, 21, 25, 41, 44, 46, 50` | `inside a string that is only compared or printed` |
| 27 | `tests/fixtures/pre_d41/c4/before/outputs/EXTERNAL_d4d_core.yaml` | `yaml` | `1` | `1` | `2` | `inside a string that is only compared or printed` |
| 28 | `tests/fixtures/pre_d41/c4/before/outputs/intermediate/EXTERNAL_core.yaml` | `yaml` | `1` | `1` | `2` | `inside a string that is only compared or printed` |
| 29 | `tests/fixtures/pre_d41/c4/before/outputs/intermediate/EXTERNAL_snapshot_index.json` | `json` | `9` | `9` | `12, 16, 20, 36, 39, 41, 45, 53, 59` | `inside a string that is only compared or printed` |
| 30 | `tests/fixtures/pre_d41/c4/before/outputs/intermediate/EXTERNAL_snapshot_index.previous-b6bf9e8478c14b9a8b1271cb42553388.json` | `json` | `9` | `9` | `12, 16, 20, 36, 39, 41, 45, 53, 59` | `inside a string that is only compared or printed` |
| 31 | `tests/fixtures/pre_d41/c4/before/source manifest.yaml` | `yaml` | `1` | `1` | `6` | `inside a string that is only compared or printed` |
| 32 | `tests/fixtures/pre_d41/c4/invocation.json` | `json` | `7` | `7` | `4, 49, 52, 59, 61, 66, 69` | `inside a string that is only compared or printed` |
| 33 | `tests/fixtures/pre_d41/c7/before/outputs/EXTERNAL_d4d_core.yaml` | `yaml` | `1` | `1` | `2` | `inside a string that is only compared or printed` |
| 34 | `tests/fixtures/pre_d41/c7/before/outputs/EXTERNAL_provenance.yaml` | `yaml` | `33` | `33` | `68, 72, 75, 78, 82, 153, 164, 178, 181, 199, 205, 209, 213, 218, 315, 318, 335, 377, 380, 474, 477, 480, 483, 517, 523, 524, 542, 544, 549, 553, 558, 563, 567` | `inside a string that is only compared or printed` |
| 35 | `tests/fixtures/pre_d41/c7/before/outputs/intermediate/EXTERNAL_core.yaml` | `yaml` | `1` | `1` | `2` | `inside a string that is only compared or printed` |
| 36 | `tests/fixtures/pre_d41/c7/before/outputs/intermediate/EXTERNAL_reconcile_core.yaml` | `yaml` | `1` | `1` | `2` | `inside a string that is only compared or printed` |
| 37 | `tests/fixtures/pre_d41/c7/before/outputs/intermediate/EXTERNAL_snapshot_index.json` | `json` | `13` | `13` | `12, 16, 20, 36, 39, 41, 45, 53, 59, 64, 70, 76, 81` | `inside a string that is only compared or printed` |
| 38 | `tests/fixtures/pre_d41/c7/before/source manifest.yaml` | `yaml` | `1` | `1` | `6` | `inside a string that is only compared or printed` |
| 39 | `tests/fixtures/pre_d41/c7/invocation.json` | `json` | `7` | `7` | `4, 49, 52, 59, 61, 66, 69` | `inside a string that is only compared or printed` |
| 40 | `tests/fixtures/pre_d41/c8/before/outputs/EXTERNAL_d4d_core.yaml` | `yaml` | `1` | `1` | `2` | `inside a string that is only compared or printed` |
| 41 | `tests/fixtures/pre_d41/c8/before/outputs/EXTERNAL_provenance.yaml` | `yaml` | `33` | `33` | `68, 72, 75, 78, 82, 153, 164, 178, 181, 199, 205, 209, 213, 218, 315, 318, 335, 377, 380, 474, 477, 480, 483, 517, 523, 524, 542, 544, 549, 553, 558, 563, 567` | `inside a string that is only compared or printed` |
| 42 | `tests/fixtures/pre_d41/c8/before/outputs/intermediate/EXTERNAL_core.yaml` | `yaml` | `1` | `1` | `2` | `inside a string that is only compared or printed` |
| 43 | `tests/fixtures/pre_d41/c8/before/outputs/intermediate/EXTERNAL_reconcile_core.yaml` | `yaml` | `1` | `1` | `2` | `inside a string that is only compared or printed` |
| 44 | `tests/fixtures/pre_d41/c8/before/outputs/intermediate/EXTERNAL_snapshot_index.json` | `json` | `13` | `13` | `12, 16, 20, 36, 39, 41, 45, 53, 59, 64, 70, 76, 81` | `inside a string that is only compared or printed` |
| 45 | `tests/fixtures/pre_d41/c8/before/source manifest.yaml` | `yaml` | `1` | `1` | `6` | `inside a string that is only compared or printed` |
| 46 | `tests/fixtures/pre_d41/c8/invocation.json` | `json` | `7` | `7` | `4, 49, 52, 59, 61, 66, 69` | `inside a string that is only compared or printed` |
| 47 | `tests/fixtures/pre_d41/i1/before/outputs/EXTERNAL_api_usage_f4cd3de7180382eb.json` | `json` | `7` | `7` | `72, 76, 80, 96, 99, 101, 105` | `inside a string that is only compared or printed` |
| 48 | `tests/fixtures/pre_d41/i1/before/outputs/EXTERNAL_d4d_core.yaml` | `yaml` | `1` | `1` | `2` | `inside a string that is only compared or printed` |
| 49 | `tests/fixtures/pre_d41/i1/before/outputs/EXTERNAL_provenance.yaml` | `yaml` | `33` | `33` | `68, 72, 75, 78, 82, 153, 164, 178, 181, 199, 205, 209, 213, 218, 315, 318, 335, 377, 380, 474, 477, 480, 483, 517, 523, 524, 542, 544, 549, 553, 558, 563, 567` | `inside a string that is only compared or printed` |
| 50 | `tests/fixtures/pre_d41/i1/before/outputs/intermediate/EXTERNAL_core.yaml` | `yaml` | `1` | `1` | `2` | `inside a string that is only compared or printed` |
| 51 | `tests/fixtures/pre_d41/i1/before/outputs/intermediate/EXTERNAL_reconcile_core.yaml` | `yaml` | `1` | `1` | `2` | `inside a string that is only compared or printed` |
| 52 | `tests/fixtures/pre_d41/i1/before/outputs/intermediate/EXTERNAL_snapshot_index.json` | `json` | `13` | `13` | `12, 16, 20, 36, 39, 41, 45, 53, 59, 64, 70, 76, 81` | `inside a string that is only compared or printed` |
| 53 | `tests/fixtures/pre_d41/i1/before/source manifest.yaml` | `yaml` | `1` | `1` | `6` | `inside a string that is only compared or printed` |
| 54 | `tests/fixtures/pre_d41/i1/invocation.json` | `json` | `7` | `7` | `4, 49, 52, 59, 61, 66, 69` | `inside a string that is only compared or printed` |
| 55 | `tests/fixtures/pre_d41/i2/before/outputs/EXTERNAL_api_progress.json` | `json` | `9` | `9` | `9, 13, 17, 33, 36, 38, 42, 56, 63` | `inside a string that is only compared or printed` |
| 56 | `tests/fixtures/pre_d41/i2/before/outputs/EXTERNAL_api_usage_f4cd3de7180382eb.json` | `json` | `7` | `7` | `30, 34, 38, 54, 57, 59, 63` | `inside a string that is only compared or printed` |
| 57 | `tests/fixtures/pre_d41/i2/before/outputs/EXTERNAL_d4d_core.yaml` | `yaml` | `1` | `1` | `2` | `inside a string that is only compared or printed` |
| 58 | `tests/fixtures/pre_d41/i2/before/outputs/intermediate/EXTERNAL_core.yaml` | `yaml` | `1` | `1` | `2` | `inside a string that is only compared or printed` |
| 59 | `tests/fixtures/pre_d41/i2/before/outputs/intermediate/EXTERNAL_snapshot_index.json` | `json` | `9` | `9` | `12, 16, 20, 36, 39, 41, 45, 53, 59` | `inside a string that is only compared or printed` |
| 60 | `tests/fixtures/pre_d41/i2/before/source manifest.yaml` | `yaml` | `1` | `1` | `6` | `inside a string that is only compared or printed` |
| 61 | `tests/fixtures/pre_d41/i2/invocation.json` | `json` | `7` | `7` | `4, 49, 52, 59, 61, 66, 69` | `inside a string that is only compared or printed` |
| 62 | `tests/fixtures/pre_d41/split/before/data/d4d_concatenated/custom_core/synthetic/EXTERNAL_api_usage_f4cd3de7180382eb.json` | `json` | `7` | `7` | `72, 76, 80, 96, 99, 101, 105` | `inside a string that is only compared or printed` |
| 63 | `tests/fixtures/pre_d41/split/before/data/d4d_concatenated/custom_core/synthetic/EXTERNAL_d4d_core.yaml` | `yaml` | `1` | `1` | `2` | `inside a string that is only compared or printed` |
| 64 | `tests/fixtures/pre_d41/split/before/data/d4d_concatenated/custom_core/synthetic/EXTERNAL_provenance.yaml` | `yaml` | `32` | `32` | `68, 72, 75, 78, 82, 153, 178, 181, 199, 205, 209, 213, 218, 315, 318, 335, 377, 380, 474, 477, 480, 483, 517, 523, 524, 542, 544, 549, 553, 558, 563, 567` | `inside a string that is only compared or printed` |
| 65 | `tests/fixtures/pre_d41/split/before/data/d4d_concatenated/custom_core/synthetic/intermediate/EXTERNAL_core.yaml` | `yaml` | `1` | `1` | `2` | `inside a string that is only compared or printed` |
| 66 | `tests/fixtures/pre_d41/split/before/data/d4d_concatenated/custom_core/synthetic/intermediate/EXTERNAL_reconcile_core.yaml` | `yaml` | `1` | `1` | `2` | `inside a string that is only compared or printed` |
| 67 | `tests/fixtures/pre_d41/split/before/data/d4d_concatenated/custom_core/synthetic/intermediate/EXTERNAL_snapshot_index.json` | `json` | `13` | `13` | `12, 16, 20, 36, 39, 41, 45, 53, 59, 64, 70, 76, 81` | `inside a string that is only compared or printed` |
| 68 | `tests/fixtures/pre_d41/split/before/source manifest.yaml` | `yaml` | `1` | `1` | `6` | `inside a string that is only compared or printed` |
| 69 | `tests/fixtures/pre_d41/split/generation.json` | `json` | `4` | `4` | `2, 3, 26, 401` | `inside a string that is only compared or printed` |
| 70 | `tests/fixtures/pre_d41/split/invocation.json` | `json` | `6` | `6` | `4, 48, 51, 58, 60, 66` | `inside a string that is only compared or printed` |
| 71 | `tests/fixtures/receipt_completion_saved/CHORUS_2026-10-20a.json` | `json` | `39` | `80` | `21, 43, 47, 62, 63, 65, 66, 89, 103, 112, 117, 122, 127, 132, 137, 142, 147, 152, 157, 162, 543, 547, 562, 563, 565, 566, 589, 603, 612, 617, 622, 627, 632, 637, 642, 647, 652, 657, 662` | `inside a string that is only compared or printed` |
| 72 | `tests/fixtures/receipt_completion_saved/CHORUS_2026-10-22a.json` | `json` | `39` | `80` | `21, 43, 47, 62, 63, 65, 66, 89, 103, 112, 117, 122, 127, 132, 137, 142, 147, 152, 157, 162, 576, 580, 595, 596, 598, 599, 622, 636, 645, 650, 655, 660, 665, 670, 675, 680, 685, 690, 695` | `inside a string that is only compared or printed` |
| 73 | `tests/offline_bc1_planline.py` | `python` | `1` | `1` | `16` | `a path that is opened or resolved` |
| 74 | `tests/test_5139_relative_paths.py` | `python` | `1` | `1` | `60` | `a path that is opened or resolved` |
| 75 | `tests/test_arm_comparison.py` | `python` | `1` | `1` | `1254` | `a path that is opened or resolved` |
| 76 | `tests/test_native_u3c_round4_helpers.py` | `python` | `1` | `1` | `25` | `a path that is opened or resolved` |
| 77 | `tests/test_native_u3c_test_driver.py` *(added by 5875 fix)* | `python` | `3` | `3` | `21, 28, 33` | `a path that is opened or resolved` |
| 78 | `tests/test_receipt_origin.py` | `python` | `1` | `1` | `3543` | `inside a string that is only compared or printed` |
| 79 | `tests/utils/run_spec_boundary_contracts.json` | `json` | `3` | `3` | `252, 268, 271` | `inside a string that is only compared or printed` |

---

## 3. Exact Commands Run

1. **Part 2, Step 1 — Run the 4 tests in `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy-native-ci-collection-20261112`:**
   ```bash
   PYTHONPATH=/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy-native-ci-collection-20261112/src \
     /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python -m pytest \
     -p no:cacheprovider \
     --basetemp /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy-native-ci-collection-20261112/tmp/basetemp \
     /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy-native-ci-collection-20261112/tests/test_native_u3c_test_driver.py \
     > /tmp/agy4-5875-step1-worktree-pytest.log 2>&1
   ```
   - **Exit code:** `0`
   - **Summary line:** `4 passed in 0.24s`

2. **Part 2, Step 2 — Copy changed test file to `/Users/marcin/agent-work/data-sheets-schema/ci-sim-b11931410305/tests/test_native_u3c_test_driver.py` and run the 4 tests outside `d4d-executions`:**
   ```bash
   cp /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy-native-ci-collection-20261112/tests/test_native_u3c_test_driver.py \
     /Users/marcin/agent-work/data-sheets-schema/ci-sim-b11931410305/tests/test_native_u3c_test_driver.py
   PYTHONPATH=/Users/marcin/agent-work/data-sheets-schema/ci-sim-b11931410305/src \
     /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python -m pytest \
     -p no:cacheprovider \
     --basetemp /tmp/agy4-5875-ci-sim-basetemp \
     /Users/marcin/agent-work/data-sheets-schema/ci-sim-b11931410305/tests/test_native_u3c_test_driver.py \
     > /tmp/agy4-5875-step2-cisim-pytest.log 2>&1
   ```
   - **Exit code:** `0`
   - **Summary line:** `4 passed in 0.09s`

3. **Part 2, Step 2 — Run `pytest --collect-only -q tests` in `/Users/marcin/agent-work/data-sheets-schema/ci-sim-b11931410305`:**
   ```bash
   cd /Users/marcin/agent-work/data-sheets-schema/ci-sim-b11931410305 && \
     PYTHONPATH=/Users/marcin/agent-work/data-sheets-schema/ci-sim-b11931410305/src \
     /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python -m pytest \
     --collect-only -q tests -p no:cacheprovider \
     > /tmp/agy4-5875-step2-cisim-collect.log 2>&1
   ```
   - **Exit code:** `2` (only the `3` `fairscape_models.rocrate` environment errors remain)
   - **Summary line:** `26240 tests collected, 3 errors in 62.42s` (vs baseline `26236 tests collected, 4 errors in 81.91s` in `/Users/marcin/agent-work/data-sheets-schema/ci-sim-b11931410305.collect.log`)

4. **Part 2, Step 3 — Generate JSON handoff and Markdown tables:**
   ```bash
   /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python \
     /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/scripts/adhoc/native_tests_layout_dependence_20261112.py \
     > /tmp/agy4-5875-tables.md
   ```
   - **Exit code:** `0`

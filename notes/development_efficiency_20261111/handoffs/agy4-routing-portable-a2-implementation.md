# AGY4 Implementation Handoff: Option A2 (`routing-portable` + `routing-portable-tamper`)

- **Worker**: `agy4` (`E4`)
- **Date**: `2026-11-11`
- **Track**: CI efficiency (second priority; never a final-generation prerequisite)
- **Assignment**: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/notes/development_efficiency_20261111/assignments/claude-lead-agy4-routing-portable-a2-implementation.md`
- **Worktree**: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy4-ci-routing-portable-split-20261111`
- **Branch**: `agy/ci-routing-portable-split-20261111` (base `main` `925d726d67cdd03fe28fdeafdde60fa27df57205`)
- **HEAD Commit**: `e999aa7453ffe2e8ba389767463260e65977480c` (`Split routing-portable dedicated CI lane into two single-process lanes`)
- **Tracked Worktree Status**: Clean (`git status --short` empty; no push, no PR, no CI trigger)

---

## 1. Modified Files and SHA-256 Hashes

Exactly the five scoped files were edited and committed in `e999aa7453ffe2e8ba389767463260e65977480c` (`5 files changed, 108 insertions(+), 87 deletions(-)`):

| File Path (relative to worktree root) | Size (bytes) | SHA-256 | Summary of Local Edit |
| --- | --- | --- | --- |
| `tests/test_source_heading_runtime_api.py` | `38,291` | `dde323c6e129b29004f06e6f562bbb3bfa4d31f53c7b06b938f7ed902a8e3bbb` | Extracted `_portable_completed_capture_sandbox` (`lines 261-322`, building a fresh capture per call) and split the portable checks into `test_actual_completed_capture_is_portable_and_refuses_changed_bytes` (`lines 325-362`, keeping the original function name so `routing-portable` target stays unchanged) and `test_actual_completed_capture_refuses_tampered_bytes_and_ledger` (`lines 365-410`, target of `routing-portable-tamper`). |
| `utils/pytest_shard.py` | `10,142` | `087dac1189080a5fd0fa8eee2581dbd017489009f7e5a00950636f5004ba0257` | Added `"routing-portable-tamper"` to `API_CASE_LANES` (`line 23`) and updated `seven` -> `eight` in the module docstring (`line 6`) and `pytest_report_header` (`line 213`). `_DedicatedCaseOutcome` and the single-process rule (`lines 50-77, 109-110`) are untouched. |
| `.github/workflows/main.yaml` | `17,058` | `cf0fb5ac96ba2c044184687ff9f31f1d2e8633a8336bcbbae0cf6c0871a249e5` | Added `routing-portable-tamper` to `jobs.api-completion.strategy.matrix.case` (`line 90`). Nothing else changed. |
| `tests/test_ci_sharding.py` | `22,053` | `c649ecf3a2f6c250deb9472e6d5606c2d1906dba8e45d0632b9fa1adf6ac7b0a` | Updated the total collected testcase count with dedicated lanes enabled from `97` to `98` at `line 59` (`_lane_fixture` and the parametrized lane checks dynamically read `API_CASE_LANES` and `DEDICATED_CASE_LANES`). |
| `utils/ci_sharding.md` | `14,579` | `124d95e40b0526f4af9739d2b463970f10b7739ef1ee0ec4bf4e18c3cd0033e4` | Updated dedicated-lane counts and prose in `lines 9-12, 49, 168-174, 191-194` (`Four` -> `Five` API jobs, `seven` -> `eight` dedicated cases, `nineteen`/`eighteen`/`thirty-eight` -> `twenty`/`nineteen`/`forty` required successes). |

---

## 2. Mapping of All 21 Explicit `recheck_completed` Calls (`main` `925d726d` -> `e999aa745`)

Every one of the 21 explicit `recheck_completed` calls from the original `test_actual_completed_capture_is_portable_and_refuses_changed_bytes` runs under the identical `monkeypatch.context()` guard (`lines 308-319`), with the identical assertions and expected refusals. Each test function invokes `_portable_completed_capture_sandbox(tmp_path, draft_files, monkeypatch)` independently (no shared module/session capture fixture), so Call `#1` runs in both functions:

| Call # | Original Line (`925d726d`) | New Function & Helper Location (`e999aa745`) | New Line (`tests/test_source_heading_runtime_api.py`) | Dedicated CI Lane | Assertion / Expected Refusal (Unchanged) |
| --- | --- | --- | --- | --- | --- |
| `#1` | `line 272` | `_portable_completed_capture_sandbox` (invoked at `line 330` by `test_actual_completed_capture_is_portable_and_refuses_changed_bytes` and at `line 367` by `test_actual_completed_capture_refuses_tampered_bytes_and_ledger`) | `line 274` (runs in **both** functions) | `routing-portable` **and** `routing-portable-tamper` | `initial = complete.recheck_completed(raw)` (`assert initial['complete'] and initial['scientific_eligibility'] is False`) |
| `#2` | `line 317` | `test_actual_completed_capture_is_portable_and_refuses_changed_bytes` | `line 333` | `routing-portable` | `assert complete.recheck_completed(raw) == initial` |
| `#3` | `line 318` | `test_actual_completed_capture_is_portable_and_refuses_changed_bytes` | `line 334` | `routing-portable` | `CliRunner().invoke(cli, ['api', 'check-routing-completed', str(capture)])` (`exit_code == 0`, `json.loads(output.output) == initial`) |
| `#4` | `line 324` | `test_actual_completed_capture_is_portable_and_refuses_changed_bytes` | `line 340` | `routing-portable` | `changed_display` (`core_source = 'unrelated-record.yaml'`): `pytest.raises(ledger.UsageLedgerError, match='original core differs')` |
| `#5` | `line 344` (`name='full'`) | `test_actual_completed_capture_is_portable_and_refuses_changed_bytes` | `line 359` (`name='full'`) | `routing-portable` | `with_schema_claims({'full_md5': '0' * 32})`: `pytest.raises(ledger.UsageLedgerError, match='schema MD5 claim')` |
| `#6` | `line 346` (`name='full'`) | `test_actual_completed_capture_is_portable_and_refuses_changed_bytes` | `line 361` (`name='full'`) | `routing-portable` | `with_schema_claims({'full_path': 'unrelated/schema.yaml'})`: `pytest.raises(ledger.UsageLedgerError, match='schema path claim')` |
| `#7` | `line 344` (`name='core'`) | `test_actual_completed_capture_is_portable_and_refuses_changed_bytes` | `line 359` (`name='core'`) | `routing-portable` | `with_schema_claims({'core_md5': '0' * 32})`: `pytest.raises(ledger.UsageLedgerError, match='schema MD5 claim')` |
| `#8` | `line 346` (`name='core'`) | `test_actual_completed_capture_is_portable_and_refuses_changed_bytes` | `line 361` (`name='core'`) | `routing-portable` | `with_schema_claims({'core_path': 'unrelated/schema.yaml'})`: `pytest.raises(ledger.UsageLedgerError, match='schema path claim')` |
| `#9` | `line 347` | `test_actual_completed_capture_is_portable_and_refuses_changed_bytes` | `line 362` | `routing-portable` | `assert complete.recheck_completed(with_schema_claims(md5s)) == initial` |
| `#10` | `line 361` (`targets[0] = str(spec.full_path)`) | `test_actual_completed_capture_refuses_tampered_bytes_and_ledger` | `line 384` (`targets[0]`) | `routing-portable-tamper` | Appended `b'\n# altered captured bytes\n'` to `spec.full_path`: `pytest.raises((ValueError, ledger.UsageLedgerError))` |
| `#11` | `line 361` (`targets[1] = str(spec.core_path)`) | `test_actual_completed_capture_refuses_tampered_bytes_and_ledger` | `line 384` (`targets[1]`) | `routing-portable-tamper` | Appended `b'\n# altered captured bytes\n'` to `spec.core_path`: `pytest.raises((ValueError, ledger.UsageLedgerError))` |
| `#12` | `line 361` (`targets[2] = str(spec.report_path)`) | `test_actual_completed_capture_refuses_tampered_bytes_and_ledger` | `line 384` (`targets[2]`) | `routing-portable-tamper` | Appended `b'\n# altered captured bytes\n'` to `spec.report_path`: `pytest.raises((ValueError, ledger.UsageLedgerError))` |
| `#13` | `line 361` (`targets[3] = str(spec.bundle)`) | `test_actual_completed_capture_refuses_tampered_bytes_and_ledger` | `line 384` (`targets[3]`) | `routing-portable-tamper` | Appended `b'\n# altered captured bytes\n'` to `spec.bundle`: `pytest.raises((ValueError, ledger.UsageLedgerError))` |
| `#14` | `line 361` (`targets[4] = str(api._receipt_path(spec))`) | `test_actual_completed_capture_refuses_tampered_bytes_and_ledger` | `line 384` (`targets[4]`) | `routing-portable-tamper` | Appended `b'\n# altered captured bytes\n'` to `api._receipt_path(spec)`: `pytest.raises((ValueError, ledger.UsageLedgerError))` |
| `#15` | `line 361` (`targets[5] = full_schema root`) | `test_actual_completed_capture_refuses_tampered_bytes_and_ledger` | `line 384` (`targets[5]`) | `routing-portable-tamper` | Appended `b'\n# altered captured bytes\n'` to `full_schema` root: `pytest.raises((ValueError, ledger.UsageLedgerError))` |
| `#16` | `line 361` (`targets[6] = routing.artifact`) | `test_actual_completed_capture_refuses_tampered_bytes_and_ledger` | `line 384` (`targets[6]`) | `routing-portable-tamper` | Appended `b'\n# altered captured bytes\n'` to `routing.artifact`: `pytest.raises((ValueError, ledger.UsageLedgerError))` |
| `#17` | `line 378` (`kind = 'usage_id'`) | `test_actual_completed_capture_refuses_tampered_bytes_and_ledger` | `line 401` (`kind='usage_id'`) | `routing-portable-tamper` | `rows[0]['usage_id'] = 'foreign-call'`: `pytest.raises((ValueError, ledger.UsageLedgerError))` |
| `#18` | `line 378` (`kind = 'usage_counter'`) | `test_actual_completed_capture_refuses_tampered_bytes_and_ledger` | `line 401` (`kind='usage_counter'`) | `routing-portable-tamper` | `rows[0]['input_tokens'] += 1`: `pytest.raises((ValueError, ledger.UsageLedgerError))` |
| `#19` | `line 378` (`kind = 'lost_admission'`) | `test_actual_completed_capture_refuses_tampered_bytes_and_ledger` | `line 401` (`kind='lost_admission'`) | `routing-portable-tamper` | `data[admission.KEY]['rows'].pop(0)`: `pytest.raises((ValueError, ledger.UsageLedgerError))` |
| `#20` | `line 378` (`kind = 'lost_typed_stage'`) | `test_actual_completed_capture_refuses_tampered_bytes_and_ledger` | `line 401` (`kind='lost_typed_stage'`) | `routing-portable-tamper` | `data['typed_audit']['stages'].pop(0)`: `pytest.raises((ValueError, ledger.UsageLedgerError))` |
| `#21` | `line 387` (`missing` intermediate `_full.yaml`) | `test_actual_completed_capture_refuses_tampered_bytes_and_ledger` | `line 410` | `routing-portable-tamper` | Omitted intermediate `_full.yaml` from `files`/`blobs`: `pytest.raises((ValueError, ledger.UsageLedgerError))` |

---

## 3. Commands Executed, Results, Durations, and Saved Logs

All validation logs are preserved under `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy4-ci-routing-portable-split-20261111/tmp/`:

| Step | Command | Exit Code | Duration | Result Summary & Saved Log Path |
| --- | --- | --- | --- | --- |
| **1. Collection Canary (`120s` cap)** | `PYTHONPYCACHEPREFIX=/tmp/agy4-pycache PYTHONPATH=src /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python -m pytest tests/test_source_heading_runtime_api.py --collect-only -q -p no:cacheprovider` | `0` | `1.92s` (`4s` wall) | **Passed**: `19 tests collected in 1.92s`, showing both `tests/test_source_heading_runtime_api.py::test_actual_completed_capture_is_portable_and_refuses_changed_bytes` and `tests/test_source_heading_runtime_api.py::test_actual_completed_capture_refuses_tampered_bytes_and_ledger`. Log: `tmp/collect-only-runtime-api.log`. |
| **2. Sharding Contract Suite (`600s` cap)** | `PYTHONPYCACHEPREFIX=/tmp/agy4-pycache PYTHONPATH=src /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python -m pytest tests/test_ci_sharding.py -v -p no:cacheprovider` | `0` | `117.15s` (`1m57s`) | **Passed**: `77 passed, 1 warning in 117.15s (0:01:57)`, including `test_explicit_lanes_and_real_shards_equal_full_default_collection` (`6` and `8` shards, weighted and unweighted), `test_dedicated_collect_only_does_not_pass_as_execution[routing-portable-tamper]`, and `test_case_workflow_binds_all_lanes_and_retains_budget_setup_and_evidence`. Log: `tmp/test_ci_sharding.log`. |
| **3a. Host Load Check** | `uptime` | `0` | `<1s` | **Passed**: `load averages: 7.39 7.66 10.57` (1-minute load `7.39 < 25`). |
| **3b. Dedicated Lane Execution Canary (`routing-portable-tamper`)** | `PYTHONPYCACHEPREFIX=/tmp/agy4-pycache PYTHONPATH=src /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python -m pytest tests -v -p no:cacheprovider -p utils.pytest_shard --ci-lane=routing-portable-tamper` | `2` | `40.70s` | **Stopped at full-tree collection due to sparse-checkout paths omitted from the worktree (not retried per instructions)**: header printed `CI dedicated case routing-portable-tamper: tests/test_source_heading_runtime_api.py::test_actual_completed_capture_refuses_tampered_bytes_and_ledger`, and `utils.pytest_shard` selected the exact 1 target and deselected `22,354` items (`collected 22355 items / 14 errors / 22354 deselected / 1 selected`), but full `tests` collection aborted with 14 collection `FileNotFoundError`/`ModuleNotFoundError` errors on paths outside the sparse checkout. Log: `tmp/routing-portable-tamper-canary.log`. |
| **4. Local Git Commit** | `GIT_CONFIG_GLOBAL=/dev/null git -C /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy4-ci-routing-portable-split-20261111 add ... && GIT_CONFIG_GLOBAL=/dev/null git -C ... commit -m "Split routing-portable dedicated CI lane into two single-process lanes"` | `0` | `4s` | **Committed locally**: `e999aa7453ffe2e8ba389767463260e65977480c` (`5 files changed, 108 insertions(+), 87 deletions(-)`). |

---

## 4. Missing Sparse-Checkout Paths Identified (Not Added Locally)

As required by the assignment, no paths were added to the sparse checkout (`src tests utils project docs scripts .github .claude config data/preprocessed data/rubric`). Running `--ci-lane=routing-portable-tamper` across `tests` requires the following paths that are absent from this sparse checkout:

1. **Required at full-suite `tests` collection time (`14` collection errors in `tmp/routing-portable-tamper-canary.log`)**:
   - `notes/absence_v3_v4_second_reading_judgements_3876.yaml` (imported by `tests/test_absence_second_reading.py:37`)
   - `notes/matched_cborg_2026-09-13/audit_controls.py` (imported by `tests/test_audit_recall_leak_rendered.py:104` and `tests/test_wave7_5213_d76_binding_records.py:8`)
   - `notes/matched_cborg_2026-09-13/budgeted_cborg.py` (loaded at import time by `tests/test_canary_attempt_caps.py:14`, `tests/test_canary_budget_continuation.py:13`, and `tests/test_evaluation/test_streaming_api_judge.py:19`)
   - `notes/reference_rescore_2026-09-12_cborg_runtime/execution_tools/write_completion_summary.py` (loaded at import time by `tests/test_cborg_report_publication.py:16`)
   - `notes/claudecode_direct/run_direct_canary_awake.py` (loaded at import time by `tests/test_direct_keep_awake.py:16`)
   - `notes/native_trace_comparison_2026-10-08/compare_trace.py` (loaded at import time by `tests/test_native_trace_comparison.py:20`)
   - `data/ro-crate_packages/crate_manifest.yaml` (read at import time by `tests/test_release_inventory.py:18`)
   - `data/_wcrate/` and `data/wcrates/` (read during `pytest.mark.parametrize` collection in `tests/test_wcrate_copies.py:47`)
   - `fairscape_models/` submodule (imported by `tests/test_fairscape_integration/test_canonical_routes.py:21`, `tests/test_fairscape_integration/test_forward_typed_projections.py:18`, and `tests/test_fairscape_integration/test_nested_dataset_readback.py:13`)
2. **Required at `draft_files` fixture setup time when executing `tests/test_source_heading_runtime_api.py`**:
   - `notes/D4D_MISSING_URI_RECOMMENDATIONS.tsv` (read by `draft_files` at `tests/test_source_heading_runtime_api.py:40`).

---

## 5. What Stays Unverified Until the Hosted CI Run

1. **End-to-end execution of `test_actual_completed_capture_is_portable_and_refuses_changed_bytes` (`routing-portable`) and `test_actual_completed_capture_refuses_tampered_bytes_and_ledger` (`routing-portable-tamper`)**:
   - Because `routing-portable-tamper` halted at full-suite collection due to the 14 missing sparse-checkout paths above (and `notes/D4D_MISSING_URI_RECOMMENDATIONS.tsv` is also outside the sparse checkout), and `routing-portable` was not run locally per instructions, actual test-body execution of both split functions awaits a checkout with full paths / the hosted CI run.
2. **Actual wall-clock balance between `routing-portable` and `routing-portable-tamper`**:
   - The per-call costs behind the split between Calls `#2–#9` (`routing-portable`) and Calls `#10–#21` (`routing-portable-tamper`) are reconstruction-depth estimates, not measured per-call timings. Only the hosted GitHub Actions run will measure the real wall-clock duration and balance of the two lanes.
3. **Combined PR critical-path wall time alongside AGY1's ordinary-shard changes**:
   - AGY1's ordinary-shard floor is governed by the shard holding the `1,416s` pipeline test (`~25m` test floor, `26m–28m` expected shard wall time). The hosted run on the combined branch will establish the actual wall-clock durations of both `routing-portable` lanes and the rebalanced ordinary shards.

---

## Execution by node id

After the lead added `notes/claudecode_direct` to the worktree's sparse checkout (materializing `notes/D4D_MISSING_URI_RECOMMENDATIONS.tsv`), both split test functions were executed once by node ID in parallel on frozen commit `e999aa7453ffe2e8ba389767463260e65977480c` after verifying host load (`uptime`: `6.16 7.04 9.04`, 1-minute load `6.16 < 25`), using separate base temp roots outside any git worktree (`/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-agy4-a2-basetemp-20261111/tamper` and `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-agy4-a2-basetemp-20261111/portable`).

| Node ID | Command (from worktree root `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy4-ci-routing-portable-split-20261111`) | Exit Status | JUnit Counts (`tests` / `failures` / `errors` / `skipped`) | JUnit Case / Suite Time | Pytest Reported Wall Time |
| --- | --- | --- | --- | --- | --- |
| `tests/test_source_heading_runtime_api.py::test_actual_completed_capture_refuses_tampered_bytes_and_ledger` | `PYTHONPYCACHEPREFIX=/tmp/agy4-pycache-tamper PYTEST_DEBUG_TEMPROOT=/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-agy4-a2-basetemp-20261111/tamper PYTHONPATH=src /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python -m pytest tests/test_source_heading_runtime_api.py::test_actual_completed_capture_refuses_tampered_bytes_and_ledger -v -p no:cacheprovider --junitxml=/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy4-ci-routing-portable-split-20261111/tmp/junit-routing-portable-tamper-by-node.xml` | `0` | `tests=1`, `failures=0`, `errors=0`, `skipped=0` (`1 passed`) | `654.849s` case / `656.650s` suite | **`656.65s` (`0:10:56`)** |
| `tests/test_source_heading_runtime_api.py::test_actual_completed_capture_is_portable_and_refuses_changed_bytes` | `PYTHONPYCACHEPREFIX=/tmp/agy4-pycache-portable PYTEST_DEBUG_TEMPROOT=/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-agy4-a2-basetemp-20261111/portable PYTHONPATH=src /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python -m pytest tests/test_source_heading_runtime_api.py::test_actual_completed_capture_is_portable_and_refuses_changed_bytes -v -p no:cacheprovider --junitxml=/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy4-ci-routing-portable-split-20261111/tmp/junit-routing-portable-by-node.xml` | `0` | `tests=1`, `failures=0`, `errors=0`, `skipped=0` (`1 passed`) | `830.487s` case / `832.272s` suite | **`832.27s` (`0:13:52`)** |

### Saved Execution Logs and JUnit XML Artifacts

| Artifact | Path | Size (bytes) | SHA-256 |
| --- | --- | --- | --- |
| `routing-portable-tamper` node execution log | `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy4-ci-routing-portable-split-20261111/tmp/exec-routing-portable-tamper-by-node.log` | `1,995` | `7cf56919b7088aaffaeb14c7f22149453814caedcd05ad14d182c68450e1e117` |
| `routing-portable` node execution log | `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy4-ci-routing-portable-split-20261111/tmp/exec-routing-portable-by-node.log` | `1,992` | `62d25500de3cc15d6a82baa4db8fda08b3035321f7684b26f0dd908552d81f86` |
| `routing-portable-tamper` JUnit XML | `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy4-ci-routing-portable-split-20261111/tmp/junit-routing-portable-tamper-by-node.xml` | `385` | `3b65bef6ddbe1a3bc82e861cb4aee1cee671a8682fb747ac09cdcbf89aab6182` |
| `routing-portable` JUnit XML | `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy4-ci-routing-portable-split-20261111/tmp/junit-routing-portable-by-node.xml` | `389` | `7d78eea77156b3a224ff2bd0d72b188c588d4a344deb1cd99dfbece4c5acc447` |


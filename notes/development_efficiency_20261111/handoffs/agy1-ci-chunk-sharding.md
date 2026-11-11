# AGY1 Handoff: Sub-File Chunk Sharding Above a Duration Threshold

- **Agent**: `AGY1` (`window 3155 / /dev/ttys034`)
- **Date**: `2026-11-11`
- **Assignment**: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/notes/development_efficiency_20261111/assignments/claude-lead-agy1-ci-chunk-sharding.md`
- **Follow-up Stop Notice**: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/notes/development_efficiency_20261111/assignments/claude-lead-agy1-chunk-slice-stopped.md`
- **Worktree**: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy1-ci-chunk-sharding-20261111`
- **Branch**: `agy/ci-chunk-sharding-20261111`
- **Base Commit (`HEAD` at start)**: `925d726d67cdd03fe28fdeafdde60fa27df57205`
- **Preserved Local Evidence Commit (by Claude lead, unpushed, not for merge)**: `bc4649524238ab583c136b9a04eac982e977e01a`

---

## Status: stopped by the lead

The sub-file chunk sharding slice is **stopped** and is not going to a PR.

The Claude lead replayed `balanced_nodeids` exactly as written against the actual per-test durations recorded in hosted run `42947560899` (using committed weights from run `42916359440`, so out of sample). Summed case time on the slowest shard:

| Shards | Existing file-level partition | Your chunked partition |
|---:|---:|---:|
| 8 | 7,434 s | 8,534 s |
| 6 | 9,351 s | 11,079 s |

- **Why the chunked partition makes the slowest shard slower**: Whole-file weights in `utils/ci_test_durations.json` do not record which individual tests inside a file are slow, and in the heavy files most of the duration sits in a few tests. Splitting a heavy file into equal-count chunks billed at an equal share of the file weight mis-estimates chunk loads by hundreds of seconds each. The replay also does not count the extra module and class fixture setup across split chunks, so true wall-clock performance would be even worse (as `AGY2`'s pre-review predicted).
- **What actually caused the shard spread in run `42947560899`**: The lead's replay (`scripts/adhoc/replay_chunk_sharding_true_load_20261111.py` and `tmp/chunk-replay-20261111/` in the report worktree) showed that shards 2 and 3 ran at about `0.63` of their predicted time across nearly all their files while shard 8 ran at `1.17` — a hosted runner throughput effect, not a partition defect.
- **Correction to the earlier bottleneck assessment's description of `tests/test_bc1_g2_journal.py`**: `AGY1`'s earlier bottleneck assessment described `test_every_bc1_response_is_journaled_before_parse` in `tests/test_bc1_g2_journal.py` as having a seven-iteration loop over independent subdirectories. **That earlier description was wrong**: no such seven-iteration loop exists (the test runs a single stateful multi-phase `pipeline(...)` call with a shared `observed` dict; see Section 3).
- **Preserved local evidence**: The Claude lead committed the three implementation/provenance files locally as `bc4649524238ab583c136b9a04eac982e977e01a` on `agy/ci-chunk-sharding-20261111` (unpushed, marked as evidence, not for merge).

---

## 1. Commit Status & Preserved Files

The Claude lead committed the following three files locally on `agy/ci-chunk-sharding-20261111` at commit `bc4649524238ab583c136b9a04eac982e977e01a` (unpushed evidence commit):

| Status | Relative Path in Worktree | Absolute Path | SHA256 |
|---|---|---|---|
| Committed (`bc46495242`) | `utils/pytest_shard.py` | `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy1-ci-chunk-sharding-20261111/utils/pytest_shard.py` | `ff3266c50191078cd988a80ba24d34e5480e3bff4276674612d0e30b2da1f8e0` |
| Committed (`bc46495242`) | `tests/test_ci_sharding.py` | `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy1-ci-chunk-sharding-20261111/tests/test_ci_sharding.py` | `56c7d787226c038005367210a3551461dbffe248d69163529e5f16c6e96c76fe` |
| Committed (`bc46495242`) | `scripts/adhoc/verify_chunk_sharding_partition_20261111.py` | `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy1-ci-chunk-sharding-20261111/scripts/adhoc/verify_chunk_sharding_partition_20261111.py` | `41a2d62e991f7fef32bc0f54554bea434cec7d9c75c1bb4ed21524e2726a764e` |

Retained local verification output (under gitignored `tmp/`, not committed):
- `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy1-ci-chunk-sharding-20261111/tmp/partition_proof_20261111.json` (SHA256 `f07b160353a15920dd75dfbebd90b88c7255521fe46326d5fca2ce1b8149c857`)

Table-rendering script (in the report worktree's sibling `tmp/` directory) used to regenerate all figures and tables in Sections 2, 4.1, 4.2, and 5 directly from `tmp/partition_proof_20261111.json`:
```zsh
/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/notes/development_efficiency_20261111/tmp/render_agy1_partition_tables_20261111.py
```

**Files explicitly left unchanged**:
- `tests/test_bc1_g2_journal.py` (see Section 3 stop condition)
- `utils/ci_test_durations.json` (SHA256 `99a5f47162f3e059df4c5cc37e57b9f8ffe7777505ca1155464ff91d62a658eb`)
- `.github/workflows/Test-with-PyTest.yaml` and `.github/workflows/Test-D4D-Execution-Single-Routes.yaml`

---

## 2. Threshold Choice & Bounded Fixture-Setup Trade-Off

- **Named constant**: `CHUNK_THRESHOLD_SECONDS = 300.0` (`5 minutes` of estimated sequential case-sum duration in `utils/ci_test_durations.json`).
- **Splitting rule (`balanced_nodeids`)**:
  - Dedicated targets (`DEDICATED_CASE_LANES`, 7 node IDs) are filtered out first and never appear in the returned mapping.
  - Ordinary collected node IDs are grouped by test file path in first-seen collection order (`22,528` collected occurrences / `22,527` unique ordinary node IDs across `671` ordinary files in `collect2.log`).
  - A file is kept as a single unit (`chunk_count = 1`) whenever `len(file_items) <= 1` or `estimate <= CHUNK_THRESHOLD_SECONDS`.
  - A multi-item file with `estimate > CHUNK_THRESHOLD_SECONDS` is split into:
    $$\text{chunk\_count} = \min\left(\text{len(file\_items)},\ \text{total},\ \lceil \text{estimate} / \text{chunk\_seconds} \rceil\right)$$
    contiguous chunks in collection order (`start = idx * count // chunk_count`, `end = (idx + 1) * count // chunk_count`), with each chunk weighted proportionally (`estimate * len(chunk) / count`).
  - **Distinct-shard-per-chunk invariant**: All units (unsplit files and split chunks) are sorted descending by `(unit_weight, -item_count, file_path, chunk_index)` and assigned greedily by longest-processing-time (LPT) to the lightest shard **that does not already hold a chunk of the same file** (`candidates = [idx for idx in range(total) if idx not in file_shards[path]]`).
- **Breakdown of the 671 ordinary files at `300.0s` (from `tmp/partition_proof_20261111.json`)**:
  1. **638 of 671 ordinary test files (`95.1%`) have `estimate <= 300.0s`** (`15,351.582s` total weight, `30.0%` of ordinary weight) and incur **zero** extra module/class fixture setups across shards.
  2. **2 files above `300.0s` have only `1` collected item** (`tests/test_bc1_pipeline.py` at `1912.934s` and `tests/test_assistant_generation_integration.py` at `307.404s`, totaling `2,220.338s` / `4.3%` of ordinary weight) and are never split (`chunk_count = 1`).
  3. **31 multi-item files (`4.6%` of ordinary files) exceed `300.0s`**, accounting for **`33,533.901s` (`65.6%`)** of the entire `51,105.821s` committed ordinary weight.
  4. Restricting each chunk of a split file to a distinct shard bounds module/class fixture duplication to at most `chunk_count <= total` shards (`102` total chunks = `71` extra file-shard visits across all 671 files for `total = 6`; `111` total chunks = `80` extra file-shard visits for `total = 8`).

---

## 3. Stop Condition Triggered on `tests/test_bc1_g2_journal.py` (Left Unchanged)

The assignment specified:
> *"In `tests/test_bc1_g2_journal.py`: turn the seven-iteration loop in `test_every_bc1_response_is_journaled_before_parse` into seven parametrized cases, **only if** each iteration is already independent (its own `tmp_path` subdirectory, a fresh spec, no assertion after the loop that needs all seven). If any cross-iteration state exists, stop and report it instead of changing the test's meaning."*

Inspection of `tests/test_bc1_g2_journal.py` (`lines 45–86`) showed that **our earlier bottleneck assessment's description of a seven-iteration loop over independent subdirectories in `test_every_bc1_response_is_journaled_before_parse` was wrong**:
1. There is no 7-iteration `tmp_path` loop in `test_every_bc1_response_is_journaled_before_parse`. Instead, it monkeypatches `runtime._rebuild` to record pre-parse disk journal states into a shared `observed: dict[str, dict[str, object]] = {}` dictionary across a single end-to-end call to `pipeline(registered, journal_launch_monitor)` (which delegates to `test_public_bc1_pipeline_multiple_groups_final_and_completed_replay`).
2. Inside that single pipeline run, 7 sequential phases (`PHASES` in `test_bc1_pipeline.py`) share a single workspace/spec, mutate cumulative run state from initial launch through replay/finalization, and emit `typed_rows` (`usage.jsonl`) and `journal_rows` (`raw_response_journal.jsonl`).
3. Lines `76–86` execute aggregate post-run assertions over all collected rows simultaneously:
   - `assert len(typed_rows) == len(journal_rows) == len(observed)`
   - `assert {row["phase"] for row in typed_rows} == set(runtime.PHASES)`
   - `assert set(observed) == {row["usage_id"] for row in typed_rows}`

Because the phases are stateful across a single pipeline workspace and the post-run assertions require all phases in `runtime.PHASES` to have populated `observed` together, `tests/test_bc1_g2_journal.py` was **left completely unchanged** per the stop condition.

---

## 4. Files Above `300.0s` & Split-File Table (`total = 6` and `total = 8`)

Generated directly from `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy1-ci-chunk-sharding-20261111/tmp/partition_proof_20261111.json` via `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/notes/development_efficiency_20261111/tmp/render_agy1_partition_tables_20261111.py`.

### 4.1 Unsplit Single-Item Files Above Threshold (`2` files)

| File | Ordinary Items | Committed Weight (s) | Assigned Shard (`total = 6`) | Assigned Shard (`total = 8`) | Why Unsplit |
|---|---:|---:|---:|---:|---|
| `tests/test_bc1_pipeline.py` | 1 | `1912.934` | `1` | `1` | `ordinary_items == 1` |
| `tests/test_assistant_generation_integration.py` | 1 | `307.404` | `3` | `6` | `ordinary_items == 1` |

*(No uncollected file in `utils/ci_test_durations.json` has weight `> 300.0s`.)*

### 4.2 Multi-Item Files Split Above `300.0s` (`31` files)

| # | File | Ordinary Items | Weight (s) | `total = 6` Chunks (`k`) | `total = 6` Chunk Sizes (items) | `total = 6` Assigned Shards (in chunk order) | `total = 8` Chunks (`k`) | `total = 8` Chunk Sizes (items) | `total = 8` Assigned Shards (in chunk order) |
|---:|---|---:|---:|---:|---|---|---:|---|---|
| 1 | `tests/test_report_admission.py` | 32 | `5162.752` | 6 | `5, 5, 6, 5, 5, 6` | `4, 5, 2, 6, 1, 3` | 8 | `4, 4, 4, 4, 4, 4, 4, 4` | `2, 3, 4, 5, 6, 7, 8, 1` |
| 2 | `tests/test_d42_claude_d55.py` | 23 | `3418.224` | 6 | `3, 4, 4, 4, 4, 4` | `1, 3, 4, 5, 6, 2` | 8 | `2, 3, 3, 3, 3, 3, 3, 3` | `1, 4, 5, 6, 7, 8, 2, 3` |
| 3 | `tests/test_shared_generation_runtime.py` | 10 | `2999.822` | 6 | `1, 2, 2, 1, 2, 2` | `3, 4, 5, 1, 6, 2` | 8 | `1, 1, 1, 2, 1, 1, 1, 2` | `8, 7, 6, 2, 4, 5, 1, 3` |
| 4 | `tests/test_download/test_api_runner.py` | 158 | `2539.521` | 6 | `26, 26, 27, 26, 26, 27` | `5, 6, 3, 2, 1, 4` | 8 | `19, 20, 20, 20, 19, 20, 20, 20` | `3, 4, 5, 6, 1, 7, 8, 2` |
| 5 | `tests/test_generation_specificity_skill.py` | 380 | `1803.166` | 6 | `63, 63, 64, 63, 63, 64` | `3, 6, 4, 5, 1, 2` | 7 | `54, 54, 54, 55, 54, 54, 55` | `2, 6, 4, 7, 8, 1, 3` |
| 6 | `tests/test_d69_artifact_completeness.py` | 11 | `1522.922` | 6 | `1, 2, 2, 2, 2, 2` | `1, 2, 3, 5, 6, 4` | 6 | `1, 2, 2, 2, 2, 2` | `1, 3, 5, 4, 6, 7` |
| 7 | `tests/test_native_execution.py` | 73 | `1402.260` | 5 | `14, 15, 14, 15, 15` | `1, 5, 3, 4, 2` | 5 | `14, 15, 14, 15, 15` | `6, 3, 7, 8, 2` |
| 8 | `tests/test_bc1_g2_journal.py` | 4 | `1062.111` | 4 | `1, 1, 1, 1` | `4, 1, 2, 3` | 4 | `1, 1, 1, 1` | `5, 6, 4, 8` |
| 9 | `tests/test_pr5531_regressions.py` | 29 | `1010.513` | 4 | `7, 7, 7, 8` | `4, 2, 3, 5` | 4 | `7, 7, 7, 8` | `3, 1, 8, 5` |
| 10 | `tests/test_source_heading_runtime_api.py` | 14 | `933.863` | 4 | `3, 4, 3, 4` | `1, 5, 2, 6` | 4 | `3, 4, 3, 4` | `6, 8, 2, 3` |
| 11 | `tests/test_receipt_completion_runtime.py` | 85 | `898.762` | 3 | `28, 28, 29` | `4, 2, 6` | 3 | `28, 28, 29` | `8, 2, 7` |
| 12 | `tests/test_evaluation/test_cross_family_judge_analysis.py` | 35 | `897.451` | 3 | `11, 12, 12` | `6, 3, 5` | 3 | `11, 12, 12` | `7, 4, 5` |
| 13 | `tests/test_wave7_5213_d76_round2_binding.py` | 47 | `864.589` | 3 | `15, 16, 16` | `3, 4, 2` | 3 | `15, 16, 16` | `2, 7, 6` |
| 14 | `tests/test_native_receipt_origin_reporting.py` | 76 | `780.934` | 3 | `25, 25, 26` | `5, 6, 2` | 3 | `25, 25, 26` | `7, 5, 2` |
| 15 | `tests/test_native_attempt_supervisor.py` | 87 | `750.861` | 3 | `29, 29, 29` | `2, 3, 5` | 3 | `29, 29, 29` | `7, 5, 6` |
| 16 | `tests/test_shared_generation_scope_context.py` | 13 | `728.937` | 3 | `4, 4, 5` | `4, 1, 3` | 3 | `4, 4, 5` | `6, 5, 4` |
| 17 | `tests/test_usage_ledger.py` | 60 | `624.980` | 3 | `20, 20, 20` | `3, 1, 5` | 3 | `20, 20, 20` | `6, 5, 7` |
| 18 | `tests/test_routed_condition_reporting.py` | 68 | `598.424` | 2 | `34, 34` | `6, 5` | 2 | `34, 34` | `8, 3` |
| 19 | `tests/test_source_heading_output_layout.py` | 10 | `577.254` | 2 | `5, 5` | `3, 6` | 2 | `5, 5` | `4, 5` |
| 20 | `tests/test_wave7_5213_d76_round3_binding.py` | 42 | `545.039` | 2 | `21, 21` | `6, 4` | 2 | `21, 21` | `5, 4` |
| 21 | `tests/test_d41_request_parity.py` | 6 | `451.892` | 2 | `3, 3` | `3, 5` | 2 | `3, 3` | `6, 1` |
| 22 | `tests/test_d69_round5_boundaries.py` | 71 | `448.768` | 2 | `35, 36` | `6, 2` | 2 | `35, 36` | `4, 5` |
| 23 | `tests/test_pr5212_round7_journal.py` | 24 | `435.419` | 2 | `12, 12` | `4, 6` | 2 | `12, 12` | `3, 8` |
| 24 | `tests/test_evaluation_model.py` | 48 | `422.582` | 2 | `24, 24` | `3, 1` | 2 | `24, 24` | `4, 3` |
| 25 | `tests/test_schema_straddle.py` | 18 | `417.416` | 2 | `9, 9` | `6, 2` | 2 | `9, 9` | `8, 1` |
| 26 | `tests/test_arm_comparison.py` | 81 | `412.386` | 2 | `40, 41` | `4, 5` | 2 | `40, 41` | `1, 2` |
| 27 | `tests/test_shared_generation_batch_authority.py` | 22 | `408.248` | 2 | `11, 11` | `2, 3` | 2 | `11, 11` | `3, 8` |
| 28 | `tests/test_registered_eval_runner.py` | 155 | `377.169` | 2 | `77, 78` | `5, 6` | 2 | `77, 78` | `8, 3` |
| 29 | `tests/test_bc1_registration.py` | 30 | `349.318` | 2 | `15, 15` | `6, 5` | 2 | `15, 15` | `7, 5` |
| 30 | `tests/test_generation_specificity_delegated.py` | 95 | `344.607` | 2 | `47, 48` | `4, 1` | 2 | `47, 48` | `2, 6` |
| 31 | `tests/test_pr5212_r4_fixes.py` | 5 | `343.711` | 2 | `2, 3` | `5, 4` | 2 | `2, 3` | `6, 2` |

- **Totals across the 31 split files**:
  - Total committed weight across the 31 split files: `33,533.901s` (`65.6%` of `51,105.821s`).
  - `total = 6` (`main`): `102` chunks across `31` files (`71` extra file-shard visits across the 671-file suite; every split file's chunks land on `k` distinct shards).
  - `total = 8` (`pull_request`): `111` chunks across `31` files (`80` extra file-shard visits across the 671-file suite; every split file's chunks land on `k` distinct shards).

---

## 5. Predicted Per-Shard Loads Before and After (From Committed Weights, Not Runtime Measurements)

> **Important caveat**: All numbers in Sections 5.1 and 5.2 are **static predictions computed from committed file weights in `utils/ci_test_durations.json`** ( assuming uniform per-item duration within each split file) over the `22,527` unique ordinary collected node IDs in `collect2.log`. They are **not** measured wall-clock shard runtimes, and as the lead's out-of-sample per-test replay demonstrated (see **Status: stopped by the lead** at the top), uniform per-item chunking of whole-file weights actually **increases** true summed case time on the slowest shard (`7,434s -> 8,534s` on 8 shards; `9,351s -> 11,079s` on 6 shards).

Static file-weight breakdown:
- The 671 ordinary files have a total committed weight of `51,105.821s` (`8517.637s` mean on 6 shards; `6388.228s` mean on 8 shards).
- The 640 unsplit files supply `17,571.920s` of weight (`15,351.582s` across the 638 files `<= 300.0s` plus `2,220.338s` across the 2 single-item files `> 300.0s`), allowing greedy LPT to pack the **static sum of file weights** on every shard to the mean (`8517.634s–8517.639s` on 6 shards; `6388.225s–6388.230s` on 8 shards) both before and after.
- Under `balanced_nodeids`, the predicted maximum multi-item file slice on any single shard drops from `5162.752s` to `968.016s` (`-81.2%`) on `main` and from `5162.752s` to `645.344s` (`-87.5%`) on `pull_request` under the uniform-item-weight assumption — an assumption falsified by the real per-test duration distribution inside those files.

### 5.1 `main` (`total = 6` Ordinary Shards) — Predicted Loads from Committed Weights

| Shard | Before (`balanced_files`) Items | Before Files | Before Predicted Total Weight (s) | Before Max Single-File Slice on Shard (s) | After (`balanced_nodeids`) Items | After Files Touched | After Predicted Total Weight (s) | After Max Single-File Slice on Shard (s) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 3682 | 110 | `8517.637` | `5162.752` | 3801 | 120 | `8517.635` | `1912.934` |
| 2 | 4226 | 112 | `8517.639` | `3418.224` | 3774 | 124 | `8517.638` | `968.016` |
| 3 | 3512 | 111 | `8517.634` | `2999.822` | 3480 | 125 | `8517.639` | `968.016` |
| 4 | 3881 | 112 | `8517.634` | `2539.521` | 3892 | 124 | `8517.635` | `806.680` |
| 5 | 3875 | 113 | `8517.639` | `1912.934` | 4165 | 125 | `8517.639` | `806.680` |
| 6 | 3351 | 113 | `8517.638` | `1803.166` | 3415 | 124 | `8517.635` | `806.680` |
| **Summary** | **22527** (unique `22527`) | **671** | **min `8517.634` / max `8517.639` (spread `0.005s`)** | **max `5162.752s`** | **22527** (unique `22527`) | **742 shard-file visits (`+71`)** | **min `8517.635` / max `8517.639` (spread `0.004s`)** | **max `1912.934s` (`968.016s` multi-item)** |

### 5.2 `pull_request` (`total = 8` Ordinary Shards) — Predicted Loads from Committed Weights

| Shard | Before (`balanced_files`) Items | Before Files | Before Predicted Total Weight (s) | Before Max Single-File Slice on Shard (s) | After (`balanced_nodeids`) Items | After Files Touched | After Predicted Total Weight (s) | After Max Single-File Slice on Shard (s) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 2513 | 77 | `6388.227` | `5162.752` | 2098 | 89 | `6388.226` | `1912.934` |
| 2 | 2661 | 84 | `6388.229` | `3418.224` | 2969 | 94 | `6388.229` | `645.344` |
| 3 | 2212 | 84 | `6388.227` | `2999.822` | 3346 | 93 | `6388.225` | `645.344` |
| 4 | 3425 | 85 | `6388.230` | `2539.521` | 2770 | 95 | `6388.229` | `645.344` |
| 5 | 3353 | 85 | `6388.229` | `1912.934` | 3054 | 95 | `6388.227` | `645.344` |
| 6 | 2868 | 85 | `6388.226` | `1803.166` | 2553 | 95 | `6388.229` | `645.344` |
| 7 | 2975 | 86 | `6388.228` | `1522.922` | 2734 | 95 | `6388.228` | `645.344` |
| 8 | 2520 | 85 | `6388.225` | `1402.260` | 3003 | 95 | `6388.229` | `645.344` |
| **Summary** | **22527** (unique `22527`) | **671** | **min `6388.225` / max `6388.230` (spread `0.005s`)** | **max `5162.752s`** | **22527** (unique `22527`) | **751 shard-file visits (`+80`)** | **min `6388.225` / max `6388.229` (spread `0.004s`)** | **max `1912.934s` (`645.344s` multi-item)** |

---

## 6. Figures Corrected Against `tmp/partition_proof_20261111.json`

When regenerating Sections 2, 4.1, 4.2, and 5 programmatically from `tmp/partition_proof_20261111.json` via `render_agy1_partition_tables_20261111.py`, the following figures were corrected from the initial handoff draft:

1. **Section 2**:
   - Total committed weight of the 31 split multi-item files (`> 300.0s`) corrected from `31,205.847s (61.1%)` to **`33,533.901s (65.6%)`** of `51,105.821s`, and the 638 unsplit files (`<= 300.0s`) explicitly stated as **`15,351.582s (30.0%)`** (plus `2,220.338s` for the 2 single-item files `> 300.0s`).
2. **Section 4.1**:
   - Checked against `single_item_files_above_threshold` in `evaluations["6"]` and `evaluations["8"]`: **no figures needed change** (`tests/test_bc1_pipeline.py` and `tests/test_assistant_generation_integration.py` matched in full).
3. **Section 4.2**:
   - **Rows 9–31**: Replaced all 23 hand-transcribed nonexistent file entries with the true 23 split files (`tests/test_pr5531_regressions.py` through `tests/test_pr5212_r4_fixes.py`) and their exact item counts, weights, chunk counts, chunk sizes, and shard assignments from `tmp/partition_proof_20261111.json`.
   - **Rows 2–8**: Corrected `total = 8` assigned shard lists on rows 2–8 (`test_d42_claude_d55.py`, `test_shared_generation_runtime.py`, `test_download/test_api_runner.py`, `test_generation_specificity_skill.py`, `test_d69_artifact_completeness.py`, `test_native_execution.py`, `test_bc1_g2_journal.py`), `total = 8` chunk-size ordering on rows 4 and 5 (`19, 20, 20, 20, 19, 20, 20, 20` and `54, 54, 54, 55, 54, 54, 55`), and `total = 6` assigned shards on row 8 (`4, 1, 2, 3`).
4. **Section 5**:
   - **Section 5 prose**: Corrected the 640-file unsplit weight sum from `17,679s` to **`17,571.920s`**.
   - **Section 5.1 (`total = 6`) table**: Replaced all per-shard `items`, `files` / `files_touched`, `predicted_seconds` (3rd decimal place on Shards 1, 2, 4 before and Shards 1, 2, 3, 5, 6 after), and `Before Max Single-File Slice` on Shards 5 and 6 (`1912.934s` on Shard 5 and `1803.166s` on Shard 6, rather than `1803.166s` and `1522.922s`) with the exact values from `evaluations["6"]["predicted_before_balanced_files"]` and `evaluations["6"]["predicted_after_balanced_nodeids"]`.
   - **Section 5.2 (`total = 8`) table**: Replaced all per-shard `items`, `files` / `files_touched`, and `predicted_seconds` (3rd decimal place) with the exact values from `evaluations["8"]["predicted_before_balanced_files"]` and `evaluations["8"]["predicted_after_balanced_nodeids"]`.

---

## 7. Validation Commands Run and Exact Results

1. **Canary unit test (`test_balanced_nodeids_pure_function_invariants[6]`)**:
   ```zsh
   PYTHONPATH=/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy1-ci-chunk-sharding-20261111:/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy1-ci-chunk-sharding-20261111/src /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/pytest -q -p no:cacheprovider /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy1-ci-chunk-sharding-20261111/tests/test_ci_sharding.py -k "test_balanced_nodeids_pure_function_invariants and 6"
   ```
   - **Result**: `1 passed, 77 deselected in 1.31s` (exit `0`).

2. **Both `6` and `8` unit nodes (`test_balanced_nodeids_pure_function_invariants`)**:
   ```zsh
   PYTHONPATH=/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy1-ci-chunk-sharding-20261111:/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy1-ci-chunk-sharding-20261111/src /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/pytest -q -p no:cacheprovider /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy1-ci-chunk-sharding-20261111/tests/test_ci_sharding.py -k "test_balanced_nodeids_pure_function_invariants"
   ```
   - **Result**: `2 passed, 76 deselected in 0.68s` (exit `0`).

3. **Full `tests/test_ci_sharding.py` suite**:
   ```zsh
   PYTHONPATH=/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy1-ci-chunk-sharding-20261111:/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy1-ci-chunk-sharding-20261111/src /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/pytest -q -p no:cacheprovider /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy1-ci-chunk-sharding-20261111/tests/test_ci_sharding.py
   ```
   - **Result**: `78 passed, 1 warning in 164.72s (0:02:44)` (exit `0`).

4. **Collection check on `tests/test_bc1_g2_journal.py`**:
   ```zsh
   PYTHONPATH=/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy1-ci-chunk-sharding-20261111:/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy1-ci-chunk-sharding-20261111/src /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/pytest -q -p no:cacheprovider --collect-only /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy1-ci-chunk-sharding-20261111/tests/test_bc1_g2_journal.py
   ```
   - **Result**: `4 tests collected in 0.87s` (exit `0`).

5. **Full-suite partition proof and before/after load comparison script (`22,535` collected items from `collect2.log`)**:
   ```zsh
   PYTHONPATH=/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy1-ci-chunk-sharding-20261111:/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy1-ci-chunk-sharding-20261111/src /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy1-ci-chunk-sharding-20261111/scripts/adhoc/verify_chunk_sharding_partition_20261111.py --output /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy1-ci-chunk-sharding-20261111/tmp/partition_proof_20261111.json
   ```
   - **Result**: Exit `0`.

6. **Table regeneration script from `tmp/partition_proof_20261111.json`**:
   ```zsh
   /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/notes/development_efficiency_20261111/tmp/render_agy1_partition_tables_20261111.py
   ```
   - **Result**: Exit `0`.

---

## 8. What Remains Unverified / Disposition

1. **Out-of-sample per-test replay falsified uniform sub-file chunking**: Because `utils/ci_test_durations.json` stores whole-file weights and the heavy files concentrate most of their runtime in a few tests, uniform equal-count chunking increases the slowest shard's summed case duration (`7,434s -> 8,534s` on 8 shards; `9,351s -> 11,079s` on 6 shards) before even counting duplicated module/class fixture setup.
2. **Slice stopped**: Per the Claude lead's decision, this slice is stopped and retained only as local commit `bc4649524238ab583c136b9a04eac982e977e01a` on `agy/ci-chunk-sharding-20261111` for evidence.

# AGY4 Handoff: Read-Only Analysis of the Completed D132 `382f0dfd1ce8` `cpu-monitoring` Diagnostic Run

- **Worker**: `agy4` (`E4` — Terminal window 6921, tab 1, `/dev/ttys010`)
- **Lead**: Claude lead (`window 5094`)
- **Track**: Native (offline synthetic pre-reservation diagnostic; not on the API route)
- **Assignment**: [claude-lead-agy4-diagnostic-result-analysis.md](file:///Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/notes/development_efficiency_20261111/assignments/claude-lead-agy4-diagnostic-result-analysis.md)
- **Provenance Script**: [analyze_wp1_382f_diagnostic_result_20261111.py](file:///Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/scripts/adhoc/analyze_wp1_382f_diagnostic_result_20261111.py)
- **Generated JSON**: [result-analysis.json](file:///Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/tmp/diagnostic-result-20261111/result-analysis.json) (`788,133` bytes, SHA-256 `4b104257ec4a752c71adddc1ddf739893dafdd7a83e3f67fbb18de27e5875c6f`)
- **Date**: 2026-11-11

## Command Used to Generate the Analysis JSON

```sh
/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python -S -P -B /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/scripts/adhoc/analyze_wp1_382f_diagnostic_result_20261111.py
```

Every number in the tables below comes from [result-analysis.json](file:///Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/tmp/diagnostic-result-20261111/result-analysis.json). Each conclusion is tagged `[measured]`, `[derived]`, or `[inference]`. All three runs are unqualified contended host diagnostics (`qualified: false`); no quiet-host figure or live-generation speedup claim is made.

---

## 1. Confirmation of the Lead's Table and Complete Phase CPU Breakdown

### 1.1 Verification of the Lead's Summary Table

- **[measured]** All seven columns of the lead's summary table in [claude-lead-agy4-diagnostic-result-analysis.md](file:///Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/notes/development_efficiency_20261111/assignments/claude-lead-agy4-diagnostic-result-analysis.md#L31-L35) match the exact 2-decimal-place rounded values from the three runs' `phase-metrics/*-measurement.json` (`phases[0].elapsed` and `phases[1].elapsed`), `phase-metrics/*-diagnostic.json` (`outcome`), and `*.outer.json` (`host_contention.max_one_minute_load_per_cpu`).
- **[measured]** One minor start-load detail on `382f0dfd1ce8`: the runner script log ([lead-cpu-monitoring-rerun-382f0dfd1ce8-20261111.log](file:///Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/lead-cpu-monitoring-rerun-382f0dfd1ce8-20261111.log)) recorded `start_load_1m_5m_15m=14.36 15.86 15.65` (`1.44` per CPU across `10` logical CPUs) immediately before invoking the supervisor, whereas [host-load.json](file:///Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/wp1-382f0dfd1ce8-cpu-monitoring-lead-rerun-20261111/host-load.json) inside the run directory recorded `before.load[0] = 13.7705078125` (`1.38` per CPU) at `2026-11-11T16:38:21.529064+00:00`. Both confirm an unqualified contended start.

| Source | Run Directory & PID | Fixture CPU s (`process_cpu`) | Fixture Wall s (`wall_monotonic`) | Launch CPU s (`process_cpu`) | Launch Wall s (`wall_monotonic`) | Start Load / CPU (`host-load.json`) | Max Load / CPU (`outer.json`) | Mean Host CPU % (`outer.json`) | Outcome (`diagnostic.json`) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| `3cc113e2606c` | `wp1-3cc113e2606c-cpu-monitoring-e1-observer-baseline-20261111` (`PID 64652`) | `149.126013` (`149.13`) | `160.995700` (`161.00`) | `275.663033` (`275.66`) | `302.462816` (`302.46`) | `0.800146` (`0.80`) | `1.576367` (`1.58`) | `61.458575%` (`61.5%`) | `genuine_refusal` |
| `458887766eff` | `wp1-458887766eff-cpu-monitoring-post-5834-20261111` (`PID 34474`) | `119.921989` (`119.92`) | `183.040185` (`183.04`) | `237.958053` (`237.96`) | `310.922975` (`310.92`) | `1.532812` (`1.53`) | `2.865332` (`2.87`) | `92.135551%` (`92.1%`) | `genuine_refusal` |
| `382f0dfd1ce8` | `wp1-382f0dfd1ce8-cpu-monitoring-lead-rerun-20261111` (`PID 67941`) | `110.880490` (`110.88`) | `138.842940` (`138.84`) | `243.398143` (`243.40`) | `295.745893` (`295.75`) | `1.377051` (`1.38`; runner log `1.44`) | `2.743604` (`2.74`) | `97.776019%` (`97.8%`) | `genuine_refusal` |

### 1.2 Phase-by-Phase Self User, Self System, and Reaped-Child CPU Breakdown

- **[measured]** In `phase-metrics/*-measurement.json`, `process_cpu` and `thread_cpu` measure the Python test worker process (`RUSAGE_SELF` / `CLOCK_PROCESS_CPUTIME_ID`), so `process_cpu == self_user_cpu + self_system_cpu` (within floating-point rounding of `RUSAGE_SELF` vs `clock_gettime`).
- **[measured]** `reaped_child_user_cpu` and `reaped_child_system_cpu` (`RUSAGE_CHILDREN`) are tracked separately per `cpu_policy` and are **not** included in `process_cpu`.
- **[derived]** Adding `reaped_child_total_cpu = reaped_child_user_cpu + reaped_child_system_cpu` to `process_cpu` gives total CPU consumed by the Python worker plus its reaped subprocesses (`self_plus_reaped_child_cpu`).

| Source | Phase | Call Rows (`[first, last)`) | `process_cpu` s | `thread_cpu` s | `self_user_cpu` s | `self_system_cpu` s | `reaped_child_user_cpu` s | `reaped_child_system_cpu` s | `reaped_child_total_cpu` s (`[derived]`) | `self + reaped_child` CPU s (`[derived]`) | `wall_monotonic` s |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `3cc113e2606c` | `fixture` | `521` (`0..521`) | `149.126013` | `149.126012` | `132.394365` | `16.731651` | `2.922378` | `4.151457` | `7.073835` | `156.199851` | `160.995700` |
| `3cc113e2606c` | `launch` | `530` (`521..1051`) | `275.663033` | `275.663011` | `213.979865` | `61.683168` | `4.668014` | `7.432917` | `12.100931` | `287.763964` | `302.462816` |
| `3cc113e2606c` | `fixture + launch` (`[derived]`) | `1051` (`0..1051`) | `424.789046` | `424.789023` | `346.374230` | `78.414819` | `7.590392` | `11.584374` | `19.174766` | `443.963815` | `463.458516` |
| `458887766eff` | `fixture` | `457` (`0..457`) | `119.921989` | `119.921989` | `97.171085` | `22.750902` | `3.281463` | `6.410084` | `9.691547` | `129.613534` | `183.040185` |
| `458887766eff` | `launch` | `537` (`457..994`) | `237.958053` | `237.958050` | `191.363264` | `46.594797` | `5.028861` | `8.882245` | `13.911106` | `251.869167` | `310.922975` |
| `458887766eff` | `fixture + launch` (`[derived]`) | `994` (`0..994`) | `357.880042` | `357.880040` | `288.534349` | `69.345699` | `8.310324` | `15.292329` | `23.602653` | `381.482701` | `493.963161` |
| `382f0dfd1ce8` | `fixture` | `457` (`0..457`) | `110.880490` | `110.880487` | `91.630159` | `19.250331` | `3.219667` | `5.910107` | `9.129774` | `120.010264` | `138.842940` |
| `382f0dfd1ce8` | `launch` | `665` (`457..1122`) | `243.398143` | `243.398140` | `183.609124` | `59.789019` | `5.833375` | `11.474900` | `17.308275` | `260.706418` | `295.745893` |
| `382f0dfd1ce8` | `fixture + launch` (`[derived]`) | `1122` (`0..1122`) | `354.278633` | `354.278627` | `275.239283` | `79.039350` | `9.053042` | `17.385007` | `26.438049` | `380.716682` | `434.588833` |

- **[derived]** Confirming the lead's observation: in the `382f0dfd1ce8` `launch` phase alone, `process_cpu` is `243.398143s` (`+33.398143s` above the `210.0s` effective freshness target), and `self + reaped_child` CPU is `260.706418s` (`+50.706418s` above `210.0s`). Because the Python worker is single-threaded (`threads: [8263655040]`) and waits synchronously on its reaped children, even at `100%` single-core utilization with zero host contention, `launch` wall time cannot be less than `243.398143s` (self CPU only) or `260.706418s` (self + reaped child CPU). Host contention is therefore **not** what stands between `382f0dfd1ce8` and the `210.0s` target.

---

## 2. Where the Launch Phase's CPU Goes on `382f0dfd1ce8`

### 2.1 Exact `cpu_policy` and Measurement Semantics

From [67941-measurement.json](file:///Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/wp1-382f0dfd1ce8-cpu-monitoring-lead-rerun-20261111/phase-metrics/67941-measurement.json) (`[measured]`):

> `"cpu_policy": "Phase process/thread CPU, self user/system and reaped-child CPU are separate. Inclusive function times overlap and are not added across functions."`

- **[measured]** Each row in `calls[457:1122]` (`665` rows, all on thread `8263655040`) records `inclusive_thread_cpu` and `inclusive_wall` from function entry to exit.
- **[measured]** Five coarse outer labels (`public_launch`, `engine_entry`, `launch_engine`, `controller_prewarm`, `accept_saved_capture`) also carry a `coarse_elapsed` object with `process_cpu`, `self_user_cpu`, `self_system_cpu`, `reaped_child_user_cpu`, `reaped_child_system_cpu`, `thread_cpu`, and `wall_monotonic`.
- **[measured]** One label (`accept_saved_capture`) is registered on two nested functions in `native_subscription_admission.py`: `accept_current_selection` (first line `108`, row `890`, `inclusive_thread_cpu = 14.553751s`) immediately calls `load_current` (first line `158`, row `891`, `inclusive_thread_cpu = 14.552713s`). Summing the two rows (`29.106464s`) double-counts the same `14.553751s` call; both the raw 2-row sum and the non-self-nested outer value (`14.553751s`) are shown below.
- **[derived]** Because every call row in `calls[457:1122]` has exact `entered_wall` and `left_wall` timestamps on a single thread (`0` open rows), the monitored call tree is strictly nested. Subtracting a call's direct monitored children's `inclusive_thread_cpu` from its own `inclusive_thread_cpu` yields its **unmonitored-self `thread_cpu`** (CPU spent inside that function and any unmonitored helpers it calls directly, without overlapping other monitored functions).

### 2.2 All 16 Monitored Labels in `382f0dfd1ce8` Launch Phase (`rows 457..1122`)

Ordered by non-self-nested `inclusive_thread_cpu` (`[measured]` inclusive metrics; `[derived]` unmonitored-self metrics from the call tree; inclusive columns are **not** summed across rows):

| Label | Function Name(s) (`file:first_line`) | Call Count (`call_counts`) | Distinct Code Objects | Inclusive `thread_cpu` Sum s (`[measured]`) | Inclusive `thread_cpu` Mean / Min / Max s (`[measured]`) | Inclusive `wall` Sum s (`[measured]`) | Unmonitored-Self `thread_cpu` s (`[derived]`) | Direct Monitored Children `thread_cpu` s (`[derived]`) | Monitored Parent(s) in `launch` (`count`) |
|---|---|---:|---:|---:|---|---:|---:|---:|---|
| `public_launch` | `synthetic_launch` (`native_shared_execution_orchestration.py:97`) | `1` | `1` | `243.397365` | `243.397365` / `243.397365` / `243.397365` | `295.745113` | `0.161396` | `243.235968` | `<phase_root> (1)` |
| `engine_entry` | `synthetic_launch` (`native_execution_orchestration.py:278`) | `1` | `1` | `219.599567` | `219.599567` / `219.599567` / `219.599567` | `268.011705` | `0.239430` | `219.360137` | `public_launch (1)` |
| `launch_engine` | `_launch` (`native_execution_orchestration.py:315`) | `1` | `1` | `209.585050` | `209.585050` / `209.585050` / `209.585050` | `255.900335` | `20.421243` | `189.163807` | `engine_entry (1)` |
| `shared_registration_verified` | `verified` (`native_shared_registration_orchestration.py:129`) | `9` | `1` | `108.372327` | `12.041370` / `9.774378` / `23.627346` | `130.140890` | `28.604915` | `79.767412` | `public_launch (1)`, `engine_entry (1)`, `launch_engine (6)`, `accept_saved_capture (1)` |
| `execution_registration_verified` | `verified` (`native_execution_registration_v2.py:678`) | `14` | `2` | `113.838536` | `8.131324` / `5.864857` / `20.590297` | `140.731167` | `53.939775` | `59.898761` | `shared_registration_verified (9)`, `launch_engine (2)`, `fresh_admission (2)`, `controller_prewarm (1)` |
| `preparer_verified` | `verify_preparer` (`native_execution_registration_v2.py:375`) | `21` | `15` | `66.579529` | `3.170454` / `1.045458` / `15.553598` | `84.176072` | `52.664646` | `13.914883` | `execution_registration_verified (14)`, `launch_engine (6)`, `fresh_admission (1)` |
| `controller_prewarm` | `prewarm_before_acceptance` (`native_shared_controller_orchestration.py:228`) | `1` | `1` | `64.187670` | `64.187670` / `64.187670` / `64.187670` | `72.393237` | `56.764656` | `7.423014` | `launch_engine (1)` |
| `selection_rebuild` | `_rebuild` (`native_shared_selection.py:356`) | `91` | `91` | `22.451025` | `0.246715` / `0.002975` / `4.199771` | `24.163610` | `0.399112` | `22.051912` | `selection_capture (88)`, `launch_engine (2)`, `controller_prewarm (1)` |
| `schema_reconstruction` | `_schemas` (`native_shared_selection.py:236`) | `3` | `3` | `19.181809` | `6.393936` / `4.088823` / `10.962201` | `20.746998` | `8.429480` | `10.752329` | `selection_rebuild (2)`, `schema_cache_lookup (1)` |
| `selection_capture` | `capture` (`native_shared_selection.py:487`) | `88` | `88` | `16.025877` | `0.182112` / `0.017609` / `11.124328` | `17.341500` | `1.857621` | `14.168257` | `preparer_verified (63)`, `execution_registration_verified (14)`, `launch_engine (8)`, `controller_prewarm (2)`, `accept_saved_capture (1)` |
| `fresh_admission` | `admit` (`native_execution_registration_v2.py:657`) | `1` | `1` | `14.925277` | `14.925277` / `14.925277` / `14.925277` | `19.838469` | `2.080373` | `12.844904` | `launch_engine (1)` |
| `accept_saved_capture` | `accept_current_selection` (`:108`) + nested `load_current` (`:158`) | `2` (`1` outer + `1` self-nested) | `2` | `14.553751` outer (`29.106464` raw 2-row sum) | `14.553232` / `14.552713` / `14.553751` | `19.235290` outer (`38.469202` raw) | `4.005415` (`0.001038` `:108` + `4.004377` `:158`) | `10.548336` (below `load_current`) | `launch_engine (1)`, `accept_saved_capture (1)` |
| `schema_cache_lookup` | `_cached_schemas` (`native_shared_selection.py:321`) | `89` | `89` | `13.832304` | `0.155419` / `0.002227` / `11.008074` | `14.935207` | `2.870103` | `10.962201` | `selection_rebuild (89)` |
| `schema_capture` | `_capture_native_schema` (`schema_snapshot.py:290`) | `6` | `3` | `10.752329` | `1.792055` / `1.448640` / `2.189955` | `11.767243` | `10.752329` | `0.000000` | `schema_reconstruction (6)` |
| `synthetic_peer_fingerprint` | `require_synthetic` (`native_runtime_profiles.py:122`) | `292` | `15` | `0.172770` | `0.000592` / `0.000283` / `0.002323` | `0.194463` | `0.172770` | `0.000000` | `shared_registration_verified (126)`, `launch_engine (71)`, `preparer_verified (42)`, `accept_saved_capture (30)`, `execution_registration_verified (14)`, `public_launch (6)`, `controller_prewarm (1)`, `engine_entry (1)`, `fresh_admission (1)` |
| `freshness_check` | `_fresh` (`native_subscription_guard_v2.py:419`) | `4` | `1` | `0.024341` | `0.006085` / `0.005512` / `0.006618` | `0.024580` | `0.024341` | `0.000000` | `freshness_before_dispatch (3)`, `freshness_before_reservation (1)` |
| `freshness_before_dispatch` | `before_dispatch` (`native_subscription_guard_v2.py:449`) | `3` | `1` | `0.018157` | `0.006052` / `0.005622` / `0.006698` | `0.018260` | `0.000267` | `0.017889` | `public_launch (1)`, `accept_saved_capture (1)`, `launch_engine (1)` |
| `u4b_binary_fingerprint` | `_binary_pin` (`native_u4b_runtime.py:48`) | `36` | `1` | `0.008962` | `0.000249` / `0.000181` / `0.000585` | `0.009105` | `0.008962` | `0.000000` | `shared_registration_verified (18)`, `launch_engine (12)`, `accept_saved_capture (5)`, `public_launch (1)` |
| `freshness_before_reservation` | `before_reservation` (`native_subscription_guard_v2.py:439`) | `1` | `1` | `0.006523` | `0.006523` / `0.006523` / `0.006523` | `0.006732` | `0.000071` | `0.006452` | `launch_engine (1)` |
| `legacy_binary_fingerprint` | `binary_fingerprint` (`native_legacy_Lightweight.py:130`) | `1` | `1` | `0.000460` | `0.000460` / `0.000460` / `0.000460` | `0.000459` | `0.000460` | `0.000000` | `launch_engine (1)` |

### 2.3 Coarse-Instrumented Launch Wrappers (`coarse_elapsed` User/System/Child Split on `382f0dfd1ce8`)

- **[measured]** The five coarse-instrumented rows in `launch` provide exact `self_user_cpu`, `self_system_cpu`, and `reaped_child` CPU for the major nested scopes of `launch`:

| Row | Label (`name`) | `process_cpu` s | `self_user_cpu` s | `self_system_cpu` s | `reaped_child_user_cpu` s | `reaped_child_system_cpu` s | `reaped_child_total_cpu` s (`[derived]`) | `wall_monotonic` s | Outcome |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---|
| `457` | `public_launch` (`synthetic_launch`) | `243.397353` | `183.608505` | `59.788848` | `5.833375` | `11.474900` | `17.308275` | `295.745109` | `exception:ValueError` |
| `504` | `engine_entry` (`synthetic_launch`) | `219.599562` | `164.087266` | `55.512296` | `5.263301` | `10.506781` | `15.770082` | `268.011699` | `exception:ValueError` |
| `540` | `launch_engine` (`_launch`) | `209.585046` | `156.607558` | `52.977488` | `4.909100` | `9.865579` | `14.774679` | `255.900330` | `exception:ValueError` |
| `863` | `controller_prewarm` (`prewarm_before_acceptance`) | `64.187662` | `58.972226` | `5.215436` | `0.219129` | `0.409052` | `0.628181` | `72.393232` | `return` |
| `890` | `accept_saved_capture` (`accept_current_selection`) | `14.553747` | `10.135772` | `4.417976` | `0.583192` | `1.124305` | `1.707497` | `19.235290` | `return` |
| `891` | `accept_saved_capture` (`load_current`, inside `890`) | `14.552709` | `10.134935` | `4.417775` | `0.583192` | `1.124305` | `1.707497` | `19.233906` | `return` |

### 2.4 Where the `243.40s` of Launch CPU Actually Goes (`[derived]` Disjoint Attribution)

Because unmonitored-self `thread_cpu` is disjoint across all `665` call rows in `launch` (`sum = 243.397365s`, matching `public_launch` `243.397365s` and phase `thread_cpu` `243.398140s` to `0.000775s`), we can partition the entire `243.40s` `launch` CPU without double-counting (`[derived]`):

1. **`controller_prewarm` (`prewarm_before_acceptance`, `1` call, row `863`)**:
   - **Inclusive**: `64.187670s` thread CPU (`58.972226s` user, `5.215436s` system; `72.393237s` wall).
   - **Unmonitored-self**: **`56.764656s`** (`23.32%` of total `launch` CPU) inside `prewarm_before_acceptance` outside its monitored children (`execution_registration_verified` `7.213155s`, `selection_capture` `0.154184s`, `selection_rebuild` `0.054820s`, `synthetic_peer_fingerprint` `0.000855s`).
2. **Registration & Preparer Verification Family (`shared_registration_verified`, `execution_registration_verified`, `preparer_verified`)**:
   - **Unmonitored-self across these three verification layers**:
     - `execution_registration_verified` (`14` calls): **`53.939775s`** (`22.16%` of `launch` CPU)
     - `preparer_verified` (`21` calls): **`52.664646s`** (`21.64%` of `launch` CPU)
     - `shared_registration_verified` (`9` calls): **`28.604915s`** (`11.75%` of `launch` CPU)
     - **Subtotal (unmonitored-self in the 3 verification functions alone)**: **`135.209336s`** (`55.55%` of `launch` CPU), **before** counting their `selection_capture` / `selection_rebuild` / `schema_*` children!
   - **Inclusive**: The `9` calls to `shared_registration_verified` alone have an inclusive `thread_cpu` sum of **`108.372327s`** (`130.140890s` wall) — `1` in `public_launch` (`23.627346s`, which includes a cold `schema_reconstruction` of `10.962201s`), `1` in `engine_entry` (`9.774378s`), `1` inside `accept_saved_capture` (`10.500568s`), and `6` directly inside `launch_engine` (`64.470035s`: `3` before `accept_saved_capture` and `3` after `accept_saved_capture`).
3. **Selection & Schema Rebuild/Capture Family (`selection_capture`, `selection_rebuild`, `schema_cache_lookup`, `schema_reconstruction`, `schema_capture`)**:
   - **Unmonitored-self across these five labels**:
     - `schema_capture` (`6` calls): **`10.752329s`**
     - `schema_reconstruction` (`3` calls): **`8.429480s`**
     - `schema_cache_lookup` (`89` calls): **`2.870103s`**
     - `selection_capture` (`88` calls): **`1.857621s`**
     - `selection_rebuild` (`91` calls): **`0.399112s`**
     - **Subtotal (unmonitored-self in selection/schema functions)**: **`24.308645s`** (`9.99%` of `launch` CPU).
4. **Top-Level Orchestration & Admission Unmonitored-Self (`launch_engine`, `accept_saved_capture`, `fresh_admission`, `engine_entry`, `public_launch`)**:
   - `launch_engine` (`_launch`, `1` call): **`20.421243s`** (`8.39%` of `launch` CPU) in unmonitored helpers called directly from `_launch` (such as `_recheck_authority`, `_unchanged`, `capture_admission_lease`, `inspect_current_selection`, etc.).
   - `accept_saved_capture` (`accept_current_selection` + `load_current`): **`4.005415s`** (`1.65%` of `launch` CPU) outside its single `shared_registration_verified` child (`10.500568s`).
   - `fresh_admission` (`admit`, `1` call): **`2.080373s`** (`0.85%` of `launch` CPU) outside its `2` `execution_registration_verified` (`11.734254s`) and `1` `preparer_verified` (`1.109413s`) children.
   - `engine_entry` + `public_launch`: **`0.400826s`** (`0.16%` of `launch` CPU).
5. **Fingerprints & Freshness Guards (`synthetic_peer_fingerprint`, `freshness_check`, `u4b_binary_fingerprint`, `freshness_before_dispatch`, `freshness_before_reservation`, `legacy_binary_fingerprint`)**:
   - **Subtotal**: **`0.206871s`** (`0.08%` of `launch` CPU).

---

## 3. `382f0dfd1ce8` Against `458887766eff`, Launch Phase

### 3.1 Why the Launch Row Count Rose from `537` to `665` (`+128` Rows)

- **[measured]** The fundamental fact revealed by the call records is that **`458887766eff` and `382f0dfd1ce8` did not terminate at the same point in `_launch` ([native_execution_orchestration.py](file:///Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/worktree-382f0dfd1ce8/src/data_sheets_schema/native_execution_orchestration.py#L334-L386))**:

```python
        selection = admission.inspect_current_selection(
            value,
            registration_raw,
            subscription,
            current_launch=True,
        )
        ...
        accepted = admission.accept_current_selection(
            value,
            registration_raw,
            subscription,
        )
        authorization = _join_subscription_authority(
            value,
            registration_raw,
            subscription,
            accepted,
            current_launch=True,
        )
        _unchanged(value, registration_raw, authorization)
        with capture_admission_lease(
            value,
            registration_raw,
            subscription,
            authorization,
        ) as lease:
            launch_guard = v2.SubscriptionGuard(
                subscription,
                authorization,
                lease,
            )
            launch_guard.before_reservation()
```

- **[measured]** **On `458887766eff` (`537` launch rows, `rows 457..994`)**:
  - `accept_current_selection` (row `904`, wrapping `load_current` row `905`) entered at `04:46:44.453103+00:00` and called `freshness_before_dispatch` (row `992`) -> `freshness_check` (`_fresh`, row `993`) at `04:47:16.661465+00:00`.
  - At that moment, capture age (`captured_at = 04:41:41.803810Z`) was **`334.857655s > 300.0s`** (`max_age_seconds = 300`).
  - `_fresh` raised `ValueError("subscription observation is stale or future-dated")` **inside `accept_current_selection`** (`_launch` line `366`)!
  - Therefore, `458887766eff` (and `3cc113e2606c` at `318.890236s`) **never exited `accept_current_selection`** and never executed lines `369-385` of `_launch`.
- **[measured]** **On `382f0dfd1ce8` (`665` launch rows, `rows 457..1122`)**:
  - PR #5835 (`382f0dfd1ce8`) replaced the second `registration.verified(registration_raw)` (`shared_registration_verified`) call inside `read_capture_for_event` ([native_subscription_capture.py](file:///Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/worktree-382f0dfd1ce8/src/data_sheets_schema/native_subscription_capture.py#L673-L742)) with `_read_capture_with_authority` -> `_recheck_authority` -> `registration._recheck_verified`:

```python
    authority = registration.verified(registration_raw)
    first = _read_capture_with_authority(
        value,
        registration_raw,
        subscription,
        authority,
        current=current,
    )
    second = _read_capture_with_authority(
        value,
        registration_raw,
        subscription,
        _recheck_authority(registration_raw, authority),
        current=current,
    )
```

  - **[measured]** That change had two direct effects before and during `accept_current_selection` (**Stage A**, from `launch` start through the exit of `accept_current_selection`):
    1. In `fixture` (after `capture_timestamp` is stamped inside the first pass of `capture_current_subscription`), the second verification pass of `capture_current_subscription` also uses `_recheck_authority`, cutting the time from `capture_timestamp` to `launch` start from **`23.950053s`** (`458887766eff`) to **`10.802291s`** (`382f0dfd1ce8`, **`-13.147762s`**).
    2. In **Stage A** of `launch` (`rows 457..966`), both `inspect_current_selection` (`_launch` line `334`) and `accept_current_selection` (`_launch` line `366`) call `read_capture_for_event`. Each call eliminated `1` `shared_registration_verified` subtree (`-2` `shared_registration_verified`, `-2` `execution_registration_verified`, `-2` `preparer_verified`, `-6` `selection_capture` / `selection_rebuild` / `schema_cache_lookup`, `-4` `synthetic_peer_fingerprint` = **`-28` rows**). Stage A row count fell from **`537` rows** (`458887766eff`) to **`509` rows** (`382f0dfd1ce8`).
    3. Specifically, `accept_current_selection` (row `890` on `382f` vs row `904` on `4588`) dropped from **`23.581882s` process CPU / `32.216250s` wall** (`458887766eff`) to **`14.553747s` process CPU / `19.235290s` wall** (`382f0dfd1ce8`) — a reduction of **`-9.028135s` process CPU (`-38.28%`)** and **`-12.980959s` wall (`-40.29%`)**.
    4. As a result, when `accept_current_selection` on `382f0dfd1ce8` reached `freshness_before_dispatch` (row `964`) -> `freshness_check` (row `965`) at `16:44:51.834767+00:00`, the capture age was **`259.396095s <= 300.0s`**, so **`accept_current_selection` SUCCEEDED (`outcome: "return"`, `guard_accepted_at: "2026-11-11T16:44:51.840625+00:00"`)** after **`248.598090s`** of `launch` wall time!
  - **[measured]** Because `accept_current_selection` returned normally on `382f0dfd1ce8`, execution entered **Stage B** (`_launch` lines `369-385`, `rows 966..1122`, **`156` new rows** that `458887766eff` never reached):
    - `_join_subscription_authority` (`_launch` line `369`): calls `context(..., current=True)` -> `read_capture_for_event` (executing `shared_registration_verified` row `972`, `11.519216s` CPU / `14.387324s` wall, plus `_recheck_authority`, plus `freshness_before_dispatch` row `1044` / `freshness_check` row `1045`, which **also passed** at capture age **`279.556707s <= 300.0s`**), and then constructs `v2.SubscriptionGuard(...)` (executing `shared_registration_verified` row `1046`, `11.370907s` CPU / `13.312553s` wall).
    - `_unchanged(value, registration_raw, authorization)` (`_launch` line `375`).
    - `with capture_admission_lease(...)` (`_launch` line `376`): calls `_current_authority` -> `_authority` -> `shared_registration_verified` (row `1080`, `9.980186s` CPU / `11.972933s` wall).
    - `launch_guard.before_reservation()` (`_launch` line `385`, row `1120`) -> `self._fresh(self._pre_reservation_margin_seconds)` (row `1121`) at `16:45:38.972431+00:00`: capture age is now **`306.533759s > 300.0s`** (`96.533759s` over the `210.0s` pre-reservation target, and `6.533759s` over the `300.0s` hard `max_age` limit), which raises `ValueError("subscription observation is stale or future-dated")`.
- **[derived]** Exact row-count accounting between `458887766eff` and `382f0dfd1ce8`:
  - Stage A (`launch` start through exit of `accept_current_selection`): `537 - 28 = 509` rows (`-28` rows from PR #5835).
  - Stage B (post-acceptance `_launch` lines `369-385`, reached only on `382f0dfd1ce8`): `+156` rows.
  - Total `launch` rows on `382f0dfd1ce8`: `509 + 156 = 665` rows (`+128` net rows over `458887766eff`).

### 3.2 Function-by-Function Side-by-Side Comparison (`458887766eff` vs `382f0dfd1ce8`, Launch Phase)

- **[measured]** / **[derived]** Side-by-side comparison of all `16` monitored labels in `launch`, showing total counts, Stage A vs Stage B counts on `382f0dfd1ce8`, inclusive `thread_cpu` sums, inclusive `thread_cpu` means per call, and unmonitored-self `thread_cpu` sums (inclusive times are **not** summed across functions):

| Label | `4588` Count (All Stage A) | `382f` Stage A Count (`[derived]`) | `382f` Stage B Count (`[derived]`) | `382f` Total Count (`Δ` vs `4588`) | `4588` Inclusive `thread_cpu` Sum s | `382f` Inclusive `thread_cpu` Sum s (`Δ` s) | `4588` Mean CPU / Call s | `382f` Mean CPU / Call s (`Δ` %) | `4588` Unmonitored-Self CPU s (`[derived]`) | `382f` Unmonitored-Self CPU s (`Δ` s, `[derived]`) | Status & Structural Attribution |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `public_launch` | `1` | `1` | `0` | `1` (`0`) | `237.956837` | `243.397365` (`+5.440528`) | `237.956837` | `243.397365` (`+2.29%`) | `0.214019` | `0.161396` (`-0.052623`) | Dearer inclusive (`+5.44s`) because `382f` ran Stage B (`+47.15s` wall / `~38.6s` CPU); Stage A was `~33.2s` CPU cheaper |
| `engine_entry` | `1` | `1` | `0` | `1` (`0`) | `211.819736` | `219.599567` (`+7.779830`) | `211.819736` | `219.599567` (`+3.67%`) | `0.335756` | `0.239430` (`-0.096327`) | Same as `public_launch`: includes Stage B on `382f` |
| `launch_engine` | `1` | `1` | `0` | `1` (`0`) | `201.270961` | `209.585050` (`+8.314089`) | `201.270961` | `209.585050` (`+4.13%`) | `10.175743` | `20.421243` (`+10.245500`) | Unmonitored-self rose `+10.25s` because `382f` executed `3` unmonitored `_recheck_authority` calls (`~4.5s` CPU each in Stage A+B) + `_unchanged` + `capture_admission_lease` in Stage B |
| `shared_registration_verified` | `8` | `6` | `3` | `9` (`+1`) | `94.756840` | `108.372327` (`+13.615487`) | `11.844605` | `12.041370` (`+1.66%`) | `23.952242` | `28.604915` (`+4.652673`) | `-2` calls in Stage A (PR #5835), `+3` calls in Stage B (`+1` net call); per-call mean unchanged (`+1.66%`) |
| `execution_registration_verified` | `13` | `11` | `3` | `14` (`+1`) | `102.931797` | `113.838536` (`+10.906739`) | `7.917831` | `8.131324` (`+2.70%`) | `46.517739` | `53.939775` (`+7.422036`) | `-2` calls in Stage A, `+3` calls in Stage B (`+1` net call); per-call mean `+2.70%` |
| `preparer_verified` | `20` | `18` | `3` | `21` (`+1`) | `64.084699` | `66.579529` (`+2.494831`) | `3.204235` | `3.170454` (`-1.05%`) | `49.286957` | `52.664646` (`+3.377689`) | `-2` calls in Stage A, `+3` calls in Stage B (`+1` net call); per-call mean `-1.05%` |
| `controller_prewarm` | `1` | `1` | `0` | `1` (`0`) | `78.591930` | `64.187670` (`-14.404260`) | `78.591930` | `64.187670` (`-18.33%`) | `71.630381` | `56.764656` (`-14.865725`) | **Cheaper** by `-14.40s` CPU (`-18.33%`) and `-31.68s` wall (`104.08s -> 72.39s`); identical bytecode (`58d123c4…`), so difference is run-to-run / contention sensitivity |
| `accept_saved_capture` (outer row) | `1` (`2` raw) | `1` (`2` raw) | `0` | `1` (`2` raw, `0` Δ) | `23.581882` (`47.162499` raw) | `14.553751` (`29.106464` raw; **`-9.028131` outer**) | `23.581249` | `14.553232` (**`-38.28%`**) | `4.199567` | `4.005415` (`-0.194152`) | **Cheaper** by **`-9.03s` process CPU (`-38.28%`)** and **`-12.98s` wall (`-40.29%`)** due to PR #5835 removing 1 `shared_registration_verified` subtree (`~9.5s` CPU) inside `load_current` |
| `selection_rebuild` | `84` | `78` | `13` | `91` (`+7`) | `24.160498` | `22.451025` (`-1.709474`) | `0.287625` | `0.246715` (`-14.22%`) | `0.369478` | `0.399112` (`+0.029634`) | `-6` calls in Stage A, `+13` calls in Stage B (`+7` net); cheaper inclusive sum because cold `schema_reconstruction` under `selection_rebuild` was faster on `382f` |
| `schema_reconstruction` | `3` | `3` | `0` | `3` (`0`) | `20.996420` | `19.181809` (`-1.814611`) | `6.998807` | `6.393936` (`-8.64%`) | `9.299156` | `8.429480` (`-0.869676`) | Cheaper by `-1.81s` (`-8.64%`), all in Stage A (`0` calls in Stage B because schemas are cached) |
| `selection_capture` | `81` | `75` | `13` | `88` (`+7`) | `17.503044` | `16.025877` (`-1.477167`) | `0.216087` | `0.182112` (`-15.72%`) | `1.884221` | `1.857621` (`-0.026601`) | `-6` calls in Stage A, `+13` calls in Stage B (`+7` net) |
| `schema_cache_lookup` | `82` | `76` | `13` | `89` (`+7`) | `15.320497` | `13.832304` (`-1.488193`) | `0.186835` | `0.155419` (`-16.81%`) | `2.626373` | `2.870103` (`+0.243731`) | `-6` calls in Stage A, `+13` calls in Stage B (`+7` net) |
| `fresh_admission` | `1` | `1` | `0` | `1` (`0`) | `14.576187` | `14.925277` (`+0.349090`) | `14.576187` | `14.925277` (`+2.39%`) | `2.142423` | `2.080373` (`-0.062051`) | Within run-to-run variation (`+2.39%`) |
| `schema_capture` | `6` | `6` | `0` | `6` (`0`) | `11.697265` | `10.752329` (`-0.944936`) | `1.949544` | `1.792055` (`-8.08%`) | `11.697265` | `10.752329` (`-0.944936`) | Cheaper by `-0.94s` (`-8.08%`), all in Stage A |
| `synthetic_peer_fingerprint` | `205` | `201` | `91` | `292` (`+87`) | `0.138176` | `0.172770` (`+0.034593`) | `0.000674` | `0.000592` (`-12.22%`) | `0.138176` | `0.172770` (`+0.034593`) | `-4` calls in Stage A, `+91` calls in Stage B (`+87` net) |
| `freshness_check` | `2` | `2` | `2` | `4` (`+2`) | `0.012027` | `0.024341` (`+0.012314`) | `0.006013` | `0.006085` (`+1.20%`) | `0.012027` | `0.024341` (`+0.012314`) | `+2` calls in Stage B (`_join_subscription_authority` + `before_reservation`) |
| `freshness_before_dispatch` | `2` | `2` | `1` | `3` (`+1`) | `0.012196` | `0.018157` (`+0.005960`) | `0.006098` | `0.006052` (`-0.75%`) | `0.000170` | `0.000267` (`+0.000098`) | `+1` call in Stage B (`_join_subscription_authority`) |
| `u4b_binary_fingerprint` | `23` | `23` | `13` | `36` (`+13`) | `0.006262` | `0.008962` (`+0.002699`) | `0.000272` | `0.000249` (`-8.57%`) | `0.006262` | `0.008962` (`+0.002699`) | `0` Δ in Stage A, `+13` calls in Stage B |
| `freshness_before_reservation` | **`0`** | `0` | `1` | **`1` (`+1`, NEW)** | `0.000000` | `0.006523` (`+0.006523`) | `—` | `0.006523` | `0.000000` | `0.000071` (`+0.000071`) | **New in `382f` launch**: `launch_guard.before_reservation()` at `_launch` line `385`, never reached by `458887766eff` or `3cc113e2606c` |
| `legacy_binary_fingerprint` | `1` | `1` | `0` | `1` (`0`) | `0.000516` | `0.000460` (`-0.000056`) | `0.000516` | `0.000460` (`-10.92%`) | `0.000516` | `0.000460` (`-0.000056`) | Unchanged (`1` call) |

- **[measured]** **Which functions are new or gone in `launch`**:
  - **New**: `freshness_before_reservation` (`before_reservation` at `native_subscription_guard_v2.py:439`, row `1120`) appears in `launch` for the first time (`0 -> 1` call) because `382f0dfd1ce8` is the first run among the three to pass `accept_current_selection` and reach `launch_guard.before_reservation()` at `_launch` line `385`.
  - **Gone**: None (`0` labels disappeared).
- **[measured]** **Bytecode identity check (`registered_code_objects`)**:
  - All `15` labels shared between `458887766eff` and `382f0dfd1ce8` in `launch` have **identical `bytecode_sha256` hashes** across both runs (`bytecode_changed_4588_to_382f == false` for all `15` labels; see `registered_code_objects_comparison` in `result-analysis.json`). The functions modified in PR #5835 (`read_capture_for_event`, `_read_capture_with_authority`, `_recheck_authority`, ` registration._recheck_verified`) are unmonitored callers/helpers between `accept_saved_capture` / `launch_engine` and `shared_registration_verified`.

### 3.3 Separating User CPU from System CPU (`46.59s -> 59.79s` System, `191.36s -> 183.61s` User)

- **[measured]** From `coarse_elapsed` on the `5` coarse-instrumented wrappers in `launch`, we can partition `self_user_cpu`, `self_system_cpu`, and `reaped_child` CPU across the major sub-scopes of `launch` on `458887766eff` vs `382f0dfd1ce8`:

| Launch Sub-Scope | `4588` `self_user_cpu` s | `382f` `self_user_cpu` s (`Δ` s) | `4588` `self_system_cpu` s | `382f` `self_system_cpu` s (`Δ` s) | `4588` `reaped_child_total` s | `382f` `reaped_child_total` s (`Δ` s) | `4588` `process_cpu` s | `382f` `process_cpu` s (`Δ` s) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **Total `launch` phase** (`phases[1].elapsed`) | `191.363264` | `183.609124` (`-7.754140`) | `46.594797` | `59.789019` (`+13.194222`) | `13.911106` (`5.03u + 8.88s`) | `17.308275` (`5.83u + 11.47s`, `+3.397169`) | `237.958053` | `243.398143` (`+5.440090`) |
| 1. `public_launch` outside `engine_entry` (`[derived]`) | `22.842750` | `19.521239` (`-3.321511`) | `3.294351` | `4.276552` (`+0.982201`) | `1.100844` | `1.538193` (`+0.437349`) | `26.137104` | `23.797791` (`-2.339313`) |
| 2. `engine_entry` outside `launch_engine` (`[derived]`) | `8.741321` | `7.479708` (`-1.261613`) | `1.807468` | `2.534808` (`+0.727340`) | `0.730438` | `0.995403` (`+0.264965`) | `10.548790` | `10.014516` (`-0.534274`) |
| 3. `controller_prewarm` (inside `launch_engine`, `[measured]`) | `73.702447` | `58.972226` (`-14.730221`) | `4.889480` | `5.215436` (`+0.325956`) | `0.556707` | `0.628181` (`+0.071474`) | `78.591926` | `64.187662` (`-14.404264`) |
| 4. `accept_saved_capture` (outer row, inside `launch_engine`, `[measured]`) | `18.310003` | `10.135772` (`-8.174231`) | `5.271879` | `4.417976` (`-0.853903`) | `2.190594` | `1.707497` (`-0.483097`) | `23.581882` | `14.553747` (`-9.028135`) |
| 5. Rest of `launch_engine` (`_launch` outside `controller_prewarm` & `accept_saved_capture`, `[derived]`) | `67.765867` | `87.499560` (`+19.733693`) | `31.331266` | `43.344076` (`+12.012810`) | `9.332523` | `12.439001` (`+3.106478`) | `99.097129` | `130.843637` (`+31.746508`) |

- **[derived]** **What the records CAN attribute the User/System CPU shift to**:
  1. **Why `self_user_cpu` fell by `-7.754140s` (`191.363264s -> 183.609124s`)**:
     - `accept_saved_capture` (`accept_current_selection`) user CPU fell by **`-8.174231s`** (`18.310003s -> 10.135772s`, directly attributable to PR #5835 skipping one `shared_registration_verified` subtree in `read_capture_for_event`), and `controller_prewarm` user CPU fell by **`-14.730221s`** (`73.702447s -> 58.972226s`), plus `-4.583124s` in `public_launch`/`engine_entry` pre-`_launch`.
     - Those **`-27.487576s`** of Stage A user-CPU reductions were partially offset by **`+19.733693s`** of net user CPU in the rest of `launch_engine` because `382f0dfd1ce8` ran **Stage B** (`rows 966..1122`, `3` additional `shared_registration_verified` subtrees + `_recheck_authority` + `_unchanged` + `capture_admission_lease`, costing `~38.6s` of total Stage B thread CPU after subtracting Stage A's `inspect_current_selection` savings).
  2. **Why `self_system_cpu` rose by `+13.194222s` (`46.594797s -> 59.789019s`) and `reaped_child_total_cpu` rose by `+3.397169s` (`13.911106s -> 17.308275s`)**:
     - **`+12.012810s` (`91.0%`) of the `+13.194222s` `self_system_cpu` increase** and **`+3.106478s` (`91.4%`) of the `+3.397169s` `reaped_child_total_cpu` increase** occurred inside **"Rest of `launch_engine`"** (`31.331266s -> 43.344076s` system CPU; `9.332523s -> 12.439001s` reaped child CPU).
     - Notice that **"Rest of `launch_engine`"** has a much higher system-to-user CPU ratio (`31.6%` system on `4588`, `33.1%` system on `382f`) than `controller_prewarm` (`6.2%` system on `4588`, `8.1%` system on `382f`), and generates `~70%` of all reaped child CPU (`9.33s` of `13.91s` on `4588`; `12.44s` of `17.31s` on `382f`) and `sys.audit` events (`audit_events` rose from `12,504,807` on `458887766eff` to `13,335,145` on `382f0dfd1ce8`, **`+830,338` audit events**, `+6.64%`).
     - Because `382f0dfd1ce8` executed **Stage B** (`_launch` lines `369-385`, which runs `3` full `shared_registration_verified` subtrees, `1` `_recheck_authority`, `_unchanged`, and `capture_admission_lease`), it executed more subprocess/file/registration operations in `launch_engine` than `458887766eff` (which aborted at line `366`).
- **[measured]** **What the records CANNOT attribute**:
  - Individual call rows in `calls` record only `inclusive_thread_cpu` and `inclusive_wall`; only the `5` coarse-instrumented labels (`public_launch`, `engine_entry`, `launch_engine`, `controller_prewarm`, `accept_saved_capture`) record `coarse_elapsed` (`self_user_cpu`, `self_system_cpu`, `reaped_child_*`).
  - Therefore, inside "Rest of `launch_engine`", the JSON records **cannot** split `self_system_cpu` (`43.344076s`) or `reaped_child_total_cpu` (`12.439001s`) between Stage A (`inspect_current_selection`, `fresh_admission`, and the first `3` `shared_registration_verified` calls) and Stage B (`_join_subscription_authority`, `_unchanged`, `capture_admission_lease`), nor between individual `shared_registration_verified` vs `_recheck_authority` calls.
- **[inference]** **What is structural vs within contended run-to-run variation vs no basis to tell (`1` contended sample each)**:
  - **Structurally established (not run-to-run noise)**:
    1. The removal of `1` `shared_registration_verified` subtree per `read_capture_for_event` call on `382f0dfd1ce8` (`-1` in `fixture` post-capture, `-1` in `inspect_current_selection`, `-1` in `accept_current_selection`, `-1` in `_join_subscription_authority`), reducing Stage A row count from `537` to `509` (`-28` rows) and reducing `accept_current_selection` CPU by `-9.03s` (`-38.3%`) and post-capture `fixture` tail by `-13.15s`.
    2. The progression of `382f0dfd1ce8` past `accept_current_selection` (`259.40s <= 300.0s`) and past `_join_subscription_authority` (`279.56s <= 300.0s`) to `launch_guard.before_reservation()` (`306.53s > 300.0s`), adding `156` Stage B rows (`~38.6s` thread CPU, `47.15s` wall) and increasing `audit_events` by `+830,338`.
  - **Within contended run-to-run variation**:
    - Per-call CPU of unchanged code objects (`shared_registration_verified` mean `11.84s` vs `12.04s`, `+1.66%`; `execution_registration_verified` mean `7.92s` vs `8.13s`, `+2.70%`; `preparer_verified` mean `3.20s` vs `3.17s`, `-1.05%`; `fresh_admission` `14.58s` vs `14.93s`, `+2.39%`).
  - **No basis to tell from a single contended sample each**:
    - How much of the `-14.40s` CPU decrease in `controller_prewarm` (`78.59s -> 64.19s`, identical bytecode `58d123c4…`) or how much of the remaining system-CPU variance in `public_launch`/`engine_entry` (`+0.98s` / `+0.73s`) is host-scheduler/cache contention noise under load `2.74-2.87` per CPU.

---

## 4. The Freshness Arithmetic

### 4.1 Guard Rule in `native_subscription_guard_v2.py`

From [native_subscription_guard_v2.py](file:///Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/worktree-382f0dfd1ce8/src/data_sheets_schema/native_subscription_guard_v2.py#L419-L456) (`[measured]`):

```python
    def _fresh(self, margin_seconds: int = 0) -> None:
        now = int(time.time())
        captured_at = int(self._subscription["captured_at"])
        max_age = int(self._subscription["max_age_seconds"])
        if captured_at > now or now - captured_at > max_age - margin_seconds:
            raise ValueError("subscription observation is stale or future-dated")
```

```python
    def before_reservation(self) -> None:
        self._Verify()
        self._fresh(self._pre_reservation_margin_seconds)
        self._state = "ready_for_reservation"

    def before_dispatch(self) -> None:
        self._Verify()
        if self._state not in ("created", "ready_for_reservation"):
            raise RuntimeError("guard must be verified before dispatch")
        self._fresh(0)
```

- **[measured]** In all three runs, `max_age_seconds = 300` and `pre_reservation_margin_seconds = 90`:
  - `before_dispatch()` calls `self._fresh(0)` -> requires `now - captured_at <= 300` seconds.
  - `before_reservation()` calls `self._fresh(90)` -> requires `now - captured_at <= 300 - 90 = 210` seconds.

### 4.2 Exact Timestamps, Intervals, and Freshness Check Progression Across All Three Runs

- **[measured]** / **[derived]** From `phase-metrics/*-diagnostic.json` and `phase-metrics/*-measurement.json`:

| Metric / Interval | `3cc113e2606c` (`PID 64652`) | `458887766eff` (`PID 34474`) | `382f0dfd1ce8` (`PID 67941`) |
|---|---:|---:|---:|
| `fixture` `before.utc` (`[measured]`) | `2026-11-11T03:26:49.853876+00:00` | `2026-11-11T04:39:02.714713+00:00` | `2026-11-11T16:38:24.396857+00:00` |
| `capture_timestamp` (`diagnostic.json`, `[measured]`) | `2026-11-11T03:29:14.415406Z` | `2026-11-11T04:41:41.803810Z` | `2026-11-11T16:40:32.438672Z` |
| `fixture` `after.utc` (`[measured]`) | `2026-11-11T03:29:30.849629+00:00` | `2026-11-11T04:42:05.752990+00:00` | `2026-11-11T16:40:43.240674+00:00` |
| `launch` `before.utc` (`[measured]`) | `2026-11-11T03:29:30.849894+00:00` | `2026-11-11T04:42:05.753863+00:00` | `2026-11-11T16:40:43.240963+00:00` |
| **Time from capture to start of `launch` phase** (`[derived]`) | **`16.434488s`** | **`23.950053s`** | **`10.802291s`** |
| Remaining `210.0s` budget at `launch` start (`210 - capture_to_launch_start`, `[derived]`) | `193.565512s` | `186.049947s` | **`199.197709s`** |
| Remaining `300.0s` budget at `launch` start (`300 - capture_to_launch_start`, `[derived]`) | `283.565512s` | `276.049947s` | **`289.197709s`** |
| Launch Check #1 (`public_launch` `before_dispatch` -> `_fresh(0)`) age at entry (`[derived]`) | *(not called on `3cc`)* | `71.055234s <= 300s` (`return`, row `503`) | **`38.526354s <= 300s`** (`return`, row `503`) |
| Launch Check #2 (`accept_saved_capture` `before_dispatch` -> `_fresh(0)`) age at entry (`[derived]`) | **`318.890236s > 300s`** (**`ValueError`**, row `1012`) | **`334.857655s > 300s`** (**`ValueError`**, row `993`) | **`259.396095s <= 300s`** (**`return`**, row `965`) |
| Launch Check #3 (`_join_subscription_authority` `before_dispatch` -> `_fresh(0)`) age at entry (`[derived]`) | *(never reached)* | *(never reached)* | **`279.556707s <= 300s`** (**`return`**, row `1045`) |
| Launch Check #4 (`launch_guard.before_reservation` -> `_fresh(90)`) age at entry (`[derived]`) | *(never reached)* | *(never reached)* | **`306.533759s > 210s` (and `> 300s`)** (**`ValueError`**, row `1121`) |
| Failing `_fresh` `entered_utc` (`[measured]`) | `2026-11-11T03:34:33.305642+00:00` | `2026-11-11T04:47:16.661465+00:00` | `2026-11-11T16:45:38.972431+00:00` |
| Failing `_fresh` `left_utc` (`[measured]`) | `2026-11-11T03:34:33.311038+00:00` | `2026-11-11T04:47:16.668925+00:00` | `2026-11-11T16:45:38.979091+00:00` |
| `launch` `after.utc` (`[measured]`) | `2026-11-11T03:34:33.312814+00:00` | `2026-11-11T04:47:16.673591+00:00` | `2026-11-11T16:45:38.983227+00:00` |
| `diagnostic.json` `observed_at` (`[measured]`) | `2026-11-11T03:34:33.317318+00:00` | `2026-11-11T04:47:16.678355+00:00` | `2026-11-11T16:45:38.987869+00:00` |
| **Time from capture to refusal (`_fresh` entry / exit / `launch` end / `observed_at`)** (`[derived]`) | `318.890236s` / `318.895632s` / `318.897408s` / `318.901912s` | `334.857655s` / `334.865115s` / `334.869781s` / `334.874545s` | **`306.533759s` / `306.540419s` / `306.544555s` / `306.549197s`** |

### 4.3 How Much Launch-Phase Time Must Go on `382f0dfd1ce8` for a Reservation Boundary Inside `210s` of Capture

Under the unchanged `300.0s` `max_age_seconds` limit and `90.0s` `pre_reservation_margin_seconds` (`effective_freshness_target_seconds = 210.0s`):

1. **[derived]** **Time already consumed before `launch` starts**:
   - Capture (`16:40:32.438672Z`) to `launch` start (`16:40:43.240963+00:00`) is **`10.802291s`**.
   - With `10.802291s` post-capture fixture time unchanged, the **maximum allowable `launch` wall time** to reach `launch_guard.before_reservation()` inside `210.0s` of capture is:
     $$210.0\text{ s} - 10.802291\text{ s} = \mathbf{199.197709\text{ s}}$$
2. **[derived]** **Launch-phase wall-time reduction required on this run (`295.745893s` launch wall)**:
   - At `launch_guard.before_reservation()` -> `_fresh(90)` entry (row `1121`, `295.735097s` into `launch`, `306.533759s` after capture):
     $$306.533759\text{ s} - 210.0\text{ s} = \mathbf{96.533759\text{ s}}\text{ of wall time must go }(\mathbf{96.537388\text{ s}}\text{ monotonic})$$
   - At `launch` phase end (`295.745893s` monotonic, `306.544555s` UTC after capture) / `diagnostic.json` `observed_at` (`306.549197s` after capture):
     $$\mathbf{96.548184\text{ s}}\text{ (monotonic) / }\mathbf{96.549197\text{ s}}\text{ (at }\texttt{observed\_at}\text{) must go }(\mathbf{-32.65\%}\text{ of }\texttt{launch}\text{ wall time})$$
3. **[derived]** **Minimum launch-phase CPU reduction required even on an ideal zero-contention host (`1.0` CPU second per `1.0` wall second)**:
   - Even if host contention were zero and wall time equalled CPU time (`199.197709s` remaining budget at `launch` start):
     - Against `launch` `process_cpu` alone (`243.398143s`): at least **`44.200434s` (`-18.16%`)** of `launch` `process_cpu` must be removed (`33.398143s` even if post-capture fixture time were `0s`).
     - Against `launch` `self + reaped_child` CPU (`260.706418s`): at least **`61.508709s` (`-23.59%`)** of `launch` total (`self + reaped_child`) CPU must be removed (`50.706418s` even if post-capture fixture time were `0s`).

---

## 5. What This Run Settles and What It Leaves Open (Addressing Section 7 Questions)

### 5.1 What This Run Settles

1. **Why the earlier `382f0dfd1ce8` run (`wp1-382f0dfd1ce8-cpu-monitoring-post-capture-ast-20261111`) hit the `891.09s` (`125`) driver cutoff**:
   - **[derived]** **Settled**: It was caused by extreme external host overload (`start_load = 44.16 / 10 = 4.42` per CPU, `max_one_minute_load_per_cpu = 5.51`, `mean_cpu_percent = 99.70%`), **not** by an infinite loop or a hang introduced by `382f0dfd1ce8`. On the completed rerun (`max_one_minute_load_per_cpu = 2.74`), `382f0dfd1ce8` completed cleanly (`returncode = 0`) in `434.59s` combined phase wall time (`452.40s` supervisor wall time, less than half of the `900s` limit).
2. **Whether `382f0dfd1ce8` (PR #5835) is a regression or an improvement over `458887766eff`**:
   - **[measured]** / **[derived]** **Settled**: `382f0dfd1ce8` is a **clear structural improvement**, not a regression:
     - `fixture` CPU fell from `119.921989s` to `110.880490s` (`-9.041499s`, `-7.54%`), and the post-capture `fixture` tail (`capture_timestamp` to `launch` start) fell from `23.950053s` to `10.802291s` (`-13.147762s`, `-54.90%`).
     - In `launch`, `accept_current_selection` (`accept_saved_capture`) CPU fell from `23.581882s` to `14.553747s` (`-9.028135s`, `-38.28%`), and Stage A row count fell from `537` to `509` (`-28` rows).
     - The only reason total `launch` `process_cpu` is `+5.440090s` higher (`243.398143s` vs `237.958053s`) and row count is `+128` higher (`665` vs `537`) is that **`382f0dfd1ce8` succeeded at `accept_current_selection` (`259.40s <= 300.0s`) and progressed `156` rows further (`Stage B`, `_launch` lines `369-385`, `~38.6s` thread CPU / `47.15s` wall)** all the way to `launch_guard.before_reservation()`, whereas `458887766eff` died inside `accept_current_selection` at line `366` (`334.86s > 300.0s`).
3. **Where a next reduction would have to come from to reach `before_reservation()` inside `210.0s`**:
   - **[derived]** **Settled**: Removing at least `44.20s` of `launch` `process_cpu` (`61.51s` of `self + reaped_child` CPU, and `96.53s` of contended wall time) cannot come from micro-optimizing small helpers (`synthetic_peer_fingerprint`, binary pins, or command-policy tokenization); it **must** come from the two dominant CPU sinks in `launch`:
     1. **Repeated full registration/preparer verification across `launch` (`9` `shared_registration_verified` calls = `108.37s` inclusive thread CPU; `14` `execution_registration_verified` calls = `113.84s` inclusive; `21` `preparer_verified` calls = `66.58s` inclusive; `135.21s` combined unmonitored-self CPU)**:
        - Even after PR #5835 (`382f0dfd1ce8`) replaced the second `registration.verified(registration_raw)` in `read_capture_for_event` with `_recheck_authority`, a single `synthetic_launch` still executes **`9` full `shared_registration_verified` (`registration.verified(registration_raw)`) calls** in `launch` (`1` in `public_launch`, `1` in `engine_entry`, `3` in `_launch` before acceptance, `1` in `accept_current_selection`, `2` in `_join_subscription_authority`, and `1` in `capture_admission_lease`), plus `2` direct `execution_registration_verified` calls in `_launch`, `2` in `fresh_admission`, and `1` in `controller_prewarm` — all re-verifying the same `registration_raw` payload (`~10-11.5s` CPU per warm `shared_registration_verified` call).
     2. **`controller_prewarm` (`prewarm_before_acceptance`, row `863`)**:
        - Spends **`64.187670s` inclusive thread CPU** (`56.764656s` unmonitored-self CPU inside `prewarm_before_acceptance` outside its `1` `execution_registration_verified` child of `7.213155s`) and **`72.393237s` wall time** in a single call at `_launch` line `360` right before `accept_current_selection`.

### 5.2 What This Run Leaves Open

1. **[measured]** **What happens inside the `56.764656s` unmonitored-self CPU of `controller_prewarm` (`prewarm_before_acceptance`, `native_shared_controller_orchestration.py:228`)**:
   - Because `cpu-monitoring` only instruments `execution_registration_verified`, `selection_capture`, `selection_rebuild`, and `synthetic_peer_fingerprint` inside `controller_prewarm` (`7.423014s` total), the remaining **`56.764656s` of thread CPU (`88.4%` of `controller_prewarm`)** is opaque in `67941-measurement.json`.
2. **[measured]** **What happens inside the `53.939775s` unmonitored-self CPU of `execution_registration_verified` and `52.664646s` unmonitored-self CPU of `preparer_verified`**:
   - Below `preparer_verified`, `cpu-monitoring` only instruments `selection_capture` (`13.886150s`) and `synthetic_peer_fingerprint` (`0.028733s`), leaving `106.604421s` of unmonitored-self CPU across `execution_registration_verified` + `preparer_verified` unattributed to specific inner helpers in `67941-measurement.json`, and does not distinguish which of the `9` `shared_registration_verified` calls in `launch` can share an already-verified authority via `_recheck_authority` (the pattern introduced by PR #5835 in `native_subscription_capture.py`).

### 5.3 Single Most Informative Next Step That Needs NO New Run

- **[inference]** **Static call-site & authority-reuse audit of the `9` `shared_registration_verified` calls in `launch` and of `prewarm_before_acceptance` (`native_shared_controller_orchestration.py:228`) against existing `cProfile` artifacts (zero runs required)**:
  1. **Source audit of the `9` `shared_registration_verified` call sites in `launch`**:
     - Trace all `9` `registration.verified(registration_raw)` calls in `launch` across `native_shared_execution_orchestration.py`, `native_execution_orchestration.py`, `native_subscription_admission.py`, `native_subscription_capture.py`, and `native_subscription_guard_v2.py` to determine which of the `8` subsequent calls after row `458` can legally accept an already-verified `authority` + `_recheck_authority(registration_raw, authority)` (the exact pattern PR #5835 used inside `read_capture_for_event`). Each warm `shared_registration_verified` call that is converted to `_recheck_authority` saves `~6.5-7.5s` of CPU (`~10.8s` minus `~3.5-4.0s`). Converting `6` to `7` of the `8` redundant `shared_registration_verified` calls in `launch` would save **`~40-50s` of `launch` CPU** and **`~50-65s` of wall time** on its own.
  2. **Cross-reference `prewarm_before_acceptance` (`native_shared_controller_orchestration.py:228`) and `verify_preparer` (`native_execution_registration_v2.py:375`) against the already-saved `call-calibration` `.pstats` files on disk** (e.g., under `scratch-native-u1u3/u3m/wp1-*-call-calibration-*`):
     - Because `bytecode_sha256` for both `prewarm_before_acceptance` (`58d123c4ad454eded8200055b1aac92263728bd33b2988d3c9f40a5dbb6f2483`) and `verify_preparer` (`7d6e2a1fc966a59233f3c06e21ba167d3ad0775325622b45cc10ab40f37facf2`) is **identical** across `3cc113e2606c`, `458887766eff`, and `382f0dfd1ce8`, reading the existing `.pstats` files and source code decomposes the `56.76s` unmonitored-self CPU of `controller_prewarm` and the `106.60s` unmonitored-self CPU of `execution_registration_verified` + `preparer_verified` with **zero new test executions**.

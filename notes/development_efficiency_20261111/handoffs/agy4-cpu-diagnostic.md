# E4 Handoff — Explicit Contended CPU Diagnostic (`a36c7174fb35c62a2499ee52918354e57a877d6a`)

- **Worktree**: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy-native-cpu-diagnostic-20261111` (isolated sparse checkout)
- **Branch / Commit**: `agy/native-cpu-diagnostic-20261111` at `a36c7174fb35c62a2499ee52918354e57a877d6a` (parent `38fbaf2ef985faf45a435d1a8c486cef4f1ca1bf`, base `3cc113e2606c563236d9c06098c5329ddd027a38` / `01bdcb22dad66da1a167595251b23e6352c97ab7`); accepted by Lead final review and published to `origin/agy/native-cpu-diagnostic-20261111` on Draft PR `#5841`
- **Scope**: 4 files frozen at `3cc113e2606c563236d9c06098c5329ddd027a38` plus 1 standalone read-only CLI helper (`scripts/adhoc/native_wp1_cpu_diagnostic_compare_20261110.py`, 283 lines at `a36c7174fb35c62a2499ee52918354e57a877d6a`); `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-native-u1u3`, `scripts/adhoc/native_wp1_qualification_20261110.py`, `scripts/adhoc/native_wp1_quiet_20261110.py`, and all production/protected files untouched.

## 1. Minimal Design & Postimage Hashes

| Relative Path | SHA-256 (`a36c7174fb35`) | Change Summary |
|---|---|---|
| `scripts/adhoc/native_wp1_cpu_diagnostic_compare_20261110.py` | `aa3551c5ab3988858b5a553042e2e35c349fa7934c52dfbb4618a3eb399259c7` (was `c18d435313cd4f46d1e0e08776ba734ca7302c984f6ac3576aa3077fefa1f4b2` at `38fbaf2ef985`) | New read-only CLI helper (`--legacy-out` / `--monitoring-out` / `--out`) that reads the recorded `.outer.json`, `.supervisor.json`, `wp1-harness.json`, and single `phase-metrics/<pid>-measurement.json` + `<pid>-diagnostic.json` (plus `outcome.json` when present) bounded by `handle.read(MAX_JSON_BYTES + 1)` (`#5842`), retains input `{path, bytes, sha256}` hashes, verifies unqualified classification, cleanup, and matching recorded `source_commit` / `manifest_sha256` / `interpreter`, delegates comparison to `native_wp1_validation_20261110.compare_cpu_diagnostic_arms`, and writes a new comparison JSON via `write_new`. |
| `scripts/adhoc/native_wp1_validation_20261110.py` | `f7426c2fd0560d5f8bf84935c083fcfe6908327213db1023af8607167eb88d07` | Frozen at `3cc113e2606c563236d9c06098c5329ddd027a38`. Adds fixed `cpu-legacy` and `cpu-monitoring` entries to `KINDS`, `QUALIFIED_KINDS`, `CPU_DIAGNOSTIC_KINDS`, and `NO_LEASE_KINDS`, plus `measurement_classification`, `require_accepted_measurement`, and `compare_cpu_diagnostic_arms` (`#5817`–`#5820`). |
| `scripts/adhoc/run_native_wp1_20261110.py` | `8124db6c15367e177f01590fb7742c89c5b912a8306a93b665610a1ecda4aa8d` | Frozen at `3cc113e2606c563236d9c06098c5329ddd027a38`. |
| `tests/test_native_u3k_profile.py` | `6ae66a0ec242df628c0540243ada579f2949520a174dae7174e06b7e39d8729c` | Frozen at `3cc113e2606c563236d9c06098c5329ddd027a38`. |
| `scripts/adhoc/native_wp1_quiet_fixture_20261110.py` | `cdf714f9f075a5e0e220526fdb7c3a67eda5f67f81d70b2468348de979b4b304` | Frozen at `3cc113e2606c563236d9c06098c5329ddd027a38`. |

## 2. Review Findings Incorporated (`#5817`–`#5820`)

- **`#5817` (Completed-prefix comparability & `cpu_policy` wording)**: `compare_cpu_diagnostic_arms` scopes `diagnostic_outcome_differs` to the `launch` phase and aggregate `equal_completed_work` / `total_explicit_phase_cpu`, retaining `comparable: True` and `relative_cpu` on an identical completed `fixture` prefix when `launch` diverges, and `cpu_policy` explicitly states that divergent aggregate or later-phase work suppresses those ratios while identical completed phase prefixes remain comparable.
- **`#5818` (Qualification and acceptance grounding)**: `measurement_classification(kind, *, qualification=None, certified=False, final_owner=False)` never sets `host_qualified`, `wall_time_freshness_qualified`, or `accepted_quiet_host_timing` from `kind` alone; `cpu-legacy` and `cpu-monitoring` are unconditionally `False`; intermediate records (`wp1-quiet-lease.json`, `wp1-harness.json`, `.outer.json`, `diagnostic.json`) never set acceptance booleans `True`; `require_accepted_measurement` unconditionally requires a present `qualification` dict with `qualification_passed: True` and `cleanup_verified: True`.
- **`#5819` (Well-formed pair identity & `wp1-harness.json` interpreter)**: `_valid_arm_identity` requires 64-hex `manifest_sha256`, 40-hex `source_commit`, and a closed `interpreter` dict (`{path, sha256, version}` from `harness['interpreter']` or `arm['interpreter']`), preventing `None == None` from passing `same_identity`. Removed per-label inclusive thread-CPU sums (`within_label_inclusive_thread_cpu`).
- **`#5820` (Producer terminal outcomes)**: `_terminal_phase_outcome` requires `'return'` or `'exception'`, and `_terminal_call_outcome` requires `'return'` or `'exception:<nonempty>'`, preventing missing or unknown outcomes on both arms from counting as closed or comparable.

## 3. Bounded Fixture Canary Witness (`wp1-quiet-fixture-e4-3cc113e2606c563236d9c06098c5329ddd027a38-canary`)

- **Command**: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python -I -S -B /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy-native-cpu-diagnostic-20261111/scripts/adhoc/native_wp1_quiet_fixture_20261110.py --source 3cc113e2606c563236d9c06098c5329ddd027a38 --out /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/wp1-quiet-fixture-e4-3cc113e2606c563236d9c06098c5329ddd027a38-canary`
- **Outcome**: `passed: true`, `cleanup_verified: true`, `bytecode_cache_created: false`, `source_unchanged: true`, `runtime_unchanged: true`, `sandbox_handoff.admitted: true`, `sandbox_handoff.observed_surviving_pids: []`, `sandbox_handoff.errors: []`, `elapsed_seconds: 1.4847322500136215` (within `30s` total / `25s` work cap).
- **Artifact SHA-256 Digests**:
  - `outcome.json` (`32234` bytes): `c74abc85156a18c2a1ef9a5a921eeb90d4440bdde93b7c3cef6ad32312489d93`
  - `manifest.json` (`1984` bytes): `861ba62eecacb1bda9f3dd168e603c79614205246af06e8689e10acc080c8fc8`
  - `sandbox.sb` (`613` bytes): `fbf093dfb546204673db0e8656d8f543302b02305e987b268b5d2ab1709adb24`

## 4. Deferred Interval Draft & Restored `38fbaf2ef985` Verification

- **Committed `38fbaf2ef985faf45a435d1a8c486cef4f1ca1bf` collector (`scripts/adhoc/native_wp1_cpu_diagnostic_compare_20261110.py`)**: `c18d435313cd4f46d1e0e08776ba734ca7302c984f6ac3576aa3077fefa1f4b2` (restored and verified; `git status --porcelain --untracked-files=no` is empty).
- **Deferred 2-line working-tree draft (`03:35:42` UTC)**: working-tree bytes had SHA-256 `61e0c869bf190dc84369a3f28c254fb8319263421bc98423bc80b97e2ac8c139` (describing only the uncommitted 2-line draft, not committed `38fbaf2ef985`). Preserved verbatim at `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy-native-cpu-diagnostic-20261111/tmp/deferred-controller-interval-20261111.patch` (`732` bytes, SHA-256 `dcdf4ec9f0bc714d5533cc0f87e1bc7deac0491b36d7bfbd9dc0e0bffd4d19cb`).

## 5. Stacked Draft PR & Matched-Pair Comparison Publication

- **Stacked Draft PR**: `https://github.com/bridge2ai/data-sheets-schema/pull/5841` (`#5841`, Draft)
- **Base / Head**: `codex/native-u1u3-combined-20261108` (`#5839`) <- `agy/native-cpu-diagnostic-20261111` at `38fbaf2ef985faf45a435d1a8c486cef4f1ca1bf` (parent `3cc113e2606c563236d9c06098c5329ddd027a38`)
- **Three-dot diff**: `scripts/adhoc/native_wp1_cpu_diagnostic_compare_20261110.py` only (`1 file changed, 282 insertions(+)`, `0 deletions(-)`)
- **Matched-pair comparison artifact**: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/wp1-cpu-comparison-3cc113e2606c-20261111.json` (SHA-256 `d6c3a077889039e81a62fde5e202e94786a1d4dd74f6d53e5fec8fba682d53b4`; `same_identity: true`, `arms_clean: true`, `equal_completed_work: true`, `same_diagnostic_outcome: true`, `measurement_class: "unqualified_contended_cpu_diagnostic"`, `host_qualified: false`, `wall_time_freshness_qualified: false`, `accepted_quiet_host_timing: false`)
- **CI Workflow Runs on `38fbaf2ef985faf45a435d1a8c486cef4f1ca1bf`**:
  - `42962719524` (`Check for large files`): `completed` (`success`) — `https://github.com/bridge2ai/data-sheets-schema/actions/runs/42962719524`
  - `42962719426` (`D4D AI Assistant GitHub Mentions`): `completed` (`skipped`) — `https://github.com/bridge2ai/data-sheets-schema/actions/runs/42962719426`
  - `42962719481` (`Build and test data_sheets_schema`): `completed` (`cancelled`, retained) — `https://github.com/bridge2ai/data-sheets-schema/actions/runs/42962719481`

## 6. Issue `#5842` Bounded Read Fix, Verification & Final Publication (`a36c7174fb35c62a2499ee52918354e57a877d6a`)

- **Published Commit**: `a36c7174fb35c62a2499ee52918354e57a877d6a` on `agy/native-cpu-diagnostic-20261111` (accepted by Lead final review, pushed to `origin/agy/native-cpu-diagnostic-20261111`, Draft PR `#5841` description updated and review recorded; new full native CI run `42964017924` cancelled with cancellation retained and cheap checks untouched; `38fbaf2ef985faf45a435d1a8c486cef4f1ca1bf`, original comparison `wp1-cpu-comparison-3cc113e2606c-20261111.json`, and `tmp/deferred-controller-interval-20261111.patch` preserved untouched).
- **Updated Helper SHA-256**: `aa3551c5ab3988858b5a553042e2e35c349fa7934c52dfbb4618a3eb399259c7` (`14223` bytes, `283` lines; three-dot diff `3cc113e2606c...a36c7174fb35` is only `scripts/adhoc/native_wp1_cpu_diagnostic_compare_20261110.py`, `1 file changed, 283 insertions(+)`).
- **Exact Diff (`38fbaf2ef985..a36c7174fb35`, lines 23–30)**:
  ```diff
  --- a/scripts/adhoc/native_wp1_cpu_diagnostic_compare_20261110.py
  +++ b/scripts/adhoc/native_wp1_cpu_diagnostic_compare_20261110.py
       path = Path(path)
       if not path.is_absolute() or path.is_symlink() or path != path.resolve(strict=True) or not path.is_file():
           raise ValueError('physical absolute file required: ' + str(path))
  -    raw = path.read_bytes()
  +    with path.open('rb') as handle:
  +        raw = handle.read(MAX_JSON_BYTES + 1)
       if not (0 < len(raw) <= MAX_JSON_BYTES):
           raise ValueError('empty or oversized file: ' + str(path))
       return raw, {
  ```
- **Verification 1 — Unchanged saved-pair comparison to new output**:
  - Command: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python -I -S -B /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy-native-cpu-diagnostic-20261111/scripts/adhoc/native_wp1_cpu_diagnostic_compare_20261110.py --legacy-out /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/wp1-3cc113e2606c-cpu-legacy-e1-observer-baseline-20261111 --monitoring-out /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/wp1-3cc113e2606c-cpu-monitoring-e1-observer-baseline-20261111 --out /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy-native-cpu-diagnostic-20261111/tmp/wp1-cpu-comparison-3cc113e2606c-5842-recheck-20261111.json`
  - New output artifact: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy-native-cpu-diagnostic-20261111/tmp/wp1-cpu-comparison-3cc113e2606c-5842-recheck-20261111.json` (`278986` bytes, SHA-256 `747bc9744366750ddc2d3ee956be45495b5a5b3cc068fa4045115fe236aebaed`).
  - `/usr/bin/diff -u` against `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/wp1-cpu-comparison-3cc113e2606c-20261111.json` (`d6c3a077889039e81a62fde5e202e94786a1d4dd74f6d53e5fec8fba682d53b4`) shows only `helper.bytes` (`14169` -> `14223`) and `helper.sha256` (`c18d4353...` -> `aa3551c5...`); all comparison metrics, phase rosters, and input hashes are identical.
- **Verification 2 — Oversized saved-input refusal**:
  - Input: sparse `67108865`-byte (`MAX_JSON_BYTES + 1`) file `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy-native-cpu-diagnostic-20261111/tmp/oversized-legacy-input-5842.outer.json` with directory `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy-native-cpu-diagnostic-20261111/tmp/oversized-legacy-input-5842`.
  - Command: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python -I -S -B /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy-native-cpu-diagnostic-20261111/scripts/adhoc/native_wp1_cpu_diagnostic_compare_20261110.py --legacy-out /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy-native-cpu-diagnostic-20261111/tmp/oversized-legacy-input-5842 --monitoring-out /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/wp1-3cc113e2606c-cpu-monitoring-e1-observer-baseline-20261111 --out /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy-native-cpu-diagnostic-20261111/tmp/oversized-refusal-5842.json`
  - Result: exited with code `1` (`ValueError: empty or oversized file: /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy-native-cpu-diagnostic-20261111/tmp/oversized-legacy-input-5842.outer.json`); `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy-native-cpu-diagnostic-20261111/tmp/oversized-refusal-5842.json` was not created.

## 7. Read-Only Diagnosis of Preserved Integrated Diagnostic Deadline (`wp1-382f0dfd1ce8-cpu-monitoring-post-capture-ast-20261111`)

- **Target Artifact**: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/wp1-382f0dfd1ce8-cpu-monitoring-post-capture-ast-20261111` (`.outer.json`, `.supervisor.json`, `outcome.json`, `wp1-harness.json`, `wp1-cutoff.json`, `host-load.json`, `cases/popen-gw0/test_neutral_pre_reservation_d0/u3k-neutral`).
- **Identity & Outcome**:
  - `source_commit`: `382f0dfd1ce863fdf257a77e2bbb2637dbe2f67b` (`composition_commit`: `78723931aaa803f7a706d565da76953c1e9baad4`, `manifest_sha256`: `df9eb421572b3a9ca578adfe1664cd23b372c61f315d6c191d3eba4e57eeda4e`).
  - `kind`: `"cpu-monitoring"`, `arm`: `"monitoring"`, `measurement_class`: `"unqualified_contended_cpu_diagnostic"`, `host_qualified: false`, `wall_time_freshness_qualified: false`, `accepted_quiet_host_timing: false`.
  - `outcome.json`: `returncode: 124`, `worker_returncode: -15` (`SIGTERM`), `interrupted: "deadline"`, `forced_cleanup: true`, `cleanup_verified: false`, `seconds: 881.3745801448822`, `observed_surviving_pids: []`.
  - `.outer.json` / `.supervisor.json`: `returncode: 125`, `child_returncode: 124`, `seconds: 894.4693244590017`, `observed_surviving_pids: []`.
- **Last Evidenced Completed Boundary**:
  1. **Runner / Sandbox Admission**: Session leader PID `76847` started at epoch `1794376360.880962` (`2026-11-11T05:52:40.880962Z`), worker PID `76851` started at `1794376361.255639` (`+0.37s`), and `origins-before.json` + `subprocess-origins.json` (PID `76951` network bind denial at `1794376363.828914`) completed.
  2. **Complete `fixture` (`make_case(tmp_path / 'u3k-neutral')`) Materialization on Disk**: All 68 non-`.git` fixture paths under `cases/popen-gw0/test_neutral_pre_reservation_d0/u3k-neutral/` (identical path set to completed `3cc113e2606c` and `458887766eff` runs) completed on disk:
     - `authority/bundle.txt` at `1794376373.640544` (`+12.76s`) -> `authority/preparation.json` at `1794376425.317668` (`+64.44s`) -> `authority/composition.json` at `1794376462.450567` (`+101.57s`) -> `authority/runtime-execution.json` at `1794376508.384238` (`+147.50s`) -> `authority/preparation-execution.json` at `1794376510.330603` (`+149.45s`) -> `authority/composition-execution.json` at `1794376572.429055` (`+211.55s`) -> `synthetic-runtime/probe-sequence/sequence.json` at `1794376586.038106` (`+225.16s`) -> `authority/invented-ci.json` at `1794376731.794521` (`+370.91s`).
     - Inside `authority_for()` (`tests/utils/native_synthetic_evidence.py:113-192`), `synthetic-capture/authority.json` was written at `1794376807.921819` (`+447.04s`), `capture-1/capture.json` at `1794376849.994952` (`+489.11s`, `captured_at: "2026-11-11T06:00:49.992598Z"`), `capture.read_capture(..., require_current=True)` and `guard.prepare_guard(...)` returned, and the final `make_case()` files `authority/invented-subscription.json` (`1794376916.164117`) and `authority/SYNTHETIC-AUTHORITY.txt` (`1794376916.164509`, `2026-11-11T06:01:56.164509Z`, **`+555.28s` after session start** / **`542.52s` after `bundle.txt`**) completed on disk.
  3. **Partial `launch` (`execute.synthetic_launch`) Progress Before `SIGTERM`**:
     - After `SYNTHETIC-AUTHORITY.txt` (`1794376916.164509`), `make_case()` returns directly and `test_neutral_pre_reservation_diagnostic` enters `with recorder.phase('launch')` (`tests/test_native_u3k_profile.py:244-248`).
     - In `launch`, `outcome.json` recorded 4 subprocess spawns at `1794376921.56`–`1794376928.07` (`+5.4s` to `+11.9s` after `SYNTHETIC-AUTHORITY.txt`), followed by a `126.90s` in-process window with no subprocess spawns (`1794376928.07`–`1794377054.97`), followed by 13 subprocess spawns between `1794377054.97` (`+694.09s`) and `1794377228.53` (`+867.65s`, PID `907`; plus 5 more in `.outer.json` at `1794377237.73`–`1794377244.93`, PIDs `1005`..`1049`) until the `881.37s` driver cutoff (`driver_cutoff_seconds_before_outer: 10` on `900s` limit) sent `SIGTERM` (`-15`). Neither `u3k-neutral/native-attempt` nor `u3k-neutral/native-evidence` was created.
- **What Remains Unknown**:
  - Because `<pid>-diagnostic.json` is written only in the `finally:` block of `test_neutral_pre_reservation_diagnostic` and `<pid>-measurement.json` is written only in `Recorder.finish()` during `pytest_runtest_teardown`, `SIGTERM` (`-15`) left `phase-metrics/` empty (`0` files), `pytest.log` at `0` bytes, and `pytest.xml` / `worker-outcome.json` / `origins-after.json` unwritten.
  - Consequently, (a) the exact in-process function call inside `execute.synthetic_launch` at `SIGTERM`, (b) actual worker `process_cpu` / `thread_cpu` vs. scheduler wait time in `fixture` and `launch`, and (c) `call_counts` / `profile_stability.audit_events` for `382f0dfd1ce8` are unrecorded in `wp1-382f0dfd1ce8-cpu-monitoring-post-capture-ast-20261111`.
- **Justified Comparison with Earlier Completed `cpu-monitoring` Traces (`3cc113e2606c` and `458887766eff`)**:
  - Across `3cc113e2606c` -> `458887766eff`, actual worker `process_cpu` decreased by `-66.91s` (`-15.75%`, from `424.79s` to `357.88s`: `fixture` `149.13s` -> `119.92s`, `launch` `275.66s` -> `237.96s`), while total wall time increased (`472.82s` -> `504.26s`) as host contention rose from `61.46%` mean CPU (`1.576` max 1m load/CPU) to `92.14%` mean CPU (`2.865` max 1m load/CPU).
  - In `wp1-382f0dfd1ce8-cpu-monitoring-post-capture-ast-20261111`, `host_contention` reached **`99.70%` mean CPU (`100.0%` peak)** and **`5.511` max 1m load/CPU** (`host-load.json` 1m load `44.16` before -> `40.89` after across `10` logical CPUs; `3.50x` the load/CPU of `3cc113e2606c` and `1.92x` `458887766eff`).
  - Under that `5.51` load/CPU contention, `fixture` (`bundle.txt` -> `SYNTHETIC-AUTHORITY.txt`) stretched to **`542.52s` wall time** (`3.37x` `3cc113e2606c`'s `160.90s` and `2.97x` `458887766eff`'s `182.94s`), with both pre-capture (`bundle.txt` -> `invented-ci.json`: `358.15s` vs `95.83s` / `90.98s`) and `authority_for` (`invented-ci.json` -> `SYNTHETIC-AUTHORITY.txt`: `184.37s` vs `65.07s` / `91.95s`) stretching proportionally. Consuming `555.28s` (`63.0%` of the `881.37s` driver budget) before `launch` started left only `326.09s` of wall time for `launch` (which required `237.96s` of pure `process_cpu` in `458887766eff`).
  - Attribution limit: because `phase-metrics/` was not flushed in `382f0dfd1ce8`, the `881.37s` wall-clock timeout cannot be attributed to a `382f0dfd1ce8` CPU regression, nor do retained traces isolate `policy.command_policy` CPU to support a micro-optimization cycle.
- **Cheapest Existing Next Observation**:
  - On `382f0dfd1ce863fdf257a77e2bbb2637dbe2f67b`, both `wp1-382f0dfd1ce8-canary-capture-ast-20261111` (`rc=0`, `cleanup_verified=true`) and `wp1-382f0dfd1ce8-capture-recheck-capture-ast-20261111` (`rc=0`, `cleanup_verified=true`, `318.57s`) have already passed, and `composition-382f0dfd1ce8` + `wp1-contract-382f0dfd1ce8.json` are already prepared.
  - The single cheapest existing observation that resolves the remaining uncertainty (obtaining flushed `<pid>-measurement.json` and `<pid>-diagnostic.json` for `test_neutral_pre_reservation_diagnostic` on `382f0dfd1ce8`) is **one existing `scripts/adhoc/native_wp1_validation_20261110.py --kind cpu-monitoring` run against the existing `wp1-contract-382f0dfd1ce8.json` launched only after a free read-only host-load check shows 1-minute load per CPU below `~2.5` (1m load `< 25` on 10 CPUs, or under the existing quiet-host gate for `kind=monitoring`)**, avoiding guaranteed wall-clock cutoff under `40+` host load.





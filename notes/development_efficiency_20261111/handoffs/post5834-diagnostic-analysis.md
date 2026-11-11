# Post-#5834 native diagnostic analysis

**The import-binding blocker is passed, but current capture acceptance still fails before reservation.** WP2 preflight passed, fresh execution admission and controller prewarm returned, and `accept_current_selection` was entered but never returned a guard. Optimizing only work after successful acceptance cannot resolve this earlier failure.

Post-fix source `458887766effe38207a77fea2d8033f1f3e1c7f3`, PID34474: saved pytest XML reports 1 test, 0 failures, 0 errors, 0 skips, 501.380 seconds. The passing diagnostic records `genuine_refusal`, not a successful launch. Attempt/evidence are absent; no reservation boundary, controller activation or child execution was observed. Guard stable/restored, zero open rows; all timing/freshness qualification flags remain false. Final outer/config cleanup belongs to the native owner and is not certified by this analysis.

## Refusal boundary

The preserved capture timestamp is `2026-11-11T04:41:41.803810Z`; maximum age is 300 seconds with a 90-second reservation margin.

| Boundary | UTC entry | Capture age at entry (s) | Observed outcome |
|---|---|---:|---|
| Preflight freshness (row503) | 2026-11-11T04:42:52.859044+00:00 | 71.055 | return |
| Fresh execution admission (row744) | 2026-11-11T04:44:23.491952+00:00 | 161.688 | return |
| Controller prewarm (row877) | 2026-11-11T04:45:20.356403+00:00 | 218.553 | return |
| Current capture acceptance (row904) | 2026-11-11T04:46:44.453103+00:00 | 302.649 | exception:ValueError |
| Final acceptance freshness (row993) | 2026-11-11T04:47:16.661465+00:00 | 334.858 | exception:ValueError |

Observed exception ancestry: `synthetic_launch → synthetic_launch → _launch → accept_current_selection → load_current → before_dispatch → _fresh`. The pinned source fills in the unmonitored call from `load_current` through `load_guard` and `SubscriptionGuard.__init__` to `before_dispatch(check_only=True)` and `_fresh`. The saved capture is already 302.649 seconds old when acceptance begins; acceptance then consumes 23.582 thread-CPU / 32.216 wall seconds before refusing. It does not reach `before_reservation` or attempt mkdir. The 210-second latest margin-preserving point also precedes controller prewarm entry.

Source anchors at the post-fix commit: `native_shared_execution_orchestration.py:123` (mandatory preflight before engine); `native_execution_orchestration.py:363` (controller prewarm), `:366` (acceptance), `:379` (lease), `:385` (reservation freshness), `native_subscription_admission.py:158` (load_current), `native_subscription_guard_v2.py:398` (constructor freshness), `:429` (age refusal).

## Descriptive phase comparison

Baseline monitoring source `3cc113e2606c563236d9c06098c5329ddd027a38`, PID7351. Both have the same interpreter identity, but the source heads, call rosters and host conditions differ. These figures do not establish a causal WP3 speedup or wall-time improvement. Explicit fixture and launch phases do not overlap; pytest wrapper and nested function durations must not be added to them.

| Phase | Baseline calls | Post-fix calls | Baseline process CPU (s) | Post-fix process CPU (s) | Baseline wall (s) | Post-fix wall (s) |
|---|---:|---:|---:|---:|---:|---:|
| fixture | 478 | 457 | 149.126 | 119.922 | 160.996 | 183.040 |
| launch | 535 | 537 | 275.663 | 237.958 | 302.463 | 310.923 |

Changed call counts (baseline → post-fix; all other label counts unchanged):

- fixture: `schema_capture` 26 → 12; `schema_reconstruction` 13 → 6.
- launch: `freshness_before_dispatch` 1 → 2; `freshness_check` 1 → 2.

## Dominant recorded work

The next table ranks post-fix **observed residual thread CPU**: each call interval minus its immediate monitored children, inferred from same-thread nested monotonic intervals. This avoids double counting within the observed tree, but still includes uninstrumented descendants; it is not true function self CPU. Inclusive totals are shown separately and overlap. No full cProfile data exists in these control-mode records.

| Phase / label | Calls | Baseline residual thread CPU (s) | Post-fix residual thread CPU (s) | Post-fix inclusive thread CPU (s) |
|---|---:|---:|---:|---:|
| fixture / public_fixture | 1 | 24.317 | 26.358 | 119.919 |
| fixture / schema_capture | 12 | 54.243 | 25.094 | 25.094 |
| fixture / preparer_verified | 17 | 24.467 | 21.948 | 28.458 |
| fixture / execution_registration_verified | 5 | 16.469 | 20.384 | 35.614 |
| fixture / shared_registration_verified | 5 | 10.795 | 15.671 | 51.330 |
| launch / controller_prewarm | 1 | 55.953 | 63.155 | 71.005 |
| launch / execution_registration_verified | 13 | 57.417 | 56.958 | 114.803 |
| launch / preparer_verified | 20 | 100.000 | 50.455 | 64.156 |
| launch / shared_registration_verified | 8 | 24.053 | 25.834 | 103.487 |
| launch / launch_engine | 1 | 11.986 | 13.346 | 201.271 |

Controller prewarm alone returned after 71.005 process-CPU / 84.097 wall seconds. Registration/schema verification calls are nested inside several enclosing boundaries; their inclusive totals are not independent phase costs.

The next development target must address measured work before successful current-capture acceptance while preserving the original capture timestamp and fresh checks. A post-acceptance redesign may address a later boundary, but this run has not reached that boundary and cannot validate that benefit.

## Provenance and limits

Produced by `scripts/adhoc/analyze_post5834_diagnostic_20261111.py` using only saved inputs. Detailed call counts, ordered rosters, observed-tree parent indices and hashes are retained in `tmp/post5834-analysis-20261111/summary.json`. The JSON summary retains original local source paths. No input evidence is rewritten. This analysis does not certify outer cleanup, quiet-host performance, accepted reservation or model generation.

| Input | SHA256 |
|---|---|
| `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/wp1-3cc113e2606c-cpu-monitoring-e1-observer-baseline-20261111/phase-metrics/7351-measurement.json` | `004949ed96e4aeaabe0525aa23ce02ec3e9842f33ced18f1ab7c87f0a16e2110` |
| `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/wp1-3cc113e2606c-cpu-monitoring-e1-observer-baseline-20261111/phase-metrics/7351-diagnostic.json` | `2a501f6b73443a183bb3895cecbc61a29b7af7752fa68f46be08e5fbb0a08173` |
| `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/wp1-3cc113e2606c-cpu-monitoring-e1-observer-baseline-20261111/wp1-harness.json` | `ba5d39fe18675634407a87a8887b83a5c3c814e4cdc33d8ea0afb8da2f5732e6` |
| `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/wp1-3cc113e2606c-cpu-monitoring-e1-observer-baseline-20261111/pytest.xml` | `97a34f09e16b657a1adb7b6c7430a994d48125153e2abc1ccc206910475cc381` |
| `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/wp1-458887766eff-cpu-monitoring-post-5834-20261111/phase-metrics/34474-measurement.json` | `36395ceb9db354c4ab7d4f778297726445e55b44ee48210f9cf27f568665786b` |
| `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/wp1-458887766eff-cpu-monitoring-post-5834-20261111/phase-metrics/34474-diagnostic.json` | `c995ec363c53e484670587e2c4003b23634e2a2af8e8d60066f874c7b5aa1ff2` |
| `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/wp1-458887766eff-cpu-monitoring-post-5834-20261111/wp1-harness.json` | `eacb2948f3bc82200eb04ff21df1b8b0af8463431a8a76ad79871c77b2b5a529` |
| `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/wp1-458887766eff-cpu-monitoring-post-5834-20261111/pytest.xml` | `bfd033fffa8b49036e20933b04f46d266e2ea9343f25dbb0b93dcd8d7ced1943` |
| `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/worktree-458887766eff/src/data_sheets_schema/native_subscription_admission.py` | `dca8b62e19fcf6e941e36fb9ef2d3df737871e3818bfe1472cf8e4f12843d1f9` |
| `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/worktree-458887766eff/src/data_sheets_schema/native_subscription_guard_v2.py` | `cb5444686171426a265bd5e2a5396ace35b0d92116f4bfb97b375ef3c1764988` |
| `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/worktree-458887766eff/src/data_sheets_schema/native_execution_orchestration.py` | `08503aebb96956c5f6356c8447909d381560eedc5bfcb8a9330a2f8edf3fd5c2` |
| `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/worktree-458887766eff/src/data_sheets_schema/native_shared_execution_orchestration.py` | `46c5da411dff1bbe240341138abeb2b5d1678ea933ceb519e46e92108693704c` |

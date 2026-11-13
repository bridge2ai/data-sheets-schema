# Callback prewarm efficiency: source-only disposition

2026-11-11. Inspected frozen native `458887766effe38207a77fea2d8033f1f3e1c7f3` and retained artifacts only. Report is on existing analysis branch `codex/native-development-analysis-20261111`; native and tools branches remain unchanged. No code, imports, tests, benchmarks, new profiling or provider/native calls were run for this task.

**Recommendation: no additional implementation is justified by the available measurements.** A concrete duplicate module-attestation candidate exists, but its material benefit on the current prewarm path is unproven. Defer it. Do not remove current-input checks, extend freshness or retain an admission across lifetimes based on the residual alone.

## Evidence and limits

The post-5834 measurement records controller prewarm at **71.004678959 thread-CPU seconds / 84.097215500 wall seconds**. The retained analysis attributes **63.155 seconds of observed residual thread CPU** to that boundary. Residual includes unmonitored descendants and instrumentation; it is **not function self CPU**. Nested inclusive timings overlap and cannot be added.

The detailed historical cProfile is from `a2241d4c67b17149e3baf2eeb41be4ebf3d9bde7`, before `prewarm_before_acceptance` was introduced. Direct ignore-independent searches of its fixture and launch function JSON files find no `preloaded_callbacks`, `check_active` or `prewarm_before_acceptance` rows. This is not a zero-cost result: the older launch refused before callback activation, and source-loaded labels also suffer collisions. Its launch rows report `module_source_identity`: 6,861 calls, 0.716164766 inclusive thread-CPU seconds; `_own_callables`: 8,180 calls, 0.830536125 inclusive thread-CPU seconds. These nested rows are not additive, do not isolate duplicate callback checks, and provide neither a current-head estimate nor an upper bound on savings.

U3K-H4 documents cProfile's collapse/overwrite of distinct reloaded code objects sharing `(filename, line, name)`. Lost rows cannot be recovered from pstats. That profile imposed substantial overhead and reached a different refusal boundary. The current monitoring trace is unqualified and has no full per-function profile. Neither attributes the 63.155-second residual to this candidate.

## Concrete candidate, deferred

`native_shared_callback_orchestration.py:242–251` discovers a graph containing its starting modules and opens them through the verified loader. At `:273–275`, `_SourceCheck.modules` concatenates explicit modules, graph modules and `rebuild` without deduplication. When the loader reuses an exact object, `_SourceCheck.__call__` (`:162–167`) repeats its attestation, including `_own_callables` in `native_execution_authority_v2.py:332–349`.

A bounded future patch could build a first-seen, exact-object-identity roster once per `_SourceCheck`, rejecting contradictory expected identities for one object. Every invocation must still reread **every current source pin** and freshly attest **every distinct module**. Distinct objects sharing a name/path must remain separate. No verdict or callable inventory may be cached across calls. Scope would be the callback orchestrator and focused tests; authority/loader and protected files need no edits.

Required tests: repeated references, distinct same-name/path objects, contradictory expectations, source-byte mutation between checks, callable/code replacement, unchanged teardown and worker locking. A separately authorized comparison would need to establish actual duplicate cardinality and attributable cost on the current path before a latency claim. Neither implementation nor that comparison is started here.

`Admission.check_active()` (`native_shared_callback_capture.py:84–85`) only validates mint membership/references. `reconstruct()` (`:87–96`) deliberately checks sources around fresh execution reconstruction. Prewarm and activation (`native_shared_controller_orchestration.py:228–264`) deliberately use separate loader/admission lifetimes. Removing those checks or sharing their verdicts would change the contract.

## Ownership and remaining gates

AST-fact reuse belongs to the separate import-graph work; selection capture/rebuild belongs to capture-A work. No overlapping implementation, capture deduplication, loader change, source-pin caching, controller lifetime change or protected packet edit is proposed.

Native acceptance still fails on stale capture before reservation. The latest diagnostic passed by recording a genuine refusal. Fresh pre-reservation acceptance, two public-completion witnesses, 17 failure-path cases and eight deferred cohorts remain pending; quiet-host qualification is separate. Owner decisions remain assigned-source protected API postimage installation and exact D128 scanner approval. This review supplies no approval or runtime authorization.

## Retained evidence

Paths are relative to `d4d-executions/`.

| Input | SHA-256 |
|---|---|
| `scratch-native-u1u3/u3m/wp1-458887766eff-cpu-monitoring-post-5834-20261111/phase-metrics/34474-measurement.json` | `36395ceb9db354c4ab7d4f778297726445e55b44ee48210f9cf27f568665786b` |
| `scratch-native-u1u3/u3k/baseline-profile-summary.json` | `14bd79d6a8f7c7d6ad03cbc047ec6ab5e6b063abc48354c30ae227e58422b486` |
| `scratch-native-u1u3/u3k/profile-pre-reservation-a2241d4c6/phase-metrics/41580-launch-functions.json` | `49a47ed794474dac372419224d1fd796154173eb8783304cfddce88da6d789c7` |
| `codex-native-u1u3/src/data_sheets_schema/native_shared_callback_orchestration.py` | `9af7b484bda253884d027a5eaacdd28601bb500e7841bef66b456e792df4888d` |
| `codex-native-u1u3/src/data_sheets_schema/native_shared_callback_capture.py` | `450f0b3276a18021073bf43699bd2816779a6c5cad035276f2f160f34b7988d2` |
| `codex-native-u1u3/src/data_sheets_schema/native_shared_controller_orchestration.py` | `bc03cb162340ac6a1d2e7a0afc6a3373745227e6a84fd5bfbc0dcfc4596de619` |
| `codex-native-u1u3/src/data_sheets_schema/native_execution_authority_v2.py` | `9b7a2d3842a007bae35f2d079e6ffa631190e7d2f4b5f10aad9a6d1243407687` |

Residual derivation and chronology: `codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/post5834-diagnostic-analysis.md`. Profile limitations: `plans/reviews/native_u3k_2026-11-09.md`. Values above are direct reads of retained records; no new analysis script was needed.

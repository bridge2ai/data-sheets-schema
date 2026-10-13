This external pytest plugin profiles only the exact real shared-generation pipeline node. It is disabled unless --d4d-profile-output is supplied, refuses multiple/different nodes or xdist workers, and requires new external output names. It does not modify the worktree. No plugin or project code was executed during authoring; stdlib AST parsing passed with Python3.9 grammar.

Root-only invocation proposal (after inspecting this source; root has prepared the isolated Python3.12 environment):

```bash
cd /private/tmp/d4d-performance-implementation-20261012
PATH=/private/tmp/d4d-performance-implementation-20261012/.venv/bin:$PATH \
PYTHONPATH=/private/tmp/d4d-agent-performance-20261012-vq8rgbu9/implementation/profiling:/private/tmp/d4d-performance-implementation-20261012/src \
PYTHONPYCACHEPREFIX=/private/tmp/d4d-agent-performance-20261012-vq8rgbu9/implementation/profile-run01/pycache \
/private/tmp/d4d-performance-implementation-20261012/.venv/bin/python -m pytest \
  tests/test_shared_generation_runtime.py::test_real_complete_api_pipeline_and_completed_recheck \
  --rootdir=/private/tmp/d4d-performance-implementation-20261012 \
  --confcutdir=/private/tmp/d4d-performance-implementation-20261012 \
  -n0 -v -p no:cacheprovider -p d4d_target_profile --durations=0 \
  --d4d-profile-output=/private/tmp/d4d-agent-performance-20261012-vq8rgbu9/implementation/profile-run01/events.json \
  --junitxml=/private/tmp/d4d-agent-performance-20261012-vq8rgbu9/implementation/profile-run01/junit.xml
```

Create that fresh external result directory before invocation. Root supplied the fresh isolated .venv: Python3.12.11, pytest7.4.4, xdist3.8.0, LinkML1.9.3/runtime1.9.4, PyYAML6.0.2, anthropic0.72.0 and pydantic2.12.3. The earlier system-site environment is not used. Placing this .venv/bin first on PATH gives validator children the same installed toolchain. Verify loaded project origins as part of the recorded invocation. A profiler source-origin check rejects instrumented modules outside this checkout's src/data_sheets_schema. Root should also record HEAD/status, dependency provenance, command/stdout and unmodified source pins before/after.

Wrappers replace only the listed module function attributes and DerivationCache._derive method; classes and input objects remain original. functools.wraps preserves function metadata, but wrapper function/code identity changes. A bounded ignored-inclusive source search of these target modules and the two test/helper modules found no function-code identity admission for the selected targets. Current explicit exact-type admission is on the unchanged DerivationCache class and captured data. Source/asset bytes are untouched. This is not a claim about arbitrary other tests; the one-node gate is deliberate.

Each wrapper returns the exact object returned by its original, re-raises the same exception with bare raise, and records time in finally. It does not mock validators, freshness, transport or writes. Original exception type is diagnostic only; no arguments, captured documents or return payloads are logged. api.execute events identify their actual test/helper caller and finite mutation/change/case label. Existing seven-phase, no-new-call, independent-check, mutation and file-preservation assertions all remain real.

Installation occurs after collection and before fixture setup. It may import a listed module not already loaded; that import's duration and already_loaded status are explicitly recorded. Therefore this is attribution of the test/fixture work, not a cold-import benchmark. Every source is hashed before replacement. The wrappers remain installed through teardown, then are restored in sessionfinish; unconfigure and atexit repeat the idempotent restoration/save as fallbacks. A binding later replaced by another owner is left intact and reported as an error instead of being overwritten. Graceful failure/KeyboardInterrupt restores and saves; SIGKILL or machine failure cannot guarantee cleanup/persistence.

The JSON contains individual nested calls, pytest setup/call/teardown outcomes, restoration/errors, Python/executable/sys.path and source hashes. Inclusive wall/thread-CPU times overlap; do not sum parent and descendants. Exclusive fields subtract only instrumented descendants, not all Python work. Validator events include the process-wide delta of reaped-child user/system CPU, while their wall includes launch/wait. Other concurrently reaped children could affect that counter; run this workload alone. Child CPU does not appear in thread CPU.

The final JSON must have errors=[] and restored=true; JUnit must retain the exact real node and successful phases before treating the profile as valid. An instrumentation save error does not replace a test return/exception, so an empty/missing profile is not evidence of fast or successful execution. Aggregate events after the run by function/caller, not by adding all inclusive values. Do not compare this instrumented time directly with old CI wall time as a speedup.

First candidate to assess from counts/times: typed_audit.prepare:274 fully builds and discards omissions._schema's catalog, followed by cold _derive_uncached -> omissions.prepare:361 rebuilding it. A future bounded optimization could retain fresh snapshot/root/import-closure validation at both sites and reuse only successful pure catalog construction within that one caller-owned derivation lifecycle. Final independent checks must still start with a new DerivationCache. No optimization is implemented here.

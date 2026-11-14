# Native import-fact reuse: bounded evidence

2026-11-11. Branch `codex/native-import-facts-reuse-20261111`, based on
`458887766effe38207a77fea2d8033f1f3e1c7f3`. Local worktree:
`/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-native-import-facts-20261111`.
Paths below are relative to that worktree unless stated otherwise.

The change retains immutable syntax/import descriptors keyed by exact source
bytes, filename and traversal mode. It keeps fresh source checks, graph traversal,
current lint policy, import-origin resolution and downstream loading/attestation.
It caches neither AST objects nor completed graphs or authority decisions.
Retention has bounded entry, row and text accounting. Changed or unfamiliar
producer state uses the original AST path. Sources below 4096 bytes also take
that original path before scanning producer state; this is a conservative size
heuristic, not an optimum for every syntax shape.

## Findings and corrections

- #5844: effective import-hook changes and equal-looking compile flags could
  escape the initial producer key. Effective `__import__` and exact type/value
  flag keys now have warm/cold mutation witnesses.
- #5845: unconditional UnionType import conflicted with Python 3.9 support.
  UnionType is now optional.
- #5846: Python 3.9 lacks the inspectable effective function builtins used here;
  optional reuse remains unavailable there. Only retention-specific tests are
  skipped on 3.9; cold behavior remains. **Python 3.9 was not executed locally.**
- #5848: the first canary failed because CPython 3.13's private `_ast_Ellipsis`
  alias disabled producer binding. Public AST bindings are now checked without
  treating this private alias as a public class name; diagnostic state is kept.
  The positive cache assertion remains strict. The same-node retry passed.
- #5849: the first CPU comparison exposed a tiny-graph regression. Small sources
  now bypass guard/extraction, with positive and refusal witnesses. Warm fixtures
  use substantive assignments above the threshold, not comment padding.
- #5850: narrow the environment-removal statement to the actual variable list
  and distinguish pinned historical helpers from a replay command catalog.
  These note-only corrections do not change executed code or evidence.

Current SHA256s: production `b2189db86428b5977bfcbaa72adc5f504f3449c31b583359555b074916a95558`;
tests `cb565125f92baa095cf0f8489381d7fe82888fd7e8280768f7085e49b772ac9e`.

## Validation and retained raw evidence

All eight runs used the existing primary repository `.venv/bin/python -B`
(CPython 3.13.12), worktree PYTHONPATH and the existing owned subprocess-deadline
helper, capped at 30 seconds per run. No provider, profiler or whole-launch test
ran. Every run completed without expiry and with verified owned-process
termination. Helpers removed variables ending in `_API_KEY`, plus
`ANTHROPIC_AUTH_TOKEN`, `CLAUDE_CODE_OAUTH_TOKEN`, `ANTHROPIC_BASE_URL`,
`OPENAI_BASE_URL`, `PYTEST_ADDOPTS` and `PYTEST_PLUGINS`. Other environment
variables were inherited; command records contain only explicit overrides.

All evidence directories are under `tmp/`, retained locally and deliberately
excluded from this commit. Each has command, log, outcome and deadline evidence;
pytest runs also have JUnit, CPU runs input manifests and flushed completed rows.

| Evidence directory under `tmp/` | Actual result |
|---|---|
| `import-facts-canary-20261111` | Initial failure: 1 failed in 0.26 s; #5848; return 1 |
| `import-facts-canary-retry-20261111` | 1 passed in 0.14 s; return 0 |
| `import-facts-module-20261111` | 24 passed in 0.29 s; return 0 |
| `import-facts-regression-20261111` | 18 passed, 17 deselected in 0.37 s; return 0 |
| `import-facts-cpu-20261111` | 18 completed comparison rows; return 0; tiny regression |
| `import-facts-small-canary-20261111` | Revised positive: 1 passed in 0.32 s; return 0 |
| `import-facts-small-validation-20261111` | 45 passed in 0.59 s; return 0 |
| `import-facts-small-cpu-20261111` | Revised 18 comparison rows; return 0 |

The final 45 cases are 27 focused cases plus the same 18 existing import-graph,
verified-loader and implicit-parent cases. No unrelated cohort was repeated.
Original evidence and helpers are unchanged. Helpers from superseded source
snapshots refuse the current tree; all helpers also refuse to overwrite an
already-used output directory. They are pinned, single-use provenance rather
than commands that can all be replayed against the final tree. Before #5849, the initial CPU-run
source and tests were saved under `tmp/import-facts-cpu-20261111/source_snapshot/`
with a binary-capable production diff. Snapshot SHA256s are production
`98f18a06619fa50aee89f61b924fbabf27928ec7b82e9f9941b6dab50bebb557` and tests
`60ddb6a0949642d6b465bdaea462fcaf2af4c013ad8c2e60d300c4b1042f2c9b`.
This snapshot covers that initial CPU revision, not the exact source of every
earlier run; the original failed canary used the different pins in its helper.

## Component CPU result and limits

Both arms call the same public graph checker with identical bytes/pins. The
reference disables only optional retention to take the original AST branch;
it is **not a benchmark against a previous Git revision**. Each input completed
one cold/first/repeated comparison before further repetitions. Pair order
alternated; first calls were excluded from repeated-call totals. Graph equality
and retained tuple identity were verified. These are process-CPU totals for
three completed calls per column, not wall times.

| Snapshot / input | Cold reference | Normal repeated | Normal first calls | Repeated/cold |
|---|---:|---:|---:|---:|
| Initial / tiny | 0.001484 s | 0.007511 s | 0.017212 s | 5.0613 |
| Initial / current registration | 1.604345 s | 0.624947 s | 2.017523 s | 0.3895 |
| Revised / tiny, zero eligible sources | 0.000808 s | 0.000535 s | 0.000617 s | 0.6621 |
| Revised / current registration, 57 eligible sources | 1.392191 s | 0.522727 s | 1.731362 s | 0.3755 |

The revised tiny input stays entirely cold; sub-millisecond differences do not
establish a tiny-input speedup. All 57 eligible representative sources were
retained and reused; smaller reached files still take the cold path. First-fill
cost is higher. The representative result supports testing this integration
candidate, **not** a whole-launch speedup, freshness pass, quiet-host wall-time
result, cross-loader cache lifetime or cross-platform performance claim.
The older 38.455-second inclusive import-graph profile motivated the candidate;
its time is not projected onto the current launch.

## Helper and input identities

Saved helpers are in `scripts/adhoc/`; each embeds exact source/test pins and
uses a fresh evidence directory. SHA256s:

| Helper basename | SHA256 |
|---|---|
| `run_native_import_fact_canary_20261111.py` | `8e693a5be596c47c1d3d5176a0c4a2e42e75ae3bfba970d3d86528d963bf3aed` |
| `run_native_import_fact_canary_retry_20261111.py` | `98cf5364aa496a55132bf8a0b69fa8bf80aeaba287c2d5b74111725430e942c3` |
| `run_native_import_fact_module_20261111.py` | `8f49dfe5fa73646bbba8c165f9df22f9b8a02754a0501edbb9ce5fe1a671f570` |
| `run_native_import_fact_regression_20261111.py` | `57e57a93a1f68a213bd61cf4a023a445d0968aeb4130de9d98712623de38a8c0` |
| `measure_native_import_facts_cpu_20261111.py` | `0fb250e483597544a3975ac871bcc3f08950b9fb3bafac3ac6541767400cce8e` |
| `run_native_import_fact_small_canary_20261111.py` | `774463d1f6f6b61f59ebbfc47fd92037b3627ba66b2b72fee6ddeaa46b01aefb` |
| `run_native_import_fact_small_validation_20261111.py` | `5c17aeeb172df00c5aa2cda7ac73860b8de9ef785493530276cc6cc08d8dd730` |
| `measure_native_import_facts_small_cpu_20261111.py` | `b276ff4ab4648504dd1b5b6d44442e6d31771b387042964a09300cc8c5829ec1` |

CPU input manifests contain exact source roster hashes/sizes and entry identity:

| Path under `tmp/` | SHA256 |
|---|---|
| `import-facts-cpu-20261111/tiny-inputs.json` | `e61b8c0b4ffaf2c4e6fa17113cf9111344327620f663dc9f9e68cbdc7a3e249f` |
| `import-facts-cpu-20261111/current_registration-inputs.json` | `f3086e7391acc3ce7de6483c6b17067dae4c72730e8060da7716f75d3b3adeb3` |
| `import-facts-small-cpu-20261111/tiny-inputs.json` | `cf4c0ee2379eedcbfb53f6246fd8f8409ce04940897a0522385d0ca30996c531` |
| `import-facts-small-cpu-20261111/current_registration-inputs.json` | `50a817aed0eda8f906bc3df9c867c9867a9723e4be12795128fc12537e8c701d` |

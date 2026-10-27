# Unit 2 fixture repairs before downstream integration

2026-10-27. Refs #4354, #4537. This is the fresh
`codex/n2-2-restack-20261026` branch, initially
`8f4c3e328b623080424df15139ba539bb136f40b`; original N2 branches remain preserved.

All three affected test modules first appear in fresh unit 2. Unit 1 has none
of them. Their original Git blobs and the relevant capture, observations,
results, contract, evidence, effects, stage and streams implementations are
identical in fresh units 2, 3, 4 and the final pre-repair stack `9ea9b70a3`.
The six directly imported fixture modules (observations, stages, typed audit,
results, live capture and registration) also exist in unit 2 and are identical
to that stack. This is source evidence for placing the repair here, rather
than treating final-stack validation as validation of each earlier unit.

The three test files are copied exactly from tested repair
`9e1ac52272ded77eb73f1656ff1b88e6d073439e`:

- `test_native_shared_response_identity.py` creates a fresh captured-prefix
  object when extending fixture streams, while retaining the production
  verification caches shared between snapshots.
- `test_native_shared_stream_bindings.py` accepts and verifies the strict
  loader's `_catalogs` keyword before raising its existing sentinel.
- `test_native_trace_single_decode.py` reads the exact original literal
  observations module and checks the three later cache dictionaries explicitly.
  All original fields, exception graphs, partial state and public outcomes
  remain compared; unknown attributes remain visible.

The inert [literal fixture](../tests/fixtures/native_trace/native_shared_observations_0125eebbc.py.txt)
retains the original SHA256
`3bc93c2d1720d4e41ee83e7be7d8758a56836062c316f75ecc4b505e80b6d3ab`.
The [recovery helper](../scripts/adhoc/recover_native_trace_oracle_20261027.py),
[original recovery result](native_trace_oracle_20261027/recovery.json) and
[later-cache diff](native_trace_oracle_20261027/later-cache-change.diff)
are preserved byte-for-byte from the repair branch. The result correctly
identifies the original recovery checkout/head; it is not presented as a new
unit 2 execution. It proves the original `a8c11973d` factoring reverses to
literal `0125eebbc`, while later `a462dcfec` caching prevents the old partial
reversal from reconstructing that oracle. Pytest itself needs no Git history.

No production module, prompt, schema, protected file, runtime deadline or
registered attempt changes here. Unit 2 does not contain the later unit 4
acceptance utility, so its [bounded validation helper](../scripts/adhoc/validate_n2_unit2_repairs_20261027.py)
is standalone. It runs only these three modules with closed project/test
imports, normal virtual-environment prefixes restored without `.pth` execution,
source/blob checks before and after, and retained logs/JUnit. It does not run a
real native binary, provider call, full-unit suite or scientific acceptance.

Unit 2 validation is pending. The later stack's 56 passing cases are prior
evidence only; they are not claimed as this branch's result. After this unit
passes its focused check, downstream fresh units must carry this repair before
being treated as independently reviewable PRs.

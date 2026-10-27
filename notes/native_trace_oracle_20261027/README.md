# Preserve the literal Trace oracle after later caching

2026-10-27. Refs #4537, #4354. Test-only repair; production, saved attempts,
runtime deadlines and the original performance evidence are unchanged.

The 41 setup errors in the frozen N2 `9ea9b70a3` run all arose before the
constructor comparisons ran. The test reversed only `a8c11973d`'s single-decode
factoring in the *current* source, then required the fixed original hash.
Current source also contains `a462dcfec`'s subsequent prefix/event and per-Trace
request/admission/settlement caches. Reversing the earlier factoring cannot
remove those later changes. Its resulting SHA256 is
`2be668cf81eb0ede4d733e683bd435e4e101ed7c6327403ea529cea5aaa6d92a`, not the
literal oracle's `3bc93c2d1720d4e41ee83e7be7d8758a56836062c316f75ecc4b505e80b6d3ab`.

This is neither a harmless docstring change nor a newly introduced restack
edit. The recovery commit `0d5bddbc03b02cfa3efdea312c10aca002f6d85c` restored
the exact later cached production file and the exact earlier test. The
[unit2 recovery manifest](../coordination/n2_unit2_recovery_manifest_20261025.json)
records both as pre-owner files copied from `a33d80d8`. Original
[comparison evidence](../native_trace_comparison_2026-10-08/validation.json)
records the literal source, initial single-decode candidate and test hashes.

The [recovery helper](../../scripts/adhoc/recover_native_trace_oracle_20261027.py)
reads exact local Git objects, verifies all expected hashes, and proves that
the *original* `a8c11973d` source still reverses byte-for-byte to
`0125eebbc214d0907c3b69d23758cd9441911a78`. It also proves the restored/current
production bytes equal `a462dcfecb55503f6f8227e4908b56133b2c7572`. Results and
Git blob IDs are in [recovery.json](recovery.json); the substantive later
production changes are retained in [later-cache-change.diff](later-cache-change.diff).
These are source-history checks, not reruns of the original benchmark.

The new inert [fixture](../../tests/fixtures/native_trace/native_shared_observations_0125eebbc.py.txt)
is the complete original 17,785-byte Git blob, unchanged. Pytest checks the
**same original SHA256** before compiling it under the original canonical
module name. Tests no longer reconstruct an oracle from mutable current
production and need no Git history at test time. The fixture imports current
contract/evidence dependencies, as the old test did; this is an exact historical
observations-module oracle, not a complete historical runtime reconstruction.

Every original instance field, scalar/collection type, mapping order, complete
exception graph, partial constructor state and public method outcome remains
compared. The three explicitly added cache dictionaries (`_req_cache`,
`_adm_cache`, `_set_cache`) are checked separately before removing only those
three fields from the original-state comparison. All three must exist after
successful initialization; on partial refusals they must be absent before
their initialization boundary or present and empty afterward. Their dictionary
types, key/value types, order and contents must exactly match successful
request/admitted/settled results, which also remain compared with the literal
oracle. Unknown attributes, including private ones, are never filtered out.
Three causal mutations exercise a missing cache, a foreign cache entry and
an unexpected private field.

Separate Codex internal review cleared the exact fixture and explicit cache checks.
At `9e1ac52272ded77eb73f1656ff1b88e6d073439e`, all 56 cases across the three
repaired modules passed, including the 41 original oracle cases and three new
causal mutations. Source and project-import checks passed. The retained 41
setup errors remain historical failures; the new targeted run does not rewrite
that record or establish a fresh whole-suite pass. Full evidence is linked in
[the restack handoff](../native_n2_restack_2026-10-26.md).

Reproduction of fixture/provenance creation requires fresh output paths:

```sh
python3 scripts/adhoc/recover_native_trace_oracle_20261027.py
```

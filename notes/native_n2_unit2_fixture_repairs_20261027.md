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

The repair was committed as `1c620ce96570f46f990aa416201ee87e235cc61c`;
the bounded helper's tracked-origin and unique-JUnit-identity checks followed
in `7265a8d7c3b373ce049b5ebb4eba22c5091b7e98`. The fresh unit 2 run at that
exact latter head passed **56 cases** (5 response-identity, 7 stream-binding,
44 literal-oracle/cache cases), with no failures, errors or skips. Pytest
reported 18.43 seconds; the enclosing driver reported 21.02 seconds.
All tracked source bytes/modes were unchanged, protected files matched the
cached target, and project/test imports before and after matched the current
tree's tracked source hashes. The explicit dependency bootstrap restored the
physical venv prefixes without executing `.pth` files. Installed dependency
versions were recorded; their bytes were not independently attested.

The first invocation mistakenly supplied the abbreviated expected head
`7265a8d7c`. The exact-head guard refused before creating a test child or
collecting tests. Its external directory contains only `source-before.json`;
there is **no saved raw stderr, driver outcome or JUnit** for that invocation.
The refusal and its exit 1 were observed in the tool session. We preserve the
available file without manufacturing a retrospective raw log. The second run
used the full 40-character head and a fresh output directory, with identical
source and no relaxed guard.

The [archive manifest](native_n2_unit2_fixture_repairs_20261027/manifest.json)
pins both retained result bundles and records byte/mode round-trip checks,
followed by rereading all selected originals. `run-01.tar.gz` preserves the
first attempt's sole source inventory; `run-02.tar.gz` preserves the completed
second run's source/origin/bootstrap records, command, outcome, log and JUnit.
The [archive helper](../scripts/adhoc/archive_n2_restack_validation_20261027.py)
is copied exactly from the already reviewed final delivery; its existing eight
tests were not rerun. Its selection includes ignored files at the named result
boundaries but deliberately excludes the `cases/` tree, which remains in the
original external run directory. It neither recalculates nor endorses pass totals.

Reproduction on the tested clean head uses:

```sh
/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python \
  scripts/adhoc/validate_n2_unit2_repairs_20261027.py \
  --expect-head 7265a8d7c3b373ce049b5ebb4eba22c5091b7e98 \
  --output /private/tmp/d4d-n2-unit2-repairs-20261027-r2
```

The output path must be fresh; the retained directory is never overwritten.
The later stack's separate 56-case run is prior evidence and is not added to
this unit's count. This bounded result does not establish a complete unit 2
suite pass, validation of units 1/3/4, scientific acceptance or a real native
run. Downstream fresh units must carry the repair through their dependencies;
no downstream merge was performed during this unit 2 task.

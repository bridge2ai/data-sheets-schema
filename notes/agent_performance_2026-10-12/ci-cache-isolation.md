# Schema-digest test isolation after the timing refresh

[PR #5022](https://github.com/bridge2ai/data-sheets-schema/pull/5022)'s refreshed
weights exposed [#5027](https://github.com/bridge2ai/data-sheets-schema/issues/5027).
The Python 3.12 shard 4 [completed job](https://github.com/bridge2ai/data-sheets-schema/actions/runs/38342496007/job/115116774404)
reported 3,768 passed, one failed and three skipped. The identifier-form test
failed the real API guard: the merged schema matched, but its digest did not.
No production schema or cache code changed in that PR.

At the failing [commit](https://github.com/bridge2ai/data-sheets-schema/commit/363714122048ef40b567229158d4995afb7735bb),
the [truncation test](https://github.com/bridge2ai/data-sheets-schema/blob/363714122048ef40b567229158d4995afb7735bb/tests/test_schema/test_datacite_relationships.py#L220-L232)
temporarily set `MAX_ENUM_VALUES=5` and cleared only `_BUILD_CACHE`. It restored
the constant but left the capped text in `_TEXT_CACHE`; that cache's
[key](https://github.com/bridge2ai/data-sheets-schema/blob/363714122048ef40b567229158d4995afb7735bb/src/data_sheets_schema/schema_digest.py#L799-L816)
does not include a test-mutated module constant. Both tests ran on CI worker
`gw0`, with the truncation test first.

The local causal comparison kept the source and actual schema-sync check:

| Fresh serial process | Before-fix result | Pytest duration |
| --- | --- | --- |
| Identifier-form node alone | 1 passed | 41.74 s |
| Truncation node, then the same identifier node | 1 passed, 1 failed with the same digest mismatch | 22.81 s |

The local interpreter was Python 3.12.11; CI used 3.12.15. This difference did
not prevent reproducing the failure, but these timings are not a performance
comparison. [Portable pre-fix receipts](ci-cache-isolation.json) preserve the
exact case identities, counts, failure message, XML durations and raw receipt
hashes without local paths or hostnames.

The correction isolates the test's build and rendered-text caches while its
synthetic cap is active. The test first warms a normal digest, then checks the
specific relationship vocabulary's five retained values and exact omitted
count, and finally verifies the normal text is unchanged. Both cache objects
and the cap restore on exceptional exit. This prevents a warm cache from making
the truncation check vacuous and prevents capped text leaking into later tests.
Production cache keys, schema-sync admission, weights and test coverage remain
unchanged. Post-fix validation passed all 21 occurrences in 55.52 seconds: the
original failing ordered pair followed by the complete affected test file.
Independent static review confirmed other test bodies and production checks
are unchanged.

The first broader local run passed the ordered pair but had two validator
setup failures: inherited `CONDA_DEFAULT_ENV=base` caused Poetry to disregard
the selected virtual environment and attempt a new environment in an
unwritable cache directory. The final run removed that variable, set
`VIRTUAL_ENV` to the locked Python 3.12.11 environment, and put its `bin`
directory first on `PATH`; dependencies and tested source were unchanged.
That first run remains unsuccessful setup evidence. Required final-head CI
remains a separate acceptance gate.

Reproducible metadata helpers are retained at
[`2026-10-12_trace_5022_ci_failure.py`](../../scripts/adhoc/2026-10-12_trace_5022_ci_failure.py)
and [`2026-10-12_trace_5027_cache_receipts.py`](../../scripts/adhoc/2026-10-12_trace_5027_cache_receipts.py).
The first was saved after the initial static diagnosis and does not claim to
have generated its original artifacts. The second reads the completed local
receipts; neither imports project code or runs tests.

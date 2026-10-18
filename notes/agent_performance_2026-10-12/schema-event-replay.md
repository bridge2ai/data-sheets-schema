# Schema admission event replay — #5015

The unchanged complete API pipeline test passed with its measured call phase reduced from **791.641s to 672.876s (15.0%)** in this local comparison. The change removes a repeated YAML parser pass during schema admission. It preserves fresh validation and does not cache catalogs, accepted inputs or verdicts.

`audit_omissions.py` now retains the events from the existing pure-Python SafeLoader depth scan, then feeds the completed stream to the existing UniqueLoader composer, resolver and constructors. Composition starts only after the depth scan completes. This preserves grammar, original error locations, duplicate-key/alias handling, typed scalars and depth-before-composer error precedence. Only the existing schema-validation sites in `_schema` and `typed_audit._capture` opt in; other record and JSON readers retain their original route. Byte, node, root and complete import-closure checks still run on every admission. No schema content or generated artifact changed.

The final retention limit is **131,072 events**, increased from the initially tested 65,536 to provide headroom beyond the current merged schema. The separate retained scalar/anchor/tag/directive limit remains 8,000,000 characters. Overflow releases the retained events, finishes the same depth check and uses the original second parse; a first-pass parser error also falls back to the original loader so it retains the original error precedence. The tradeoff is bounded additional event storage when replay is used and no parser-pass saving for inputs that overflow. These are retention thresholds, not new input rejection limits or exact memory-byte bounds.

| Measurement | Baseline | Event replay |
|---|---:|---:|
| Pytest session elapsed | 799.95s | 680.85s |
| Target call phase | 791.641s | 672.876s |
| `_schema`, 50 calls: cumulative wall | 290.390s | 172.959s |
| `_schema`, 50 calls: thread CPU | 264.773s | 163.985s |
| `api_runner.execute`, 19 calls: thread CPU | 611.313s | 513.468s |

Both runs passed the same target and all three pytest phases, restored profiler bindings and recorded no observer errors. All 5,244 instrumented events retained the exact function/parent/caller/outcome order. Both retained 19 `execute` calls—6 successful returns and 13 expected exceptions—plus 2,341 fresh captures, 2,032 current-state assertions, 50 schema admissions, 123 `version_document` calls and 13 validator calls. The complete target and completed-replay test files are byte-identical. All **seven mutation controls** remain: bundle, context, receipt, rehashed packet, rehashed assembly, usage and lost progress. Bundle/context refuse during RunSpec reconstruction before the `execute` wrapper; the other five appear as instrumented mutation calls. The unchanged passing test and saved source pins support all seven controls; there are not seven mutation `execute` events.

The separate unprofiled real-schema sequence ran old/new/new/old, with imports and initial capture outside timing. Wall times were 4.24485, 2.71025, 2.76681 and 4.26584s: the two-call means were 4.25535s old and 2.73853s new (35.6% lower). Thread CPU was 3.96477, 2.67643, 2.71770 and 4.01206s. All four catalogs were byte-identical after canonical serialization: 1,126,509 bytes, SHA-256 `3848a20966d6fc0531ab6d306f9ad353153ecc29f6ab99f8d4a901538e226c3d`. Source preservation and restoration checks passed.

Validation status at this report revision:

- Initial focused suite: **126 passed in 10.19s** at the 65,536-event default, including 44 new equivalence cases covering original error causes, late depth/parser errors, forced retention overflow, alias identity, fresh objects and genuine schema closure/catalog behavior.
- Final controls at 131,072 events: **54 passed in 18.46s**. These comprise 44 event-replay cases and 10 selected portable/freshness/native-context/deferred-owner cases.
- Unchanged complete pipeline and four-call admission comparison: **passed**. Project runtime was serial; independent reviewers used static source and completed metadata only.
- Adversarial source review and independent byte-identical report recomputation: **passed**. Complete PR CI remains required. The separate saved-response recovery integration was not repeated locally and remains covered by that full CI gate.

The earlier catalog-cache candidate is archived in `schema-catalog-5015-withdrawn01` and withdrawn. Its matched pipeline observation did not demonstrate material gain: 791.641s to 780.924s call phase, while schema thread CPU rose 264.773s to 272.270s. Its two production and two test deltas were preserved externally before restoration; the repository's original bounded derivation cache and tests remain. Event replay avoids carrying that additional catalog-cache complexity.

Receipt limits remain explicit. The candidate has contemporaneous before/after pins for the two changed production files and two complete test files. Instrumented modules also have installation-time hashes. No separate baseline after manifest was supplied. Baseline `pyproject.toml`/`poetry.lock` hashes match later current files, but the candidate's pre-run manifest did not include them; no historical snapshot was fabricated. Root retained the same locked virtual environment/interpreter, while the report itself verifies executable/Python identity rather than a full environment inventory. The historical `/usr/bin/time -l` sandbox error followed a passing baseline test and is not its pytest outcome.

These are two local profiled pipeline observations and four unprofiled admissions, not a statistical significance or universal throughput claim. Host load was high; wall time is contention-sensitive. Thread CPU excludes child processes, nested cumulative times overlap, and process high-water RSS is not an isolated per-call allocation measurement. Timing provides no scientific-quality, model-exposure or generation-completeness claim.

The reusable helpers and their purpose/input/output/date/issue headers are retained in `scripts/adhoc/2026-10-12_5015_pipeline_profile`, `2026-10-12_5015_schema_profile01`, `2026-10-12_5015_schema_abba`, `2026-10-12_5015_schema_report` and `2026-10-12_performance_metadata`, identically in the primary repository and task branch. Historical helper sources/configurations and migration hash/AST joins are retained. Profiler implementation and actual invocation provenance remain separate evidence joins from the comparison helper.

The [portable machine-readable comparison](schema-event-replay.json) (original artifact `schema-event-replay-comparison01.json`), SHA-256 `2947eca2600e25b48923850480563f001212b263cd553eb8a80b35b07666c1be`, contains individual source/evidence hashes, exact control sequences, timings and preservation coverage. Merge acceptance is tracked separately in issue #5014.

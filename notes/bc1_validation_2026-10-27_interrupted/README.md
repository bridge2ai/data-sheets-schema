# Interrupted BC1 validation evidence, 2026-10-27

The original source-frozen BC1 batch at
`17ca65b0a00f8f3c665e1f7d343b93b121176320` was interrupted with SIGINT sent only
to its identified child PID85974. Pytest reports **106 passed, 12 failed**;
the public pipeline was incomplete, and four resource tests were not reached.
All twelve failures came from the test client's missing `stream` interface,
subsequently corrected and independently verified in the runtime fixture branch.
No pass is inferred from the unnamed interruption entry in JUnit.

The original driver completed both origin checks and confirmed unchanged
tracked source. Pytest exit was 2; the attestation wrapper exited 1. The log
reports 3,282.66 seconds while the driver's outcome records 2,827.08 seconds.
Both are preserved verbatim; this is not an idle-host performance measurement.
Outcome SHA-256:
`ae927198f2d87df83d0c7dd2e10a74fd5e5a19a1844fe7bd87da8c92bb428a5a`.

The interrupt landed in `yaml/scanner.py:279`. A preceding one-second macOS
native-stack sample is preserved as `process-sample.log`, SHA-256
`5b15756977322a8efc65427a7ff09127e536342af181aa676cf7b1bf9f4146b9`.
Neither observation proves an algorithmic hang or a sole bottleneck.

The committed helper `scripts/adhoc/archive_n2_restack_validation_20261027.py`
archived selected JSON/log/XML results, verified byte/mode round trips and
unchanged originals. The complete synthetic case tree remains external at
`/private/tmp/d4d-bc1-validation-20261027/17ca65b0a-bc1/cases`.
Manifest SHA-256:
`b8437e9b1000c533c928074ea630fd57d1a5c57ddb4360e14d570a3af2b1e180`.
This archive does not certify completion, scientific validity or installed hooks.

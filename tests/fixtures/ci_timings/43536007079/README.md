These are lossless gzip copies of the downloaded ordinary-shard JUnit from
run 43536007079 at commit 6ed891e845c1a46282338794dadb342a6fa6f261. Only shards
whose retained job metadata reports success are included. The overall run
failed; these fixtures do not establish successful CI for that commit.

`scripts/adhoc/refresh_ci_capacity_timings_20261114.py` creates these files,
checks decompression against the originals, removes dedicated cases in scratch
XML, and invokes the unchanged timing updater. The active duration file retains
the original and filtered hashes, excluded node IDs and previous complete map.
`tests/test_ci_timing_update.py` pins the raw XML hashes and reconstructs sums
independently from these fixtures. No external artifact access is needed in CI.

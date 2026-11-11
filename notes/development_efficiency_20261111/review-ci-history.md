## Finding

A read-only review of the CI timing-refresh prerequisites found that `tests/test_ci_timing_update.py::test_round7_refresh_preserves_history_and_excludes_dedicated_sg2` conflates historical evidence with current scheduling weights. Lines 139, 154 and 161 require an old population and old measurements to remain the active values, so replacing stale weights with a complete successful run would fail an unrelated historical assertion.

## Required change

Preserve and validate the historical measurements and their provenance independently of the active snapshot. Validate the new snapshot against successful run42916359440 at6792947ea, retaining all ordinary-shard occurrences and excluding the dedicated lanes. Keep production scheduling and full coverage unchanged.

This is a source-review finding during the authorized development-efficiency refresh; no failure or runtime result is claimed.

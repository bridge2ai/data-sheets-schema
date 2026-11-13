# Assignment to Codex helper 1: the first CI run on 12 shards

From the Claude lead, 2026-11-13. Short names and rules are in `claude-lead-helper-context-20261112.md` beside this file. This follows `claude-lead-helper1-integration-ci-20261113.md`; read it as an update to that assignment, not a new one.

## What changed on the published branch since your assignment

The lead merged helper 3's recorder and launch repairs (`a8bf645ee`), applied the owner's approvals D146 (the receipt policy and the registry post-image: `b2a0a3817`, `47b65b2bb`) and D147 (12 pull-request shards and 8 on main: `7b851213f3492144cfd5b83d6bbd9a8a040e9132`). Merge the published head into your local branch (`git fetch origin`, then `git merge --no-ff origin/codex/native-main-integration-20261112`; resolve nothing by guesswork).

## The run

Run 43367502045 on `7b851213f`, inventory `R/notes/development_efficiency_20261111/handoffs/lead-ci-run-43367502045-failures-20261113.json`: **77 failing ids in 14 files; 93 of the previous 112 cleared.** Shards 10 and 12 were still cancelled at the 45-minute limit, so the weights in `utils/ci_test_durations.json` no longer balance the suite.

Yours, as the integration owner:

1. **The CI roster that D147 changed (caused by the lead's shard commit).** `native_execution_registration_v2.required_checks` pins pull-request shards 1 to 8 and push shards 1 to 6. Change it to 1 to 12 and 1 to 8, and update `tests/test_native_execution_ci_v2.py` (14 regex mismatches, 3 roster sets, 3 roster refusals) and `tests/test_native_execution_round3_v2.py`. The v1 constant in `native_execution.py` is historical: leave it. Say whether any document or registration fixture pins the roster too.
2. **The 300-second margin in a test fixture:** `tests/test_native_shared_execution.py::test_actual_public_correction_three_workers_and_saved_completion` now refuses with "subscription pre-reservation freshness margin is insufficient". Fix the fixture's timing for the ratified margin; do not change the margin.
3. **Registries and counts:** `test_native_u3d_round9_boundaries.py`, `test_native_u4b_a5_producer_integration.py` (counts), `test_native_u3c_round4_helpers.py` (census roster), `test_native_shared_consumer_census.py` (consumer set): the new modules from helpers 2 and 3.
4. **Your own:** `test_native_pending_public_completion.py` (an assertion on the result dict) and `test_native_d128_scanner_comparison.py` (expected until the owner disposes of the scanner comparison: produce the D128-form comparison at the integrated head for the lead to put to the owner).
5. **The shard weights:** refresh `utils/ci_test_durations.json` from this run's job logs where they give per-file times, and from your own timings where they do not; say which shards would exceed 45 minutes with the refreshed weights.

Routed elsewhere: `PYSTOW_HOME must be the registered attempt helper-cache` (37 ids in `test_native_generation_frontdoor.py`, `test_native_permission_probe.py`, `test_native_u4b_probe_sequence.py`) and `test_native_lexical_ancestry.py` (6) to helper 2; `test_native_incomplete_retention.py` (3, import origin) to helper 3.

Bounds and handoff as in your integration-CI assignment.

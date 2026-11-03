# W7-BC1-CACHE-01: extracted formatter missing from cache dependencies

2026-10-30. Local issue; GitHub filing is deferred by the offline task rule.
This is a confirmed integration defect, not a new scientific-condition choice.

**Original evidence.** Packet `07700a4c70fcd9f842d4d51086c2dd6ec39958ce`,
private proposal-applied archive `28a2d625d6224d4848303197f0739daecacb43e3`.
The unchanged standard validation canary passed 1/1. The unchanged regression
`tests/test_wave7_bc1_formatter_cache.py::test_changed_extracted_formatter_cannot_reuse_a_warmed_bc1_entry`
then failed 1/1 at line 22: the cached path did not raise after only
`audit_omissions._render_prepared` was replaced with a distinctive refusal.
Before replacement, warmed, repeated and uncached outputs matched. After
replacement, the uncached path raised the expected refusal. Source, imports,
hygiene, OS network guard and exact node accounting all passed.

Evidence is retained under
`d4d-executions/plans/reviews/wave7_resume_2026-10-30/bc1-original-cache-01/`:

- `outcome.json`: `1fd24a317573fa4b48edbd769afe50615283d4b4eaa9f3071401c6ee978f66a3`.
- `pytest.xml`: `632847d6df175c7db4db2693935ec024d7fb190b0e60cf8263523fb1954a7f50`.
- The original canary outcome is `6f27d59dc4549d67e0890612bd39b0d6cc136e021e57e980ee9b73e38c913006`.

**Cause and bounded repair.** F6 preserved argument propagation but A17's
extracted formatter was absent from BC1's enumerated pure-function dependency
roster. Add only `_render_prepared` to that roster in `bc1_audit.py`. Existing
refresh logic then rejects stale runtime dependencies and clears both optional
pure caches before entering the uncached validating path. No response verdict,
source coverage, scientific gate, production limit, protected file or cache
policy is weakened. The regression itself stays unchanged.

**Status.** One-line repair prepared; independent review and replay on a fresh
archive are pending. Preserve the original failure and original archive.

Independent read-only review confirmed the one-line repair (source SHA-256
`0e43a00224aa994b765ebc22746a92d044e864ea241f93bcffb8fa2a6b77b572`),
the causal failure trace and unchanged regression bytes
(`ae3c10f8194c7b2d76979849b41f2cf681c5b02f1883c0e49b55e56b1c33f332`).
No additional source change was suggested; fresh-archive replay remains pending.

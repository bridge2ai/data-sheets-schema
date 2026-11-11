# #5867 fixed singleton selections (preparation only)

Delta from `5a14c6de8cc80099053448e46e76788f225a58e2`, 2026-11-11.
The separately verified v3 canary took 6.87306175 s; the lead held the old
2–4-case groups and authorized this minimal split. No new test run, collection,
import, compile, sandbox probe or genuine diagnostic was performed.

All **19 cases** remain: canary1, values4, inputs3, direct4, margin2,
admission4, lease1. Every fixed selection now names exactly one pytest case.
Multi-argument parametrizations gain explicit stable IDs; argument values,
fixture bodies and all assertions remain unchanged. Single-argument value
IDs remain current/fresh/both. JUnit matching now requires exact class and
case names instead of accepting a family of bracketed cases.

Every selection expects one successful scripted capture except the lease case
(zero captures) and the two poison cases (two captures, exactly one failed
capture with successful peer exit). Thus the complete proposed roster retains
20 captures, including two intentional failed captures. Capture lifecycle,
bytes/hash checks, supervisor, Git/peer allowances, credential isolation,
network denial and 10s work plus20s cleanup/30s acceptance criterion are unchanged.

Evidence moves to the exclusive fresh
`scratch-native-postaccept-fusion-v4-20261111/` root, checked absent including
symlink lookup. V1/V2 failures and the v3 pass remain intact. The changed helper
and test hashes require a separately released v4 canary before any affected
case. No old result can satisfy the same-source gate and no selection fans out.
This is source preparation, not a passing execution/collection claim.

| File | SHA-256 |
|---|---|
| scripts/adhoc/run_postaccept_fusion_checks_20261111.py | `8a5f5c3877e0674d3817e3c39660d3475a9848ca56015587eea876fc839954d7` |
| tests/test_native_u4b_a3_reservation.py | `2880785a41a075ea2e955ae372fbfa8db364ad6bd5ef9d5c0d39ccb3e10fd478` |

Production and unchanged deadline identities remain those recorded by the v3
result. The source/helper whitespace check passes. Stop for independent delta
review and an explicit new canary release; no affected-case execution is inferred.

# N2 unit 2: default controller and receipt-to-record recovery

Base: local unit 1 `44deb5220`, descended from cached `7c1002cae`.
Recovery source: pre-owner `a33d80d84`, using `286b88688` as the common
ancestor for existing-file merges. This is offline engineering only; no
provider call, live native binary probe, GitHub command or push was used.

The branch restores the default selected native controller, capture, helper
stages, independent saved readers, permission/subscription libraries, and the
receipt-to-record CLI adapters. API receipt registrations v1/v2/v3 keep their
existing route. Native original receipt history is separate from the effective
receipt used by final counts. The core derivation adapter carries the selected
schema identity through the current source-spelling helper.

The four current legacy native modules (`native_execution`,
`native_execution_registration`, `native_execution_gates`,
`native_attempt_supervisor`) are retained byte-for-byte from `7c1002cae`.
New default entrypoints use their extracted engines and current legacy effect
and lifecycle helpers. The current receipt-origin path, alias, sealed-snapshot
and final publication size safeguards are preserved; native shared origin adds
only its separate family/effective-receipt reporting. No owner-profile module
is recovered. `native_execution_authority` keeps the current whole-package
source roster. Protected shared-generation and canonical-hash files are intact.

Captured omission/schema support combines the current bounded schema-event
reader with the pre-owner captured-asset and logical-schema route. Typed cache
recovery includes `2a9c60d43`: opened and derived products share the bounded
serialized store. Its tests preserve the literal historical producer, the
explicit target-S7 compact worker payload adaptation, and the original four
instance-attribute assertion. Permission encoding/digest reuse is recovered
from `123a73431`, adapted only to the pre-owner `_trace` signature. Production
permission checks still run on each call.

`scripts/adhoc/recover_native_default_unit2_20261025.py` records the initial
98-path recovery and conflicts. `resolve_native_default_unit2_20261025.py`
resolves the current/legacy boundary and independent schema conflicts.
`recover_native_pure_fixes_20261025.py` recovers the bounded cache and pure
permission fixes. Subsequent narrow manual edits are visible in this branch:
selected core-header identity, native-origin integration, current final-size
preflight, missing-format refusal, and an inherited test's explicit offline
provider fixture. The initial recovery manifest records incoming blobs and
conflict results, not the final reviewed source hashes.

Exploratory validation: compilation passed; the typed-cache/captured-assets,
omission-event and engine/gate group passed 81 tests. This exploratory run
overlapped source edits and is not the frozen-head acceptance result. An earlier
receipt-dispatch run exposed a missing imported offline provider fixture in
the recovered test; the fixture now matches the synthetic registration. That
run was interrupted after retaining the diagnostic. Frozen-head focused tests
are required and will be reported separately. The 900-second fake execution
acceptance, real-binary probe and registered canary are not claimed here.

The cached base has D32 documentation, not the later A12/A13 implementations.
Their subsequent integration/rebase remains explicit work for the orchestrator.
Scanner compatibility, probe producer/front door and 900-second acceptance
belong to later units in the series.

Frozen head `0d5bddbc0`: **310 passed** in 422.26 seconds across the 14-module
receipt, derivation, provenance and origin regression group. This includes the
existing API receipt/floor, backfill and core-derivation tests, plus actual
offline legacy/direct/native registration and pure stage-to-origin joins.
The log is `native_n2_validation_2026-10-25/receipts-0d5bddbc0.log`.

Review finding N2-R1 is recorded in `native_n2_review_issues_2026-10-25.md`.
Its new mutation test failed before the correction; the corrected schema-event
guard and broader dependency/native typed-catalog tests passed 73 tests.
The frozen 310-test run precedes that narrow cache correction; later focused
cache results cover the changed boundary explicitly.

The later permission preparation recovery is deliberately limited to
`13d4c6077`'s `_view_factory` / `_view` / `projection`, `87dfe8208`'s
per-trace view factory and fresh classifier calls, and `6f016c25f`'s permission
isolation-root / default registration lexical ancestry calls. Unit 1 already
supplies the exact lexical helper. No owner reconstruction or stream
coordination changes are included. The helper and JSON manifest
`recover_native_permission_preparation_20261025.py` /
`native_n2_permission_preparation_2026-10-25.json` preserve exact patch/source
identities. The inherited projection and lexical oracle tests remain intact.
Final frozen-head tests follow this separate performance commit.

Final source head `f719de581`: **267 passed** in 67.86 seconds. This covers
the restored 13-view / 25-classification pure projection oracles, lexical
ancestry parity, permission encoding/digest scope, target parser mutations,
bounded typed cache (including the unchanged four-attribute assertion), and
default controller/prompt/stage behavior. Exact module rosters and logs are in
`native_n2_validation_2026-10-25/README.md`. The 900-second acceptance remains
pending in unit 4. Unit 2 introduces no provider calls or launch authorization.

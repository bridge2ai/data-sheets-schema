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

# U3-C round 5: verified projection lifetime

The round-4 instruction to keep A's loader unchanged came from the **lead's
brief**, not from the owner. The external round-4 STATUS attribution was wrong.
Round 5 records that correction while retaining the historical evidence.

Merge `93cb9103a2ab24b4109d56770a1ad1bcdb1986b8` has parents
`834cd93604c33a64efa24e76d5984b06cfa09e67` and
`a6edb1c2df9095e436df00acfc7f8e2a14229328`. It required no manual conflict
resolution. The three automatic overlaps were:

- `notes/native_authority_v2.md`: both units' appended records are retained.
- `scripts/adhoc/run_native_u3a_tests_20261107.py`: A5's assigned scratch is
  retained alongside C's existing quiet-lock polling; the C wrapper still
  overrides the execution scratch and child entry point.
- `native_execution_authority_v2.py`: A5's scoped verified module set and
  physical-path import handling are retained alongside C's 28-module roster.

C orchestration now obtains the projection class and private mint ledger through
`loaded_verified_package_module`, within the real historical helper lifetime.
The scope stays open until the consumer returns, and the carrier is revoked
before scope exit. Source-loaded controller/policy consumers share the same
verified module set; ordinary imports are not projection authorities. The fixed
A entry still carries `classifier_projection` unchanged. No consumer check is
weakened, and C does not modify A's loader, control map or guard.

The selection carrier also has an exact class check. Orchestration recaptures
selection, runtime and instruction through source-loaded producers in that
verified module set, compares every nested dataclass value with the original
capture, and temporarily binds those same-scope captures to the spec. A `finally`
restores the original two spec attributes; returned orchestration captures keep
their prior identity. This does not synthesize a carrier or relax a type check.

The new handoff regressions retain a genuine positive and distinct negative
cases for an ordinary-import mint, forgery, expiry, and changed source bytes.
The source-change case edits an exact scratch copy, never the checkout.

The protected U1 shared-admission hook is outside this round and stays pending.
No integration into D, native execution or admission is claimed. Detailed
validation and any review findings belong in the external Round 5 report.
GitHub issue publication remains deferred by the explicit offline restriction.

## Local review and validation findings

- **C5-R1 — addressed before repeating the canary.** A5's expanded lint rejects
  an `ast.Name` whose spelling ends in `modules`. The first genuine canary
  stopped at the inert `_PureControls.__init__(modules)` parameter, before minting.
  Renamed that plain mapping parameter to `projections`; no import, reflective
  operation, consumer check or guard changed. The failed invocation is retained.

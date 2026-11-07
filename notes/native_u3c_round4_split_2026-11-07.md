# U3-C round 4: consumer and orchestration boundary

This local integration candidate starts at `1e784ed9101d4f43e6115ca60d4f0ebc14dae308`
and merges A round 4 `26a8632d9fba325dd6c9463b84f5281ebfffa64e` in
`ea1689e96372da5d5d33f40ba6b02103012f9a3d`. It does not include later C round-3
commits or merge into D. No native execution authority is claimed.

The consumer modules contain captured-wire parsing, explicit-input composition,
classification, attribution replay, stage decisions and trace reconstruction.
Live preparation verification, loader entry, callbacks, fresh evidence reads
and durable publication use the corresponding `*_orchestration` modules.
The stage consumer is now `native_shared_stage/__init__.py`; its CLI is
`native_shared_stage/__main__.py`, preserving the exact registered `-m` command.

The six pure protocol functions are source-loaded with a closed member/signature
inventory and checks before and after calls. Successful frames, digests and argv
are compared byte-for-byte with pinned historical sources. Unknown contracts
raise `ValueError` with the historical text, rather than importing the historical
`BudgetStop` class into the pure module. Exception-class identity is not claimed
as parity.

`native_shared_render._runtime` now obtains `ROUTE` and `RUNTIME_KEYS` from
`native_shared_runtime_constants`. This is the authorized U1-file change to list
in the combined U1+U3 PR body. Frozen v1 and U2 sources are unchanged.

The only A-authority edit is `CONSUMER_OWNED_MODULES` metadata. A's map, guard
implementation and source loader remain unchanged. The current blocker is
**C4-PROJECTION-LIFETIME**: a genuine C projection becomes foreign to a fresh
consumer's exact class and private mint ledger after A reloads the package.
`tests/test_native_shared_projection_handoff.py` retains a real positive
requirement without a stand-in, skip or xfail. The proposed narrowly bounded
loader exception is in `native_u3c_projection_lifetime_ruling_2026-11-07.md`;
it is not implemented or authorized by this note.

D's later integration must adopt C's explicit verified-capture reconstruction
arguments, pass the genuine classifier projection unchanged, and route live
calls to the orchestration modules. Passing a source-graph census proves import
closure only; it does not resolve the projection lifetime or establish complete
execution admission. The protected U1 hook remains pending.

## Offline review ledger

- **C4-PROJECTION-LIFETIME — pending ruling.** Real source reload invalidates the
  original class and private mint ledger. Keep the strict refusal; do not accept
  look-alike mappings, carrier-provided validators or ordinary cached modules.
- **C4-R1 — reviewed, no new finding.** Independent read-only inspection of the
  controls split retained exact class/mint/member/source checks, checks around
  helper use and lifetime revocation. Partial-mint failure now revokes accumulated
  projections as well. This is not a positive cross-loader handoff result.
- **C4-R2 — reviewed, no new finding.** Independent read-only inspection of the
  attribution split retained saved instruction/full/report joins and fresh live
  composition comparison. Neither consumer imports the bootstrap boundary.
- **C4-R3 — addressed.** Independent read-only controller review found stale
  policy documentation claiming it accepted no caller-supplied commands. The
  new input-only boundary accepts independently derived argv/directories from
  trusted orchestration; the docstring now states that precondition precisely.
- **C4-R4 — reviewed, no new finding.** Independent protocol/runtime review
  checked both historical source hashes, byte formulas, member/signature/source
  checks and the single render import change. D's actual permission inventory
  integration remains separate from these C tests.
- **C4-R5 — addressed before execution.** Root review of the diagnostic census
  found the old stage-module path and an incomplete consumer list. The helper
  resolves module/package paths and includes the new pure C/D modules; this is
  diagnostic plumbing, not a change to A's guard.
- **C4-R6 — addressed after the first census.** Full-body lint correctly rejects
  an imported `FunctionType` constructor in a consumer, even when this file only
  used it as a type predicate. The consumer now uses the standard-library
  `inspect.isfunction` predicate for that exact test; it neither constructs code
  nor imports a constructor under another spelling. A's guard stays unchanged.
- **C4-R7 — addressed before suite execution.** A path migration had changed a
  scanner test whose synthetic fixture still creates a `.py` module. Restored
  that original assertion and removed the unnecessary migration; its existing
  closure helper already understands both modules and package initializers.
- **C4-R8 — addressed after the first full C suite.** Two stream test modules
  still imported the moved callback class from the consumer. Two saved-attribution
  tests (six cases) still patched the moved live reader there. The test imports
  and reader traps now target orchestration; all adversarial assertions remain.
- **C4-U1-HOOK — inherited, pending protected integration.** The unchanged
  `test_native_construction_and_replay_use_validated_shared_admission` expects
  two native calls to `shared_generation.select`; the unchanged RunSpec entry
  deliberately skips that selector for the native route. `api_runner.py`,
  `shared_generation.py` and this test are identical to the requested C4 base.
  Its assertion remains unchanged; this task does not authorize that hook.
- **C4-R9 — validation attempt retained, not accepted.** The first migration
  canary passed its test, but an evidence-helper-only edit changed the working
  tree while it ran. The runner returned 125 on source stability. Production
  bytes did not change; repeat the canary on the committed frozen helper state.

GitHub issue publication is deferred under the explicit offline/no-GitHub rule.
Detailed test results, graph census and remaining failures belong in the Round 4
section of the external review report after validation.

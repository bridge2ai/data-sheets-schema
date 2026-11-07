# U3-C R4: projection lifetime requires a narrow A-loader ruling

Status: **proposal only; not approved or implemented**. Date: 2026-11-07.
Finding: **C4-PROJECTION-LIFETIME**. Worktree: `codex-native-u3c-r4`, branch
`codex/native-u3c-interface-20261107`. No production or test changes accompany
this note. Independent C splitting and the six-function protocol can continue;
positive projection handoff remains an executable integration requirement.

## Why the approved pass-through parameter is insufficient

The inspected baseline is `1e784ed9101d4f43e6115ca60d4f0ebc14dae308`.
Its `native_shared_controls.py` SHA-256 is
`e08ecd63c5c3ae647a9daf34ecb4943e85809ddcb346bfe26994fd19abdebe5b`.
`require_controls`, lines 99–115, requires both exact local `_PureControls`
identity and membership in that module's private `_LOADER_CONTROLS` weak ledger.
It then verifies each original projection object's identity, roster, source
pins and active lifetime. Construction of an equivalent map or carrier alone
does not mint it.

The inspected `native_execution_authority_v2.py` SHA-256 is
`181b3e075b2ee46be21a5771ee033fd699b50c34ab0f7dc36296498441d18ed9`.
Its `verified_source_module(..., package_sources=...)`, lines 370–399,
evicts and recompiles every package child, including C's class and ledger.
Consequently, a genuine carrier minted before A's reconstruction call fails
the fresh consumer's exact class and mint-membership checks. Passing the same
object unchanged through A does not preserve the defining module's identity.

There is no safe correction within the current instruction to leave A's loader
unchanged. Matching class names, filenames, source digests or code objects does
not authenticate the original mint ledger. Calling a validator supplied by an
otherwise untrusted carrier is self-authentication. Accepting such fallbacks
would weaken the current constructor and look-alike refusal guarantees.

## Proposed stable identity module

Introduce one self-contained, pure C module, provisionally
`data_sheets_schema.native_shared_projection_carrier`, at the fixed path
`src/data_sheets_schema/native_shared_projection_carrier.py`.
It holds the exact carrier/projection classes, fixed member rosters and private
weak mint ledger. It imports neither A nor frozen v1. Its actual committed
SHA-256 must be recorded in the selected package-source closure; this proposal
does not invent a digest for a file that has not been implemented.

C orchestration opens A's existing source-only loading context for that exact
module and selected bytes, obtains the genuine helper projections, and mints
the carrier within that lifetime. It then calls A with the unchanged carrier.
The consumer imports the same identity module and applies the existing exact
class, mint-membership, member-identity, source-pin and lifetime checks.
Only the ordinary consumer modules around that identity module are recompiled.

Helper source checks still run before and after each helper invocation.
The trusted C minting path may retain its already-bound source attestor in
private mint state; it must not accept an attestor, ledger, class or identity
claim from the supplied carrier or serialized input. Those checks run only
after the anchored exact class and private ledger have authenticated the
carrier. Their detailed implementation needs adversarial review: the preserved
module does not turn a caller-selected callback into authority.

A continues to forward the projection unchanged. It neither interprets its
fields nor constructs or serializes it. The proposed A bookkeeping concerns
active source-module contexts only, not projections or their verdicts. A's
public two-entry control map, import guard, frozen sources and source-only
compiler remain unchanged.

## Exact A exception requested

The following references are to the pinned A source identified above.

1. Keep graph construction and captured package sources at lines 353–376
   unchanged. Afterward, before building/removing bindings at lines 378–399,
   consider preservation of **only** the fixed identity module named above.
   Do not accept a caller-supplied exemption list or a general cached-module
   fallback.
2. Preserve it only when all conditions hold:
   - An enclosing, still-active `verified_source_module` context compiled or
     explicitly borrowed this exact module object from verified source bytes.
   - The existing `_SOURCE_MODULES` record recognizes it, and
     `module_source_identity` validates its loader, path, cache state and own
     callable identities/code. A record surviving after context exit is not
     sufficient; add explicit active-source-context bookkeeping.
   - The current `package_sources` contains the fixed path with the exact
     selected digest, matching that active module's source identity.
   - `_verified_source_bytes` freshly proves the current physical file still
     matches that digest. There is no bytecode or ordinary import fallback.
   - The canonical module binding and its package-parent attribute are the
     exact active object. A replaced or missing active binding refuses.
3. At lines 395–399, exclude that eligible binding and parent attribute from
   eviction. Every other pinned and unpinned cached package child retains the
   present eviction/recompilation behavior. Keep the module in `sources` and
   in the initial identity snapshot at line 402.
4. Preserve the ordinary post-yield identity/binding checks at lines 404–412
   and additionally reread the identity module's physical source against its
   selected pin before completing the borrowed scope. Any changed source,
   callable, loader or binding refuses; do not reload or mint a replacement
   to make an in-progress call succeed.
5. At lines 413–426, borrowed scopes restore only their own other bindings and
   retain the enclosing identity module. The outermost source context restores
   the exact pre-context module and parent bindings, paths, finder and bytecode
   policy, and removes its active-module eligibility.

The existing `_VerifiedBytesFinder`, lines 296–319, needs no exception to its
v1/bootstrap refusals or source compilation. A legitimate preserved module is
already the verified, active binding; every other import follows the current
finder. An ordinarily imported module, stale source-loaded module or forged
cache entry is not eligible for preservation.

## Nested contexts and invalidation

Track active module contexts with explicit nesting, not a permanent cache.
A same-pin nested request borrows the same exact identity object. It must not
recompile the module and strand an outer live carrier. A request for a different
path, digest or object while the identity context is active refuses before
changing bindings. Out-of-order closure must fail closed rather than silently
restore a different identity into a still-active consumer scope.

Each C minting context owns its own ledger entry. Closing an inner context
revokes its carriers without revoking an enclosing context's distinct carriers.
C's `finally` removes its entries and deactivates its projections on normal
return and exception. Once the outer A source context closes, the module is no
longer eligible for preservation. A later invocation compiles a fresh identity
module; a retained old carrier fails its constructor/ledger checks.

Source or callable drift causes refusal, never an automatic refresh. After a
failed handoff, cleanup/restoration must still run. A later attempt must satisfy
fresh source and active-context checks; a previous passing verdict is not reused.
This preserves the existing scope of the proof: reviewed source, current own
callables and checked member state, not a sandbox against arbitrary privileged
Python reflection or mutation of all interpreter globals.

## Required acceptance and regression evidence

- Real outer source load, genuine C mint, A's unchanged-object forwarding and
  a freshly compiled consumer: consumer class/ledger identity remains exact,
  classification succeeds, and the returned object is the original carrier.
- Plain mapping, equivalent manually constructed carrier, copied projection,
  forged class with matching names/code, caller-supplied ledger/validator, and
  expired carrier all refuse. None is promoted by the loader exception.
- Same-pin nested scopes preserve identity. Inner closure revokes only inner
  carriers; outer closure revokes outer carriers. Test exception paths,
  out-of-order closure and restoration of prior parent/module bindings.
- Wrong/missing source pin, path substitution, changed physical bytes, changed
  callable, changed loader, replaced binding and stale source-module records
  refuse before consumer use. Mid-call changes refuse on completion too.
- A source-loaded module with no active enclosing context cannot claim the
  exception. A normal cached module and a forged valid timestamp `.pyc` remain
  ineligible. Retain all R3 cached, unpinned, deferred and v1 import regressions.
- Existing C tests for exact member rosters, original object membership,
  source-pin changes, post-call mutations and closed lifetimes must still pass.
- Confirm the whole package graph, including this new pure module, remains
  pinned; no A/v1 consumer import or dynamic-import workaround is introduced.
  Run A and C suites, the guarded-source census and the actual bytecode probe
  under the prescribed offline runner before claiming the integration gate.

## Proposed ruling question

May implementation introduce the fixed pure C identity module and the narrowly
bounded active-source-module preservation in `verified_source_module` described
above, with independent review of the A-loader change and all listed regression
gates, while leaving A's control map, import guard and carrier pass-through
semantics unchanged?

Until that exception is explicitly approved, preserve A's loader as-is and
report C4-PROJECTION-LIFETIME as an unmet integration gate. This note grants no
implementation, merge, execution or native-canary authority.

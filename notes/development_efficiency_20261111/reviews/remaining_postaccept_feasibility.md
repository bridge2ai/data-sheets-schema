# Remaining post-acceptance verification: bounded feasibility finding

2026-11-11. Source-only review of clean native commit
`382f0dfd1ce863fdf257a77e2bbb2637dbe2f67b` in `codex-native-u1u3`.
Read the prior `handoffs/private-postaccept-design.md`, the rejection record
`review-post-acceptance-design.md` (#5836/#5837), and the actual current producers.
No imports, tests, source edits, runtime or worker contact.

**Conclusion:** no smaller equivalently guarded replacement is established by
these existing helpers. A private launch-local check remains the appropriate
wiring boundary, but preserving the actual fresh derivations currently returns
to the full verifier. This is a precise implementation limit, not a request for
new attestation infrastructure. Track the remaining structural work in [#5722](https://github.com/bridge2ai/data-sheets-schema/issues/5722)
and the live-launch authority boundary in [#5836](https://github.com/bridge2ai/data-sheets-schema/issues/5836);
no duplicate issue is needed. This work is not an additional
prerequisite for the already scoped final D4D generation.

## Current call graph

After `accept_current_selection`, `native_execution_orchestration.py:369–388`
has **three**, not four, full registration-verification cascades:

| Boundary | Current path |
|---|---|
| Join | `_join_subscription_authority` → `native_subscription_admission.context` → `read_capture_for_event` → `_authority` → `registration.verified`. Capture A already replaced the inner duplicate with `_recheck_authority` → `_recheck_verified`. |
| Unchanged | `native_shared_execution_orchestration._unchanged` (37–45) → `registration.verified`, followed by committed-source, authorization-byte and host checks. |
| Lease | `native_subscription_capture.capture_admission_lease` (457–469) → `_current_authority` → `_authority` → `registration.verified`, then the journal lock/require operation held through `mkdir`. |

The full call is `native_shared_registration_orchestration.verified` (129–139):
fresh dependency identity and `loaded_controls`, then
`native_execution_registration_v2.verified` (475–534). Its indispensable producer
steps are:

1. `_wire` (176–192) checks the envelope through currently loaded pinned helpers.
2. `verify_preparer` (375–400) calls the profile-selected real preparer, rebuilding
   the guarded RunSpec, instruction, render specification, input identity,
   outputs and pins from current captures.
3. `_consumer` (403–433) freshly reads/checks the source graph and loads the fixed
   consumer. `rebuild_v2_body` then receives only original preparation bytes and
   primitive input arguments, with the live classifier projection.
4. `native_shared_registration._selection` (73–138) reconstructs rendering,
   composition, policy and toolchain. `_registration_body` (240–290) recomputes
   effective system text, permission expectations and saved-probe acceptance,
   command, environment and optional receipt origin. The complete reconstructed
   body and dependency identity are compared again before returning.

## Exact gap in the cheaper alternatives

`_recheck_verified` (registration orchestration, 142–269) is useful for capture
A's bounded inner recapture: it retains fresh selection/resource traversal,
source/runtime/pinned-byte checks, path checks and bound runtime observations.
It does not freshly produce all the derived fields above. Adding only
`verify_preparer` would repair preparation coverage but still omit policy,
permission expectation/observations, effective system, argv and environment.
Calling `_selection` alone also omits the later registration-body production.
Calling the actual `rebuild_v2_body` under `_consumer`, plus preparation and
outer comparisons, reproduces the current full verification rather than a
supported smaller replacement.

The existing controls are real guards, but have a narrower contract:
`native_shared_controls.require_controls` (100–116) checks exact mint/lifetime,
roster and selected helper members. `module_source_identity` (authority,
584–604) explicitly checks source provenance and own callable code, not arbitrary
interpreter globals. Neither establishes a reusable complete preparation/render
producer-state boundary. For example, fresh instruction rendering calls current
`shlex.join` (`native_shared_render.py:379–380`); equal source pins do not establish
an unchanged result after that dependency changes.

Keeping a consumer open across the join/unchanged/lease orchestration is not a
free replacement: it changes module bindings and the active import finder.
`verified_source_module` (969–1103) defines that lifetime and restores bindings;
its finder rejects bootstrap-boundary imports (893–918). The launch explicitly
closes the warmup scope before acceptance (360–364).
`CallbackAdapter.prewarm_before_acceptance` (228–249) leaves no admission to reuse;
`native_shared_callback_capture.Admission.reconstruct` (87–97) itself rebuilds E
on every use. Do not revive it or treat its captured bytes as a verdict.

## Smallest defensible next boundary and witnesses

Keep public entry points cold and keep the pre-admission `_unchanged` unchanged.
A later private zero-argument checker inside the live `_launch` may compare
immutable original bytes and invoke actual guarded producers; it must not
accept a supplied verified body or branch on monkeypatches. Before deleting a
full call, its implementation must show where **both fresh preparation and the
complete input-only E reconstruction** still run. No cheaper complete boundary
or net saving is demonstrated here; duplicating those producers into a new
partial verifier would enlarge this task.

Reuse these existing witnesses selectively if that narrow boundary is supplied:

- `test_native_execution_registration_v2.py`: real preparation rederivation,
  live source/selection/runtime/executable drift, and changed runtime after
  preparer verification.
- `test_native_shared_registration.py`: every closed body field and uncached
  permission acceptance; `test_native_shared_controls.py`: actual minted helper
  mutation and mid-call mutation, plus expired/constructed carrier refusal.
- `test_native_subscription_capture.py`: outer/inner recapture order and genuine
  stage-root mutation parity. These do not prove a new post-acceptance producer.
- `test_native_u4b_a3_reservation.py`: actual margin/order/journal reservation
  behavior, explicitly with registration/source prerequisites isolated.

A changed in-memory rendering dependency with unchanged files must additionally
exercise the actual proposed producer path, alongside one unchanged success.
Retain current capture bytes, actual clock identity/freshness after slow work,
authorization rereads, one-use paths and the final journal lock through
`attempt.mkdir`. These are equivalence witnesses for a future efficiency change,
not a new test campaign or final-generation acceptance checklist.

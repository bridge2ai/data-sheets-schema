# Adjacent post-acceptance reconstruction: implementation checkpoint

2026-11-11. SOURCE IMPLEMENTATION ONLY; stop for separate adversarial review.

Branch `codex/native-postaccept-fusion-20261111`, isolated worktree
`d4d-executions/codex-native-postaccept-fusion-20261111`, exact parent
`382f0dfd1ce863fdf257a77e2bbb2637dbe2f67b`. The source-only design was
`native_postaccept_producer_boundary_20261111.md`, SHA-256
`8c4286318f6f2c69f346c3692b897d6a294d5f951d570c4c92cfd0386c46adc9`.
The lead's bounded implementation brief explicitly releases source work only.

The patch removes at most one full reconstruction from the accepted shared
CurrentSelection route. It does not replace the verifier with stored pins, a
previous verdict, or an expired loader scope. The existing complete
`_current_authority` producer chain remains at the lease boundary. Runtime,
refusal equivalence, freshness, speed and U3K-F1 closure are unproved.

## Exact patch

Only two production files change: 46 insertions, 8 deletions. The exact source
diff is `notes/reviews/native_postaccept_fusion_20261111.diff` (5,885 bytes),
SHA-256 `cce882721e0e54f9afc48159a56c8be61f34353e3ea07be8c092402e59246217`.

| File under src/data_sheets_schema | Postimage SHA-256 |
|---|---|
| native_execution_orchestration.py | `13573951995c5e7d27b164feaab1b328dad09b33c8dce9ff53afa50ec360a89b` |
| native_shared_execution_orchestration.py | `c77d692deafafb483e8ccf0781cad9434f1aee14aa4585fec4a2269d081025e5` |

The shared module extracts `_unchanged_inputs(value, authorization)` without
changing its statements: committed-source verification, authorization rereads
using shared `_file`, and host comparison using shared `_platform`. Existing
full `_unchanged` still verifies and compares execution first, then calls this
tail. The tail only refuses; it supplies no admission or execution capability.

The engine captures `c.canonical(value)` immediately after genuine initial
verification. These immutable bytes are local comparison data and never leave
that invocation. A local boolean becomes true only after the actual
CurrentSelection acceptance returns and the contract is the shared route.
The same subsequent join still validates guard type, actual clock and capture.

Only for that route, the engine calls the extracted tail instead of its second
`effects.unchanged`. This intentionally bypasses that one effects callback; it
is not hidden behind monkeypatch detection or a compatibility fallback.
A nested zero-argument `reservation_lease` calls the existing input-only
`_current_authority` with original registration/review/word bytes. That entry
performs current v3 request validation and genuine full verification, including
fresh preparation, guarded consumer reconstruction, classifier lifetime and
runtime/probe checks. Before locking, the engine compares both the fresh value
and its current mutable value to the immutable original.

The nested lease then uses `words.locked(fresh_value, registration_raw,
create=False)` and `journal.require(word_raw)`. It keeps the lock held through
controls, original-clock freshness/margin, profile, mkdir and fsync. No capture
lookup is introduced under the held lock. Direct-guard paths use the existing
full `_unchanged` and public `capture_admission_lease` through the local wrapper.
Public APIs and all later dispatch checks are untouched.

## Before and after call order

Both paths retain initial full verification, authorizations, static inspection,
pre-admission full `_unchanged`, composition/path checks, real admission,
controller prewarm, actual CurrentSelection acceptance and post-acceptance join.
The difference starts immediately after that join:

| Before | After, accepted shared CurrentSelection only |
|---|---|
| Full `_unchanged`: fresh verifier, equality | No verifier here; equality moves to the lease's existing fresh reconstruction |
| Committed source; shared `_file` reads; shared `_platform` | Same tail, same dependencies/order/position |
| Public lease: `_current_authority` -> full verifier | Local lease: same `_current_authority` -> full verifier |
| Lock/current word | Compare fresh and current engine value to immutable original, then same lock/current word |
| Controls; freshness/margin; profile; mkdir; fsync | Unchanged, within the same held lease |
| Later pre-dispatch `_unchanged` and dispatch path | Unchanged |

The fresh verification still traverses
`registration_orchestration.verified -> loaded_controls -> execution_v2.verified
-> verify_preparer -> _consumer -> rebuild_v2_body`, complete-body/dependency
comparisons and runtime-observation checks. `_recheck_verified` is not used as
its replacement. No consumer finder is retained across orchestration.

## Semantic differences and known test conflict

One intermediate full sample is removed. The retained source/auth/platform
checks therefore precede the remaining reconstruction; they previously
followed one reconstruction and preceded another. The patch does not claim to
detect every transient input/interpreter change restored before the remaining
sample. It compares against the original immutable execution in addition to
the current mutable engine value, rather than allowing a shared mutable alias
to become the only comparison baseline. Initial canonical serialization also
runs on the direct path, but no direct/public verifier, tail or lease call is
removed. No caller-supplied value, new API or persistent cache is introduced.

Source inspection found no stated requirement for two independent genuine
samples at these exact points. One existing component assertion does encode
the old trace: `tests/test_native_u4b_a3_reservation.py:330–345` expects
`isolated-source-recapture -> lease-enter`. Its fixture patches
`effects.unchanged` and traces the public lease, both deliberately bypassed by
the new private route. Its module docstring explicitly isolates genuine
registration/source prerequisites. This is a concrete expected fixture/trace
conflict, not evidence that the full producer contract has passed. Tests remain
untouched. If review finds a genuine distinct-sampling requirement, retain both
reconstructions instead of weakening it.

## Smallest proposed checks — NOT EXECUTED OR RELEASED

1. Adapt only the deferred-selection fixture/trace in
   `test_native_u4b_a3_reservation.py` (fixture lines36–80 and order node330).
   Observe the real extracted tail, `_current_authority`, and common
   `words.locked`/`Journal.require` boundaries. Isolate committed-source
   prerequisites explicitly beneath the tail. Keep actual shared `_file` and
   `_platform`, with witnesses that changing those inputs refuses. Preserve
   margin, controls, current word, mkdir/fsync, lease lifetime and release
   assertions. No production test-detection branch.
2. Cover unchanged success, then three separate after-acceptance mutations:
   current engine value only, fresh execution value only, and both values to the
   same changed value. Each must refuse before lock/mkdir; the third demonstrates
   why the immutable original snapshot matters. Exercise the actual shared input
   tail, isolating only `require_committed`, with changed authorization bytes,
   read failure and platform mismatch. Include input mutation during those reads,
   wrong current protocol, expired freshness, changed guard clock and existing
   reservation. The fixture clock can charge source/controls work before the
   90-second margin without sleeping; that is not elapsed-freshness proof.
   Retain deferred superseded/poison cases at line357. Refusals
   must precede lock/reservation when applicable; journal refusals stay under
   their genuine lock.
3. Keep direct-guard reservation nodes at lines262/279/291 and
   `test_native_subscription_capture.py::test_admission_lease_excludes_word_renewal_during_reservation`
   as unchanged public/direct witnesses. They isolate full registration and use
   an ordinary-Python capture peer; they do not prove genuine reconstruction or
   native execution. No such peer has been run here.
4. Separately propose one unchanged genuine-producer witness and one mutation of
   in-memory rendering/producer interpretation with unchanged disk bytes, through
   the actual retained reconstruction. Existing preparation, registration and
   controls tests can supply components, but call counts or isolated verifiers
   cannot establish full-chain parity. This needs its own bounded runtime release
   after adversarial review; it is not an instruction to rerun a diagnostic.

No test command is offered as already approved. No tests, Python imports,
compilation, profiling, captures, native/provider calls, preparation or config
rearm ran. The only mechanical check was `git diff --check`, which passed;
it is a whitespace check, not syntax or behavioral validation.

## Preserved state and handoff

Original native S382f, tools7043, helper/report8bb, original458887 branch,
private composition/configuration and all evidence remain unchanged. No
protected file, test, prompt, packet or fixture was edited. The implementation
and this packet are local on the new branch; no push or merge.

The lead owns the separate adversarial review and files concrete findings
before any repair. Stop here. Existing issues5722/5836 remain the trackers;
this slice adds no prerequisite to the separately scoped API-only final D4D
run. The earlier deadline result (#5865), remaining acceptance work and owner
packet/scanner decisions are unchanged.

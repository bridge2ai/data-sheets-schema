# Private post-acceptance design boundary

Date: 2026-11-11. Source-only assessment at native commit
`458887766effe38207a77fea2d8033f1f3e1c7f3`; no imports, tests or native edits.
This follows the rejection of public `verified_value` plumbing (#5836) and
test-dependent production fallback (#5837). Capture deduplication A remains
AGY3's separate work under #5838.

**Recommendation:** keep A as the next implementation slice. The private wiring
below is concrete, but replacing all remaining reconstruction with pin checks
is not yet justified by the existing helpers. The precise missing obligation is
preservation of the preparation/composition producer's mutable interpretation
state, beyond its files. Do not report this proposal as Gate 3B-S closure.

## Smallest private wiring

1. In `native_execution_orchestration._launch`, keep the genuine
   `registration.verified(registration_raw)` and pre-admission `_unchanged`
   unchanged. Immediately after the genuine verification, retain canonical
   bytes of its result and immutable pin tuples as local comparison data.
   Neither is returned, stored globally, installed on the adapter, or accepted
   from a caller. Later compare the engine's mutable `value` against those bytes.
2. Define the post-acceptance check as a **nested, zero-argument function in
   that invocation**. Its inputs come only from those locals, the existing
   independently captured authorizations and the accepted guard. Do not add a
   module-level factory taking an allegedly verified body or a pass flag.
3. Keep public `context`, `read_capture_for_event`, `read_capture`,
   `capture_admission_lease`, `require_current_capture_authority`, and the
   lower-engine `_join_subscription_authority` entry fully verifying. The
   optimized branch must follow the actual `CurrentSelection` acceptance in
   this invocation; direct guard callers retain their current route.
4. Separate private **data operations**, not authority-granting APIs:
   `_authority` may share a private request/binding/non-overlap parser after its
   own full verification; private slot reading can reuse A's extracted body.
   The launch-local function may use those same operations only after its live
   check. Such helpers return parsed/captured data, never a reusable admission.
5. Replace only this invocation's post-acceptance join, second `_unchanged`, and
   lease reconstruction. Leave the later pre-dispatch checks and public APIs
   unchanged. Lease acquisition stays local: current request checks, then
   `words.locked(value, registration_raw, create=False)` and `journal.require`,
   followed by the existing source-controls check, guard freshness, profile,
   `mkdir` and fsync. The lock remains held through reservation, with no nesting.

This wiring prevents the caller-supplied-body bypass. It does **not**, by itself,
prove that the replacement checks below are complete.

## Checks that must remain live

| Obligation | Existing source / reuse |
|---|---|
| Complete package/helper bytes and reviewed Git closure | `native_execution_authority_v2.require_committed`; `dependency_identity`; do not replace them with stored hashes alone. |
| Selected input bytes, physical paths, installed asset/schema locations and profile vocabulary selection | `native_shared_selection.capture`, especially lines 487-536. `preparation.pinned_files` covers bytes but does not check current resource-path resolution. Reuse capture initially rather than invent a second incomplete selector. |
| Runtime declaration, instruction, composition, system and permission input | Bounded `native_shared_evidence.read_regular`, checking original expected bytes/pins and the role's existing limit. Executable identity belongs to the runtime validator, including its device/inode rules. |
| Runtime observation and all bound probe-sequence files | `native_shared_registration_orchestration._require_runtime_observation`, which calls `validate_prepared_runtime` and `validate_bound_probe`. Permission top-level hash alone is insufficient. |
| Host, interpreter, current toolchain/resource resolution and active classifier | Current cwd, `sys.executable`, `sys.version`, host platform, actual toolchain, and existing source-minted classifier checks. `_selection` in `native_shared_registration.py` compares these during reconstruction. |
| Review, CI, owner word, selected guard | Existing authorization-file rereads, exact raw joins, exact v2 guard type and real `_now` identity. Guard `_fresh` also rereads its file. |
| Selected capture and journal | Re-read claims, manifest, streams and observations; retain exact-one-match, event chronology, terminal/limits checks. Keep current/superseded/refused journal checks and the final held lease. |
| One-use reservation and timing | `execution_paths_v2(..., fresh=True, extra_protected=authorization paths)`; unchanged original captured time; freshness after slow checks; before-dispatch consumption remains later. |

## Exact unresolved implementation boundary

`verify_preparer` reconstructs the entire preparation, not just its file map
(`native_execution_registration_v2.py:375-401`). `RunSpec.input_identity`
recomputes the profile digest (`api_runner.py:1172-1174`); instruction production
uses current JSON/string/command rendering functions
(`native_shared_render.py:320-385`). `_selection` also reconstructs policy with
the actual classifier and compares the current toolchain. Equal pinned bytes
therefore do not establish equivalence of these computations after an in-memory
dependency or resource-binding change.

The existing `native_catalog_reuse.runtime_token/schema_derivation_state` is
explicitly a **schema-metadata** guard. It is not a complete instruction/policy/
preparation producer guard. For example, command rendering uses `shlex.join`;
that function is not covered by the schema guard. Treating that guard as a
registration verdict would repeat the rejected design in another form.

The existing callback admission is also unavailable for this shortcut:
`CallbackAdapter.prewarm_before_acceptance` explicitly closes its temporary
source-loader/mint scope, and `native_shared_callback_capture.Admission`
reconstructs E on use. Do not export or revive that expired admission, retain
its finder across live launch orchestration, or weaken its reconstruction.

Thus the smallest defensible remaining change needs either (a) an explicitly
reviewed, complete producer-state refusal check established during the genuine
same-invocation reconstruction, or (b) preservation of the affected fresh pure
derivations using the actual guarded producer. Neither helper exists as a
complete boundary in the inspected source. A new assertion that a body is
"already verified" is not a substitute. No speedup is claimed for either path;
fresh `selection.capture` and retained pure derivations may still be material.

## Bounded witnesses before integration

Exercise the real private route, with component isolations below it, never a
test-detection branch. Mutate one input/source, one installed resource binding,
one bound permission file and one capture file after acceptance; mutate a
producer dependency without changing its on-disk source; alter the guard clock;
supersede/refuse the journal; consume freshness during checks; and pre-create a
reservation. Each must refuse before mkdir. Existing A3 reservation tests supply
ordering/margin/lease witnesses, but explicitly isolate registration/source
prerequisites and cannot prove the missing producer-state boundary.

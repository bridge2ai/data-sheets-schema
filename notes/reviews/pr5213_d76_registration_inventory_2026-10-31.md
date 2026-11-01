# D76 registration input-path inventory

Source implementation: `253a436e47b828d72de99a674abcac95617666d6`.
This is the source inventory and closure-repin account, not a validation result.
The final detached-checkout test report supplies execution evidence.

The common spelling predicate is `provenance.registered_input_paths`
(`src/data_sheets_schema/provenance.py:1611`). It recognizes the shared-generation
and native-attribution selections and an explicit boolean binding for older
registration builders. `RunSpec.__post_init__` excludes those bindings from
absolute-to-relative input rewriting (`api_runner.py:679`); `build_record`
uses the same predicate (`provenance.py:1712`). Neither predicate validates a
registration or grants execution authority. Existing guards still do that.

The inventory used ignore-independent searches (`rg -uu`) of Python under
`src/`, `scripts/`, and the operative `notes/` helpers; unrelated local worktree
and draft directories were excluded. Fresh `RunSpec` constructors and literal
replay consumers were inspected separately.

| Registration or route | Input authority and consumer | D76 disposition |
| --- | --- | --- |
| Shared generation v1 | `shared_generation.py:16`, absolute path guard `:316`, parser `:337`, capture `:503`; `cli/api.py:154` constructs the bound spec | Exempt through exact integer `shared_generation_version=1` with registration metadata. Registered bundle, chunk manifest and selected source manifest remain absolute. |
| Shared generation v2 | `shared_generation.py:40`, same parser/capture; completed capture compares literal input displays | Exempt through exact integer version 2. The completed-capture guard remains unchanged. |
| Receipt-completion v1 | `receipt_completion_policy.py:57`; closed registration keys at `:69` contain policy, limits and coverage-floor selections, with no input paths | Standalone v1 is not an input-pinning registration. It retains ordinary unregistered input spelling. |
| Receipt-completion v2/v3 | `receipt_completion_policy.py:157` binds the receipt registration to shared generation v1/v2 and compares the exact embedded registration | Exempt through its enclosing shared-generation registration, not merely because it is a receipt policy. |
| Native source-attribution offline registration | `native_attribution_registration.py:48` pins absolute inputs, `:66` constructs the registration, `:107` restores its literal render spec, `:412` constructs the CLI selection with absolute inputs | Exempt through exact integer `native_source_attribution_version=1`, the explicit selection from which this registration is prepared. |
| Native attribution execution registration | `native_execution_registration.py:163` consumes the verified attribution registration; permission expectation at `:179` binds the selected bundle; `:223` prepares execution authority | Covered by attribution selection and literal replay. `verify_saved_probe` and the absolute canonical permission-path checks remain unchanged. |
| Neutral native attempt supervisor v1 | `native_attempt_supervisor.py:26`, registration at `:121`, attribution replay at `:137` | Covered by the same attribution registration. No synthetic result authorizes native execution. |
| Direct-arm registration v1 | `notes/claudecode_direct/prepare_direct.py:207` freezes the three discovered input paths before pins/jobs, constructor `:221`; `run_direct_canary.py:80` reconstructs the registered job | New registrations explicitly select `registered_input_paths=True`. The new job's render spec and its reconstructor agree. |
| Matched API/agentic registration, schema version 1 | `notes/matched_cborg_2026-09-13/prepare_registration.py:41` supplies both API and agentic specs; `:179` freezes discovered input spellings before pinning new jobs | New registration builders and their launch reconstructors explicitly select the same boolean binding. The API/native runtime choice alone does not activate it. |
| Audit and finalization continuation registrations | `notes/matched_cborg_2026-09-13/audit_controls/registration.py:253`, `audit_controls/contract.py:97,151`, `finalization_controls/contract.py:109` use `RunSpec.from_render_spec` | Existing literal replay preserves recorded spellings. No new normalization or fabricated registration metadata is added to saved specs. |
| Registered semantic evaluation v1 | `evaluation/registered_eval_runner.py:295–308` checks the selected shared registration and its pinned inputs directly | No fresh `RunSpec` is constructed here; input authority is already literal and absolute. |

The explicit binding is a strict boolean (`api_runner.py:587,598`), appears in
serialized render specs only as `true` (`:1006`), and is restored and validated by
literal replay (`:786,812`). Old render specs without this field still omit it.
Unregistered CLI runs retain their existing cwd-dependent spelling. No code
infers registration from project names, runtime names or profile-basis prose.

## Fresh registration and historical compatibility

The three older fresh constructors now state their registration binding.
A saved old job reconstructed through these changed constructors can therefore
fail its exact render/input-identity comparison. That is deliberate refusal:
these launchers also bind their registered code commit, source files and review
approval. They must prepare and review a fresh registration for changed code.
The patch does not silently migrate old jobs, rewrite old instructions, or
relax the code, instruction, input or permission checks. Historical literal
`from_render_spec` replay remains separate and preserves the old metadata.

Independent review identified that conventional chunk discovery may return a
relative name. D76-REG-2 is addressed by freezing `manifest`, `bundle`, and
`chunks` to absolute paths before the direct and matched builders create their
new pins and jobs. The constructor then retains those supplied registered
spellings. It does not reinterpret arbitrary malformed registrations or search
for replacement inputs.

## Native helper closure

The modern native controller imports three older registration helpers as part
of its captured source closure. Keeping their old hardcoded source digests
would correctly refuse the changed files. The closure was therefore re-pinned
without removing any check or rewriting prior evidence:

- `native_controller_sources_v1.json` names source snapshot
  `253a436e47b828d72de99a674abcac95617666d6` and the new matched helper digest.
- `native_attribution_controller.py` pins the resulting manifest bytes.
- `native_supervisor_authority.py` pins the two updated direct helpers.

`scripts/adhoc/wave7_d76_repin_native_sources_20261031.py` verified every selected
module against that exact local Git commit before writing anything: twelve
controller modules and two additional direct helpers. Only the three expected
helper files changed; the other eleven member digests remain unchanged.
The manifest's source commit identifies the complete selected snapshot, not the
first introduction of each member. No network, provider or native binary was
used. The helper also re-read each output and verified it was persisted.

Retained evidence:
`d4d-executions/plans/reviews/pr5213_d76_2026-10-31/closure-repin/`.

| Artifact | SHA-256 |
| --- | --- |
| Repinning helper | `e8c2d7f8821447f71dd9e969343552e8836556f43a997f142882f78d72a7e1bd` |
| `plan.json` | `15d9140c200faff6e820052682ca2266ff68717578cb2ac84c0737aa36311b0c` |
| `applied.json` | `1004fe4c8f4f8f61a43152cb02d8980780de3014d5342216abdb3d0a8e1c1b24` |
| Updated native controller source manifest | `e55f332b2cc4d679c2ffa9cba5d40acb8a333fd821e3b6d0f2746b8cba7f3971` |
| Updated native attribution controller | `b56faf4e3623337f5a96fb559c0c785fca05da60b18018beb09854bc2534ffce` |
| Updated native supervisor authority | `83f728648a8beee70b8f80219ae552aeb60a6e407f9e4d097dd3d319e2b07058` |

Regression coverage is authored in
`tests/test_wave7_5213_d76_registration.py`,
`tests/test_wave7_5213_d76_legacy_registration.py`, and
`tests/test_wave7_5213_d76_binding_records.py`. It includes fake-client SG v2
completion for all three manifest layouts, SG v1 cross-directory instruction
identity, native execution registration with the real saved-probe verifier and
fabricated observations, legacy fresh constructors, the actual direct preparer
with a fake version/auth fixture, provenance spelling, invalid flags, and
unchanged unregistered/literal-replay controls. This note does not claim those
checks have passed; the parent validation ledger records the pinned executions.

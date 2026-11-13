# Capture A live-precondition review

Review recorded: **2026-11-11 05:16:11 UTC**. Source-only review of a moving,
uncommitted draft in `agy-native-path-alias-parity-20261111`, based on
`458887766effe38207a77fea2d8033f1f3e1c7f3`. The latest observed
`src/data_sheets_schema/native_shared_registration_orchestration.py` SHA-256 was
`c674f2bea05d20d744871fe8839ee634527045e8fef23c027548afbc1b6ce233`.
Line references below describe that inspected source and its unchanged dependencies;
this is not a review of a later frozen commit.

No imports, tests, model calls, evidence reruns or worker-file edits were performed.
Only this lead-owned report was written.

## Disposition

The latest observed draft calls genuine `execution_v2.selection.capture` at
`native_shared_registration_orchestration.py:193–194`. That restores a group of
live selection checks omitted by the earlier SHA-only recheck, including the
concrete stage-directory regression filed as #5847. This is stronger than adding
only an `is_dir` check.

No additional ordinary production-state bypass was established in this bounded
follow-up. This does **not** establish complete equivalence to the replaced
verifier. Genuine positive-path and differential runtime evidence for the revised
draft remains unverified by this review; mocked rechecks and fabricated registration
bodies cannot supply that evidence.

## Checklist of live preconditions

| State | Old live check and current disposition |
|---|---|
| Selected stage path | `native_shared_selection.py:489,496–498,529–530` requires a canonical path and, if present, a directory. Creating a regular file at a previously absent stage root during slot discovery is the concrete #5847 counterexample: all pinned input bytes can remain unchanged. Current fresh selection capture restores this check. |
| Installed resource and schema selection | `native_shared_selection.py:501–508` binds declared asset paths and schema roots to their actual selected resources. Current fresh capture retains this independently of saved file digests. |
| Profile vocabulary selection | `native_shared_selection.py:509–514` compares the selected profile's current vocabulary path. `profiles.py:89–106` explicitly supports the in-process `schema_digest.VOCABULARY_PIN` override. Current fresh capture checks that configuration again. |
| Selected member cohort | `native_shared_selection.py:515–528` enforces member pins and role/aggregate bounds; `_Reads` at `412–467` and `reader.stable()` at `528` check device, inode, mode, link count, size and modification/change timestamps across capture. The original independent SHA-read loop did not replace this cohort-stability check. Current fresh capture restores it. |
| Other live state | The recheck retains cwd, source/dependency identity and committed-byte proof, runtime/executable validation, U4b observation evidence and physical reservation checks. Capture still checks reviews, journal/current word and saved slot records. Preserve these checks alongside file pins. |

Anchors for the last row: `native_shared_registration_orchestration.py:163–169,200,265–269`;
`native_shared_runtime_values.py:75–95,161–166`;
`native_u4b_runtime.py:267–308`;
`native_shared_registration.py:185–210`;
`native_subscription_capture.py:98–137,590–602`.
The synthetic route additionally checks its isolated HOME's physical directory and
emptiness in `native_runtime_profiles.py:122–156`.

## Boundaries of the finding

The registered native path explicitly supplies manifest, profile, effort and
provider from captured selection/runtime values
(`native_execution_registration_v2.py:250–260,324–341`; `api_runner.py:828–834`).
Its child environment is derived from the runtime plus fixed policy, with explicit
`D4D_MANIFEST` and `D4D_PROFILE` (`native_shared_registration.py:28–39`). An ordinary
change to ambient `D4D_PROFILE` or `PATH` does not itself reselect this path.

U4b's final toolchain uses the closed `NATIVE_SHARED_RESOURCES` roster
(`agentic_runtime.py:33–35,61–67`); adding an ambient agent Markdown file does not
change that final roster. The older auto-enumerated non-U4b route is not the
capture function's admitted runtime: `_authority_from_value` always calls
`validate_prepared_runtime`.

The documented vocabulary override is a library configuration point, not an
external shell-environment or ordinary filesystem mutation. Replacing classifier
or `shlex` callables, arbitrary `sys.prefix` changes, and forging producer objects
require in-process intervention and were excluded from this ordinary-state
checklist. No separate ordinary filesystem/environment mutation was established
that changes source-fixed rendering or producer semantics while the fresh
selection, source, runtime and path checks remain true. Missing reconstruction
calls alone are not additional demonstrated regressions.

## Smallest relevant acceptance evidence

Use an actually valid registration whose initial value comes from the genuine
verifier. Establish unchanged matching-slot readback, then create a regular file
at its previously absent selected stage root during outer `_claims`/slot discovery
and require refusal at matching-slot recheck. Compare that refusal with the old
path. Do not substitute a mocked `_recheck_verified` or invent an otherwise invalid
selection/render/permission body. This review did not run those cases and does not
authorize or recommend a broad test cohort before their result is known.

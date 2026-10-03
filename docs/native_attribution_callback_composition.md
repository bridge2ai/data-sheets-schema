# Offline native attribution callback composition

This source-checkout adapter demonstrates pre-tool enforcement of the native
attribution draft obligation through the existing controller. It provides no
production launcher and makes no authentication or provider call. Parent #2427
still requires a fresh execution registration, native-runtime permission checks,
independent review, CI, explicit launch authorization and empirical evaluation.
Shared-condition decisions under #3336 are unchanged.

`native_attribution_registration.NativeAttributionState` provides ordered prefix
observation and completed-history reporting. The existing `verify_history` API
still verifies a supplied completed trace. In callback mode, a passing result is
recomputed against current saved files before another callback is released.
Report writes invalidate that pass even if their bytes are later restored.
Pending tools, malformed results, protected-file corrections, exceeded draft
limits and prior terminal failures cannot be cleared by a later successful check.
After the first draft check, inherited mutation-capable shell helpers cannot
bypass the report-only correction rule. Registered read-only lookups remain
eligible; unknown shell effects refuse.

The new `native_attribution_controller` module builds its policy from the exact
explicit RunSpec. It adds only the fully bound draft command to the existing
command grammar. Every concrete command in the selected instruction is checked
for admission before a composition can be written. An instruction whose quoting
is rejected by the frozen runtime grammar remains rejected; preparation does not
silently rewrite it. The old launchers and their registration kinds are unchanged.

The composition selects the existing version3 `HISTORY_CONTRACT` explicitly.
Its observer barrier precedes callback publication; the controller retains its
bounded queues, timeouts, sticky stop handling and worker-shutdown accounting.
The adapter is passed through existing `execute_child` callback parameters in
neutral local-process tests. Historical phase/receipt checks run first. A passing
draft gate is not a complete generation acceptance and does not replace final
evidence, schema, pair, receipt, usage, permission or provenance requirements.

After an actual current final-evidence pass, one exception permits the exact
emitted provenance-recorder command. Its existing consumer writes the one new
registered provenance file (including its inline-check update); the adapter
does not authorize a module or metadata commands in general. Existing targets,
symlinks, hard links, failed recorder results and later tool continuation refuse.
Final input hashes are rechecked through recording, the resulting metadata hash
is retained, and a completed report rechecks both. This preserves evidence of
what executed; it does not certify all provenance checks or model usage.

## Capture and verify

Start with a freshly prepared #4304 offline registration and its exact instruction
bytes, in the same source checkout and interpreter. These are new files, not a
copy of a spent paid registration. The Python API can write a new composition:

```python
from pathlib import Path
from data_sheets_schema.native_attribution_controller import write_composition

write_composition(
    Path("fresh-offline-registration.json").read_bytes(),
    Path("fresh-instruction.md"),
    Path("new-callback-composition.json"),
)
```

The destination must be new and outside captured source/historical-control
directories. No existing file or attempt is overwritten. `verified_composition`
reconstructs the selection before accepting it. `CallbackAdapter` exposes observer
and classifier hooks for an independently reviewed caller; it has no method that
starts a process and is not an execution approval.

The artifact includes the original registration's exact bytes/hash, instruction
path/hash, exact command policy/hash, Python identity and the pinned twelve-module
local controller dependency closure. The source inventory is frozen as
`native_controller_sources_v1.json`; source drift, missing dependencies or modules
loaded from another checkout refuse before use. The original package source-tree
and canonical prompt pins remain mandatory. These hashes bind local declarations;
they do not authenticate a provider or certify a live runtime.

An absent/unused source manifest is excluded from the draft command and its
source authority. A selected-but-unused manifest can still be needed by the
unchanged recorder/profile command. The composition pins that file separately as
metadata-only and retains the recorder's selected manifest permission; it never
relabels the file as draft evidence.

## Offline evidence and remaining limits

Tests use an ordinary local Python process that speaks the initialize/tool-use/
callback/result protocol. It executes the actual deterministic preflight and
final evidence and provenance-recorder commands on neutral temporary files, and writes markers only after
receiving a real allow reply. Tests preserve originals and failed transcripts,
exercise report-only correction, pending callbacks, deadlines, inherited stops,
finite checks, and refusal to reuse an attempt directory. A later queued callback
receives no permission while recomputation is blocked.

A direct native controller cannot meter provider spend already incurred in
producing a tool request. Terminal failure raises into existing close/terminate
handling instead of inviting a tool retry; there is no automatic restart or
resume. A fake-runtime success is neither a live permission proof nor a canary
result. Actual model/effort/context/budget/deadline choices, keep-awake composition,
owner-approved shared condition and a separately authorized paid canary remain
outside this delivery. Held audit28 controls and historical attempts are untouched.

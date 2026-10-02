# Registered API receipt completion

This is the software prerequisite for #2926, tracked in #4266. It is an explicit
`receipt_completion_version=1` condition axis for receipt-producing API renderer
8 conditions. The default omits the axis. Renderer 24 remains an offline-only
instrument with its historical request identity and execution refusal.

No production output cap, request limit, model, spending budget, or empirical
coverage threshold is selected here. Human/empirical calibration and separately
authorized CHORUS/AI_READI pilots remain open under #2926. The examples in tests
are synthetic engineering probes, not measurements of receipt quality.

## Registration and gates

Supply `--receipt-completion-version 1 --receipt-completion-registration PATH`
to `d4d api plan`, `render-prompt`, `run`, or `batch`. The file is strict UTF-8
JSON. Its exact text and SHA256 are preserved in the render specification under
`prompts.request.spec`; the registration binds the frozen runtime policy and is
not inferred from a run label or a receipt's origin marker.

Required fields are `format: receipt_completion_registration_v1`, a nonempty
`registration_id`, the selected `condition`, `runtime_policy_sha256`,
`receipt_instrument_version: 4`, explicit positive integer `max_output_tokens`
and `max_request_bytes`, positive integer `context_limit_tokens`, nonblank
`context_limit_basis`, and `coverage_floor`. Extra keys, booleans used as
integers, duplicate keys, and nonfinite numbers are refused.

The floor is either `{state: pending, mode: diagnostic_pilot}` or
`{state: registered, numerator: INTEGER, denominator: POSITIVE_INTEGER}` within
[0,1]. A pending diagnostic pilot retains measurements but never passes a strict
coverage gate. Exact integer cross-multiplication evaluates a registered floor;
a rounded percentage is not authority. No eligible leaves is explicit N/A, not
100 percent, and does not authorize fan-out. Existing independent vacuity and
receipt-defect checks still apply. The new condition cannot use the ordinary
canary bypass to evade its floor. Changing a pilot to a registered floor creates
a new identity; it does not retroactively certify the pilot.

`receipts check --strict` and current canary evaluation share the same policy
resolver. Before provenance exists, an explicit registration can select the
checker. With provenance, it must agree with the recorded registration. An old
record cannot acquire new-condition status via a command-line override or
`--write`. Default historical callers keep the existing v3 instrument and five
receipt defect floors.

## Durable continuation

The full record and any existing re-addressing finish first. The runner saves
the normalized full, original receipt snapshots, effective receipt, complete
last full/readdress exchange and usage identity before the completion boundary.
A separate generation-ledger state prevents a lost progress file from purchasing
full again. This does not add a phase to the historical global phase sequence.

The continuation captures the selected schema and transitive imports and validates
the full against those captured bytes. Every uncovered path enters one complete
request, together with the original exchange, immutable registration and runtime
policy. The registered output cap must fit the selected route without clamping;
the whole request must fit the supplied byte limit. For nonempty inventories,
the same client's `messages.count_tokens` endpoint receives the complete logical
system/messages/model/thinking request (including any effort configuration).
An unavailable or malformed count refuses generation. The endpoint-reported
input count plus the output cap must fit the caller-asserted context window.
Its asserted basis and request-hash-bound count are preserved with the intent;
neither a byte bound nor the assertion independently establishes actual capacity.
No path is silently truncated. Empty inventories record explicit no-work without
a counter or completion call. A saved intent reuses its pinned count.

One durable admitted completion request uses the existing bounded transport
retry/accounting machinery. There is no answer retry or restart of full. Raw
response, finish reason, usage, reasoning and checked result are preserved in
separate hash-bound snapshots. Unknown usage, source-review/evidence refusals,
and accepted-restoration restrictions retain their existing terminal semantics.
The response envelope includes the full captured reasoning entry. Recovery
appends a missing entry exactly once and refuses contradictory logs, so a crash
between response publication and reasoning append does not discard disclosure.

The existing typed receipt parser, quote checker and validated merge produce
v4 counts. Verified partial additions may be published, but an incomplete answer
set stops downstream execution. Unsupported answers can complete answer
accounting without adding coverage. Every unsupported path/reason, original
input identity and result artifact digest is carried into the actual audit
request for independent assessment. They do not instruct deletion.

Publication checks the pinned original receipt hash and records the exact
resulting hash. After an interruption, recovery recomputes the result from the
saved response and inputs, adopts the recorded resulting receipt if already
published, and refuses unexpected drift. It never reapplies a merge or repeats a
completion admission. Missing progress after the durable full boundary requires
restoration of the saved progress or a matching completed provenance record;
it does not silently reconstruct which later phases ran.

Keep three facts separate: complete answer accounting, coverage-floor status,
and scientific support. The fixed phase-1 before/after denominator remains in
the completion outcome alongside final-record coverage. Later removals cannot
be presented as receipt-completion improvement. Origin and padding diagnostics
remain descriptive unless separately registered policy changes their role.

## Validation and limits

Offline tests use actual local LinkML validation and receipt/snippet checks,
fake provider responses, deliberate malformed/partial/truncated answers and
interruption/drift mutations. They exercise the saved request payload and audit
carry, not only helper return values. Historical renderer captures remain the
byte-parity oracle. No paid generation, calibration, old-cohort rewrite, held
#2605/#2714 change, or frozen controller edit is part of this implementation.

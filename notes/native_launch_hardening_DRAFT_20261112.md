# Launch hardening notes — DRAFT, not permission

Use `python -I -B -m data_sheets_schema.native_launch_entry` from the registered
installation that exposes this checkout, with the existing sequence arguments.
If the package is selected explicitly by a bootstrap, import this entry, not the
sequence implementation. The entry reads the sequence bytes once, compares that
capture to the current review and registration source pins, compiles that same
capture, and gives it to the sequence for retention. It does not import the
verifier bootstrap. Full authority validation remains in the command consumers.

The interpreter (including its site startup), the small entry, the pure wire
reader and the local operating system remain trusted. This does not authenticate
a human, a direction, host state or account quietness, and cannot protect against
arbitrary code already controlling that interpreter. The old sequence `main`
only delegates to this entry; its private verified-body API is not an alternate
operator entry. Sequence-unit tests call that private body with explicitly
captured fixture bytes; entry tests separately exercise the actual byte check.

Delegated direction identity is the recorded UTC instant within the exact
registration digest, normalized to microseconds. The registration's attempt
parent holds `.native-sequence-starts/<registration-sha256>/direction-<identity-sha256>.json`.
A new packet directory or renewed host confirmation does not renew it. A new
owner-recorded direction must have a distinct time; it must never be invented
by the helper. Owner starts (neither flag) retain unique owner-start records and
can start again. Partial or failed claims are kept; they are never cleaned up to
permit reuse. Capture/word and attempt reservations are separate and unchanged.

No registered document kind or version changes. New records are local sequence
start evidence, not an alternative authorization document. All source closure,
permission and review pins must be derived from the eventual integrated source.

Each sequence child receives `--sequence-inputs`, a closed mapping of the five
input paths and their expected digests, plus the newly produced capture or guard
when relevant. These are invocation arguments, not a new registered document.
The child checks all named bytes before proceeding and compares the bytes it
actually consumes. Launch carries the three authority digests to the engine's
captured review/CI/word set before any reservation; guard preparation compares
its actual locked capture-manifest read. Existing independent reconstruction,
freshness, current-word, latest-claim and profile gates remain mandatory.
Standalone command callers without these arguments retain their prior behavior;
the reviewed sequence always supplies them. The final delegated-time check is
after durable start claiming, so claim latency cannot carry dispatch past a limit.

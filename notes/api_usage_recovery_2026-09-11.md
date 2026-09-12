# Completed API usage recovery (#656)

The API generation runner previously kept completed-call token usage in memory
until final provenance was written. A process exit after the full or core phase
could leave valid progress and artifacts but no usage record. Resume then skipped
the paid work and emitted incomplete accounting.

Completed responses now receive a UUID and are persisted before reasoning writes,
parsing, snapshots or progress updates. This covers main phases, validator repair,
receipt re-addressing and report regeneration. An atomic JSON replacement, with
the temporary file flushed and synced first, keeps the prior ledger readable if
the write is interrupted. Later unusable-response and re-addressing details update
the same call instead of adding a second charge. The existing abandoned-stream
journal remains in use for its separate partial-usage evidence.

The ledger is beside provenance, named with the project and a hash of the run's
project, label, method and condition. Resume merges UUIDs exactly once and retains
legacy provenance rows without guessing identities from timestamps. A forced
fresh run archives its previous ledger byte-for-byte and does not seed usage from
old provenance. Malformed or mismatched ledgers stop resume before another model
call; a failed persistence write stops the current attempt instead of retrying it.

Regression tests use fake clients throughout. A child process terminates with
`os._exit` immediately after either full or core progress is saved, before any
final provenance exists. The resumed run skips full, makes only the remaining
three model calls, preserves all four usage rows and does not duplicate them on
another resume. Further tests cover identities sharing a flat output directory,
same-second calls, optional post-response failures, atomic write failure,
malformed accounts, unusable attempts and forced fresh execution.

This change records future calls. It cannot recover usage that was lost by a
historical process, and it does not claim that an in-flight response interrupted
before the runner receives final usage is a completed call. It changes no prompt,
rubric or score and makes no live API calls as part of validation.

Codex review round 1 found #1290: recovering a call before its reasoning append
could shift the old positional telemetry join. All four call sites now include
the usage ID in reasoning entries. Telemetry matches identified calls by phase
and ID; unmatched calls have no reasoning estimate. Positional matching remains
only for legacy rows and entries without IDs. Identified reasoning from a prior
forced-fresh run is also excluded from the current record's reasoning total.

Round 2 found #1291 (a fresh run's later resume re-imported the old provenance)
and #1292 (YAML-native receipt dates could fail JSON serialization). A durable
generation ID now links ledger, progress and provenance. A fresh boundary is
committed by atomic ledger replacement after syncing an archived copy; the old
ledger remains active if replacement fails. Earlier-generation progress,
provenance and abandoned-stream rows cannot be imported into a fresh generation.
Legacy partial runs can adopt an identity without losing their recorded usage.
A finished portable record still takes the no-call exit without a ledger;
unfinished identified progress with a missing ledger stops before spending.

Receipt diagnostic values are normalized for JSON. If optional diagnostics
cannot be encoded, the usage row records `diagnostics_unavailable` and retains
the call counters; the original receipt remains on disk. Tests cover dates,
timestamps, non-string mapping keys, fresh interruptions before progress and
after full/core progress, archived bytes and legacy recovery.

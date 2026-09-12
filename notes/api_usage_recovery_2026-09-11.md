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

Round 3 found #1293 (abandoned-only evidence could be excluded after losing its
ledger) and #1294 (another label's provenance could falsely trigger the missing
ledger guard). Recovery now checks ownership before adopting provenance or
progress. New progress and abandoned entries carry the full run identity.
Identified abandoned evidence is checked before either a new call or the
completed-record exit; only charges already preserved exactly in that run's
record permit portable completion without a ledger. Abandoned calls also get
UUIDs, so repeated snapshot names cannot collapse distinct charges. Foreign
progress survives a completed record's read-only return.

The same missing-ledger boundary also covers identified reasoning left by a
completed response before snapshots or progress could be saved. Reasoning entries
carry generation and run identity as well as the call ID; portable completion
requires their call IDs and recorded output counters to be covered by provenance.
Fresh execution also preserves the IDs of superseded generations in the ledger
and provenance. Their retained log entries are historical; a later unknown
generation still blocks completion when its ledger is missing.

Round 4 found #1295: fresh execution from a portable completed record could
lose its predecessor's history because the ledger had not been copied. The
fresh boundary now combines matching provenance history with any existing
ledger history. It does not import prior charges or another run's history.
Tests cover fresh execution from a portable record, its subsequent no-call
return, and repeated fresh boundaries with stale provenance.

Round 4 also found #1296: a failed completed-response write left no durable
evidence to stop a subsequent invocation from understating usage. Every paid
call path now commits a pending identity before the request and resolves it
atomically with the completed counters. Failure or process interruption in
between leaves that marker, which blocks further calls and the completed-record
exit until accounting is restored. Explicit fresh execution archives the
uncertain generation without claiming to recover its counters. A reported
transport error with no completed response clears the marker; partial usage
continues to use the abandoned-stream journal. Tests cover all four call paths,
the next invocation after storage recovers, interruption and explicit fresh.

Round 5 found #1297: overlapping invocations could both pass the pending check
and overwrite one another's intent. Public execution now holds an exclusive
process lock for the shared output directory and project, including fresh
execution and different labels sharing flat output paths. A contender stops
before reading or changing recovery state or sending a request. The lock is
released on return and process exit; independent output directories remain
independent. Tests exercise overlapping execution before the first intent is
written, all three contender cases, and a hard child-process exit.
Existing source-inspection guards now inspect the execution body beneath the
lock wrapper; their original assertions are retained.

Round 6 found #1298: standard split and flat layouts can share a full record
without sharing metadata. The exclusion now acquires the resolved full, core,
report and provenance file locks in a deterministic order, releasing earlier
acquisitions if any file is already owned. Tests cover both layout directions,
shared core paths and a symlink alias to a shared physical output.

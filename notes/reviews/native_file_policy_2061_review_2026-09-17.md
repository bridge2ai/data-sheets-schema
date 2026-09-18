# Native file-tool controls review, 2026-09-17

The v10v canary read an unregistered agent definition through the broad native
Read permission. #2061 keeps the input scope and now enforces Read and Write
through the parent SDK PreToolUse channel before either file operation. It does
not widen the playbook closure or repair the stopped attempt.

Policy version 4 and control contract 2 cover Bash, Read and Write. Observed
calls, native callbacks, parent decisions and results must match at completion.
File paths resolve against the registered repository; input files are read-only,
output links cannot escape frozen roots, and output hard links cannot alias
pre-existing files. Relative-to-absolute path normalization is allowed while
other input fields, including write content and read windows, remain exact.

Persisted Bash output is readable only after a corresponding prescribed call,
matching native metadata, the current configuration/project/session directory,
and recorded size/hash verification. This includes error diagnostics; allowing
their read does not waive the procedure's checker stop rules. A source passage
that mentions a filename grants no access. Persisted files cannot be written by
the agent. Stop receipts retain available control evidence and the named cause.

## Adversarial review and validation

The first review identified filesystem resolution in callback matching outside
the classifier deadline (#2062). The regression allowed a write before the fix;
a timed worker now covers matching as well as classification. Both the regression
and an actual-runtime stall probe verify a stop before writing, with no remaining
handler. The second review checked call substitution, unknown/orphan results,
symlink and hard-link targets, source overwrites, persisted-output spoofing,
changed bytes and legitimate diagnostic reads. No unresolved finding remains
in this reviewed change.

The [probe summary](native_file_policy_2061_probes_2026-09-17.json) retains:

- 39 cases on the pinned runtime without project settings, including 11 file calls.
- 41 cases with broad project settings, including one persisted output and 12 file calls.
- A stalled path-match probe: one callback, zero tool results or writes, and zero unfinished handlers.
- Five behavioral tests that fail when the file-admission guard is disabled.

The nonzero-exit helper returned its diagnostic directly on this runtime; the
following read used the earlier persisted output. Error-result provenance is
also exercised by unit tests. No second persisted runtime file is claimed.

All runtime probes used scripted local responses and zero real provider requests.
The native binary is 2.1.272, SHA-256
`195e24e8e1f9bf46f1eaee72d434a33e18f9f5796f29a6348a00d16c5f8aee75`.
Full local evidence is archived with inventories including hidden/ignored files.
333 focused transport, launch, evidence and receipt tests passed (19 API-only
combinations skipped);
CI includes the file-policy tests in the existing single native-controls lane.

## Limits and retry

These controls are not an OS filesystem sandbox. Prescribed helper arguments,
phase order, receipt timing, original-freeze evidence and source entailment still
need independent acceptance review. The native callback establishes admission
and evidence consistency, not scientific quality or repeatability.

v10v remains stopped and unaccepted. The user explicitly requested "resolve and
retry" after its outcome. Prepare and review a fresh condition, require successful
CI and fresh bindings, then bind that existing authorization to one CHORUS native
retry. Do not fabricate a later user instruction or reinterpret prior attempts.

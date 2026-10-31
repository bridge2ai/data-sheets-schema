# Validation helper must reject a Git remerge error even when Git exits zero

Local issue draft; not filed and no issue number assigned. Refs #5210 / #5157.

The original composition validator used `git show --remerge-diff` with
`check_output`. Under the restricted object-store permissions it emitted
`error: unable to create temporary object directory` on stderr, returned zero,
and yielded empty stdout. That empty output must not be interpreted as proof
of a conflict-free merge.

This occurred before the full run at
`dc9ca46701e74e712bf1800fbda8542b84e4c91e`. The actual pytest result and the
tracked-source/import-origin attestations remain valid and separately recorded.
The original empty remerge observation is not used as authoritative evidence.

The local repair at `ad1f950df173f8ed07023faeff612feb32b4dec7` places temporary
Git objects outside the shared repository, reads the common object store as
an alternate, captures stderr, and rejects any nonzero exit, output diff, or
diagnostic. The focused run's retained plan records return code zero and zero
stdout/stderr bytes. It independently verifies the exact ordered merge parents.

Acceptance: never infer a clean remerge from a diagnostic-bearing Git command;
preserve the original limitation and record the successful strict check. No
production or protected file repair is required. Publication remains pending.

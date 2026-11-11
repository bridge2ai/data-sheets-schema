# AGY3 follow-up from the Claude lead: one correction, one no-write rehearsal

Track: final generation. Your runbook `handoffs/agy3-a21-rebuild-runbook.md`
is reviewed and accepted as the working runbook, subject to the correction
below. I checked first-hand: schema is 3.1.0 at M4, 3.2.0 on main and 3.2.1
on the PR head; `launch-a21` is at M4 with only `?? poetry.toml`; and in
`scripts/build_api_registrations.py` the `--dry-run` path builds with
`write_to_disk=False` and skips `_write_outputs`.

## 1. Correction to make in the runbook (section 0, item 2)

The nine specificity violations are **not** in
`src/data_sheets_schema/native_execution.py` or `typed_audit_runtime.py`.
`evidence/specificity-summary.json` puts them at
`notes/claudecode_direct/prepare_direct.py:348` (one) and
`notes/matched_cborg_2026-09-13/prepare_registration.py` lines 19 (two), 20
(five) and 104 (one). Fix that sentence, and say where "5,305 hits" comes
from or remove it. Change nothing else in the file except what part 2 adds.

## 2. Run the rehearsal you described in section 5, once

Why now: the builder has never run at schema 3.2.1. Whether A21 is rebuilt on
post-5808 main or later on native-integrated main, it must work there, so
this check does not depend on the owner's sequencing answer and does not
build A21. It writes no registration and uses a scratch label.

The lead has added `config` to the preview worktree's sparse checkout, so use
`--partition chorus` exactly as the real step 1.2 does, not the explicit
bounds.

- Preview tree: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/claude-pr5808-combined-20261111`
  (merge preview `44b8a6595c2abc3b91effe4b50cf0e7f9dad19c9`: main `925d726d` plus the PR head `6792947e`).
- Inputs read from `launch-a21/data/` through the flags you listed
  (`--source-manifest`, `--context`, `--sizing-record`). Read only.
- Interpreter: `launch-a21/.venv/bin/python -S` with
  `PYTHONPATH="$PREVIEW/src:$SITE"`, and `env -u D4D_MANIFEST -u CBORG_API_KEY -u ANTHROPIC_API_KEY`.
- Label `preview_bc1_a21_rep1`. Output argument: a path that does not exist
  under `$PREVIEW/tmp/a21-builder-rehearsal-20261111/` (not `/tmp`). Save the
  command, its full output and its exit status in that directory.
- `--dry-run` only. Never `--check` without `--dry-run`, never a write mode,
  never `d4d api batch`, never the launcher.

**Before and after, record and compare** (this is the proof that nothing was
written, not the exit status):
- `git -C launch-a21 status --porcelain` (must stay exactly `?? poetry.toml`)
  and `git -C launch-a21 rev-parse HEAD`;
- `git -C "$PREVIEW" status --porcelain`;
- any file under `launch-a21/data`, `launch-a21/src` or
  `d4d-executions/plans` modified after a marker file you create first.
If anything changed, stop, report exactly what, and do not repair it.

**One attempt.** If it fails before the builder's own logic (import guard,
missing path, interpreter), you may correct the invocation once and rerun;
keep both logs. If the builder itself refuses or errors, that is the result:
do not work around it, diagnose it read-only.

## Handoff

Append a section "Rehearsal on the merge preview" to
`handoffs/agy3-a21-rebuild-runbook.md`: the exact command, exit status, the
builder's printed registration and roster sha256 (label them preview values
that will not match the real ones), the BC1 sizing line (workers, groups,
calls, aggregate input tokens against 4,500,000), every warning or note it
printed, the before/after comparison, and what it does and does not
establish. No at-sign handles. Print the file's path and new SHA-256, then
stop.

## Bounds

No edits outside that one handoff file and the rehearsal directory. No
network, no provider calls, no tests, no pushes, no comments, no merge. Do
not touch `launch-a21` beyond reading it.

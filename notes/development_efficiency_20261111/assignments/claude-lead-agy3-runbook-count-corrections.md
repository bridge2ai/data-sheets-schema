# AGY3 follow-up from the Claude lead: three corrections to runbook section 2

Your section 2 table of the six pinned items that moved between M4
`673838c51` and the merge preview `44b8a6595` is **confirmed** twice: by
AGY2's mechanical check and by an independent lead check
(`tmp/a21-pinned-closure-20261111/lead_independent_check.json` in the report
worktree: 82 path and hash pairs, all equal to the M4 bytes, exactly your six
differing at the preview). The rehearsal result is also accepted.

Correct these three statements in
`handoffs/agy3-a21-rebuild-runbook.md`, and nothing else:

1. **The pinned Python file counts.** The registration pins **61** unique
   Python files, not 50: 53 under
   `selection.stage_contracts.request_code_sha256` and 59 under
   `bounded_carry.contract.code`. Four moved, so **57** are unchanged, not
   46. Take the numbers from the lead's JSON (count the `rows` whose path
   ends in `.py`) rather than retyping them from this note.
2. **The inputs are in git.** `CHORUS_preprocessed.txt`, `CHORUS_chunks.yaml`,
   `chorus_omission_context.json` and `source_manifest.yaml` are tracked
   files, identical at both commits and on disk in `launch-a21`. Remove any
   wording that calls them outside git.
3. **The two calibration notes.** The registration carries two sha256
   constants that `bc1_registration.py` hard-codes for review notes
   (`bc1_fit_calibration_claude_2026-10-28.md` and
   `bc1_8f83d6cb3_claude_review_2026-10-28.md`) that are not tracked in git.
   Add one line to section 6 (open items): the constants are unchanged
   because `bc1_registration.py` is unchanged, and the notes themselves were
   not located in the inspected checkouts (unverified, not absent).

Add one line under the section 2 heading saying the table was checked
mechanically on 2026-11-11 and by which two files.

Bounds: edit only the runbook. No other writes, no runs, no network. No
at-sign handles. Print the runbook's path and new SHA-256, then stop.

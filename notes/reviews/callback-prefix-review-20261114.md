Callback prefix implementation review, issue 6233, 2026-11-14

The read-only review of the draft found one admission-lifetime defect: removing
the weak registry entry did not invalidate an owner retained by a captured run.
An old transaction could therefore consult semantic checkpoints after its
verified admission scope closed. The follow-up fix adds a weak admission
reference, checks active admission before lookup/publication, and closes and
clears the owner during loader teardown. A retained-transaction regression and
the real-worker harness cover closure. The lead must file this finding as a
GitHub issue; this helper assignment prohibits GitHub writes.

Two earlier development checks also found and corrected draft defects under
issue 6233: cached decisions retained predicted journal prefix bytes, and an
overlapping older transaction could rewind the owner's byte anchors. Compact
decisions now retain only the new records and predicted journal pin; a new
epoch check refuses stale commits. Both have focused regressions. No deadline,
window, acceptance rule, protected file or pin was changed to address them.

This note records the findings, not final test outcomes. The final handoff and
saved test outputs report validation against the resulting committed source.

A subsequent read-only pass found that direct observation checkpoint access
bypassed the retained-owner lifetime guard. The expanded closure regression
failed before the follow-up fix; observation checkpoint reads now use the
same active-admission and effective-binding checks as stage lookups.

The same pass found a standalone validation-order regression: completion
lookahead parsed the final record before the original history size checks.
The focused regression passes on the assignment base and failed on the draft.
Standalone wrappers now directly enter their original full derivation paths;
completion also goes directly to independent full replay.

The closed graph guard now refuses the alternate package namespace as well
as unknown modules in the canonical namespace. The lead must file these
additional findings; the helper has made no GitHub writes.

# Codex helper assignment from the Claude lead: can the usage capture be taken closer to the reservation?

Track: native (not on the API route). Source and record reading only. No run,
no edit.

**A21 is live.** The owner had the lead launch the CHORUS API canary at
2026-11-12T03:41:33Z from `d4d-executions/launch-a21`. Do not run anything in
`launch-a21`, do not read its run directories while it runs, and do not use
the provider key.

## Why this is being asked now

Your audit (`handoffs/codex-native-launch-verification-audit.md`) closed the
trimming route: 0 s of proven saving against about 44.2 s needed. The owner
has now asked where the native arm stands. Before the lead tells the owner
that the arm cannot reach its reservation under the present rule, one route
is left that the lead has not seen examined: the timing of the capture
itself.

From the 382f measurement: the capture is taken 10.8 s before the launch
begins; the launch then spends 243.4 s of process CPU (295.7 s wall on the
contended host) before the pre-reservation check, which allows 210 s and saw
306.5 s.

## The question

**Could the subscription observation be taken, or taken again, after the long
verification and immediately before the reservation, under the same
authority? And do the records already answer this?**

Read first, so that nothing already decided is reopened:
`handoffs/private-postaccept-design.md`, the rejection record
`review-post-acceptance-design.md`, issues 5836, 5837 and 5722,
`reviews/remaining_postaccept_feasibility.md`.

Then answer, from the source at `382f0dfd1ce863fdf257a77e2bbb2637dbe2f67b`
(`d4d-executions/codex-native-u1u3`, read-only), with file and line:

1. **What the capture is.** Who produces it, what it reads, what makes it
   costly or bound to something outside the process (an operator action, a
   command-line call, a rate-limited source), and why it is taken where it is.
2. **What the limits protect.** Where the 300-second age and the 90-second
   margin are defined, and which interval each one bounds.
3. **Re-capture immediately before the reservation.** Which invariants it
   would break (ordering, journal, authority, lock, single use), or none.
   Three possible answers: "already rejected in the records" (cite the
   passage), "possible in principle" (list what would have to be shown; no
   design and no patch), or "cannot tell from source" (say what evidence
   would decide it).
4. **Draft PR 5871.** It removes one of three full reconstructions on the
   accepted route. From the per-call costs in the 382f measurement the lead
   estimates about 10 s of the 44 s or more that is needed. Confirm or
   correct that figure.
5. **One paragraph for the owner.** On the evidence, is there a route by
   which this arm reaches its reservation within the present rule on this
   host? If there is none without changing the rule or the design, say so
   plainly.

"Already rejected, here is where" is a complete and useful answer.

## Bounds

- Read-only: no edits to any source worktree, no test, no diagnostic, no
  composition, no config change, no provider call. The diagnostic is not to
  be repeated (`lead-cpu-monitoring-rerun-382f0dfd1ce8.once.json`).
- No design and no patch.
- Write only the report:
  `codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/codex-native-capture-timing-question.md`,
  and any helper script beside the lead's under
  `codex-development-efficiency-20261111/scripts/adhoc/`.
- No commit, push, issue, comment or STATUS edit. No at-sign handles.

Print the report's path and SHA-256 and stop.

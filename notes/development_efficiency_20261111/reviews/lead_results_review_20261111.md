# Lead results: final factual review

2026-11-11. Read-only review of
`notes/development_efficiency_20261111/handoffs/lead-results.md`, SHA256
`5e962953bad3a672109342785a7d772d5b06c892e9ec2886a94cfbe2af106cb2`.
The reviewed worktree HEAD was `76a443ee34103ed18f30041c111f9f2aae1af40e`.
Only this review note was written; no report/source edits, imports, tests,
remote mutations or new runtime were performed.

**Verdict: no new substantive finding within the assigned factual-review scope.**
Historical CI and matched-observer claims were checked against the existing
reviewed evidence; this was not a rerun or a new broad audit.

- Lines 21–29 correctly limit the matched observer result to guarded diagnostic
  process CPU. Both arms refused stale evidence; no native-inference, quiet-host
  or freshness-acceptance conclusion is drawn.
- Lines 39 and 54 separate the earlier freshness refusal from the import-fact
  component result. The retained comparison supports 57 eligible sources,
  1.392191 s cold versus 0.522727 s repeated and 1.731362 s first fills, each over
  three calls. The tiny route has no retained sources or claimed speedup.
- Line 52 matches the standalone capture artifacts independently reread here:
  log SHA256 `cdb2ceea4b56f572b16c9a89342822686be43a5972ce576f443f9def0557d393`,
  JUnit SHA256 `9191266e3ec67bd9f9c1cb23d67a84fe998f807058bfdec67a962b829133b791`.
  The log reports 1 passed/31 deselected in 188.04 s; JUnit has one passing case,
  no failures/errors/skips, suite time 187.971 s. Both retained file mtimes are
  05:24:20 UTC. These reside in
  `agy-native-path-alias-parity-20261111/tmp/capture_recheck_5838_5847/` beneath
  the shared `d4d-executions` directory. The report correctly distinguishes this
  standalone software-boundary pass from combined-source/fixed-supervisor proof
  and does not claim a 30-second execution cap.
- Line 56 agrees with `capture_adapter_final_review.md`: 33 distinct passing
  cases across several invocations, not a single final 33-pass run; the corrected
  cleanup reserve was source-reviewed, not rerun.
- The CI discussion preserves the old-head green versus current-head cancelled
  distinction; identical trees do not transfer a green check to the new head.

## Ordinary status refreshes

These are later status changes, not newly discovered implementation defects:

1. Line 62 should name full integrated source
   `382f0dfd1ce863fdf257a77e2bbb2637dbe2f67b` and replace pending-review/5856-blocked
   wording with the completed independent integration review and the lead's
   bounded release. `native_capture_ast_integration.md` records clean source
   review at 05:39:47 UTC and the resolved exact-branch check. This clears only
   the approved sparse preparation, same-manifest equivalence and fixed capture
   route; it is not a combined-source runtime pass or generic setup clearance.
2. Line 48 may now state duplicate run42966522505 **confirmed cancelled** at
   05:39:55 UTC, elapsed 6m34s. `analysis_replacement_ci.md` and its retained final
   snapshot confirm that old run42963052291 passed in 37m10s, while the replacement
   aggregate failed following cancellation. Current-head full CI remains nongreen.

Source approval and the bounded runtime release do not establish that subsequent
preparation, equivalence, capture or cleanup has completed; add those outcomes
only when the native owner supplies the corresponding evidence.

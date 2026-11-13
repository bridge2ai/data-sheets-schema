# AGY3 assignment from the Claude lead: A21 rebuild runbook for the API-only route

Track: final generation (first priority). Read-only. Deliverable is one file.

## What I accepted and what I corrected in your reconciliation

Your blocker table is collected (terminal capture under
`handoffs/captures-20261111/`) and I accept its structure: merge of PR 5808,
the owner's sequencing release, the A21 rebuild with offline preflight, and
the owner's launch word are the four gates; the protected `api_runner.py`
postimage `830eec1e…` and the D128 scanner items are native-integration
matters, not API-only prerequisites.

Three corrections, which the runbook must carry:

1. **The specificity scan does not pass on PR 5808.**
   `evidence/specificity-summary.json` records `exit: 1` with nine violations,
   all under `run_controllers` and zero under `api`. They are the retained
   open issues 5582 to 5590. Say that, not "passes".
2. **The budget is not settled by D88.** D129 (STATUS.md line 595) says the
   owner gives the launch word for the rebuilt registration "within the ~$25
   slice". D88's $60 slice and $51 stop were given for the M4 registration
   `d4ac7f88…`, suspended by D89, and under D93 apply "only if the owner
   reinstates" them. Quote both and present the figure as an owner choice.
3. **D89, D93 and D129 are recorded owner decisions that hold A21 behind
   native integration.** Nothing in STATUS.md releases them. The lead is
   asking the owner for that release explicitly. The runbook must state the
   hold as current fact and must not assume the release.

## Deliverable

Write `handoffs/agy3-a21-rebuild-runbook.md` (in this notes directory's
`handoffs/`), short enough for the owner to review in one sitting:

1. **Ordered steps after PR 5808 merges**, each with the exact command, the
   directory it runs in, who runs it, and the persisted output that proves it
   worked (a file and what it must contain, never an exit code). Use the
   placeholder `<MAIN_AFTER_5808>` for the merge commit. Cover: where the
   launch base lives (the `launch-a21` tag or its successor), rebuilding the
   CHORUS generic_v10 (BC1) registration and
   `shared_generation_batch_roster_v1`, the offline check and the no-spend
   dry-run, and the registration review.
2. **What the M4 packet pinned and what has moved since** (`673838c51` to
   current main plus PR 5808): schema 3.2.0 to 3.2.1 and its digests, PRs
   5532, 5620, 5677, 5678, and anything else the registration hashes. This is
   the scope of the re-review.
3. **The launch step as the owner would run it** (D43: the owner launches
   personally), the stop trigger and who may run `d4d api stop`, the
   wall-clock cap, and each figure's source decision quoted with its
   STATUS.md line.
4. **The canary verification checklist**: which files must be on disk and
   non-empty, which counters must have moved, and what
   `docs/final-generation-acceptance.md` requires before any batch.
5. **What can be exercised for free before the merge**, if anything: is there
   a no-write plan or dry-run that could run against a local merge preview
   without creating a registration at a real label, and what must be on disk
   for it (the preview worktree
   `d4d-executions/claude-pr5808-combined-20261111` is sparse: no `data/`, no
   `notes/`). Describe it; do not run it.
6. **Open items you could not verify**, each marked unverified, not absent.

## Bounds

- Read-only. No edits outside the one deliverable file. No tests, scanner
  runs, registration builds, dry-runs, provider calls, network reads, pushes,
  comments or merges.
- Use the known packets and notes: `d4d-executions/plans/a21_launch_packet_2026-11-05.md`,
  `plans/reviews/a21_registration_review_2026-11-05.md`, STATUS.md decisions
  D07, D22, D43, D58, D64, D88, D89, D93, D129, `agy4-prerequisites.md`, and
  `docs/final-generation-acceptance.md` on the PR 5808 branch. No walks of
  execution trees. The disk has about 12 GB free: create nothing large.
- No at-sign handles anywhere in the file.
- When the file is written, print its path and SHA-256 in your terminal and
  stop. Do not start follow-ups.

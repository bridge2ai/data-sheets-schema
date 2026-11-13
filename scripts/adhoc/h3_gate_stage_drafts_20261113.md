# Historical RF17 stage drafts

The adjacent `h3_gate_stage_worker_draft_20261113.py` and
`h3_gate_stage_roles_draft_20261113.json` preserve the initial design prepared
while the gate worktree was frozen. Neither draft was executed or tested.
Do not invoke the draft worker: its required final source identity is the gate
worktree's `scripts/adhoc/h3_gate_stage_worker_20261113.py`, so the draft's own
path fails its runtime guard.

The maintained implementation is in sibling
`codex-native-pin-comparison-20261113`, first committed as `03f203709`, with the
nonblocking FIFO-reader follow-up in `b18161637`. That implementation also binds
the actual canary input manifest and both worker attestations to the current
reference packet (RF18). These historical drafts predate those corrections and
are not an execution entry, validation proof, or source for a fresh rehearsal.

The original bytes remain here as provenance. Test results for the maintained
implementation belong to its separate gate-worktree commits and external
scratch cohorts; they do not attest these drafts.

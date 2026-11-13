# AGY4 follow-up from the Claude lead: execute the two split tests once, by node id

## Lead review of your implementation

`e999aa7453ffe2e8ba389767463260e65977480c` is reviewed against main. The test
diff is a faithful move: the mutation bodies, the sandbox and every assertion
are unchanged, the original function name is kept so the `routing-portable`
target does not move, and each function builds its own capture. Accepted as a
frozen candidate. Two notes for the record:

- Your **design** table (section 1.3 of `agy4-routing-portable-split.md`)
  described several mutations that are not what the code does: "flip last
  byte" where the code appends a comment line, `rows[0].pop('routing_admission')`
  where the code pops the first admission row, named refusal messages where
  the code accepts either exception type. Your **implementation** table is
  the accurate one. Add one sentence to the design handoff saying its
  section 1.3 descriptions of calls 10 to 21 are superseded by the
  implementation handoff's table.
- Neither split function has executed anywhere yet. The lane canary stopped
  at full-tree collection, which the sparse checkout explains.

Where this slice stands: AGY1's chunk sharding is stopped (a replay on real
per-test timings showed it slows the slowest shard). With eight ordinary
shards the slowest one sets pull-request wall time, so this lane split alone
changes little. It becomes the binding improvement only if the owner raises
the shard count, which is being sized as an option. Until then nothing is
pushed.

## Task: one execution of each new function, by node id

The lane selection is already covered by `tests/test_ci_sharding.py` and your
collect-only canary. What is missing is that the two bodies run to the end.

The lead has added `notes/claudecode_direct` to your worktree's sparse
checkout, which also materializes the files directly under `notes/`,
including `notes/D4D_MISSING_URI_RECOMMENDATIONS.tsv` that `draft_files`
reads.

Run, with the primary checkout's interpreter and `PYTHONPATH=src`, from your
worktree root, each once:

- `tests/test_source_heading_runtime_api.py::test_actual_completed_capture_refuses_tampered_bytes_and_ledger`
- `tests/test_source_heading_runtime_api.py::test_actual_completed_capture_is_portable_and_refuses_changed_bytes`

Rules:
- `-p no:cacheprovider`, a `--junitxml` per run, and a `--basetemp` outside
  any git worktree (for example under
  `d4d-executions/scratch-agy4-a2-basetemp-20261111/`). No
  `-o tmp_path_retention_policy=none`.
- Check `uptime` first; do not start while the one-minute load is above 25.
- You may run the two at the same time as two separate processes with
  separate base temps, or one after the other. 45 minute cap each.
- One attempt each. If a run fails for a reason a missing sparse path
  explains, name the path and stop; do not add paths and do not retry. If it
  fails inside the test body, that is a finding: keep the log, diagnose
  read-only, change nothing.
- No edits to the five committed files. No git writes except none. No push.

## Handoff

Append a section "Execution by node id" to
`handoffs/agy4-routing-portable-a2-implementation.md`: commands, exit
status, JUnit counts, wall time of each, and the two logs' paths and
SHA-256. Add the one-sentence correction to the design handoff. No at-sign
handles. Print both files' paths and SHA-256 and stop.

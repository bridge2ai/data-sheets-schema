# AGY4 assignment from the Claude lead: the routing-portable lane, read-only design

Track: CI efficiency (second priority). Read-only. Deliverable is one file.

## Your diagnostic assessment: collected, and held

`handoffs/agy4-cpu-diagnostic.md` section 7 is read and accepted as an
account of the retained evidence: fixture materialization completed at
+555 s under 5.5 load per CPU, the launch phase was cut off at the 881 s
driver limit, and the phase metrics were never flushed, so the timeout cannot
be attributed to source `382f0dfd`. Your proposed next witness, one existing
`cpu-monitoring` run on the existing contract when the one-minute load per
CPU is under about 2.5, is a genuine native diagnostic and needs the private
configuration armed again. No current authorization covers that. It is
recorded as an option for the owner and is not released. Do not prepare it.

## New task

On pull requests the workflow's critical path is two jobs within 90 seconds
of each other: the slowest ordinary shard (33m08s in run 42947560899) and the
dedicated lane `routing-portable` (31m38s), which runs the single test
`tests/test_source_heading_runtime_api.py::test_actual_completed_capture_is_portable_and_refuses_changed_bytes`.
AGY1 is implementing a change for the ordinary shards. Unless this lane also
gets shorter, pull-request wall time improves by at most about 1m30s.

Design the smallest change that shortens this lane while every check it makes
today is still made. Read the current source on main `925d726d` (a sparse
checkout of that tree plus PR 5808 is at
`/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/claude-pr5808-combined-20261111`;
read only, do not write there). Establish, with file and line evidence:

1. **Where the 31 minutes go**, from the saved run responses and logs the
   earlier CI analysis kept (use them; fetch nothing): the one `api.execute`,
   the 21 sequential tamper-mutation `recheck_completed` reconstructions, and
   anything else. Give seconds where the evidence has them and say
   "unmeasured" where it does not.
2. **Whether the mutations are independent** given one completed capture: can
   each run against its own copy of the same completed state, or does one
   mutate what the next reads?
3. **The options, each with its cost**: for example, more dedicated lanes
   each owning a subset of the mutations (the completed capture is then
   built once per lane: what does that cost?); parametrized cases inside one
   lane run with xdist (the plugin currently refuses multiple processes in a
   dedicated lane, and `_DedicatedCaseOutcome` requires exactly one node:
   what would have to change, and what guarantee would that weaken?); or
   building the completed capture once and sharing it across cases.
   For each: files touched, what stays byte-for-byte the same check, the
   expected lane time with its arithmetic, and the new floor.
4. **What must not be done.** AGY1 already noted that the repeated catalog
   and schema reconstructions in `source_heading_routing.py`,
   `source_heading_runtime.py` and `source_heading_completed.py` are
   intentional independent-verification invariants and must not be cached in
   production verifiers. Hold to that: the change is to how the test is
   scheduled, not to what production code verifies.
5. **Your recommendation**: one option, or "leave it" if no option keeps
   every check and saves a material amount.

## Bounds and handoff

- Read-only: no edits, no tests, no CI triggers, no network reads, no pushes,
  no comments. Protected files (`api_runner.py`, `shared_generation.py`,
  `canonical_hashes.yaml`, the boundary contracts, the scanner) are out of
  scope even as proposals.
- Write `handoffs/agy4-routing-portable-split.md` in this notes directory.
  No at-sign handles. Print its path and SHA-256 and stop.

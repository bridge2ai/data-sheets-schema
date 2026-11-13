# AGY4 assignment from the Claude lead: read the 382f diagnostic that completed

Track: native (not on the API route). Read-only analysis of saved JSON. No
runs.

## What happened (owner decision D132)

The lead ran the one approved `cpu-monitoring` diagnostic with
`codex-development-efficiency-20261111/scripts/adhoc/run_native_cpu_monitoring_once_20261111.sh`.
It is not to be repeated: `scratch-native-u1u3/u3m/lead-cpu-monitoring-rerun-382f0dfd1ce8.once.json`
blocks a second start.

- Evidence: `scratch-native-u1u3/u3m/wp1-382f0dfd1ce8-cpu-monitoring-lead-rerun-20261111`
  with its sibling `.outer.json`, `.outer.log`, `.supervisor.json`; canary
  `wp1-382f0dfd1ce8-canary-lead-rerun-20261111`; runner log
  `lead-cpu-monitoring-rerun-382f0dfd1ce8-20261111.log`; config evidence in
  `lead-config-rearm-382f0dfd1ce8-20261111/`.
- It completed normally: supervisor and outer return code 0, cleanup
  verified, no forced cleanup, no survivors, 452.4 s of a 900 s limit, one
  test passed. Both `phase-metrics/67941-diagnostic.json` and
  `67941-measurement.json` were written. The private config is back at
  `95a1f7d1…`.
- **Outcome: `genuine_refusal`** ("subscription observation is stale or
  future-dated"), `reservation_boundary: null`. Capture
  `2026-11-11T16:40:32.438672Z`, refusal observed `16:45:38.987869Z`.
- Host during the run: maximum 1-minute load per CPU 2.74, mean CPU 97.8%.
  It started at 1.44. It stays an unqualified contended CPU diagnostic.

The lead's first reading, to check rather than assume:

| Source | Fixture CPU s | Fixture wall s | Launch CPU s | Launch wall s | Max load per CPU | Outcome |
|---|---:|---:|---:|---:|---:|---|
| `3cc113e2606c` | 149.13 | 161.00 | 275.66 | 302.46 | 1.58 | genuine_refusal |
| `458887766eff` | 119.92 | 183.04 | 237.96 | 310.92 | 2.87 | genuine_refusal |
| `382f0dfd1ce8` (this run) | 110.88 | 138.84 | 243.40 | 295.75 | 2.74 | genuine_refusal |

If these hold, the launch phase alone spends more process CPU (243 s) than
the 210-second freshness target allows in wall time, so host contention is
not what stands between 382f and the target.

## Task

1. **Confirm or correct the table** from the three runs' measurement and
   outer records (`wp1-3cc113e2606c-cpu-monitoring-e1-observer-baseline-20261111`,
   `wp1-458887766eff-cpu-monitoring-post-5834-20261111`, and the new one).
   Add self user, self system and reaped-child CPU for each phase.
2. **Where the launch phase's CPU goes on 382f.** From the new
   `67941-measurement.json` (`calls`, `call_counts`, `registered_code_objects`,
   `phases[1]` rows 457 to 1122): the functions with the most CPU, with call
   counts, stated with whatever inclusive or exclusive meaning the file's own
   `cpu_policy` gives them. Do not add inclusive times across functions.
3. **382f against 458887, launch phase.** Same functions side by side: which
   got cheaper, which got dearer, which are new or gone (the row count rose
   from 537 to 665). Separate user from system CPU; system CPU rose from
   46.6 s to 59.8 s while user fell from 191.4 s to 183.6 s. Say what the
   records can and cannot attribute that to. One contended sample each: say
   plainly what is within run-to-run variation and what is not, and where
   there is no basis to tell.
4. **The freshness arithmetic.** From the diagnostic and measurement records:
   the time from capture to the start of the launch phase, and from capture
   to the refusal. State how much launch-phase time would have to go for a
   reservation boundary inside 210 s of capture, under the unchanged
   300-second limit and 90-second margin.
5. **What this run settles and what it leaves open** about your section 7
   questions (the earlier 382f run's cutoff; regression or not; where a next
   reduction would have to come from). Name the single most informative next
   step that needs **no** new run, if there is one.

## Rules

- Read-only. No run, no import of project code. Write only a script under
  `codex-development-efficiency-20261111/scripts/adhoc/` (usual header), its
  JSON under `codex-development-efficiency-20261111/tmp/diagnostic-result-20261111/`,
  and the handoff.
- Every number in a table comes from that JSON, written by the script; show
  the command. Mark each conclusion as measured, derived, or inference.
- No timing claim beyond what an unqualified contended diagnostic supports:
  no quiet-host figure, no speedup claim for live generation.
- No at-sign handles.

Write `handoffs/agy4-diagnostic-result-analysis.md` in this notes directory,
print its path and SHA-256, and stop.

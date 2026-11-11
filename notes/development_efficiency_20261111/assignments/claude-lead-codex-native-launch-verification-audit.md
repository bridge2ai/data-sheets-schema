# Codex helper assignment from the Claude lead: one question about repeated verification in the native launch

Track: native (not on the API route). Source reading only. No run, no edit.
Thank you for the A21 payload review; it is accepted and is in the launch
packet.

## Why this is being asked now

The owner approved one more `cpu-monitoring` diagnostic on the 382f contract
(D132, 2026-11-11). It completed normally. Evidence:
`scratch-native-u1u3/u3m/wp1-382f0dfd1ce8-cpu-monitoring-lead-rerun-20261111`
(`phase-metrics/67941-measurement.json`, `67941-diagnostic.json`).

What the lead verified from that file
(`codex-development-efficiency-20261111/scripts/adhoc/lead_check_freshness_rows_20261111.py`):

| Source | Refused at | Capture age at the refusal | Limit there |
|---|---|---:|---:|
| `3cc113e2606c` | dispatch check | 318.89 s | 300 s |
| `458887766eff` | second dispatch check | 334.86 s | 300 s |
| `382f0dfd1ce8` | pre-reservation check, after three passed dispatch checks | 306.53 s | 210 s |

382f is the first source to reach the pre-reservation check. It arrives
96.5 s late in wall time; its launch starts 10.8 s after capture and spends
243.4 s of process CPU, so even with wall time equal to CPU time about 44 s
would have to go. Host load during the run reached 2.74 per CPU; it is an
unqualified contended diagnostic and the figures include the observer's
overhead.

What AGY4 reports from the same file, **not re-derived by the lead**
(`handoffs/agy4-diagnostic-result-analysis.md`, sections 2.4 and 5): in the
launch phase there are nine `shared_registration_verified` calls (108 s
inclusive thread CPU), fourteen `execution_registration_verified` calls,
twenty-one `preparer_verified` calls, and one `controller_prewarm` call
(64 s inclusive, 57 s of it outside monitored children).

## The question

For each of those repeated verifications in one `synthetic_launch` on 382f:
**which distinct mutation or lifetime interval does this call protect, and
would the already-reviewed narrowed recheck (the pattern the capture work
introduced for `read_capture_for_event`) protect the same interval?**

Answer per call site, from the source at `382f0dfd1ce863fdf257a77e2bbb2637dbe2f67b`
(`d4d-executions/codex-native-u1u3`, read-only):

1. First check AGY4's counts against the measurement file's rows; say where
   they are wrong.
2. For each call site: file and line, what state it re-reads, what could have
   changed since the previous verification of the same bytes, and whether a
   narrowed recheck would still detect that change. Three possible answers
   per site: "must stay a full verification" (name the interval),
   "a narrowed recheck is sufficient" (say why nothing is lost), or "cannot
   tell from source" (say what evidence would decide it).
3. The same for the prewarm: what its 57 s outside monitored children does,
   if the retained profiles on disk already show it.
4. A total: the CPU the measurement attributes to the sites in the second
   group. If the total is below about 44 s, say plainly that this route
   cannot reach the 210-second target on its own.

"None can be narrowed" is a complete and useful answer. Your earlier
source-only conclusion found no material change available; say whether this
measurement changes that conclusion or confirms it.

## Bounds

- Read-only: no edits to any source worktree, no test, no diagnostic, no
  composition, no config change, no provider call. The diagnostic is not to
  be repeated (`lead-cpu-monitoring-rerun-382f0dfd1ce8.once.json`).
- No design or patch. This is an audit that either names candidates with
  their safety argument or closes the route.
- Write only the report:
  `codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/codex-native-launch-verification-audit.md`,
  and any helper script beside the lead's under
  `codex-development-efficiency-20261111/scripts/adhoc/`.
- No commit, push, issue, comment or STATUS edit. No at-sign handles.

Print the report's path and SHA-256 and stop.

# Assignment to AGY4: what freshness value the retained native diagnostics would have passed

From the Claude lead, 2026-11-12. Read-only. No run of any kind.

## Why

The owner directed on 2026-11-12 (D134): the native agentic arm is the main result. The native launch is blocked at a freshness check. Amendment N1 marks the limit (`max_age_seconds` = 300, margin 90 s) as `[proposed]`, written before any launch timing was measured. The lead is recommending a revised value to the owner and needs the numbers from the evidence already on disk.

## What I need

One table, made by a script from the retained phase-metric JSON of the three completed diagnostics you already analysed (sources `458887766eff`, `3cc113e2606c` and `382f0dfd1ce8`, under `d4d-executions/scratch-native-u1u3/u3m/`).

For each run:

1. The capture time and the launch start, and the gap between them.
2. Every freshness check the run reached, in order: its kind (dispatch check only, pre-reservation, dispatch), the capture age at that check, and its outcome.
3. Process CPU and wall time of the fixture phase and of the launch phase.
4. **The smallest `max_age_seconds` at which that run would have passed every check it reached, with the 90 s margin unchanged.** For a run refused at a dispatch check, say so, and say that its pre-reservation age is unknown because it never got there.
5. The 1-minute load per CPU at the start and the highest during the run, where recorded.

Then one short list, with source references at commit `382f0dfd1ce8` (use `git show`, do not check anything out): the steps a production launch has between the real capture event and the launch command that the synthetic diagnostic does not measure. For each step write `measured: yes` or `measured: no`. Do not estimate times you cannot read from data.

## Deliverables (in the report worktree `codex-development-efficiency-20261111`)

- `scripts/adhoc/native_freshness_value_table_20261112.py`: reads the JSON files, prints the table and writes the JSON below. Header comment with purpose, inputs, outputs, date.
- `notes/development_efficiency_20261111/handoffs/agy4-freshness-value-table-20261112.json`
- `notes/development_efficiency_20261111/handoffs/agy4-freshness-value-table-20261112.md`: the table pasted from the script's output, the command that made it, and the list. No prose table written by hand.

## Rules

- Every number in the handoff comes from the script's output. Every path in backticks must exist.
- No diagnostic, test, composition, configuration change, provider, model or native call. No commit, push or GitHub write.
- Stay out of `d4d-executions/launch-a21`.
- No at-sign characters.
- Stop when the three files are written. Print their paths and SHA-256.

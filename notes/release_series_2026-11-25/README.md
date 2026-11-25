# Release series 2026-11-25c: 5 projects x 3 replicates, headless Claude Code

Generated 2026-11-25 (UTC) for the owner's decision of 2026-11-24 to rerun the release series
(issues #6312, #6324; driver and runtime key from PR #6325).

## What was run

| | |
|---|---|
| Generator | `claude-fable-5-2`, effort `high`, headless Claude Code 2.1.332 |
| Condition, method, runtime | `generic_v9`, `claudecode_release`, `Claude Code (release)` |
| Labels | `2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep1`, `_rep2`, `_rep3` |
| Launch commit | `edd279fd27e1d4add4b0d536888638f55254a022` (main since 2026-11-25T06:59Z) |
| Driver | `scripts/adhoc/run_release_series_20261124.sh`, one project per session |
| Streams | `scripts/adhoc/run_release_series_stream_20261125.sh`, three replicate streams side by side |
| Account | claude-work subscription |
| Window | 2026-11-25T05:24:59Z to 08:17:15Z |

The first run (CHORUS replicate 1, 05:24:59Z) was the canary, taken through the same driver
and account; the other 14 started at 05:52Z after it passed. Two earlier canary labels,
`2026-11-25a` (provider overloaded before any model turn, nothing written) and `2026-11-25b`
(passed at the superseded commit `9ac7b91cb`), are not part of this series and are not
committed.

Each replicate ran in its own launch worktree. The worktree directory names do not match the
replicate numbers, and each provenance record's `repo.resource_root` names the directory:

| Replicate | Launch worktree directory | Order |
|---|---|---|
| 1 | `release-series-20261125-rep2` | CHORUS (canary), AI_READI, CM4AI, VOICE, VOICE_PEDIATRIC |
| 2 | `release-series-20261125-rep1` | CHORUS, AI_READI, CM4AI, VOICE, VOICE_PEDIATRIC |
| 3 | `release-series-20261125-rep3` | CHORUS, AI_READI, CM4AI, VOICE, VOICE_PEDIATRIC |

## Files here

- `launch/`: per record, the instruction sent (`.md`), the launch record (`.launch.txt`) and the
  rendering specification (`.render_spec.json`).
- `gates/`: per record, the driver's gate file as written at the end of the run.
- `streams/`: the three stream logs, with each budget check.
- `series_2026-11-25c_summary.tsv`: one row per record, from the gate files and transcripts
  (`scripts/adhoc/summarize_release_series_20261125.py`).
- `evidence_boundary_scan.txt`: every tool call that names generated-record territory other
  than the run's own files (`scripts/adhoc/scan_release_series_evidence_boundary_20261125.py`).

The transcripts (about 60 MB) stay in the launch worktrees and are not committed.

## Results

All 15 records ended with `GATES: PASS`: one exact model on every model message, schema-valid
full and core records, `receipts check --strict`, the scope check, `runs check --strict`, the
render gate (`match`) and no absolute home-directory path in what the run wrote. The same
record gates were rerun on the copies in this branch
(`scripts/adhoc/check_release_series_assembled_20261125.sh`): 15 of 15 pass.

No run was retried by the provider for overload, and no run's result lists a permission
denial. The summarizer reads those two counts from the transcript's `api_retry` events and
the result's `permission_denials`; it was checked against canary `2026-11-25b`, which has four
retries and one denial.

Total cost at list price as reported by the sessions: 251.49 USD (8.47 to 22.64 per record).

## What a reader should know before using or selecting from these records

1. **Receipt coverage differs in one record.** AI_READI replicate 1 has a receipt on 414 of
   453 receiptable slots; the other 14 records have one on every receiptable slot. The 39
   slots are mostly entry labels and enumerated or boolean leaves (`name`, `bias_type`,
   `limitation_type`, `is_representative`) of entries whose other leaves are receipted.
   Reported by the check, not gated. `d4d runs select` ranks coverage after validity.
2. **The gate's "recorder attempts" count is above one for three records, and none was a
   failed recording of a changed record.**
   - AI_READI replicate 1 (count 3): one `provenance record --help` call, one recording, and
     one re-recording after the session corrected three sentences of its reconciliation
     report. The full and core records did not change between the two recordings
     ("validation: carried forward").
   - VOICE replicate 2 (count 2): one recording, and one re-recording after the session added
     a section to its reconciliation report. Full and core unchanged.
   - CM4AI replicate 2 (count 2): the first recorder line was refused for lacking the
     `--phase` flags and wrote nothing; the second recorded.
3. **Evidence boundary.** The driver's gate checks the paths of the Read tool only (none
   outside the run's own files). The scan here covers every tool call. It lists 56 calls, all
   shell commands of two kinds: 46 name the run's own label directory (`ls` listings,
   `mkdir -p`, and own-project file paths built by string concatenation), and 10 name the
   `claudecode_release` method directories (`ls` listings, or a path prefix assigned to a
   variable). A listing shows the names and sizes of sibling projects' records of the same
   replicate; no call reads the content of another project's or another label's record,
   evaluation output, rendered HTML or the attic. Shell variables used as paths were resolved
   and all name the run's own files, the bundle, the chunk manifest or the schema.
4. **Not rated, not selected.** No rubric evaluation and no `d4d runs select` mark is in this
   branch.
5. **Not checked here**: that a chunk marked `nothing_relevant` held nothing for the record,
   and that a verified snippet supports the value it is attached to. Both are review
   judgements.

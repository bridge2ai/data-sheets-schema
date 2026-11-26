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
- `evidence_boundary_scan.txt`: the tool calls whose input names generated-record territory
  other than the run's own files (`scripts/adhoc/scan_release_series_evidence_boundary_20261125.py`).
  The committed copy is the script's output with the launch worktrees' parent directory removed
  from two `cd` lines; the script itself prints the absolute path.

- `review_1_pr6349.md`: the independent read-only review of PR 6349 at commit `0dd706fba`, as
  written. Its check scripts are `scripts/adhoc/review_pr6349_*_20261125.py`; they read the
  transcripts in the launch worktrees and take the worktrees' parent directory from
  `D4D_EXECUTIONS_ROOT`.

The transcripts (about 60 MB) stay in the launch worktrees and are not committed.

## Results

All 15 records ended with `GATES: PASS`: one exact model on every model message, schema-valid
full and core records, `receipts check --strict`, the scope check, `runs check --strict`, the
render gate (`match`) and no absolute home-directory path in what the run wrote. The same
record gates were rerun on the copies in this branch
(`scripts/adhoc/check_release_series_assembled_20261125.sh`): 15 of 15 pass, and a label that
does not exist fails every check.

No run has an `api_retry` event of any status, and no run's result lists a permission
denial. The summarizer reads those two counts from the transcript's `api_retry` events and
the result's `permission_denials`; it was checked against canary `2026-11-25b`, which has four
retries and one denial.

Total cost at list price as reported by the sessions: 251.49 USD (8.47 to 22.64 per record).

## What a reader should know before using or selecting from these records

1. **Receipt coverage differs in one record.** AI_READI replicate 1 has a receipt on 414 of
   453 receiptable slots; the other 14 records have one on every receiptable slot. Of the 39
   slots, 29 are `name` leaves (28 entry labels, and `maintainers[0].name`, a factual value),
   five are enumerated or boolean leaves (`bias_type`, `limitation_type`, `is_representative`,
   `compensation_provided`, `sensitive_elements_present`), one is a short free-text category
   (`use_category`, whose range is a string), and four are
   free-text statements a reviewer should sample: `direct_collection[0].collection_details`,
   `raw_data_sources[1].source_description`,
   `participant_compensation[0].compensation_type` and
   `missing_data_documentation[0].missing_data_causes`. Each sits in an entry with at least one
   receipted leaf. Reported by the check, not gated. `d4d runs select` ranks coverage after
   validity.
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
   outside the run's own files). The scan here reads the input of every tool call for paths
   under `d4d_concatenated`, evaluation outputs, rendered HTML, per-source records, the attic,
   other launch worktrees and earlier labels. It lists 56 calls, all shell commands of two
   kinds: 46 name the run's own label directory (`ls` listings, `mkdir -p`, and own-project
   file paths built by string concatenation), and 10 name the `claudecode_release` method
   directories (`ls` listings, or a path prefix assigned to a variable). A listing shows the
   names and sizes of sibling projects' records of the same replicate.

   The scan does not see: the worktree's `.temp/launch/` (sibling instructions and
   transcripts), the account's per-worktree session directory, a recursive search from a broad
   root that names no record path, `notes/`, or what a tool printed. The independent review of
   PR 6349 (review 1, finding F2) checked each of those routes in the 15 transcripts directly:
   the only tools used are Read, Bash, Write and Edit, with no subagent and no web call; no
   call reads a sibling transcript, instruction or session file (one `ls .temp/launch` and one
   `ls` of a sibling's schema digest show names only); no recursive search targets anything but
   `src/` or a single file; every command-line entry point carries the run's own label and
   project; and no tool-output line of 40 characters or more matches another record,
   evaluation, rendered page or attic file. On that evidence no other record's content reached
   a session. A foreign value shorter than 40 characters printed by a tool would not be caught
   by the output comparison.
4. **Rated and selected on 2026-11-26, after the records were merged.** One replicate per
   project carries a `d4d runs select` mark; `CANONICAL_SELECTION.md` names them and gives
   the rubric scores (`rubric_scores_root_scope_v6.tsv`), and `html/` holds a preview of
   every run. The evaluation files themselves are in PR #6372.
5. **Not checked here**: that a chunk marked `nothing_relevant` held nothing for the record,
   and that a verified snippet supports the value it is attached to. Both are review
   judgements. The receipt check counts 109 verified snippets, in 12 of the 15 records, that
   share no token with the value they are attached to (most in VOICE_PEDIATRIC replicates 3
   and 1, with 22 and 21).
6. **The report check read no claim in 8 of the 15 reconciliation reports** (AI_READI
   replicates 1 and 2, CHORUS 1 and 3, CM4AI 2, VOICE 1 and 3, VOICE_PEDIATRIC 2). A zero there
   means no readable claim, not a measured clean report. The other seven hold 9 claims and no
   finding.
7. **Identifiers differ between replicates, within the declared scope.** VOICE_PEDIATRIC
   replicate 1 uses the project-level DOI as `id` and the release DOI as `doi`; replicates 2
   and 3 use the release DOI for both. VOICE replicate 3 gives the version DOI as `doi`;
   replicates 1 and 2 use the project DOI for both. Only CM4AI replicate 2 carries a `doi`.
   Every one is a declared alias of the right dataset and the scope check passes.
8. **One value defect seen in passing, with no systematic value review done:** VOICE replicate
   3 has `machine_annotation_tools[0].tools: ["OpenAI Whisper Large unknown"]`; the bundle says
   "OpenAI's Whisper Large model", and "unknown" is the model's addition.
9. **Launch records name the launch machine.** Each `launch/*.launch.txt` gives the resolved
   path of the `claude` binary and the account used; each provenance record's
   `repo.resource_root` is absolute by design.

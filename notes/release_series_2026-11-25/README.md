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
| Account | a Claude subscription account, through headless Claude Code |
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
- `streams/`: the three stream logs, with the decision of each budget check.
- `series_2026-11-25c_summary.tsv`: one row per record, from the gate files and transcripts
  (`scripts/adhoc/summarize_release_series_20261125.py`).
- `evidence_boundary_scan.txt`: the tool calls whose input names generated-record territory
  other than the run's own files (`scripts/adhoc/scan_release_series_evidence_boundary_20261125.py`).
  The committed copy is the script's output with the launch worktrees' parent directory removed
  from two `cd` lines; the script itself prints the absolute path.

- `review_1_pr6349.md`: the independent read-only review of PR 6349 at commit `0dd706fba`, as
  written apart from the removals listed below. Its check scripts are
  `scripts/adhoc/review_pr6349_*_20261125.py`; they read the transcripts in the launch
  worktrees and take the worktrees' parent directory from `D4D_EXECUTIONS_ROOT`.

The transcripts (about 60 MB) stay in the launch worktrees and are not committed.

## Removed from these notes (2026-11-25)

At the owner's decision (issue #6352) two things the run wrote are no longer in these notes:
the name of the subscription account the series ran on, and the estimates of that account's
weekly allowance that each budget check logged, with the figures they can be rebuilt from.
The repository history before this change was not rewritten and still holds them.

| File | Change |
|---|---|
| `launch/*.launch.txt` (15) | the `account:` line is replaced by a fixed line; since 2026-11-27 the home directory in the path of the `claude` binary is written `~/` and the closing words of the `environment:` line are the ones the driver now writes (see the extension below); every other line is as the driver wrote it |
| `streams/stream_rep*.txt` (3) | each of the 14 `budget:` lines keeps the decision, the next project, the replicate, the count of finished runs and the projects in flight elsewhere; the usage estimates, the limit and the amount spent are removed, and the line gains the key `"usage_estimates": "removed"` to say so |
| `README.md` | the Account row of the first table; the `streams/` and `review_1_pr6349.md` entries of the file list; this section |
| `review_1_pr6349.md` | five mentions of the account are reworded so that it is not named; two phrases that stated the budget calibration and a projected usage figure are replaced by wording without figures; the path of a session scratch folder, which named the launch machine's login and folders, is replaced by a placeholder (added 2026-11-26); the placeholders read `<session storage>` and `<session scratchpad>`; otherwise as the reviewer wrote it |
| `scripts/adhoc/release_series_budget_20261125.py` | the calibration constants and the comment that derived them are replaced by environment variables, which are checked; given the values the series used, it prints the same line as before |
| `scripts/adhoc/run_release_series_stream_20261125.sh` | the header names those variables; no change to what it runs |

`scripts/adhoc/redact_release_series_account_usage_20261125.py` makes the changes to the launch
records, stream logs, Account row and review report from the originals. The account name and
every text it replaces in the review report are its arguments and are not in the script.

What follows from it:

- The 15 launch records are no longer byte-identical to the files in the launch worktrees, and
  the 3 stream logs are no longer byte-identical to the stream runner's own logs (kept outside
  the repository). They differ in the lines above and nowhere else. Review 1 found them
  identical, which was true of the commit it read.
- `scripts/adhoc/review_pr6349_compare_notes_20261125.py` compares the launch and gate files
  of the checkout named `release-series-data-20261125` under `D4D_EXECUTIONS_ROOT`, not of the
  checkout it sits in, and never the stream logs. Pointed at a checkout of this state it
  reports the 15 launch records as different and the other 45 files as the same.
- The 90 record files, the instructions, the rendering specifications and the gate files are
  not changed by this removal. Later changes to the records are separate from it: the
  selection added a `canonical` block to five provenance records (PR #6373).
- Not removed by this change: the home-directory path of the `claude` binary in the launch
  records, which issue #6352 lists (it was written home-relative on 2026-11-27, below), and
  `repo.resource_root` in the provenance records, which is absolute by design and stays.
- After the calibration left the budget script, the published costs and decisions bound the
  account's usage (every check answered start under a limit the script still states) but do
  not determine it.

### Extended on 2026-11-27: one account line for every series, and no login in the binary path

The final review of the removal (issue #6426) asked that the launch records of every series
state the account in the same way, and that the login in the binary's path not be published.
At the owner's decision of 2026-11-27:

| File | Change |
|---|---|
| `notes/final_agentic_2026-11-22/launch/*.launch.txt` (16) | the `account:` line is replaced by the same fixed line as here, byte for byte; in the one record of the 2026-11-22 canary, the launcher in the launch command is replaced by the placeholder `<launcher>` |
| `launch/*.launch.txt` here (15) | on the `claude code:` line the home directory of the binary's path is written `~/` |
| `notes/final_agentic_2026-11-22/launch/*.launch.txt` (16), in a commit of its own | the other 17 home directories in these records (the `worktree:` line of each, and the directory in the canary's launch command) are written `~/`. The owner's decision named the binary's path; this goes one step further and can be undone alone: a revert of that commit restores the 16 records, and the part of this section that later edits touched (rows of this table and the paragraph after it) is then resolved by hand |
| `scripts/adhoc/run_agentic_fanout_20261122.sh`, `scripts/adhoc/run_release_series_20261124.sh` | a new launch record gets a neutral account line, and from the release-series driver a home-relative path of the binary |
| the same two drivers, `scripts/adhoc/run_rubric_eval_20261122.sh` and `scripts/adhoc/run_release_series_stream_20261125.sh` | the account to run on is not chosen in these files. The caller's environment chooses it: `D4D_SERIES_CONFIG_DIR` and `D4D_SERIES_OAUTH_TOKEN` (the configuration directory and the login token, either or both), or `D4D_SERIES_DEFAULT_LOGIN=1` for the login of the default configuration directory. Each driver stops before any launch when no choice is made, or when the directory is relative or not an existing directory. Each driver also stops when the default-login switch is given together with a directory or a token, or when `D4D_SERIES_ACCOUNT` is set, and the two earlier drivers pass no `D4D_SERIES_*` variable on to the session. The stream runner stops when the launch worktree holds no driver or one from before this change. The rubric-evaluation driver's worktree path starts at `$HOME`, and the release-series driver never writes a `/Users/<x>/` or `/home/<x>/` part into the binary's path, whatever `$HOME` holds and however `PATH` spells it |
| `launch/*.launch.txt` here (15), `review_1_pr6349.md` | the closing words of the `environment:` line are the ones the release-series driver now writes, which hold whichever of the two values the launcher was given; one placeholder of the review report is restated |

`scripts/adhoc/redact_launch_records_account_login_20261127.py` makes the changes to the 31
launch records and restates the placeholder in the review report. For the 15 records of this
series and for the report it runs after PR #6359's script: the published files are that
script's output followed by this one's. Its rules name no account and no login, so it needs
no private argument; `--check --other-home-paths` says whether a tree is in the final state.
The drivers were edited by hand, line for line, so no line of them moved.
`scripts/adhoc/check_series_driver_account_env_20261127.sh` runs each driver's launch lines
with a stub in place of `claude`. It shows that a session receives the account the caller
chose under Claude Code's own variable names and no `D4D_SERIES_*` variable, that each
driver stops without a choice or on a contradictory one, and, given the same account through
the new variables, that a session receives the same environment and arguments as before
the edit. The two earlier drivers otherwise pass the caller's environment on, as they did
when they ran; the release-series driver builds the session's environment from nothing.

What this does and does not achieve:

- The 31 launch records of the two series now state the account in the same words.
- The four scripts no longer read as they ran. In the three drivers, the lines that choose
  and check the account, the header lines that describe them, the launch-record lines named
  in the table above and, in the rubric-evaluation driver, the worktree path are of
  2026-11-27; in the stream runner, two lines are. Everything else in them is as it ran.
- A setup that started a session before the edit no longer does so by itself: the drivers
  stop until the account is stated through the variables above. Run a canary first; the
  edited drivers have launched nothing.
- This is not a guarantee about the rest of the repository: other tracked files are not
  changed (#6362).
- The fixed line keeps its date, 2026-11-25, in all 31 records, so that the two series
  carry one line; for the earlier series the decision is the one of 2026-11-27.
- A home directory is still written out in files this change does not edit: the 16
  instruction files of the earlier series (`notes/final_agentic_2026-11-22/launch/*.md`,
  320 lines), which are pinned by `instruction_sha256`; 10 lines of its gate files; and
  the record files, in `repo.resource_root` of every provenance record (by design) and,
  for the earlier series, also in the `# Schema:` header of each full record, the `path:`
  fields of each provenance record and four lines of reconciliation notes.
- `review_1_pr6349.md` describes the `claude code:` line as it was when it was reviewed.
- The repository history still holds every replaced line.

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
9. **Launch records named the launch machine.** Each `launch/*.launch.txt` gave the resolved
   path of the `claude` binary and the account used; the published copies no longer give the
   account, and give the path home-relative (see the removal section). Each provenance
   record's `repo.resource_root` is absolute by design.

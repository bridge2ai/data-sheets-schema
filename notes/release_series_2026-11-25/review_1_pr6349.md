# Review 1 of PR 6349 (data: release series 2026-11-25c), commit 0dd706fba

Independent, read-only review. Assembled worktree `d4d-executions/release-series-data-20261125`
(HEAD 0dd706fba, working tree = HEAD apart from untracked `.temp/`), launch worktrees
`release-series-20261125-rep{1,2,3}`, the 15 stream-json transcripts, and `gh pr view 6349`.
Nothing was written into any checkout. Not every command was individually bracketed, but at the
end one `find <tree> -newer <first helper file> -not -path '*/.git/*'` over all four worktrees
(assembled, rep1, rep2, rep3 including `rep3/.venv`) returned 0 files; the first helper file
predates every Python command I ran in the assembled tree. `git status --short` there still shows
only `?? .temp/`. Review helpers live in this session's scratchpad, not in a repository (list at
the end). Disclosure: one of my greps printed dataset contact email addresses (from the records)
into my own tool output while checking their provenance; none is copied into this report.

## Coverage of the eight areas

| Area | Coverage |
|---|---|
| 1 Copy fidelity and labelling | Full |
| 2 README / PR body claims | Full (one claim, the "pytest -m corpus 167 passed" pre-pin run, not re-run) |
| 3 Evidence boundary | Full for tool inputs; tool outputs checked by 40+ character line match plus an enumeration of every repository entry point called (short values printed alone would escape the line match); model thinking is not inspectable (blocks are empty, signature only) |
| 4 Model and launch facts | Full |
| 5 Committed content that should not be public | Full |
| 6 Test changes | Full (ran the three files plus `tests/test_backfill_checks.py`) |
| 7 Helper scripts | Full for the five scripts; driver (`run_release_series_20261124.sh`) only where its gate logic matters |
| 8 Record defects | Partial: structural scan of all 15 records, identity fields, placeholders and empties; no semantic reading of values against the bundle beyond spot checks |

## Findings

### F1. should-fix: the assembled-tree gate script can report `ok` for a record whose `runs check` did not run on it
`scripts/adhoc/check_release_series_assembled_20261125.sh` line 42 takes `runs check --strict`
exit 0 as a pass and sends its output to `/dev/null`. `runs check` exits 0 when no complete
run matches the filters (`src/data_sheets_schema/cli/runs.py` 584-600: runs filtered by
method/label/project and `is_complete`, failure only on `failed`/`bad_requests`/... lists, no
zero-match failure). Confirmed:

```
runs check --method claudecode_release --label 2026-11-25z_nonexistent_rep1 --project CHORUS --strict
-> "0 run(s) checked, 0 subject to the requirement, 0 failing" / "All runs ... satisfy it." exit=0
```

So any record that `runs check` does not select (zero matches) still prints `runs_check=0` and
`ok`. (Which copy defects would make `is_complete` skip a record I did not test; the demonstrated
fact is the zero-match exit 0.) The other sub-checks fail when their input is missing or bad, all
tested on scratchpad inputs or a nonexistent label: linkml validator on an invalid record exit 1,
on a missing file exit 2; `receipts check --strict` with no receipt exit 1 ("unchecked: no
coverage receipt"); `download scope --record <missing>` exit 2; `verify_request` returns
`absent`, not `match`.
For the actual copies this did not happen: I ran `runs check` per record in the assembled tree
and all 15 report `1 run(s) checked, 1 subject to the requirement, 0 failing`; the 15 launch
gate files show the same line. The driver's gate (not under review) has the same reliance on
the exit code but at least prints the count. Fix: require the `1 run(s) checked, 1 subject`
line, not only the exit code. Also my rerun of the script: 15 of 15 `ok`, exit 0, nothing
written.

### F2. should-fix (instrument, not the conclusion): the evidence-boundary scan misses whole routes; the README's "the scan here covers every tool call" overstates what it can see
`scripts/adhoc/scan_release_series_evidence_boundary_20261125.py` flags only tokens matching
`d4d_concatenated...` or its `OTHER` list, in tool inputs only. Routes it would not flag:
- `.temp/launch/` of the same worktree: holds the sibling projects' instructions and their full
  stream-json transcripts, which contain the sibling records verbatim (Write payloads). Not in
  `OTHER`.
- `~/.claude-work/projects/<worktree slug>/`: shared by every session launched in that worktree
  (session transcripts and `tool-results/`). The slug contains the own worktree name, which the
  scan exempts (line 73), so a read of a sibling session's file there passes.
- Broad roots without the territory token: `rg X .`, `grep -r X data/`, `find . -name '*_d4d.yaml'`,
  `cd data && cat */*/*/*.yaml`, Python `glob('**', recursive=True)` / `os.walk('.')`,
  `git show <rev>:<path built from variables>`.
- `notes/` (many notes quote record values), `data/ro-crate_packages`, other top-level `data/` trees.
- Tool outputs: a CLI the session runs that prints another record's content is invisible to an
  input scan.

I checked every one of these routes directly, so the README's conclusion holds:
- Tools used across all 15 transcripts: only `Read`, `Bash`, `Write`, `Edit` (counts per record
  match the gate files). No `Grep`, `Glob`, `WebFetch`, `WebSearch`, `Task`/`Agent`, `Skill`,
  `Workflow`, `SendMessage`, `RemoteTrigger`; no `server_tool_use` blocks; zero events with
  `parent_tool_use_id` (no subagent). The 15-43 `task_started` events per run are all
  `task_type: local_bash` (foreground Bash), not subagents.
- Independent path scan of all 1,771 tool inputs (any project name other than the run's own, any
  label or `_repN` other than its own, any absolute path outside the own worktree, any `data/`
  tree other than `preprocessed`/`d4d_concatenated`, any method directory other than
  `claudecode_release[_core]`): 6 hits, all benign: four `Read`s of `~/.claude-work/.../tool-results/*.txt`
  whose session ids equal the reading transcript's own `session_id` (checked for all four);
  `rep2 VOICE` ran `ls -la .temp/schema_digest_Dataset_AI_READI_rep2.txt` (a sibling's schema
  digest, listed not read); `rep2 VOICE_PEDIATRIC` grepped VOICE naming in the source manifest.
- `.temp/launch`: one call, `rep2 VOICE` `ls .temp/launch | head` (file names only). No read of a
  transcript, sibling instruction or render spec.
- No `find`, no `git show/log/grep/diff`, no `curl/wget`, no `cd` other than into the own worktree
  (15 in rep1 AI_READI), no `..`, no wildcard read over `data/`. All 26 recursive `grep -r`/`rg`
  calls target `src/`, a single schema/record/note file, or a variable resolving to one.
- All shell variables used in paths (`L`, `F`, `C`, `P`, `R`, `D`, `d`, `S`, `B`, `FULL`, `CORE`)
  resolve to the run's own label/files, the bundle, the chunk manifest or the schema. Each
  `.temp/playbook_view*.md` / `.temp/schema_digest_*` the runs read was written by that same
  session before it read it.
- Content-level check of tool OUTPUTS: every tool-result line (>= 40 chars, line-number prefixes
  stripped) that occurs in any of 4,513 files under `data/d4d_concatenated`, `data/evaluation*`,
  `data/ATTIC`, `data/d4d_html`, `data/d4d_individual` (548,765 distinct lines) and not in the
  run's allowed inputs (own bundle, own chunk manifest, own instruction, `src/`, `.claude/`,
  `CLAUDE.md`, the source manifest, own provenance/receipts/derived core) nor in text the session
  had itself written earlier in the transcript. Result: 2-4 lines per run, all tool boilerplate
  ("PASS: 79 schema-identical slots ...", "none is about a dataset its project declares distinct",
  a `semantic-review-required` warning, two slot-path strings). Limit: the line match needs 40+
  characters, so a short foreign value (a DOI, a grant id, a count) printed alone would pass it.
  To cover that, I enumerated every repository entry point the 613 Bash calls used: CLI
  `agents playbook`, `api prompts check`, `bundle chunk`, `derive core`, `download priority|scope`,
  `prompt render`, `provenance record`, `receipts check|invert|readdress|status-context`,
  `runs check|validate`, plus `--help` calls; Python imports of `receipts`, `schema_digest`,
  `grounding.check_run`, `identifiers.uriorcurie_slots`, `profiles.profile_named`,
  `report_claims.check_report`. Every `runs`/`receipts check` call carries the run's own
  `--label` and `--project`, and every `status-context`/`invert`/`readdress` call names the run's
  own `--receipt`; `api prompts check` reports prompt pins only. None of the whole-corpus or
  baseline readers (`runs select`, `compare-arms`, `api verdict`, `evaluate`, `review pack`,
  unscoped `status-context`) was called. On that basis: no other record's content reached any
  session through a tool input or a tool output that I can detect; the model's thinking is not
  inspectable.

Fix: widen the scan (`.temp/launch`, the account's projects directory, broad roots, `notes/`,
tool outputs) or say in the README what it does not cover; the conclusion should cite the direct
checks, not only this scan.

### F3. minor: the committed `evidence_boundary_scan.txt` is not the script's output
Rerunning the committed scan reproduces 56 flagged calls (46 label-directory, 10 broad), exit 1,
but two lines differ from the committed file: the committed copy has `cd release-series-20261125-rep2`
where the script prints the absolute `cd /Users/<user>/Documents/.../release-series-20261125-rep2`.
A hand redaction is reasonable, but the README presents the file as the scan's output; say it
was redacted (or redact in the script).

### F4. minor: home path, username and account name committed in a public repository
`gh repo view` reports the repository `PUBLIC`. Added files carry:
- `repo.resource_root: /Users/<user>/Documents/VIMSS/.../release-series-20261125-repN` in all 15
  provenance records: by design (the record contract documents it as absolute).
- `claude code: 2.1.332 (Claude Code) (/Users/<user>/.local/bin/claude)` in all 15
  `notes/.../launch/*.launch.txt`: not by design; the driver writes the resolved binary path.
- The account name `claude-work` and `CLAUDE_CONFIG_DIR=~/.claude-work` in the 15 launch records and
  the README ("Account: claude-work subscription"); the budget lines of the three stream logs
  expose weekly-allowance percentages of that account.
No tokens, keys, session ids, UUIDs or personal notes were found. The email addresses in the
records (172 distinct address-per-file occurrences) all occur verbatim in the record's own input
bundle (checked programmatically; none outside it), i.e. public dataset contacts carried from
the source documents, as in earlier series. The README's "no absolute home-directory path in
what the run wrote" is true of the run's outputs; it does not cover the launch records.

### F5. minor: README description of AI_READI replicate 1's 39 slots without a receipt is incomplete
Recomputed with `receipts.uncovered_receiptable_leaves`: 39 leaves: 29 `name` (entry labels:
collection_mechanisms x10, external_resources x8, prohibited_uses x4, sampling_strategies x3,
subpopulations x2, file_collections[9], maintainers[0]), six enum/boolean leaves (`bias_type`,
`limitation_type`, `is_representative`, `compensation_provided`, `sensitive_elements_present`,
`use_category`), and four free-text factual leaves the README does not mention:
`direct_collection[0].collection_details`, `raw_data_sources[1].source_description`,
`participant_compensation[0].compensation_type` ("Compensation for the study visit, paid through
the grant funding."), `missing_data_documentation[0].missing_data_causes` (a statement about
Alabama law). One of the 29 "labels" is a factual value too: `maintainers[0].name` ("AI-READI
team"). Each of the six I inspected has at least one receipted sibling leaf, so "entries whose
other leaves are receipted" holds, and "mostly labels/enums" is numerically true (35/39). Name the
free-text ones; they are the ones a reviewer should sample.

### F6. note: 109 "verified" snippets bear on no token of their value
`receipts check` reports, beside `snippets N/N verified`, "(k bearing on no token of their
value)": 109 snippets over 12 of 15 records (VOICE_PEDIATRIC rep3 22, rep1 21, VOICE rep3 14,
AI_READI rep2 14, ...). These are verbatim in the cited chunk but share no token with the value
they are attached to. Not gated; the README's "all snippets verified" and its point 5 ("not
checked here: that a verified snippet supports the value") cover it in principle, but the count
is worth stating for selection/review.

### F7. note: 8 of 15 reconciliation reports give the report gate nothing to read
`report_claims.claims_checked` is 0 on 8 of 15 blocks (AI_READI rep1/rep2, CHORUS rep1/rep3,
CM4AI rep2, VOICE rep1/rep3, VOICE_PEDIATRIC rep2); totals 9 claims, 2 prose-retention claims, 0
findings, matching the new test pins. Consistent with the agentic path (no dispositions table
required) and with the 2026-11-22 series, but a zero there is "no readable claim", not a
measured clean report.

### F8. note: cross-replicate identifier variance (selection-relevant, not a scope error)
- VOICE_PEDIATRIC: rep1 `id: doi:10.13026/mf9s-5r03` (the manifest's project-level referent_id)
  with `doi: 10.13026/h995-bt35` (release 1.1.0); rep2/rep3 use `h995-bt35` for both.
- VOICE: rep3 `doi: 10.13026/8xbn-nq66` (the 3.1.0 version DOI) beside `id` `37yb-1t42`;
  rep1/rep2 use `37yb-1t42` for both.
- CM4AI: only rep2 carries a `doi` (`10.18130/V3/HIGT4C`); rep1/rep3 none. CHORUS: no DOI in any
  (none in its corpus).
All are declared aliases of the right dataset in `source_manifest.yaml` scope; no VOICE record
identifies as the pediatric dataset or vice versa (scope check 2 records each, all pass). No
record has an empty or null leaf; no placeholder text (TODO/TBD/lorem/example.org).

### F9. minor: one small value defect seen in passing
VOICE rep3 `machine_annotation_tools[0].tools: ["OpenAI Whisper Large unknown"]`: the bundle says
"OpenAI's Whisper Large model" (three occurrences); " unknown" is the model's addition. Not
checked whether a playbook rule asks for a version token. Only seen because I grepped for
"unknown"; no systematic value review was done (area 8 partial).

### F10. note: helper-script measurement details (no wrong number in this series)
- `summarize_release_series_20261125.py` counts only `api_retry` events with `error_status == 529`;
  any other retry status would be silent. I counted `api_retry` events of any status in all 15
  transcripts: 0. So "no overload retry" holds, and more strongly no retry at all. Its
  `model_messages` column counts stream `assistant` events (216 for AI_READI rep1), not distinct
  messages (75 turns in `run_observed`); "one exact model on every model message" still holds
  (every assistant event names `claude-fable-5-2`; no `<synthetic>`; `modelUsage` keys only
  `claude-fable-5-2`).
- Rerunning the summarizer reproduces the committed TSV exactly apart from the order of the three
  `# ATTENTION` lines (worktree argument order). Cost total 251.49 USD, range 8.47-22.64: confirmed
  from the transcripts' `total_cost_usd`.
- `release_series_budget_20261125.py` drops the cost of any `is_error` result (underestimates
  spend after a failed run) and its calibration (6 points per 21 USD) is a single /usage delta.
  No effect here (no failed run; the final projection was about 75% against a 90% limit).
- `run_release_series_stream_20261125.sh` retried only zero-turn 529 results; the three stream
  logs show attempt 1 for all 14 stream runs, no overload, no STOP.

### F11. note: pre-existing study-specific example text in a file every run reads
`src/data_sheets_schema/receipts.py` (read by every run, 38 Reads in total) and
`notes/receipts_pattern_2026-08-27.md` (grepped by rep1 AI_READI and rep3 VOICE_PEDIATRIC) carry a
receipt example with a real-looking grant id (`OT2OD...` in the `funders[0].grant_id` example)
and "a longitudinal, multimodal ...". Three sessions saw it in a tool result. The id is not in
the AI_READI bundle and appears in none of the 15 records, so no leak resulted. Not introduced
by this PR; worth an issue against the neutral-generation scan, since it is in the generation
path's reading set.

## Area-by-area confirmations (what was checked and how)

**1. Copy fidelity and labelling.** `diff -rq` of each of the six label directories against its
launch worktree: identical (90 files; each launch worktree's method directories hold only that
one label). Every provenance record: `run.label`, `run.project`, `run.replicate` match its path;
`repo.resource_root` names the worktree the README maps it to (rep1 in `...-rep2`, rep2 in
`...-rep1`, rep3 in `...-rep3`); `repo.commit` edd279fd2; `record_generated_at` falls inside the
matching transcript's first/last event window for all 15 (e.g. AI_READI rep1 06:23:26 within
05:52:25-06:24:08). Launch `launched_at_utc` precedes each transcript's first event by 2-3 s.
All 45 `launch/` and 15 `gates/` files are byte-identical to the originals (60/60), and the three
`streams/stream_repN.txt` are byte-identical to `~/agent-work/data-sheets-schema/release-series-2026-11-25c/stream_repN.log`; the 15
`*.render.err` files were not committed (benign: render confirmations; 577 bytes max). Gate files
list the provenance at a smaller size than the committed file (e.g. 28,117 vs 31,658) because the
driver's `annotate-observed` step writes `run_observed` after the size listing: expected, not a
copy fault.

**2. Claims.** Table of minutes and slots, byte sizes, chunk/snippet counts, render `match`:
reproduced from gate files. Total cost and range: confirmed. Canary 2026-11-25b: its transcript
(in `~/agent-work/.../release-series-canary-evidence/attempts-25a-25b-at-9ac7b91cb`) has four
529 `api_retry` events and one `Bash` permission denial, as stated. No permission denial in any
of the 15 results; `permission_check_status` events all end `done`; no tool-error result text
mentions a permission or classifier block. Recorder attempts, read from the transcripts:
- AI_READI rep1: `provenance record --help` (06:21:28), recording (06:21:40, exit 0), three `Edit`s
  of `AI_READI_reconciliation.md` only, re-recording (06:23:13, "validation: carried forward").
  As stated.
- VOICE rep2: recording (07:49:09), one `Edit` adding a "Provenance record" section to
  `VOICE_reconciliation.md`, re-recording (07:50:35, "carried forward"). As stated.
- CM4AI rep2: first line without `--phase` refused ("this recorder line requires the run's phase
  history", exit 1), second with phases recorded (exit 0). As stated; that the refused call wrote
  nothing is not directly observable, but the second call overwrote the record anyway.
No `Write`/`Edit` of a full or core record between recordings in any of the three. Launch commit
edd279fd2 became main at 2026-11-25T06:59:24Z (PR 6325 merge), so the PR body's "launched at
edd279fd2 (main)" is loose (it was the PR head at launch); the README states it correctly.

**3. Evidence boundary.** See F2.

**4. Model and launch facts.** Every assistant event in all 15 transcripts: `claude-fable-5-2`
(125-242 events each). Init events identical across all 15 apart from `cwd`/ids: `model
claude-fable-5-2`, `permissionMode auto`, `mcp_servers []`, `apiKeySource none`, Claude Code
2.1.332, 25 tools (including `Task`, `WebSearch`, `Workflow`, `RemoteTrigger`, `SendMessage`,
`PushNotification`, cron tools; no advisor tool), 22 skills, 21 agents, 68 slash commands, 4
plugins all `path: builtin` (`cc-plugin-agents-md`, `-telemetry`, `-privacy`, `-plugin-authoring`),
no memory paths. No advisor use (no `server_tool_use`; gate "advisor calls: 0"). Canary vs the
other 14: normalised launch records are identical except `tree dirty paths: 1` for the three
CHORUS runs (first in each worktree) vs 3 for the other 12 (siblings' outputs present), and the
canary ran alone whereas the 14 ran as three concurrent streams on one account. Effort `high`
is a launcher assertion, not observable in the transcript (the record says so).

**5. Public content.** See F4.

**6. Tests.** `tests/data/report_claims_origins.json`: `basis_commit` unchanged, `origins` (278)
unchanged, `v8_origins` 16 -> 31 (15 additions, all `d4d provenance record`, no entry changed or
removed), `scope` text extended (old text kept as prefix). The two Python changes only update
four equality pins (31 blocks, 18 claims, 6 prose-retention; snippets 20,596, located 20,124,
not_verified 466 and unresolved 6 unchanged) and comments; no assertion removed or loosened. The
new pins are what the records produce: summed from the 15 `report_claims` blocks = 9 claims,
2 prose-retention, 0 findings; summed snippets 5,666 = 20,596 - 14,930. Ran
`pytest -p no:cacheprovider tests/test_report_claims_corpus.py tests/test_status_context.py
tests/test_backfill_checks.py` (PYTHONDONTWRITEBYTECODE=1, PYTHONPATH=assembled src): 303
passed, 0 failed, exit 0.

**7. Scripts.** F1, F3, F10.

**8. Records.** F6-F9. All 15 full records: non-empty, no null/empty leaves, top-level keys 27-70,
the right dataset per title/id; scope check pass.

## Not checked
- Whether `nothing_relevant` chunks really held nothing, and whether verified snippets support
  their values (review judgements; F6 gives the lexical-mismatch count).
- The PR body's pre-pin `pytest -m corpus` result and the specificity scanner numbers.
- CI: `gh pr checks 6349` at review time: 88 pending, 6 skipping, none passed or failed yet. The
  full suite on this branch is therefore unverified.
- Model reasoning content (thinking blocks carry only signatures).

## Review helpers (scratchpad, not committed anywhere)
`/private/tmp/claude-501/-Users-marcin-Documents-VIMSS-ontology-bridge2ai-data-sheets-schema/739c8f5b-2480-48d9-b567-1229e9d76264/scratchpad/`
`transcript_facts.py`, `path_scan.py`, `content_scan.py`, `content_scan_seq.py`,
`recorder_calls.py`, `compare_notes.py`.

VERDICT: APPROVE WITH FOLLOW-UPS

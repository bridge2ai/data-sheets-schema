# Assignment to Codex helper 2: repair the two defects your public completion run found, then finish the proof

From the Claude lead, 2026-11-12. Short names and rules are in `claude-lead-helper-context-20261112.md` beside this file. This extends `claude-lead-helper2-public-path-proof-20261112.md`; its bounds and its handoff file stay.

## Standing

Your incremental handoff is read. The repair `d2efa55014e131f92733bf2c3a90c0830214dc89` of your own commit is accepted and is on helper 1's integration list. Helper 1 reached the same HOME refusal independently in its own composition at `df0122254cc7c9fe10470ee9eabc26c71a411a14` and saved the evidence (`handoffs/codex-h1-public-home-finding-20261112.json`): the `full_terms` helper imports the term validator, which imports oaklib, which imports PyStow; PyStow writes `.data/README.md` and `.data/oaklib/` under HOME at import. Two independent observations, same cause.

The earlier rule "fix only your own commits" is lifted for the two defects below. You own both repairs. Helper 1 does not work on them.

## Where you work

A new branch and worktree from the candidate's current head (record the head you take; at least `df0122254`):

```sh
git -C /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema worktree add \
  -b codex/native-helper-cache-home-20261112 \
  /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-native-helper-cache-home-20261112 \
  df0122254cc7c9fe10470ee9eabc26c71a411a14
```

Tests run in your scratch composition as before, with the four protected post-images applied there only.

## Defect 1: a helper's dependency writes into HOME (required)

The lead's rulings on the repair:

1. **The guard is not relaxed.** The empty-HOME and account-artifact check stays exactly as strict, in the synthetic profile and anywhere else it runs. No allowlist of tolerated names under HOME.
2. **One code path for both profiles.** The repair is in the environment the controller constructs for the native process, which the helpers inherit, so that production and the synthetic peer take the same path and the test proves the production path. A change only in the test peer or the fixture is not a repair.
3. **A declared, per-attempt location.** The cache location is an explicit variable in that constructed environment, pointing at a directory the controller creates empty for this attempt, outside HOME, outside the staged source and the output roots that are inventoried or published, and removed or left out of evidence by a stated rule. It must appear wherever the environment is declared, allow-listed, pinned or validated (runtime declaration, profiles, permission expectations, registration). Name every document identity that moves.
4. **Not a channel into the model.** Show from the tool policy that the model cannot read or write that directory with its file tools, and that nothing a previous attempt wrote can be in it.
5. **Only what is evidenced.** Set the variable PyStow reads. Do not add speculative variables for other libraries. Instead, after the completion run passes, census the HOME and the cache directory (hidden entries included) and report every entry: the guard is what catches the next writer.
6. **Network.** Confirm from the saved network-denial witness that the term-validator path made no network attempt in this run, or report what it attempted.

Tests: one that fails at the old head with the HOME refusal and passes with the repair; one that the directory is fresh per attempt; one that the guard still refuses a HOME with an entry in it.

## Defect 2: no exact failed readback when runtime revalidation itself fails (required)

Your second finding: when the runtime revalidation fails during failure publication, the attempt keeps its early evidence but writes no `final.json`, `published.json` or `actual-result.json`, so the failure cannot be read back exactly. Amendment N1.4(A) item 6 requires "an exact failed readback".

Repair it as its own commit with tests: a failure whose cause is the runtime validation must still be published as a failure and read back exactly, stating that the runtime validation failed and why. Acceptance and the readback verification stay fail-closed: nothing in the repair may let a run with a failed runtime validation be published as anything but a failure, and no check is skipped on the success path. If the cleanest repair needs a design choice you are unsure of, write the two options and your recommendation in the handoff and implement the one that changes least.

## Defect 3: prepare, on a separate local branch, the retention of the record on an incomplete capture (a decision is pending)

A Claude review of the production amendment (`E/plans/reviews/np1v3_27429678_claude_review_2026-11-12.md`, finding P1-1) reads the source at `5d63d0a77` this way: the end capture records the full record only if the recorder's output and the report exist (`native_shared_results_orchestration.py`, about lines 68 to 74 and 208); otherwise it falls back to `incomplete_capture`, which keeps only the streams (about lines 274 to 294; `native_execution_orchestration.py`, about 500 to 508); and the recorder runs only after every final check has passed (`native_shared_phase.py`, lines 111 to 113 and 212 to 214), which includes the registered floor and schema validation. If so, a rejected attempt leaves no pinned full record, and the set of records the analysis may use is gated on acceptance and on the coverage floor. The analysis plan refuses that (`notes/generic_v10_analysis_plan.md` at main, lines 799 to 800 and 1163). It also extends what your own eligibility audit found.

1. **Confirm or refute the reading** at the candidate's head, with the lines.
2. **If it holds, implement on a separate local branch** from your repair branch's head, named `codex/native-incomplete-capture-retention-20261112`, so that it can be taken or dropped: an incomplete capture also keeps the current full record and the current core record, if each exists as a regular file at its registered path, with their sizes and SHA-256, bound into the same published failure evidence as the streams. It keeps them as evidence of a failed attempt: nothing in the change may make a failed attempt count as accepted, and a record that is missing or unreadable is recorded as such, not as an error that prevents publication. With tests: a failure before any record exists, a failure after the full record exists, a failure after both exist, and a floor failure at the final stage.
3. Say what a reader of the evidence would call to list the retained records of rejected and stopped attempts, and whether that reader exists.

The owner decides whether this is taken; the lead is asking. Do this after defects 1 and 2 and before the long failure-case cohorts if those are still running.

## Then finish the proof

Re-canary the first public completion test alone and verify its saved artifacts. Then the second, then the seventeen failure cases not yet run. Report each new stop as before.

**Expect one more stop, already known:** the final receipt check under a pending coverage floor (issue #5939: `receipts check … --strict` exits 1 for a pending floor, so a pilot cannot complete). Helper 1 is repairing it on the candidate branch. If your completion test reaches that stop before helper 1's commit exists, record the exact point, do not repair it yourself, and say so in the handoff; the lead will tell you which commit to take.

## Bounds

As before: offline only; no provider, model or native-binary execution; no `cpu-monitoring` diagnostic; no real capture; nothing pushed; no GitHub write; protected files equal to main on every branch; helper 1's and helper 3's trees are read-only for you. Helper 3 is building its own composition from the same commits under `E/scratch-h3-packet-builder-20261112/`; do not share a scratch tree with it.

## Handoff

Update `R/notes/development_efficiency_20261111/handoffs/codex-h2-public-path-proof-20261112.md` and its JSON. Answer first: the two repair commits and what they change; every declared identity that moves; do the two public completions now pass and where does each stop if not; the failure cases' count.

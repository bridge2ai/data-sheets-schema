# Assignment to Codex helper 2: repair the HOME cache defect your public completion run found, then finish the proof

From the Claude lead, 2026-11-12. Short names and rules are in `claude-lead-helper-context-20261112.md` beside this file. This extends `claude-lead-helper2-public-path-proof-20261112.md`; its bounds and its handoff file stay.

## Standing

Your incremental handoff is read. The repair `d2efa55014e131f92733bf2c3a90c0830214dc89` of your own commit is accepted and is on helper 1's integration list. Helper 1 reached the same HOME refusal independently in its own composition at `df0122254cc7c9fe10470ee9eabc26c71a411a14` and saved the evidence (`handoffs/codex-h1-public-home-finding-20261112.json`): the `full_terms` helper imports the term validator, which imports oaklib, which imports PyStow; PyStow writes `.data/README.md` and `.data/oaklib/` under HOME at import. Two independent observations, same cause.

The earlier rule "fix only your own commits" is lifted for defect 1 below. You own that repair. Helper 1 does not work on it.

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

## Defects 2 and 3 are reassigned to helper 3 (changed by the lead at 20:13Z, before this file was delivered)

Your second finding (no failure record when the runtime revalidation itself fails, issue #5967) and the retention of the record on an incomplete capture are now helper 3's, on its own branches, because helper 3 is free and both changes are in the failure-publication code. Do not work on them. Your repair is defect 1 only (issue #5966). Keep out of `native_shared_results_orchestration.py` and `native_execution_orchestration.py` where you can; if defect 1 needs a change there, say so in the handoff.

## Then finish the proof

Re-canary the first public completion test alone and verify its saved artifacts. Then the second, then the seventeen failure cases not yet run. Report each new stop as before.

**Expect one more stop, already known:** the final receipt check under a pending coverage floor (issue #5939: `receipts check … --strict` exits 1 for a pending floor, so a pilot cannot complete). Helper 1 is repairing it on the candidate branch. If your completion test reaches that stop before helper 1's commit exists, record the exact point, do not repair it yourself, and say so in the handoff; the lead will tell you which commit to take.

## Bounds

As before: offline only; no provider, model or native-binary execution; no `cpu-monitoring` diagnostic; no real capture; nothing pushed; no GitHub write; protected files equal to main on every branch; helper 1's and helper 3's trees are read-only for you. Helper 3 is building its own composition from the same commits under `E/scratch-h3-packet-builder-20261112/`; do not share a scratch tree with it.

## Handoff

Update `R/notes/development_efficiency_20261111/handoffs/codex-h2-public-path-proof-20261112.md` and its JSON. Answer first: the repair commit and what it changes; every declared identity that moves; do the two public completions now pass and where does each stop if not; the failure cases' count.

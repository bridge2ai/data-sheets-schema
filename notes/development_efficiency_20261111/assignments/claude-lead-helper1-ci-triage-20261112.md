# Assignment to Codex helper 1: what stands between the candidate and a green CI run

From the Claude lead, 2026-11-12. Short names and rules are in `claude-lead-helper-context-20261112.md` beside this file. This comes after `claude-lead-helper1-pending-floor-review-followup-20261112.md` (issues #5994 and #5995).

## The CI result

The lead published your Part 1 head `0fc003a86081891abbe8e130ac760c01da06423e` as draft PR #5968 to get a complete CI run. Run 43294096351 ended in failure. The inventory, one entry per failing or erroring test id with its message: `R/notes/development_efficiency_20261111/handoffs/lead-ci-run-43294096351-failures-20261112.json` (made by `R/scripts/adhoc/summarize_ci_run_failures_20261112.py`). The previous inventory, on `1a137b588`, is `lead-ci-run-42976790438-failures-20261112.json`.

- 593 distinct ids in 44 test files (453 errors, 140 failures). Of the previous run's 152 ids, 56 are cleared and 96 still fail; 497 are new, mostly because collection now works and tests run that never ran before.
- Shard 8 was cancelled at the 45-minute limit; shard 5 took 43.6 minutes; the others 21 to 37.
- **387 ids are the expected one:** the protected files are equal to main on the branch, so `RunSpec.__init__() got an unexpected keyword argument 'native_shared_generation_version'` (380) or `'RunSpec' object has no attribute 'native_shared_generation_version'` (7).
- **The other 206 are what this assignment is about.** By message, from the inventory:
  - 78: `registered recorder failed or has unusable result; preserve the attempt` (`test_native_attempt_supervisor.py`, `test_native_receipt_origin_reporting.py`, `test_native_attribution_controller.py`, `test_native_attribution_results.py`). Helper 3 saw the same message in an exported tree with local Git metadata; issue #5965.
  - about 70 in the scanner tests: `TypeError: 'NoneType' object is not subscriptable` (30), `model-facing native command table lacks its derived native-only route` (about 15, as an error and inside assertions), `DID NOT RAISE ConfigError` (8), `assert None` (8), and the 13 the summary script classes as "could not derive a meaning".
  - 29: `closed dependency registry is not ready` (`test_native_launch_schema_metadata.py`), the same count as in the previous run.
  - 9: `assert None is not None` (`test_native_u3b_reuse.py`).
  - the rest in ones and twos; list them.

## The question

**Would CI be green on the candidate once the four protected post-images are applied, and if not, what exactly is left?** The owner's approval of the post-images is pending, so the branch cannot carry them and CI cannot answer this. A CI-equivalent run can.

## What to do

1. **Build a CI-equivalent tree.** An exported copy of the candidate's current head (after your #5994 and #5995 commits) with the four protected post-images applied, outside every `d4d-executions` path, under `~/agent-work/data-sheets-schema/` (helper 3's handoff `handoffs/codex-h3-ci-origin-and-shard-time-20261112.md` shows the method, including local Git metadata and what the export lacks). As close to the CI checkout as you can make it: one commit of history, no sibling worktrees, the workflow's own install and test commands (read `.github/workflows/`), the same shard assignment. Say every way it still differs from a CI runner (operating system, Python build, installed submodule content).
2. **One class first, alone:** the recorder class. Run one of its ids in that tree and read the saved attempt to find why the registered recorder failed. Do not guess from the message. Then the whole class.
3. **Then every other class,** each as its own cohort, then the 387 expected ids, then the complete shards if time allows, at most two workers.
4. **Classify each of the 593 ids:** passes with the post-images applied; fails for a cause in source (name it and fix it, one commit per cause, with the test that shows it); fails for a cause in the test or its fixture (fix the test without weakening what it asserts, say what it asserted before and after); fails only because of the tree's remaining difference from CI (say which difference, and how you know).
5. **Shard time.** From the run's job durations and your own timings, say whether the suite fits the 45-minute limit once it passes, and what the refreshed weights would be. Data and a recommendation only; no change to the workflow's limits.

A fix for a cause that belongs to another helper's open work (the HOME cache, #5966, helper 2; the failure record, #5967, and the launch-sequence follow-ups, #5992 and #5993, helper 3) is theirs: record the ids and move on.

## Bounds

As before. Offline; no provider, model or native-binary execution; nothing pushed; no GitHub write. The protected files stay equal to main on the branch; the post-images live only in the exported tree and your scratch. Restore and record any private test configuration.

## Handoff

`R/notes/development_efficiency_20261111/handoffs/codex-h1-ci-triage-20261112.md` with a JSON that carries the classification of all 593 ids. Answer first: how many ids pass with the post-images applied, how many remain and in which classes, the cause of the recorder class, the commits you made, and the shard-time answer. Write a first version when the recorder class is understood.

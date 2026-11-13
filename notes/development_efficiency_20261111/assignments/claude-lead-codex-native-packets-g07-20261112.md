# Assignment to the Codex helper: the protected-file packets on the merged candidate (your gate G07), and capture selection

From the Claude lead, 2026-11-12. Offline work in your integration worktree and in a scratch composition. Nothing is published and nothing protected is changed on the branch.

## What has changed since your last assignment

- **The owner decided three things at 2026-11-12T07:39:17Z** (D135 to D137 in STATUS): native production mirrors the API matrix (a separate amendment; not your concern here); **the freshness age is 1200 s with the 90 s margin unchanged**, so your commit `a68efbd687e5` carries the owner's value, though amendment N1 as a whole is still to be ratified; and the lead has a standing permission for free offline native checks. The offline cohorts and compositions you need for this assignment are covered. Provider, model and native-binary calls are not.
- **Your integration handoff is accepted.** I take G04-F1 as the next step: the 270 merge-caused negatives wait on the protected integration.
- **G04-F2 was my instruction's fault.** I required `--basetemp` inside the worktree, which puts it inside the source authority. Use a scratch directory beside the worktree from now on: `d4d-executions/scratch-native-main-integration-20261112/`. Never the system temporary directory.
- **The first full CI run on the native stack finished** (run 42976790438, head `1a137b588604`): 152 distinct failing or erroring test ids in 21 files, and two shards cancelled at the 45-minute limit. The inventory is `handoffs/lead-ci-run-42976790438-failures-20261112.json`, made by `scripts/adhoc/summarize_ci_run_failures_20261112.py`. AGY4 has fixed the collection error (issue 5875; commit `ddcadcdc2` on `agy/native-ci-collection-5875-20261112`) and is working on the host-layout and import-origin failures. AGY1 is working on shard time.
- **Amendment N1 is at draft v8** (commit `98adf23eb966` on `claude/native-amendment-n1-v7-20261112`). Two of its new code prerequisites are yours below.

## Part A: the four protected packets (G07)

1. Compute, against main `7ad8c9e7295f1575ae9108ea62c12c83b1dd4db1`, the exact post-image of each of the four D127 files that the native integration needs on the merged candidate: `shared_generation.py`, `api_runner.py`, `canonical_hashes.yaml`, `tests/utils/run_spec_boundary_contracts.json`.
2. Build them in a scratch composition, not on the branch. On the branch the four files stay equal to main until the owner approves.
3. Show what they fix: re-run, in the composition, the cohorts that carried the 270 merge-caused negatives (scanner, execution constructor, shared-policy constructor), with the basetemp outside the source tree. Report what clears, what remains and why.
4. Produce the scanner comparison in D128's form on the integrated head: exact matches, line relocations, field changes, additions, removals, and the violation objects, each itemised. Say which differences D128 already covers and which are new.
5. Write the owner's review packet: for each file, its post-image sha256, D127's approved sha256, whether they are equal, and for each one that differs a plain account of what changed in main since D127 and what the native change adds, with the diff. The owner approves by sha256; make that easy to do correctly.
6. From the CI inventory, say which failure classes the packets resolve (the 71 scanner failures, the 29 "closed dependency registry is not ready" in `tests/test_native_launch_schema_metadata.py`, the others) and which they do not.

## Part B: capture selection (amendment N1 v8, item (ac) and N1.9 item 3)

Both reviewers of the amendment found that the rule "the guard is prepared on the latest capture" is not enforced at `382f0dfd1ce8`, and that a longer freshness age makes it matter: an earlier, more favourable capture could back a guard after a later capture was refused.

1. Confirm or correct that reading of `native_subscription_capture.py` and the guard, with the callers the reviewers did not read.
2. If it holds, implement on your candidate branch, as a separate commit with tests:
   - guard preparation refuses a capture that is not the last one claimed under the word;
   - the pre-reservation check, under the same lock that protects the reservation, refuses when the guard's capture is no longer the last one claimed;
   - the checked index and the claim count are recorded.
3. If this needs a design decision (lock order, what a refused guard costs, anything that changes the recorded event order), stop at that point and report the choice with your recommendation. Do not weaken any existing check to make it fit.

## Bounds

- No push, no pull request, no GitHub write. No provider, model or native-binary call. No `cpu-monitoring` diagnostic in this assignment; the lead runs that one.
- Protected files on the branch stay equal to main. The canonical prompt pins are not rotated outside the composition.
- At most two xdist workers; `PYTHONPATH` set to the tree under test; never `-o tmp_path_retention_policy=none`.
- Stay out of `d4d-executions/launch-a21` and out of the other workers' worktrees (`agy-native-ci-collection-20261112`, `agy-native-launch-sequence-20261112`).

## Deliverables (in the report worktree `codex-development-efficiency-20261111`)

- `notes/development_efficiency_20261111/handoffs/codex-native-packets-g07-20261112.json` and `.md`: the answer first, then tables made from the JSON by a script under `scripts/adhoc/`.
- The owner's review packet as its own file: `notes/development_efficiency_20261111/handoffs/codex-native-packets-owner-review-20261112.md`. Plain language, the four hashes at the top.
- No at-sign characters. Write a first version when Part A's hashes exist and update it as parts finish. Print paths and SHA-256 each time, then stop at the end.

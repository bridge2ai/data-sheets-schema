# Assignment to the Codex helper: the main-targeted native integration candidate (your gates G04 and G05)

From the Claude lead, 2026-11-12. This one writes code on a new branch in a new worktree and runs offline tests. It publishes nothing.

## Standing

- Your critical-path report (`handoffs/codex-native-critical-path-20261112.md`, SHA-256 `e407a36ed2bd9e904164c00c593bb1e12095548bcc8305e895043997978c7410`) is the lead's working plan. I checked its counts against the amendment, AGY2's pull-request data and the source.
- Lead dispositions for your gate G02, recorded in STATUS under D134: the later-capture redesign, the cheaper post-acceptance verifier (issue 5722, F1) and any N=10 quiet-host campaign are follow-ups, not gates for the first canary. The first canary keeps full genuine verification. The constraint of issue 5836 stays binding. The landing is one main-targeted combined pull request, not eleven merges.
- Under D134 the native offline test cohorts are no longer stopped. Run what you need to trust this candidate, within the bounds below.

## Part 1: reconcile the native stack with current main (G04)

1. Check free disk first; stop and report if less than 10 GiB is free.
2. Create a new worktree `d4d-executions/codex-native-main-integration-20261112` on a new branch `codex/native-main-integration-20261112`, starting at `1a137b58860416a31618de44173180d021dfcc61` (the head of draft PR 5871). Sparse checkout as the other native worktrees use. Do not touch any existing worktree.
3. Merge main `7ad8c9e7295f1575ae9108ea62c12c83b1dd4db1` into it with a merge commit. No rebase, no force.
4. Resolve every conflict. For each conflicted path record: the path, the kind of conflict, what each side intended, what you kept and why.
5. The four D127 protected files must come out byte-identical to main's. Do not apply the packets here. Record each file's SHA-256 beside main's.
6. Prove the merge:
   - full collection (`pytest --collect-only`) over `tests`, with the count and every collection error;
   - the tests in files the resolution touched;
   - the native cohorts you judge necessary, run one after another with at most two workers.
   Record each command, its duration and its outcome. A failure is a finding: classify it as caused by the merge, already present at `1a137b588604`, or environmental, and say how you know.

## Part 2: the freshness value (G05), as a separate commit on top

The owner has not decided the value. The lead recommended 900 and is now recommending **1200**, because your third answer shows four full verifications after the capture event that the diagnostic never timed (your estimate: 58 to 309 seconds more). Treat the number as provisional.

1. Change only the two active places you listed: `native_u4b_policy.py` and `native_subscription_guard_v2.py` (constant and rejection text). Guard v1 stays byte-identical. The margin stays 90. No other clock changes.
2. Update the tests you listed. Derive boundaries from the registered terms wherever the test's purpose allows, so that a different number later costs two source lines and the few literals that exist to pin the registered value. List those literals.
3. Run the affected test files and record the results.
4. Commit this as one commit whose message says the value awaits the owner's ratification of amendment N1 item (o).

Do not edit the amendment or the operator guide; the lead revises the amendment.

## Bounds

- No push, no pull request, no GitHub write. The lead reviews and publishes.
- No private-composition arming, no `cpu-monitoring` diagnostic, no provider, model or native-binary call. Those still need the owner's word.
- No change to the canonical prompt pins, no packet application, no edit of protected files beyond taking main's bytes in the merge.
- Tests: `PYTHONPATH` set to the new worktree's `src`; `--basetemp` inside the new worktree; never `-o tmp_path_retention_policy=none`; at most two xdist workers.
- Stay out of `d4d-executions/launch-a21`.
- If the merge needs a design decision rather than a mechanical or clearly intended resolution, stop at that point and report the choice with your recommendation.

## Deliverables (in the report worktree `codex-development-efficiency-20261111`)

- `notes/development_efficiency_20261111/handoffs/codex-native-main-integration-20261112.json`: the conflict ledger, the protected-file hashes, every test command with duration and outcome, the two commit ids.
- `notes/development_efficiency_20261111/handoffs/codex-native-main-integration-20261112.md`: the answer first (is the candidate sound, and what is still open), then tables made from the JSON by a script under `scripts/adhoc/`. Show the command.
- No at-sign characters.
- Write a first version of the handoff as soon as Part 1's merge commit exists, and update it when Part 2 is done. Print the paths and SHA-256 each time, then stop at the end.

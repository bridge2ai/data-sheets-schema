# Re-check brief: the repairs of issues 6015 and 6016 on the native route (read-only)

Read-only adversarial code review. You wrote none of this code. Do not edit, commit, push or write to GitHub; run no test, no model or provider call, and nothing that executes the Claude Code binary. Read with `git -C <worktree> show` and `git -C <worktree> diff` only.

Two earlier reviews each found one P1. Both are in `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/plans/reviews/`: `native_failure_record_c9af5f51_codex_review_2026-11-12.md` (finding P1-1: the diagnostic readback accepts contradictory lifecycle evidence) and `native_retention_200dbc7b_codex_review_2026-11-12.md` (finding P1-1: one changing optional artifact discards the whole incomplete capture). Read both findings first.

## The repairs

- Issue 6015: commit `86a80f96ce7656b88d3514d72aeaa314875f4982` in the worktree `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-native-failure-record-20261112` (its parent chain starts at `c9af5f5148f229e0e9605dea059211c86f5423f0`).
- Issue 6016: commit `920344848373fb1dae78b04f785fc59cf61e2783` in the worktree `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-native-incomplete-capture-retention-20261112` (on top of `200dbc7be7f7c7c1e638aa009940696363e8950d`, and it should also contain the 6015 repair; say how it was carried).

If either worktree's branch has other new commits by the same author after the reviewed ones, list them and review them too.

## Questions

1. **6015.** Is the earlier finding closed: are the diagnostic pins built from the bytes already consumed, is a later change on disk recorded explicitly rather than silently pinned, and does the readback cross-check the lifecycle pins against the diagnostic pins and run the byte-based lifecycle consistency checks? Try the two scenarios of the finding (a file changed between the lifecycle read and the diagnostic pinning; a rehashed record with a changed cleanup assessment or lifecycle hash) against the new code. Does the repair open any way for a failed run to read back as a success, or weaken the success path?
2. **6016.** Is the earlier finding closed: is each optional artifact verified on its own, an unstable one removed from the snapshot consistently with a recorded omission reason, and the streams and the other records kept? Does strict all-or-nothing verification still apply to a successful capture? Can the per-artifact handling hide a change in a required member (a stream, the composition) by treating it as optional?
3. For both: any change to the four protected files, guard v1, or a registered document's kind or version? Do the new tests assert the property?

## Output

Verdict first for each issue: closed, closed with remaining findings, or not closed. Then findings headed `### P1-1: title`, `### P2-1: title`, `### P3-1: title`, each with file and line, the concrete scenario and the smallest fix. Then what you checked and what you did not. Use no at-sign characters.

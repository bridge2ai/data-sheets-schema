# Assignment to Codex helper 3: the failure record when the runtime validation fails, then the retention of the record on an incomplete capture

From the Claude lead, 2026-11-12. Short names and rules are in `claude-lead-helper-context-20261112.md` beside this file.

## Standing

Your hardening handoff is accepted as work done (`handoffs/codex-h3-launch-sequence-hardening-20261112.md`, SHA-256 `d7dd8ac97bb759674c1cae6a0642774a0e8a6a0d0054f5ce4d6a5657317d66e6`; commits `b832233b798da1f350a764f49f19039195fab4c5`, `9abf48b31122da7a89ba462274a8e3980d1b7973`, `c1ad9baa19a5b938d7976541bed27a73eee32d8c`). The lead is starting an independent read-only review of the three commits; they are integrated after it.

Two changes in the failure-publication code were going to helper 2. They are yours now, because helper 2 is still on the failure cases and you have just worked in `native_execution_orchestration.py`. Helper 2 keeps only the HOME cache repair (#5966) and is told to stay out of `native_shared_results_orchestration.py` and `native_execution_orchestration.py`.

## Where you work

Two branches, the second on top of the first, both starting from your hardening head so that you do not conflict with yourself:

```sh
git -C /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema worktree add \
  -b codex/native-failure-record-20261112 \
  /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-native-failure-record-20261112 \
  c1ad9baa19a5b938d7976541bed27a73eee32d8c
```

and, for Part 2, `codex/native-incomplete-capture-retention-20261112` from the head of Part 1 (a branch in the same worktree or a second worktree, as you prefer; record which). Part 2 must be removable without touching Part 1.

Tests that need the protected post-images run in your own scratch composition, as before.

## Part 1: a failure whose cause is the runtime validation is still published as a failure (issue #5967; required)

**What was seen.** In helper 2's and helper 1's offline runs of `tests/test_native_shared_execution.py::test_actual_public_correction_three_workers_and_saved_completion`, the observer refused a tool result because the synthetic HOME was not empty (issue #5966, helper 2 is repairing that cause). Failure publication then ran the same runtime validation again (`subscription_admission.context` to `validate_prepared_runtime` to `validate_runtime_v2`), which refused again, so publication ended with a second error. The attempt kept its early evidence (started, registration, guard, dispatch, runtime, keep-awake, the peer's streams) and wrote no `final.json`, `published.json` or `actual-result.json`. Evidence: `handoffs/codex-h2-public-path-proof-20261112.md` and its JSON; `handoffs/codex-h1-public-home-finding-20261112.json`. Amendment N1.4(A) item 6 requires an exact failed readback.

**The repair, its own commit with tests.**

1. Reproduce it first, at your Part 1 base, in your scratch composition. While #5966 is unrepaired the public completion test reproduces it by itself; also write a narrower test that does not depend on #5966 staying broken (a runtime validation made to fail by a declared fixture condition).
2. A failure whose cause is the runtime validation is published as a failure and can be read back exactly: the record says that the runtime validation failed, where and why, and binds the evidence the attempt already holds.
3. **Fail-closed, and say how you know:** no path lets a run with a failed runtime validation be published as anything but a failure; no check is skipped or weakened on the success path; the readback verification of a successful run is unchanged. A test for each of those three statements.
4. If the cleanest repair needs a design choice (for example which checks failure publication may run without, or a separate failure-only publication path), write the options and your recommendation in the handoff first, then implement the one that changes least.

## Part 2: an incomplete capture keeps the records that exist (a decision is pending; separate branch)

**The reading, confirmed twice at `5d63d0a77`** (a Claude review of the production amendment, `E/plans/reviews/np1v3_27429678_claude_review_2026-11-12.md` finding P1-1, and the lead's copy): the complete capture needs the recorder's provenance file (`native_shared_results_orchestration.py`, about lines 68 to 74 and 208); any failure falls back to `incomplete_capture`, which keeps the streams and no record (about lines 274 to 294; `native_execution_orchestration.py`, about 500 to 508); and the recorder is admitted only after every final check, the draft and the final evidence (`native_shared_phase.py`, lines 111 to 113 and 212 to 214). So a rejected attempt leaves no pinned full record, and the records the analysis may use are gated on acceptance and on the coverage floor. The analysis plan refuses that (`notes/generic_v10_analysis_plan.md` at main, lines 799 to 800 and 1163). Helper 2's audit of what the source saves is `handoffs/codex-h2-native-eligibility-audit-20261112.md`.

1. **Confirm or refute the reading at your base**, with the lines.
2. **If it holds, implement on the separate branch:** an incomplete capture also keeps the current full record and the current core record, each if it exists as a regular file at its registered path, with size and SHA-256, bound into the same published failure evidence as the streams. Also keep the live phase report if one exists, and say whether it does today. They are evidence of a failed attempt: nothing in the change may make a failed attempt count as accepted, and a record that is missing or unreadable is recorded as such, never as an error that prevents publication.
3. Tests: a failure before any record exists; after the full record exists; after both exist; a floor failure at the final stage; and a record replaced by a symlink or a directory (recorded as not kept, with the reason).
4. Say what a reader of the evidence would call to list the retained records of rejected and stopped attempts with their hashes, and whether such a reader exists. If it does not, write the smallest one as a read-only function with a test, on the same branch.
5. The production amendment's eligibility rule needs a current successful `derive_final_core` as well. Say whether the phase rules guarantee that derivation has run before the final receipt check (a Codex review reads `native_shared_phase.py`, lines 195 to 202, as not requiring it, while the rendered instruction orders it first), and what the smallest change would be if the guarantee is wanted. Do not implement that.

The owner decides whether Part 2 is taken. Guard v1 stays byte-identical; protected files stay equal to main; no registered document's kind or version changes without stopping to propose first.

## Bounds

As in the context file. Offline; no real-binary execution, no probe, no capture, no reservation; no provider or model call; nothing pushed; no GitHub write. Helper 1's and helper 2's trees are read-only for you.

## Handoff

`R/notes/development_efficiency_20261111/handoffs/codex-h3-failure-record-and-retention-20261112.md` with its JSON. Answer first: Part 1's commit, what a published runtime-validation failure now contains, and the three fail-closed tests; whether the retention reading held; Part 2's commit and what is kept; the answer on the derivation ordering. Write a first version when Part 1 is committed.

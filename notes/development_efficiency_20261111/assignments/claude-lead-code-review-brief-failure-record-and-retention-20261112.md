# Review brief: failure publication and incomplete-capture retention on the native route (read-only)

Read-only adversarial code review. You wrote none of this code. Do not edit, commit, push or write to GitHub; run no test, no model or provider call, and nothing that executes the Claude Code binary. Read with `git -C <worktree> show` and `git -C <worktree> diff` only. Your invocation names which of the two parts is yours.

Context: the native agentic route runs a generation under a registration and publishes saved evidence (`final.json`, `published.json`, `actual-result.json`) that a reader verifies. The canary's rules are in amendment N1, draft v12: `git -C /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema show c289eed19e37e227e04dd5e0c4fc077da54184aa:notes/generic_v10_analysis_plan_amendment_n1_2026-11-08.md` (N1.4(A) item 6 requires "an exact failed readback"). The author's account of both parts: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/codex-h3-failure-record-and-retention-20261112.md`.

## Part P: a failure whose cause is the runtime validation is still published as a failure (issue 5967)

Worktree `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-native-failure-record-20261112`. Base `c1ad9baa19a5b938d7976541bed27a73eee32d8c`; commit `c9af5f5148f229e0e9605dea059211c86f5423f0`.

The defect: when the runtime validation itself failed, failure publication ran the same validation again, failed again, and wrote nothing. The repair adds a failure-only diagnostic publication and readback route.

Questions:

1. Can anything published through the diagnostic route ever be read as a success, an accepted run, or a completed run: by the ordinary reader, by the completion gate, by the recorder, by a later resume, or by a reader that sees only some of the files? Try a forged or rehashed record that claims success, and a record whose failure fields are removed.
2. Is the success path unchanged: does a successful run still run every check it ran at the base, and does a successful readback still require fresh registration, authority, subscription and gate verification? Is there an input for which a run that should fail its runtime validation is now routed to the diagnostic path and reported in a way a caller treats as "published, fine"?
3. What decides that the diagnostic route is taken? Can a caller, a file on disk, or an exception of another type select it for a failure that is not a runtime-validation failure, and so skip checks that would have applied?
4. The published failure pins "available consumed evidence by size and SHA-256". Are the pins of the bytes actually consumed, read without following symlinks, bounded, and verified on readback? What does readback do when a pinned file is later changed, removed or replaced?
5. Does the change alter guard v1, any registered document's kind or version, or any of the four protected files (`src/data_sheets_schema/shared_generation.py`, `src/data_sheets_schema/api_runner.py`, `src/download/prompts/canonical_hashes.yaml`, `tests/utils/run_spec_boundary_contracts.json`)?
6. Do the tests assert the property, or only a message an earlier refusal also produces?

## Part R: an incomplete capture keeps the records that exist

Worktree `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-native-incomplete-capture-retention-20261112`. Base `c9af5f5148f229e0e9605dea059211c86f5423f0`; commit `200dbc7be7f7c7c1e638aa009940696363e8950d`.

Why: before this change, any failure fell back to an incomplete capture that kept the streams and no record, so the records an analysis may use were gated on a run passing every final check, the coverage floor included. The analysis plan refuses that (`notes/generic_v10_analysis_plan.md` at main `7ad8c9e7295f1575ae9108ea62c12c83b1dd4db1`, lines 799 to 800 and 1163). The change keeps the current full and core records, the registered report and the live phase history on an incomplete capture, as evidence of a failed attempt, and adds a read-only inventory reader `native_shared_results.list_retained_records`.

Questions:

1. Can a retained record make a failed or stopped attempt count as complete, accepted or replayable anywhere (`replay_complete`, the saved gate, the recorder, a resume)? Can the inventory reader's output be mistaken for a verified successful result?
2. Are the kept files read safely: regular files only, no symlink or directory followed, bounded in size, the bytes hashed being the bytes copied, with a stated reason for each omission? Is there a window between the check and the copy?
3. Could retention change what a successful run publishes or how it is verified? Does `read_final` behave identically for evidence written before this change (no retention manifest)?
4. Does the inventory reader verify the binding of the retained copies to this attempt (final, publication, start, registration) before it returns rows, and refuse tampered copies? What does it trust?
5. A kept core record does not show that a current successful core derivation happened. Is anything in the change, its names or its output liable to be read as an eligibility decision?
6. Protected files, guard v1 and registered document versions, as in Part P question 5. Tests, as in Part P question 6.

## Output

Verdict first for your part: acceptable as is, acceptable after listed fixes, or not acceptable. Then findings headed `### P1-1: title`, `### P2-1: title`, `### P3-1: title` (P1: could let a failed run be treated as a success, lose or falsify failure evidence, or weaken the success path; P2: should be fixed before the final review; P3: minor), each with file and line, the concrete scenario, and the smallest fix. Then what you checked and what you did not. Use no at-sign characters.

# Assignment to Codex helper 3: the two review findings on the failure record and the retention

From the Claude lead, 2026-11-12. Short names and rules are in `claude-lead-helper-context-20261112.md` beside this file. This comes after `claude-lead-helper3-hardening-review-followup-20261112.md` (issues #5992 and #5993).

## Standing

Your handoff is accepted as work done (`handoffs/codex-h3-failure-record-and-retention-20261112.md`, SHA-256 `750b2c6997b2f06b401f66800e86cc515839924fe8586cc50db4c8e92e05d785`): Part 1 `c9af5f5148f229e0e9605dea059211c86f5423f0`, Part 2 `200dbc7be7f7c7c1e638aa009940696363e8950d`. Your answer on the derivation order is noted and goes into the production amendment as a known behaviour; nothing is to be implemented for it.

Two independent read-only Codex CLI reviews, both "acceptable after the listed fix". Each confirms no route from your change to a success, an accepted run or a resume, the success path unchanged, bounded no-follow reads, protected files and guard v1 unchanged, and no registered document's kind or version changed. One P1 each, filed:

## Part 1: issue #6015, the diagnostic readback accepts contradictory lifecycle evidence

Review: `E/plans/reviews/native_failure_record_c9af5f51_codex_review_2026-11-12.md`. `src/data_sheets_schema/native_execution_orchestration.py`, about lines 574 to 626, 680 to 690 and 746 to 781. Publication captures the lifecycle bytes and derives their gates before the subscription validation; when that validation fails, `_failure_evidence()` rereads the files independently. The diagnostic readback verifies those later pins but never compares them with `lifecycle_artifacts`, `runtime_observation`, `keep_awake` or the lifecycle gates. So (a) a `keep-awake.json` that changes between the lifecycle read and the diagnostic pinning yields a published record whose assessment and pins disagree, and (b) a rehashed record with a changed cleanup assessment or lifecycle hash reads back successfully. The attempt stays failed, but its failure evidence can be falsified without detection.

Repair, one commit on `codex/native-failure-record-20261112`: build the diagnostic pins from the bytes already consumed where they exist, and record a later change on disk explicitly instead of silently pinning another version; on readback, cross-check the lifecycle pins against the diagnostic pins and run the byte-based lifecycle consistency checks the ordinary reader keeps. Tests: the publication-time change, the rehashed contradictory record, and the three cases the review found uncovered (removal of the diagnostic field, deletion of a pinned file, a symlink in place of a pinned file).

The review also notes, without grading it: the reader now opens the final file before fresh registration verification, to choose its route; and the route is taken for any `ValueError` or `OSError` from the subscription context or the observation validation, not only a runtime-validation failure. Say in the handoff whether either matters, and why not if not. If the first can be reordered without cost, reorder it.

## Part 2: issue #6016, one changing optional artifact discards the whole incomplete capture

Review: `E/plans/reviews/native_retention_200dbc7b_codex_review_2026-11-12.md`. `src/data_sheets_schema/native_shared_results_orchestration.py`, about lines 307 to 327 (the optional artifacts are added to the snapshot at about line 315); `src/data_sheets_schema/native_execution_orchestration.py`, about 512 to 514. If a kept record is modified, removed or replaced after its read and before `snapshot.verify_unchanged()`, that call raises outside the per-artifact handlers, `incomplete_capture` never returns, and publication proceeds with nothing captured: no streams, no retained records, no omission reasons.

Repair, one commit on `codex/native-incomplete-capture-retention-20261112`: verify each optional artifact on its own; an unstable one is removed from the snapshot consistently and recorded with its omission reason, and the others and the streams are kept. Strict all-or-nothing verification stays for a successful capture. Tests: one optional artifact changed between its read and the final verification, asserting that the public failure publication keeps the unaffected record and the streams, reports the omission and reads back exactly; and a public finalization after a final-stage floor failure, which the review found covered only by a phase fixture.

Carry Part 1's commit into the retention branch in a recorded way (the retention branch sits on the failure-record branch).

## Bounds

As before. Offline; no real-binary execution, no probe, no capture, no reservation; no provider or model call; nothing pushed; no GitHub write; protected files equal to main; guard v1 byte-identical.

## Handoff

Update `R/notes/development_efficiency_20261111/handoffs/codex-h3-failure-record-and-retention-20261112.md` and its JSON. Answer first: the two commits, what the diagnostic readback now cross-checks, what an unstable optional artifact now leaves behind, and the test counts. Then the final order of all your branches for integration: hardening (with #5992 and #5993), failure record (with #6015), retention (with #6016), each with its head.

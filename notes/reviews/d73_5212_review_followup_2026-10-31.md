# D73 follow-up to the 4cde66d2d implementation review

Work is in progress; this is not a completed-validation report.

## Required PR merge strategy

**#5212 must land as a merge commit. Do not squash or rebase it.** The positive
D41 ancestry boundary is `8ab03fda923d2c8caa9a2e65e558be73e92500e9`.
The explicit ancestry regression fails in a full repository if that commit is
not an ancestor of HEAD; a shallow repository skips with the stated reason
that the ancestry cannot be established from its incomplete graph.

## Completed initial checks

- Finding 1: all four prefix-sibling controls failed on unchanged production
  source at `4cde66d2d`. The same flat-layout canary passed after the fix, then
  all 214 legacy/refusal/verifier regressions passed. Raw reports and artifacts
  are under the authorized `scratch-5212fix/f1-*` basetemps.
- D73(a): 17 targeted age/reporting checks passed. Unknown age is eligible and
  reported separately from quality rows and the registered-evaluation plan hash.
- D73(b): the verifier remains limited to generic_v6 API records with a
  structured request specification. Other API conditions and agentic records
  are unsupported; the lead will file the extension issue.
- D73(c): all four additional accepted flips are disclosed individually in
  `tests/fixtures/pre_d41/README.md`.

The stopped earlier gate is evidence of `4cde66d2d` only. The revised validation
will use external basetemps, the requested broad set and one ordinary shard
out of four with up to four xdist workers. Main will be merged only after those
checks, with no hand resolution of production conflicts.

## NF3-B / #5409: all 16 original failing nodes

### Additional local finding NF-D73-1 (introduced, fixed)

The first broad run at `439c7b73d` exposed an omission in the anchored
ownership matcher: `usage_ledger.abandoned_journal_path()` emits
`PROJECT_abandoned_attempts.jsonl`, which the new matcher did not recognize.
The existing D69 adoption-refusal test failed with “DID NOT RAISE”. That run
was intentionally stopped at 89 passes and one failure; it is partial evidence.
All 24 new entry/layout/resume regressions failed before the correction.
The exact anchored artifact name is now included, and both execution and
verifier sibling controls include `P_X` abandoned evidence. No GitHub issue was
filed because this task expressly forbids network and `gh`; this paragraph
retains the finding for the lead's review/issue workflow.

No production guard was weakened or reordered. The following dispositions
include repairs already present at `4cde66d2d`; only the two `metadata_dir`
stub additions are new in this follow-up. Each row names the original node,
including both retired parameters. Paths are under `tests/`.

| # | Original node | Disposition and reason |
|---|---|---|
| 1 | `test_download/test_api_runner.py::TestValidatorRepairRefreshCheckpoint::test_missing_corrupt_or_stale_checkpoint_refuses_before_calls` | Retain checkpoint permutations, earlier ownership/parse errors and exact journal discrepancy assertions (event key, expected and found). The independently latched tampering refusal correctly precedes the controller guard; zero dispatch and unchanged evidence remain required. |
| 2 | `test_duplicate_keys.py::TestReviewRound::test_the_repair_round_is_told_about_a_duplicate_and_checks_it_again` | Prepare the guarded account before partial output. This is a current repair test, so a journal-less historical setup was wrong. Retain real repair prompt and duplicate recheck assertions. |
| 3 | `test_fresh_orphan_partial_generation.py::test_fresh_restart_does_not_accept_unrelated_archived_attempts` | Authentic C1: the earlier D68/D69 refusal is correct; assert zero calls and whole-tree equality. |
| 4 | `test_fresh_orphan_partial_generation.py::test_fresh_restart_records_an_orphaned_partial_predecessor[missing]` | Authentic C3: same-directory restart is forbidden, even with the ledger missing. Assert refusal and whole-tree equality. |
| 5 | `test_fresh_orphan_partial_generation.py::test_fresh_restart_records_an_orphaned_partial_predecessor[malformed]` | Authentic C2: malformed historical accounting cannot authorize archival or execution. Assert refusal and whole-tree equality. |
| 6 | `test_fresh_orphan_partial_generation.py::test_predecessor_binding_survives_interrupted_index_activation` | Authentic C4 call 3: a prepared journal-less ledger cannot resume. Preserve the interrupted index and all evidence. |
| 7 | `test_generation_manifest_identity.py::test_changed_inputs_in_portable_record_are_refused_without_a_ledger` | Retain the d9b69d84d repair: test the portable parser's success and exact manifest-drift error independently, then require the public deleted-ledger journal refusal and unchanged tree. D41 correctly refuses first. |
| 8 | `test_generation_manifest_identity.py::test_legacy_progress_without_input_evidence_requires_explicit_restart` | Authentic C5: missing input identity no longer offers a restart route. Earlier D68/D69 no-spend refusal is correct. |
| 9 | `test_generation_recovery_review.py::test_changed_input_restart_recovers_only_its_own_snapshots` | Use a valid guarded restart, then assert exact journal discrepancy for changed snapshot evidence. Retain independent snapshot-byte parser checks and unchanged state. |
| 10 | `test_generation_recovery_review.py::test_explicit_restart_preserves_an_unreadable_snapshot_index` | Authentic C6, now both resume modes: refusal preserves the unreadable historical index instead of archiving it. |
| 11 | `test_midnight_resume.py::test_automatic_date_is_restored_before_cached_instruction_or_portable_checks[True-False]` | Retired before 4cde66d2d; **this is one of #5409's 16**. Deleting a current guarded ledger tests D41 damage, not historical portability. Authentic C7 verifies read-only and refuses execution; current deleted-ledger guards remain tested. |
| 12 | `test_packaging_review_r7.py::test_readable_repair_gets_another_round_when_schema_findings_increase` | Prepare current accounting before partial output. Retain the two repair calls and increased-findings progression; no legacy continuation is needed. |
| 13 | `test_reasoning_generation_restart.py::test_fresh_generation_archives_malformed_predecessor_reasoning[True]` | Retired before 4cde66d2d; **this is one of #5409's 16**. The portable variant deleted current guarded accounting. Authentic C8 now proves read-only refusal; the intact current-journal restart parameter remains. |
| 14 | `test_resume_instrument_and_activation.py::test_portable_record_refuses_changed_instruction_without_a_ledger` | Retain d9b69d84d's independent parser success/exact instruction-drift checks and the public deleted-ledger journal refusal, with zero output changes. |
| 15 | `test_thinking_request.py::TestTheRequestStatesThinking::test_the_runner_request_path_puts_the_display_on_the_wire` | Add a real temporary `metadata_dir` to the stub. Retain the explicitly mocked per-attempt latch check and assert it was called once; this unit tests actual SDK request construction on a mock transport. |
| 16 | `test_thinking_request.py::TestTheRequestStatesThinking::test_the_shared_2_admission_path_puts_the_display_on_the_wire` | Add the same real temporary `metadata_dir`. Retain the latch invocation assertion and bounded-client wire assertions; no production guard bypass added. |

| Source | Files |
| --- | ---: |
| 41735860489 | 528 |
| retained-current | 32 |
| 41707437114 | 75 |

| File (`tests/`) | Previous s | New s | Change s | Source |
| --- | ---: | ---: | ---: | --- |
| test_report_admission.py | 3008.989 | 4576.868 | +1567.879 | 41707437114 |
| test_d42_claude_d55.py | 2892.072 | 2184.783 | -707.289 | 41735860489 |
| test_native_receipt_origin_reporting.py | 1019.910 | 475.608 | -544.302 | 41735860489 |
| test_download/test_api_runner.py | 3676.161 | 3200.050 | -476.111 | 41735860489 |
| test_shared_generation_runtime.py | 2549.919 | 3017.212 | +467.293 | 41735860489 |
| test_native_attempt_supervisor.py | 1122.606 | 770.845 | -351.761 | 41735860489 |
| test_receipt_completion_runtime.py | 726.880 | 1068.698 | +341.818 | 41735860489 |
| test_preflight_resource_authority.py | 118.985 | 400.561 | +281.576 | 41735860489 |
| test_generation_specificity_skill.py | 909.462 | 1148.699 | +239.237 | 41707437114 |
| test_d69_artifact_completeness.py | 1136.778 | 1357.606 | +220.828 | 41735860489 |
| test_shared_generation_scope_context.py | 797.771 | 583.657 | -214.114 | 41735860489 |
| test_arm_comparison.py | 197.986 | 402.117 | +204.131 | 41735860489 |
| test_evaluation_model.py | 206.108 | 394.885 | +188.777 | 41735860489 |
| test_d41_request_parity.py | 235.456 | 394.567 | +159.111 | 41735860489 |
| test_evaluation/test_cross_family_panel_analysis.py | 129.384 | 265.218 | +135.834 | 41735860489 |

| Run | Shard | Case s | Job wall s | Residual s |
| --- | ---: | ---: | ---: | ---: |
| 41735860489 | 1 | 6341.707 | 1674.000 | 88.573 |
| 41735860489 | 3 | 7430.806 | 2473.000 | 615.298 |
| 41735860489 | 4 | 5723.472 | 1511.000 | 80.132 |
| 41735860489 | 5 | 9010.219 | 2351.000 | 98.445 |
| 41735860489 | 6 | 7718.491 | 2025.000 | 95.377 |
| 41707437114 | 2 | 8397.341 | 2409.000 | 309.665 |
| 41707437114 | 3 | 7209.788 | 2133.000 | 330.553 |
| 41707437114 | 4 | 7804.379 | 2145.000 | 193.905 |
| 41707437114 | 6 | 5683.359 | 1643.000 | 222.160 |

| Plan | Shard | Files | Cases | Case s | Estimated job s | Margin to 80% s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| PR | 1 | 103 | 3353 | 7570.132 | 2507.832 | -347.832 |
| PR | 2 | 106 | 4210 | 7570.135 | 2507.832 | -347.832 |
| PR | 3 | 106 | 3696 | 7570.133 | 2507.832 | -347.832 |
| PR | 4 | 106 | 3477 | 7570.133 | 2507.832 | -347.832 |
| PR | 5 | 107 | 4381 | 7570.133 | 2507.832 | -347.832 |
| PR | 6 | 107 | 3243 | 7570.136 | 2507.832 | -347.832 |
| Main | 1 | 158 | 5699 | 11355.201 | 3454.099 | -574.099 |
| Main | 2 | 159 | 5001 | 11355.200 | 3454.098 | -574.098 |
| Main | 3 | 159 | 5964 | 11355.201 | 3454.099 | -574.099 |
| Main | 4 | 159 | 5696 | 11355.200 | 3454.099 | -574.099 |

| Largest file (`tests/`) | Weight s | Source | PR shard | Main shard |
| --- | ---: | --- | ---: | ---: |
| test_report_admission.py | 4576.868 | 41707437114 | 1 | 1 |
| test_download/test_api_runner.py | 3200.050 | 41735860489 | 2 | 2 |
| test_shared_generation_runtime.py | 3017.212 | 41735860489 | 3 | 3 |
| test_bc1_registration.py | 2808.544 | 41735860489 | 4 | 4 |
| test_d42_claude_d55.py | 2184.783 | 41735860489 | 5 | 4 |
| test_native_execution.py | 1865.454 | 41735860489 | 6 | 3 |
| test_bc1_g2_journal.py | 1492.334 | 41735860489 | 6 | 2 |
| test_d69_artifact_completeness.py | 1357.606 | 41735860489 | 5 | 1 |
| test_generation_specificity_skill.py | 1148.699 | 41707437114 | 4 | 2 |
| test_receipt_completion_runtime.py | 1068.698 | 41735860489 | 3 | 3 |
| test_native_attempt_supervisor.py | 770.845 | 41735860489 | 2 | 4 |
| test_evaluation/test_cross_family_judge_analysis.py | 745.260 | 41735860489 | 6 | 4 |
| test_routed_condition_reporting.py | 715.424 | 41707437114 | 5 | 2 |
| test_usage_ledger.py | 666.370 | 41735860489 | 4 | 1 |
| test_source_heading_runtime_api.py | 636.861 | retained-current | 2 | 3 |

| Retained file (`tests/`): neither BC1+G2 run complete | Weight s | PR shard | Main shard |
| --- | ---: | ---: | ---: |
| test_source_heading_runtime_api.py | 636.861 | 2 | 3 |
| test_backfill_interrupted_api.py | 198.829 | 5 | 2 |
| test_scope.py | 167.271 | 5 | 2 |
| test_absence_lint.py | 140.492 | 3 | 4 |
| test_shared_generation_selection.py | 76.689 | 2 | 4 |
| test_report_gate.py | 45.388 | 6 | 2 |
| test_recall_target_baseline.py | 31.530 | 2 | 2 |
| test_receipt_sources.py | 26.770 | 6 | 4 |
| test_receipt_rereceipt.py | 20.028 | 6 | 2 |
| test_data_standards.py | 13.762 | 2 | 3 |
| test_external_dataset_onboarding.py | 12.459 | 5 | 1 |
| test_backfill_manifest_portability.py | 10.015 | 4 | 4 |
| test_shared_generation_completed_replay.py | 8.837 | 1 | 4 |
| test_native_full_schema_profile_evidence.py | 6.310 | 5 | 3 |
| test_attainability_check_gate.py | 4.502 | 1 | 2 |
| test_schema/test_schema_stats.py | 3.233 | 1 | 4 |
| test_review_pack_schema_refresh.py | 2.661 | 6 | 1 |
| test_agentic_provenance_completeness.py | 1.635 | 3 | 2 |
| test_evaluation/test_enumeration.py | 1.338 | 3 | 4 |
| test_download/test_organized_dataset_extractor.py | 1.092 | 5 | 1 |
| test_report_core_inventory.py | 0.994 | 6 | 4 |
| test_native_temperature.py | 0.706 | 3 | 3 |
| test_ci_bytecode_hygiene.py | 0.424 | 4 | 2 |
| test_rocrate/test_legacy_root_identity_adversarial.py | 0.358 | 6 | 1 |
| test_evaluation/test_legacy_score_repair_refuses.py | 0.157 | 4 | 4 |
| test_cli/test_rocrate_raw_merge_retirement.py | 0.129 | 2 | 3 |
| test_resume_inputs.py | 0.094 | 1 | 2 |
| test_schema_release_identity.py | 0.092 | 2 | 4 |
| test_download/test_concatenate.py | 0.021 | 2 | 2 |
| test_stream_guard.py | 0.017 | 2 | 2 |
| test_cli/test_repo_utils.py | 0.006 | 4 | 3 |
| test_legacy_migration.py | 0.006 | 4 | 1 |

| Three slowest selected cases | Measured s | PR shard | Main shard |
| --- | ---: | ---: | ---: |
| `tests/test_bc1_g2_journal.py::test_every_bc1_response_is_journaled_before_parse` | 1452.424 | 6 | 2 |
| `tests/test_bc1_registration.py::test_completed_run_cli_and_library_refuse_before_any_write[aggregate_input_tokens-over allowance]` | 1442.672 | 4 | 4 |
| `tests/test_shared_generation_runtime.py::test_real_complete_api_pipeline_and_completed_recheck` | 1211.453 | 3 | 3 |

# N2 unit 2 offline validation

Working tree: `/private/tmp/d4d-codex-n2-2-20261025`.
Interpreter: primary checkout `.venv/bin/python` (Python 3.13).
Environment: `PYTHONPATH` selects this tree's `src` and repository root.
Every listed pytest invocation used `-xq --tb=short`. Runs were serial after
the earlier exploratory runs; source remained frozen within each listed run.
No provider, live native binary, GitHub or push call occurred.

## Receipt and current-route regressions

Source head `0d5bddbc0`: **310 passed**, 13 deprecation warnings, 422.26 s.
Log: `receipts-0d5bddbc0.log`.

```
tests/test_native_receipt_policy_dispatch.py
tests/test_derive_core_selected_schemas.py
tests/test_receipt_origin_native_record.py
tests/test_native_shared_provenance.py
tests/test_native_shared_receipt_write.py
tests/test_native_shared_initial_receipts.py
tests/test_native_shared_receipt_readers.py
tests/test_receipt_completion_policy.py
tests/test_receipts.py
tests/test_backfill_checks.py
tests/test_derive_core.py
tests/test_native_receipt_origin_reporting.py
tests/test_native_receipt_origin_registration.py
tests/test_native_receipt_origin_stage_join.py
```

## N2-R1 causal parser mutation

Source head `0d5bddbc0` plus the new regression test: **one expected failure**
at the first parser replacement, after the literal constructor had refused.
Log: `cache-target-parser-before.log`. After adding the four guard bindings,
the following group passed **73 tests**, one deprecation warning, 4.85 s;
log: `cache-target-parser-after.log`. This correction is commit `7ada9e7c4`.

```
tests/test_native_catalog_target_schema_events.py
tests/test_native_catalog_dependencies.py
tests/test_native_typed_catalog.py
```

## Final cache, permission, controller and stage group

Frozen source head `f719de581`: **267 passed**, one deprecation warning,
67.86 s. Log: `final-f719de581-cache-permission-controller.log`.

```
tests/test_native_permission_projection_derivation.py
tests/test_native_lexical_ancestry.py
tests/test_native_permission_wrapper_encoding.py
tests/test_native_policy_digest_scope.py
tests/test_native_catalog_target_schema_events.py
tests/test_native_catalog_dependencies.py
tests/test_native_typed_catalog.py
tests/test_typed_audit_schema_reuse.py
tests/test_typed_audit_captured_assets.py
tests/test_omission_yaml_event_reuse.py
tests/test_native_execution_engine.py
tests/test_native_gate_engine.py
tests/test_native_shared_controller.py
tests/test_native_shared_prompt_cli.py
tests/test_native_shared_stages.py
```

The 73-test group is included in the final 267 and must not be counted twice.
The 310-test group predates the narrow cache and pure permission corrections;
their changed boundaries have the focused final tests above. No complete-suite
or 900-second end-to-end runtime acceptance is asserted. Unit 3 owns the real
binary probe producer and subscription front door; unit 4 owns final alignment
and the fake-runtime 900-second acceptance.

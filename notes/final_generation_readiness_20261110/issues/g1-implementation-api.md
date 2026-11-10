Read-only review of the first G1 draft `tests/test_final_generation_acceptance.py` found that it cannot exercise the intended acceptance boundary because it calls APIs that the pinned source does not implement.

- `lint_instance(..., label=...)` uses an unsupported argument. Actual signature takes data, schema_path, target_class, and optional skip_schema_validation.
- Errors expose `Issue.code`, not `Issue.category`.
- `derive_core.derive_core` takes only full and pair_schema; phase4_complete and include_transformation_receipt are unsupported there.
- `validate_pair_data` does not accept full_path or core_path.

These are fixture implementation defects, not failures of generated data. Correct against actual source signatures before using runtime evidence. Reduce the oversized draft to the assigned tiny positive case and four diagnostic negative mutations; reuse existing permission-normalization and renderer tests rather than introducing repeated broad cases. Keep schema identity dynamic for the upcoming 3.2.1 integration. No production changes are requested.

Completed source review additionally confirmed linter paths are JSON pointers (`/description`), not `$.description`. Unknown Core fields produce `unknown-field`; the expanded draft incorrectly demands `schema-violation` for those cases. The helper executes the entire expanded suite and needs a positive-only canary selection plus an existing external deadline. These are covered by simplifying to the assigned boundaries. Positional schema/class linter arguments are valid.

Adversarial review of G3 commit `36d9bb25b`, `docs/final-generation-acceptance.md`, found inaccurate descriptions of the implemented record contract.

Section 6 says the API stub guard admits an `id` OR `Dataset`/`resources`. Actual `_looks_like_a_record` at pinned `api_runner.py:3576–3608` requires `id`, rejects every unknown top-level key, and requires at least five keys.

Section 2 describes nonexistent derivation symbols (`derive_core_dict`, `CORE_DATASET_SLOTS`, `_project_resources`, `_project_distributions`, `_derive_dialect`). The implementation uses runtime `PairSchema`, `synchronize_core_data` and `_add_distributions`. The guide should state observable preservation/projection behavior without an invented implementation tour. Verify inline Person and schema-field assertions against the actual pinned schema as part of this same correction.

Fix the documentation only; do not change the schema or implementation to fit the draft.

Completed review confirmed: `Dataset.creators` is a list of `Creator` containers and `maintainers` a list of `Maintainer`; Person is nested (for example `principal_investigator`). Also the described `evaluate_pair` symbol is not the implemented API, and actual `validate_pair_data` / pair CLI checks consistency, not schema validity. Preserve separate full/Core shape validation.

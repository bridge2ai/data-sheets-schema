# AI_READI Full/Core Reconciliation

Model: gpt-5.5
Reasoning effort: high
Mode: fast
Temperature: 0.0
Generated: 2026-07-23

Full D4D: `data/d4d_concatenated/claudecode_agent/2026-07-23_gpt-5.5-high-fast/AI_READI_d4d.yaml`
Core D4D: `data/d4d_concatenated/claudecode_agent_core/2026-07-23_gpt-5.5-high-fast/AI_READI_d4d_core.yaml`

## Summary

The core record was derived from the full D4D plus `data/preprocessed/concatenated/AI_READI_preprocessed.txt`.
Scalar overlapping fields were kept byte-identical where both records include the same slot.
Narrative overlapping fields were reviewed for consistency and no contradictory values remain.

## Discrepancies

| Field | Full value | Core value | Resolution | Files changed |
| --- | --- | --- | --- | --- |
| `distributions` / `file_collections` | Full schema does not use `distributions`; no `file_collections` slot was present in the validated structural reference. | Core includes two `CoreDistribution` objects for public and controlled access ZIP archives. | Accepted as the schema-defined structural difference. Distribution facts remain represented in full through `distribution_formats`, `subsets`, `license_and_use_terms`, `external_resources`, and maintenance/access descriptions. | Core only |
| `confidential_elements` | Not present in full record. | Present in core record. | Accepted as an additional CoreDataset-supported data governance field derived from source-supported controlled-access documentation. No scalar conflict. | Core only |
| `prohibited_uses` | Represented in full narrative fields `discouraged_uses` and `license_and_use_terms`. | Present as explicit core objects. | Accepted as core-specific normalization of license restrictions. No factual conflict. | Core only |
| `collection_timeframes`, `data_collectors`, `distribution_dates`, `version_access`, `extension_mechanism`, `informed_consent`, `at_risk_populations`, `is_deidentified`, `ip_restrictions`, `regulatory_restrictions` | Not present as top-level full slots in the validated full record. | Present as explicit core fields. | Accepted as CoreDataset-supported normalized fields derived from the full record and source documents. No back-port needed beyond existing full narratives. | Core only |

## Overlapping Fields Checked

Checked 32 shared top-level fields: `id`, `name`, `title`, `description`, `page`, `language`, `license`, `doi`, `keywords`, `purposes`, `tasks`, `addressing_gaps`, `creators`, `funders`, `instances`, `sampling_strategies`, `subpopulations`, `collection_mechanisms`, `acquisition_methods`, `preprocessing_strategies`, `cleaning_strategies`, `intended_uses`, `discouraged_uses`, `license_and_use_terms`, `distribution_formats`, `maintainers`, `updates`, `retention_limit`, `ethical_reviews`, `human_subject_research`, `sensitive_elements`, and `external_resources`.

## Final Validation Status

- Full schema validation: passed with `linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset`.
- Core schema validation: passed with `linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml -C CoreDataset`.
- Full ontology term validation: blocked because `linkml-term-validator` is not available as a command or importable module in the active Poetry environment.
- Remaining scalar conflicts: 0.

# Enum: ComplianceStatusEnum 




_Compliance status for regulatory frameworks. Indicates the extent to which a dataset complies with specific regulations (e.g., HIPAA, 45 CFR 46). These are workflow status values that may evolve as regulations are assessed or as the dataset is modified._



URI: [data_sheets_schema:ComplianceStatusEnum](https://w3id.org/bridge2ai/data-sheets-schema/ComplianceStatusEnum)

## Permissible Values

| Value | Meaning | Description |
| --- | --- | --- |
| compliant | None | Dataset is compliant with the regulation |
| partially_compliant | None | Dataset is partially compliant, with known limitations or gaps in compliance |
| not_compliant | None | Dataset does not comply with the regulation |
| not_applicable | None | Regulation does not apply to this dataset based on scope, jurisdiction, or su... |
| under_review | None | Compliance status is currently under review or assessment |




## Slots

| Name | Description |
| ---  | --- |
| [hipaa_compliant](hipaa_compliant.md) | Indicates compliance with the Health Insurance Portability and Accountability... |





## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema






## LinkML Source

<details>
```yaml
name: ComplianceStatusEnum
description: Compliance status for regulatory frameworks. Indicates the extent to
  which a dataset complies with specific regulations (e.g., HIPAA, 45 CFR 46). These
  are workflow status values that may evolve as regulations are assessed or as the
  dataset is modified.
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
permissible_values:
  compliant:
    text: compliant
    description: Dataset is compliant with the regulation. All requirements are met
      and documented.
    broad_mappings:
    - dcterms:conformsTo
  partially_compliant:
    text: partially_compliant
    description: Dataset is partially compliant, with known limitations or gaps in
      compliance. Some but not all requirements are met.
    broad_mappings:
    - dcterms:conformsTo
  not_compliant:
    text: not_compliant
    description: Dataset does not comply with the regulation. Significant requirements
      are not met.
  not_applicable:
    text: not_applicable
    description: Regulation does not apply to this dataset based on scope, jurisdiction,
      or subject matter.
  under_review:
    text: under_review
    description: Compliance status is currently under review or assessment. Final
      determination has not been made.

```
</details>
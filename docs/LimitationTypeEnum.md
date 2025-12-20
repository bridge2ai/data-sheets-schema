# Enum: LimitationTypeEnum 




_Types of limitations that may affect dataset use or interpretation. Distinct from biases (systematic errors) and anomalies (data quality issues)._



URI: [data_sheets_schema:LimitationTypeEnum](https://w3id.org/bridge2ai/data-sheets-schema/LimitationTypeEnum)

## Permissible Values

| Value | Meaning | Description |
| --- | --- | --- |
| scope_limitation | None | Dataset does not cover all intended use cases or populations |
| temporal_limitation | None | Dataset is limited to specific time periods |
| coverage_limitation | None | Dataset has incomplete coverage of target domain |
| methodological_limitation | None | Data collection methodology introduces constraints |
| representativeness_limitation | None | Dataset may not be representative of target population |
| resolution_limitation | None | Data granularity or resolution is insufficient for some uses |
| integration_limitation | None | Challenges in combining with other data sources |




## Slots

| Name | Description |
| ---  | --- |
| [limitation_type](limitation_type.md) | Category of limitation (e |





## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema






## LinkML Source

<details>
```yaml
name: LimitationTypeEnum
description: Types of limitations that may affect dataset use or interpretation. Distinct
  from biases (systematic errors) and anomalies (data quality issues).
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
permissible_values:
  scope_limitation:
    text: scope_limitation
    description: Dataset does not cover all intended use cases or populations. The
      scope of the dataset is narrower than the intended application domain.
  temporal_limitation:
    text: temporal_limitation
    description: Dataset is limited to specific time periods. Data may not reflect
      current conditions or may not be applicable to other time periods.
  coverage_limitation:
    text: coverage_limitation
    description: Dataset has incomplete coverage of target domain. Missing data points,
      categories, or geographic regions within the intended scope.
  methodological_limitation:
    text: methodological_limitation
    description: Data collection methodology introduces constraints. Limitations arising
      from how data was gathered, measured, or processed.
  representativeness_limitation:
    text: representativeness_limitation
    description: Dataset may not be representative of target population. Sample may
      not accurately reflect the broader population of interest.
  resolution_limitation:
    text: resolution_limitation
    description: Data granularity or resolution is insufficient for some uses. Level
      of detail may not support fine-grained analysis or specific applications.
  integration_limitation:
    text: integration_limitation
    description: Challenges in combining with other data sources. Incompatibilities
      in formats, identifiers, or schemas that hinder data integration.

```
</details>
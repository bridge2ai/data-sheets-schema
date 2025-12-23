

# Slot: known_limitations 


_Known limitations of the dataset that may affect its use or interpretation. Distinct from biases (systematic errors) and anomalies (data quality issues)._





URI: [data_sheets_schema:known_limitations](https://w3id.org/bridge2ai/data-sheets-schema/known_limitations)
Alias: known_limitations

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [DataSubset](DataSubset.md) | A subset of a dataset, likely containing multiple files of multiple potential... |  no  |
| [Dataset](Dataset.md) | A single component of related observations and/or information that can be rea... |  no  |






## Properties

* Range: [DatasetLimitation](DatasetLimitation.md)

* Multivalued: True




## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | data_sheets_schema:known_limitations |
| native | data_sheets_schema:known_limitations |




## LinkML Source

<details>
```yaml
name: known_limitations
description: Known limitations of the dataset that may affect its use or interpretation.
  Distinct from biases (systematic errors) and anomalies (data quality issues).
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
alias: known_limitations
owner: Dataset
domain_of:
- Dataset
range: DatasetLimitation
multivalued: true
inlined: true
inlined_as_list: true

```
</details>
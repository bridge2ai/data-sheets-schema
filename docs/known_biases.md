

# Slot: known_biases 


_Known biases present in the dataset that may affect fairness, representativeness, or model performance. Uses BiasTypeEnum for standardized bias categorization mapped to the AI Ontology (AIO)._





URI: [data_sheets_schema:known_biases](https://w3id.org/bridge2ai/data-sheets-schema/known_biases)
Alias: known_biases

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [DataSubset](DataSubset.md) | A subset of a dataset, likely containing multiple files of multiple potential... |  no  |
| [Dataset](Dataset.md) | A single component of related observations and/or information that can be rea... |  no  |






## Properties

* Range: [DatasetBias](DatasetBias.md)

* Multivalued: True




## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | data_sheets_schema:known_biases |
| native | data_sheets_schema:known_biases |




## LinkML Source

<details>
```yaml
name: known_biases
description: Known biases present in the dataset that may affect fairness, representativeness,
  or model performance. Uses BiasTypeEnum for standardized bias categorization mapped
  to the AI Ontology (AIO).
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
alias: known_biases
owner: Dataset
domain_of:
- Dataset
range: DatasetBias
multivalued: true
inlined: true
inlined_as_list: true

```
</details>
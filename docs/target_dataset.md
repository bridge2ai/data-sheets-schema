

# Slot: target_dataset 


_The dataset that this relationship points to. Can be specified by identifier, URL, or Dataset object._





URI: [data_sheets_schema:target_dataset](https://w3id.org/bridge2ai/data-sheets-schema/target_dataset)
Alias: target_dataset

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [DatasetRelationship](DatasetRelationship.md) | Typed relationship to another dataset, enabling precise specification of how ... |  no  |






## Properties

* Range: [String](String.md)

* Required: True




## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | data_sheets_schema:target_dataset |
| native | data_sheets_schema:target_dataset |




## LinkML Source

<details>
```yaml
name: target_dataset
description: The dataset that this relationship points to. Can be specified by identifier,
  URL, or Dataset object.
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
alias: target_dataset
owner: DatasetRelationship
domain_of:
- DatasetRelationship
range: string
required: true

```
</details>
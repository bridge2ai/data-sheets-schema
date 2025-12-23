

# Slot: related_datasets 


_Related datasets with typed relationships (e.g., supplements, derives from, is version of). Use DatasetRelationship class to specify relationship types._





URI: [data_sheets_schema:related_datasets](https://w3id.org/bridge2ai/data-sheets-schema/related_datasets)
Alias: related_datasets

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [DataSubset](DataSubset.md) | A subset of a dataset, likely containing multiple files of multiple potential... |  no  |
| [Dataset](Dataset.md) | A single component of related observations and/or information that can be rea... |  no  |






## Properties

* Range: [DatasetRelationship](DatasetRelationship.md)

* Multivalued: True




## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | data_sheets_schema:related_datasets |
| native | data_sheets_schema:related_datasets |




## LinkML Source

<details>
```yaml
name: related_datasets
description: Related datasets with typed relationships (e.g., supplements, derives
  from, is version of). Use DatasetRelationship class to specify relationship types.
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
alias: related_datasets
owner: Dataset
domain_of:
- Dataset
range: DatasetRelationship
multivalued: true
inlined: true
inlined_as_list: true

```
</details>
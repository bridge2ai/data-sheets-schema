

# Slot: resources 


_Sub-resources or component datasets. Used in DatasetCollection to contain Dataset objects, and in Dataset to allow nested resource structures._





URI: [data_sheets_schema:resources](https://w3id.org/bridge2ai/data-sheets-schema/resources)
Alias: resources

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [Dataset](Dataset.md) | A single component of related observations and/or information that can be rea... |  yes  |
| [DataSubset](DataSubset.md) | A subset of a dataset, likely containing multiple files of multiple potential... |  no  |
| [DatasetCollection](DatasetCollection.md) | A collection of related datasets, likely containing multiple files of multipl... |  yes  |






## Properties

* Range: [Dataset](Dataset.md)

* Multivalued: True




## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | data_sheets_schema:resources |
| native | data_sheets_schema:resources |




## LinkML Source

<details>
```yaml
name: resources
description: Sub-resources or component datasets. Used in DatasetCollection to contain
  Dataset objects, and in Dataset to allow nested resource structures.
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
alias: resources
domain_of:
- DatasetCollection
- Dataset
range: Dataset
multivalued: true

```
</details>


# Slot: created_by 



URI: [dcterms:creator](http://purl.org/dc/terms/creator)
Alias: created_by

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [Dataset](Dataset.md) | A single component of related observations and/or information that can be rea... |  no  |
| [DatasetCollection](DatasetCollection.md) | A collection of related datasets, likely containing multiple files of multipl... |  no  |
| [DataSubset](DataSubset.md) | A subset of a dataset, likely containing multiple files of multiple potential... |  no  |
| [Information](Information.md) | Grouping for datasets and data files |  no  |






## Properties

* Range: [String](String.md)




## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | dcterms:creator |
| native | data_sheets_schema:created_by |




## LinkML Source

<details>
```yaml
name: created_by
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
slot_uri: dcterms:creator
alias: created_by
domain_of:
- Information
range: string

```
</details>
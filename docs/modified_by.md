

# Slot: modified_by 



URI: [pav:lastUpdateBy](http://purl.org/pav/lastUpdateBy)
Alias: modified_by

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [DatasetCollection](DatasetCollection.md) | A collection of related datasets, likely containing multiple files of multipl... |  no  |
| [Information](Information.md) | Grouping for datasets and data files |  no  |
| [Dataset](Dataset.md) | A single component of related observations and/or information that can be rea... |  no  |
| [DataSubset](DataSubset.md) | A subset of a dataset, likely containing multiple files of multiple potential... |  no  |






## Properties

* Range: [String](String.md)




## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | pav:lastUpdateBy |
| native | data_sheets_schema:modified_by |




## LinkML Source

<details>
```yaml
name: modified_by
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
slot_uri: pav:lastUpdateBy
alias: modified_by
domain_of:
- Information
range: string

```
</details>


# Slot: doi 


_digital object identifier_





URI: [void:uriRegexPattern](http://rdfs.org/ns/void#uriRegexPattern)
Alias: doi

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

* Regex pattern: `10\.\d{4,}\/.+`




## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | void:uriRegexPattern |
| native | data_sheets_schema:doi |




## LinkML Source

<details>
```yaml
name: doi
description: digital object identifier
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
slot_uri: void:uriRegexPattern
alias: doi
domain_of:
- Information
range: string
pattern: 10\.\d{4,}\/.+

```
</details>
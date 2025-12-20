

# Slot: language 


_language in which the information is expressed_





URI: [dcterms:language](http://purl.org/dc/terms/language)
Alias: language

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [Information](Information.md) | Grouping for datasets and data files |  no  |
| [Dataset](Dataset.md) | A single component of related observations and/or information that can be rea... |  no  |
| [DataSubset](DataSubset.md) | A subset of a dataset, likely containing multiple files of multiple potential... |  no  |
| [DatasetCollection](DatasetCollection.md) | A collection of related datasets, likely containing multiple files of multipl... |  no  |






## Properties

* Range: [String](String.md)




## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | dcterms:language |
| native | data_sheets_schema:language |
| exact | schema:inLanguage |




## LinkML Source

<details>
```yaml
name: language
description: language in which the information is expressed
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
exact_mappings:
- schema:inLanguage
rank: 1000
slot_uri: dcterms:language
alias: language
domain_of:
- Information
range: string

```
</details>
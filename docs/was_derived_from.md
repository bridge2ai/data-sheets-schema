

# Slot: was_derived_from 



URI: [prov:wasDerivedFrom](http://www.w3.org/ns/prov#wasDerivedFrom)
Alias: was_derived_from

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
| self | prov:wasDerivedFrom |
| native | data_sheets_schema:was_derived_from |
| exact | dcterms:source |




## LinkML Source

<details>
```yaml
name: was_derived_from
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
exact_mappings:
- dcterms:source
rank: 1000
slot_uri: prov:wasDerivedFrom
alias: was_derived_from
domain_of:
- Information
range: string

```
</details>
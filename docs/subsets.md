

# Slot: subsets 



URI: [dcat:distribution](http://www.w3.org/ns/dcat#distribution)
Alias: subsets

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [Dataset](Dataset.md) | A single component of related observations and/or information that can be rea... |  no  |
| [DataSubset](DataSubset.md) | A subset of a dataset, likely containing multiple files of multiple potential... |  no  |






## Properties

* Range: [DataSubset](DataSubset.md)

* Multivalued: True




## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | dcat:distribution |
| native | data_sheets_schema:subsets |
| exact | schema:distribution |




## LinkML Source

<details>
```yaml
name: subsets
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
exact_mappings:
- schema:distribution
rank: 1000
slot_uri: dcat:distribution
alias: subsets
owner: Dataset
domain_of:
- Dataset
range: DataSubset
multivalued: true
inlined: true
inlined_as_list: true

```
</details>


# Slot: parent_datasets 


_Parent datasets that this dataset is part of or derived from. Enables hierarchical dataset composition (hasPart/isPartOf relationships)._





URI: [schema:isPartOf](http://schema.org/isPartOf)
Alias: parent_datasets

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [DataSubset](DataSubset.md) | A subset of a dataset, likely containing multiple files of multiple potential... |  no  |
| [Dataset](Dataset.md) | A single component of related observations and/or information that can be rea... |  no  |






## Properties

* Range: [Dataset](Dataset.md)

* Multivalued: True




## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | schema:isPartOf |
| native | data_sheets_schema:parent_datasets |
| exact | schema:isPartOf |




## LinkML Source

<details>
```yaml
name: parent_datasets
description: Parent datasets that this dataset is part of or derived from. Enables
  hierarchical dataset composition (hasPart/isPartOf relationships).
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
exact_mappings:
- schema:isPartOf
rank: 1000
slot_uri: schema:isPartOf
alias: parent_datasets
owner: Dataset
domain_of:
- Dataset
range: Dataset
multivalued: true
inlined: true
inlined_as_list: true

```
</details>
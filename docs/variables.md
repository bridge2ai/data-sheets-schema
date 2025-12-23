

# Slot: variables 


_Metadata describing individual variables, fields, or columns in the dataset._





URI: [schema:variableMeasured](http://schema.org/variableMeasured)
Alias: variables

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [DataSubset](DataSubset.md) | A subset of a dataset, likely containing multiple files of multiple potential... |  no  |
| [Dataset](Dataset.md) | A single component of related observations and/or information that can be rea... |  no  |






## Properties

* Range: [VariableMetadata](VariableMetadata.md)

* Multivalued: True




## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | schema:variableMeasured |
| native | data_sheets_schema:variables |
| exact | schema:variableMeasured |




## LinkML Source

<details>
```yaml
name: variables
description: Metadata describing individual variables, fields, or columns in the dataset.
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
exact_mappings:
- schema:variableMeasured
rank: 1000
slot_uri: schema:variableMeasured
alias: variables
owner: Dataset
domain_of:
- Dataset
range: VariableMetadata
multivalued: true
inlined: true
inlined_as_list: true

```
</details>
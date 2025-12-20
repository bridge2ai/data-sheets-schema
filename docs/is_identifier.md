

# Slot: is_identifier 


_Indicates whether this variable serves as a unique identifier or key for records in the dataset._





URI: [schema:identifier](http://schema.org/identifier)
Alias: is_identifier

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [VariableMetadata](VariableMetadata.md) | Metadata describing an individual variable, field, or column in a dataset |  no  |






## Properties

* Range: [Boolean](Boolean.md)




## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | schema:identifier |
| native | data_sheets_schema:is_identifier |




## LinkML Source

<details>
```yaml
name: is_identifier
description: Indicates whether this variable serves as a unique identifier or key
  for records in the dataset.
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
slot_uri: schema:identifier
alias: is_identifier
owner: VariableMetadata
domain_of:
- VariableMetadata
range: boolean

```
</details>
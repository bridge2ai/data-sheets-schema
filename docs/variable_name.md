

# Slot: variable_name 


_The name or identifier of the variable as it appears in the data files._





URI: [schema:name](http://schema.org/name)
Alias: variable_name

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [VariableMetadata](VariableMetadata.md) | Metadata describing an individual variable, field, or column in a dataset |  no  |






## Properties

* Range: [String](String.md)

* Required: True




## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | schema:name |
| native | data_sheets_schema:variable_name |
| exact | schema:name |




## LinkML Source

<details>
```yaml
name: variable_name
description: The name or identifier of the variable as it appears in the data files.
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
exact_mappings:
- schema:name
rank: 1000
slot_uri: schema:name
alias: variable_name
owner: VariableMetadata
domain_of:
- VariableMetadata
range: string
required: true

```
</details>


# Slot: data_type 


_The data type of the variable (e.g., integer, float, string, boolean, date, categorical). Use standard type names when possible._





URI: [schema:DataType](http://schema.org/DataType)
Alias: data_type

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [VariableMetadata](VariableMetadata.md) | Metadata describing an individual variable, field, or column in a dataset |  no  |






## Properties

* Range: [VariableTypeEnum](VariableTypeEnum.md)




## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | schema:DataType |
| native | data_sheets_schema:data_type |
| exact | schema:DataType |




## LinkML Source

<details>
```yaml
name: data_type
description: The data type of the variable (e.g., integer, float, string, boolean,
  date, categorical). Use standard type names when possible.
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
exact_mappings:
- schema:DataType
rank: 1000
slot_uri: schema:DataType
alias: data_type
owner: VariableMetadata
domain_of:
- VariableMetadata
range: VariableTypeEnum

```
</details>
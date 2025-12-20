

# Slot: maximum_value 


_The maximum value that the variable can take. Applicable to numeric variables._





URI: [schema:maxValue](http://schema.org/maxValue)
Alias: maximum_value

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [VariableMetadata](VariableMetadata.md) | Metadata describing an individual variable, field, or column in a dataset |  no  |






## Properties

* Range: [Float](Float.md)




## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | schema:maxValue |
| native | data_sheets_schema:maximum_value |




## LinkML Source

<details>
```yaml
name: maximum_value
description: The maximum value that the variable can take. Applicable to numeric variables.
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
slot_uri: schema:maxValue
alias: maximum_value
owner: VariableMetadata
domain_of:
- VariableMetadata
range: float

```
</details>
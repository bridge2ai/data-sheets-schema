

# Slot: missing_value_code 


_Code(s) used to represent missing values for this variable. Examples: "NA", "-999", "null", "". Multiple codes may be specified._





URI: [data_sheets_schema:missing_value_code](https://w3id.org/bridge2ai/data-sheets-schema/missing_value_code)
Alias: missing_value_code

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [VariableMetadata](VariableMetadata.md) | Metadata describing an individual variable, field, or column in a dataset |  no  |






## Properties

* Range: [String](String.md)

* Multivalued: True




## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | data_sheets_schema:missing_value_code |
| native | data_sheets_schema:missing_value_code |




## LinkML Source

<details>
```yaml
name: missing_value_code
description: 'Code(s) used to represent missing values for this variable. Examples:
  "NA", "-999", "null", "". Multiple codes may be specified.'
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
alias: missing_value_code
owner: VariableMetadata
domain_of:
- VariableMetadata
range: string
multivalued: true

```
</details>
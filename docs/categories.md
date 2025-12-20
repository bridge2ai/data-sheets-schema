

# Slot: categories 


_The permitted categories or values for a categorical variable. Each entry should describe a possible value and its meaning._





URI: [schema:valueReference](http://schema.org/valueReference)
Alias: categories

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
| self | schema:valueReference |
| native | data_sheets_schema:categories |




## LinkML Source

<details>
```yaml
name: categories
description: The permitted categories or values for a categorical variable. Each entry
  should describe a possible value and its meaning.
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
slot_uri: schema:valueReference
alias: categories
owner: VariableMetadata
domain_of:
- VariableMetadata
range: string
multivalued: true

```
</details>
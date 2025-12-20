

# Slot: unit 


_The unit of measurement for the variable, preferably using QUDT units (http://qudt.org/vocab/unit/). Examples: qudt:Kilogram, qudt:Meter, qudt:DegreeCelsius._





URI: [qudt:unit](http://qudt.org/schema/qudt/unit)
Alias: unit

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [VariableMetadata](VariableMetadata.md) | Metadata describing an individual variable, field, or column in a dataset |  no  |






## Properties

* Range: [Uriorcurie](Uriorcurie.md)




## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | qudt:unit |
| native | data_sheets_schema:unit |
| exact | qudt:hasUnit, schema:unitCode |




## LinkML Source

<details>
```yaml
name: unit
description: 'The unit of measurement for the variable, preferably using QUDT units
  (http://qudt.org/vocab/unit/). Examples: qudt:Kilogram, qudt:Meter, qudt:DegreeCelsius.'
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
exact_mappings:
- qudt:hasUnit
- schema:unitCode
rank: 1000
slot_uri: qudt:unit
alias: unit
owner: VariableMetadata
domain_of:
- VariableMetadata
range: uriorcurie

```
</details>
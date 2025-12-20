

# Slot: measurement_technique 


_The technique or method used to measure this variable. Examples: "mass spectrometry", "self-report survey", "GPS coordinates"._





URI: [schema:measurementTechnique](http://schema.org/measurementTechnique)
Alias: measurement_technique

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [VariableMetadata](VariableMetadata.md) | Metadata describing an individual variable, field, or column in a dataset |  no  |






## Properties

* Range: [String](String.md)




## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | schema:measurementTechnique |
| native | data_sheets_schema:measurement_technique |




## LinkML Source

<details>
```yaml
name: measurement_technique
description: 'The technique or method used to measure this variable. Examples: "mass
  spectrometry", "self-report survey", "GPS coordinates".'
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
slot_uri: schema:measurementTechnique
alias: measurement_technique
owner: VariableMetadata
domain_of:
- VariableMetadata
range: string

```
</details>


# Slot: cleaning_details 


_Details on data cleaning procedures applied._

__





URI: [dcterms:description](http://purl.org/dc/terms/description)
Alias: cleaning_details

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [CleaningStrategy](CleaningStrategy.md) | Was any cleaning of the data done (e |  no  |






## Properties

* Range: [String](String.md)

* Multivalued: True




## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | dcterms:description |
| native | data_sheets_schema:cleaning_details |




## LinkML Source

<details>
```yaml
name: cleaning_details
description: 'Details on data cleaning procedures applied.

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
slot_uri: dcterms:description
alias: cleaning_details
owner: CleaningStrategy
domain_of:
- CleaningStrategy
range: string
multivalued: true

```
</details>
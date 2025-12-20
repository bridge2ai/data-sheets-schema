

# Slot: confidentiality_details 


_Details on confidential data elements and handling procedures._

__





URI: [dcterms:description](http://purl.org/dc/terms/description)
Alias: confidentiality_details

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [Confidentiality](Confidentiality.md) | Does the dataset contain data that might be confidential (e |  no  |






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
| native | data_sheets_schema:confidentiality_details |




## LinkML Source

<details>
```yaml
name: confidentiality_details
description: 'Details on confidential data elements and handling procedures.

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
slot_uri: dcterms:description
alias: confidentiality_details
owner: Confidentiality
domain_of:
- Confidentiality
range: string
multivalued: true

```
</details>
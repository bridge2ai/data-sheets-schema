

# Slot: consent_details 


_Details on how consent was requested, provided, and documented._

__





URI: [dcterms:description](http://purl.org/dc/terms/description)
Alias: consent_details

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [CollectionConsent](CollectionConsent.md) | Did the individuals in question consent to the collection and use of their da... |  no  |






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
| native | data_sheets_schema:consent_details |




## LinkML Source

<details>
```yaml
name: consent_details
description: 'Details on how consent was requested, provided, and documented.

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
slot_uri: dcterms:description
alias: consent_details
owner: CollectionConsent
domain_of:
- CollectionConsent
range: string
multivalued: true

```
</details>


# Slot: erratum_details 


_Details on any errata or corrections to the dataset._

__





URI: [dcterms:description](http://purl.org/dc/terms/description)
Alias: erratum_details

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [Erratum](Erratum.md) | Is there an erratum? If so, please provide a link or other access point |  no  |






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
| native | data_sheets_schema:erratum_details |




## LinkML Source

<details>
```yaml
name: erratum_details
description: 'Details on any errata or corrections to the dataset.

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
slot_uri: dcterms:description
alias: erratum_details
owner: Erratum
domain_of:
- Erratum
range: string
multivalued: true

```
</details>
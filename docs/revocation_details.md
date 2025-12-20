

# Slot: revocation_details 


_Details on consent revocation mechanisms and procedures._

__





URI: [dcterms:description](http://purl.org/dc/terms/description)
Alias: revocation_details

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [ConsentRevocation](ConsentRevocation.md) | If consent was obtained, were the consenting individuals provided with a mech... |  no  |






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
| native | data_sheets_schema:revocation_details |




## LinkML Source

<details>
```yaml
name: revocation_details
description: 'Details on consent revocation mechanisms and procedures.

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
slot_uri: dcterms:description
alias: revocation_details
owner: ConsentRevocation
domain_of:
- ConsentRevocation
range: string
multivalued: true

```
</details>
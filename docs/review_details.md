

# Slot: review_details 


_Details on ethical review processes, outcomes, and supporting documentation._

__





URI: [dcterms:description](http://purl.org/dc/terms/description)
Alias: review_details

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [EthicalReview](EthicalReview.md) | Were any ethical or compliance review processes conducted (e |  no  |






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
| native | data_sheets_schema:review_details |




## LinkML Source

<details>
```yaml
name: review_details
description: 'Details on ethical review processes, outcomes, and supporting documentation.

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
slot_uri: dcterms:description
alias: review_details
owner: EthicalReview
domain_of:
- EthicalReview
range: string
multivalued: true

```
</details>
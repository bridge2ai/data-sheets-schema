

# Slot: split_details 


_Details on recommended data splits and their rationale._

__





URI: [dcterms:description](http://purl.org/dc/terms/description)
Alias: split_details

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [Splits](Splits.md) | Are there recommended data splits (e |  no  |






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
| native | data_sheets_schema:split_details |




## LinkML Source

<details>
```yaml
name: split_details
description: 'Details on recommended data splits and their rationale.

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
slot_uri: dcterms:description
alias: split_details
owner: Splits
domain_of:
- Splits
range: string
multivalued: true

```
</details>
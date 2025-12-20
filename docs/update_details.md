

# Slot: update_details 


_Details on update plans, responsible parties, and communication methods._

__





URI: [dcterms:description](http://purl.org/dc/terms/description)
Alias: update_details

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [UpdatePlan](UpdatePlan.md) | Will the dataset be updated (e |  no  |






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
| native | data_sheets_schema:update_details |




## LinkML Source

<details>
```yaml
name: update_details
description: 'Details on update plans, responsible parties, and communication methods.

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
slot_uri: dcterms:description
alias: update_details
owner: UpdatePlan
domain_of:
- UpdatePlan
range: string
multivalued: true

```
</details>
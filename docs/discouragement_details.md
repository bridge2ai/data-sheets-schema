

# Slot: discouragement_details 


_Details on tasks for which the dataset should not be used._

__





URI: [dcterms:description](http://purl.org/dc/terms/description)
Alias: discouragement_details

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [DiscouragedUse](DiscouragedUse.md) | Are there tasks for which the dataset should not be used? |  no  |






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
| native | data_sheets_schema:discouragement_details |




## LinkML Source

<details>
```yaml
name: discouragement_details
description: 'Details on tasks for which the dataset should not be used.

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
slot_uri: dcterms:description
alias: discouragement_details
owner: DiscouragedUse
domain_of:
- DiscouragedUse
range: string
multivalued: true

```
</details>
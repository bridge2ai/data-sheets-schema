

# Slot: affiliations 


_Organizations with which the creator or team is affiliated._





URI: [schema:affiliation](http://schema.org/affiliation)
Alias: affiliations

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [Creator](Creator.md) | Who created the dataset (e |  no  |






## Properties

* Range: [Organization](Organization.md)

* Multivalued: True




## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | schema:affiliation |
| native | data_sheets_schema:affiliations |




## LinkML Source

<details>
```yaml
name: affiliations
description: Organizations with which the creator or team is affiliated.
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
slot_uri: schema:affiliation
alias: affiliations
owner: Creator
domain_of:
- Creator
range: Organization
multivalued: true
inlined: true
inlined_as_list: true

```
</details>
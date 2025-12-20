

# Slot: relationship_details 


_Details on relationships between instances (e.g., graph edges, ratings)._

__





URI: [dcterms:description](http://purl.org/dc/terms/description)
Alias: relationship_details

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [Relationships](Relationships.md) | Are relationships between individual instances made explicit (e |  no  |






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
| native | data_sheets_schema:relationship_details |




## LinkML Source

<details>
```yaml
name: relationship_details
description: 'Details on relationships between instances (e.g., graph edges, ratings).

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
slot_uri: dcterms:description
alias: relationship_details
owner: Relationships
domain_of:
- Relationships
range: string
multivalued: true

```
</details>
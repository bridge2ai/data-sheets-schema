

# Slot: relationship_type 


_The type of relationship (e.g., derives_from, supplements, is_version_of). Uses DatasetRelationshipTypeEnum for standardized relationship types._





URI: [data_sheets_schema:relationship_type](https://w3id.org/bridge2ai/data-sheets-schema/relationship_type)
Alias: relationship_type

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [DatasetRelationship](DatasetRelationship.md) | Typed relationship to another dataset, enabling precise specification of how ... |  no  |






## Properties

* Range: [DatasetRelationshipTypeEnum](DatasetRelationshipTypeEnum.md)

* Required: True




## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | data_sheets_schema:relationship_type |
| native | data_sheets_schema:relationship_type |




## LinkML Source

<details>
```yaml
name: relationship_type
description: The type of relationship (e.g., derives_from, supplements, is_version_of).
  Uses DatasetRelationshipTypeEnum for standardized relationship types.
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
alias: relationship_type
owner: DatasetRelationship
domain_of:
- DatasetRelationship
range: DatasetRelationshipTypeEnum
required: true

```
</details>
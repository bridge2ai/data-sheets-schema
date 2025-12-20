

# Slot: is_shared 


_Boolean indicating whether the dataset is distributed to parties external to the dataset-creating entity._

__





URI: [dcterms:accessRights](http://purl.org/dc/terms/accessRights)
Alias: is_shared

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [ThirdPartySharing](ThirdPartySharing.md) | Will the dataset be distributed to third parties outside of the entity (e |  no  |






## Properties

* Range: [Boolean](Boolean.md)




## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | dcterms:accessRights |
| native | data_sheets_schema:is_shared |




## LinkML Source

<details>
```yaml
name: is_shared
description: 'Boolean indicating whether the dataset is distributed to parties external
  to the dataset-creating entity.

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
slot_uri: dcterms:accessRights
alias: is_shared
owner: ThirdPartySharing
domain_of:
- ThirdPartySharing
range: boolean

```
</details>


# Slot: collection_details 


_Details on direct vs. indirect collection methods and sources._

__





URI: [dcterms:description](http://purl.org/dc/terms/description)
Alias: collection_details

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [DirectCollection](DirectCollection.md) | Indicates whether the data was collected directly from the individuals in que... |  no  |






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
| native | data_sheets_schema:collection_details |




## LinkML Source

<details>
```yaml
name: collection_details
description: 'Details on direct vs. indirect collection methods and sources.

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
slot_uri: dcterms:description
alias: collection_details
owner: DirectCollection
domain_of:
- DirectCollection
range: string
multivalued: true

```
</details>
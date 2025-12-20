

# Slot: mechanism_details 


_Details on mechanisms or procedures used to collect the data._

__





URI: [dcterms:description](http://purl.org/dc/terms/description)
Alias: mechanism_details

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [CollectionMechanism](CollectionMechanism.md) | What mechanisms or procedures were used to collect the data (e |  no  |






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
| native | data_sheets_schema:mechanism_details |




## LinkML Source

<details>
```yaml
name: mechanism_details
description: 'Details on mechanisms or procedures used to collect the data.

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
slot_uri: dcterms:description
alias: mechanism_details
owner: CollectionMechanism
domain_of:
- CollectionMechanism
range: string
multivalued: true

```
</details>
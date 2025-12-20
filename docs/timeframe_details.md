

# Slot: timeframe_details 


_Details on the collection timeframe and relationship to data creation dates._

__





URI: [dcterms:description](http://purl.org/dc/terms/description)
Alias: timeframe_details

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [CollectionTimeframe](CollectionTimeframe.md) | Over what timeframe was the data collected, and does this timeframe match the... |  no  |






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
| native | data_sheets_schema:timeframe_details |




## LinkML Source

<details>
```yaml
name: timeframe_details
description: 'Details on the collection timeframe and relationship to data creation
  dates.

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
slot_uri: dcterms:description
alias: timeframe_details
owner: CollectionTimeframe
domain_of:
- CollectionTimeframe
range: string
multivalued: true

```
</details>
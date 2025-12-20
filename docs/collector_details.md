

# Slot: collector_details 


_Details on who collected the data and their compensation._

__





URI: [dcterms:description](http://purl.org/dc/terms/description)
Alias: collector_details

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [DataCollector](DataCollector.md) | Who was involved in the data collection (e |  no  |






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
| native | data_sheets_schema:collector_details |




## LinkML Source

<details>
```yaml
name: collector_details
description: 'Details on who collected the data and their compensation.

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
slot_uri: dcterms:description
alias: collector_details
owner: DataCollector
domain_of:
- DataCollector
range: string
multivalued: true

```
</details>
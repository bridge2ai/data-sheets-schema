

# Slot: raw_data_details 


_Details on raw data availability and access procedures._

__





URI: [dcterms:description](http://purl.org/dc/terms/description)
Alias: raw_data_details

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [RawData](RawData.md) | Was the "raw" data saved in addition to the preprocessed/cleaned/labeled data... |  no  |






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
| native | data_sheets_schema:raw_data_details |




## LinkML Source

<details>
```yaml
name: raw_data_details
description: 'Details on raw data availability and access procedures.

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
slot_uri: dcterms:description
alias: raw_data_details
owner: RawData
domain_of:
- RawData
range: string
multivalued: true

```
</details>
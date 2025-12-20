

# Slot: release_dates 


_Dates or timeframe for dataset release. Could be a one-time release date or multiple scheduled releases._

__





URI: [dcterms:available](http://purl.org/dc/terms/available)
Alias: release_dates

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [DistributionDate](DistributionDate.md) | When will the dataset be distributed? |  no  |






## Properties

* Range: [String](String.md)

* Multivalued: True




## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | dcterms:available |
| native | data_sheets_schema:release_dates |




## LinkML Source

<details>
```yaml
name: release_dates
description: 'Dates or timeframe for dataset release. Could be a one-time release
  date or multiple scheduled releases.

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
slot_uri: dcterms:available
alias: release_dates
owner: DistributionDate
domain_of:
- DistributionDate
range: string
multivalued: true

```
</details>
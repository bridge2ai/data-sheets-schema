

# Slot: source_description 


_Detailed description of where raw data comes from (e.g., sensors, databases, web APIs, manual collection)._

__





URI: [data_sheets_schema:source_description](https://w3id.org/bridge2ai/data-sheets-schema/source_description)
Alias: source_description

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [RawDataSource](RawDataSource.md) | Description of raw data sources before preprocessing, cleaning, or labeling |  no  |






## Properties

* Range: [String](String.md)

* Required: True




## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | data_sheets_schema:source_description |
| native | data_sheets_schema:source_description |




## LinkML Source

<details>
```yaml
name: source_description
description: 'Detailed description of where raw data comes from (e.g., sensors, databases,
  web APIs, manual collection).

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
alias: source_description
owner: RawDataSource
domain_of:
- RawDataSource
range: string
required: true

```
</details>
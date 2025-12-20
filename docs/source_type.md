

# Slot: source_type 


_Type of raw source (sensor, database, user input, web scraping, etc.)._

__





URI: [data_sheets_schema:source_type](https://w3id.org/bridge2ai/data-sheets-schema/source_type)
Alias: source_type

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [RawDataSource](RawDataSource.md) | Description of raw data sources before preprocessing, cleaning, or labeling |  no  |






## Properties

* Range: [String](String.md)

* Multivalued: True




## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | data_sheets_schema:source_type |
| native | data_sheets_schema:source_type |




## LinkML Source

<details>
```yaml
name: source_type
description: 'Type of raw source (sensor, database, user input, web scraping, etc.).

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
alias: source_type
owner: RawDataSource
domain_of:
- RawDataSource
range: string
multivalued: true

```
</details>
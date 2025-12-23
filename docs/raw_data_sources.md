

# Slot: raw_data_sources 


_Description of raw data sources before preprocessing._





URI: [data_sheets_schema:raw_data_sources](https://w3id.org/bridge2ai/data-sheets-schema/raw_data_sources)
Alias: raw_data_sources

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [DataSubset](DataSubset.md) | A subset of a dataset, likely containing multiple files of multiple potential... |  no  |
| [Dataset](Dataset.md) | A single component of related observations and/or information that can be rea... |  no  |






## Properties

* Range: [RawDataSource](RawDataSource.md)

* Multivalued: True




## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | data_sheets_schema:raw_data_sources |
| native | data_sheets_schema:raw_data_sources |




## LinkML Source

<details>
```yaml
name: raw_data_sources
description: Description of raw data sources before preprocessing.
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
alias: raw_data_sources
owner: Dataset
domain_of:
- Dataset
range: RawDataSource
multivalued: true
inlined: true
inlined_as_list: true

```
</details>
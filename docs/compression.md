

# Slot: compression 


_compression format used, if any. e.g., gzip, bzip2, zip_





URI: [data_sheets_schema:compression](https://w3id.org/bridge2ai/data-sheets-schema/compression)
Alias: compression

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [DatasetCollection](DatasetCollection.md) | A collection of related datasets, likely containing multiple files of multipl... |  no  |
| [Information](Information.md) | Grouping for datasets and data files |  no  |
| [Dataset](Dataset.md) | A single component of related observations and/or information that can be rea... |  no  |
| [DataSubset](DataSubset.md) | A subset of a dataset, likely containing multiple files of multiple potential... |  no  |






## Properties

* Range: [CompressionEnum](CompressionEnum.md)




## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | data_sheets_schema:compression |
| native | data_sheets_schema:compression |




## LinkML Source

<details>
```yaml
name: compression
description: compression format used, if any. e.g., gzip, bzip2, zip
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
alias: compression
domain_of:
- Information
range: CompressionEnum

```
</details>
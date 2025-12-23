

# Slot: media_type 


_The media type of the data. This should be a MIME type._





URI: [dcat:mediaType](http://www.w3.org/ns/dcat#mediaType)
Alias: media_type

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [DataSubset](DataSubset.md) | A subset of a dataset, likely containing multiple files of multiple potential... |  no  |
| [Dataset](Dataset.md) | A single component of related observations and/or information that can be rea... |  no  |






## Properties

* Range: [MediaTypeEnum](MediaTypeEnum.md)




## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | dcat:mediaType |
| native | data_sheets_schema:media_type |
| exact | schema:encodingFormat |




## LinkML Source

<details>
```yaml
name: media_type
description: The media type of the data. This should be a MIME type.
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
exact_mappings:
- schema:encodingFormat
rank: 1000
slot_uri: dcat:mediaType
alias: media_type
domain_of:
- Dataset
range: MediaTypeEnum

```
</details>
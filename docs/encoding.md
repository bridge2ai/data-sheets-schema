

# Slot: encoding 


_the character encoding of the data_





URI: [dcat:mediaType](http://www.w3.org/ns/dcat#mediaType)
Alias: encoding

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [Dataset](Dataset.md) | A single component of related observations and/or information that can be rea... |  no  |
| [DataSubset](DataSubset.md) | A subset of a dataset, likely containing multiple files of multiple potential... |  no  |






## Properties

* Range: [EncodingEnum](EncodingEnum.md)




## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | dcat:mediaType |
| native | data_sheets_schema:encoding |




## LinkML Source

<details>
```yaml
name: encoding
description: the character encoding of the data
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
slot_uri: dcat:mediaType
alias: encoding
domain_of:
- Dataset
range: EncodingEnum

```
</details>
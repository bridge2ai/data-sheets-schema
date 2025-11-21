

# Slot: format 


_The file format, physical medium, or dimensions of a resource. This should be a file extension or MIME type._





URI: [dcterms:format](http://purl.org/dc/terms/format)
Alias: format

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [DataSubset](DataSubset.md) | A subset of a dataset, likely containing multiple files of multiple potential... |  no  |
| [Dataset](Dataset.md) | A single component of related observations and/or information that can be rea... |  no  |






## Properties

* Range: [FormatEnum](FormatEnum.md)




## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | dcterms:format |
| native | data_sheets_schema:format |




## LinkML Source

<details>
```yaml
name: format
description: The file format, physical medium, or dimensions of a resource. This should
  be a file extension or MIME type.
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
slot_uri: dcterms:format
alias: format
domain_of:
- Dataset
range: FormatEnum

```
</details>
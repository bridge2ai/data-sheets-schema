

# Slot: download_url 


_URL from which the data can be downloaded. This is not the same as the landing page, which is a page that describes the dataset. Rather, this URL points directly to the data itself._





URI: [dcat:downloadURL](http://www.w3.org/ns/dcat#downloadURL)
Alias: download_url

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [Information](Information.md) | Grouping for datasets and data files |  no  |
| [Dataset](Dataset.md) | A single component of related observations and/or information that can be rea... |  no  |
| [DataSubset](DataSubset.md) | A subset of a dataset, likely containing multiple files of multiple potential... |  no  |
| [DatasetCollection](DatasetCollection.md) | A collection of related datasets, likely containing multiple files of multipl... |  no  |






## Properties

* Range: [Uri](Uri.md)




## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | dcat:downloadURL |
| native | data_sheets_schema:download_url |
| exact | schema:url |




## LinkML Source

<details>
```yaml
name: download_url
description: URL from which the data can be downloaded. This is not the same as the
  landing page, which is a page that describes the dataset. Rather, this URL points
  directly to the data itself.
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
exact_mappings:
- schema:url
rank: 1000
slot_uri: dcat:downloadURL
alias: download_url
domain_of:
- Information
range: uri

```
</details>
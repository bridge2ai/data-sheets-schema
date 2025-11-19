

# Slot: version 



URI: [pav:version](http://purl.org/pav/version)
Alias: version

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [DatasetCollection](DatasetCollection.md) | A collection of related datasets, likely containing multiple files of multipl... |  no  |
| [Dataset](Dataset.md) | A single component of related observations and/or information that can be rea... |  no  |
| [Software](Software.md) | A software program or library |  no  |
| [DataSubset](DataSubset.md) | A subset of a dataset, likely containing multiple files of multiple potential... |  no  |
| [Information](Information.md) | Grouping for datasets and data files |  no  |






## Properties

* Range: [String](String.md)




## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | pav:version |
| native | data_sheets_schema:version |




## LinkML Source

<details>
```yaml
name: version
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
slot_uri: pav:version
alias: version
domain_of:
- Software
- Information
range: string

```
</details>
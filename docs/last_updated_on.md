

# Slot: last_updated_on 



URI: [pav:lastUpdatedOn](http://purl.org/pav/lastUpdatedOn)
Alias: last_updated_on

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [DatasetCollection](DatasetCollection.md) | A collection of related datasets, likely containing multiple files of multipl... |  no  |
| [Information](Information.md) | Grouping for datasets and data files |  no  |
| [Dataset](Dataset.md) | A single component of related observations and/or information that can be rea... |  no  |
| [DataSubset](DataSubset.md) | A subset of a dataset, likely containing multiple files of multiple potential... |  no  |






## Properties

* Range: [Datetime](Datetime.md)




## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | pav:lastUpdatedOn |
| native | data_sheets_schema:last_updated_on |




## LinkML Source

<details>
```yaml
name: last_updated_on
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
slot_uri: pav:lastUpdatedOn
alias: last_updated_on
domain_of:
- Information
range: datetime

```
</details>
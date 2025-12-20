

# Slot: principal_investigator 


_A key individual (Principal Investigator) responsible for or overseeing dataset creation._





URI: [dcterms:creator](http://purl.org/dc/terms/creator)
Alias: principal_investigator

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [Creator](Creator.md) | Who created the dataset (e |  no  |






## Properties

* Range: [Person](Person.md)




## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | dcterms:creator |
| native | data_sheets_schema:principal_investigator |
| exact | schema:creator |




## LinkML Source

<details>
```yaml
name: principal_investigator
description: A key individual (Principal Investigator) responsible for or overseeing
  dataset creation.
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
exact_mappings:
- schema:creator
rank: 1000
slot_uri: dcterms:creator
alias: principal_investigator
owner: Creator
domain_of:
- Creator
range: Person

```
</details>
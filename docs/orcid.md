

# Slot: orcid 


_ORCID (Open Researcher and Contributor ID) - a persistent digital identifier for researchers. Format: 0000-0000-0000-0000 (16 digits in groups of 4). Use this for stable cross-dataset identification._





URI: [schema:identifier](http://schema.org/identifier)
Alias: orcid

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [Person](Person.md) | An individual human being |  no  |






## Properties

* Range: [String](String.md)

* Regex pattern: `^\d{4}-\d{4}-\d{4}-\d{3}[0-9X]$`




## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | schema:identifier |
| native | data_sheets_schema:orcid |
| exact | schema:identifier |




## LinkML Source

<details>
```yaml
name: orcid
description: 'ORCID (Open Researcher and Contributor ID) - a persistent digital identifier
  for researchers. Format: 0000-0000-0000-0000 (16 digits in groups of 4). Use this
  for stable cross-dataset identification.'
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
exact_mappings:
- schema:identifier
rank: 1000
slot_uri: schema:identifier
alias: orcid
owner: Person
domain_of:
- Person
range: string
pattern: ^\d{4}-\d{4}-\d{4}-\d{3}[0-9X]$

```
</details>
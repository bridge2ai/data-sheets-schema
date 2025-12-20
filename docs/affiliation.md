

# Slot: affiliation 


_The organization(s) to which the person belongs in the context of this dataset. May vary across datasets; multivalued to support multiple affiliations._





URI: [schema:affiliation](http://schema.org/affiliation)
Alias: affiliation

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [Person](Person.md) | An individual human being |  no  |






## Properties

* Range: [Organization](Organization.md)

* Multivalued: True




## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | schema:affiliation |
| native | data_sheets_schema:affiliation |




## LinkML Source

<details>
```yaml
name: affiliation
description: The organization(s) to which the person belongs in the context of this
  dataset. May vary across datasets; multivalued to support multiple affiliations.
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
slot_uri: schema:affiliation
alias: affiliation
owner: Person
domain_of:
- Person
range: Organization
multivalued: true

```
</details>
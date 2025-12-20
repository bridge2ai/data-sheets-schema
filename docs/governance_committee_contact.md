

# Slot: governance_committee_contact 


_Contact person for data governance committee. This person can answer questions about data governance policies, access procedures, and oversight mechanisms._





URI: [schema:contactPoint](http://schema.org/contactPoint)
Alias: governance_committee_contact

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [ExportControlRegulatoryRestrictions](ExportControlRegulatoryRestrictions.md) | Do any export controls or other regulatory restrictions apply to the dataset ... |  no  |






## Properties

* Range: [Person](Person.md)




## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | schema:contactPoint |
| native | data_sheets_schema:governance_committee_contact |
| exact | schema:contactPoint |




## LinkML Source

<details>
```yaml
name: governance_committee_contact
description: Contact person for data governance committee. This person can answer
  questions about data governance policies, access procedures, and oversight mechanisms.
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
exact_mappings:
- schema:contactPoint
rank: 1000
slot_uri: schema:contactPoint
alias: governance_committee_contact
owner: ExportControlRegulatoryRestrictions
domain_of:
- ExportControlRegulatoryRestrictions
range: Person

```
</details>
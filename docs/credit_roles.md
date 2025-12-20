

# Slot: credit_roles 


_Contributor roles using the CRediT (Contributor Roles Taxonomy) for the principal investigator or creator team. Specifies the specific contributions made to this dataset (e.g., Conceptualization, Data Curation, Methodology). Note: roles are specified here rather than on Person directly, since the same person may have different roles across different datasets._





URI: [data_sheets_schema:credit_roles](https://w3id.org/bridge2ai/data-sheets-schema/credit_roles)
Alias: credit_roles

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [Creator](Creator.md) | Who created the dataset (e |  no  |






## Properties

* Range: [CRediTRoleEnum](CRediTRoleEnum.md)

* Multivalued: True




## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | data_sheets_schema:credit_roles |
| native | data_sheets_schema:credit_roles |




## LinkML Source

<details>
```yaml
name: credit_roles
description: 'Contributor roles using the CRediT (Contributor Roles Taxonomy) for
  the principal investigator or creator team. Specifies the specific contributions
  made to this dataset (e.g., Conceptualization, Data Curation, Methodology). Note:
  roles are specified here rather than on Person directly, since the same person may
  have different roles across different datasets.'
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
alias: credit_roles
owner: Creator
domain_of:
- Creator
range: CRediTRoleEnum
multivalued: true

```
</details>
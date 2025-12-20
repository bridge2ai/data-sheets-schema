

# Slot: data_use_permission 


_Structured data use permissions using the Data Use Ontology (DUO). Specifies permitted uses (e.g., general research, health/medical research, disease-specific research) and restrictions (e.g., non-commercial use, ethics approval required, collaboration required). See https://github.com/EBISPOT/DUO_





URI: [DUO:0000001](http://purl.obolibrary.org/obo/DUO_0000001)
Alias: data_use_permission

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [LicenseAndUseTerms](LicenseAndUseTerms.md) | Will the dataset be distributed under a copyright or other IP license, and/or... |  no  |






## Properties

* Range: [DataUsePermissionEnum](DataUsePermissionEnum.md)

* Multivalued: True




## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | DUO:0000001 |
| native | data_sheets_schema:data_use_permission |
| exact | DUO:0000001 |




## LinkML Source

<details>
```yaml
name: data_use_permission
description: Structured data use permissions using the Data Use Ontology (DUO). Specifies
  permitted uses (e.g., general research, health/medical research, disease-specific
  research) and restrictions (e.g., non-commercial use, ethics approval required,
  collaboration required). See https://github.com/EBISPOT/DUO
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
exact_mappings:
- DUO:0000001
rank: 1000
slot_uri: DUO:0000001
alias: data_use_permission
owner: LicenseAndUseTerms
domain_of:
- LicenseAndUseTerms
range: DataUsePermissionEnum
multivalued: true

```
</details>
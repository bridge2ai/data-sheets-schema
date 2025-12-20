

# Slot: informed_consent 


_Details about informed consent procedures, including consent type, documentation, and withdrawal mechanisms._





URI: [data_sheets_schema:informed_consent](https://w3id.org/bridge2ai/data-sheets-schema/informed_consent)
Alias: informed_consent

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [Dataset](Dataset.md) | A single component of related observations and/or information that can be rea... |  no  |
| [DataSubset](DataSubset.md) | A subset of a dataset, likely containing multiple files of multiple potential... |  no  |






## Properties

* Range: [InformedConsent](InformedConsent.md)

* Multivalued: True




## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | data_sheets_schema:informed_consent |
| native | data_sheets_schema:informed_consent |




## LinkML Source

<details>
```yaml
name: informed_consent
description: Details about informed consent procedures, including consent type, documentation,
  and withdrawal mechanisms.
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
alias: informed_consent
owner: Dataset
domain_of:
- Dataset
range: InformedConsent
multivalued: true
inlined: true
inlined_as_list: true

```
</details>
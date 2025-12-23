

# Slot: prohibited_uses 


_Explicitly prohibited or forbidden uses for this dataset. Stronger than discouraged_uses - these are not permitted._





URI: [data_sheets_schema:prohibited_uses](https://w3id.org/bridge2ai/data-sheets-schema/prohibited_uses)
Alias: prohibited_uses

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [DataSubset](DataSubset.md) | A subset of a dataset, likely containing multiple files of multiple potential... |  no  |
| [Dataset](Dataset.md) | A single component of related observations and/or information that can be rea... |  no  |






## Properties

* Range: [ProhibitedUse](ProhibitedUse.md)

* Multivalued: True




## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | data_sheets_schema:prohibited_uses |
| native | data_sheets_schema:prohibited_uses |




## LinkML Source

<details>
```yaml
name: prohibited_uses
description: Explicitly prohibited or forbidden uses for this dataset. Stronger than
  discouraged_uses - these are not permitted.
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
alias: prohibited_uses
owner: Dataset
domain_of:
- Dataset
range: ProhibitedUse
multivalued: true
inlined: true
inlined_as_list: true

```
</details>
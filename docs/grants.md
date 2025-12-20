

# Slot: grants 


_Grant mechanisms supporting dataset creation. Multiple grants may fund a single dataset._





URI: [schema:funding](http://schema.org/funding)
Alias: grants

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [FundingMechanism](FundingMechanism.md) | Who funded the creation of the dataset? If there is an associated grant, plea... |  no  |






## Properties

* Range: [Grant](Grant.md)

* Multivalued: True




## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | schema:funding |
| native | data_sheets_schema:grants |




## LinkML Source

<details>
```yaml
name: grants
description: Grant mechanisms supporting dataset creation. Multiple grants may fund
  a single dataset.
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
slot_uri: schema:funding
alias: grants
owner: FundingMechanism
domain_of:
- FundingMechanism
range: Grant
multivalued: true
inlined: true
inlined_as_list: true

```
</details>
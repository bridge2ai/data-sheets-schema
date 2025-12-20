

# Slot: grantor 


_Name/identifier of the organization providing monetary or resource support._





URI: [schema:funder](http://schema.org/funder)
Alias: grantor

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [FundingMechanism](FundingMechanism.md) | Who funded the creation of the dataset? If there is an associated grant, plea... |  no  |






## Properties

* Range: [Grantor](Grantor.md)




## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | schema:funder |
| native | data_sheets_schema:grantor |




## LinkML Source

<details>
```yaml
name: grantor
description: Name/identifier of the organization providing monetary or resource support.
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
slot_uri: schema:funder
alias: grantor
owner: FundingMechanism
domain_of:
- FundingMechanism
range: Grantor

```
</details>
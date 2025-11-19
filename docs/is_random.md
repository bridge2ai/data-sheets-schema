

# Slot: is_random 


_Indicates whether the sample is random._





URI: [data_sheets_schema:is_random](https://w3id.org/bridge2ai/data-sheets-schema/is_random)
Alias: is_random

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [SamplingStrategy](SamplingStrategy.md) | Does the dataset contain all possible instances, or is it a sample (not neces... |  no  |






## Properties

* Range: [Boolean](Boolean.md)

* Multivalued: True




## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | data_sheets_schema:is_random |
| native | data_sheets_schema:is_random |




## LinkML Source

<details>
```yaml
name: is_random
description: Indicates whether the sample is random.
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
alias: is_random
owner: SamplingStrategy
domain_of:
- SamplingStrategy
range: boolean
multivalued: true

```
</details>
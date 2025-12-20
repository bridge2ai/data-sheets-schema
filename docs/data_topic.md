

# Slot: data_topic 


_General topic of each instance (e.g., from Bridge2AI standards)._

__





URI: [dcat:theme](http://www.w3.org/ns/dcat#theme)
Alias: data_topic

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [Instance](Instance.md) | What do the instances that comprise the dataset represent (e |  no  |






## Properties

* Range: [Uriorcurie](Uriorcurie.md)




## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | dcat:theme |
| native | data_sheets_schema:data_topic |




## LinkML Source

<details>
```yaml
name: data_topic
description: 'General topic of each instance (e.g., from Bridge2AI standards).

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
values_from:
- B2AI_TOPIC
slot_uri: dcat:theme
alias: data_topic
owner: Instance
domain_of:
- Instance
range: uriorcurie

```
</details>
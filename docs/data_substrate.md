

# Slot: data_substrate 


_Type of data (e.g., raw text, images) from Bridge2AI standards._

__





URI: [dcterms:format](http://purl.org/dc/terms/format)
Alias: data_substrate

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
| self | dcterms:format |
| native | data_sheets_schema:data_substrate |




## LinkML Source

<details>
```yaml
name: data_substrate
description: 'Type of data (e.g., raw text, images) from Bridge2AI standards.

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
values_from:
- B2AI_SUBSTRATE
slot_uri: dcterms:format
alias: data_substrate
owner: Instance
domain_of:
- Instance
range: uriorcurie

```
</details>
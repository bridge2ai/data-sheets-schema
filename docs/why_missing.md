

# Slot: why_missing 


_Explanation of why each piece of data is missing._

__





URI: [dcterms:description](http://purl.org/dc/terms/description)
Alias: why_missing

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [MissingInfo](MissingInfo.md) | Is any information missing from individual instances? (e |  no  |






## Properties

* Range: [String](String.md)

* Multivalued: True




## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | dcterms:description |
| native | data_sheets_schema:why_missing |




## LinkML Source

<details>
```yaml
name: why_missing
description: 'Explanation of why each piece of data is missing.

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
slot_uri: dcterms:description
alias: why_missing
owner: MissingInfo
domain_of:
- MissingInfo
range: string
multivalued: true

```
</details>
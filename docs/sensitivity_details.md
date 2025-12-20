

# Slot: sensitivity_details 


_Details on sensitive data elements present and handling procedures._

__





URI: [dcterms:description](http://purl.org/dc/terms/description)
Alias: sensitivity_details

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [SensitiveElement](SensitiveElement.md) | Does the dataset contain data that might be considered sensitive (e |  no  |






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
| native | data_sheets_schema:sensitivity_details |




## LinkML Source

<details>
```yaml
name: sensitivity_details
description: 'Details on sensitive data elements present and handling procedures.

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
slot_uri: dcterms:description
alias: sensitivity_details
owner: SensitiveElement
domain_of:
- SensitiveElement
range: string
multivalued: true

```
</details>
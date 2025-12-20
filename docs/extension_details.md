

# Slot: extension_details 


_Details on extension mechanisms, contribution validation, and communication._

__





URI: [dcterms:description](http://purl.org/dc/terms/description)
Alias: extension_details

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [ExtensionMechanism](ExtensionMechanism.md) | If others want to extend/augment/build on/contribute to the dataset, is there... |  no  |






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
| native | data_sheets_schema:extension_details |




## LinkML Source

<details>
```yaml
name: extension_details
description: 'Details on extension mechanisms, contribution validation, and communication.

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
slot_uri: dcterms:description
alias: extension_details
owner: ExtensionMechanism
domain_of:
- ExtensionMechanism
range: string
multivalued: true

```
</details>
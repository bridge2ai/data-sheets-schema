

# Slot: maintainer_details 


_Details on who will support, host, or maintain the dataset._

__





URI: [dcterms:description](http://purl.org/dc/terms/description)
Alias: maintainer_details

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [Maintainer](Maintainer.md) | Who will be supporting/hosting/maintaining the dataset? |  no  |






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
| native | data_sheets_schema:maintainer_details |




## LinkML Source

<details>
```yaml
name: maintainer_details
description: 'Details on who will support, host, or maintain the dataset.

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
slot_uri: dcterms:description
alias: maintainer_details
owner: Maintainer
domain_of:
- Maintainer
range: string
multivalued: true

```
</details>
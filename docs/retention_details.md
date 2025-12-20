

# Slot: retention_details 


_Details on data retention limits and enforcement procedures._

__





URI: [dcterms:description](http://purl.org/dc/terms/description)
Alias: retention_details

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [RetentionLimits](RetentionLimits.md) | If the dataset relates to people, are there applicable limits on the retentio... |  no  |






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
| native | data_sheets_schema:retention_details |




## LinkML Source

<details>
```yaml
name: retention_details
description: 'Details on data retention limits and enforcement procedures.

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
slot_uri: dcterms:description
alias: retention_details
owner: RetentionLimits
domain_of:
- RetentionLimits
range: string
multivalued: true

```
</details>
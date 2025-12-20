

# Slot: anomaly_details 


_Details on errors, noise sources, or redundancies in the dataset._

__





URI: [dcterms:description](http://purl.org/dc/terms/description)
Alias: anomaly_details

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [DataAnomaly](DataAnomaly.md) | Are there any errors, sources of noise, or redundancies in the dataset? |  no  |






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
| native | data_sheets_schema:anomaly_details |




## LinkML Source

<details>
```yaml
name: anomaly_details
description: 'Details on errors, noise sources, or redundancies in the dataset.

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
slot_uri: dcterms:description
alias: anomaly_details
owner: DataAnomaly
domain_of:
- DataAnomaly
range: string
multivalued: true

```
</details>
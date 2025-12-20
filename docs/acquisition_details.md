

# Slot: acquisition_details 


_Details on how data was acquired for each instance._

__





URI: [dcterms:description](http://purl.org/dc/terms/description)
Alias: acquisition_details

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [InstanceAcquisition](InstanceAcquisition.md) | Describes how data associated with each instance was acquired (e |  no  |






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
| native | data_sheets_schema:acquisition_details |




## LinkML Source

<details>
```yaml
name: acquisition_details
description: 'Details on how data was acquired for each instance.

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
slot_uri: dcterms:description
alias: acquisition_details
owner: InstanceAcquisition
domain_of:
- InstanceAcquisition
range: string
multivalued: true

```
</details>
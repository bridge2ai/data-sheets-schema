

# Slot: version_details 


_Details on version support policies and obsolescence communication._

__





URI: [dcterms:description](http://purl.org/dc/terms/description)
Alias: version_details

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [VersionAccess](VersionAccess.md) | Will older versions of the dataset continue to be supported/hosted/maintained... |  no  |






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
| native | data_sheets_schema:version_details |




## LinkML Source

<details>
```yaml
name: version_details
description: 'Details on version support policies and obsolescence communication.

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
slot_uri: dcterms:description
alias: version_details
owner: VersionAccess
domain_of:
- VersionAccess
range: string
multivalued: true

```
</details>


# Slot: license_terms 


_Description of the dataset's license and terms of use (including links, costs, or usage constraints)._

__





URI: [dcterms:license](http://purl.org/dc/terms/license)
Alias: license_terms

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [LicenseAndUseTerms](LicenseAndUseTerms.md) | Will the dataset be distributed under a copyright or other IP license, and/or... |  no  |






## Properties

* Range: [String](String.md)

* Multivalued: True




## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | dcterms:license |
| native | data_sheets_schema:license_terms |




## LinkML Source

<details>
```yaml
name: license_terms
description: 'Description of the dataset''s license and terms of use (including links,
  costs, or usage constraints).

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
slot_uri: dcterms:license
alias: license_terms
owner: LicenseAndUseTerms
domain_of:
- LicenseAndUseTerms
range: string
multivalued: true

```
</details>
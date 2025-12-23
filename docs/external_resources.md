

# Slot: external_resources 


_Links or identifiers for external resources. Can be used either as a list of ExternalResource objects (in Dataset) or as a list of URL strings (within ExternalResource class)._





URI: [dcterms:references](http://purl.org/dc/terms/references)
Alias: external_resources

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [ExternalResource](ExternalResource.md) | Is the dataset self-contained or does it rely on external resources (e |  yes  |
| [DataSubset](DataSubset.md) | A subset of a dataset, likely containing multiple files of multiple potential... |  no  |
| [Dataset](Dataset.md) | A single component of related observations and/or information that can be rea... |  yes  |






## Properties

* Range: [String](String.md)

* Multivalued: True




## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | dcterms:references |
| native | data_sheets_schema:external_resources |




## LinkML Source

<details>
```yaml
name: external_resources
description: Links or identifiers for external resources. Can be used either as a
  list of ExternalResource objects (in Dataset) or as a list of URL strings (within
  ExternalResource class).
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
slot_uri: dcterms:references
alias: external_resources
domain_of:
- Dataset
- ExternalResource
range: string
multivalued: true

```
</details>
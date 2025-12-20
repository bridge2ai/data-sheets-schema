

# Slot: repository_details 


_Details on the repository of known dataset uses._

__





URI: [dcterms:description](http://purl.org/dc/terms/description)
Alias: repository_details

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [UseRepository](UseRepository.md) | Is there a repository that links to any or all papers or systems that use the... |  no  |






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
| native | data_sheets_schema:repository_details |




## LinkML Source

<details>
```yaml
name: repository_details
description: 'Details on the repository of known dataset uses.

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
slot_uri: dcterms:description
alias: repository_details
owner: UseRepository
domain_of:
- UseRepository
range: string
multivalued: true

```
</details>
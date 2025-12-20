

# Slot: warnings 



URI: [dcterms:description](http://purl.org/dc/terms/description)
Alias: warnings

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [ContentWarning](ContentWarning.md) | Does the dataset contain any data that might be offensive, insulting, threate... |  no  |






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
| native | data_sheets_schema:warnings |




## LinkML Source

<details>
```yaml
name: warnings
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
slot_uri: dcterms:description
alias: warnings
owner: ContentWarning
domain_of:
- ContentWarning
range: string
multivalued: true

```
</details>
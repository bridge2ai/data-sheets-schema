

# Slot: preprocessing_details 


_Details on preprocessing steps applied to the data._

__





URI: [dcterms:description](http://purl.org/dc/terms/description)
Alias: preprocessing_details

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [PreprocessingStrategy](PreprocessingStrategy.md) | Was any preprocessing of the data done (e |  no  |






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
| native | data_sheets_schema:preprocessing_details |




## LinkML Source

<details>
```yaml
name: preprocessing_details
description: 'Details on preprocessing steps applied to the data.

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
slot_uri: dcterms:description
alias: preprocessing_details
owner: PreprocessingStrategy
domain_of:
- PreprocessingStrategy
range: string
multivalued: true

```
</details>
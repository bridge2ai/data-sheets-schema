

# Slot: labeling_details 


_Details on labeling/annotation procedures and quality metrics._

__





URI: [dcterms:description](http://purl.org/dc/terms/description)
Alias: labeling_details

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [LabelingStrategy](LabelingStrategy.md) | Was any labeling of the data done (e |  no  |






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
| native | data_sheets_schema:labeling_details |




## LinkML Source

<details>
```yaml
name: labeling_details
description: 'Details on labeling/annotation procedures and quality metrics.

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
slot_uri: dcterms:description
alias: labeling_details
owner: LabelingStrategy
domain_of:
- LabelingStrategy
range: string
multivalued: true

```
</details>
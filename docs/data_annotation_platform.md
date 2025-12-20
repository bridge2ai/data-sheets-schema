

# Slot: data_annotation_platform 


_Platform or tool used for annotation (e.g., Label Studio, Prodigy, Amazon Mechanical Turk, custom annotation tool)._





URI: [schema:instrument](http://schema.org/instrument)
Alias: data_annotation_platform

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [LabelingStrategy](LabelingStrategy.md) | Was any labeling of the data done (e |  no  |






## Properties

* Range: [String](String.md)




## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | schema:instrument |
| native | data_sheets_schema:data_annotation_platform |
| exact | rai:dataAnnotationPlatform |




## LinkML Source

<details>
```yaml
name: data_annotation_platform
description: Platform or tool used for annotation (e.g., Label Studio, Prodigy, Amazon
  Mechanical Turk, custom annotation tool).
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
exact_mappings:
- rai:dataAnnotationPlatform
rank: 1000
slot_uri: schema:instrument
alias: data_annotation_platform
owner: LabelingStrategy
domain_of:
- LabelingStrategy
range: string

```
</details>


# Slot: annotations_per_item 


_Number of annotations collected per data item. Multiple annotations per item enable calculation of inter-annotator agreement._





URI: [data_sheets_schema:annotations_per_item](https://w3id.org/bridge2ai/data-sheets-schema/annotations_per_item)
Alias: annotations_per_item

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [LabelingStrategy](LabelingStrategy.md) | Was any labeling of the data done (e |  no  |






## Properties

* Range: [Integer](Integer.md)




## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | data_sheets_schema:annotations_per_item |
| native | data_sheets_schema:annotations_per_item |
| exact | rai:annotationsPerItem |




## LinkML Source

<details>
```yaml
name: annotations_per_item
description: Number of annotations collected per data item. Multiple annotations per
  item enable calculation of inter-annotator agreement.
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
exact_mappings:
- rai:annotationsPerItem
rank: 1000
alias: annotations_per_item
owner: LabelingStrategy
domain_of:
- LabelingStrategy
range: integer

```
</details>
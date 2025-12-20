

# Slot: annotator_demographics 


_Demographic information about annotators, if available and relevant (e.g., geographic location, language background, expertise level)._





URI: [data_sheets_schema:annotator_demographics](https://w3id.org/bridge2ai/data-sheets-schema/annotator_demographics)
Alias: annotator_demographics

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
| self | data_sheets_schema:annotator_demographics |
| native | data_sheets_schema:annotator_demographics |
| exact | rai:annotatorDemographics |




## LinkML Source

<details>
```yaml
name: annotator_demographics
description: Demographic information about annotators, if available and relevant (e.g.,
  geographic location, language background, expertise level).
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
exact_mappings:
- rai:annotatorDemographics
rank: 1000
alias: annotator_demographics
owner: LabelingStrategy
domain_of:
- LabelingStrategy
range: string
multivalued: true

```
</details>
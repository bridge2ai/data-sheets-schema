

# Slot: inter_annotator_agreement 


_Measure of agreement between annotators (e.g., Cohen's kappa, Fleiss' kappa, Krippendorff's alpha, percent agreement). Include both the metric name and value._





URI: [schema:measurementMethod](http://schema.org/measurementMethod)
Alias: inter_annotator_agreement

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
| self | schema:measurementMethod |
| native | data_sheets_schema:inter_annotator_agreement |




## LinkML Source

<details>
```yaml
name: inter_annotator_agreement
description: Measure of agreement between annotators (e.g., Cohen's kappa, Fleiss'
  kappa, Krippendorff's alpha, percent agreement). Include both the metric name and
  value.
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
slot_uri: schema:measurementMethod
alias: inter_annotator_agreement
owner: LabelingStrategy
domain_of:
- LabelingStrategy
range: string

```
</details>
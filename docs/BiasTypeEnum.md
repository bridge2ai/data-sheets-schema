# Enum: BiasTypeEnum 




_Types of bias that may be present in datasets. Values are mapped to the Artificial Intelligence Ontology (AIO) bias taxonomy from BioPortal. See https://bioportal.bioontology.org/ontologies/AIO_



URI: [data_sheets_schema:BiasTypeEnum](https://w3id.org/bridge2ai/data-sheets-schema/BiasTypeEnum)

## Permissible Values

| Value | Meaning | Description |
| --- | --- | --- |
| selection_bias | None | Bias arising from non-random selection of data or participants |
| measurement_bias | AIO:MeasurementBias | Bias in how data is measured or recorded |
| historical_bias | AIO:HistoricalBias | Bias reflecting historical inequities or societal biases |
| representation_bias | AIO:RepresentationBias | Certain groups are over- or under-represented in the data |
| aggregation_bias | None | Bias from inappropriately combining distinct groups |
| algorithmic_bias | None | Bias introduced or amplified by algorithmic processing |
| sampling_bias | None | Bias from sampling methodology not representative of the population |
| annotation_bias | None | Bias introduced during data labeling or annotation |
| confirmation_bias | AIO:ConfirmationBias | Bias from seeking data that confirms pre-existing beliefs |




## Slots

| Name | Description |
| ---  | --- |
| [bias_type](bias_type.md) | The type of bias identified, using standardized categories from the Artificia... |





## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema






## LinkML Source

<details>
```yaml
name: BiasTypeEnum
description: Types of bias that may be present in datasets. Values are mapped to the
  Artificial Intelligence Ontology (AIO) bias taxonomy from BioPortal. See https://bioportal.bioontology.org/ontologies/AIO
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
permissible_values:
  selection_bias:
    text: selection_bias
    description: Bias arising from non-random selection of data or participants.
    broad_mappings:
    - AIO:SelectionAndSamplingBias
  measurement_bias:
    text: measurement_bias
    description: Bias in how data is measured or recorded. Occurs when features and
      labels are proxies for desired quantities, potentially leading to differential
      performance.
    meaning: AIO:MeasurementBias
  historical_bias:
    text: historical_bias
    description: Bias reflecting historical inequities or societal biases. Long-standing
      biases encoded in society over time.
    meaning: AIO:HistoricalBias
  representation_bias:
    text: representation_bias
    description: Certain groups are over- or under-represented in the data. Results
      from non-random sampling of subgroups making trends non-generalizable to new
      populations.
    meaning: AIO:RepresentationBias
  aggregation_bias:
    text: aggregation_bias
    description: Bias from inappropriately combining distinct groups. Related to making
      inferences about individuals based on their group membership.
    broad_mappings:
    - AIO:EcologicalFallacyBias
  algorithmic_bias:
    text: algorithmic_bias
    description: Bias introduced or amplified by algorithmic processing. Computational
      bias from data analysis processes and methods.
    broad_mappings:
    - AIO:ProcessingBias
    - AIO:ComputationalBias
  sampling_bias:
    text: sampling_bias
    description: Bias from sampling methodology not representative of the population.
    broad_mappings:
    - AIO:SelectionAndSamplingBias
  annotation_bias:
    text: annotation_bias
    description: Bias introduced during data labeling or annotation. Occurs when annotators
      rely on heuristics or exhibit systematic patterns in labeling.
    broad_mappings:
    - AIO:AnnotatorReportingBias
  confirmation_bias:
    text: confirmation_bias
    description: Bias from seeking data that confirms pre-existing beliefs. Tendency
      to prefer information that confirms existing beliefs, influencing the search
      for, interpretation of, and recall of information.
    meaning: AIO:ConfirmationBias

```
</details>